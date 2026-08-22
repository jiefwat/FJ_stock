export type Meta = { source: string; observed_at: string; fetched_at: string; freshness: string; coverage: number; errors: string[] };
export type RefreshResult = { status: string; meta: Meta };
export type Quote = { symbol: string; code: string; name: string; price: number | null; change_pct: number | null; amount: number | null; turnover_rate: number | null; volume_ratio: number | null; pe: number | null; pb: number | null; market_cap: number | null; net_flow: number | null; sector: string | null; asset_type?: "stock" | "etf" | "index" | "global"; exchange?: "SH" | "SZ" | "BJ" | "HK" | "US" | null; price_limit_pct?: number | null };
export type IndexQuote = { symbol: string; name: string; price: number | null; change_pct: number | null; amount: number | null };
export type Sector = { code: string; name: string; change_pct: number | null; net_flow: number | null };
export type SectorDossier = { sector: Sector; summary: string[]; evidence_coverage: number; missing_evidence: string[]; constituents: Quote[] };
export type Factor = { key: string; label: string; score: number | null; weight: number; available: boolean; evidence: string };
export type Analysis = { score: number; regime: string; confidence: number; factors: Factor[]; advancing: number; declining: number; unchanged: number };
export type MarketDistributionBand = { key: string; label: string; count: number; tone: "strong_down" | "down" | "flat" | "up" | "strong_up" };
export type MarketDashboard = { meta: Meta; score: number; regime: string; confidence: number; breadth_pct: number | null; capital_inflow_pct: number | null; total_turnover: number | null; limit_up_count: number; limit_down_count: number; distribution: MarketDistributionBand[]; strongest_sectors: Sector[]; weakest_sectors: Sector[]; activity_leaders: Quote[]; missing_evidence: string[] };
export type StrategyBoardCard = { id: string; name: string; category: string; summary: string; entry_signal: string; exit_signal: string; hit_count: number; available: boolean; confidence: number; top_candidate: Quote | null };
export type StrategyBoard = { meta: Meta; cards: StrategyBoardCard[] };
export type LimitLadderStock = { quote: Quote; streak: number; limit_pct: number; one_word: boolean | null; confidence: number; evidence: string[] };
export type LimitLadderLevel = { streak: number; label: string; stocks: LimitLadderStock[] };
export type LimitLadderResult = { meta: Meta; mode: "up" | "down"; available: boolean; unavailable_reason: string | null; total: number; max_streak: number; confidence: number; levels: LimitLadderLevel[]; industry_distribution: Record<string, number>; methodology: string[] };
export type MarketGroupLeader = { quote: Quote; score: number };
export type MarketGroupStat = { code: string; name: string; kind: "concept" | "industry"; change_pct: number | null; net_flow: number | null; constituent_count: number; advancing: number; declining: number; average_change_pct: number | null; average_turnover_rate: number | null; total_amount: number | null; heat_score: number; risk_score: number; evidence_coverage: number; leader: MarketGroupLeader | null; constituents: Quote[]; missing_evidence: string[] };
export type MarketGroupAnalysis = { meta: Meta; kind: "concept" | "industry"; available: boolean; degraded: boolean; unavailable_reason: string | null; summary: string; groups: MarketGroupStat[]; methodology: string[] };
export type MarketEvent = { id: string; title: string; summary: string; source: string; url: string | null; published_at: string; related_symbols: string[]; related_sectors: string[]; category: string; sentiment: string; importance_score: number; tags: string[]; impact: string; action: string };
export type MarketEventCluster = { key: string; label: string; signal: string; count: number; summary: string; hot_score: number };
export type MarketEventResult = { meta: Meta; summary: string[]; next_actions: string[]; clusters: MarketEventCluster[]; events: MarketEvent[] };
export type CapabilityState = { status: "not_checked" | "ready" | "partial" | "empty" | "unavailable"; provider: string; error: string | null; fetched_at: string | null };
export type SourceRef = { provider: string; label: string; capability: string; source_url: string | null; observed_at: string; fetched_at: string; freshness: string };
export type EvidenceDocument = { id: string; kind: "filing" | "research"; symbol: string; title: string; category: string; publisher: string; published_at: string; url: string; rating: string | null; eps_forecasts: Record<string, number>; source: SourceRef };
export type InstrumentTheme = { code: string; name: string; change_pct: number | null; lead_stock: string | null; source: SourceRef };
export type InstrumentEvidenceResult = { symbol: string; filings: EvidenceDocument[]; research: EvidenceDocument[]; themes: InstrumentTheme[]; capabilities: Record<string, CapabilityState> };
export type FinancialPeriod = { report_date: string; report_label: string; report_type: string; revenue: number | null; revenue_yoy: number | null; net_profit: number | null; net_profit_yoy: number | null; roe: number | null; gross_margin: number | null; operating_cash_flow_per_share: number | null; cash_receipts_to_revenue: number | null; debt_to_assets: number | null };
export type FinancialHealth = { available: boolean; score: number | null; score_impact: number; conclusion: string; report_date: string | null; risks: string[]; periods: FinancialPeriod[]; error: string | null };
export type StockNewsItem = { id: string; title: string; summary: string; media: string; url: string; published_at: string; sentiment: "positive" | "neutral" | "negative"; hard_risk: boolean; hard_risk_terms: string[] };
export type StockNewsSentiment = { available: boolean; window_days: number; conclusion: string; positive_count: number; negative_count: number; neutral_count: number; hard_risk_count: number; score_impact: number; risks: string[]; items: StockNewsItem[]; error: string | null };
export type TradingAnomaly = { symbol: string; name: string; trade_date: string; reason: string; close: number | null; change_pct: number | null; net_buy: number | null; buy_amount: number | null; sell_amount: number | null; turnover_rate: number | null; source: SourceRef };
export type MarketIntelligenceResult = { meta: Meta; sector_flows: Sector[]; anomalies: TradingAnomaly[]; capabilities: Record<string, CapabilityState> };
export type OpportunityDimension = { key: string; label: string; signal: string; score: number | null; summary: string; evidence: string[]; available?: boolean };
export type OpportunityHistoryCheck = { available: boolean; lookback_days: number; score: number | null; trend_20d_pct: number | null; trend_60d_pct: number | null; ma20_gap_pct: number | null; volatility_20d: number | null; max_drawdown_60d: number | null; volume_ratio_20d: number | null; summary: string; evidence: string[]; risk_flags: string[] };
export type StrategyValidation = { passed: boolean; checks: string[]; failures: string[] };
export type DecisionPresentation = { action: string; summary: string; severity: "critical" | "high" | "action" | "info"; user_required: boolean; reason_code: string; layer: "priority" | "review" | "watch_only" | "high_risk" | null; confidence?: number | null };
export type Candidate = { quote: Quote; base_score: number; context_penalty: number; score: number; upside_score?: number; upside_label?: string; upside_summary?: string; upside_drivers?: string[]; upside_risks?: string[]; evidence_coverage: number; components: { key: string; label: string; raw_value: number | null; score: number; weight: number; weighted_score: number }[]; dimensions: OpportunityDimension[]; history_check?: OpportunityHistoryCheck | null; strategy_validation?: StrategyValidation; thesis: string; invalidation: string[]; next_actions: string[]; risk_flags: string[]; decision?: DecisionPresentation | null };
export type RecommendationPerformancePick = { rank: number; symbol: string; name: string; sector: string | null; entry_price: number | null; current_price: number | null; score: number; evidence_coverage: number; thesis: string; risk_flags: string[]; observed_sessions: number; return_1d: number | null; return_5d: number | null; return_20d: number | null; current_return: number | null; benchmark_20d_return: number | null; excess_20d_return: number | null; current_benchmark_return: number | null; current_excess_return: number | null; peak_return: number | null; max_drawdown: number | null; status: "tracking" | "validating" | "evaluated" | "missing" };
export type RecommendationPerformanceDay = { preset: string; trading_date: string; observed_at: string; available: boolean; unavailable_reason: string | null; summary: string; picks: RecommendationPerformancePick[] };
export type RecommendationHistoryResult = { preset: string; generated_at: string; first_tracking_date: string | null; last_observed_at: string | null; summary: { run_count: number; pick_count: number; evaluated_count: number; average_20d_return: number | null; hit_rate_20d: number | null; benchmark_win_rate_20d: number | null; average_20d_excess: number | null; average_current_return: number | null; current_positive_rate: number | null }; days: RecommendationPerformanceDay[]; methodology: string[] };
export type WatchlistItem = { id: number; symbol: string; name: string; thesis: string; invalidation: string; status: string; created_at?: string; updated_at: string };
export type HoldingItem = { id: number; symbol: string; name: string; quantity: number; cost_price: number; target_weight?: number; thesis: string; invalidation: string; status: string; created_at?: string; updated_at: string };
export type HoldingAnalysisDimension = { key: string; label: string; signal: string; summary: string; evidence: string[] };
export type HoldingDailyChange = { date: string; change_pct: number | null };
export type HoldingDossier = { item: HoldingItem; quote: Quote; market_value: number | null; cost_value: number; pnl: number | null; pnl_pct: number | null; day_pnl?: number | null; day_pnl_pct?: number | null; three_day_pnl?: number | null; three_day_pnl_pct?: number | null; five_day_pnl?: number | null; five_day_pnl_pct?: number | null; recent_daily_changes?: HoldingDailyChange[]; portfolio_weight: number | null; drift: number | null; target_market_value: number | null; rebalance_value: number | null; rebalance_quantity: number | null; break_even_price: number; price_gap_to_cost_pct: number | null; analysis_dimensions: HoldingAnalysisDimension[]; action: string; decision?: DecisionPresentation | null; conclusion: string; risk_flags: string[]; next_actions: string[] };
export type DecisionEvent = { id: number; source: "holding" | "opportunity"; subject_key: string; symbol: string; name: string; strategy: string | null; previous_action: string; action: string; summary: string; severity: "critical" | "high" | "action" | "info"; user_required: boolean; reason_code: string; confidence: number | null; href: string; observed_at: string; created_at: string; read_at: string | null; email_status: "not_required" | "pending" | "sent" | "failed"; email_attempts: number; email_error: string | null; email_sent_at: string | null };
export type DecisionEventFeed = { unread_count: number; requires_action: DecisionEvent[]; monitoring: DecisionEvent[]; monitored_at: string | null };
export type UserAccount = { id: number; email: string; display_name: string; created_at: string; updated_at: string };
export type AuthResult = { user: UserAccount; access_token: string; token_type: "bearer" };
export type UserPreferences = { default_symbol: string; start_page: string; risk_profile: string; morning_email_enabled: boolean };
export type EquityExchange = "all" | "sh" | "sz" | "bj";
export type EquitySort = "amount" | "change_pct" | "turnover_rate" | "market_cap";
export type SortDirection = "asc" | "desc";
export type EquityViewFilters = {
  query: string;
  exchange: EquityExchange;
  sector: string | null;
  min_change_pct: number | null;
  max_change_pct: number | null;
  min_amount: number | null;
  max_amount: number | null;
  min_turnover_rate: number | null;
  max_turnover_rate: number | null;
  min_market_cap: number | null;
  max_market_cap: number | null;
  complete_only: boolean;
  sort_by: EquitySort;
  direction: SortDirection;
  page_size: 25 | 50;
};
export type SavedEquityView = { id: number; name: string; filters: EquityViewFilters; created_at: string; updated_at: string };
export type EquityPage = { meta: Meta; total: number; page: number; page_size: number; exchange: EquityExchange; sort_by: EquitySort; direction: SortDirection; available_sectors: string[]; items: Quote[] };
export type AskStockCell = string | number | boolean | null;
export type AskStockMetric = {
  label: string;
  value: string;
  tone: "positive" | "neutral" | "negative" | "missing";
};
export type AskStockFactor = {
  label: string;
  impact: number;
  signal: "positive" | "neutral" | "negative" | "missing";
  evidence: string;
};
export type AskStockHoldingContext = {
  owned: boolean;
  quantity: number | null;
  cost_price: number | null;
  market_value: number | null;
  pnl_pct: number | null;
  portfolio_weight: number | null;
  drift: number | null;
  ten_day_change_pct?: number | null;
  ten_day_contribution?: number | null;
  action: string | null;
  risk_flags: string[];
};
export type AskStockConversationMessage = {
  role: "user" | "assistant";
  content: string;
};
export type AskStockSourceContext = {
  origin: string;
  label: string;
  detail?: string | null;
  stock?: { symbol?: string | null; name?: string | null } | null;
};
export type AskStockResponse = {
  kind: "stock_analysis" | "semantic_screen" | "portfolio_analysis" | "llm_answer";
  question: string;
  intent: "risk" | "trend" | "valuation" | "fundamental" | "catalyst" | "action" | "movement" | "overview" | "screening" | "portfolio";
  symbol: string | null;
  name: string | null;
  answer: string;
  evidence: string[];
  risks: string[];
  next_actions: string[];
  metrics?: AskStockMetric[];
  factors?: AskStockFactor[];
  holding_context?: AskStockHoldingContext | null;
  observed_at: string | null;
  confidence?: number | null;
  source: string;
  disclaimer: string;
  columns: string[];
  rows: Array<Record<string, AskStockCell>>;
};

