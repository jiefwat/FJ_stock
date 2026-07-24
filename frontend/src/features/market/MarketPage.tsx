import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { AsyncState } from "../../components/AsyncState";
import { DataStamp } from "../../components/DataStamp";
import { api, fmt, pct, percent, type Analysis, type IndexQuote, type MarketEventResult, type Meta, type Sector, type SectorDossier } from "../../lib/api";
import { EquityBrowser } from "./EquityBrowser";

type MarketData = { snapshot: { meta: Meta; indices: IndexQuote[]; sectors: Sector[] }; analysis: Analysis };

export function MarketPage() {
  const [showAllSectors, setShowAllSectors] = useState(false);
  const [params, setParams] = useSearchParams();
  const selectedSector = params.get("sector");
  const query = useQuery({ queryKey: ["market"], queryFn: () => api<MarketData>("/api/v1/market") });
  const eventsQuery = useQuery({ queryKey: ["market-events"], queryFn: () => api<MarketEventResult>("/api/v1/market-events?limit=30") });
  const sectorQuery = useQuery({
    queryKey: ["sector", selectedSector],
    queryFn: () => api<SectorDossier>(`/api/v1/sectors/${selectedSector}`),
    enabled: Boolean(selectedSector),
  });
  const openSector = (code: string) => setParams({ sector: code });
  return <AsyncState loading={query.isLoading} error={query.error as Error | null}>{query.data && <>
    <header className="page-head"><div><p className="eyebrow">MARKET / 全市场体检</p><h1>市场不是一个点数，<br /><em>而是一组证据。</em></h1></div><DataStamp meta={query.data.snapshot.meta} /></header>
    <section className="breadth-board"><div><span>上涨</span><strong className="up">{query.data.analysis.advancing}</strong></div><div><span>下跌</span><strong className="down">{query.data.analysis.declining}</strong></div><div><span>平盘</span><strong>{query.data.analysis.unchanged}</strong></div><div><span>综合温度</span><strong>{fmt(query.data.analysis.score, 0)}</strong></div></section>
    <div className="two-column"><section className="panel"><div className="panel-title"><span>指数</span></div><div className="market-table">{query.data.snapshot.indices.map((item) => <div key={item.symbol}><span>{item.name}</span><b>{fmt(item.price)}</b><i className={(item.change_pct ?? 0) >= 0 ? "up" : "down"}>{pct(item.change_pct)}</i></div>)}</div></section><section className="panel"><div className="panel-title"><span>评分证据</span><small>分数 · 权重 · 事实</small></div><div className="factor-ledger">{query.data.analysis.factors.map((factor) => <article key={factor.key} className={factor.available ? "available" : "missing"}><span>{factor.label}<small>{factor.evidence}</small></span><strong>{factor.available ? fmt(factor.score, 0) : "未计入"}</strong><em>{factor.available ? `权重 ${percent(factor.weight * 100)}` : "权重 0%"}</em></article>)}</div></section></div>
    <EquityBrowser />
    <section className="panel event-radar">
      <div className="panel-title"><span>市场异动雷达</span><small>今天股市正在发生什么</small></div>
      <AsyncState loading={eventsQuery.isLoading} error={eventsQuery.error as Error | null}>
        {eventsQuery.data && <MarketEventRadar data={eventsQuery.data} />}
      </AsyncState>
    </section>
    <section className="panel"><div className="panel-title"><span>板块热度</span><small>点击板块查看成分股和简析</small></div><div className="sector-grid">{query.data.snapshot.sectors.slice(0, showAllSectors ? undefined : 12).map((item) => <button key={item.code} className={`sector-card ${selectedSector === item.code ? "active" : ""}`} onClick={() => openSector(item.code)}><span>{item.name}</span><strong className={(item.change_pct ?? 0) >= 0 ? "up" : "down"}>{pct(item.change_pct)}</strong><small>{item.net_flow == null ? "资金流待增强" : `净流入 ${fmt(item.net_flow / 100000000)} 亿`}</small></button>)}</div><div className="panel-actions"><button className="text-button" onClick={() => setShowAllSectors((value) => !value)}>{showAllSectors ? "收起板块" : `查看全部 ${query.data.snapshot.sectors.length} 个板块`}</button><Link className="button" to="/opportunities">按当前市场找机会 →</Link></div></section>
    {selectedSector && <section className="panel sector-detail"><AsyncState loading={sectorQuery.isLoading} error={sectorQuery.error as Error | null}>{sectorQuery.data && <>
      <div className="sector-detail-head"><div><span>SECTOR DOSSIER</span><h2>{sectorQuery.data.sector.name}板块简析</h2></div><button className="text-button" onClick={() => setParams({})}>关闭</button></div>
      <div className="sector-digest"><article><span>板块涨跌</span><strong className={(sectorQuery.data.sector.change_pct ?? 0) >= 0 ? "up" : "down"}>{pct(sectorQuery.data.sector.change_pct)}</strong></article><article><span>资金温度</span><strong>{sectorQuery.data.sector.net_flow == null ? "待增强" : `${fmt(sectorQuery.data.sector.net_flow / 100000000)} 亿`}</strong></article><article><span>证据覆盖</span><strong>{percent(sectorQuery.data.evidence_coverage * 100)}</strong></article></div>
      <div className="sector-summary">{sectorQuery.data.summary.map((item) => <p key={item}>{item}</p>)}{sectorQuery.data.missing_evidence.length > 0 && <small>缺口：{sectorQuery.data.missing_evidence.join("、")}</small>}</div>
      <div className="sector-constituents">{sectorQuery.data.constituents.map((item) => <Link key={item.symbol} to={`/stocks?symbol=${item.symbol}`}><span><b>{item.name}</b><small>{item.symbol}</small></span><strong className={(item.change_pct ?? 0) >= 0 ? "up" : "down"}>{pct(item.change_pct)}</strong><em>{item.net_flow == null ? `成交 ${fmt((item.amount ?? 0) / 100000000)} 亿` : `净流 ${fmt(item.net_flow / 100000000)} 亿`}</em></Link>)}</div>
    </>}</AsyncState></section>}
  </>}</AsyncState>;
}

