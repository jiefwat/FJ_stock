from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class EvidenceStatus(StrEnum):
    COMPLETE = "complete"
    DEGRADED = "degraded"
    MISSING = "missing"
    STALE = "stale"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class EvidenceItem:
    block: str
    source: str
    as_of: str
    status: EvidenceStatus
    detail: str


def audit_status(items: list[EvidenceItem], *, required: set[str]) -> EvidenceStatus:
    by_block = {item.block: item for item in items}
    blocked = {EvidenceStatus.MISSING, EvidenceStatus.STALE, EvidenceStatus.BLOCKED}
    if any(block not in by_block or by_block[block].status in blocked for block in required):
        return EvidenceStatus.BLOCKED
    if any(item.status != EvidenceStatus.COMPLETE for item in items):
        return EvidenceStatus.DEGRADED
    return EvidenceStatus.COMPLETE
