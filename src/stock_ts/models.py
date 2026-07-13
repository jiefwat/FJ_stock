from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class IndexQuote:
    code: str
    name: str
    close: float
    pct_chg: float
    amount: float = 0.0


@dataclass(frozen=True)
class DailyBar:
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class MarketHistoryPoint:
    trade_date: str
    advancing: int
    declining: int
    breadth_ratio: float
    limit_up: int
    limit_down: int
    amount: float


@dataclass(frozen=True)
class FundamentalPeriod:
    date: str
    source: str
    revenue_yoy: float | None = None
    net_profit_yoy: float | None = None
    roe: float | None = None
    gross_margin: float | None = None
    debt_to_assets: float | None = None
    ocf_to_profit: float | None = None


@dataclass(frozen=True)
class ValuationPoint:
    date: str
    source: str
    pe_ttm: float | None = None
    pb: float | None = None
    ps: float | None = None


@dataclass(frozen=True)
class MarketRawData:
    trade_date: str
    indices: list[IndexQuote]
    advancing: int
    declining: int
    limit_up: int
    limit_down: int
    unchanged: int = 0
    top_sectors: list[tuple[str, float]] = field(default_factory=list)
    northbound_net_inflow: float | None = None
    limit_down_details: list[LimitDownStock] = field(default_factory=list)
    history: list[MarketHistoryPoint] = field(default_factory=list)


@dataclass(frozen=True)
class MarketSnapshot:
    trade_date: str
    heat_score: int
    breadth_ratio: float
    summary: str
    regime: str
    indices: list[IndexQuote]
    top_sectors: list[tuple[str, float]]
    dimensions: list[MarketDimension]
    opportunities: list[str]
    risks: list[str]
    tomorrow_watch: list[str]
    northbound_net_inflow: float | None = None
    limit_up_count: int = 0
    limit_down_count: int = 0
    advancing_count: int = 0
    declining_count: int = 0
    unchanged_count: int = 0
    limit_down_details: list[LimitDownStock] = field(default_factory=list)
    history: list[MarketHistoryPoint] = field(default_factory=list)


@dataclass(frozen=True)
class LimitDownStock:
    code: str
    name: str
    sector: str
    latest_close: float
    pct_chg: float
    reason: str = ""


@dataclass(frozen=True)
class MarketDimension:
    name: str
    score: int
    status: str
    evidence: str


@dataclass(frozen=True)
class StockRawData:
    code: str
    name: str
    bars: list[DailyBar]
    fund_flow: float | None = None
    pe_ttm: float | None = None
    valuation: dict[str, float | str | None] = field(default_factory=dict)
    fundamental_metrics: dict[str, float | str | None] = field(default_factory=dict)
    fund_flow_detail: dict[str, float | str | None] = field(default_factory=dict)
    news_items: list[NewsItem] = field(default_factory=list)
    announcements: list[dict[str, object]] = field(default_factory=list)
    data_sources: list[str] = field(default_factory=list)
    fundamental_history: list[FundamentalPeriod] = field(default_factory=list)
    valuation_history: list[ValuationPoint] = field(default_factory=list)


@dataclass(frozen=True)
class StockAnalysisDecision:
    verdict: str
    core_conflicts: list[str]
    today_action: str
    forbidden_action: str
    strengthen_condition: str
    exit_condition: str
    data_reliability: str


@dataclass(frozen=True)
class StockAnalysisReport:
    code: str
    name: str
    latest_date: str
    latest_close: float
    pct_change: float
    trend: str
    risk_level: str
    observations: list[str]
    watch_points: list[str]
    fund_flow: float | None = None
    pe_ttm: float | None = None
    dimensions: list[StockAnalysisDimension] = field(default_factory=list)
    decision: StockAnalysisDecision = field(
        default_factory=lambda: StockAnalysisDecision(
            verdict="观察",
            core_conflicts=["证据不足，先观察。"],
            today_action="只观察，不追高。",
            forbidden_action="不因单一指标临时交易。",
            strengthen_condition="等待趋势、资金和事件证据补齐。",
            exit_condition="跌破关键均线或失效线时降风险。",
            data_reliability="低可信",
        )
    )


@dataclass(frozen=True)
class StockAnalysisDimension:
    name: str
    score: int
    status: str
    evidence: str
    action: str


@dataclass(frozen=True)
class Holding:
    code: str
    name: str
    shares: float
    cost_price: float
    sector: str = ""
    note: str = ""


@dataclass(frozen=True)
class Transaction:
    date: str
    code: str
    name: str
    side: str
    shares: float
    price: float
    fee: float = 0.0
    tax: float = 0.0
    sector: str = ""
    note: str = ""


@dataclass(frozen=True)
class PositionAnalysis:
    holding: Holding
    latest_price: float
    previous_close: float
    market_value: float
    cost_value: float
    daily_pnl: float
    daily_pnl_ratio: float
    pnl: float
    pnl_ratio: float
    weight: float
    trend: str
    risk_level: str
    observations: list[str]


@dataclass(frozen=True)
class PortfolioAnalysisReport:
    trade_date: str
    total_market_value: float
    total_cost: float
    total_pnl: float
    total_pnl_ratio: float
    daily_pnl: float
    health_score: int
    cash_position_note: str
    top_position_weight: float
    sector_weights: list[tuple[str, float]]
    positions: list[PositionAnalysis]
    risk_alerts: list[str]
    market_alignment: list[str]
    action_checklist: list[str]


@dataclass(frozen=True)
class SectorRawData:
    name: str
    pct_chg: float
    advancing_ratio: float
    amount_change: float
    fund_flow: float | None = None
    consecutive_days: int = 1
    limit_up_count: int = 0
    high_divergence: bool = False


@dataclass(frozen=True)
class SectorAnalysis:
    name: str
    pct_chg: float
    heat_score: int
    advancing_ratio: float
    amount_change: float
    limit_up_count: int
    continuity: str
    fund_status: str
    rotation_status: str
    risk: str


@dataclass(frozen=True)
class SectorAnalysisReport:
    trade_date: str
    sectors: list[SectorAnalysis]
    market_mainline: list[str]
    rotation_notes: list[str]
    risk_notes: list[str]


@dataclass(frozen=True)
class CandidateStockRawData:
    code: str
    name: str
    sector: str
    bars: list[DailyBar]
    fund_flow: float | None = None
    turnover_rate: float = 0.0
    amount: float = 0.0
    pe_ttm: float | None = None
    price_reliable: bool = True
    news_items: list[NewsItem] = field(default_factory=list)
    announcements: list[dict[str, object]] = field(default_factory=list)


@dataclass(frozen=True)
class CandidateStockAnalysis:
    code: str
    name: str
    sector: str
    score: int
    latest_close: float
    pct_change: float
    reasons: list[str]
    risks: list[str]
    watch_conditions: list[str]
    price_reliable: bool = True


@dataclass(frozen=True)
class CandidatePoolReport:
    trade_date: str
    candidates: list[CandidateStockAnalysis]
    method_notes: list[str]
    disclaimer: str
    price_reliable: bool = True


@dataclass(frozen=True)
class NewsItem:
    date: str
    source: str
    title: str
    summary: str
    url: str = ""
    sentiment: str = "neutral"


@dataclass(frozen=True)
class NewsSentimentReport:
    trade_date: str
    items: list[NewsItem]
    positive_count: int
    negative_count: int
    neutral_count: int
    summary: str
    risks: list[str]
