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
export type HoldingDossier = { item: HoldingItem; quote: Quote; market_value: number | null; cost_value: number; pnl: number | null; pnl_pct: number | null; portfolio_weight: number | null; drift: number | null; target_market_value: number | null; rebalance_value: number | null; rebalance_quantity: number | null; break_even_price: number; price_gap_to_cost_pct: number | null; analysis_dimensions: HoldingAnalysisDimension[]; action: string; conclusion: string; risk_flags: string[]; next_actions: string[] };
export type TodayData = { meta: Meta; analysis: Analysis; indices: IndexQuote[]; sectors: Sector[]; top_opportunities: Candidate[]; risk_budget: number; next_actions: string[] };

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { ...init, headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) } });
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
