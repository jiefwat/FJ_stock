import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowUpRight, BellRing, CheckCheck, ShieldCheck } from "lucide-react";
import { Link } from "react-router-dom";

import { AsyncState } from "../../components/AsyncState";
import { api, type DecisionEvent, type DecisionEventFeed } from "../../lib/api";

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
  const source = event.source === "holding" ? "持仓" : "候选";
  return <article className={`decision-event-card ${event.severity} ${event.read_at ? "read" : "unread"}`}>
    <div className="decision-event-main">
      <div className="decision-event-meta"><span>{source}</span><time dateTime={event.observed_at}>{observedTime(event.observed_at)}</time></div>
      <strong>{event.action}</strong>
      <h3>{event.name}<small>{event.symbol}</small></h3>
      <p>{event.summary}</p>
      <div className="decision-transition"><span>之前：{event.previous_action}</span><b>现在：{event.action}</b></div>
    </div>
    <Link to={event.href} aria-label={`查看${event.name}决定`} onClick={() => onRead(event.id)}>查看决定<ArrowUpRight size={15} /></Link>
  </article>;
}

export function DecisionCenterPage() {
  const client = useQueryClient();
  const query = useQuery({
    queryKey: ["decision-events"],
    queryFn: () => api<DecisionEventFeed>("/api/v1/decision-events"),
    refetchOnWindowFocus: true,
  });
  const read = useMutation({
    mutationFn: (eventId: number) => api<DecisionEvent>(`/api/v1/decision-events/${eventId}/read`, { method: "POST" }),
    onMutate: (eventId) => client.setQueryData<DecisionEventFeed>(["decision-events"], (feed) => updateRead(feed, eventId)),
    onSettled: () => client.invalidateQueries({ queryKey: ["decision-events"] }),
  });
  const readAll = useMutation({
    mutationFn: () => api<{ read: number }>("/api/v1/decision-events/read-all", { method: "POST" }),
    onMutate: () => client.setQueryData<DecisionEventFeed>(["decision-events"], (feed) => updateRead(feed)),
    onSettled: () => client.invalidateQueries({ queryKey: ["decision-events"] }),
  });
  const feed = query.data;
  const empty = feed && feed.requires_action.length === 0 && feed.monitoring.length === 0;

  return <>
    <header className="page-head decision-page-head">
      <div><p className="eyebrow">DECISION LOG</p><h1>决策变更</h1></div>
      <div className="decision-monitor-stamp"><BellRing size={17} /><span>最近更新</span><strong>{observedTime(feed?.monitored_at ?? null)}</strong></div>
    </header>

    <AsyncState loading={query.isLoading} error={query.error as Error | null}>
      {feed ? <div className="decision-center">
        {empty ? <section className="decision-empty"><ShieldCheck size={28} /><strong>暂无待处理变更</strong><p>每 10 分钟更新</p></section> : <>
          <section className="decision-event-section actionable" aria-label="待处理">
            <header><div><h2>待处理</h2><strong>{feed.requires_action.length ? `${feed.requires_action.length} 项` : "0 项"}</strong></div>{feed.unread_count > 0 ? <button type="button" onClick={() => readAll.mutate()}><CheckCheck size={15} />全部已读</button> : null}</header>
            {feed.requires_action.length ? <div className="decision-event-grid">{feed.requires_action.map((event) => <DecisionCard key={event.id} event={event} onRead={(id) => read.mutate(id)} />)}</div> : <div className="decision-section-empty">暂无待确认交易变更</div>}
          </section>
          {feed.monitoring.length ? <section className="decision-event-section monitoring" aria-label="观察记录">
            <header><div><h2>观察记录</h2><strong>无需操作</strong></div></header>
            <div className="decision-event-grid">{feed.monitoring.map((event) => <DecisionCard key={event.id} event={event} onRead={(id) => read.mutate(id)} />)}</div>
          </section> : null}
        </>}
      </div> : null}
    </AsyncState>
  </>;
}
