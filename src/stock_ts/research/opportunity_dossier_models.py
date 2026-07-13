from __future__ import annotations

from dataclasses import dataclass

from .evidence import EvidenceStatus


@dataclass(frozen=True)
class OpportunityGate:
    state: str
    action: str
    risk_budget: str
    data_status: str
    scanned_count: int | None
    evidence_ready_count: int
    eligible_count: int
    thesis: str
    next_step: str


@dataclass(frozen=True)
class FunnelStage:
    name: str
    count: int
    status: str
    note: str


@dataclass(frozen=True)
class CandidateDecision:
    code: str
    name: str
    sector: str
    state: str
    strategy: str
    evidence: tuple[str, ...]
    counter_evidence: tuple[str, ...]
    data_date: str
    data_status: EvidenceStatus
    next_verification: str
    exclusion_reason: str


@dataclass(frozen=True)
class OpportunityRisk:
    category: str
    severity: str
    evidence: str
    consequence: str


@dataclass(frozen=True)
class OpportunityDossier:
    gate: OpportunityGate
    funnel: tuple[FunnelStage, ...]
    candidates: tuple[CandidateDecision, ...]
    risks: tuple[OpportunityRisk, ...]
    source_notes: tuple[str, ...]
