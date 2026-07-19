from datetime import date, datetime
from enum import StrEnum

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


class ScoreComponent(StrictModel):
    key: str
    label: str
    raw_value: float | None
    score: float
    weight: float
    weighted_score: float


class RankedCandidate(StrictModel):
    quote: EquityQuote
    base_score: float
    context_penalty: float
    score: float
    evidence_coverage: float = Field(ge=0, le=1)
    components: list[ScoreComponent]
    risk_flags: list[str] = Field(default_factory=list)


class ExcludedCandidate(StrictModel):
    quote: EquityQuote
    reasons: list[str]


class OpportunityResult(StrictModel):
    preset: str
    available: bool
    unavailable_reason: str | None = None
    rules: list[str]
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


class StockDossier(StrictModel):
    quote: EquityQuote
    stance: str
    stance_score: float | None
    evidence_coverage: float = Field(ge=0, le=1)
    score_factors: list[StockScoreFactor]
    research_evidence: list[str] = Field(default_factory=list)
    technical: TechnicalSummary | None
    bull_case: list[str]
    bear_case: list[str]
    invalidation: list[str]
    missing_evidence: list[str]
    bars: list[Bar]


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
