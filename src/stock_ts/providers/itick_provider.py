from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from stock_ts.models import DailyBar
from stock_ts.providers.base import DataProviderError

ITICK_BASE_URL = "https://api.itick.org"


class ItickClient:
    """Small REST client for iTick quote/K-line enrichment."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = ITICK_BASE_URL,
        session: object | None = None,
        timeout: float = 8.0,
        region_cn: str = "CN",
    ) -> None:
        if not api_key.strip():
            raise DataProviderError("ITICK_API_KEY is missing. Configure it before using iTick.")
        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")
        self.session = session or _requests_session()
        self.timeout = timeout
        self.region_cn = region_cn

    def fetch_daily_bars(self, code: str, *, limit: int = 120) -> list[DailyBar]:
        region, symbol = to_itick_region_code(code, region_cn=self.region_cn)
        payload = self._get(
            "/stock/kline",
            params={"region": region, "code": symbol, "kType": "8"},
        )
        rows = payload.get("data")
        if not isinstance(rows, list):
            return []
        bars = [_bar_from_itick(item) for item in rows if isinstance(item, dict)]
        return [bar for bar in bars if bar.close > 0][-limit:]

    def fetch_tick(self, code: str) -> dict[str, Any]:
        region, symbol = to_itick_region_code(code, region_cn=self.region_cn)
        payload = self._get("/stock/tick", params={"region": region, "code": symbol})
        data = payload.get("data")
        if not isinstance(data, dict):
            return {}
        return {
            "source": "itick.stock_tick",
            "symbol": str(data.get("s") or symbol),
            "latest_price": _optional_float(data.get("ld")),
            "timestamp": _format_timestamp(data.get("t")),
            "volume": _optional_float(data.get("v")),
            "amount": _optional_float(data.get("tu")),
        }

    def _get(self, path: str, *, params: dict[str, object]) -> dict[str, Any]:
        response = self.session.get(  # type: ignore[attr-defined]
            f"{self.base_url}{path}",
            params=params,
            headers={"accept": "application/json", "token": self.api_key},
            timeout=self.timeout,
        )
        if int(getattr(response, "status_code", 0)) != 200:
            raise DataProviderError(
                f"iTick HTTP {getattr(response, 'status_code', 'unknown')}: "
                f"{str(getattr(response, 'text', ''))[:180]}"
            )
        try:
            payload = response.json()
        except Exception as exc:
            raise DataProviderError("iTick returned non-JSON response") from exc
        if not isinstance(payload, dict):
            raise DataProviderError("iTick returned unexpected response payload")
        code = payload.get("code")
        if code not in {0, "0", None}:
            message = payload.get("msg") or payload.get("message") or f"code={code}"
            raise DataProviderError(f"iTick API error: {message}")
        return payload


def to_itick_region_code(code: str, *, region_cn: str = "CN") -> tuple[str, str]:
    normalized = _normalize_code(code)
    if not normalized:
        raise DataProviderError(f"Unsupported iTick stock code: {code}")
    if "." in str(code):
        suffix = str(code).strip().split(".")[-1].upper()
    elif normalized.startswith(("6", "9")):
        suffix = "SH"
    elif normalized.startswith(("8", "4")):
        suffix = "BJ"
    else:
        suffix = "SZ"
    return region_cn, f"{normalized}.{suffix}"


def _bar_from_itick(item: dict[str, Any]) -> DailyBar:
    return DailyBar(
        date=_format_timestamp(item.get("t")),
        open=_float(item.get("o")),
        high=_float(item.get("h")),
        low=_float(item.get("l")),
        close=_float(item.get("c")),
        volume=_float(item.get("v")),
    )


def _format_timestamp(value: object) -> str:
    timestamp = _optional_float(value)
    if timestamp is None:
        return ""
    if timestamp > 10_000_000_000:
        timestamp = timestamp / 1000
    return datetime.fromtimestamp(timestamp, timezone.utc).date().isoformat()


def _normalize_code(code: str) -> str:
    digits = "".join(ch for ch in str(code).strip() if ch.isdigit())
    return digits[:6] if len(digits) >= 6 else ""


def _requests_session() -> object:
    try:
        import requests  # type: ignore[import-not-found]
    except ImportError as exc:
        raise DataProviderError("requests is required for iTick API access") from exc
    return requests.Session()


def _float(value: object) -> float:
    parsed = _optional_float(value)
    return parsed if parsed is not None else 0.0


def _optional_float(value: object) -> float | None:
    if value in {None, ""}:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
