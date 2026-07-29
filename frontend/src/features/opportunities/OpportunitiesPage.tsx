import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, ChevronDown, Download, Filter, ListChecks } from "lucide-react";
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
  ["all", "全部线索"],
  ["priority", "优先复核"],
  ["review", "待复核"],
  ["watch_only", "可能暂不参与"],
  ["high_risk", "高风险线索"],
] as const;

type LeadLayer = typeof leadLayers[number][0];


type CandidateRow = { item: Candidate; badge: ReturnType<typeof leadBadge> };

type QueuePlan = { tone: "positive" | "caution" | "negative" | "neutral"; route: string; steps: string[] };

function opportunityAskHref(item: Candidate, preset: string, question: string) {
  return `/ask?symbol=${encodeURIComponent(item.quote.symbol)}&name=${encodeURIComponent(item.quote.name)}&from=opportunities&preset=${encodeURIComponent(preset)}&question=${encodeURIComponent(question)}`;
}

function upgradeQuestion(item: Candidate, presetLabel: string | undefined) {
  return `${item.quote.name}这条${presetLabel ?? "机会"}线索能升级吗`;
}

function buildQueuePlan(counts: Record<LeadLayer, number>): QueuePlan {
  if (counts.all === 0) {
    return {
      tone: "neutral",
      route: "当前策略没有线索，不为了交易而交易",
      steps: ["先切换策略或回到大盘作战台", "等待成交额、趋势或风险收益重新满足规则"],
    };
  }
  if (counts.priority > 0) {
    return {
      tone: "positive",
      route: "先复核优先线索，再扫待复核",
      steps: ["第一批只打开优先复核线索", "确认板块/题材是否仍在主线", "进入个股页后以 FINAL GATE 决定是否参与"],
    };
  }
  if (counts.high_risk >= Math.max(2, Math.ceil(counts.all * 0.5))) {
    return {
      tone: "negative",
      route: "高风险占比高，今天先降级观察",
      steps: ["先看高风险标签是否来自环境扣分", "只保留少量待复核样本", "不要把线索排序当作参与建议"],
    };
  }
  if (counts.review > 0) {
    return {
      tone: "caution",
      route: "没有优先线索，只看待复核",
      steps: ["先补齐证据覆盖缺口", "只处理板块配合更好的个股", "个股页若仍无确认就保留观察"],
    };
  }
  return {
    tone: "neutral",
    route: "线索偏弱，只做观察名单清理",
    steps: ["先过滤可能暂不参与与高风险线索", "等待市场环境或个股证据改善", "必要时回到大盘路线重新选策略"],
  };
}

function OpportunityQueueDesk({
  preset,
  presetLabel,
  candidateRows,
  layerCounts,
  onSelectLayer,
}: {
  preset: string;
  presetLabel: string | undefined;
  candidateRows: CandidateRow[];
  layerCounts: Record<LeadLayer, number>;
  onSelectLayer: (layer: LeadLayer) => void;
}) {
  const topRow = candidateRows.reduce<CandidateRow | undefined>((best, row) => (!best || row.item.score > best.item.score ? row : best), undefined);
  const plan = buildQueuePlan(layerCounts);
  const topHref = topRow ? `/stocks?symbol=${topRow.item.quote.symbol}&from=opportunities&preset=${preset}` : "";
  const reviewTotal = layerCounts.priority + layerCounts.review;
  const riskTotal = layerCounts.watch_only + layerCounts.high_risk;

  return <section className={`panel opportunity-queue ${plan.tone}`} aria-label="机会线索队列">
    <div className="queue-gate">
      <span><ListChecks size={14} />QUEUE GATE</span>
      <strong>线索队列</strong>
      <p>{plan.route}</p>
    </div>
    <div className="queue-metrics" aria-label="线索队列统计">
      <div><span>策略</span><strong>{presetLabel ?? preset}</strong></div>
      <div><span>候选</span><strong>{layerCounts.all}</strong></div>
      <div><span>需复核</span><strong>{reviewTotal}</strong></div>
      <div><span>先观察</span><strong>{riskTotal}</strong></div>
    </div>
    {topRow ? <Link className="queue-top-card" to={topHref}>
      <small>第一张复核单</small>
      <strong>{topRow.item.quote.name}</strong>
      <span>{topRow.item.quote.symbol} · 最终分 {fmt(topRow.item.score, 0)} · 证据 {percent(topRow.item.evidence_coverage * 100)} · {topRow.badge.label}</span>
    </Link> : <div className="queue-top-card empty-card"><small>第一张复核单</small><strong>暂无候选</strong><span>切换策略或等待下一次行情刷新</span></div>}
    {topRow ? <nav className="queue-ask-bridge" aria-label="第一候选快捷动作">
      <Link to={topHref}>打开 FINAL GATE</Link>
      <Link to={opportunityAskHref(topRow.item, preset, upgradeQuestion(topRow.item, presetLabel))}>问能否升级</Link>
      <Link to={opportunityAskHref(topRow.item, preset, `${topRow.item.quote.name}这条线索主要风险是什么`)}>问主要风险</Link>
    </nav> : null}
    <div className="queue-route">
      <strong>今日处理路线</strong>
      <ol>{plan.steps.map((step) => <li key={step}>{step}</li>)}</ol>
    </div>
    <div className="queue-shortcuts" aria-label="队列快捷筛选">
      <button aria-label={`队列筛选优先线索 ${layerCounts.priority}`} onClick={() => onSelectLayer("priority")}>只看优先复核 <b>{layerCounts.priority}</b></button>
      <button aria-label={`队列筛选待复核线索 ${layerCounts.review}`} onClick={() => onSelectLayer("review")}>只看待复核 <b>{layerCounts.review}</b></button>
      <button aria-label={`队列筛选高风险线索 ${layerCounts.high_risk}`} onClick={() => onSelectLayer("high_risk")}>只看高风险 <b>{layerCounts.high_risk}</b></button>
    </div>
  </section>;
}

