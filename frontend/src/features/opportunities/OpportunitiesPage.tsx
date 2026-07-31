import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, ChevronDown, Download } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { AsyncState } from "../../components/AsyncState";
import { api, fmt, pct, percent, type Candidate, type OpportunityDimension } from "../../lib/api";

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
};

const presets = [
  ["trend", "趋势延续"],
  ["volume_breakout", "放量突破"],
  ["value_rebound", "低估反弹"],
  ["oversold_repair", "超跌修复"],
];

const leadLayers = [
  ["all", "全部"],
  ["priority", "优先"],
  ["review", "候选"],
  ["watch_only", "观察"],
  ["high_risk", "高风险"],
] as const;

type LeadLayer = typeof leadLayers[number][0];


type CandidateRow = { item: Candidate; badge: ReturnType<typeof leadBadge> };

type QueuePlan = { tone: "positive" | "caution" | "negative" | "neutral"; route: string; };

function upsideScore(item: Candidate) {
  return item.upside_score ?? item.score;
}

function upsideLabel(item: Candidate) {
  return item.upside_label || (upsideScore(item) >= 72 ? "大概率候选" : "待确认");
}

function opportunityAskHref(item: Candidate, preset: string, question: string) {
  return `/ask?symbol=${encodeURIComponent(item.quote.symbol)}&name=${encodeURIComponent(item.quote.name)}&from=opportunities&preset=${encodeURIComponent(preset)}&question=${encodeURIComponent(question)}`;
}

function upgradeQuestion(item: Candidate, presetLabel: string | undefined) {
  return `${item.quote.name}这条${presetLabel ?? "机会"}线索能升级吗`;
}

function buildQueuePlan(counts: Record<LeadLayer, number>): QueuePlan {
  if (counts.all === 0) return { tone: "neutral", route: "无候选" };
  if (counts.priority > 0) return { tone: "positive", route: "优先" };
  if (counts.high_risk >= Math.max(2, Math.ceil(counts.all * 0.5))) return { tone: "negative", route: "风险偏高" };
  if (counts.review > 0) return { tone: "caution", route: "候选" };
  return { tone: "neutral", route: "观察" };
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
  const topRow = candidateRows.reduce<CandidateRow | undefined>((best, row) => (!best || upsideScore(row.item) > upsideScore(best.item) ? row : best), undefined);
  const plan = buildQueuePlan(layerCounts);
  const topHref = topRow ? `/stocks?symbol=${topRow.item.quote.symbol}&from=opportunities&preset=${preset}` : "";
  const reviewTotal = layerCounts.priority + layerCounts.review;
  const riskTotal = layerCounts.watch_only + layerCounts.high_risk;

  return <section className={`panel opportunity-queue ${plan.tone}`} aria-label="机会线索队列">
    <div className="queue-gate">
      <span>机会</span>
      <strong>{plan.route}</strong>
    </div>
    <div className="queue-metrics" aria-label="线索队列统计">
      <div><span>策略</span><strong>{presetLabel ?? preset}</strong></div>
      <div><span>候选</span><strong>{layerCounts.all}</strong></div>
      <div><span>可看</span><strong>{reviewTotal}</strong></div>
      <div><span>谨慎</span><strong>{riskTotal}</strong></div>
    </div>
    {topRow ? <Link className="queue-top-card" to={topHref}>
      <small>最可能上涨</small>
      <strong>{topRow.item.quote.name}</strong>
      <span>{topRow.item.quote.symbol} · {upsideLabel(topRow.item)} · 上涨 {fmt(upsideScore(topRow.item), 0)}分 · 证据 {percent(topRow.item.evidence_coverage * 100)}</span>
    </Link> : <div className="queue-top-card empty-card"><small>首选</small><strong>暂无候选</strong><span>切换条件或等待刷新</span></div>}
    {topRow ? <nav className="queue-ask-bridge" aria-label="第一候选快捷动作">
      <Link to={topHref}>打开个股</Link>
      <Link to={opportunityAskHref(topRow.item, preset, upgradeQuestion(topRow.item, presetLabel))}>问升级</Link>
      <Link to={opportunityAskHref(topRow.item, preset, `${topRow.item.quote.name}这条线索主要风险是什么`)}>问风险</Link>
    </nav> : null}
  </section>;
}