const tokenKey = "marketdesk.accessToken";

export function getAuthToken(): string | null {
  if (typeof localStorage === "undefined" || typeof localStorage.getItem !== "function") return null;
  return localStorage.getItem(tokenKey);
}

export function setAuthToken(token: string): void {
  if (typeof localStorage === "undefined" || typeof localStorage.setItem !== "function") return;
  localStorage.setItem(tokenKey, token);
}

export function clearAuthToken(): void {
  if (typeof localStorage === "undefined" || typeof localStorage.removeItem !== "function") return;
  localStorage.removeItem(tokenKey);
}

export class ApiError extends Error {
  constructor(public readonly status: number, public readonly detail: string) {
    super(detail);
    this.name = "ApiError";
  }
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("Content-Type", "application/json");
  const token = getAuthToken();
  if (token && !headers.has("Authorization")) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(path, { ...init, headers });
  if (!response.ok) {
    let detail = `请求失败 (${response.status})`;
    try {
      const payload = await response.json() as { detail?: unknown };
      if (typeof payload.detail === "string" && payload.detail.trim()) detail = payload.detail;
    } catch {
      // Keep the status-based fallback when the backend did not return JSON.
    }
    throw new ApiError(response.status, detail);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export function fmt(value: number | null | undefined, digits = 2): string {
  return value == null || !Number.isFinite(value) ? "—" : value.toLocaleString("zh-CN", { maximumFractionDigits: digits });
}

export function pct(value: number | null | undefined): string {
  return value == null ? "—" : `${value > 0 ? "+" : ""}${value.toFixed(2)}%`;
}

export function percent(value: number | null | undefined, digits = 0): string {
  return value == null ? "—" : `${value.toFixed(digits)}%`;
}
