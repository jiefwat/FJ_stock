from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IndexQuote:
    name: str
    code: str
    value: float
    pct_change: float


@dataclass(frozen=True)
class SectorPulse:
    name: str
    pct_change: float
    advancing_ratio: float
    amount_change: float
    consecutive_days: int
    high_divergence: bool


@dataclass(frozen=True)
class Candidate:
    code: str
    name: str
    sector: str
    pct_change: float | None
    latest_price: float
    reason: str
    risk: str


@dataclass(frozen=True)
class NewsItem:
    published_at: str
    source: str
    title: str
    summary: str


@dataclass(frozen=True)
class MarketSnapshot:
    trade_date: str
    generated_at: str
    source: str
    indices: tuple[IndexQuote, ...]
    advancing: int
    declining: int
    limit_up: int
    limit_down: int
    northbound_net_inflow: float | None
    sectors: tuple[SectorPulse, ...]
    candidates: tuple[Candidate, ...]
    news: tuple[NewsItem, ...]