function leadBadge(item: Candidate): { key: LeadLayer; label: string; tone: string; reason: string } {
  const history = item.history_check;
  const likelyScore = upsideScore(item);
  const hasHistoryRisk = Boolean(history?.risk_flags.length) || (history?.score != null && history.score < 45);
  const historyConfirmed = !history || (history.available && history.score != null && history.score >= 65 && history.risk_flags.length === 0);
  if (hasHistoryRisk) {
    return { key: "high_risk", label: "高风险", tone: "negative", reason: "历史K线出现追高、波动或回撤警报" };
  }
  if (item.evidence_coverage < 0.65 || item.risk_flags.length >= 3 || item.context_penalty >= 15) {
    return { key: "high_risk", label: "高风险", tone: "negative", reason: "证据或市场环境偏弱" };
  }
  if (likelyScore >= 75 && item.evidence_coverage >= 0.75 && item.context_penalty === 0 && historyConfirmed) {
    return { key: "priority", label: "优先", tone: "positive", reason: "上涨概率、历史K线和证据覆盖靠前" };
  }
  if (likelyScore < 60 || item.context_penalty > 0) {
    return { key: "watch_only", label: "观察", tone: "caution", reason: "市场或风险收益压低上涨概率" };
  }
  return { key: "review", label: "候选", tone: "neutral", reason: "需要补齐关键证据" };
}

function HistoryCheckCard({ item }: { item: Candidate }) {
  const history = item.history_check;
  if (!history) return null;
  return <div className={`candidate-history ${history.available ? "available" : "missing"}`}>
    <div>
      <span>历史K线</span>
      <strong>{history.available ? `${fmt(history.score, 0)}/100` : "待补K线"}</strong>
    </div>
    <p>{history.summary}</p>
    <dl>
      <div><dt>20日趋势</dt><dd>{pct(history.trend_20d_pct)}</dd></div>
      <div><dt>60日趋势</dt><dd>{pct(history.trend_60d_pct)}</dd></div>
      <div><dt>MA20偏离</dt><dd>{pct(history.ma20_gap_pct)}</dd></div>
      <div><dt>波动</dt><dd>{percent(history.volatility_20d)}</dd></div>
      <div><dt>回撤</dt><dd>{history.max_drawdown_60d == null ? "—" : `-${fmt(history.max_drawdown_60d, 1)}%`}</dd></div>
      <div><dt>量能</dt><dd>{history.volume_ratio_20d == null ? "—" : `${fmt(history.volume_ratio_20d, 1)}x`}</dd></div>
    </dl>
    <small>{history.evidence.join(" · ")}</small>
  </div>;
}

function CandidatePotential({ item }: { item: Candidate }) {
  const drivers = item.upside_drivers ?? [];
  const risks = item.upside_risks ?? [];
  return <div className="candidate-potential">
    <div className="potential-score">
      <span>上涨评分</span>
      <strong>{fmt(upsideScore(item), 0)}</strong>
      <small>{upsideLabel(item)}</small>
    </div>
    <div>
      <b>为什么可能涨</b>
      <p>{item.upside_summary || "按趋势、资金、风险收益和估值空间综合排序。"}</p>
      {drivers.length > 0 && <div className="potential-tags">{drivers.slice(0, 4).map((driver) => <i key={driver}>{driver}</i>)}</div>}
    </div>
    <div>
      <b>还差什么确认</b>
      <p>{risks.slice(0, 3).join("；") || "继续核验催化和板块共振。"}</p>
    </div>
  </div>;
}

function CandidateDetail({ item, preset, presetLabel }: { item: Candidate; preset: string; presetLabel: string | undefined }) {
  return <div className="candidate-detail">
    <CandidatePotential item={item} />
    <div className="candidate-thesis"><strong>线索理由</strong><p>{item.thesis}</p></div>
    <HistoryCheckCard item={item} />
    <details className="candidate-more"><summary>更多依据</summary><div className="candidate-dimensions">{item.dimensions.map((dimension) => <div key={dimension.key} className={dimension.signal}><span>{dimension.label}</span><p>{dimension.summary}</p></div>)}</div></details>
    <div className="candidate-playbook"><div><strong>失效条件</strong>{item.invalidation.map((rule) => <p key={rule}>× {rule}</p>)}</div><div><strong>下一步</strong>{item.next_actions.map((action) => <p key={action}>→ {action}</p>)}</div></div>
    <div className="risk-tags">{item.risk_flags.map((flag) => <i key={flag}>{flag}</i>)}</div>
    <div className="candidate-ask-actions" aria-label={`${item.quote.name} 线索快捷动作`}>
      <Link to={`/stocks?symbol=${item.quote.symbol}&from=opportunities&preset=${preset}`}>看个股 →</Link>
      <Link to={opportunityAskHref(item, preset, upgradeQuestion(item, presetLabel))}>问线索能否升级 →</Link>
      <Link to={opportunityAskHref(item, preset, `${item.quote.name}这条线索主要风险是什么`)}>问风险 →</Link>
    </div>
  </div>;
}

