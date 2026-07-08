from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from stock_ts.config import get_settings
from stock_ts.models import DailyBar, IndexQuote, MarketRawData, StockRawData
from stock_ts.providers.base import DataProviderError, StockDataProvider


class TushareProvider(StockDataProvider):
    """Tushare Pro adapter for token-backed A-share daily data."""

    def __init__(self, token: str | None = None, pro_client: object | None = None) -> None:
        self._token = (token if token is not None else get_settings().tushare_token).strip()
        if pro_client is not None:
            self._pro = pro_client
            return
        if not self._token:
            raise DataProviderError("Tushare token is missing. Set TUSHARE_TOKEN first.")
        try:
            import tushare as ts  # type: ignore[import-not-found]
        except ImportError as exc:
            raise DataProviderError("Tushare is not installed. Run: pip install tushare") from exc
        self._pro = ts.pro_api(self._token)

    def fetch_market(self) -> MarketRawData:
        index_map = {
            "000001.SH": ("000001", "上证指数"),
            "399001.SZ": ("399001", "深证成指"),
            "399006.SZ": ("399006", "创业板指"),
        }
        indices: list[IndexQuote] = []
        latest_trade_date = "latest"
        for ts_code, (code, name) in index_map.items():
            rows = _records(self._pro.index_daily(ts_code=ts_code, limit=2))
            if not rows:
                continue
            latest = _sort_trade_rows(rows)[-1]
            latest_trade_date = _format_trade_date(str(latest.get("trade_date", latest_trade_date)))
            indices.append(
                IndexQuote(
                    code=code,
                    name=name,
                    close=_float(latest.get("close")),
                    pct_chg=_float(latest.get("pct_chg")),
                    amount=_float(latest.get("amount")) / 100000,
                )
            )
        if not indices:
            raise DataProviderError("Tushare index_daily returned no market rows")
        return MarketRawData(
            trade_date=latest_trade_date,
            indices=indices,
            advancing=0,
            declining=0,
            limit_up=0,
            limit_down=0,
            top_sectors=[],
            northbound_net_inflow=None,
        )

    def fetch_stock(self, code: str) -> StockRawData:
        ts_code = to_tushare_code(code)
        rows = _records(self._pro.daily(ts_code=ts_code, limit=120))
        if not rows:
            raise DataProviderError(f"Tushare daily returned no rows for {ts_code}")
        bars = [
            DailyBar(
                date=_format_trade_date(str(row.get("trade_date", ""))),
                open=_float(row.get("open")),
                high=_float(row.get("high")),
                low=_float(row.get("low")),
                close=_float(row.get("close")),
                volume=_float(row.get("vol")) * 100,
            )
            for row in _sort_trade_rows(rows)[-80:]
        ]
        name = _stock_name(self._pro, ts_code) or ts_code
        return StockRawData(code=ts_code[:6], name=name, bars=bars)


def to_tushare_code(code: str) -> str:
    normalized = code.strip().upper()
    if normalized.endswith((".SH", ".SZ", ".BJ")):
        return normalized
    digits = "".join(ch for ch in normalized if ch.isdigit())
    if len(digits) != 6:
        raise DataProviderError(f"Invalid A-share code for Tushare: {code}")
    if digits.startswith(("6", "9")) and not digits.startswith("920"):
        return f"{digits}.SH"
    if digits.startswith(("920", "8", "4")):
        return f"{digits}.BJ"
    return f"{digits}.SZ"


def _stock_name(pro_client: object, ts_code: str) -> str:
    try:
        rows = _records(pro_client.stock_basic(ts_code=ts_code, fields="ts_code,name"))  # type: ignore[attr-defined]
    except Exception:
        return ""
    for row in rows:
        if str(row.get("ts_code", "")).upper() == ts_code:
            return str(row.get("name", "")).strip()
    return ""


def _records(frame: object) -> list[dict[str, Any]]:
    if frame is None or bool(getattr(frame, "empty", False)):
        return []
    if isinstance(frame, list):
        return [dict(item) for item in frame if isinstance(item, dict)]
    if hasattr(frame, "to_dict"):
        return [dict(item) for item in frame.to_dict("records")]  # type: ignore[call-arg]
    if isinstance(frame, Iterable):
        return [dict(item) for item in frame if isinstance(item, dict)]
    return []


def _sort_trade_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: str(row.get("trade_date", "")))


def _format_trade_date(value: str) -> str:
    digits = "".join(ch for ch in value if ch.isdigit())
    if len(digits) == 8:
        return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"
    return value or "latest"


def _float(value: object) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0
