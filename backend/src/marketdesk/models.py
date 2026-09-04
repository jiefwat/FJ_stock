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


DecisionSeverity = Literal["critical", "high", "action", "info"]


class DecisionPresentation(StrictModel):
    action: str = Field(min_length=1, max_length=40)
    summary: str = Field(min_length=1, max_length=300)
    severity: DecisionSeverity
    user_required: bool
    reason_code: str = Field(min_length=1, max_length=80)
    layer: Literal["priority", "review", "watch_only", "high_risk"] | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)


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


class FinancialPeriod(StrictModel):
    report_date: date
    report_label: str
    report_type: str
    revenue: float | None = None
    revenue_yoy: float | None = None
    net_profit: float | None = None
    net_profit_yoy: float | None = None
    roe: float | None = None
    gross_margin: float | None = None
    operating_cash_flow_per_share: float | None = None
    cash_receipts_to_revenue: float | None = None
    debt_to_assets: float | None = None


class FinancialHealth(StrictModel):
    available: bool
    score: float | None = Field(default=None, ge=0, le=100)
    score_impact: float = Field(default=0, ge=-10, le=6)
    conclusion: str
    report_date: date | None = None
    risks: list[str] = Field(default_factory=list)
    periods: list[FinancialPeriod] = Field(default_factory=list)
    error: str | None = None


class StockNewsItem(StrictModel):
    id: str
    title: str
    summary: str
    media: str
    url: str
    published_at: datetime
    sentiment: Literal["positive", "neutral", "negative"] = "neutral"
    hard_risk: bool = False
    hard_risk_terms: list[str] = Field(default_factory=list)

    @field_validator("published_at")
    @classmethod
    def require_news_timezone(cls, value: datetime) -> datetime:
        return DatasetMeta.require_timezone(value)

    @field_validator("url")
    @classmethod
    def require_http_news_url(cls, value: str) -> str:
        if not value.startswith(("http://", "https://")):
            raise ValueError("news URL must use http or https")
        return value


class StockNewsSentiment(StrictModel):
    available: bool
    window_days: int = Field(default=30, ge=1, le=90)
    conclusion: str
    positive_count: int = Field(default=0, ge=0)
    negative_count: int = Field(default=0, ge=0)
    neutral_count: int = Field(default=0, ge=0)
    hard_risk_count: int = Field(default=0, ge=0)
    score_impact: float = Field(default=0, ge=-6, le=0)
    risks: list[str] = Field(default_factory=list)
    items: list[StockNewsItem] = Field(default_factory=list)
    error: str | None = None


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
    asset_type: Literal["stock", "etf", "index", "global"] = "stock"
    exchange: Literal["SH", "SZ", "BJ", "HK", "US"] | None = None
    price_limit_pct: float | None = Field(default=None, gt=0)


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


class MarketDistributionBand(StrictModel):
    key: str
    label: str
    count: int = Field(ge=0)
    tone: Literal["strong_down", "down", "flat", "up", "strong_up"]


class MarketDashboard(StrictModel):
    meta: DatasetMeta
    score: float = Field(ge=0, le=100)
    regime: str
    confidence: float = Field(ge=0, le=1)
    breadth_pct: float | None = Field(default=None, ge=0, le=100)
    capital_inflow_pct: float | None = Field(default=None, ge=0, le=100)
    total_turnover: float | None = Field(default=None, ge=0)
    limit_up_count: int = Field(default=0, ge=0)
    limit_down_count: int = Field(default=0, ge=0)
    distribution: list[MarketDistributionBand] = Field(default_factory=list)
    strongest_sectors: list[SectorSnapshot] = Field(default_factory=list)
    weakest_sectors: list[SectorSnapshot] = Field(default_factory=list)
    activity_leaders: list[EquityQuote] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)


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


class OpportunityHistoryCheck(StrictModel):
    available: bool
    lookback_days: int = 0
    score: float | None = Field(default=None, ge=0, le=100)
    trend_20d_pct: float | None = None
    trend_60d_pct: float | None = None
    ma20_gap_pct: float | None = None
    volatility_20d: float | None = None
    max_drawdown_60d: float | None = None
    volume_ratio_20d: float | None = None
    summary: str
    evidence: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)


class StrategyValidation(StrictModel):
    passed: bool = True
    checks: list[str] = Field(default_factory=list)
    failures: list[str] = Field(default_factory=list)


