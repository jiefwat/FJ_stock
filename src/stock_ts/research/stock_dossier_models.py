from __future__ import annotations

from dataclasses import dataclass

from .evidence import EvidenceItem


@dataclass(frozen=True)
class DossierVerdict:
    stance: str
    action: str
    evidence_grade: str
    confidence: int
    horizon: str
    thesis: str
    strongest_evidence: str
    strongest_counter_evidence: str
    next_review: str


@dataclass(frozen=True)
class DecisionStep:
    label: str
    state: str
    condition: str
    consequence: str


@dataclass(frozen=True)
class DiagnosticBlock:
    name: str
    status: str
    conclusion: str
    facts: tuple[str, ...]
    risks: tuple[str, ...]
    limitation: str


@dataclass(frozen=True)
class RiskItem:
    severity: str
    category: str
    evidence: str
    consequence: str
    monitor: str


@dataclass(frozen=True)
class PositionGuidance:
    audience: str
    current_action: str
    position_cap: str
    risk_budget: str
    entry_trigger: str
    add_trigger: str
    reduce_trigger: str
    invalidation: str
    prohibited_action: str


@dataclass(frozen=True)
class DossierScenario:
    name: str
    premise: str
    confirmation: str
    action: str
    invalidation: str
    evidence_source: str


@dataclass(frozen=True)
class ThesisFramework:
    headline: str
    core_conflict: str
    causal_chain: tuple[str, str, str]
    expectation_gap: str
    valuation_fit: str
    catalyst_window: str
    key_unknown: str
    falsifier: str


@dataclass(frozen=True)
class WeightedEvidence:
    dimension: str
    importance: str
    direction: str
    fact: str
    inference: str
    unknown: str


@dataclass(frozen=True)
class ProfessionalStockDossier:
    code: str
    name: str
    trade_date: str
    latest_close: float
    verdict: DossierVerdict
    decision_steps: tuple[DecisionStep, ...]
    diagnostics: tuple[DiagnosticBlock, ...]
    risks: tuple[RiskItem, ...]
    position: PositionGuidance
    scenarios: tuple[DossierScenario, ...]
    evidence: tuple[EvidenceItem, ...]
    thesis: ThesisFramework
    weighted_evidence: tuple[WeightedEvidence, ...]
