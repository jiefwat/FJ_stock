from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Callable

QuoteFetcher = Callable[[str], "RealtimeQuote"]


class QuoteFetchError(RuntimeError):
    pass


@dataclass(frozen=True)
class RealtimeQuote:
    code: str
    name: str
    source: str
    price: float | None
    change_pct: float | None
    fetched_at: str = ""
    provider_timestamp: str = ""
    market: str = "cn"
    currency: str = "CNY"
    fallback_from: list[str] = field(default_factory=list)
    data_quality: str = "good"
    missing_fields: list[str] = field(default_factory=list)
    is_stale: bool = False
    stale_seconds: int = 0
    volume: float | None = None
    amount: float | None = None
    turnover_rate: float | None = None
    open: float | None = None
    high: float | None = None
    low: float | None = None
    pre_close: float | None = None


def fetch_realtime_quote(code: str, fetchers: list[tuple[str, QuoteFetcher]]) -> RealtimeQuote:
    failed: list[str] = []
    last_error = ""
    for source, fetcher in fetchers:
        try:
            quote = fetcher(code)
        except Exception as exc:
            failed.append(source)
            last_error = str(exc)
            continue
        missing = _missing_quote_fields(quote)
        quality = _quality(missing=missing, failed=failed, is_stale=quote.is_stale)
        return replace(
            quote,
            fallback_from=failed,
            data_quality=quality,
            missing_fields=missing,
            fetched_at=quote.fetched_at or datetime.now(timezone.utc).isoformat(),
        )
    raise QuoteFetchError(f"all realtime quote sources failed for {code}: {last_error}")


def _missing_quote_fields(quote: RealtimeQuote) -> list[str]:
    missing: list[str] = []
    if quote.price is None:
        missing.append("price")
    if quote.change_pct is None:
        missing.append("change_pct")
    return missing


def _quality(*, missing: list[str], failed: list[str], is_stale: bool) -> str:
    if is_stale:
        return "stale"
    if len(missing) >= 2:
        return "poor"
    if missing or failed:
        return "partial"
    return "good"
