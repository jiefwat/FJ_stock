import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowUpRight, BellRing, CheckCheck, ShieldCheck } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { AsyncState } from "../../components/AsyncState";
import { api, type DecisionEvent, type DecisionEventFeed } from "../../lib/api";

type CategoryFilter = "all" | "actionable" | "holding" | "opportunity";
type ReadFilter = "all" | "unread" | "read";
type ReadNotice = { tone: "success" | "error"; message: string };

const MONITORING_PAGE_SIZE = 6;

const strategyLabels: Record<string, string> = {
  trend: "趋势延续",
  volume_breakout: "放量突破",
  capital_confirmed: "资金确认",
  sector_momentum: "板块共振",
  pullback_support: "回踩企稳",
  value_rebound: "低估反弹",
  oversold_repair: "超跌修复",
  quality_value: "质量价值",
  large_cap_stability: "大盘稳健",
};

function observedTime(value: string | null) {
  if (!value) return "等待首次后台监控";
  return new Date(value).toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

function updateRead(feed: DecisionEventFeed | undefined, eventId?: number): DecisionEventFeed | undefined {
  if (!feed) return feed;
  const readAt = new Date().toISOString();
  const update = (event: DecisionEvent) => (
    eventId == null || event.id === eventId ? { ...event, read_at: event.read_at ?? readAt } : event
  );
  const unreadChange = eventId == null
    ? feed.unread_count
    : [...feed.requires_action, ...feed.monitoring].some((event) => event.id === eventId && !event.read_at) ? 1 : 0;
  return {
    ...feed,
    unread_count: Math.max(0, feed.unread_count - unreadChange),
    requires_action: feed.requires_action.map(update),
    monitoring: feed.monitoring.map(update),
  };
}

function DecisionCard({ event, onRead }: { event: DecisionEvent; onRead: (id: number) => void }) {
  const source = event.source === "holding" ? "持仓变化" : `候选 · ${strategyLabels[event.strategy ?? ""] ?? "策略监控"}`;
  const percent = event.confidence == null ? null : Math.round(event.confidence * 100);
  const confidence = percent == null
    ? { label: "证据待补", tone: "unknown" }
    : percent >= 80
      ? { label: "证据较充分", tone: "high" }
      : percent >= 60
        ? { label: "证据一般", tone: "medium" }
        : { label: "证据较少", tone: "low" };
  return <article className={`decision-event-card ${event.severity} ${event.read_at ? "read" : "unread"}`}>
    <Link className="decision-event-link" to={event.href} aria-label={`查看${event.name}原因：${event.action}`} onClick={() => onRead(event.id)}>
      <div className="decision-event-main">
        <div className="decision-event-meta"><span>{source}</span><time dateTime={event.observed_at}>{observedTime(event.observed_at)}</time>{!event.read_at ? <i>未读</i> : null}</div>
        <div className="decision-event-title"><div><h3>{event.name}<small>{event.symbol}</small></h3><strong>{event.action}</strong></div><div className={`decision-confidence ${confidence.tone}`} title="分析置信度衡量证据完整度，不代表上涨概率"><span>{percent == null ? confidence.label : `${confidence.label} · ${percent}%`}</span><i><em style={{ width: `${percent ?? 0}%` }} /></i></div></div>
        <p>{event.summary}</p>
        <div className="decision-transition"><span>之前：{event.previous_action}</span><b>现在：{event.action}</b></div>
      </div>
      <span className="decision-card-cta">查看原因<ArrowUpRight size={15} /></span>
    </Link>
  </article>;
}

export function DecisionCenterPage() {
  const client = useQueryClient();
  const [category, setCategory] = useState<CategoryFilter>("all");
  const [readFilter, setReadFilter] = useState<ReadFilter>("all");
  const [monitoringLimit, setMonitoringLimit] = useState(MONITORING_PAGE_SIZE);
  const [readNotice, setReadNotice] = useState<ReadNotice | null>(null);
  const query = useQuery({
    queryKey: ["decision-events"],
    queryFn: () => api<DecisionEventFeed>("/api/v1/decision-events"),
    refetchOnWindowFocus: true,
  });
  const read = useMutation({
    mutationFn: (eventId: number) => api<DecisionEvent>(`/api/v1/decision-events/${eventId}/read`, { method: "POST" }),
    onMutate: async (eventId) => {
      await client.cancelQueries({ queryKey: ["decision-events"] });
      const previous = client.getQueryData<DecisionEventFeed>(["decision-events"]);
      client.setQueryData<DecisionEventFeed>(["decision-events"], (feed) => updateRead(feed, eventId));
      return { previous };
    },
    onError: (_error, _eventId, context) => {
      if (context?.previous) client.setQueryData(["decision-events"], context.previous);
      setReadNotice({ tone: "error", message: "未能标记为已读，请稍后重试" });
    },
    onSettled: () => client.invalidateQueries({ queryKey: ["decision-events"] }),
  });
  const readAll = useMutation({
    mutationFn: () => api<{ read: number }>("/api/v1/decision-events/read-all", { method: "POST" }),
    onMutate: async () => {
      setReadNotice(null);
      await client.cancelQueries({ queryKey: ["decision-events"] });
      const previous = client.getQueryData<DecisionEventFeed>(["decision-events"]);
      client.setQueryData<DecisionEventFeed>(["decision-events"], (feed) => updateRead(feed));
      return { previous };
    },
    onSuccess: () => setReadNotice({ tone: "success", message: "全部提醒已标为已读" }),
    onError: (_error, _variables, context) => {
      if (context?.previous) client.setQueryData(["decision-events"], context.previous);
      setReadNotice({ tone: "error", message: "全部已读操作失败，未读状态已恢复" });
    },
    onSettled: () => client.invalidateQueries({ queryKey: ["decision-events"] }),
  });
  const feed = query.data;
  const empty = feed && feed.requires_action.length === 0 && feed.monitoring.length === 0;
  const allEvents = useMemo(() => feed ? [...feed.requires_action, ...feed.monitoring] : [], [feed]);
  const matches = (event: DecisionEvent) => {
    const categoryMatch = category === "all"
      || (category === "actionable" && event.user_required)
      || event.source === category;
    const readMatch = readFilter === "all"
      || (readFilter === "unread" && !event.read_at)
      || (readFilter === "read" && Boolean(event.read_at));
    return categoryMatch && readMatch;
  };
  const requiredEvents = feed?.requires_action.filter(matches) ?? [];
  const monitoringEvents = feed?.monitoring.filter(matches) ?? [];
  const visibleMonitoringEvents = monitoringEvents.slice(0, monitoringLimit);
  const hiddenMonitoringCount = Math.max(0, monitoringEvents.length - visibleMonitoringEvents.length);
  const visibleCount = requiredEvents.length + monitoringEvents.length;
  const categoryOptions: Array<[CategoryFilter, string, number]> = [
    ["all", "全部", allEvents.length],
    ["actionable", "需要处理", feed?.requires_action.length ?? 0],
    ["holding", "持仓变化", allEvents.filter((event) => event.source === "holding").length],
    ["opportunity", "候选变化", allEvents.filter((event) => event.source === "opportunity").length],
  ];

  useEffect(() => setMonitoringLimit(MONITORING_PAGE_SIZE), [category, readFilter]);
  useEffect(() => {
    if (!readNotice) return undefined;
    const timer = window.setTimeout(() => setReadNotice(null), 3_200);
    return () => window.clearTimeout(timer);
  }, [readNotice]);

  return <>
    <header className="page-head decision-page-head">
      <div><p className="eyebrow">CHANGE MONITOR</p><h1>变化提醒</h1><span>只记录动作发生变化的时刻；候选和真实持仓分开处理。分析置信度衡量证据完整度，不代表上涨概率。</span></div>
      <div className="decision-monitor-stamp"><BellRing size={17} /><span>最近更新</span><strong>{observedTime(feed?.monitored_at ?? null)}</strong></div>
    </header>

    <AsyncState loading={query.isLoading} error={query.error as Error | null} onRetry={() => void query.refetch()}>
      {feed ? <div className="decision-center">
        {empty ? <section className="decision-empty"><ShieldCheck size={28} /><strong>没有需要你处理的变化</strong><p>系统每 10 分钟自动检查。你可以继续完成今天的研究任务。</p><nav aria-label="提醒为空时的下一步"><Link to="/opportunities">查看今日候选</Link><Link to="/holdings">维护真实持仓</Link><Link to="/market">回到市场概览</Link></nav></section> : <>
          {requiredEvents.length ? <section className="decision-event-section actionable" aria-label="需要处理">
            <header><div><span>YOUR MOVE</span><h2>需要处理</h2><strong>{requiredEvents.length} 项 · 仅真实持仓或可执行候选</strong></div></header>
            <div className="decision-event-grid">{requiredEvents.map((event) => <DecisionCard key={event.id} event={event} onRead={(id) => read.mutate(id)} />)}</div>
          </section> : null}
          <section className="decision-filter-panel" aria-label="提醒筛选">
            <div className="decision-filter-summary"><strong>{feed.unread_count}</strong><span>条未读</span><p>持仓提醒只来自当前账号仍在持有的股票。</p></div>
            <div className="decision-filter-groups"><div role="group" aria-label="提醒类别">{categoryOptions.map(([key, label, count]) => <button type="button" className={category === key ? "active" : ""} aria-pressed={category === key} key={key} onClick={() => setCategory(key)}>{label} <b>{count}</b></button>)}</div><div role="group" aria-label="阅读状态"><button type="button" className={readFilter === "all" ? "active" : ""} aria-pressed={readFilter === "all"} onClick={() => setReadFilter("all")}>全部状态</button><button type="button" className={readFilter === "unread" ? "active" : ""} aria-pressed={readFilter === "unread"} onClick={() => setReadFilter("unread")}>未读 {feed.unread_count}</button><button type="button" className={readFilter === "read" ? "active" : ""} aria-pressed={readFilter === "read"} onClick={() => setReadFilter("read")}>已读</button></div></div>
            {feed.unread_count > 0 || readAll.isPending ? <button type="button" className="decision-read-all" onClick={() => readAll.mutate()} disabled={readAll.isPending}><CheckCheck size={15} />{readAll.isPending ? "正在标记…" : "全部已读"}</button> : null}
          </section>
          <span className="sr-only" role="status" aria-live="polite">当前筛选显示 {visibleCount} 条提醒</span>
          {readNotice ? <div className={`decision-read-notice ${readNotice.tone}`} role={readNotice.tone === "error" ? "alert" : "status"} aria-live={readNotice.tone === "error" ? "assertive" : "polite"}>{readNotice.message}</div> : null}
          {visibleCount === 0 ? <section className="decision-filter-empty"><ShieldCheck size={20} /><span>当前筛选下没有提醒</span><button type="button" onClick={() => { setCategory("all"); setReadFilter("all"); }}>清除筛选</button></section> : null}
          {monitoringEvents.length ? <section className="decision-event-section monitoring" aria-label="自动记录">
            <header><div><span>SYSTEM LOG</span><h2>自动记录</h2><strong>{monitoringEvents.length} 项 · 无需操作</strong></div></header>
            <div className="decision-event-grid">{visibleMonitoringEvents.map((event) => <DecisionCard key={event.id} event={event} onRead={(id) => read.mutate(id)} />)}</div>
            {hiddenMonitoringCount > 0 ? <button type="button" className="decision-show-more" onClick={() => setMonitoringLimit((current) => current + MONITORING_PAGE_SIZE)}>再显示 {Math.min(MONITORING_PAGE_SIZE, hiddenMonitoringCount)} 条 <span>还剩 {hiddenMonitoringCount} 条</span></button> : null}
          </section> : null}
        </>}
      </div> : null}
    </AsyncState>
  </>;
}