class RankedCandidate(StrictModel):
    quote: EquityQuote
    base_score: float
    context_penalty: float
    score: float
    upside_score: float = Field(default=0.0, ge=0, le=100)
    upside_label: str = ""
    upside_summary: str = ""
    upside_drivers: list[str] = Field(default_factory=list)
    upside_risks: list[str] = Field(default_factory=list)
    evidence_coverage: float = Field(ge=0, le=1)
    components: list[ScoreComponent]
    dimensions: list[OpportunityDimension] = Field(default_factory=list)
    history_check: OpportunityHistoryCheck | None = None
    strategy_validation: StrategyValidation = Field(default_factory=StrategyValidation)
    thesis: str = ""
    invalidation: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    decision: DecisionPresentation | None = None


class ExcludedCandidate(StrictModel):
    quote: EquityQuote
    reasons: list[str]


class OpportunityResult(StrictModel):
    preset: str
    available: bool
    unavailable_reason: str | None = None
    monitoring_active: bool = False
    monitored_at: datetime | None = None
    summary: str = ""
    rules: list[str]
    diagnostics: list[OpportunityDimension] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    funnel: dict[str, int]
    candidates: list[RankedCandidate]
    excluded: list[ExcludedCandidate]


class StrategyBoardCard(StrictModel):
    id: str
    name: str
    category: str
    summary: str
    entry_signal: str
    exit_signal: str
    hit_count: int = Field(ge=0)
    available: bool = True
    confidence: float = Field(ge=0, le=1)
    top_candidate: EquityQuote | None = None


class StrategyBoard(StrictModel):
    meta: DatasetMeta
    cards: list[StrategyBoardCard]


class LimitLadderStock(StrictModel):
    quote: EquityQuote
    streak: int = Field(ge=1)
    limit_pct: float = Field(gt=0)
    one_word: bool | None = None
    confidence: float = Field(ge=0, le=1)
    evidence: list[str] = Field(default_factory=list)


class LimitLadderLevel(StrictModel):
    streak: int = Field(ge=1)
    label: str
    stocks: list[LimitLadderStock] = Field(default_factory=list)


class LimitLadderResult(StrictModel):
    meta: DatasetMeta
    mode: Literal["up", "down"]
    available: bool
    unavailable_reason: str | None = None
    total: int = Field(default=0, ge=0)
    max_streak: int = Field(default=0, ge=0)
    confidence: float = Field(ge=0, le=1)
    levels: list[LimitLadderLevel] = Field(default_factory=list)
    industry_distribution: dict[str, int] = Field(default_factory=dict)
    methodology: list[str] = Field(default_factory=list)


class MarketGroupLeader(StrictModel):
    quote: EquityQuote
    score: float = Field(ge=0, le=100)


class MarketGroupStat(StrictModel):
    code: str
    name: str
    kind: Literal["concept", "industry"]
    change_pct: float | None = None
    net_flow: float | None = None
    constituent_count: int = Field(default=0, ge=0)
    advancing: int = Field(default=0, ge=0)
    declining: int = Field(default=0, ge=0)
    average_change_pct: float | None = None
    average_turnover_rate: float | None = None
    total_amount: float | None = Field(default=None, ge=0)
    heat_score: float = Field(ge=0, le=100)
    risk_score: float = Field(ge=0, le=100)
    evidence_coverage: float = Field(ge=0, le=1)
    leader: MarketGroupLeader | None = None
    constituents: list[EquityQuote] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)


class MarketGroupAnalysis(StrictModel):
    meta: DatasetMeta
    kind: Literal["concept", "industry"]
    available: bool
    degraded: bool = False
    unavailable_reason: str | None = None
    summary: str
    groups: list[MarketGroupStat] = Field(default_factory=list)
    methodology: list[str] = Field(default_factory=list)


class RecommendationSnapshotPick(StrictModel):
    rank: int = Field(ge=1)
    symbol: str
    name: str
    sector: str | None = None
    entry_price: float | None = Field(default=None, gt=0)
    score: float
    evidence_coverage: float = Field(ge=0, le=1)
    thesis: str
    risk_flags: list[str] = Field(default_factory=list)


