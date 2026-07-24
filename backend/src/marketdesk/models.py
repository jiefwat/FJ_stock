from datetime import date, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Freshness(StrEnum):
    FRESH = "fresh"
    DELAYED = "delayed"
    STALE = "stale"
    UNAVAILABLE = "unavailable"


class DatasetMeta(StrictModel):
    source: str
    observed_at: datetime
    fetched_at: datetime
    freshness: Freshness
    coverage: float = Field(ge=0, le=1)
    errors: list[str] = Field(default_factory=list)

    @field_validator("observed_at", "fetched_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must be timezone-aware")
        return value


class IndexQuote(StrictModel):
    symbol: str
    name: str
    price: float | None = None
    change_pct: float | None = None
    amount: float | None = None


class EquityQuote(StrictModel):
    symbol: str
    code: str
    name: str
    price: float | None = None
    change_pct: float | None = None
    amount: float | None = None
    turnover_rate: float | None = None
    volume_ratio: float | None = None
    pe: float | None = None
    pb: float | None = None
    market_cap: float | None = None
    net_flow: float | None = None
    sector: str | None = None


class SectorSnapshot(StrictModel):
    code: str
    name: str
    change_pct: float | None = None
    net_flow: float | None = None


class SectorDossier(StrictModel):
    sector: SectorSnapshot
    summary: list[str]
    evidence_coverage: float = Field(ge=0, le=1)
    missing_evidence: list[str]
    constituents: list[EquityQuote]


class EquityDataset(StrictModel):
    meta: DatasetMeta
    items: list[EquityQuote]


class EquityPage(StrictModel):
    meta: DatasetMeta
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=50)
    exchange: Literal["all", "sh", "sz", "bj"]
    sort_by: Literal["amount", "change_pct", "turnover_rate", "market_cap"]
    direction: Literal["asc", "desc"]
    items: list[EquityQuote]


class MarketSnapshot(StrictModel):
    meta: DatasetMeta
    indices: list[IndexQuote]
    equities: list[EquityQuote]
    sectors: list[SectorSnapshot]


class MarketFactor(StrictModel):
    key: str
    label: str
    score: float | None
    weight: float
    available: bool
    evidence: str


class MarketAnalysis(StrictModel):
    score: float
    regime: str
    confidence: float
    factors: list[MarketFactor]
    advancing: int
    declining: int
    unchanged: int


class MarketSummarySnapshot(StrictModel):
    meta: DatasetMeta
    indices: list[IndexQuote]
    sectors: list[SectorSnapshot]


class MarketPayload(StrictModel):
    snapshot: MarketSummarySnapshot
    analysis: MarketAnalysis


class MarketEventRaw(StrictModel):
    id: str
    title: str
    summary: str
    source: str
    url: str | None = None
    published_at: datetime
    related_symbols: list[str] = Field(default_factory=list)
    related_sectors: list[str] = Field(default_factory=list)

    @field_validator("published_at")
    @classmethod
    def require_event_timezone(cls, value: datetime) -> datetime:
        return DatasetMeta.require_timezone(value)


class MarketEvent(StrictModel):
    id: str
    title: str
    summary: str
    source: str
    url: str | None = None
    published_at: datetime
    related_symbols: list[str] = Field(default_factory=list)
    related_sectors: list[str] = Field(default_factory=list)
    category: str
    sentiment: str
    importance_score: float = Field(ge=0, le=100)
    tags: list[str] = Field(default_factory=list)
    impact: str
    action: str

    @field_validator("published_at")
    @classmethod
    def require_classified_event_timezone(cls, value: datetime) -> datetime:
        return DatasetMeta.require_timezone(value)


class MarketEventCluster(StrictModel):
    key: str
    label: str
    signal: str
    count: int
    summary: str
    hot_score: float = Field(ge=0, le=100)


class MarketEventResult(StrictModel):
    meta: DatasetMeta
    summary: list[str]
    next_actions: list[str]
    clusters: list[MarketEventCluster]
    events: list[MarketEvent]


class ScoreComponent(StrictModel):
    key: str
    label: str
    raw_value: float | None
    score: float
    weight: float
    weighted_score: float


class OpportunityDimension(StrictModel):
    key: str
    label: str
    signal: str
    score: float | None = Field(default=None, ge=0, le=100)
    summary: str
    evidence: list[str] = Field(default_factory=list)
    available: bool = True


class RankedCandidate(StrictModel):
    quote: EquityQuote
    base_score: float
    context_penalty: float
    score: float
    evidence_coverage: float = Field(ge=0, le=1)
    components: list[ScoreComponent]
    dimensions: list[OpportunityDimension] = Field(default_factory=list)
    thesis: str = ""
    invalidation: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)


