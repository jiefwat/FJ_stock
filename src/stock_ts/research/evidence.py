from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import Enum


class EvidenceStatus(str, Enum):
    COMPLETE = "complete"
    DEGRADED = "degraded"
    MISSING = "missing"
    STALE = "stale"
    BLOCKED = "blocked"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class EvidenceItem:
    block: str
    source: str
    as_of: str
    status: EvidenceStatus
    detail: str


FUNDAMENTAL_QUALITY_FIELDS = (
    "revenue_yoy",
    "net_profit_yoy",
    "roe",
    "gross_margin",
    "debt_to_assets",
    "ocf_to_profit",
)


@dataclass(frozen=True)
class ResearchInputQuality:
    quote_status: EvidenceStatus = EvidenceStatus.COMPLETE
    fundamental_coverage: float = 0.0
    valuation_comparable: bool = False
    event_status: EvidenceStatus = EvidenceStatus.MISSING
    blockers: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()


def audit_status(items: list[EvidenceItem], *, required: set[str]) -> EvidenceStatus:
    by_block = {item.block: item for item in items}
    blocked = {EvidenceStatus.MISSING, EvidenceStatus.STALE, EvidenceStatus.BLOCKED}
    if any(block not in by_block or by_block[block].status in blocked for block in required):
        return EvidenceStatus.BLOCKED
    if any(item.status != EvidenceStatus.COMPLETE for item in items):
        return EvidenceStatus.DEGRADED
    return EvidenceStatus.COMPLETE


def fundamental_metric_coverage(metrics: Mapping[str, object]) -> float:
    available = sum(
        _finite_number(metrics.get(key)) is not None for key in FUNDAMENTAL_QUALITY_FIELDS
    )
    return available / len(FUNDAMENTAL_QUALITY_FIELDS)


def has_comparable_valuation(
    valuation: Mapping[str, object], *, pe_ttm: object = None
) -> bool:
    percentile = _finite_number(valuation.get("pe_percentile"))
    if percentile is not None and 0 <= percentile <= 100:
        return True
    pe = _finite_number(pe_ttm if pe_ttm is not None else valuation.get("pe_ttm"))
    median = _finite_number(valuation.get("industry_pe_median"))
    return pe is not None and pe > 0 and median is not None and median > 0


def has_usable_events(
    announcements: Iterable[Mapping[str, object]], news_items: Iterable[object]
) -> bool:
    if any(str(item.get("title") or "").strip() for item in announcements):
        return True
    return any(str(getattr(item, "title", "") or "").strip() for item in news_items)


def _finite_number(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None
