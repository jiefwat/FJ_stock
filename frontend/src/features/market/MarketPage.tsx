import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { AsyncState } from "../../components/AsyncState";
import { DataStamp } from "../../components/DataStamp";
import { api, fmt, pct, percent, type Analysis, type IndexQuote, type MarketEventResult, type MarketIntelligenceResult, type Meta, type Quote, type Sector, type SectorDossier } from "../../lib/api";
import { EquityBrowser } from "./EquityBrowser";

type MarketData = { snapshot: { meta: Meta; indices: IndexQuote[]; sectors: Sector[] }; analysis: Analysis };
type DetailSort = "net_flow" | "change_pct" | "amount";
type DetailFilter = "all" | "net_inflow" | "up";

const regimeCopy: Record<string, { label: string; action: string }> = {
  risk_off: { label: "防守", action: "先保护本金，机会只保留观察。" },
  cautious: { label: "谨慎", action: "只复核板块、量能、价格同时确认的线索。" },
  balanced: { label: "均衡", action: "可以复核机会，但不要脱离证据链追涨。" },
  risk_on: { label: "进攻", action: "可提高复核强度，仍按失效条件执行。" },
};

export function MarketPage() {
  const [showAllSectors, setShowAllSectors] = useState(false);
  const [params, setParams] = useSearchParams();
  const selectedSector = params.get("sector");
  const selectedTheme = params.get("theme");
  const selectedThemeName = params.get("themeName") ?? selectedTheme ?? "";
  const selectedThemeChange = params.get("themeChange");
  const query = useQuery({ queryKey: ["market"], queryFn: () => api<MarketData>("/api/v1/market") });
  const eventsQuery = useQuery({ queryKey: ["market-events"], queryFn: () => api<MarketEventResult>("/api/v1/market-events?limit=30") });
  const intelligenceQuery = useQuery({ queryKey: ["cn-market-intelligence"], queryFn: () => api<MarketIntelligenceResult>("/api/v1/markets/CN/intelligence?limit=20") });
  const sectorQuery = useQuery({
    queryKey: ["sector", selectedSector],
    queryFn: () => api<SectorDossier>(`/api/v1/sectors/${selectedSector}`),
    enabled: Boolean(selectedSector),
  });
  const themeQuery = useQuery({
    queryKey: ["theme", selectedTheme, selectedThemeName, selectedThemeChange],
    queryFn: () => {
      const search = new URLSearchParams({ name: selectedThemeName });
      if (selectedThemeChange != null) search.set("change_pct", selectedThemeChange);
      return api<SectorDossier>(`/api/v1/themes/${selectedTheme}?${search.toString()}`);
    },
    enabled: Boolean(selectedTheme),
  });
  const openSector = (code: string) => setParams({ sector: code });
  return <AsyncState loading={query.isLoading} error={query.error as Error | null}>{query.data && <>
    <header className="page-head"><div><p className="eyebrow">MARKET / 全市场体检</p><h1>市场不是一个点数，<br /><em>而是一组证据。</em></h1></div><DataStamp meta={query.data.snapshot.meta} /></header>
    <MarketCommandCenter market={query.data} intelligence={intelligenceQuery.data} events={eventsQuery.data} onOpenSector={openSector} />
    <section className="breadth-board"><div><span>上涨</span><strong className="up">{query.data.analysis.advancing}</strong></div><div><span>下跌</span><strong className="down">{query.data.analysis.declining}</strong></div><div><span>平盘</span><strong>{query.data.analysis.unchanged}</strong></div><div><span>综合温度</span><strong>{fmt(query.data.analysis.score, 0)}</strong></div></section>
    <div className="two-column"><section className="panel"><div className="panel-title"><span>指数</span></div><div className="market-table">{query.data.snapshot.indices.map((item) => <div key={item.symbol}><span>{item.name}</span><b>{fmt(item.price)}</b><i className={(item.change_pct ?? 0) >= 0 ? "up" : "down"}>{pct(item.change_pct)}</i></div>)}</div></section><section className="panel"><div className="panel-title"><span>评分证据</span><small>分数 · 权重 · 事实</small></div><div className="factor-ledger">{query.data.analysis.factors.map((factor) => <article key={factor.key} className={factor.available ? "available" : "missing"}><span>{factor.label}<small>{factor.evidence}</small></span><strong>{factor.available ? fmt(factor.score, 0) : "未计入"}</strong><em>{factor.available ? `权重 ${percent(factor.weight * 100)}` : "权重 0%"}</em></article>)}</div></section></div>
    <MarketIntelligencePanel data={intelligenceQuery.data} loading={intelligenceQuery.isLoading} failed={intelligenceQuery.isError} onOpenSector={openSector} />
    <EquityBrowser />
    <section className="panel event-radar">
      <div className="panel-title"><span>市场异动雷达</span><small>今天股市正在发生什么</small></div>
      <AsyncState loading={eventsQuery.isLoading} error={eventsQuery.error as Error | null}>
        {eventsQuery.data && <MarketEventRadar data={eventsQuery.data} />}
      </AsyncState>
    </section>
    <section className="panel"><div className="panel-title"><span>板块热度</span><small>点击板块查看成分股和简析</small></div><div className="sector-grid">{query.data.snapshot.sectors.slice(0, showAllSectors ? undefined : 12).map((item) => <button key={item.code} className={`sector-card ${selectedSector === item.code ? "active" : ""}`} onClick={() => openSector(item.code)}><span>{item.name}</span><strong className={(item.change_pct ?? 0) >= 0 ? "up" : "down"}>{pct(item.change_pct)}</strong><small>{item.net_flow == null ? "资金流待增强" : `净流入 ${fmt(item.net_flow / 100000000)} 亿`}</small></button>)}</div><div className="panel-actions"><button className="text-button" onClick={() => setShowAllSectors((value) => !value)}>{showAllSectors ? "收起板块" : `查看全部 ${query.data.snapshot.sectors.length} 个板块`}</button><Link className="button" to="/opportunities">按当前市场找机会 →</Link></div></section>
    {selectedSector && <DossierPanel key={`sector-${selectedSector}`} data={sectorQuery.data} loading={sectorQuery.isLoading} error={sectorQuery.error as Error | null} variant="sector" onClose={() => setParams({})} />}
    {selectedTheme && <DossierPanel key={`theme-${selectedTheme}`} data={themeQuery.data} loading={themeQuery.isLoading} error={themeQuery.error as Error | null} variant="theme" onClose={() => setParams({})} />}
  </>}</AsyncState>;
}

