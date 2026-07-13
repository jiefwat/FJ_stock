from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PortfolioVerdict:
    state: str
    action: str
    risk_budget: str
    confidence: int
    thesis: str
    primary_risk: str
    next_review: str


@dataclass(frozen=True)
class PortfolioMetric:
    label: str
    value: str
    status: str
    note: str


@dataclass(frozen=True)
class PortfolioQueueItem:
    priority: int
    state: str
    code: str
    name: str
    current_weight: float
    cost_context: str
    reason: str
    trigger: str
    invalidation: str


@dataclass(frozen=True)
class PortfolioExposure:
    name: str
    weight: float
    severity: str
    consequence: str


@dataclass(frozen=True)
class PortfolioBoundary:
    code: str
    name: str
    current_action: str
    target_range: str
    reduce_trigger: str
    invalidation: str
    prohibited_action: str


@dataclass(frozen=True)
class PortfolioDossier:
    verdict: PortfolioVerdict
    metrics: tuple[PortfolioMetric, ...]
    queue: tuple[PortfolioQueueItem, ...]
    exposures: tuple[PortfolioExposure, ...]
    boundaries: tuple[PortfolioBoundary, ...]
