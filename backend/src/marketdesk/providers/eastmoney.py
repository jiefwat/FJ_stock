from __future__ import annotations

import asyncio
import math
from datetime import UTC, date, datetime
from typing import Any, cast

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


def _number(value: Any) -> float | None:
    if value in (None, "", "-", "--"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _symbol(code: str) -> str:
    market = "SH" if code.startswith(("5", "6", "9")) else "SZ"
    return f"{market}.{code}"


def _index_symbol(code: str) -> str:
    return f"{'SH' if code in {'000001', '000016', '000300', '000688'} else 'SZ'}.{code}"


class EastmoneyProvider:
    base_url = "https://82.push2.eastmoney.com/api/qt/clist/get"
    quote_url = "https://push2.eastmoney.com/api/qt/stock/get"
    index_url = "https://push2.eastmoney.com/api/qt/ulist.np/get"
    kline_url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self.client = client or httpx.AsyncClient(
            timeout=10,
            headers={"User-Agent": "MarketDesk/0.1 local-research"},
            follow_redirects=True,
        )

    async def _get_json(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = await self.client.get(url, params=params)
                response.raise_for_status()
                return cast(dict[str, Any], response.json())
            except (httpx.HTTPError, ValueError) as error:
                last_error = error
                if attempt < 2:
                    await asyncio.sleep(0.15 * (attempt + 1))
        raise ProviderUnavailable(f"eastmoney request failed: {last_error}") from last_error

    def normalize_equities(self, payload: dict[str, Any]) -> EquityDataset:
        rows = (payload.get("data") or {}).get("diff") or []
        if not isinstance(rows, list) or not rows:
            raise ProviderUnavailable("empty A-share universe")
        items: list[EquityQuote] = []
        present = 0
        required = 0
        for row in rows:
            code = str(row.get("f12") or "")
            if not code:
                continue
            values: dict[str, Any] = {
                "price": _number(row.get("f2")),
                "change_pct": _number(row.get("f3")),
                "amount": _number(row.get("f6")),
                "turnover_rate": _number(row.get("f8")),
                "pe": _number(row.get("f9")),
                "volume_ratio": _number(row.get("f10")),
                "market_cap": _number(row.get("f20")),
                "pb": _number(row.get("f23")),
                "net_flow": _number(row.get("f62")),
            }
            required += len(values)
            present += sum(value is not None for value in values.values())
            items.append(
                EquityQuote(
                    symbol=_symbol(code), code=code, name=str(row.get("f14") or code), **values
                )
            )
        now = datetime.now(UTC)
        coverage = present / required if required else 0
        return EquityDataset(
            meta=DatasetMeta(
                source="eastmoney",
                observed_at=now,
                fetched_at=now,
                freshness=Freshness.FRESH,
                coverage=coverage,
            ),
            items=items,
        )

    def normalize_indices(self, payload: dict[str, Any]) -> list[IndexQuote]:
        rows = (payload.get("data") or {}).get("diff") or []
        return [
            IndexQuote(
                symbol=_index_symbol(str(row.get("f12") or "")),
                name=str(row.get("f14") or ""),
                price=_number(row.get("f2")),
                change_pct=_number(row.get("f3")),
                amount=_number(row.get("f6")),
            )
            for row in rows
            if row.get("f12")
        ]

    def normalize_sectors(self, payload: dict[str, Any]) -> list[SectorSnapshot]:
        rows = (payload.get("data") or {}).get("diff") or []
        return [
            SectorSnapshot(
                code=str(row.get("f12") or ""),
                name=str(row.get("f14") or ""),
                change_pct=_number(row.get("f3")),
                net_flow=_number(row.get("f62")),
            )
            for row in rows
            if row.get("f12")
        ]

    def normalize_kline(self, payload: dict[str, Any]) -> list[Bar]:
        lines = (payload.get("data") or {}).get("klines") or []
        bars: list[Bar] = []
        for line in lines:
            parts = str(line).split(",")
            if len(parts) < 7:
                continue
            bars.append(
                Bar(
                    date=date.fromisoformat(parts[0]),
                    open=float(parts[1]),
                    close=float(parts[2]),
                    high=float(parts[3]),
                    low=float(parts[4]),
                    volume=float(parts[5]),
                    amount=float(parts[6]),
                )
            )
        return sorted(bars, key=lambda item: item.date)

    async def fetch_equities(self) -> EquityDataset:
        params = {
            "pn": 1,
            "pz": 100,
            "po": 1,
            "np": 1,
            "fltt": 2,
            "invt": 2,
            "fid": "f3",
            "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",
            "fields": "f12,f14,f2,f3,f6,f8,f9,f10,f20,f23,f62",
        }
        first_payload = await self._get_json(self.base_url, params)
        first_data = first_payload.get("data") or {}
        rows = list(first_data.get("diff") or [])
        total = int(first_data.get("total") or len(rows))
        page_size = max(1, len(rows))
        page_count = math.ceil(total / page_size)
        semaphore = asyncio.Semaphore(3)

        async def fetch_page(page: int) -> list[dict[str, Any]]:
            async with semaphore:
                payload = await self._get_json(self.base_url, {**params, "pn": page})
                return list((payload.get("data") or {}).get("diff") or [])

        if page_count > 1:
            pages = await asyncio.gather(*(fetch_page(page) for page in range(2, page_count + 1)))
            for page_rows in pages:
                rows.extend(page_rows)
        return self.normalize_equities({"data": {"diff": rows}})

    async def fetch_indices(self) -> list[IndexQuote]:
        params = {
            "secids": "1.000001,0.399001,0.399006,1.000300,1.000016,1.000688",
            "fltt": 2,
            "fields": "f12,f14,f2,f3,f6",
        }
        return self.normalize_indices(await self._get_json(self.index_url, params))

    async def fetch_sectors(self) -> list[SectorSnapshot]:
        params = {
            "pn": 1,
            "pz": 40,
            "po": 1,
            "np": 1,
            "fltt": 2,
            "fid": "f3",
            "fs": "m:90+t:2+f:!50",
            "fields": "f12,f14,f3,f62",
        }
        return self.normalize_sectors(await self._get_json(self.base_url, params))

    async def fetch_kline(self, symbol: str, limit: int = 180) -> list[Bar]:
        market, code = symbol.split(".", 1)
        secid = f"{1 if market == 'SH' else 0}.{code}"
        params = {
            "secid": secid,
            "klt": 101,
            "fqt": 1,
            "lmt": limit,
            "end": 20500101,
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        }
        return self.normalize_kline(await self._get_json(self.kline_url, params))
