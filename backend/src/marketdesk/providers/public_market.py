from __future__ import annotations

import asyncio
import json
import math
import re
import subprocess
from datetime import UTC, date, datetime, time, timedelta
from typing import Any, cast
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

import httpx

from marketdesk.models import (
    Bar,
    DatasetMeta,
    EquityDataset,
    EquityQuote,
    Freshness,
    IndexQuote,
    MarketEventRaw,
    SectorSnapshot,
)
from marketdesk.providers.base import ProviderUnavailable
from marketdesk.providers.iwencai import IwencaiProvider


def _market_observed_at(now: datetime) -> datetime:
    shanghai = ZoneInfo("Asia/Shanghai")
    local = now.astimezone(shanghai)
    market_date = local.date()
    if local.weekday() >= 5 or local.time() < time(9, 15):
        market_date -= timedelta(days=1)
        while market_date.weekday() >= 5:
            market_date -= timedelta(days=1)
        observed = datetime.combine(market_date, time(15), tzinfo=shanghai)
    elif local.time() > time(15):
        observed = datetime.combine(market_date, time(15), tzinfo=shanghai)
    else:
        observed = local
    return observed.astimezone(UTC)


class PublicMarketProvider:
    sina_list_url = "https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData"
    sina_count_url = "https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeStockCount"
    sina_sector_url = "https://vip.stock.finance.sina.com.cn/q/view/newSinaHy.php"
    eastmoney_list_url = "https://push2delay.eastmoney.com/api/qt/clist/get"
    tencent_quote_url = (
        "https://qt.gtimg.cn/q=sh000001,sz399001,sz399006,sh000300,sh000016,sh000688"
    )
    tencent_kline_url = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
    eastmoney_fast_news_url = "https://np-weblist.eastmoney.com/comm/web/getFastNewsList"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self.client = client or httpx.AsyncClient(
            timeout=12,
            headers={
                "User-Agent": "Mozilla/5.0 MarketDesk/0.1",
                "Referer": "https://finance.sina.com.cn/",
            },
            follow_redirects=True,
        )
        self._enhancement_status: dict[str, dict[str, Any]] = {
            "eastmoney_fund_flow": {
                "status": "not_checked",
                "required": False,
                "description": "东方财富资金流增强源",
            },
            "semantic_research": {
                "status": "not_configured",
                "required": False,
                "description": "语义研究增强",
            },
            "eastmoney_fast_news": {
                "status": "not_checked",
                "required": False,
                "description": "东方财富市场快讯",
            },
        }
        self.research_provider = IwencaiProvider(client=self.client)
        if self.research_provider.configured:
            self._mark_research_status("configured")

    async def _get(self, url: str, params: dict[str, Any] | None = None) -> httpx.Response:
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = await self.client.get(url, params=params)
                response.raise_for_status()
                return response
            except httpx.HTTPError as error:
                last_error = error
                if attempt < 2:
                    await asyncio.sleep(0.2 * (attempt + 1))
        raise ProviderUnavailable(f"public market request failed: {last_error}") from last_error

    async def _get_eastmoney_json(self, params: dict[str, Any]) -> dict[str, Any]:
        try:
            response = await self.client.get(
                self.eastmoney_list_url,
                params=params,
                headers={
                    "User-Agent": "Mozilla/5.0 MarketDesk/0.1",
                    "Referer": "https://quote.eastmoney.com/",
                },
            )
            response.raise_for_status()
            return cast(dict[str, Any], response.json())
        except (httpx.HTTPError, ValueError) as error:
            return self._get_eastmoney_json_with_curl(params, error)

    def _get_eastmoney_json_with_curl(
        self, params: dict[str, Any], original_error: Exception
    ) -> dict[str, Any]:
        url = f"{self.eastmoney_list_url}?{urlencode(params)}"
        try:
            completed = subprocess.run(
                [
                    "curl",
                    "-fsSL",
                    "--http1.1",
                    "-A",
                    "Mozilla/5.0 MarketDesk/0.1",
                    "-e",
                    "https://quote.eastmoney.com/",
                    "--max-time",
                    "12",
                    url,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            return cast(dict[str, Any], json.loads(completed.stdout))
        except (OSError, subprocess.CalledProcessError, ValueError) as curl_error:
            raise ProviderUnavailable(
                f"eastmoney request failed: {original_error}; curl fallback failed: {curl_error}"
            ) from curl_error

    def provider_status(self) -> dict[str, dict[str, Any]]:
        return self._enhancement_status

    def _mark_fund_flow_status(self, status: str, error: str | None = None) -> None:
        payload: dict[str, Any] = {
            "status": status,
            "required": False,
            "description": "东方财富资金流增强源",
        }
        if error:
            payload["error"] = error
        self._enhancement_status["eastmoney_fund_flow"] = payload

    def _mark_research_status(self, status: str, error: str | None = None) -> None:
        payload: dict[str, Any] = {
            "status": status,
            "required": False,
            "description": "语义研究增强",
        }
        if error:
            payload["error"] = error
        self._enhancement_status["semantic_research"] = payload

    def _mark_fast_news_status(self, status: str, error: str | None = None) -> None:
        payload: dict[str, Any] = {
            "status": status,
            "required": False,
            "description": "东方财富市场快讯",
        }
        if error:
            payload["error"] = error
        self._enhancement_status["eastmoney_fast_news"] = payload

    @staticmethod
    def _float(value: Any) -> float | None:
        try:
            return None if value in (None, "", "-", "--") else float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _symbol(raw: str) -> str:
        return f"{raw[:2].upper()}.{raw[-6:]}"

    @staticmethod
    def _symbol_from_code(code: str) -> str:
        market = "SH" if code.startswith(("5", "6", "9")) else "SZ"
        return f"{market}.{code}"

    def normalize_equities(self, rows: list[dict[str, Any]]) -> EquityDataset:
        items: list[EquityQuote] = []
        present = 0
        required = 0
        for row in rows:
            raw_symbol = str(row.get("symbol") or "")
            code = str(row.get("code") or raw_symbol[-6:])
            if len(code) != 6 or not raw_symbol:
                continue
            core = [
                self._float(row.get(key))
                for key in ("trade", "changepercent", "amount", "turnoverratio", "mktcap")
            ]
            present += sum(value is not None for value in core)
            required += len(core)
            market_cap_wan = self._float(row.get("mktcap"))
            items.append(
                EquityQuote(
                    symbol=self._symbol(raw_symbol),
                    code=code,
                    name=str(row.get("name") or code),
                    price=core[0],
                    change_pct=core[1],
                    amount=core[2],
                    turnover_rate=core[3],
                    volume_ratio=None,
                    pe=self._float(row.get("per")),
                    pb=self._float(row.get("pb")),
                    market_cap=market_cap_wan * 10_000 if market_cap_wan is not None else None,
                    net_flow=None,
                    sector=None,
                )
            )
        if not items:
            raise ProviderUnavailable("empty Sina A-share universe")
        now = datetime.now(UTC)
        freshness = Freshness.DELAYED if now.weekday() >= 5 else Freshness.FRESH
        return EquityDataset(
            meta=DatasetMeta(
                source="sina+tencent",
                observed_at=_market_observed_at(now),
                fetched_at=now,
                freshness=freshness,
                coverage=present / required if required else 0,
            ),
            items=items,
        )

    def normalize_sectors(self, text: str) -> list[SectorSnapshot]:
        match = re.search(r"=\s*(\{.*\})\s*;?", text, re.S)
        if not match:
            raise ProviderUnavailable("invalid Sina sector payload")
        payload = json.loads(match.group(1))
        sectors: list[SectorSnapshot] = []
        for code, value in payload.items():
            parts = str(value).split(",")
            if len(parts) < 6:
                continue
            sectors.append(
                SectorSnapshot(
                    code=code, name=parts[1], change_pct=self._float(parts[5]), net_flow=None
                )
            )
        return sorted(sectors, key=lambda item: item.change_pct or -999, reverse=True)

    @staticmethod
    def normalize_eastmoney_sector_funds(payload: dict[str, Any]) -> list[SectorSnapshot]:
        rows = (payload.get("data") or {}).get("diff") or []
        sectors: list[SectorSnapshot] = []
        for row in rows:
            code = str(row.get("f12") or "")
            if not code:
                continue
            sectors.append(
                SectorSnapshot(
                    code=code,
                    name=str(row.get("f14") or code),
                    change_pct=PublicMarketProvider._float(row.get("f3")),
                    net_flow=PublicMarketProvider._float(row.get("f62")),
                )
            )
        return sectors

    @staticmethod
    def normalize_eastmoney_equity_enrichment(
        rows: list[dict[str, Any]],
    ) -> dict[str, dict[str, float | str]]:
        enrichment: dict[str, dict[str, float | str]] = {}
        for row in rows:
            code = str(row.get("f12") or "")
            if not code:
                continue
            values: dict[str, float | str] = {}
            net_flow = PublicMarketProvider._float(row.get("f62"))
            if net_flow is not None:
                values["net_flow"] = net_flow
            sector = str(row.get("f100") or "")
            if sector:
                values["sector"] = sector
            if values:
                enrichment[code] = values
        return enrichment

    @staticmethod
    def normalize_eastmoney_board_constituents(payload: dict[str, Any]) -> list[EquityQuote]:
        rows = (payload.get("data") or {}).get("diff") or []
        quotes: list[EquityQuote] = []
        for row in rows:
            code = str(row.get("f12") or "")
            if not code:
                continue
            quotes.append(
                EquityQuote(
                    symbol=PublicMarketProvider._symbol_from_code(code),
                    code=code,
                    name=str(row.get("f14") or code),
                    price=PublicMarketProvider._float(row.get("f2")),
                    change_pct=PublicMarketProvider._float(row.get("f3")),
                    amount=PublicMarketProvider._float(row.get("f6")),
                    turnover_rate=PublicMarketProvider._float(row.get("f8")),
                    pe=PublicMarketProvider._float(row.get("f9")),
                    volume_ratio=PublicMarketProvider._float(row.get("f10")),
                    market_cap=PublicMarketProvider._float(row.get("f20")),
                    pb=PublicMarketProvider._float(row.get("f23")),
                    net_flow=PublicMarketProvider._float(row.get("f62")),
                    sector=str(row.get("f100") or "") or None,
                )
            )
        return quotes

    def normalize_indices(self, text: str) -> list[IndexQuote]:
        indices: list[IndexQuote] = []
        for raw_symbol, body in re.findall(r"v_(\w+)=\"([^\"]*)\"", text):
            fields = body.split("~")
            if len(fields) < 33:
                continue
            amount = None
            if len(fields) > 37 and "/" in fields[37]:
                amount = self._float(fields[37].split("/")[-1])
            indices.append(
                IndexQuote(
                    symbol=self._symbol(raw_symbol),
                    name=fields[1],
                    price=self._float(fields[3]),
                    change_pct=self._float(fields[32]),
                    amount=amount,
                )
            )
        if not indices:
            raise ProviderUnavailable("empty Tencent index payload")
        return indices

    def normalize_kline(self, payload: dict[str, Any], symbol: str) -> list[Bar]:
        market, code = symbol.split(".", 1)
        key = f"{market.lower()}{code}"
        data = payload.get("data", {}).get(key, {})
        rows = data.get("qfqday") or data.get("day") or []
        bars: list[Bar] = []
        for row in rows:
            if len(row) < 6:
                continue
            close = float(row[2])
            volume = float(row[5])
            bars.append(
                Bar(
                    date=date.fromisoformat(row[0]),
                    open=float(row[1]),
                    close=close,
                    high=float(row[3]),
                    low=float(row[4]),
                    volume=volume,
                    amount=close * volume * 100,
                )
            )
        return bars

    @staticmethod
    def _eastmoney_related(raw_items: list[Any]) -> tuple[list[str], list[str]]:
        symbols: list[str] = []
        sectors: list[str] = []
        for item in raw_items:
            raw = str(item)
            if raw.startswith("90.BK"):
                sectors.append(raw.split(".", 1)[1])
                continue
            if "." not in raw:
                continue
            market, code = raw.split(".", 1)
            if len(code) != 6 or not code.isdigit():
                continue
            if market == "1":
                symbols.append(f"SH.{code}")
            elif market == "0":
                symbols.append(f"SZ.{code}")
        return list(dict.fromkeys(symbols)), list(dict.fromkeys(sectors))

    @staticmethod
    def normalize_fast_news(payload: dict[str, Any]) -> list[MarketEventRaw]:
        rows = (payload.get("data") or {}).get("fastNewsList") or []
        events: list[MarketEventRaw] = []
        shanghai = ZoneInfo("Asia/Shanghai")
        for row in rows:
            event_id = str(row.get("code") or row.get("realSort") or "")
            title = str(row.get("title") or "").strip()
            summary = str(row.get("summary") or title).strip()
            show_time = str(row.get("showTime") or "")
            if not event_id or not title or not show_time:
                continue
            try:
                published_at = datetime.fromisoformat(show_time).replace(tzinfo=shanghai)
            except ValueError:
                continue
            symbols, sectors = PublicMarketProvider._eastmoney_related(row.get("stockList") or [])
            events.append(
                MarketEventRaw(
                    id=event_id,
                    title=title,
                    summary=summary,
                    source="东方财富快讯",
                    url=f"https://finance.eastmoney.com/a/{event_id}.html",
                    published_at=published_at.astimezone(UTC),
                    related_symbols=symbols,
                    related_sectors=sectors,
                )
            )
        return events

    async def fetch_equities(self) -> EquityDataset:
        count_response = await self._get(self.sina_count_url, {"node": "hs_a"})
        total = int(count_response.json())
        page_count = math.ceil(total / 100)
        semaphore = asyncio.Semaphore(5)

        async def fetch_page(page: int) -> list[dict[str, Any]]:
            async with semaphore:
                response = await self._get(
                    self.sina_list_url,
                    {
                        "page": page,
                        "num": 100,
                        "sort": "symbol",
                        "asc": 1,
                        "node": "hs_a",
                        "symbol": "",
                        "_s_r_a": "page",
                    },
                )
                return cast(list[dict[str, Any]], response.json())

        pages = await asyncio.gather(*(fetch_page(page) for page in range(1, page_count + 1)))
        dataset = self.normalize_equities([row for page in pages for row in page])
        try:
            enrichment = await self._fetch_eastmoney_equity_enrichment()
        except Exception as error:
            self._mark_fund_flow_status("partial", str(error))
            return dataset
        if not enrichment:
            self._mark_fund_flow_status("partial", "empty Eastmoney equity enrichment")
            return dataset
        self._mark_fund_flow_status("ready")
        items = [
            item.model_copy(update=enrichment[item.code]) if item.code in enrichment else item
            for item in dataset.items
        ]
        return dataset.model_copy(
            update={
                "meta": dataset.meta.model_copy(update={"source": "sina+tencent+eastmoney"}),
                "items": items,
            }
        )

    async def fetch_indices(self) -> list[IndexQuote]:
        response = await self._get(self.tencent_quote_url)
        return self.normalize_indices(response.content.decode("gb18030", errors="replace"))

    async def fetch_sectors(self) -> list[SectorSnapshot]:
        response = await self._get(self.sina_sector_url)
        sectors = self.normalize_sectors(response.content.decode("gb18030", errors="replace"))
        try:
            funds = await self._fetch_eastmoney_sector_funds()
        except Exception as error:
            self._mark_fund_flow_status("partial", str(error))
            return sectors
        if funds:
            self._mark_fund_flow_status("ready")
            return sorted(funds, key=lambda item: item.change_pct or -999, reverse=True)[:120]
        return sectors

    async def fetch_sector_constituents(self, sector_code: str) -> list[EquityQuote]:
        if sector_code.upper().startswith("BK"):
            payload = await self._get_eastmoney_json(
                {
                    "pn": 1,
                    "pz": 80,
                    "po": 1,
                    "np": 1,
                    "fltt": 2,
                    "fid": "f3",
                    "fs": f"b:{sector_code}",
                    "fields": "f12,f14,f2,f3,f6,f8,f9,f10,f20,f23,f62,f100",
                }
            )
            return self.normalize_eastmoney_board_constituents(payload)
        response = await self._get(
            self.sina_list_url,
            {
                "page": 1,
                "num": 80,
                "sort": "amount",
                "asc": 0,
                "node": sector_code,
                "symbol": "",
                "_s_r_a": "page",
            },
        )
        return self.normalize_equities(cast(list[dict[str, Any]], response.json())).items

    async def _fetch_eastmoney_sector_funds(self) -> list[SectorSnapshot]:
        payload = await self._get_eastmoney_json(
            {
                "pn": 1,
                "pz": 200,
                "po": 1,
                "np": 1,
                "fltt": 2,
                "fid": "f3",
                "fs": "m:90+t:2+f:!50",
                "fields": "f12,f14,f3,f62",
            }
        )
        return self.normalize_eastmoney_sector_funds(payload)

    async def _fetch_eastmoney_equity_enrichment(self) -> dict[str, dict[str, float | str]]:
        params = {
            "pn": 1,
            "pz": 100,
            "po": 1,
            "np": 1,
            "fltt": 2,
            "invt": 2,
            "fid": "f62",
            "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",
            "fields": "f12,f62,f100",
        }
        first_payload = await self._get_eastmoney_json(params)
        first_data = first_payload.get("data") or {}
        rows = list(first_data.get("diff") or [])
        total = int(first_data.get("total") or len(rows))
        page_size = max(1, len(rows))
        page_count = math.ceil(total / page_size)
        semaphore = asyncio.Semaphore(3)

        async def fetch_page(page: int) -> list[dict[str, Any]]:
            async with semaphore:
                payload = await self._get_eastmoney_json({**params, "pn": page})
                return list((payload.get("data") or {}).get("diff") or [])

        if page_count > 1:
            pages = await asyncio.gather(*(fetch_page(page) for page in range(2, page_count + 1)))
            for page_rows in pages:
                rows.extend(page_rows)
        return self.normalize_eastmoney_equity_enrichment(rows)

    async def fetch_equity_enrichment(self, symbol: str) -> dict[str, float | str]:
        _market, code = symbol.split(".", 1)
        enrichment = await self._fetch_eastmoney_equity_enrichment()
        return enrichment.get(code, {})

    async def fetch_research_enrichment(
        self, symbol: str, name: str, sector: str | None
    ) -> list[str]:
        if not self.research_provider.configured:
            self._mark_research_status("not_configured")
            return []
        try:
            evidence = await self.research_provider.fetch_research_evidence(symbol, name, sector)
        except ProviderUnavailable as error:
            self._mark_research_status("partial", str(error))
            return []
        self._mark_research_status("ready" if evidence else "empty")
        return evidence

    async def fetch_market_events(self, limit: int = 50) -> list[MarketEventRaw]:
        try:
            response = await self.client.get(
                self.eastmoney_fast_news_url,
                params={
                    "client": "web",
                    "biz": "web_724",
                    "fastColumn": "102",
                    "sortEnd": "",
                    "pageSize": limit,
                    "req_trace": str(int(datetime.now(UTC).timestamp() * 1000)),
                },
                headers={
                    "User-Agent": "Mozilla/5.0 MarketDesk/0.1",
                    "Referer": "https://kuaixun.eastmoney.com/",
                },
            )
            response.raise_for_status()
            events = self.normalize_fast_news(response.json())
        except (httpx.HTTPError, ValueError) as error:
            self._mark_fast_news_status("partial", str(error))
            return []
        self._mark_fast_news_status("ready" if events else "empty")
        return events[:limit]

    async def fetch_kline(self, symbol: str, limit: int = 180) -> list[Bar]:
        market, code = symbol.split(".", 1)
        raw = f"{market.lower()}{code}"
        response = await self._get(self.tencent_kline_url, {"param": f"{raw},day,,,{limit},qfq"})
        return self.normalize_kline(response.json(), symbol)