function MarketEventRadar({ data }: { data: MarketEventResult }) {
  if (!data.events.length) {
    return <div className="empty">暂时没有拿到市场异动新闻。先用指数、板块热度和资金数据判断今天的主线。</div>;
  }
  return <>
    <div className="event-summary">
      {data.summary.map((item) => <p key={item}>{item}</p>)}
    </div>
    <div className="event-clusters">
      {data.clusters.map((cluster) => <article key={cluster.key} className={cluster.signal}>
        <span>{cluster.label}</span>
        <strong>{fmt(cluster.hot_score, 0)}</strong>
        <small>{cluster.count} 条 · {cluster.summary}</small>
      </article>)}
    </div>
    <div className="event-tape">
      {data.events.slice(0, 8).map((event) => <article key={event.id} className={event.sentiment}>
        <time>{formatEventTime(event.published_at)}</time>
        <div>
          <header>
            <h3>{event.url ? <a href={event.url} target="_blank" rel="noreferrer">{event.title}</a> : event.title}</h3>
            <b>{fmt(event.importance_score, 0)}</b>
          </header>
          <p>{event.summary}</p>
          <div className="event-tags">{event.tags.map((tag) => <span key={tag}>{tag}</span>)}</div>
          <dl>
            <div><dt>可能影响</dt><dd>{event.impact}</dd></div>
            <div><dt>下一步</dt><dd>{event.action}</dd></div>
          </dl>
          {event.related_symbols.length > 0 && <div className="event-symbols">{event.related_symbols.slice(0, 4).map((symbol) => <Link key={symbol} to={`/stocks?symbol=${symbol}`}>{symbol}</Link>)}</div>}
        </div>
      </article>)}
    </div>
    <div className="event-actions">
      {data.next_actions.map((action) => <span key={action}>{action}</span>)}
    </div>
    <section className="event-verify">
      <div className="panel-title"><span>事件-板块核验矩阵</span><small>每条新闻都要过三道闸</small></div>
      <div className="verify-grid">
        {data.events.slice(0, 4).map((event) => <article key={event.id}>
          <header><span>{event.tags[0] ?? "事件"}</span><strong>核验：{event.title}</strong></header>
          <div><b>价格是否确认</b><p>关联板块或个股需要强于大盘，不能只靠标题热度。</p></div>
          <div><b>资金是否确认</b><p>{event.related_sectors.length || event.related_symbols.length ? "回到板块温度与个股页看净流入、成交额和扩散数量。" : "暂无明确关联标的，先等待资金和板块映射补齐。"}</p></div>
          <div><b>逻辑是否可复盘</b><p>{event.action}</p></div>
        </article>)}
      </div>
    </section>
  </>;
}

function formatEventTime(value: string): string {
  return new Date(value).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
}