class RecommendationSnapshot(StrictModel):
    preset: str
    algorithm_version: str = "v1"
    trading_date: date
    observed_at: datetime
    available: bool
    unavailable_reason: str | None = None
    summary: str = ""
    benchmark_symbol: str | None = None
    benchmark_name: str | None = None
    benchmark_price: float | None = Field(default=None, gt=0)
    picks: list[RecommendationSnapshotPick] = Field(default_factory=list)

    @field_validator("observed_at")
    @classmethod
    def require_recommendation_timezone(cls, value: datetime) -> datetime:
        return DatasetMeta.require_timezone(value)


class RecommendationObservation(StrictModel):
    trading_date: date
    observed_at: datetime
    benchmark_price: float | None = Field(default=None, gt=0)
    prices: dict[str, float] = Field(default_factory=dict)

    @field_validator("observed_at")
    @classmethod
    def require_observation_timezone(cls, value: datetime) -> datetime:
        return DatasetMeta.require_timezone(value)


class RecommendationPerformancePick(StrictModel):
    rank: int
    symbol: str
    name: str
    sector: str | None = None
    entry_price: float | None = None
    current_price: float | None = None
    score: float
    evidence_coverage: float
    thesis: str
    risk_flags: list[str] = Field(default_factory=list)
    observed_sessions: int = Field(ge=0)
    return_1d: float | None = None
    return_5d: float | None = None
    return_20d: float | None = None
    current_return: float | None = None
    benchmark_20d_return: float | None = None
    excess_20d_return: float | None = None
    current_benchmark_return: float | None = None
    current_excess_return: float | None = None
    peak_return: float | None = None
    max_drawdown: float | None = None
    status: Literal["tracking", "validating", "evaluated", "missing"]


class RecommendationPerformanceDay(StrictModel):
    preset: str
    trading_date: date
    observed_at: datetime
    available: bool
    unavailable_reason: str | None = None
    summary: str = ""
    picks: list[RecommendationPerformancePick] = Field(default_factory=list)


class RecommendationPerformanceSummary(StrictModel):
    run_count: int = Field(ge=0)
    pick_count: int = Field(ge=0)
    evaluated_count: int = Field(ge=0)
    average_20d_return: float | None = None
    hit_rate_20d: float | None = Field(default=None, ge=0, le=1)
    benchmark_win_rate_20d: float | None = Field(default=None, ge=0, le=1)
    average_20d_excess: float | None = None
    average_current_return: float | None = None
    current_positive_rate: float | None = Field(default=None, ge=0, le=1)


class RecommendationHistoryResult(StrictModel):
    preset: str
    generated_at: datetime
    first_tracking_date: date | None = None
    last_observed_at: datetime | None = None
    summary: RecommendationPerformanceSummary
    days: list[RecommendationPerformanceDay] = Field(default_factory=list)
    methodology: list[str] = Field(default_factory=list)


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
    participation_status: Literal["eligible", "conditional", "blocked"]
    blockers: list[str] = Field(default_factory=list)
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
    financial_health: FinancialHealth
    news_sentiment: StockNewsSentiment
    technical: TechnicalSummary | None
    bull_case: list[str]
    bear_case: list[str]
    invalidation: list[str]
    missing_evidence: list[str]
    bars: list[Bar]


JsonScalar = str | int | float | bool | None


class SemanticScreenResult(StrictModel):
    columns: list[str] = Field(max_length=12)
    rows: list[dict[str, JsonScalar]] = Field(max_length=100)


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
    ten_day_change_pct: float | None = None
    ten_day_contribution: float | None = None
    action: str | None = None
    risk_flags: list[str] = Field(default_factory=list)


class AskStockConversationMessage(StrictModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=1000)

    @field_validator("content", mode="before")
    @classmethod
    def normalize_content(cls, value: object) -> object:
        return " ".join(value.split()) if isinstance(value, str) else value


class AskStockSourceStock(StrictModel):
    symbol: str | None = Field(default=None, max_length=16)
    name: str | None = Field(default=None, max_length=32)

    @field_validator("symbol", "name", mode="before")
    @classmethod
    def normalize_text(cls, value: object) -> object:
        normalized = " ".join(value.split()) if isinstance(value, str) else value
        if isinstance(normalized, str) and normalized == "":
            return None
        return normalized


