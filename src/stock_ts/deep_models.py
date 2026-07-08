from __future__ import annotations

from dataclasses import dataclass

from .models import (
    CandidatePoolReport,
    MarketSnapshot,
    NewsSentimentReport,
    PortfolioAnalysisReport,
    SectorAnalysisReport,
)
from .report import DISCLAIMER


@dataclass(frozen=True)
class AnalysisAngle:
    name: str
    score: int
    stance: str
    evidence: str


@dataclass(frozen=True)
class UpsidePotential:
    score: int
    label: str
    base_case: str
    bull_case: str
    bear_case: str
    drivers: list[str]
    invalid_conditions: list[str]


@dataclass(frozen=True)
class DebateRound:
    role: str
    thesis: str
    evidence: list[str]
    rebuttal: str


@dataclass(frozen=True)
class DeepStockReport:
    code: str
    name: str
    trade_date: str
    latest_close: float
    trend: str
    risk_level: str
    angles: list[AnalysisAngle]
    upside: UpsidePotential
    debate_rounds: list[DebateRound]
    final_conclusion: str
    action_plan: list[str]
    risks: list[str]
    invalid_conditions: list[str]
    disclaimer: str = DISCLAIMER


@dataclass(frozen=True)
class BatchAnalysisReport:
    trade_date: str
    stocks: list[DeepStockReport]
    market_summary: str
    sector_mainline: list[str]
    comparison_notes: list[str]
    disclaimer: str = DISCLAIMER


@dataclass(frozen=True)
class DailyDeepReport:
    trade_date: str
    market: MarketSnapshot
    sectors: SectorAnalysisReport
    candidates: CandidatePoolReport
    stocks: list[DeepStockReport]
    portfolio: PortfolioAnalysisReport | None
    news: NewsSentimentReport | None
    markdown: str
    disclaimer: str = DISCLAIMER
