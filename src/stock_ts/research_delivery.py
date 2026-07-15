from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .research_engine import ResearchContext, ResearchWorkspaceResult
from .research_snapshots import GLOBAL_SNAPSHOT_MODULES, ResearchSnapshotStore

Fallback = Callable[[str, ResearchContext], ResearchWorkspaceResult]


def deliver_research(
    service: Any,
    store: ResearchSnapshotStore,
    module: str,
    context: ResearchContext,
    *,
    refresh: bool = False,
    fallback: Fallback | None = None,
) -> dict[str, object]:
    normalized = module.strip().lower()
    is_global = normalized in GLOBAL_SNAPSHOT_MODULES
    if is_global and not refresh:
        fresh = store.load(normalized)
        if fresh is not None:
            return _with_delivery(fresh.payload, "snapshot", stale=False)

    try:
        result = service.research(normalized, context, refresh=refresh)
    except Exception:
        if is_global:
            stale = store.load(normalized, allow_stale=True)
            if stale is not None:
                return _with_delivery(stale.payload, "stale_snapshot", stale=True)
        local = _local_payload(fallback, normalized, context)
        if local is not None:
            return local
        raise
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
    local = _local_payload(fallback, normalized, context)
    if local is not None:
        return local
    return _with_delivery(payload, "live", stale=False)


def _local_payload(
    fallback: Fallback | None,
    module: str,
    context: ResearchContext,
) -> dict[str, object] | None:
    if fallback is None:
        return None
    payload = fallback(module, context).to_public_dict()
    return _with_delivery(payload, "local_fallback", stale=False)


def _with_delivery(
    payload: dict[str, object],
    delivery: str,
    *,
    stale: bool,
) -> dict[str, object]:
    result = dict(payload)
    result["delivery"] = delivery
    result["data_label"] = {
        "live": "实时研究",
        "snapshot": "当日快照",
        "stale_snapshot": "历史参考",
        "local_fallback": "本地证据",
        "unavailable": "数据缺失",
    }.get(delivery, str(result.get("data_label") or ""))
    result["stale"] = stale
    return result