class AskStockSourceContext(StrictModel):
    origin: str = Field(min_length=1, max_length=40)
    label: str = Field(min_length=1, max_length=120)
    detail: str | None = Field(default=None, max_length=300)
    stock: AskStockSourceStock | None = None

    @field_validator("origin", "label", "detail", mode="before")
    @classmethod
    def normalize_text(cls, value: object) -> object:
        normalized = " ".join(value.split()) if isinstance(value, str) else value
        if isinstance(normalized, str) and normalized == "":
            return None
        return normalized


class AskStockResponse(StrictModel):
    kind: Literal["stock_analysis", "semantic_screen", "portfolio_analysis", "llm_answer"]
    question: str
    intent: Literal[
        "risk",
        "trend",
        "valuation",
        "fundamental",
        "catalyst",
        "action",
        "movement",
        "overview",
        "screening",
        "portfolio",
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
    confidence: float | None = Field(default=None, ge=0, le=1)
    source: str
    disclaimer: str
    columns: list[str] = Field(default_factory=list, max_length=12)
    rows: list[dict[str, JsonScalar]] = Field(default_factory=list, max_length=100)


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


class HoldingDailyChange(StrictModel):
    date: date
    change_pct: float | None


class HoldingDossier(StrictModel):
    item: HoldingItem
    quote: EquityQuote
    market_value: float | None
    cost_value: float
    pnl: float | None
    pnl_pct: float | None
    day_pnl: float | None = None
    day_pnl_pct: float | None = None
    three_day_pnl: float | None = None
    three_day_pnl_pct: float | None = None
    five_day_pnl: float | None = None
    five_day_pnl_pct: float | None = None
    recent_daily_changes: list[HoldingDailyChange] = Field(default_factory=list)
    portfolio_weight: float | None
    drift: float | None
    target_market_value: float | None
    rebalance_value: float | None
    rebalance_quantity: float | None
    break_even_price: float
    price_gap_to_cost_pct: float | None
    analysis_dimensions: list[HoldingAnalysisDimension] = Field(default_factory=list)
    action: str
    decision: DecisionPresentation | None = None
    conclusion: str
    risk_flags: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)


class DecisionSnapshot(StrictModel):
    source: Literal["holding", "opportunity"]
    subject_key: str = Field(min_length=1, max_length=80)
    symbol: str = Field(min_length=1, max_length=16)
    name: str = Field(min_length=1, max_length=40)
    strategy: str | None = Field(default=None, max_length=40)
    decision: DecisionPresentation
    href: str = Field(min_length=1, max_length=300)
    observed_at: datetime

    @field_validator("observed_at")
    @classmethod
    def require_decision_snapshot_timezone(cls, value: datetime) -> datetime:
        return DatasetMeta.require_timezone(value)


class DecisionEvent(StrictModel):
    id: int
    source: Literal["holding", "opportunity"]
    subject_key: str
    symbol: str
    name: str
    strategy: str | None = None
    previous_action: str
    action: str
    summary: str
    severity: DecisionSeverity
    user_required: bool
    reason_code: str
    confidence: float | None = Field(default=None, ge=0, le=1)
    href: str
    observed_at: datetime
    created_at: datetime
    read_at: datetime | None = None
    email_status: Literal["not_required", "pending", "sent", "failed"]
    email_attempts: int = Field(ge=0)
    email_error: str | None = None
    email_sent_at: datetime | None = None

    @field_validator("observed_at", "created_at", "read_at", "email_sent_at")
    @classmethod
    def require_decision_event_timezone(cls, value: datetime | None) -> datetime | None:
        return None if value is None else DatasetMeta.require_timezone(value)


class DecisionEventFeed(StrictModel):
    unread_count: int = Field(ge=0)
    requires_action: list[DecisionEvent] = Field(default_factory=list)
    monitoring: list[DecisionEvent] = Field(default_factory=list)
    monitored_at: datetime | None = None

    @field_validator("monitored_at")
    @classmethod
    def require_decision_feed_timezone(cls, value: datetime | None) -> datetime | None:
        return None if value is None else DatasetMeta.require_timezone(value)


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
    default_symbol: str = ""
    start_page: str = "market"
    risk_profile: str = "balanced"
    morning_email_enabled: bool = True


class MorningEmailBrief(StrictModel):
    recipient: str
    enabled: bool
    generated_at: datetime
    subject: str
    preheader: str
    text: str
    html: str

    @field_validator("generated_at")
    @classmethod
    def require_generated_timezone(cls, value: datetime) -> datetime:
        return DatasetMeta.require_timezone(value)
