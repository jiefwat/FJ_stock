import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Download, Filter } from "lucide-react";
import { useState } from "react";
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

function leadBadge(item: Candidate) {
  if (item.evidence_coverage < 0.65 || item.risk_flags.length >= 3 || item.context_penalty >= 15) {
    return { label: "高风险线索", tone: "negative", reason: "证据或环境约束偏弱，优先看失效条件" };
  }
  if (item.score >= 75 && item.evidence_coverage >= 0.75 && item.context_penalty === 0) {
    return { label: "优先复核", tone: "positive", reason: "线索质量较高，但仍需个股页确认" };
  }
  if (item.score < 60 || item.context_penalty > 0) {
    return { label: "可能暂不参与", tone: "caution", reason: "市场或风险收益可能压低最终建议" };
  }
  return { label: "待复核", tone: "neutral", reason: "进入证据账本后再定是否参与" };
}

export function OpportunitiesPage() {
  const [preset, setPreset] = useState("trend");
  const query = useQuery({
    queryKey: ["opportunities", preset],
    queryFn: () => api<Result>(`/api/v1/opportunities?preset=${preset}`),
  });
  const presetLabel = presets.find((item) => item[0] === preset)?.[1];

  return <>
    <header className="page-head"><div><p className="eyebrow">OPPORTUNITIES / 研究线索</p><h1>先筛候选线索，<br /><em>再复核是否参与。</em></h1></div><a className="button secondary" href={`/api/v1/opportunities/export.csv?preset=${preset}`}><Download size={16} />导出当前结果</a></header>
    <div className="preset-bar" aria-label="策略预设">{presets.map(([key, label]) => <button key={key} className={preset === key ? "active" : ""} onClick={() => setPreset(key)}>{label}</button>)}</div>
    <AsyncState loading={query.isLoading} error={query.error as Error | null}>{query.data && <>
      <section className="strategy-contract">
        <div><Filter size={16} /><span>当前线索策略</span><strong>{presetLabel}</strong></div>
        <ul>{query.data.rules.map((rule) => <li key={rule}>{rule}</li>)}</ul>
      </section>
      <section className="opportunity-boundary" aria-label="机会页说明">
        这里筛出的是候选线索，不是参与建议；是否参与以个股证据账本为准。
      </section>
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
        <section className="panel"><div className="panel-title"><span>按复核优先级排序</span><small>最终分只是线索排序，是否参与看个股证据</small></div><div className="candidate-table opportunity-table">{query.data.candidates.map((item, index) => {
          const badge = leadBadge(item);
          return <article key={item.quote.symbol}>
          <b className="rank">{String(index + 1).padStart(2, "0")}</b>
          <span className="identity"><strong>{item.quote.name}</strong><small>{item.quote.symbol} · {item.quote.sector ?? "行业待补"}</small></span>
          <span><small>最终分</small><strong>{fmt(item.score, 0)}</strong></span>
          <span><small>涨跌</small><b className={(item.quote.change_pct ?? 0) >= 0 ? "up" : "down"}>{pct(item.quote.change_pct)}</b></span>
          <div className="score-context"><span>基础 {fmt(item.base_score, 0)}</span>{item.context_penalty > 0 && <b>环境 -{fmt(item.context_penalty, 0)}</b>}<em>证据 {percent(item.evidence_coverage * 100)}</em></div>
          <div className={`lead-badge ${badge.tone}`}><strong>{badge.label}</strong><span>{badge.reason}</span></div>
          <div className="candidate-thesis"><strong>线索理由</strong><p>{item.thesis}</p></div>
          <div className="candidate-dimensions">{item.dimensions.map((dimension) => <div key={dimension.key} className={dimension.signal}><span>{dimension.label}</span><p>{dimension.summary}</p></div>)}</div>
          <div className="candidate-playbook"><div><strong>失效条件</strong>{item.invalidation.map((rule) => <p key={rule}>× {rule}</p>)}</div><div><strong>下一步</strong>{item.next_actions.map((action) => <p key={action}>→ {action}</p>)}</div></div>
          <div className="risk-tags">{item.risk_flags.map((flag) => <i key={flag}>{flag}</i>)}</div>
          <Link className="text-link" to={`/stocks?symbol=${item.quote.symbol}&from=opportunities&preset=${preset}`}>复核是否参与 →</Link>
        </article>;
        })}</div></section>
      </>}
    </>}</AsyncState>
  </>;
}