function MarketCommandCenter({ market, intelligence, events, onOpenSector }: { market: MarketData; intelligence?: MarketIntelligenceResult; events?: MarketEventResult; onOpenSector: (code: string) => void }) {
  const regime = regimeCopy[market.analysis.regime] ?? { label: market.analysis.regime, action: "先读证据，再决定复核顺序。" };
  const total = Math.max(1, market.analysis.advancing + market.analysis.declining + market.analysis.unchanged);
  const breadth = market.analysis.advancing / total * 100;
  const topFlow = intelligence?.sector_flows[0];
  const riskEvent = events?.events.find((event) => event.sentiment === "negative" || event.category === "risk_alert");
  const eventHeadline = riskEvent?.title ?? events?.summary[0] ?? "暂无显著事件风险，继续以指数、板块和资金为主。";
  const routeText = breadth >= 55 ? "广度占优，优先看资金主线是否扩散。" : breadth >= 45 ? "广度中性，只做强势板块里的少数复核。" : "广度偏弱，候选降级，先处理持仓风险。";

  return <section className="market-command-center" aria-label="市场作战台">
    <article className="market-command-verdict">
      <span>MARKET GATE</span>
      <strong>{regime.label} · {fmt(market.analysis.score, 0)}/100</strong>
      <p>{regime.action}</p>
      <small>上涨占比 {percent(breadth)} · 置信度 {percent(market.analysis.confidence * 100)}</small>
    </article>
    <div className="market-command-grid">
      <article>
        <span>今日路线</span>
        <strong>{routeText}</strong>
        <p>市场状态决定机会复核强度，不让单个热点覆盖全局风险。</p>
      </article>
      <article>
        <span>资金主线</span>
        {topFlow ? <>
          <button type="button" onClick={() => onOpenSector(topFlow.code)}>{topFlow.name}</button>
          <p>{pct(topFlow.change_pct)} · 净流 {flowAmount(topFlow.net_flow)}</p>
        </> : <>
          <strong>等待资金确认</strong>
          <p>板块资金源未返回时，只用指数和广度做防守判断。</p>
        </>}
      </article>
      <article>
        <span>事件风险</span>
        <strong>{eventHeadline}</strong>
        <p>事件必须回到板块和个股页验证价格、资金、逻辑三道闸。</p>
      </article>
      <article>
        <span>下一步</span>
        <Link to="/opportunities">进入机会漏斗</Link>
        <p>只把通过市场和板块确认的标的带入 Stock Lab。</p>
      </article>
    </div>
  </section>;
}