class ExcludedCandidate(StrictModel):
    quote: EquityQuote
    reasons: list[str]


class OpportunityResult(StrictModel):
    preset: str
    available: bool
    unavailable_reason: str | None = None
    summary: str = ""
    rules: list[str]
    diagnostics: list[OpportunityDimension] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    funnel: dict[str, int]
    candidates: list[RankedCandidate]
    excluded: list[ExcludedCandidate]


class Bar(StrictModel):
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float


class TechnicalSummary(StrictModel):
    ma5: float | None
    ma20: float | None
    ma60: float | None
    rsi14: float | None
    volatility20: float | None
    support: float | None
    resistance: float | None


class StockScoreFactor(StrictModel):
    key: str
    label: str
    impact: float
    signal: str
    evidence: str
    available: bool


class StockAnalysisDimension(StrictModel):
    key: str
    label: str
    signal: str
    score: float | None = Field(default=None, ge=0, le=100)
    summary: str
    evidence: list[str] = Field(default_factory=list)
    available: bool = True


class StockInvestmentAdvice(StrictModel):
    action: str
    position_hint: str
    entry_plan: str
    stop_loss: str
    take_profit: str
    time_horizon: str
    confidence: float = Field(ge=0, le=1)
    rationale: list[str] = Field(default_factory=list)
    disclaimer: str


class StockTrendForecast(StrictModel):
    horizon: str
    direction: str
    confidence: float = Field(ge=0, le=1)
    summary: str
    drivers: list[str] = Field(default_factory=list)
    invalidation: str


class StockComparisonItem(StrictModel):
    key: str
    label: str
    signal: str
    value: str
    benchmark: str
    summary: str
    percentile: float | None = Field(default=None, ge=0, le=100)
    available: bool = True


class StockDossier(StrictModel):
    quote: EquityQuote
    stance: str
    stance_score: float | None
    conclusion: str
    evidence_coverage: float = Field(ge=0, le=1)
    score_factors: list[StockScoreFactor]
    analysis_dimensions: list[StockAnalysisDimension] = Field(default_factory=list)
    investment_advice: StockInvestmentAdvice
    trend_forecast: StockTrendForecast
    horizontal_comparison: list[StockComparisonItem] = Field(default_factory=list)
    vertical_comparison: list[StockComparisonItem] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    research_evidence: list[str] = Field(default_factory=list)
    technical: TechnicalSummary | None
    bull_case: list[str]
    bear_case: list[str]
    invalidation: list[str]
    missing_evidence: list[str]
    bars: list[Bar]


class HoldingItem(StrictModel):
    id: int
    symbol: str
    name: str
    quantity: float
    cost_price: float
    target_weight: float = Field(ge=0, le=1)
    thesis: str
    invalidation: str
    status: str
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at")
    @classmethod
    def require_holding_timezone(cls, value: datetime) -> datetime:
        return DatasetMeta.require_timezone(value)


class HoldingAnalysisDimension(StrictModel):
    key: str
    label: str
    signal: str
    summary: str
    evidence: list[str] = Field(default_factory=list)


class HoldingDossier(StrictModel):
    item: HoldingItem
    quote: EquityQuote
    market_value: float | None
    cost_value: float
    pnl: float | None
    pnl_pct: float | None
    day_pnl: float | None = None
    day_pnl_pct: float | None = None
    five_day_pnl: float | None = None
    five_day_pnl_pct: float | None = None
    portfolio_weight: float | None
    drift: float | None
    target_market_value: float | None
    rebalance_value: float | None
    rebalance_quantity: float | None
    break_even_price: float
    price_gap_to_cost_pct: float | None
    analysis_dimensions: list[HoldingAnalysisDimension] = Field(default_factory=list)
    action: str
    conclusion: str
    risk_flags: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)


class WatchlistItem(StrictModel):
    id: int
    symbol: str
    name: str
    thesis: str
    invalidation: str
    status: str
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at")
    @classmethod
    def require_watchlist_timezone(cls, value: datetime) -> datetime:
        return DatasetMeta.require_timezone(value)


class UserAccount(StrictModel):
    id: int
    email: str
    display_name: str
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at")
    @classmethod
    def require_user_timezone(cls, value: datetime) -> datetime:
        return DatasetMeta.require_timezone(value)


class AuthResult(StrictModel):
    user: UserAccount
    access_token: str
    token_type: str = "bearer"


class UserPreferences(StrictModel):
    default_symbol: str = "SH.600519"
    start_page: str = "today"
    risk_profile: str = "balanced"
    morning_email_enabled: bool = True
