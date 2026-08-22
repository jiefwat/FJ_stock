import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Activity, AlertTriangle, ChevronDown, Download, History } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { AsyncState } from "../../components/AsyncState";
import { api, fmt, pct, percent, type Candidate, type OpportunityDimension, type StrategyBoardCard } from "../../lib/api";
import { opportunityDecision, type OpportunityDecision } from "../../lib/decision";
import { monitoringText } from "../../lib/monitoring";
import { plainLanguage } from "../../lib/plainLanguage";

type Result = {
  preset: string;
  available: boolean;
  unavailable_reason: string | null;
  summary: string;
  rules: string[];
  diagnostics: OpportunityDimension[];
  next_actions: string[];
  funnel: Record<string, number>;
  candidates: Candidate[];
  excluded: { reasons: string[] }[];
  monitoring_active?: boolean;
  monitored_at?: string | null;
};

const presets = [
  ["trend", "趋势延续"],
  ["volume_breakout", "放量突破"],
  ["capital_confirmed", "资金确认"],
  ["sector_momentum", "板块共振"],
  ["pullback_support", "回踩企稳"],
  ["value_rebound", "低估反弹"],
  ["quality_value", "估值质量"],
  ["large_cap_stability", "蓝筹稳健"],
  ["oversold_repair", "超跌修复"],
];

function opportunitiesPath(preset: string) {
  return `/api/v1/opportunities?preset=${preset}&limit=10`;
}

const leadLayers = [
  ["all", "全部"],
  ["priority", "可试探"],
  ["review", "仅观察"],
  ["watch_only", "暂不买"],
  ["high_risk", "不参与"],
] as const;

type LeadLayer = typeof leadLayers[number][0];


type CandidateRow = { item: Candidate; badge: OpportunityDecision };

type QueuePlan = { tone: "positive" | "caution" | "negative" | "neutral"; route: string; };

function upsideScore(item: Candidate) {
  return item.upside_score ?? item.score;
}

function upsideLabel(item: Candidate) {
  return plainLanguage(item.upside_label || (upsideScore(item) >= 72 ? "优先关注" : "继续观察"));
}

function buildQueuePlan(counts: Record<LeadLayer, number>): QueuePlan {
  if (counts.all === 0) return { tone: "neutral", route: "今天没有可参与候选" };
  if (counts.priority > 0) return { tone: "positive", route: "首选可小仓试探" };
  if (counts.high_risk >= Math.max(2, Math.ceil(counts.all * 0.5))) return { tone: "negative", route: "今天暂不参与" };
  if (counts.review > 0) return { tone: "caution", route: "今天只观察" };
  return { tone: "neutral", route: "今天暂不买入" };
}

function OpportunityQueueDesk({
  preset,
  presetLabel,
  candidateRows,
  layerCounts,
}: {
  preset: string;
  presetLabel: string | undefined;
  candidateRows: CandidateRow[];
  layerCounts: Record<LeadLayer, number>;
}) {
  const layerRank: Record<OpportunityDecision["layer"], number> = { priority: 4, review: 3, watch_only: 2, high_risk: 1 };
  const topRow = candidateRows.reduce<CandidateRow | undefined>((best, row) => {
    if (!best) return row;
    const layerGap = layerRank[row.badge.layer] - layerRank[best.badge.layer];
    return layerGap > 0 || (layerGap === 0 && upsideScore(row.item) > upsideScore(best.item)) ? row : best;
  }, undefined);
  const plan = buildQueuePlan(layerCounts);
  const topHref = topRow ? `/stocks?symbol=${topRow.item.quote.symbol}&from=opportunities&preset=${preset}` : "";
  const riskTotal = layerCounts.watch_only + layerCounts.high_risk;
  const topLabel = topRow?.badge.layer === "priority" ? "首选" : "最接近条件";

  return <section className={`panel opportunity-queue ${plan.tone}`} aria-label="候选自动监控台">
    <div className="opportunity-monitoring-banner">
      <Activity size={20} aria-hidden="true" />
      <div><strong>自动更新 · 10 分钟</strong></div>
      <ul aria-label="自动监控范围"><li>价格与成交</li><li>板块与资金</li><li>公告与研报</li><li>淘汰条件</li></ul>
    </div>
    <div className="queue-gate">
      <span>当前决定</span>
      <strong>{plan.route}</strong>
    </div>
    <div className="queue-metrics" aria-label="线索队列统计">
      <div><span>策略</span><strong>{presetLabel ?? preset}</strong></div>
      <div><span>候选</span><strong>{layerCounts.all}</strong></div>
      <div><span>可试探</span><strong>{layerCounts.priority}</strong></div>
      <div><span>暂不参与</span><strong>{riskTotal}</strong></div>
    </div>
    {topRow ? <Link className="queue-top-card" to={topHref}>
      <small>{topLabel}</small>
      <strong>{topRow.item.quote.name}</strong>
      <span>{topRow.badge.action} · {topRow.item.quote.symbol} · 参考 {fmt(upsideScore(topRow.item), 0)}分 · 信息 {percent(topRow.item.evidence_coverage * 100)}</span>
    </Link> : <div className="queue-top-card empty-card"><small>首选</small><strong>暂无候选</strong><span>切换条件或等待刷新</span></div>}
    {topRow ? <nav className="queue-ask-bridge" aria-label="第一候选查看入口">
      <span>{topRow.badge.summary}</span>
      <Link to={topHref}>查看依据（可选）</Link>
    </nav> : null}
  </section>;
}

