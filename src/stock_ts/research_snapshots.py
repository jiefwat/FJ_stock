from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

GLOBAL_SNAPSHOT_MODULES = {"market", "opportunity"}


@dataclass(frozen=True)
class SnapshotRead:
    payload: dict[str, object]
    age_hours: float
    stale: bool


class ResearchSnapshotStore:
    def __init__(
        self,
        root: str | Path,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.root = Path(root)
        self.clock = clock or (lambda: datetime.now(timezone(timedelta(hours=8))))

    def save(self, module: str, payload: Mapping[str, Any]) -> None:
        normalized = self._validate_module(module)
        generated = _payload_datetime(payload) or self.clock()
        directory = self.root / normalized
        directory.mkdir(parents=True, exist_ok=True)
        serialized = json.dumps(
            dict(payload),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        self._atomic_write(directory / "latest.json", serialized)
        self._atomic_write(directory / f"{generated.date().isoformat()}.json", serialized)

    def load(
        self,
        module: str,
        *,
        max_age_hours: float = 18,
        allow_stale: bool = False,
    ) -> SnapshotRead | None:
        normalized = self._validate_module(module)
        path = self.root / normalized / "latest.json"
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(payload, dict):
            return None
        generated = _payload_datetime(payload)
        if generated is None:
            return None
        now = self.clock()
        age_hours = max((now - generated.astimezone(now.tzinfo)).total_seconds() / 3600, 0)
        stale = age_hours > max_age_hours
        if stale and not allow_stale:
            return None
        return SnapshotRead(payload=payload, age_hours=age_hours, stale=stale)

    @staticmethod
    def _validate_module(module: str) -> str:
        normalized = module.strip().lower()
        if normalized not in GLOBAL_SNAPSHOT_MODULES:
            raise ValueError("只允许保存大盘和机会快照。")
        return normalized

    @staticmethod
    def _atomic_write(path: Path, content: str) -> None:
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(path)


def _payload_datetime(payload: Mapping[str, Any]) -> datetime | None:
    value = str(payload.get("generated_at") or payload.get("as_of") or "")
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone(timedelta(hours=8)))
    return parsed