function leadBadge(item: Candidate): { key: LeadLayer; label: string; tone: string; reason: string } {
  const history = item.history_check;
  const hasHistoryRisk = Boolean(history?.risk_flags.length) || (history?.score != null && history.score < 45);
  const historyConfirmed = !history || (history.available && history.score != null && history.score >= 65 && history.risk_flags.length === 0);
  if (hasHistoryRisk) {
    return { key: "high_risk", label: "高风险线索", tone: "negative", reason: "历史K线出现追高、波动或回撤警报，先降级复核" };
  }
  if (item.evidence_coverage < 0.65 || item.risk_flags.length >= 3 || item.context_penalty >= 15) {
    return { key: "high_risk", label: "高风险线索", tone: "negative", reason: "证据或环境约束偏弱，优先看失效条件" };
  }
  if (item.score >= 75 && item.evidence_coverage >= 0.75 && item.context_penalty === 0 && historyConfirmed) {
    return { key: "priority", label: "优先复核", tone: "positive", reason: "线索质量和历史K线同时通过，但仍需个股页确认" };
  }
  if (item.score < 60 || item.context_penalty > 0) {
    return { key: "watch_only", label: "可能暂不参与", tone: "caution", reason: "市场或风险收益可能压低最终建议" };
  }
  return { key: "review", label: "待复核", tone: "neutral", reason: "进入证据账本后再定是否参与" };
}