function HistoryCheckCard({ item }: { item: Candidate }) {
  const history = item.history_check;
  if (!history) return null;
  return <div className={`candidate-history ${history.available ? "available" : "missing"}`}>
    <div>
      <span>过去一段时间</span>
      <strong>{history.available ? `${fmt(history.score, 0)}/100` : "价格数据待补"}</strong>
    </div>
    <p>{plainLanguage(history.summary)}</p>
    <dl>
      <div><dt>近20天涨跌</dt><dd>{pct(history.trend_20d_pct)}</dd></div>
      <div><dt>近60天涨跌</dt><dd>{pct(history.trend_60d_pct)}</dd></div>
      <div><dt>距近20天均价</dt><dd>{pct(history.ma20_gap_pct)}</dd></div>
      <div><dt>价格起伏</dt><dd>{percent(history.volatility_20d)}</dd></div>
      <div><dt>从高点回落</dt><dd>{history.max_drawdown_60d == null ? "—" : `-${fmt(history.max_drawdown_60d, 1)}%`}</dd></div>
      <div><dt>成交活跃度</dt><dd>{history.volume_ratio_20d == null ? "—" : `${fmt(history.volume_ratio_20d, 1)}x`}</dd></div>
    </dl>
    <small>{history.evidence.map(plainLanguage).join(" · ")}</small>
  </div>;
}

function CandidateDecisionBrief({ item }: { item: Candidate }) {
  const badge = opportunityDecision(item);
  const reason = item.upside_drivers?.[0] ?? item.upside_summary ?? item.thesis;
  const risk = item.upside_risks?.[0] ?? item.risk_flags[0] ?? "暂未发现明确风险，仍按放弃条件执行";
  const change = item.invalidation[0] ?? "策略条件失效时重新评估";
  const missingDimensions = item.dimensions
    .filter((dimension) => dimension.signal === "missing" || dimension.available === false)
    .map((dimension) => `${plainLanguage(dimension.label)}不足`);
  const lowConfidence = item.evidence_coverage < 0.75;

  return <section className={`candidate-decision-brief ${badge.tone}`} aria-label={`${item.quote.name} 决策摘要`}>
    <div className="candidate-decision-line">
      <article className="decision"><span>当前决定</span><strong>{badge.action}</strong></article>
      <article><span>主要原因</span><p>{plainLanguage(reason)}</p></article>
      <article><span>最大风险</span><p>{plainLanguage(risk)}</p></article>
      <article><span>改变决定</span><p>{plainLanguage(change)}</p></article>
    </div>
    <footer>
      <span>系统每 10 分钟自动检查价格、资金、板块、公告、财报和放弃条件</span>
      {lowConfidence && <strong>当前把握度较低：{missingDimensions.slice(0, 2).join("、") || `信息完整度只有 ${percent(item.evidence_coverage * 100)}`}</strong>}
    </footer>
  </section>;
}