export function OpportunitiesPage() {
  const [preset, setPreset] = useState("trend");
  const [leadLayer, setLeadLayer] = useState<LeadLayer>("all");
  const [expandedSymbols, setExpandedSymbols] = useState<string[]>([]);
  const query = useQuery({
    queryKey: ["opportunities", preset],
    queryFn: () => api<Result>(`/api/v1/opportunities?preset=${preset}`),
  });
  const presetLabel = presets.find((item) => item[0] === preset)?.[1];
  const candidateRows = useMemo(() => (query.data?.candidates ?? []).map((item) => ({ item, badge: leadBadge(item) })), [query.data?.candidates]);
  const layerCounts = useMemo(() => candidateRows.reduce<Record<LeadLayer, number>>((counts, row) => {
    counts.all += 1;
    counts[row.badge.key] += 1;
    return counts;
  }, { all: 0, priority: 0, review: 0, watch_only: 0, high_risk: 0 }), [candidateRows]);
  const visibleCandidates = leadLayer === "all" ? candidateRows : candidateRows.filter((row) => row.badge.key === leadLayer);
  const selectedLayerLabel = leadLayers.find(([key]) => key === leadLayer)?.[1] ?? "全部线索";
  const toggleExpanded = (symbol: string) => setExpandedSymbols((symbols) => symbols.includes(symbol) ? symbols.filter((item) => item !== symbol) : [...symbols, symbol]);

  return <>
    <header className="page-head"><div><h1>机会</h1></div><a className="button secondary" href={`/api/v1/opportunities/export.csv?preset=${preset}`}><Download size={16} />导出</a></header>
    <div className="preset-bar" aria-label="策略预设">{presets.map(([key, label]) => <button key={key} className={preset === key ? "active" : ""} onClick={() => { setPreset(key); setLeadLayer("all"); setExpandedSymbols([]); }}>{label}</button>)}</div>
    <AsyncState loading={query.isLoading} error={query.error as Error | null}>{query.data && <>
      {query.data.available && <OpportunityQueueDesk preset={preset} presetLabel={presetLabel} candidateRows={candidateRows} layerCounts={layerCounts} />}
      {!query.data.available ? <section className="strategy-unavailable">
        <AlertTriangle size={22} />
        <div><span>暂时没有结果</span><p>{query.data.unavailable_reason}</p>{query.data.next_actions.map((action) => <p key={action}>· {action}</p>)}<button className="text-button" onClick={() => setPreset("trend")}>看趋势延续 →</button></div>
      </section> : <>
        <section className="lead-layer-bar" aria-label="线索分层筛选">{leadLayers.map(([key, label]) => <button key={key} className={leadLayer === key ? "active" : ""} onClick={() => { setLeadLayer(key); setExpandedSymbols([]); }}><span>{label}</span><strong>{layerCounts[key]}</strong></button>)}</section>
        <section className="panel"><div className="panel-title"><span>{selectedLayerLabel}</span><small>{visibleCandidates.length} 只</small></div>{visibleCandidates.length === 0 ? <div className="empty">当前分层没有线索。</div> : <div className="candidate-table opportunity-table compact-opportunity-list">{visibleCandidates.map(({ item, badge }, index) => {
          const expanded = expandedSymbols.includes(item.quote.symbol);
          return <article key={item.quote.symbol} className={expanded ? "expanded" : ""}>
            <button className="candidate-list-row" type="button" aria-expanded={expanded} onClick={() => toggleExpanded(item.quote.symbol)}>
              <b className="rank">{String(index + 1).padStart(2, "0")}</b>
              <span className="identity"><strong>{item.quote.name}</strong><small>{item.quote.symbol} · {item.quote.sector ?? "行业待补"}</small></span>
              <span><small>上涨分</small><strong>{fmt(upsideScore(item), 0)}</strong></span>
              <span><small>涨跌</small><b className={(item.quote.change_pct ?? 0) >= 0 ? "up" : "down"}>{pct(item.quote.change_pct)}</b></span>
              <div className="score-context"><span>{upsideLabel(item)}</span><em>当前 {fmt(item.base_score, 0)}</em>{item.context_penalty > 0 && <b>环境 -{fmt(item.context_penalty, 0)}</b>}<em>证据 {percent(item.evidence_coverage * 100)}</em></div>
              <div className={`lead-badge ${badge.tone}`}><strong>{badge.label}</strong></div>
              <ChevronDown className="candidate-toggle" size={18} aria-hidden="true" />
            </button>
            {expanded && <CandidateDetail item={item} preset={preset} presetLabel={presetLabel} />}
          </article>;
        })}</div>}</section>
      </>}
    </>}</AsyncState>
  </>;
}
