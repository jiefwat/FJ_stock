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
    advancing_ratio: float | None
    amount_change: float
    consecutive_days: int | None
    high_divergence: bool | None


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
class PriceBar:
    date: str
    open: float | None
    high: float | None
    low: float | None
    close: float
    volume: float | None
    pct_change: float | None


@dataclass(frozen=True)
class ValuationSnapshot:
    pe_ttm: float | None
    pb: float | None
    ps: float | None
    total_market_value: float | None


@dataclass(frozen=True)
class FlowSnapshot:
    amount_yuan: float | None
    turnover_rate: float | None
    inside_volume: float | None
    outside_volume: float | None


@dataclass(frozen=True)
class StockProfile:
    code: str
    name: str
    sector: str
    bars: tuple[PriceBar, ...]
    valuation: ValuationSnapshot
    flow: FlowSnapshot
    price_reliable: bool
    data_quality: str
    primary_source: str
    missing_fields: tuple[str, ...]
    events: tuple[NewsItem, ...]


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
    stocks: tuple[StockProfile, ...] = ()
