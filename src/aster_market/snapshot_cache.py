from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .presenter import build_view
from .snapshot import SnapshotResult, load_snapshot

SnapshotFingerprint = tuple[int, int, int] | None


@dataclass(frozen=True)
class CachedSnapshot:
    fingerprint: SnapshotFingerprint
    result: SnapshotResult
    view: dict[str, Any]


def _fingerprint(path: Path) -> SnapshotFingerprint:
    try:
        stat = path.stat()
    except OSError:
        return None
    return stat.st_ino, stat.st_size, stat.st_mtime_ns


class SnapshotCache:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state: CachedSnapshot | None = None

    def get(self, path: Path) -> CachedSnapshot:
        fingerprint = _fingerprint(path)
        with self._lock:
            if self._state is not None and self._state.fingerprint == fingerprint:
                return self._state

            result = load_snapshot(path)
            view = (
                build_view(result.snapshot)
                if result.snapshot is not None
                else {"status": result.status, "message": result.message}
            )
            self._state = CachedSnapshot(fingerprint, result, view)
            return self._state
