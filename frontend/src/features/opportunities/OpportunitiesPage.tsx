import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Download, Filter } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { AsyncState } from "../../components/AsyncState";
import { api, fmt, pct, percent, type Candidate } from "../../lib/api";

type Result = {
  preset: string;
  available: boolean;
  unavailable_reason: string | null;
  rules: string[];
  funnel: Record<string, number>;
  candidates: Candidate[];
  excluded: { reasons: string[] }[];
};

const presets = [
  ["trend", "趋势延续"],
  ["sector_improving", "板块改善"],
  ["capital_confirmed", "资金确认"],
  ["oversold_rebound", "超跌观察"],
];

export function OpportunitiesPage() {
  const [preset, setPreset] = useState("trend");
  const query = useQuery({
    queryKey: ["opportunities", preset],
    queryFn: () => api<Result>(`/api/v1/opportunities?preset=${preset}`),
  });
  const presetLabel = presets.find((item) => item[0] === preset)?.[1];

  return <>
    <header className="page-head"><div><p className="eyebrow">OPPORTUNITIES / 机会漏斗</p><h1>先看为什么入选，<br /><em>再决定是否研究。</em></h1></div><a className="button secondary" href={`/api/v1/opportunities/export.csv?preset=${preset}`}><Download size={16} />导出当前结果</a></header>
    <div className="preset-bar" aria-label="策略预设">{presets.map(([key, label]) => <button key={key} className={preset === key ? "active" : ""} onClick={() => setPreset(key)}>{label}</button>)}</div>
    <AsyncState loading={query.isLoading} error={query.error as Error | null}>{query.data && <>
      <section className="strategy-contract">
        <div><Filter size={16} /><span>当前策略</span><strong>{presetLabel}</strong></div>
        <ul>{query.data.rules.map((rule) => <li key={rule}>{rule}</li>)}</ul>
      </section>
      {!query.data.available ? <section className="strategy-unavailable">
        <AlertTriangle size={22} />
        <div><span>这项策略暂时不能可靠运行</span><p>{query.data.unavailable_reason}</p><button className="text-button" onClick={() => setPreset("trend")}>改看可用的趋势策略 →</button></div>
      </section> : <>
        <section className="funnel"><div><span>全市场</span><strong>{query.data.funnel.universe}</strong></div><i>→</i><div><span>未通过规则</span><strong>{query.data.funnel.excluded}</strong></div><i>→</i><div className="accent"><span>进入研究</span><strong>{query.data.funnel.ranked}</strong></div></section>
        <section className="panel"><div className="panel-title"><span>按研究优先级排序</span><small>最终分已计入市场环境扣分</small></div><div className="candidate-table">{query.data.candidates.map((item, index) => <article key={item.quote.symbol}>
          <b className="rank">{String(index + 1).padStart(2, "0")}</b>
          <span className="identity"><strong>{item.quote.name}</strong><small>{item.quote.symbol} · {item.quote.sector ?? "行业待补"}</small></span>
          <span><small>最终分</small><strong>{fmt(item.score, 0)}</strong></span>
          <span><small>涨跌</small><b className={(item.quote.change_pct ?? 0) >= 0 ? "up" : "down"}>{pct(item.quote.change_pct)}</b></span>
          <div className="score-context"><span>基础 {fmt(item.base_score, 0)}</span>{item.context_penalty > 0 && <b>环境 -{fmt(item.context_penalty, 0)}</b>}<em>证据 {percent(item.evidence_coverage * 100)}</em></div>
          <div className="risk-tags">{item.risk_flags.slice(0, 4).map((flag) => <i key={flag}>{flag}</i>)}</div>
          <Link className="text-link" to={`/stocks?symbol=${item.quote.symbol}`}>打开证据账本 →</Link>
        </article>)}</div></section>
      </>}
    </>}</AsyncState>
  </>;
}
