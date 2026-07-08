from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CacheEntry:
    payload: dict[str, Any]
    metadata: dict[str, str]


class JsonCacheStore:
    """Small dependency-free cache for snapshots and smoke workflows."""

    def __init__(self, root: str | Path = "data/cache") -> None:
        self.root = Path(root)

    def write_json(
        self,
        key: str,
        payload: dict[str, Any],
        *,
        source: str,
        trade_date: str,
    ) -> Path:
        path = self._path_for(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        document = {
            "metadata": {
                "source": source,
                "trade_date": trade_date,
                "cached_at": datetime.now(timezone.utc).isoformat(),
            },
            "payload": payload,
        }
        path.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def read_json(self, key: str) -> CacheEntry | None:
        path = self._path_for(key)
        if not path.exists():
            return None
        document = json.loads(path.read_text(encoding="utf-8"))
        return CacheEntry(
            payload=document.get("payload", {}),
            metadata=document.get("metadata", {}),
        )

    def _path_for(self, key: str) -> Path:
        safe_parts = [part for part in key.strip("/").split("/") if part]
        if not safe_parts:
            raise ValueError("cache key cannot be empty")
        return self.root.joinpath(*safe_parts).with_suffix(".json")
