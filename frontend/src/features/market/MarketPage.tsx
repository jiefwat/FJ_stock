import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState, type RefObject } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { AsyncState } from "../../components/AsyncState";
import { DataStamp } from "../../components/DataStamp";
import { api, fmt, pct, percent, type Analysis, type IndexQuote, type MarketEventResult, type MarketIntelligenceResult, type Meta, type Quote, type Sector, type SectorDossier } from "../../lib/api";
import { EquityBrowser } from "./EquityBrowser";

type MarketData = { snapshot: { meta: Meta; indices: IndexQuote[]; sectors: Sector[] }; analysis: Analysis };
type DetailSort = "net_flow" | "change_pct" | "amount";
type DetailFilter = "all" | "net_inflow" | "up";
type MarketCommandTone = "positive" | "caution" | "negative";

const regimeCopy: Record<string, { label: string; action: string }> = {
  risk_off: { label: "防守", action: "先保护本金，机会只保留观察。" },
  cautious: { label: "谨慎", action: "只看板块、量能、价格同时确认的线索。" },
  balanced: { label: "均衡", action: "可以看机会，但不要追涨。" },
  risk_on: { label: "进攻", action: "可以更积极，仍守失效条件。" },
};

export function MarketPage() {
  const [showAllSectors, setShowAllSectors] = useState(false);
  const dossierRef = useRef<HTMLElement | null>(null);
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
  const openSector = (code: string) => {
    const next = new URLSearchParams(params);
    next.set("sector", code);
    next.delete("theme");
    next.delete("themeName");
    next.delete("themeChange");
    setParams(next);
  };
  const closeDossier = () => {
    const next = new URLSearchParams(params);
    next.delete("sector");
    next.delete("theme");
    next.delete("themeName");
    next.delete("themeChange");
    setParams(next, { replace: true });
  };
  const activeDossierKey = selectedTheme ? `theme:${selectedTheme}:${selectedThemeName}` : selectedSector ? `sector:${selectedSector}` : null;
  const activeDossierReady = selectedTheme ? Boolean(themeQuery.data) : selectedSector ? Boolean(sectorQuery.data) : false;

  useEffect(() => {
    if (!activeDossierKey || !activeDossierReady) return;
    const timer = window.setTimeout(() => {
      if (typeof dossierRef.current?.scrollIntoView === "function") {
        dossierRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    }, 0);
    return () => window.clearTimeout(timer);
  }, [activeDossierKey, activeDossierReady]);

  return <AsyncState loading={query.isLoading} error={query.error as Error | null}>{query.data && <>
    <header className="page-head"><div><h1>市场</h1></div><DataStamp meta={query.data.snapshot.meta} /></header>
    <MarketCommandCenter market={query.data} intelligence={intelligenceQuery.data} events={eventsQuery.data} onOpenSector={openSector} />
    <section className="breadth-board" aria-label="市场广度"><div><span>上涨</span><strong className="up">{query.data.analysis.advancing}</strong></div><div><span>下跌</span><strong className="down">{query.data.analysis.declining}</strong></div><div><span>平盘</span><strong>{query.data.analysis.unchanged}</strong></div><div><span>综合温度</span><strong>{fmt(query.data.analysis.score, 0)}</strong></div></section>
    <div className="two-column"><section className="panel"><div className="panel-title"><span>指数</span></div><div className="market-table">{query.data.snapshot.indices.map((item) => <div key={item.symbol}><span>{item.name}</span><b>{fmt(item.price)}</b><i className={(item.change_pct ?? 0) >= 0 ? "up" : "down"}>{pct(item.change_pct)}</i></div>)}</div></section><section className="panel"><div className="panel-title"><span>评分证据</span><small>分数 · 权重 · 事实</small></div><div className="factor-ledger">{query.data.analysis.factors.map((factor) => <article key={factor.key} className={factor.available ? "available" : "missing"}><span>{factor.label}<small>{factor.evidence}</small></span><strong>{factor.available ? fmt(factor.score, 0) : "未计入"}</strong><em>{factor.available ? `权重 ${percent(factor.weight * 100)}` : "权重 0%"}</em></article>)}</div></section></div>
    <section id="market-board-workbench" className="market-board-zone" aria-label="板块和题材工作区">
      <div className="section-bridge"><span>板块</span><strong>板块和题材</strong></div>
      <MarketIntelligencePanel data={intelligenceQuery.data} loading={intelligenceQuery.isLoading} failed={intelligenceQuery.isError} onOpenSector={openSector} />
      <section className="panel" aria-labelledby="sector-heat-title"><div className="panel-title"><span id="sector-heat-title">板块热度</span><small>点击板块查看成分股和简析</small></div><div className="sector-grid">{query.data.snapshot.sectors.slice(0, showAllSectors ? undefined : 12).map((item) => <button key={item.code} className={`sector-card ${selectedSector === item.code ? "active" : ""}`} onClick={() => openSector(item.code)}><span>{item.name}</span><strong className={(item.change_pct ?? 0) >= 0 ? "up" : "down"}>{pct(item.change_pct)}</strong><small>{item.net_flow == null ? "资金流待增强" : `净流入 ${fmt(item.net_flow / 100000000)} 亿`}</small></button>)}</div><div className="panel-actions"><button className="text-button" onClick={() => setShowAllSectors((value) => !value)}>{showAllSectors ? "收起板块" : `查看全部 ${query.data.snapshot.sectors.length} 个板块`}</button><Link className="button" to="/opportunities">按当前市场找机会 →</Link></div></section>
      {selectedSector && <DossierPanel key={`sector-${selectedSector}`} containerRef={dossierRef} data={sectorQuery.data} loading={sectorQuery.isLoading} error={sectorQuery.error as Error | null} variant="sector" onClose={closeDossier} />}
      {selectedTheme && <DossierPanel key={`theme-${selectedTheme}`} containerRef={dossierRef} data={themeQuery.data} loading={themeQuery.isLoading} error={themeQuery.error as Error | null} variant="theme" onClose={closeDossier} />}
    </section>
    <section id="market-events" className="panel event-radar" aria-labelledby="market-events-title">
      <div className="panel-title"><span id="market-events-title">市场异动</span><small>今天股市正在发生什么</small></div>
      <AsyncState loading={eventsQuery.isLoading} error={eventsQuery.error as Error | null}>
        {eventsQuery.data && <MarketEventRadar data={eventsQuery.data} />}
      </AsyncState>
    </section>
    <div id="market-browser" className="market-browser-zone">
      <EquityBrowser />
    </div>
  </>}</AsyncState>;
}

function MarketCommandCenter({ market, intelligence, events, onOpenSector }: { market: MarketData; intelligence?: MarketIntelligenceResult; events?: MarketEventResult; onOpenSector: (code: string) => void }) {
  const regime = regimeCopy[market.analysis.regime] ?? { label: market.analysis.regime, action: "先看市场，再做决定。" };
  const total = Math.max(1, market.analysis.advancing + market.analysis.declining + market.analysis.unchanged);
  const breadth = market.analysis.advancing / total * 100;
  const topFlow = intelligence?.sector_flows[0];
  const riskEvent = events?.events.find((event) => event.sentiment === "negative" || event.category === "risk_alert");
  const eventHeadline = riskEvent?.title ?? events?.summary[0] ?? "暂无显著事件风险，继续以指数、板块和资金为主。";
  const routeText = breadth >= 55 ? "广度占优，优先看资金主线是否扩散。" : breadth >= 45 ? "广度中性，只看强势板块里的少数前排。" : "广度偏弱，候选降级，先处理持仓风险。";
  const command = marketCommandDecision(market, breadth, Boolean(riskEvent), topFlow?.code);
  const mainline = topFlow ? `${topFlow.name} ${pct(topFlow.change_pct)} · ${flowAmount(topFlow.net_flow)}` : "资金主线未确认";

  return <section id="market-gate" className={`market-command-center ${command.tone}`} aria-label="市场概览">
    <article className="market-command-verdict">
      <span>市场</span>
      <strong>{regime.label} · {fmt(market.analysis.score, 0)}/100</strong>
      <b className="market-command-badge">{command.title}</b>
      <p>{regime.action}</p>
      <small>上涨占比 {percent(breadth)} · 置信度 {percent(market.analysis.confidence * 100)}</small>
      <em>大盘</em>
    </article>
    <div className="market-command-stack">
      <div className="market-command-checks" aria-label="盘面三问">
        <span>盘面三问</span>
        <b>宽度够不够：{breadth >= 55 ? "够" : breadth >= 45 ? "勉强" : "不够"}</b>
        <b>主线清不清：{topFlow ? topFlow.name : "待确认"}</b>
        <b>风险挡不挡：{riskEvent ? "先刹车" : "不挡"}</b>
      </div>
      <div className="market-command-grid">
        <article>
          <span>方向</span>
          <strong>{routeText}</strong>
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
        </article>
        <article className="market-command-route">
          <span>下一步</span>
          <Link to={command.href}>{command.action}</Link>
          <p>{command.detail}</p>
        </article>
      </div>
      <div className="market-command-tape">
        <span>摘要</span>
        <strong>{command.title}</strong>
        <p>{command.reason} · 主线：{mainline} · 风险：{riskEvent ? eventHeadline : "暂无强风险新闻"}</p>
      </div>
    </div>
  </section>;
}

function marketCommandDecision(market: MarketData, breadth: number, hasRiskEvent: boolean, topFlowCode?: string): { tone: MarketCommandTone; title: string; action: string; href: string; detail: string; reason: string } {
  if (market.analysis.regime === "risk_off" || hasRiskEvent || breadth < 40 || market.analysis.score < 45) {
    return {
      tone: "negative",
      title: "先守风险",
      action: "检查持仓风险",
      href: "/holdings",
      detail: "大盘偏弱，先看已有仓位、止损线和风险事件。",
      reason: "防守优先，机会只保留观察",
    };
  }
  if (breadth >= 55 && market.analysis.score >= 55) {
    return {
      tone: "positive",
      title: "可以找机会",
      action: "找机会",
      href: "/opportunities",
      detail: "市场宽度与温度同时过线，找板块和个股证据能接住的线索。",
      reason: "宽度过线，可以找候选",
    };
  }
  return {
    tone: "caution",
    title: "只看前排板块",
    action: topFlowCode ? "打开资金主线" : "等待资金确认",
    href: topFlowCode ? `/market?sector=${topFlowCode}` : "/market",
    detail: "大盘不够强，只看资金最强、扩散更清楚的前排。",
    reason: "宽度或温度仍需确认",
  };
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
  if (up && inflow) return "价格与资金同向，优先看";
  if (up && item.net_flow == null) return "价格走强，资金待确认";
  if (inflow) return "资金先动但价格未确认，观察是否补涨";
  if ((item.amount ?? 0) >= 1_000_000_000) return "成交活跃，可作板块样本";
  return "证据较弱，先保留观察";
}

function stockLeadTarget(item: Quote) {
  const up = (item.change_pct ?? 0) > 0;
  const inflow = (item.net_flow ?? 0) > 0;

  if (up && inflow) {
    return {
      anchor: "stock-investment-advice",
      label: "先看交易计划",
      detail: "先看入场、仓位和止损。",
    };
  }
  if (up && item.net_flow == null) {
    return {
      anchor: "stock-evidence-audit",
      label: "先看依据",
      detail: "价格已动但资金缺口待补，先看支持、反方和缺口。",
    };
  }
  if (inflow) {
    return {
      anchor: "stock-final-gate",
      label: "先看结论",
      detail: "资金先动但价格未确认，先判断是否观察。",
    };
  }
  if ((item.amount ?? 0) >= 1_000_000_000) {
    return {
      anchor: "stock-company-evidence",
      label: "先补公告研报",
      detail: "成交活跃但方向证据不足，先核验外部证据。",
    };
  }
  return {
    anchor: "stock-risk-controls",
    label: "先看风控条件",
    detail: "证据较弱，先确认放弃线和反方证据。",
  };
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

function stockHref(item: Quote, source: SectorDossier, suffix: string, anchor = stockLeadTarget(item).anchor) {
  const params = new URLSearchParams({ symbol: item.symbol, from: "market", board: source.sector.code, boardName: source.sector.name, boardType: suffix });
  return `/stocks?${params.toString()}#${anchor}`;
}

function BoardStockLeads({ data, suffix }: { data: SectorDossier; suffix: string }) {
  const leads = [...data.constituents].sort((left, right) => stockLeadScore(right) - stockLeadScore(left)).slice(0, 3);
  if (!leads.length) return null;

  return <section className="board-stock-leads" aria-label={`${data.sector.name}${suffix}优先个股线索`}>
    <div className="board-leads-title">
      <span>个股</span>
      <strong>优先个股</strong>
    </div>
    <div className="board-leads-grid">
      {leads.map((item, index) => {
        const target = stockLeadTarget(item);
        return <Link key={item.symbol} className={stockLeadTone(item)} to={stockHref(item, data, suffix, target.anchor)}>
          <em>{String(index + 1).padStart(2, "0")}</em>
          <span>{item.name}<small>{item.symbol}</small></span>
          <strong className={(item.change_pct ?? 0) >= 0 ? "up" : "down"}>{pct(item.change_pct)}</strong>
          <p>{stockLeadReason(item)}</p>
          <i className="board-lead-route">{target.label}</i>
          <b>{item.net_flow == null ? `成交 ${fmt((item.amount ?? 0) / 100000000)} 亿` : `净流 ${fmt(item.net_flow / 100000000)} 亿`}</b>
        </Link>;
      })}
    </div>
  </section>;
}

function DossierPanel({ data, loading, error, variant, onClose, containerRef }: { data?: SectorDossier; loading: boolean; error: Error | null; variant: "sector" | "theme"; onClose: () => void; containerRef?: RefObject<HTMLElement | null> }) {
  const [sort, setSort] = useState<DetailSort>("net_flow");
  const [filter, setFilter] = useState<DetailFilter>("all");
  const rows = data ? sortedRows(data.constituents, sort, filter) : [];
  const suffix = variant === "theme" ? "题材" : "板块";
  return <section ref={containerRef} className="panel sector-detail">
    <AsyncState loading={loading} error={error}>{data && <>
      <div className="sector-detail-head"><div><span>{variant === "theme" ? "题材" : "板块"}</span><h2>{data.sector.name}{suffix}简析</h2></div><button className="text-button" onClick={onClose}>关闭</button></div>
      <SectorReviewDesk data={data} suffix={suffix} />
      <div className="sector-digest"><article><span>{suffix}涨跌</span><strong className={(data.sector.change_pct ?? 0) >= 0 ? "up" : "down"}>{pct(data.sector.change_pct)}</strong></article><article><span>资金温度</span><strong>{data.sector.net_flow == null ? "待增强" : `${fmt(data.sector.net_flow / 100000000)} 亿`}</strong></article><article><span>证据覆盖</span><strong>{percent(data.evidence_coverage * 100)}</strong></article></div>
      <div className="sector-summary">{data.summary.map((item) => <p key={item}>{item}</p>)}{data.missing_evidence.length > 0 && <small>缺口：{data.missing_evidence.join("、")}</small>}</div>
      <BoardStockLeads data={data} suffix={suffix} />
      <div className="dossier-tools" aria-label={`${data.sector.name}${suffix}筛选`}>
        <label>排序<select aria-label="详情排序" value={sort} onChange={(event) => setSort(event.target.value as DetailSort)}><option value="net_flow">资金优先</option><option value="change_pct">涨幅优先</option><option value="amount">成交额优先</option></select></label>
        <label>范围<select aria-label="详情范围" value={filter} onChange={(event) => setFilter(event.target.value as DetailFilter)}><option value="all">全部</option><option value="net_inflow">只看净流入</option><option value="up">只看上涨</option></select></label>
        <span>显示 {rows.length} / {data.constituents.length}</span>
      </div>
      {rows.length > 0 ? <div className="sector-constituents">{rows.map((item) => {
        const target = stockLeadTarget(item);
        return <Link key={item.symbol} to={stockHref(item, data, suffix, target.anchor)}><span><b>{item.name}</b><small>{item.symbol}</small></span><strong className={(item.change_pct ?? 0) >= 0 ? "up" : "down"}>{pct(item.change_pct)}</strong><em>{item.net_flow == null ? `成交 ${fmt((item.amount ?? 0) / 100000000)} 亿` : `净流 ${fmt(item.net_flow / 100000000)} 亿`}</em><p>{stockLeadReason(item)}</p><small className="stock-route-hint">{target.label}</small></Link>;
      })}</div> : <div className="empty">当前筛选下没有相关股票。</div>}
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
    ? "主线可继续看"
    : tone === "negative"
      ? "扩散不足，先降级观察"
      : "只看前排，等待确认";

  return <section className={`sector-review-desk ${tone}`} aria-label={`${data.sector.name}${suffix}简析`}>
    <article className="sector-review-verdict">
      <span>板块</span>
      <strong>{verdict}</strong>
      <p>{data.summary[0] ?? `${data.sector.name}${suffix}需要继续补充价格、资金和成分股证据。`}</p>
    </article>
    <div className="sector-review-grid">
      <article>
        <span>上涨扩散</span>
        <strong>{rising} / {total}</strong>
        <p>{percent(risingRatio)} 成分上涨。</p>
      </article>
      <article>
        <span>净流入扩散</span>
        <strong>{inflow} / {total}</strong>
        <p>{data.sector.net_flow == null ? "资金证据待增强。" : `${percent(inflowRatio)} 成分净流入，板块净流 ${flowAmount(data.sector.net_flow)}。`}</p>
      </article>
      <article>
        <span>领涨核心</span>
        {topGain ? <Link to={`/stocks?symbol=${topGain.symbol}`}>{topGain.name}<small>{pct(topGain.change_pct)}</small></Link> : <strong>暂无</strong>}
        <p>强于板块优先。</p>
      </article>
      <article>
        <span>资金核心</span>
        {topFlow && topFlow.net_flow != null ? <Link to={`/stocks?symbol=${topFlow.symbol}`}>{topFlow.name}<small>{flowAmount(topFlow.net_flow)}</small></Link> : <strong>待增强</strong>}
        <p>{data.missing_evidence.length ? `缺口：${data.missing_evidence.join("、")}` : "与领涨核心交叉确认。"}</p>
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
    <div className="panel-title"><span>A 股市场情报</span><small>板块资金 + 交易异动</small></div>
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
  </>;
}

function formatEventTime(value: string): string {
  return new Date(value).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
}
