from __future__ import annotations

import json
import math
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
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
        freshness_at = _payload_freshness_datetime(payload)
        if freshness_at is None:
            return None
        now = self.clock()
        if _payload_freshness_is_date_only(payload):
            current_date = now.astimezone(freshness_at.tzinfo).date()
            workday_gap = _workday_gap(freshness_at.date(), current_date)
            age_hours = float(workday_gap * 24)
            allowed_workdays = max(1, math.ceil(max_age_hours / 24))
            stale = workday_gap > allowed_workdays
        else:
            age_hours = max(
                (now - freshness_at.astimezone(now.tzinfo)).total_seconds() / 3600,
                0,
            )
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
        temporary_path: Path | None = None
        try:
            with NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=path.parent,
                prefix=f".{path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary.write(content)
                temporary.flush()
                os.fsync(temporary.fileno())
                temporary_path = Path(temporary.name)
            temporary_path.replace(path)
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)


def _payload_datetime(payload: Mapping[str, Any]) -> datetime | None:
    value = str(payload.get("generated_at") or payload.get("as_of") or "")
    return _parse_datetime(value)


def _payload_freshness_datetime(payload: Mapping[str, Any]) -> datetime | None:
    as_of = str(payload.get("as_of") or "")
    if as_of:
        return _parse_datetime(as_of)
    return _parse_datetime(str(payload.get("generated_at") or ""))


def _payload_freshness_is_date_only(payload: Mapping[str, Any]) -> bool:
    as_of = str(payload.get("as_of") or "")
    if as_of:
        return _is_date_only(as_of)
    return _is_date_only(str(payload.get("generated_at") or ""))


def _is_date_only(value: str) -> bool:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return False
    return value == parsed.date().isoformat()


def _workday_gap(start_date, end_date) -> int:
    if end_date <= start_date:
        return 0
    return sum(
        (start_date + timedelta(days=offset)).weekday() < 5
        for offset in range(1, (end_date - start_date).days + 1)
    )


def _parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone(timedelta(hours=8)))
    return parsed
