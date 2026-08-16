from __future__ import annotations

import json
import re
from datetime import date
from typing import Any

import httpx

from marketdesk.models import Bar, EquityQuote
from marketdesk.providers.base import ProviderUnavailable


class GlobalMarketProvider:
    """On-demand Hong Kong and US quote/K-line access.

    This provider deliberately does not provide a full-market universe. It only
    resolves explicit searches/symbols so the rest of StockTs can reuse the
    deterministic A-share analysis pipeline for cross-market holdings.
    """

    tencent_quote_url = "https://qt.gtimg.cn/q={symbols}"
    tencent_search_url = "https://smartbox.gtimg.cn/s3/"
    tencent_hk_kline_url = "https://web.ifzq.gtimg.cn/appstock/app/hkfqkline/get"
    sina_us_kline_url = (
        "https://stock.finance.sina.com.cn/usstock/api/jsonp.php/var%20_/"
        "US_MinKService.getDailyK"
    )

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self.client = client or httpx.AsyncClient(
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0 MarketDesk/0.1"},
            follow_redirects=True,
            trust_env=False,
        )

    @staticmethod
    def normalize_symbol(symbol: str) -> str:
        normalized = symbol.strip().upper()
        if normalized.startswith(("SH.", "SZ.", "BJ.")):
            raise ValueError("HK/US symbol required")
        hk_match = re.fullmatch(r"(?:HK\.)?(\d{1,5})(?:\.HK)?", normalized)
        if hk_match is not None:
            return f"HK.{hk_match.group(1).zfill(5)}"
        us_match = re.fullmatch(r"(?:US\.)?([A-Z][A-Z0-9.-]{0,14})(?:\.(?:US|OQ|N|A|PK|PS))?", normalized)
        if us_match is not None:
            code = us_match.group(1).replace("_", "-")
            if code not in {"SH", "SZ", "BJ", "HK", "US"}:
                return f"US.{code}"
        raise ValueError("HK/US symbol required")

    @staticmethod
    def is_global_symbol(symbol: str) -> bool:
        try:
            GlobalMarketProvider.normalize_symbol(symbol)
        except ValueError:
            return False
        return True

    @staticmethod
    def _tencent_symbol(symbol: str) -> str:
        market, code = GlobalMarketProvider.normalize_symbol(symbol).split(".", 1)
        if market == "HK":
            return f"hk{code}"
        return f"us{code.split('.', 1)[0].replace('-', '').upper()}"

    @staticmethod
    def _canonical_from_tencent(market: str, code: str) -> str | None:
        market = market.lower()
        if market == "hk" and code.isdigit():
            return f"HK.{code.zfill(5)}"
        if market == "us" and code:
            return f"US.{code.split('.', 1)[0].upper()}"
        return None

    @staticmethod
    def _float(value: Any) -> float | None:
        try:
            return None if value in (None, "", "-", "--") else float(value)
        except (TypeError, ValueError):
            return None

    async def _get(self, url: str, params: dict[str, Any] | None = None) -> httpx.Response:
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            return response
        except httpx.HTTPError as error:
            raise ProviderUnavailable(f"global market request failed: {error}") from error

    async def fetch_quote(self, symbol: str, name: str | None = None) -> EquityQuote:
        normalized = self.normalize_symbol(symbol)
        raw_symbol = self._tencent_symbol(normalized)
        response = await self._get(self.tencent_quote_url.format(symbols=raw_symbol))
        return self.normalize_tencent_quote(
            response.content.decode("gb18030", errors="replace"), normalized, fallback_name=name
        )

    async def search(self, query: str, limit: int = 10) -> list[EquityQuote]:
        normalized_query = query.strip()
        if not normalized_query:
            return []
        try:
            return [await self.fetch_quote(self.normalize_symbol(normalized_query))]
        except (ProviderUnavailable, ValueError):
            pass
        response = await self._get(
            self.tencent_search_url,
            {"q": normalized_query, "t": "all"},
        )
        symbols = self.normalize_tencent_search(response.content.decode("gb18030", errors="replace"))[:limit]
        quotes: list[EquityQuote] = []
        for symbol in symbols:
            try:
                quotes.append(await self.fetch_quote(symbol))
            except ProviderUnavailable:
                continue
        return quotes[:limit]

    def normalize_tencent_search(self, text: str) -> list[str]:
        match = re.search(r'v_hint="(.*)"', text, re.S)
        if not match:
            return []
        symbols: list[str] = []
        for row in match.group(1).split("^"):
            parts = row.split("~")
            if len(parts) < 5 or parts[4] != "GP":
                continue
            symbol = self._canonical_from_tencent(parts[0], parts[1])
            if symbol is not None:
                symbols.append(symbol)
        return list(dict.fromkeys(symbols))

    def normalize_tencent_quote(
        self, text: str, symbol: str, fallback_name: str | None = None
    ) -> EquityQuote:
        normalized = self.normalize_symbol(symbol)
        match = re.search(r'v_[a-zA-Z0-9]+="([^"]*)"', text)
        if not match:
            raise ProviderUnavailable(f"empty quote for {normalized}")
        fields = match.group(1).split("~")
        if len(fields) < 35 or not fields[1]:
            raise ProviderUnavailable(f"invalid quote for {normalized}")
        market, code = normalized.split(".", 1)
        price = self._float(fields[3])
        volume = self._float(fields[36] if market == "US" and len(fields) > 36 else fields[36] if len(fields) > 36 else fields[6])
        amount = self._float(fields[37] if len(fields) > 37 else None)
        if amount is None and price is not None and volume is not None:
            amount = price * volume
        name = fallback_name or fields[1] or code
        currency = "港股/HKD" if market == "HK" else "美股/USD"
        return EquityQuote(
            symbol=normalized,
            code=code,
            name=name,
            price=price,
            change_pct=self._float(fields[32] if len(fields) > 32 else None),
            amount=amount,
            turnover_rate=self._float(fields[38] if market == "HK" and len(fields) > 38 else None),
            volume_ratio=None,
            pe=self._float(fields[39] if market == "HK" and len(fields) > 39 else None),
            pb=None,
            market_cap=self._float(fields[44] if market == "HK" and len(fields) > 44 else None),
            net_flow=None,
            sector=currency,
        )

    async def fetch_kline(self, symbol: str, limit: int = 180) -> list[Bar]:
        normalized = self.normalize_symbol(symbol)
        market, code = normalized.split(".", 1)
        if market == "HK":
            response = await self._get(
                self.tencent_hk_kline_url,
                {"param": f"hk{code},day,,,{limit},qfq"},
            )
            return self.normalize_tencent_kline(response.json(), f"hk{code}")[-limit:]
        response = await self._get(self.sina_us_kline_url, {"symbol": code.split(".", 1)[0]})
        return self.normalize_sina_us_kline(response.text)[-limit:]

    def normalize_tencent_kline(self, payload: dict[str, Any], key: str) -> list[Bar]:
        rows = payload.get("data", {}).get(key, {}).get("qfqday") or payload.get("data", {}).get(key, {}).get("day") or []
        bars: list[Bar] = []
        for row in rows:
            if len(row) < 6:
                continue
            close = float(row[2])
            volume = float(row[5])
            amount = self._float(row[8] if len(row) > 8 else None)
            bars.append(
                Bar(
                    date=date.fromisoformat(row[0]),
                    open=float(row[1]),
                    close=close,
                    high=float(row[3]),
                    low=float(row[4]),
                    volume=volume,
                    amount=(amount * 10_000 if amount is not None else close * volume),
                )
            )
        return bars

    def normalize_sina_us_kline(self, text: str) -> list[Bar]:
        match = re.search(r"var _\((.*)\);?", text, re.S)
        if not match:
            raise ProviderUnavailable("invalid Sina US kline payload")
        rows = json.loads(match.group(1))
        if not isinstance(rows, list):
            return []
        bars: list[Bar] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            close = float(row["c"])
            volume = float(row.get("v") or 0)
            amount = self._float(row.get("a"))
            bars.append(
                Bar(
                    date=date.fromisoformat(str(row["d"])),
                    open=float(row["o"]),
                    close=close,
                    high=float(row["h"]),
                    low=float(row["l"]),
                    volume=volume,
                    amount=amount if amount is not None and amount > 0 else close * volume,
                )
            )
        return bars
