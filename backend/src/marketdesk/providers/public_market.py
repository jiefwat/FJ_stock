from __future__ import annotations

import asyncio
import json
import math
import re
from datetime import UTC, date, datetime, time, timedelta
from typing import Any, cast
from zoneinfo import ZoneInfo

import httpx

from marketdesk.models import (
    Bar,
    DatasetMeta,
    EquityDataset,
    EquityQuote,
    Freshness,
    IndexQuote,
    SectorSnapshot,
)
from marketdesk.providers.base import ProviderUnavailable


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
    tencent_quote_url = (
        "https://qt.gtimg.cn/q=sh000001,sz399001,sz399006,sh000300,sh000016,sh000688"
    )
    tencent_kline_url = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self.client = client or httpx.AsyncClient(
            timeout=12,
            headers={
                "User-Agent": "Mozilla/5.0 MarketDesk/0.1",
                "Referer": "https://finance.sina.com.cn/",
            },
            follow_redirects=True,
        )

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

    @staticmethod
    def _float(value: Any) -> float | None:
        try:
            return None if value in (None, "", "-", "--") else float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _symbol(raw: str) -> str:
        return f"{raw[:2].upper()}.{raw[-6:]}"

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
        return self.normalize_equities([row for page in pages for row in page])

    async def fetch_indices(self) -> list[IndexQuote]:
        response = await self._get(self.tencent_quote_url)
        return self.normalize_indices(response.content.decode("gb18030", errors="replace"))

    async def fetch_sectors(self) -> list[SectorSnapshot]:
        response = await self._get(self.sina_sector_url)
        return self.normalize_sectors(response.content.decode("gb18030", errors="replace"))

    async def fetch_kline(self, symbol: str, limit: int = 180) -> list[Bar]:
        market, code = symbol.split(".", 1)
        raw = f"{market.lower()}{code}"
        response = await self._get(self.tencent_kline_url, {"param": f"{raw},day,,,{limit},qfq"})
        return self.normalize_kline(response.json(), symbol)