function CandidateDetail({ item, preset }: { item: Candidate; preset: string }) {
  const validation = item.strategy_validation;
  return <div className="candidate-detail">
    <CandidateDecisionBrief item={item} />
    <details className="candidate-more"><summary>查看专业数据</summary><div className="candidate-professional-stack">
      {validation && <div className={`candidate-validation ${validation.passed ? "passed" : "failed"}`}>
        <strong>{validation.passed ? `符合筛选条件 ${validation.checks.length} 项` : "暂不符合筛选条件"}</strong>
        <p>{(validation.passed ? validation.checks : validation.failures).slice(0, 5).map(plainLanguage).join(" · ")}</p>
      </div>}
      <div className="candidate-thesis"><strong>一句话原因</strong><p>{plainLanguage(item.thesis)}</p></div>
      <HistoryCheckCard item={item} />
      <div className="candidate-dimensions">{item.dimensions.map((dimension) => <div key={dimension.key} className={dimension.signal}><span>{plainLanguage(dimension.label)}</span><p>{plainLanguage(dimension.summary)}</p></div>)}</div>
    </div></details>
    <div className="candidate-ask-actions" aria-label={`${item.quote.name} 判断入口`}>
      <span>详细分析</span>
      <Link to={`/stocks?symbol=${item.quote.symbol}&from=opportunities&preset=${preset}`}>查看依据 →</Link>
    </div>
  </div>;
}

export function OpportunitiesPage() {
  const queryClient = useQueryClient();
  const [preset, setPreset] = useState("trend");
  const [leadLayer, setLeadLayer] = useState<LeadLayer>("all");
  const [expandedSymbols, setExpandedSymbols] = useState<string[]>([]);
  const query = useQuery({
    queryKey: ["opportunities", preset],
    queryFn: () => api<Result>(opportunitiesPath(preset)),
    placeholderData: (previous) => previous,
    staleTime: 90_000,
    refetchInterval: 600_000,
    refetchIntervalInBackground: true,
  });
  const strategyBoard = useQuery({
    queryKey: ["market-structure", "strategies"],
    queryFn: () => api<{ cards: StrategyBoardCard[] }>("/api/v1/market-structure/strategies"),
  });
  const presetLabel = presets.find((item) => item[0] === preset)?.[1];
  const candidateRows = useMemo(() => (query.data?.candidates ?? []).map((item) => ({ item, badge: opportunityDecision(item) })), [query.data?.candidates]);
  const layerCounts = useMemo(() => candidateRows.reduce<Record<LeadLayer, number>>((counts, row) => {
    counts.all += 1;
    counts[row.badge.layer] += 1;
    return counts;
  }, { all: 0, priority: 0, review: 0, watch_only: 0, high_risk: 0 }), [candidateRows]);
  const visibleCandidates = leadLayer === "all" ? candidateRows : candidateRows.filter((row) => row.badge.layer === leadLayer);
  const selectedLayerLabel = leadLayers.find(([key]) => key === leadLayer)?.[1] ?? "全部线索";
  const toggleExpanded = (symbol: string) => setExpandedSymbols((symbols) => symbols.includes(symbol) ? symbols.filter((item) => item !== symbol) : [...symbols, symbol]);

  return <>
    <header className="page-head opportunity-page-head"><div><h1>候选</h1></div><nav className="opportunity-head-actions" aria-label="候选页面操作"><Link className="button secondary" to="/history"><History size={16} />历史复盘</Link><a className="button secondary" href={`/api/v1/opportunities/export.csv?preset=${preset}`}><Download size={16} />导出</a></nav></header>
    <StrategyLibrary
      cards={Array.isArray(strategyBoard.data?.cards) ? strategyBoard.data.cards : []}
      active={preset}
      loading={strategyBoard.isLoading}
      failed={strategyBoard.isError}
      onPreview={(key) => queryClient.prefetchQuery({ queryKey: ["opportunities", key], queryFn: () => api<Result>(opportunitiesPath(key)), staleTime: 90_000 })}
      onSelect={(key) => { setPreset(key); setLeadLayer("all"); setExpandedSymbols([]); }}
    />
    <AsyncState loading={query.isLoading} error={query.error as Error | null}>{query.data && <>
      {query.data.available && <OpportunityQueueDesk preset={preset} presetLabel={presetLabel} candidateRows={candidateRows} layerCounts={layerCounts} />}
      {!query.data.available ? <section className="strategy-unavailable">
        <AlertTriangle size={22} />
        <div><span>暂时没有结果</span><p>{plainLanguage(query.data.unavailable_reason ?? "当前信息不足")}</p>{query.data.next_actions.map((action) => <p key={action}>· {monitoringText(action)}</p>)}<button className="text-button" onClick={() => setPreset("trend")}>看趋势延续 →</button></div>
      </section> : <>
        <section className="lead-layer-bar" aria-label="线索分层筛选">{leadLayers.map(([key, label]) => <button key={key} className={leadLayer === key ? "active" : ""} onClick={() => { setLeadLayer(key); setExpandedSymbols([]); }}><span>{label}</span><strong>{layerCounts[key]}</strong></button>)}</section>
        <section className="panel opportunity-list-panel"><div className="panel-title"><span>{selectedLayerLabel}</span><small>{visibleCandidates.length} 只</small></div>{visibleCandidates.length === 0 ? <div className="empty">当前分层没有线索。</div> : <div className="candidate-table opportunity-table compact-opportunity-list">{visibleCandidates.map(({ item, badge }, index) => {
          const expanded = expandedSymbols.includes(item.quote.symbol);
          return <article key={item.quote.symbol} className={expanded ? "expanded" : ""}>
            <button className="candidate-list-row" type="button" aria-expanded={expanded} onClick={() => toggleExpanded(item.quote.symbol)}>
              <b className="rank">{String(index + 1).padStart(2, "0")}</b>
              <span className="identity"><strong>{item.quote.name}</strong><small>{item.quote.symbol} · {item.quote.sector ?? "行业待补"}</small></span>
              <span className="candidate-mobile-summary">参考 {fmt(upsideScore(item), 0)} · {pct(item.quote.change_pct)} · 信息 {percent(item.evidence_coverage * 100)}</span>
              <span><small>参考分</small><strong>{fmt(upsideScore(item), 0)}</strong></span>
              <span><small>涨跌</small><b className={(item.quote.change_pct ?? 0) >= 0 ? "up" : "down"}>{pct(item.quote.change_pct)}</b></span>
              <div className="score-context"><span>{upsideLabel(item)}</span><em>当前 {fmt(item.base_score, 0)}</em>{item.context_penalty > 0 && <b>市场影响 -{fmt(item.context_penalty, 0)}</b>}<em>信息 {percent(item.evidence_coverage * 100)}</em></div>
              <div className={`lead-badge ${badge.tone}`}><strong>{badge.action}</strong></div>
              <ChevronDown className="candidate-toggle" size={18} aria-hidden="true" />
            </button>
            {expanded && <CandidateDetail item={item} preset={preset} />}
          </article>;
        })}</div>}</section>
      </>}
    </>}</AsyncState>
  </>;
}

