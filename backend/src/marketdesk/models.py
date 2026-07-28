from datetime import date, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Freshness(StrEnum):
    FRESH = "fresh"
    DELAYED = "delayed"
    STALE = "stale"
    UNAVAILABLE = "unavailable"


class CapabilityStatus(StrEnum):
    NOT_CHECKED = "not_checked"
    READY = "ready"
    PARTIAL = "partial"
    EMPTY = "empty"
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


class SourceRef(StrictModel):
    provider: str
    label: str
    capability: str
    source_url: str | None = None
    observed_at: datetime
    fetched_at: datetime
    freshness: Freshness

    @field_validator("observed_at", "fetched_at")
    @classmethod
    def require_source_timezone(cls, value: datetime) -> datetime:
        return DatasetMeta.require_timezone(value)


class CapabilityState(StrictModel):
    status: CapabilityStatus
    provider: str
    error: str | None = None
    fetched_at: datetime | None = None

    @field_validator("fetched_at")
    @classmethod
    def require_capability_timezone(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return DatasetMeta.require_timezone(value)


class EvidenceDocument(StrictModel):
    id: str
    kind: Literal["filing", "research"]
    symbol: str
    title: str
    category: str
    publisher: str
    published_at: datetime
    url: str
    rating: str | None = None
    eps_forecasts: dict[str, float] = Field(default_factory=dict)
    source: SourceRef

    @field_validator("published_at")
    @classmethod
    def require_document_timezone(cls, value: datetime) -> datetime:
        return DatasetMeta.require_timezone(value)


class InstrumentTheme(StrictModel):
    code: str
    name: str
    change_pct: float | None = None
    lead_stock: str | None = None
    source: SourceRef


class TradingAnomaly(StrictModel):
    symbol: str
    name: str
    trade_date: date
    reason: str
    close: float | None = None
    change_pct: float | None = None
    net_buy: float | None = None
    buy_amount: float | None = None
    sell_amount: float | None = None
    turnover_rate: float | None = None
    source: SourceRef


class InstrumentEvidenceResult(StrictModel):
    symbol: str
    filings: list[EvidenceDocument] = Field(default_factory=list)
    research: list[EvidenceDocument] = Field(default_factory=list)
    themes: list[InstrumentTheme] = Field(default_factory=list)
    capabilities: dict[str, CapabilityState] = Field(default_factory=dict)


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


class MarketIntelligenceResult(StrictModel):
    meta: DatasetMeta
    sector_flows: list[SectorSnapshot] = Field(default_factory=list)
    anomalies: list[TradingAnomaly] = Field(default_factory=list)
    capabilities: dict[str, CapabilityState] = Field(default_factory=dict)


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
    available_sectors: list[str] = Field(default_factory=list)
    items: list[EquityQuote]


class EquityViewFilters(StrictModel):
    query: str = Field(default="", max_length=40)
    exchange: Literal["all", "sh", "sz", "bj"] = "all"
    sector: str | None = Field(default=None, max_length=40)
    min_change_pct: float | None = None
    max_change_pct: float | None = None
    min_amount: float | None = Field(default=None, ge=0)
    max_amount: float | None = Field(default=None, ge=0)
    min_turnover_rate: float | None = Field(default=None, ge=0)
    max_turnover_rate: float | None = Field(default=None, ge=0)
    min_market_cap: float | None = Field(default=None, ge=0)
    max_market_cap: float | None = Field(default=None, ge=0)
    complete_only: bool = False
    sort_by: Literal["amount", "change_pct", "turnover_rate", "market_cap"] = "amount"
    direction: Literal["asc", "desc"] = "desc"
    page_size: Literal[25, 50] = 25

    @model_validator(mode="after")
    def require_ordered_ranges(self) -> "EquityViewFilters":
        for minimum, maximum in (
            (self.min_change_pct, self.max_change_pct),
            (self.min_amount, self.max_amount),
            (self.min_turnover_rate, self.max_turnover_rate),
            (self.min_market_cap, self.max_market_cap),
        ):
            if minimum is not None and maximum is not None and minimum > maximum:
                raise ValueError("minimum cannot exceed maximum")
        return self


class SavedEquityView(StrictModel):
    id: int
    name: str
    filters: EquityViewFilters
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at")
    @classmethod
    def require_view_timezone(cls, value: datetime) -> datetime:
        return DatasetMeta.require_timezone(value)


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
    ema12: float | None
    ema26: float | None
    macd: float | None
    macd_signal: float | None
    macd_histogram: float | None
    rsi14: float | None
    volatility20: float | None
    atr14: float | None
    atr_pct: float | None
    bollinger_upper: float | None
    bollinger_lower: float | None
    bollinger_position: float | None
    max_drawdown60: float | None
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


class StockSignalValidation(StrictModel):
    available: bool
    horizon_days: int = 20
    sample_count: int = Field(ge=0)
    positive_rate: float | None = Field(default=None, ge=0, le=1)
    average_return: float | None = None
    worst_return: float | None = None
    summary: str


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
    signal_validation: StockSignalValidation
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


JsonScalar = str | int | float | bool | None


class SemanticScreenResult(StrictModel):
    columns: list[str] = Field(max_length=12)
    rows: list[dict[str, JsonScalar]] = Field(max_length=20)


class AskStockMetric(StrictModel):
    label: str
    value: str
    tone: Literal["positive", "neutral", "negative", "missing"] = "neutral"


class AskStockFactor(StrictModel):
    label: str
    impact: float
    signal: Literal["positive", "neutral", "negative", "missing"]
    evidence: str


class AskStockHoldingContext(StrictModel):
    owned: bool
    quantity: float | None = None
    cost_price: float | None = None
    market_value: float | None = None
    pnl_pct: float | None = None
    portfolio_weight: float | None = None
    drift: float | None = None
    action: str | None = None
    risk_flags: list[str] = Field(default_factory=list)


class AskStockResponse(StrictModel):
    kind: Literal["stock_analysis", "semantic_screen", "portfolio_analysis"]
    question: str
    intent: Literal[
        "risk", "trend", "valuation", "action", "overview", "screening", "portfolio"
    ]
    symbol: str | None = None
    name: str | None = None
    answer: str
    evidence: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    metrics: list[AskStockMetric] = Field(default_factory=list, max_length=8)
    factors: list[AskStockFactor] = Field(default_factory=list, max_length=12)
    holding_context: AskStockHoldingContext | None = None
    observed_at: datetime | None = None
    source: str
    disclaimer: str
    columns: list[str] = Field(default_factory=list, max_length=12)
    rows: list[dict[str, JsonScalar]] = Field(default_factory=list, max_length=20)


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