function detailValue(item: Quote, sort: DetailSort) {
  return item[sort] ?? Number.NEGATIVE_INFINITY;
}

function filterRows(items: Quote[], filter: DetailFilter) {
  if (filter === "net_inflow") return items.filter((item) => (item.net_flow ?? 0) > 0);
  if (filter === "up") return items.filter((item) => (item.change_pct ?? 0) > 0);
  return items;
}

function sortedRows(items: Quote[], sort: DetailSort, filter: DetailFilter) {
  return [...filterRows(items, filter)].sort(
    (left, right) => detailValue(right, sort) - detailValue(left, sort),
  );
}


function stockLeadReason(item: Quote) {
  const up = (item.change_pct ?? 0) > 0;
  const inflow = (item.net_flow ?? 0) > 0;
  if (up && inflow) return "价格与资金同向，优先打开 Stock Lab 复核";
  if (up && item.net_flow == null) return "价格走强但资金缺口待补，先看证据总账";
  if (inflow) return "资金先动但价格未确认，观察是否补涨";
  if ((item.amount ?? 0) >= 1_000_000_000) return "成交活跃，适合作为板块样本复核";
  return "证据较弱，先保留观察";
}

function stockLeadTone(item: Quote) {
  if ((item.change_pct ?? 0) > 0 && (item.net_flow ?? 0) > 0) return "positive";
  if ((item.change_pct ?? 0) < 0 && (item.net_flow ?? 0) <= 0) return "negative";
  return "caution";
}

function stockLeadScore(item: Quote) {
  const change = item.change_pct ?? -20;
  const flow = item.net_flow == null ? -1 : item.net_flow / 100_000_000;
  const amount = item.amount == null ? 0 : Math.min(item.amount / 100_000_000, 50) / 10;
  return change * 2 + flow + amount;
}

function stockHref(item: Quote, source: SectorDossier, suffix: string) {
  const params = new URLSearchParams({ symbol: item.symbol, from: "market", board: source.sector.code, boardName: source.sector.name, boardType: suffix });
  return `/stocks?${params.toString()}`;
}

function BoardStockLeads({ data, suffix }: { data: SectorDossier; suffix: string }) {
  const leads = [...data.constituents].sort((left, right) => stockLeadScore(right) - stockLeadScore(left)).slice(0, 3);
  if (!leads.length) return null;

  return <section className="board-stock-leads" aria-label={`${data.sector.name}${suffix}优先个股线索`}>
    <div className="board-leads-title">
      <span>STOCK HANDOFF</span>
      <strong>优先点开这几只</strong>
      <p>从板块进入个股页前，先看价格、资金和成交额是否给出点开理由。</p>
    </div>
    <div className="board-leads-grid">
      {leads.map((item, index) => <Link key={item.symbol} className={stockLeadTone(item)} to={stockHref(item, data, suffix)}>
        <em>{String(index + 1).padStart(2, "0")}</em>
        <span>{item.name}<small>{item.symbol}</small></span>
        <strong className={(item.change_pct ?? 0) >= 0 ? "up" : "down"}>{pct(item.change_pct)}</strong>
        <p>{stockLeadReason(item)}</p>
        <b>{item.net_flow == null ? `成交 ${fmt((item.amount ?? 0) / 100000000)} 亿` : `净流 ${fmt(item.net_flow / 100000000)} 亿`}</b>
      </Link>)}
    </div>
  </section>;
}

