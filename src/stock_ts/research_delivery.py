from __future__ import annotations

from typing import Any

from .research_engine import ResearchContext
from .research_snapshots import GLOBAL_SNAPSHOT_MODULES, ResearchSnapshotStore


def deliver_research(
    service: Any,
    store: ResearchSnapshotStore,
    module: str,
    context: ResearchContext,
    *,
    refresh: bool = False,
) -> dict[str, object]:
    normalized = module.strip().lower()
    is_global = normalized in GLOBAL_SNAPSHOT_MODULES
    if is_global and not refresh:
        fresh = store.load(normalized)
        if fresh is not None:
            return _with_delivery(fresh.payload, "snapshot", stale=False)

    result = service.research(normalized, context, refresh=refresh)
    payload = result.to_public_dict()
    if result.ok:
        delivered = _with_delivery(payload, "live", stale=False)
        if is_global:
            store.save(normalized, delivered)
        return delivered

    if is_global:
        stale = store.load(normalized, allow_stale=True)
        if stale is not None:
            return _with_delivery(stale.payload, "stale_snapshot", stale=True)
    return _with_delivery(payload, "live", stale=False)


def _with_delivery(
    payload: dict[str, object],
    delivery: str,
    *,
    stale: bool,
) -> dict[str, object]:
    result = dict(payload)
    result["delivery"] = delivery
    result["stale"] = stale
    return result
