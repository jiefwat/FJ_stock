from __future__ import annotations

import asyncio
import html
import json
import math
import re
import subprocess
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, time, timedelta
from typing import Any, Literal, cast
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

import httpx

from marketdesk.models import (
    AskStockResponse,
    Bar,
    DatasetMeta,
    EquityDataset,
    EquityQuote,
    EvidenceDocument,
    FinancialPeriod,
    Freshness,
    IndexQuote,
    InstrumentTheme,
    MarketEventRaw,
    SectorSnapshot,
    SemanticScreenResult,
    StockNewsItem,
    TradingAnomaly,
)
from marketdesk.providers.base import ProviderUnavailable
from marketdesk.providers.cn_evidence import AshareEvidenceProvider
from marketdesk.providers.global_market import GlobalMarketProvider
from marketdesk.providers.iwencai import IwencaiProvider
from marketdesk.providers.llm_web import LLMWebAskContext, LLMWebAskProvider


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
    eastmoney_financial_url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
    eastmoney_stock_news_url = "https://search-api-web.eastmoney.com/search/jsonp"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self.client = client or httpx.AsyncClient(
            timeout=12,
            headers={
                "User-Agent": "Mozilla/5.0 MarketDesk/0.1",
                "Referer": "https://finance.sina.com.cn/",
            },
            follow_redirects=True,
            trust_env=False,
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
        self.evidence_provider = AshareEvidenceProvider(client=self.client)
        self.global_provider = GlobalMarketProvider(client=self.client)
        self.llm_web_provider = LLMWebAskProvider()
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
        return {
            **self._enhancement_status,
            **self.evidence_provider.provider_status(),
            **self.llm_web_provider.provider_status(),
        }

    @property
    def llm_web_configured(self) -> bool:
        return self.llm_web_provider.configured

    async def ask_stock_with_llm(self, context: LLMWebAskContext) -> AskStockResponse:
        return await self.llm_web_provider.ask_stock(context)

    async def stream_ask_stock_with_llm(self, context: LLMWebAskContext) -> AsyncIterator[str]:
        async for chunk in self.llm_web_provider.stream_answer_text(context):
            yield chunk

    def build_streamed_llm_answer(self, context: LLMWebAskContext, text: str) -> AskStockResponse:
        return self.llm_web_provider.streamed_response(context, text)

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
    def _ratio_percent(value: Any) -> float | None:
        number = PublicMarketProvider._float(value)
        if number is None:
            return None
        return number * 100 if abs(number) <= 2 else number

    @staticmethod
    def _symbol(raw: str) -> str:
        return f"{raw[:2].upper()}.{raw[-6:]}"

    @staticmethod
    def _symbol_from_code(code: str) -> str:
        market = "SH" if code.startswith(("5", "6", "9")) else "SZ"
        return f"{market}.{code}"

    @staticmethod
    def _a_share_profile(
        code: str, name: str
    ) -> tuple[Literal["SH", "SZ", "BJ"], float | None]:
        normalized_name = name.upper()
        if code.startswith(("4", "8")):
            exchange: Literal["SH", "SZ", "BJ"] = "BJ"
        else:
            exchange = "SH" if code.startswith(("5", "6", "9")) else "SZ"
        if normalized_name.startswith(("N", "C")):
            return exchange, None
        if "ST" in normalized_name:
            return exchange, 5.0
        if exchange == "BJ":
            return exchange, 30.0
        if code.startswith(("300", "301", "688")):
            return exchange, 20.0
        return exchange, 10.0

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
            name = str(row.get("name") or code)
            exchange, price_limit_pct = self._a_share_profile(code, name)
            items.append(
                EquityQuote(
                    symbol=self._symbol(raw_symbol),
                    code=code,
                    name=name,
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
                    exchange=exchange,
                    price_limit_pct=price_limit_pct,
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
            name = str(row.get("f14") or code)
            exchange, price_limit_pct = PublicMarketProvider._a_share_profile(code, name)
            quotes.append(
                EquityQuote(
                    symbol=PublicMarketProvider._symbol_from_code(code),
                    code=code,
                    name=name,
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
                    exchange=exchange,
                    price_limit_pct=price_limit_pct,
                )
            )
        return quotes

    @staticmethod
    def normalize_financial_periods(payload: dict[str, Any]) -> list[FinancialPeriod]:
        rows = (payload.get("result") or {}).get("data") or []
        periods: list[FinancialPeriod] = []
        seen: set[date] = set()
        for row in rows:
            raw_date = str(row.get("REPORT_DATE") or "")[:10]
            try:
                report_date = date.fromisoformat(raw_date)
            except ValueError:
                continue
            if report_date in seen:
                continue
            seen.add(report_date)
            periods.append(
                FinancialPeriod(
                    report_date=report_date,
                    report_label=str(row.get("REPORT_DATE_NAME") or raw_date),
                    report_type=str(row.get("REPORT_TYPE") or "定期报告"),
                    revenue=PublicMarketProvider._float(row.get("TOTALOPERATEREVE")),
                    revenue_yoy=PublicMarketProvider._float(row.get("TOTALOPERATEREVETZ")),
                    net_profit=PublicMarketProvider._float(row.get("PARENTNETPROFIT")),
                    net_profit_yoy=PublicMarketProvider._float(row.get("PARENTNETPROFITTZ")),
                    roe=PublicMarketProvider._float(row.get("ROEJQ")),
                    gross_margin=PublicMarketProvider._float(row.get("XSMLL")),
                    operating_cash_flow_per_share=PublicMarketProvider._float(
                        row.get("MGJYXJJE")
                    ),
                    cash_receipts_to_revenue=PublicMarketProvider._ratio_percent(
                        row.get("JYXJLYYSR")
                    ),
                    debt_to_assets=PublicMarketProvider._float(row.get("ZCFZL")),
                )
            )
        return sorted(periods, key=lambda item: item.report_date, reverse=True)

    @staticmethod
    def _clean_article_text(value: Any) -> str:
        text = re.sub(r"<[^>]+>", "", str(value or ""))
        return re.sub(r"\s+", " ", html.unescape(text)).strip()

    @staticmethod
    def normalize_stock_news(payload_text: str) -> list[StockNewsItem]:
        match = re.fullmatch(r"\s*[\w$]+\((.*)\)\s*;?\s*", payload_text, re.S)
        if not match:
            raise ProviderUnavailable("invalid Eastmoney stock news JSONP")
        try:
            payload = json.loads(match.group(1))
        except ValueError as error:
            raise ProviderUnavailable("invalid Eastmoney stock news payload") from error
        result = payload.get("result") or {}
        rows = result.get("cmsArticleWebOld") or []
        if isinstance(rows, dict):
            rows = rows.get("list") or rows.get("data") or []
        shanghai = ZoneInfo("Asia/Shanghai")
        items: list[StockNewsItem] = []
        seen: set[str] = set()
        for row in rows:
            title = PublicMarketProvider._clean_article_text(row.get("title"))
            url = str(row.get("url") or "").strip()
            raw_date = str(row.get("date") or "").strip()
            code = str(row.get("code") or "").strip() or url.rsplit("/", 1)[-1]
            if not title or not code or not url.startswith(("http://", "https://")):
                continue
            try:
                published_at = datetime.fromisoformat(raw_date).replace(tzinfo=shanghai)
            except ValueError:
                continue
            item_id = f"eastmoney-news:{code}"
            if item_id in seen:
                continue
            seen.add(item_id)
            items.append(
                StockNewsItem(
                    id=item_id,
                    title=title,
                    summary=PublicMarketProvider._clean_article_text(row.get("content"))[:500],
                    media=PublicMarketProvider._clean_article_text(row.get("mediaName"))
                    or "东方财富",
                    url=url,
                    published_at=published_at.astimezone(UTC),
                )
            )
        return sorted(items, key=lambda item: item.published_at, reverse=True)

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

    async def fetch_market_groups(
        self, kind: Literal["concept", "industry"]
    ) -> list[SectorSnapshot]:
        board_type = 3 if kind == "concept" else 2
        payload = await self._get_eastmoney_json(
            {
                "pn": 1,
                "pz": 200,
                "po": 1,
                "np": 1,
                "fltt": 2,
                "fid": "f3",
                "fs": f"m:90+t:{board_type}+f:!50",
                "fields": "f12,f14,f3,f62",
            }
        )
        return self.normalize_eastmoney_sector_funds(payload)

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

    async def fetch_equity_period_ranking(
        self, days: int, limit: int = 100
    ) -> SemanticScreenResult:
        period_fields = {5: "f109", 10: "f160", 60: "f24"}
        field = period_fields.get(days)
        if field is None:
            raise ValueError(f"unsupported equity ranking period: {days}")
        bounded_limit = min(max(limit, 1), 100)
        payload = await self._get_eastmoney_json(
            {
                "pn": 1,
                "pz": bounded_limit,
                "po": 1,
                "np": 1,
                "fltt": 2,
                "invt": 2,
                "fid": field,
                "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",
                "fields": f"f12,f14,f2,f3,{field}",
            }
        )
        rows = list((payload.get("data") or {}).get("diff") or [])
        period_label = f"近{days}日涨跌幅"
        normalized: list[dict[str, str | float | None]] = []
        for row in rows:
            code = str(row.get("f12") or "").strip()
            change = self._float(row.get(field))
            if not code or change is None:
                continue
            normalized.append(
                {
                    "股票代码": code,
                    "股票简称": str(row.get("f14") or code),
                    period_label: change,
                    "最新价": self._float(row.get("f2")),
                    "今日涨跌幅": self._float(row.get("f3")),
                }
            )
        if not normalized:
            raise ProviderUnavailable(f"empty Eastmoney {days}-day equity ranking")
        return SemanticScreenResult(
            columns=["股票代码", "股票简称", period_label, "最新价", "今日涨跌幅"],
            rows=normalized[:bounded_limit],
        )

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

    async def fetch_global_quote(self, symbol: str, name: str | None = None) -> EquityQuote:
        return await self.global_provider.fetch_quote(symbol, name)

    async def search_global_quotes(self, query: str, limit: int = 10) -> list[EquityQuote]:
        return await self.global_provider.search(query, limit)

    async def fetch_research_enrichment(
        self, symbol: str, name: str, sector: str | None
    ) -> list[str]:
        if not symbol.startswith(("SH.", "SZ.", "BJ.")):
            return []
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

    async def query_stock_screen(
        self, question: str, limit: int = 20
    ) -> SemanticScreenResult:
        if not self.research_provider.configured:
            self._mark_research_status("not_configured")
            raise ProviderUnavailable("semantic stock screening is not configured")
        try:
            result = await self.research_provider.query_stocks(question, limit)
        except ProviderUnavailable as error:
            self._mark_research_status("partial", str(error))
            raise
        self._mark_research_status("ready" if result.rows else "empty")
        return result

    async def fetch_market_events(self, limit: int = 50) -> list[MarketEventRaw]:
        events: list[MarketEventRaw] = []
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
        else:
            self._mark_fast_news_status("ready" if events else "empty")
        if events:
            return events[:limit]
        try:
            return await self.evidence_provider.fetch_cls_events(limit)
        except ProviderUnavailable:
            return []

    async def fetch_financial_periods(
        self, symbol: str, limit: int = 5
    ) -> list[FinancialPeriod]:
        if not symbol.startswith(("SH.", "SZ.", "BJ.")):
            return []
        market, code = symbol.split(".", 1)
        response = await self._get(
            self.eastmoney_financial_url,
            {
                "reportName": "RPT_F10_FINANCE_MAINFINADATA",
                "columns": "ALL",
                "filter": f'(SECUCODE="{code}.{market}")',
                "pageNumber": 1,
                "pageSize": max(1, min(limit, 10)),
                "sortColumns": "REPORT_DATE",
                "sortTypes": -1,
                "source": "WEB",
                "client": "WEB",
            },
        )
        try:
            payload = response.json()
        except ValueError as error:
            raise ProviderUnavailable("invalid Eastmoney financial payload") from error
        return self.normalize_financial_periods(cast(dict[str, Any], payload))[:limit]

    async def fetch_stock_news(
        self, symbol: str, name: str, limit: int = 20
    ) -> list[StockNewsItem]:
        if not symbol.startswith(("SH.", "SZ.", "BJ.")):
            return []
        query = {
            "uid": "",
            "keyword": name,
            "type": ["cmsArticleWebOld"],
            "client": "web",
            "clientType": "web",
            "clientVersion": "curr",
            "param": {
                "cmsArticleWebOld": {
                    "searchScope": "default",
                    "sort": "time",
                    "pageIndex": 1,
                    "pageSize": max(1, min(limit, 30)),
                    "preTag": "",
                    "postTag": "",
                }
            },
        }
        response = await self._get(
            self.eastmoney_stock_news_url,
            {
                "cb": "stockts",
                "param": json.dumps(query, ensure_ascii=False, separators=(",", ":")),
            },
        )
        return self.normalize_stock_news(response.text)[:limit]

    async def fetch_filings(
        self, symbol: str, limit: int = 20
    ) -> list[EvidenceDocument]:
        if not symbol.startswith(("SH.", "SZ.", "BJ.")):
            return []
        return await self.evidence_provider.fetch_filings(symbol, limit)

    async def fetch_research_documents(
        self, symbol: str, limit: int = 20
    ) -> list[EvidenceDocument]:
        if not symbol.startswith(("SH.", "SZ.", "BJ.")):
            return []
        return await self.evidence_provider.fetch_research(symbol, limit)

    async def fetch_themes(
        self, symbol: str, limit: int = 30
    ) -> list[InstrumentTheme]:
        if not symbol.startswith(("SH.", "SZ.", "BJ.")):
            return []
        return await self.evidence_provider.fetch_themes(symbol, limit)

    async def fetch_dragon_tiger(self, limit: int = 20) -> list[TradingAnomaly]:
        return await self.evidence_provider.fetch_dragon_tiger(limit)

    async def fetch_kline(self, symbol: str, limit: int = 180) -> list[Bar]:
        if symbol.startswith(("HK.", "US.")):
            return await self.global_provider.fetch_kline(symbol, limit)
        market, code = symbol.split(".", 1)
        raw = f"{market.lower()}{code}"
        response = await self._get(self.tencent_kline_url, {"param": f"{raw},day,,,{limit},qfq"})
        return self.normalize_kline(response.json(), symbol)

    async def fetch_raw_kline(self, symbol: str, limit: int = 30) -> list[Bar]:
        if not symbol.startswith(("SH.", "SZ.", "BJ.")):
            return []
        market, code = symbol.split(".", 1)
        raw = f"{market.lower()}{code}"
        response = await self._get(self.tencent_kline_url, {"param": f"{raw},day,,,{limit}"})
        return self.normalize_kline(response.json(), symbol)
