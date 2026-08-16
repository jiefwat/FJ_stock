import { useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarClock, CheckCircle2, Gauge, History, Scale } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { AsyncState } from "../../components/AsyncState";
import { api, fmt, pct, type RecommendationHistoryResult, type RecommendationPerformancePick } from "../../lib/api";
import { plainLanguage } from "../../lib/plainLanguage";

const presets = [
  ["trend", "趋势延续"],
  ["volume_breakout", "放量突破"],
  ["capital_confirmed", "资金确认"],
  ["sector_momentum", "板块共振"],
  ["pullback_support", "回踩企稳"],
] as const;

function historyQueryOptions(preset: string) {
  return {
    queryKey: ["recommendation-history", preset],
    queryFn: () => api<RecommendationHistoryResult>(`/api/v1/recommendation-history?preset=${preset}&limit=90`),
    staleTime: 5 * 60_000,
  };
}

function rate(value: number | null) {
  return value == null ? "样本积累中" : `${(value * 100).toFixed(0)}%`;
}

function returnTone(value: number | null) {
  if (value == null || value === 0) return "flat";
  return value > 0 ? "positive" : "negative";
}

function shortDate(value: string) {
  const date = new Date(`${value}T00:00:00`);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleDateString("zh-CN", { month: "2-digit", day: "2-digit", weekday: "short" });
}

function observedTime(value: string | null) {
  if (!value) return "尚无观察价";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false });
}

function statusLabel(item: RecommendationPerformancePick) {
  if (item.status === "evaluated") return "20日已验收";
  if (item.status === "validating") return `已走 ${item.observed_sessions} 日`;
  if (item.status === "missing") return "行情待补";
  return item.observed_sessions === 0 ? "今日建档" : `跟踪第 ${item.observed_sessions} 日`;
}

function ReturnCell({ label, value }: { label: string; value: number | null }) {
  return <div className={`history-return-cell ${returnTone(value)}`}><span>{label}</span><strong>{pct(value)}</strong></div>;
}

function PerformanceRow({ item }: { item: RecommendationPerformancePick }) {
  return <article className="history-pick-card">
    <div className="history-pick-identity">
      <b>{String(item.rank).padStart(2, "0")}</b>
      <div><Link to={`/stocks?symbol=${encodeURIComponent(item.symbol)}#stock-final-gate`}>{item.name}</Link><small>{item.symbol} · {item.sector ?? "板块待补"}</small></div>
      <span className={item.status}>{statusLabel(item)}</span>
    </div>
    <div className="history-entry-cell"><span>入选</span><strong>{fmt(item.entry_price)}</strong><small>参考 {fmt(item.score, 0)} · 信息 {(item.evidence_coverage * 100).toFixed(0)}%</small></div>
    <div className="history-horizon-tape" aria-label={`${item.name} 固定周期表现`}>
      <ReturnCell label="T+1" value={item.return_1d} />
      <ReturnCell label="T+5" value={item.return_5d} />
      <ReturnCell label="T+20" value={item.return_20d} />
      <ReturnCell label="至今" value={item.current_return} />
    </div>
    <div className={`history-excess-cell ${returnTone(item.excess_20d_return ?? item.current_excess_return)}`}>
      <span>{item.excess_20d_return == null ? "当前超额" : "20日超额"}</span>
      <strong>{pct(item.excess_20d_return ?? item.current_excess_return)}</strong>
      <small>最高曾到 {pct(item.peak_return)} · 从高点最多回落 {pct(item.max_drawdown)}</small>
    </div>
    <p>{plainLanguage(item.thesis || "当日候选理由待补。")}</p>
  </article>;
}