function DossierPanel({ data, loading, error, variant, onClose }: { data?: SectorDossier; loading: boolean; error: Error | null; variant: "sector" | "theme"; onClose: () => void }) {
  const [sort, setSort] = useState<DetailSort>("net_flow");
  const [filter, setFilter] = useState<DetailFilter>("all");
  const rows = data ? sortedRows(data.constituents, sort, filter) : [];
  const suffix = variant === "theme" ? "题材" : "板块";
  return <section className="panel sector-detail">
    <AsyncState loading={loading} error={error}>{data && <>
      <div className="sector-detail-head"><div><span>{variant === "theme" ? "THEME DOSSIER" : "SECTOR DOSSIER"}</span><h2>{data.sector.name}{suffix}简析</h2></div><button className="text-button" onClick={onClose}>关闭</button></div>
      <SectorReviewDesk data={data} suffix={suffix} />
      <div className="sector-digest"><article><span>{suffix}涨跌</span><strong className={(data.sector.change_pct ?? 0) >= 0 ? "up" : "down"}>{pct(data.sector.change_pct)}</strong></article><article><span>资金温度</span><strong>{data.sector.net_flow == null ? "待增强" : `${fmt(data.sector.net_flow / 100000000)} 亿`}</strong></article><article><span>证据覆盖</span><strong>{percent(data.evidence_coverage * 100)}</strong></article></div>
      <div className="sector-summary">{data.summary.map((item) => <p key={item}>{item}</p>)}{data.missing_evidence.length > 0 && <small>缺口：{data.missing_evidence.join("、")}</small>}</div>
      <BoardStockLeads data={data} suffix={suffix} />
      <div className="dossier-tools" aria-label={`${data.sector.name}${suffix}筛选`}>
        <label>排序<select aria-label="详情排序" value={sort} onChange={(event) => setSort(event.target.value as DetailSort)}><option value="net_flow">资金优先</option><option value="change_pct">涨幅优先</option><option value="amount">成交额优先</option></select></label>
        <label>范围<select aria-label="详情范围" value={filter} onChange={(event) => setFilter(event.target.value as DetailFilter)}><option value="all">全部</option><option value="net_inflow">只看净流入</option><option value="up">只看上涨</option></select></label>
        <span>显示 {rows.length} / {data.constituents.length}</span>
      </div>
      {rows.length > 0 ? <div className="sector-constituents">{rows.map((item) => <Link key={item.symbol} to={stockHref(item, data, suffix)}><span><b>{item.name}</b><small>{item.symbol}</small></span><strong className={(item.change_pct ?? 0) >= 0 ? "up" : "down"}>{pct(item.change_pct)}</strong><em>{item.net_flow == null ? `成交 ${fmt((item.amount ?? 0) / 100000000)} 亿` : `净流 ${fmt(item.net_flow / 100000000)} 亿`}</em><p>{stockLeadReason(item)}</p></Link>)}</div> : <div className="empty">当前筛选下没有相关股票。</div>}
    </>}</AsyncState>
  </section>;
}