function HistoryCheckCard({ item }: { item: Candidate }) {
  const history = item.history_check;
  if (!history) return null;
  return <div className={`candidate-history ${history.available ? "available" : "missing"}`}>
    <div>
      <span>HISTORY CHECK · 历史K线</span>
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

function CandidateDetail({ item, preset, presetLabel }: { item: Candidate; preset: string; presetLabel: string | undefined }) {
  return <div className="candidate-detail">
    <div className="candidate-thesis"><strong>线索理由</strong><p>{item.thesis}</p></div>
    <HistoryCheckCard item={item} />
    <div className="candidate-dimensions">{item.dimensions.map((dimension) => <div key={dimension.key} className={dimension.signal}><span>{dimension.label}</span><p>{dimension.summary}</p></div>)}</div>
    <div className="candidate-playbook"><div><strong>失效条件</strong>{item.invalidation.map((rule) => <p key={rule}>× {rule}</p>)}</div><div><strong>下一步</strong>{item.next_actions.map((action) => <p key={action}>→ {action}</p>)}</div></div>
    <div className="risk-tags">{item.risk_flags.map((flag) => <i key={flag}>{flag}</i>)}</div>
    <div className="candidate-ask-actions" aria-label={`${item.quote.name} 线索快捷动作`}>
      <Link to={`/stocks?symbol=${item.quote.symbol}&from=opportunities&preset=${preset}`}>复核是否参与 →</Link>
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
    <header className="page-head"><div><p className="eyebrow">OPPORTUNITIES / 研究线索</p><h1>先筛候选线索，<br /><em>再复核是否参与。</em></h1></div><a className="button secondary" href={`/api/v1/opportunities/export.csv?preset=${preset}`}><Download size={16} />导出当前结果</a></header>
    <div className="preset-bar" aria-label="策略预设">{presets.map(([key, label]) => <button key={key} className={preset === key ? "active" : ""} onClick={() => { setPreset(key); setLeadLayer("all"); setExpandedSymbols([]); }}>{label}</button>)}</div>
    <AsyncState loading={query.isLoading} error={query.error as Error | null}>{query.data && <>
      <section className="strategy-contract">
        <div><Filter size={16} /><span>当前线索策略</span><strong>{presetLabel}</strong></div>
        <ul>{query.data.rules.map((rule) => <li key={rule}>{rule}</li>)}</ul>
      </section>
      <section className="opportunity-boundary" aria-label="机会页说明">
        这里筛出的是候选线索，不是参与建议；是否参与以个股证据账本为准。
      </section>
      {query.data.available && <OpportunityQueueDesk preset={preset} presetLabel={presetLabel} candidateRows={candidateRows} layerCounts={layerCounts} onSelectLayer={setLeadLayer} />}
      <section className="panel opportunity-diagnostics">
        <div className="panel-title"><span>策略诊断</span><small>{query.data.summary || "先看这项策略是否适合今天使用"}</small></div>
        <div className="opportunity-diagnostic-grid">{query.data.diagnostics.map((item) => <article key={item.key} className={item.signal}>
          <header><span>{item.label}</span><strong>{item.score == null ? "缺数据" : `${fmt(item.score, 0)}/100`}</strong></header>
          <p>{item.summary}</p>
          <small>{item.evidence.join(" · ")}</small>
        </article>)}</div>
      </section>
      {!query.data.available ? <section className="strategy-unavailable">
        <AlertTriangle size={22} />
        <div><span>这项线索策略暂时不能可靠运行</span><p>{query.data.unavailable_reason}</p>{query.data.next_actions.map((action) => <p key={action}>· {action}</p>)}<button className="text-button" onClick={() => setPreset("trend")}>改看趋势延续 →</button></div>
      </section> : <>
        <section className="funnel"><div><span>全市场</span><strong>{query.data.funnel.universe}</strong></div><i>→</i><div><span>未通过规则</span><strong>{query.data.funnel.excluded}</strong></div><i>→</i><div className="accent"><span>待复核线索</span><strong>{query.data.funnel.ranked}</strong></div></section>
        <section className="panel opportunity-actions"><div className="panel-title"><span>线索处理清单</span><small>从短名单变成可复盘的复核动作</small></div><ol>{query.data.next_actions.map((action) => <li key={action}>{action}</li>)}</ol></section>
        <section className="lead-layer-bar" aria-label="线索分层筛选">{leadLayers.map(([key, label]) => <button key={key} className={leadLayer === key ? "active" : ""} onClick={() => { setLeadLayer(key); setExpandedSymbols([]); }}><span>{label}</span><strong>{layerCounts[key]}</strong></button>)}</section>
        <section className="panel"><div className="panel-title"><span>{selectedLayerLabel} · 点击股票展开详情</span><small>默认收成列表，最终是否参与看个股证据</small></div>{visibleCandidates.length === 0 ? <div className="empty">当前分层没有线索，切回全部线索继续查看。</div> : <div className="candidate-table opportunity-table compact-opportunity-list">{visibleCandidates.map(({ item, badge }, index) => {
          const expanded = expandedSymbols.includes(item.quote.symbol);
          return <article key={item.quote.symbol} className={expanded ? "expanded" : ""}>
            <button className="candidate-list-row" type="button" aria-expanded={expanded} onClick={() => toggleExpanded(item.quote.symbol)}>
              <b className="rank">{String(index + 1).padStart(2, "0")}</b>
              <span className="identity"><strong>{item.quote.name}</strong><small>{item.quote.symbol} · {item.quote.sector ?? "行业待补"}</small></span>
              <span><small>最终分</small><strong>{fmt(item.score, 0)}</strong></span>
              <span><small>涨跌</small><b className={(item.quote.change_pct ?? 0) >= 0 ? "up" : "down"}>{pct(item.quote.change_pct)}</b></span>
              <div className="score-context"><span>基础 {fmt(item.base_score, 0)}</span>{item.context_penalty > 0 && <b>环境 -{fmt(item.context_penalty, 0)}</b>}<em>证据 {percent(item.evidence_coverage * 100)}</em></div>
              <div className={`lead-badge ${badge.tone}`}><strong>{badge.label}</strong><span>{badge.reason}</span></div>
              <ChevronDown className="candidate-toggle" size={18} aria-hidden="true" />
            </button>
            {expanded && <CandidateDetail item={item} preset={preset} presetLabel={presetLabel} />}
          </article>;
        })}</div>}</section>
      </>}
    </>}</AsyncState>
  </>;
}
