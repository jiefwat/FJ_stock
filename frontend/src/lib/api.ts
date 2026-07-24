export type Meta = { source: string; observed_at: string; fetched_at: string; freshness: string; coverage: number; errors: string[] };
export type Quote = { symbol: string; code: string; name: string; price: number | null; change_pct: number | null; amount: number | null; turnover_rate: number | null; volume_ratio: number | null; pe: number | null; pb: number | null; market_cap: number | null; net_flow: number | null; sector: string | null };
export type IndexQuote = { symbol: string; name: string; price: number | null; change_pct: number | null; amount: number | null };
export type Sector = { code: string; name: string; change_pct: number | null; net_flow: number | null };
export type SectorDossier = { sector: Sector; summary: string[]; evidence_coverage: number; missing_evidence: string[]; constituents: Quote[] };
export type Factor = { key: string; label: string; score: number | null; weight: number; available: boolean; evidence: string };
export type Analysis = { score: number; regime: string; confidence: number; factors: Factor[]; advancing: number; declining: number; unchanged: number };
export type MarketEvent = { id: string; title: string; summary: string; source: string; url: string | null; published_at: string; related_symbols: string[]; related_sectors: string[]; category: string; sentiment: string; importance_score: number; tags: string[]; impact: string; action: string };
export type MarketEventCluster = { key: string; label: string; signal: string; count: number; summary: string; hot_score: number };
export type MarketEventResult = { meta: Meta; summary: string[]; next_actions: string[]; clusters: MarketEventCluster[]; events: MarketEvent[] };
export type OpportunityDimension = { key: string; label: string; signal: string; score: number | null; summary: string; evidence: string[]; available?: boolean };
export type Candidate = { quote: Quote; base_score: number; context_penalty: number; score: number; evidence_coverage: number; components: { key: string; label: string; raw_value: number | null; score: number; weight: number; weighted_score: number }[]; dimensions: OpportunityDimension[]; thesis: string; invalidation: string[]; next_actions: string[]; risk_flags: string[] };
export type WatchlistItem = { id: number; symbol: string; name: string; thesis: string; invalidation: string; status: string; created_at?: string; updated_at: string };
export type HoldingItem = { id: number; symbol: string; name: string; quantity: number; cost_price: number; target_weight: number; thesis: string; invalidation: string; status: string; created_at?: string; updated_at: string };
export type HoldingAnalysisDimension = { key: string; label: string; signal: string; summary: string; evidence: string[] };
export type HoldingDossier = { item: HoldingItem; quote: Quote; market_value: number | null; cost_value: number; pnl: number | null; pnl_pct: number | null; day_pnl?: number | null; day_pnl_pct?: number | null; five_day_pnl?: number | null; five_day_pnl_pct?: number | null; portfolio_weight: number | null; drift: number | null; target_market_value: number | null; rebalance_value: number | null; rebalance_quantity: number | null; break_even_price: number; price_gap_to_cost_pct: number | null; analysis_dimensions: HoldingAnalysisDimension[]; action: string; conclusion: string; risk_flags: string[]; next_actions: string[] };
export type TodayData = { meta: Meta; analysis: Analysis; indices: IndexQuote[]; sectors: Sector[]; top_opportunities: Candidate[]; risk_budget: number; next_actions: string[] };
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

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("Content-Type", "application/json");
  const token = getAuthToken();
  if (token && !headers.has("Authorization")) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(path, { ...init, headers });
  if (!response.ok) throw new Error(`请求失败 (${response.status})`);
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
