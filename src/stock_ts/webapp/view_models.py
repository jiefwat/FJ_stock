from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WorkspaceMeta:
    key: str
    label: str
    badge: str
    description: str