function StrategyLibrary({ cards, active, loading, failed, onPreview, onSelect }: { cards: StrategyBoardCard[]; active: string; loading: boolean; failed: boolean; onPreview: (key: string) => void; onSelect: (key: string) => void }) {
  const byId = new Map(cards.map((card) => [card.id, card]));
  return <section className="strategy-library" aria-label="策略预设">
    <header><div><span>STRATEGY REGISTRY</span><strong>候选策略库</strong><small>筛选、复盘与监控共用稳定策略 ID</small></div><Link to="/history">查看策略历史表现 →</Link></header>
    {failed && <p className="capability-warning">策略摘要暂不可用，仍可逐个运行现有策略。</p>}
    <div className="strategy-card-grid">{presets.map(([key, label]) => {
      const card = byId.get(key);
      return <button key={key} type="button" className={active === key ? "active" : ""} aria-pressed={active === key} onPointerEnter={() => onPreview(key)} onFocus={() => onPreview(key)} onClick={() => onSelect(key)}>
        <span><em>{card?.category ?? "策略"}</em><b>{card ? `${card.hit_count} 命中` : loading ? "计算中" : "可运行"}</b></span>
        <strong>{label}</strong>
        <p>{card?.entry_signal ?? "点击运行并查看当前触发条件"}</p>
        <small>退出：{card?.exit_signal ?? "以候选失效条件为准"}</small>
        <footer><i>置信 {card ? percent(card.confidence * 100) : "待计算"}</i><b>{card?.top_candidate?.name ?? "暂无首选"}</b></footer>
      </button>;
    })}</div>
  </section>;
}
