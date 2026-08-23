import { useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarClock, CheckCircle2, Gauge, History, Scale } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { AsyncState } from "../../components/AsyncState";
import { PageTaskRail, WorkbenchPageHeader } from "../../components/WorkbenchPageHeader";
import { api, fmt, pct, type RecommendationHistoryResult, type RecommendationPerformancePick } from "../../lib/api";
import { plainLanguage } from "../../lib/plainLanguage";

const presets = [
  ["trend", "趋势延续"],
  ["volume_breakout", "放量突破"],
  ["capital_confirmed", "资金确认"],
  ["sector_momentum", "板块共振"],
  ["pullback_support", "回踩企稳"],
] as const;
const HISTORY_DAY_PAGE_SIZE = 6;

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

const strategyFocus: Record<string, string> = {
  trend: "价格是否持续走强",
  volume_breakout: "成交突然放大并突破",
  capital_confirmed: "大额买入资金是否持续",
  sector_momentum: "个股和所属板块是否同时走强",
  pullback_support: "强势股回落后是否稳住",
};

function strategyAssessment(preset: string, summary: RecommendationHistoryResult["summary"]) {
  const focus = strategyFocus[preset] ?? "筛选条件是否持续有效";
  if (summary.evaluated_count < 12) {
    return {
      action: "继续观察",
      reason: `仅 ${summary.evaluated_count} 条走满 20 个交易日，当前收益只是过程记录，不据此提高仓位`,
      focus,
      tone: "neutral",
    };
  }
  if (
    (summary.average_20d_return ?? 0) > 0
    && (summary.average_20d_excess ?? 0) > 0
    && (summary.hit_rate_20d ?? 0) >= 0.55
  ) {
    return { action: "保留策略", reason: "成熟样本的收益、胜率和相对指数表现同时为正", focus, tone: "positive" };
  }
  if ((summary.average_20d_return ?? 0) <= 0 || (summary.average_20d_excess ?? 0) < 0) {
    return { action: "建议降级", reason: "成熟样本的收益或相对指数表现不达标，暂不把它作为主要依据", focus, tone: "negative" };
  }
  return { action: "继续观察", reason: "已有正向表现，但稳定性还不足以提高使用优先级", focus, tone: "neutral" };
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
  const [visibleDayCount, setVisibleDayCount] = useState(HISTORY_DAY_PAGE_SIZE);
  const queryClient = useQueryClient();
  const query = useQuery(historyQueryOptions(preset));
  const data = query.data;

  const selectedLabel = presets.find(([key]) => key === preset)?.[1] ?? preset;
  const evaluatedRatio = data?.summary.pick_count
    ? Math.min(100, (data.summary.evaluated_count / data.summary.pick_count) * 100)
    : 0;
  const assessment = data ? strategyAssessment(preset, data.summary) : null;
  const performanceDistribution = data ? data.days.flatMap((day) => day.picks).reduce(
    (result, pick) => {
      if (pick.status !== "evaluated") result.immature += 1;
      else if ((pick.return_20d ?? 0) > 0) result.positive += 1;
      else if ((pick.return_20d ?? 0) < 0) result.negative += 1;
      else result.flat += 1;
      return result;
    },
    { positive: 0, negative: 0, flat: 0, immature: 0 },
  ) : null;
  const allEvaluatedNegative = Boolean(
    performanceDistribution
    && performanceDistribution.negative > 0
    && performanceDistribution.positive === 0
    && performanceDistribution.flat === 0,
  );
  const visibleDays = data?.days.slice(0, visibleDayCount) ?? [];
  const hiddenDayCount = Math.max(0, (data?.days.length ?? 0) - visibleDays.length);

  useEffect(() => setVisibleDayCount(HISTORY_DAY_PAGE_SIZE), [preset]);

  return <>
    <WorkbenchPageHeader
      eyebrow="RECOMMENDATION LEDGER"
      title="推荐复盘"
      description="候选会变化，但入选时点和价格不回写；正式收益与未成熟过程收益分开验账。"
      status={<div className="history-observed"><History size={16} /><span>最新观察</span><strong>{observedTime(data?.last_observed_at ?? null)}</strong></div>}
    />
    <PageTaskRail label="推荐复盘" steps={[
      { id: "history-strategies", label: "选择策略", detail: "切换同口径账本" },
      { id: "history-result", label: "判断表现", detail: "收益、命中与成熟度" },
      { id: "history-ledger", label: "核对记录", detail: "逐日查看原始候选" },
    ]} />

    <nav id="history-strategies" className="history-preset-bar" aria-label="复盘策略">
      {presets.map(([key, label]) => <button
        type="button"
        key={key}
        className={preset === key ? "active" : ""}
        onPointerEnter={() => queryClient.prefetchQuery(historyQueryOptions(key))}
        onFocus={() => queryClient.prefetchQuery(historyQueryOptions(key))}
        onClick={() => setPreset(key)}
      >{label}</button>)}
    </nav>

    <AsyncState loading={query.isLoading} error={query.error as Error | null} onRetry={() => void query.refetch()}>
      {data ? <>
        <section id="history-result" className="history-scoreboard" aria-label="历史推荐总览">
          <div className={`history-score-intro ${assessment?.tone ?? "neutral"}`}><span>{selectedLabel}</span><strong>{assessment?.action}</strong><small>{data.summary.evaluated_count ? `正式命中率 ${rate(data.summary.hit_rate_20d)}` : "正式结果等待验收"}</small><b>重点：{assessment?.focus}</b><p>{assessment?.reason}</p></div>
          <div className="history-score-metrics">
            <article><CalendarClock size={17} /><span>已存档</span><strong>{data.summary.run_count} 天</strong><small>{data.summary.pick_count} 条候选记录</small></article>
            <article><Gauge size={17} /><span>20日平均</span><strong className={returnTone(data.summary.average_20d_return)}>{pct(data.summary.average_20d_return)}</strong><small>{data.summary.evaluated_count} 条已验收</small></article>
            <article><Scale size={17} /><span>跑赢指数</span><strong>{rate(data.summary.benchmark_win_rate_20d)}</strong><small>平均超额 {pct(data.summary.average_20d_excess)}</small></article>
            <article><CheckCircle2 size={17} /><span>截至目前</span><strong className={returnTone(data.summary.average_current_return)}>{pct(data.summary.average_current_return)}</strong><small>正收益占比 {rate(data.summary.current_positive_rate)}</small></article>
          </div>
          <div className="history-maturity"><div><span>样本成熟度</span><strong>{data.summary.evaluated_count} / {data.summary.pick_count}</strong></div><i><em style={{ width: `${evaluatedRatio}%` }} /></i><small>未走满 T+20 的候选只展示过程收益，不混入正式命中率。</small></div>
          <div className={`history-distribution ${allEvaluatedNegative ? "negative" : ""}`} aria-label="复盘收益分布"><div><span>成熟样本分布</span><strong>正、负与未成熟样本全部展示</strong></div><b className="positive">正收益 {performanceDistribution?.positive ?? 0}</b><b className="negative">负收益 {performanceDistribution?.negative ?? 0}</b><b>持平 {performanceDistribution?.flat ?? 0}</b><b>未成熟 {performanceDistribution?.immature ?? 0}</b>{allEvaluatedNegative ? <p>当前成熟样本全部为负收益：建议暂停把该策略作为主要依据；继续记录，不回写历史结果。</p> : null}</div>
        </section>

        <section id="history-ledger" className="history-ledger" aria-label="每日推荐账本">
          <header><div><span>逐日账本</span><strong>当时选了谁，后来走得怎样</strong></div><small>基准：上证指数 · 收益未计交易成本</small></header>
          {data.days.length === 0 ? <div className="history-empty"><strong>从今天开始建档</strong><p>首个交易日开始记录，不回填历史数据。</p></div> : <div className="history-day-list">
            {visibleDays.map((day) => <section className="history-day" key={`${day.preset}-${day.trading_date}`}>
              <header><time dateTime={day.trading_date}>{shortDate(day.trading_date)}</time><div><strong>{day.available ? `${day.picks.length} 只入选` : "策略不可用"}</strong><small>{plainLanguage(day.picks.length ? day.summary : day.unavailable_reason ?? "当日没有通过筛选的候选")}</small></div></header>
              {day.picks.length ? <div className="history-pick-list">{day.picks.map((item) => <PerformanceRow key={item.symbol} item={item} />)}</div> : <div className="history-no-picks">当日没有候选也会保留记录，不用结果倒推推荐。</div>}
            </section>)}
          </div>}
          {data.days.length > HISTORY_DAY_PAGE_SIZE && <div className="history-ledger-controls"><span>已显示最近 {visibleDays.length} / {data.days.length} 个交易日</span><div>{visibleDayCount > HISTORY_DAY_PAGE_SIZE && <button type="button" onClick={() => setVisibleDayCount(HISTORY_DAY_PAGE_SIZE)}>收起到最近 {HISTORY_DAY_PAGE_SIZE} 天</button>}{hiddenDayCount > 0 && <button className="primary" type="button" onClick={() => setVisibleDayCount((current) => current + HISTORY_DAY_PAGE_SIZE)}>再显示 {Math.min(HISTORY_DAY_PAGE_SIZE, hiddenDayCount)} 天</button>}</div></div>}
        </section>

        <details className="history-methodology"><summary>计算方法说明</summary><ol>{data.methodology.map((item) => <li key={item}>{plainLanguage(item)}</li>)}</ol></details>
      </> : null}
    </AsyncState>
  </>;
}