function SectorReviewDesk({ data, suffix }: { data: SectorDossier; suffix: string }) {
  const total = Math.max(1, data.constituents.length);
  const rising = data.constituents.filter((item) => (item.change_pct ?? 0) > 0).length;
  const inflow = data.constituents.filter((item) => (item.net_flow ?? 0) > 0).length;
  const topGain = [...data.constituents].sort((left, right) => (right.change_pct ?? Number.NEGATIVE_INFINITY) - (left.change_pct ?? Number.NEGATIVE_INFINITY))[0];
  const topFlow = [...data.constituents].sort((left, right) => (right.net_flow ?? Number.NEGATIVE_INFINITY) - (left.net_flow ?? Number.NEGATIVE_INFINITY))[0];
  const risingRatio = rising / total * 100;
  const inflowRatio = inflow / total * 100;
  const tone = data.missing_evidence.length > 0 ? "caution" : risingRatio >= 55 && inflowRatio >= 45 ? "positive" : risingRatio < 35 ? "negative" : "neutral";
  const verdict = tone === "positive"
    ? "主线可继续复核"
    : tone === "negative"
      ? "扩散不足，先降级观察"
      : "只看前排，等待确认";

  return <section className={`sector-review-desk ${tone}`} aria-label={`${data.sector.name}${suffix}复核工作台`}>
    <article className="sector-review-verdict">
      <span>BOARD GATE</span>
      <strong>{verdict}</strong>
      <p>{data.summary[0] ?? `${data.sector.name}${suffix}需要继续补充价格、资金和成分股证据。`}</p>
    </article>
    <div className="sector-review-grid">
      <article>
        <span>上涨扩散</span>
        <strong>{rising} / {total}</strong>
        <p>{percent(risingRatio)} 成分上涨；不过半时不把单点领涨当成板块主线。</p>
      </article>
      <article>
        <span>净流入扩散</span>
        <strong>{inflow} / {total}</strong>
        <p>{data.sector.net_flow == null ? "资金证据待增强，先看成交额和涨跌扩散。" : `${percent(inflowRatio)} 成分净流入，板块净流 ${flowAmount(data.sector.net_flow)}。`}</p>
      </article>
      <article>
        <span>领涨核心</span>
        {topGain ? <Link to={`/stocks?symbol=${topGain.symbol}`}>{topGain.name}<small>{pct(topGain.change_pct)}</small></Link> : <strong>暂无</strong>}
        <p>先确认领涨是否强于板块，而不是只看板块均值。</p>
      </article>
      <article>
        <span>资金核心</span>
        {topFlow && topFlow.net_flow != null ? <Link to={`/stocks?symbol=${topFlow.symbol}`}>{topFlow.name}<small>{flowAmount(topFlow.net_flow)}</small></Link> : <strong>待增强</strong>}
        <p>{data.missing_evidence.length ? `缺口：${data.missing_evidence.join("、")}` : "资金核心需要和领涨核心交叉确认。"}</p>
      </article>
    </div>
  </section>;
}

function flowAmount(value: number | null) {
  if (value == null) return "—";
  const amount = value / 100_000_000;
  return `${amount > 0 ? "+" : ""}${fmt(amount)} 亿`;
}

function MarketIntelligencePanel({ data, loading, failed, onOpenSector }: { data?: MarketIntelligenceResult; loading: boolean; failed: boolean; onOpenSector: (code: string) => void }) {
  return <section className="panel market-intelligence" aria-label="A股市场情报">
    <div className="panel-title"><span>A 股市场情报</span><small>板块资金 + 交易异动 · 只作核验线索</small></div>
    <p className="intelligence-boundary">供应商算法与交易异动仅作展示，不直接形成推荐或改变个股评分。</p>
    {loading && <div className="capability-empty">正在读取市场情报…</div>}
    {failed && <div className="capability-warning">市场情报暂不可用，指数、广度与全市场行情仍可继续使用。</div>}
    {data && <div className="intelligence-grid">
      <div className="flow-leaders">
        <header><span>板块资金确认</span><b>{data.sector_flows.length} 个</b></header>
        {data.capabilities.sector_flows?.status === "unavailable" && <p className="capability-warning">板块资金源暂不可用。</p>}
        {data.sector_flows.slice(0, 8).map((sector, index) => <button key={sector.code} type="button" onClick={() => onOpenSector(sector.code)}>
          <em>{String(index + 1).padStart(2, "0")}</em>
          <span>{sector.name}<small>{pct(sector.change_pct)}</small></span>
          <strong className={(sector.net_flow ?? 0) >= 0 ? "up" : "down"}>{flowAmount(sector.net_flow)}</strong>
        </button>)}
      </div>
      <div className="anomaly-list">
        <header><span>龙虎榜观察</span><b>{data.anomalies.length} 条</b></header>
        {data.capabilities.dragon_tiger?.status === "unavailable" && <p className="capability-warning">龙虎榜源暂不可用，不能据空结果判断当天没有异动。</p>}
        {data.anomalies.slice(0, 8).map((item) => <article key={`${item.trade_date}-${item.symbol}`}>
          <time>{item.trade_date.slice(5)}</time>
          <div><Link to={`/stocks?symbol=${item.symbol}`}>{item.name} <small>{item.symbol}</small></Link><p>{item.reason}</p></div>
          <strong className={(item.net_buy ?? 0) >= 0 ? "up" : "down"}>{flowAmount(item.net_buy)}</strong>
        </article>)}
      </div>
    </div>}
  </section>;
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
