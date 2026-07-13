from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DataReadinessGate:
    state: str
    action: str
    thesis: str
    blocked_count: int
    warning_count: int
    ready_count: int
    total_count: int
    next_step: str


@dataclass(frozen=True)
class DataRecoveryStep:
    priority: int
    category: str
    status: str
    severity: str
    issue: str
    consequence: str
    verification: str


@dataclass(frozen=True)
class DataImpactLane:
    key: str
    label: str
    status: str
    affected_domains: tuple[str, ...]
    guidance: str


@dataclass(frozen=True)
class DataLedgerEntry:
    category: str
    channel: str
    status: str
    latest_at: str
    coverage: str
    missing: str
    impact: str
    level: str


@dataclass(frozen=True)
class DataCenterDossier:
    gate: DataReadinessGate
    recovery_steps: tuple[DataRecoveryStep, ...]
    impacts: tuple[DataImpactLane, ...]
    ledger: tuple[DataLedgerEntry, ...]
    updated_at: str