export function RecommendationHistoryPage() {
  const [preset, setPreset] = useState("trend");
  const queryClient = useQueryClient();
  const query = useQuery(historyQueryOptions(preset));
  const data = query.data;

  const selectedLabel = presets.find(([key]) => key === preset)?.[1] ?? preset;
  const evaluatedRatio = data?.summary.pick_count
    ? Math.min(100, (data.summary.evaluated_count / data.summary.pick_count) * 100)
    : 0;

  return <>
    <header className="page-head history-page-head">
      <div><p className="eyebrow">RECOMMENDATION LEDGER</p><h1>推荐复盘</h1><span>候选会变，入选时点不改写。按固定交易日窗口验账。</span></div>
      <div className="history-observed"><History size={16} /><span>最新观察</span><strong>{observedTime(data?.last_observed_at ?? null)}</strong></div>
    </header>

    <nav className="history-preset-bar" aria-label="复盘策略">
      {presets.map(([key, label]) => <button
        type="button"
        key={key}
        className={preset === key ? "active" : ""}
        onPointerEnter={() => queryClient.prefetchQuery(historyQueryOptions(key))}
        onFocus={() => queryClient.prefetchQuery(historyQueryOptions(key))}
        onClick={() => setPreset(key)}
      >{label}</button>)}
    </nav>

    <AsyncState loading={query.isLoading} error={query.error as Error | null}>
      {data ? <>
        <section className="history-scoreboard" aria-label="历史推荐总览">
          <div className="history-score-intro"><span>{selectedLabel}</span><strong>{data.summary.evaluated_count ? rate(data.summary.hit_rate_20d) : "等待验收"}</strong><p>{data.summary.evaluated_count ? "20 日正收益命中率" : "首批候选走满 20 个交易日后形成正式命中率"}</p></div>
          <div className="history-score-metrics">
            <article><CalendarClock size={17} /><span>已存档</span><strong>{data.summary.run_count} 天</strong><small>{data.summary.pick_count} 条候选记录</small></article>
            <article><Gauge size={17} /><span>20日平均</span><strong className={returnTone(data.summary.average_20d_return)}>{pct(data.summary.average_20d_return)}</strong><small>{data.summary.evaluated_count} 条已验收</small></article>
            <article><Scale size={17} /><span>跑赢指数</span><strong>{rate(data.summary.benchmark_win_rate_20d)}</strong><small>平均超额 {pct(data.summary.average_20d_excess)}</small></article>
            <article><CheckCircle2 size={17} /><span>截至目前</span><strong className={returnTone(data.summary.average_current_return)}>{pct(data.summary.average_current_return)}</strong><small>正收益占比 {rate(data.summary.current_positive_rate)}</small></article>
          </div>
          <div className="history-maturity"><div><span>样本成熟度</span><strong>{data.summary.evaluated_count} / {data.summary.pick_count}</strong></div><i><em style={{ width: `${evaluatedRatio}%` }} /></i><small>未走满 T+20 的候选只展示过程收益，不混入正式命中率。</small></div>
        </section>

        <section className="history-ledger" aria-label="每日推荐账本">
          <header><div><span>逐日账本</span><strong>当时选了谁，后来走得怎样</strong></div><small>基准：上证指数 · 收益未计交易成本</small></header>
          {data.days.length === 0 ? <div className="history-empty"><strong>从今天开始建档</strong><p>首个交易日开始记录，不回填历史数据。</p></div> : <div className="history-day-list">
            {data.days.map((day) => <section className="history-day" key={`${day.preset}-${day.trading_date}`}>
              <header><time dateTime={day.trading_date}>{shortDate(day.trading_date)}</time><div><strong>{day.available ? `${day.picks.length} 只入选` : "策略不可用"}</strong><small>{plainLanguage(day.picks.length ? day.summary : day.unavailable_reason ?? "当日没有通过筛选的候选")}</small></div></header>
              {day.picks.length ? <div className="history-pick-list">{day.picks.map((item) => <PerformanceRow key={item.symbol} item={item} />)}</div> : <div className="history-no-picks">当日没有候选也会保留记录，不用结果倒推推荐。</div>}
            </section>)}
          </div>}
        </section>

        <details className="history-methodology"><summary>计算方法说明</summary><ol>{data.methodology.map((item) => <li key={item}>{plainLanguage(item)}</li>)}</ol></details>
      </> : null}
    </AsyncState>
  </>;
}
