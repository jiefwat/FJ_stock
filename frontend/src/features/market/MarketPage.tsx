import { useQuery } from "@tanstack/react-query";
import { lazy, Suspense, useEffect, useRef, useState, type RefObject } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { AsyncState } from "../../components/AsyncState";
import { DataStamp } from "../../components/DataStamp";
import { api, fmt, pct, percent, type Analysis, type IndexQuote, type MarketEvent, type MarketEventResult, type MarketIntelligenceResult, type Meta, type Quote, type Sector, type SectorDossier } from "../../lib/api";
import { plainLanguage } from "../../lib/plainLanguage";

type MarketData = { snapshot: { meta: Meta; indices: IndexQuote[]; sectors: Sector[] }; analysis: Analysis };
type DetailSort = "net_flow" | "change_pct" | "amount";
type DetailFilter = "all" | "net_inflow" | "up";

const EquityBrowser = lazy(() => import("./EquityBrowser").then((module) => ({ default: module.EquityBrowser })));
const browserParamKeys = [
  "q",
  "industry",
  "min_change_pct",
  "max_change_pct",
  "min_amount",
  "max_amount",
  "min_turnover_rate",
  "max_turnover_rate",
  "min_market_cap",
  "max_market_cap",
  "complete_only",
  "sort_by",
  "direction",
  "page_size",
  "page",
] as const;

function hasBrowserParams(params: URLSearchParams) {
  return browserParamKeys.some((key) => params.has(key));
}

export function MarketPage() {
  const [showAllSectors, setShowAllSectors] = useState(false);
  const dossierRef = useRef<HTMLElement | null>(null);
  const [params, setParams] = useSearchParams();
  const selectedSector = params.get("sector");
  const selectedTheme = params.get("theme");
  const selectedThemeName = params.get("themeName") ?? selectedTheme ?? "";
  const selectedThemeChange = params.get("themeChange");
  const query = useQuery({ queryKey: ["market"], queryFn: () => api<MarketData>("/api/v1/market") });
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
    <MarketDecisionBanner market={query.data} />
    <MarketPulseStrip market={query.data} />
    <section id="market-board-workbench" className="market-board-zone" aria-label="板块和题材工作区">
      <div className="section-bridge"><span>板块</span><strong>板块和题材</strong></div>
      <div className="market-board-grid" aria-label="板块与资金主线">
        <MarketIntelligencePanel data={intelligenceQuery.data} loading={intelligenceQuery.isLoading} failed={intelligenceQuery.isError} onOpenSector={openSector} />
        <section className="panel sector-heat-panel" aria-labelledby="sector-heat-title"><div className="panel-title"><span id="sector-heat-title">板块热度</span><small>点击板块查看成分股和简析</small></div><div className="sector-grid">{query.data.snapshot.sectors.slice(0, showAllSectors ? undefined : 12).map((item) => <button key={item.code} className={`sector-card ${selectedSector === item.code ? "active" : ""}`} onClick={() => openSector(item.code)}><span>{item.name}</span><strong className={(item.change_pct ?? 0) >= 0 ? "up" : "down"}>{pct(item.change_pct)}</strong><small>{item.net_flow == null ? "资金情况待补" : `${item.net_flow >= 0 ? "买入资金更多" : "卖出资金更多"} ${fmt(Math.abs(item.net_flow) / 100000000)} 亿`}</small></button>)}</div><div className="panel-actions"><button className="text-button" onClick={() => setShowAllSectors((value) => !value)}>{showAllSectors ? "收起板块" : `查看全部 ${query.data.snapshot.sectors.length} 个板块`}</button><Link className="button" to="/opportunities">查看候选决策 →</Link></div></section>
      </div>
      {selectedSector && <DossierPanel key={`sector-${selectedSector}`} containerRef={dossierRef} data={sectorQuery.data} loading={sectorQuery.isLoading} error={sectorQuery.error as Error | null} variant="sector" onClose={closeDossier} />}
      {selectedTheme && <DossierPanel key={`theme-${selectedTheme}`} containerRef={dossierRef} data={themeQuery.data} loading={themeQuery.isLoading} error={themeQuery.error as Error | null} variant="theme" onClose={closeDossier} />}
    </section>
    <DeferredMarketEvents />
    <DeferredEquityBrowser params={params} />
  </>}</AsyncState>;
}

function DeferredMarketEvents() {
  const containerRef = useRef<HTMLElement | null>(null);
  const [shouldLoad, setShouldLoad] = useState(() => (
    typeof window === "undefined"
    || typeof IntersectionObserver !== "function"
    || window.location.hash === "#market-events"
  ));
  const eventsQuery = useQuery({
    queryKey: ["market-events"],
    queryFn: () => api<MarketEventResult>("/api/v1/market-events?limit=30"),
    enabled: shouldLoad,
    staleTime: 120_000,
  });

  useEffect(() => {
    if (shouldLoad || typeof IntersectionObserver !== "function") return undefined;
    const node = containerRef.current;
    if (!node) return undefined;
    const observer = new IntersectionObserver((entries) => {
      if (!entries.some((entry) => entry.isIntersecting)) return;
      setShouldLoad(true);
      observer.disconnect();
    }, { rootMargin: "360px 0px" });
    observer.observe(node);
    return () => observer.disconnect();
  }, [shouldLoad]);

  return <section ref={containerRef} id="market-events" className="panel event-radar" aria-labelledby="market-events-title">
    <div className="panel-title"><span id="market-events-title">市场异动</span><small>今天股市正在发生什么</small></div>
    {shouldLoad ? <AsyncState loading={eventsQuery.isLoading} error={eventsQuery.error as Error | null}>
      {eventsQuery.data && <MarketEventRadar data={eventsQuery.data} />}
    </AsyncState> : <div className="market-events-placeholder" role="status">市场异动待加载</div>}
  </section>;
}

function DeferredEquityBrowser({ params }: { params: URLSearchParams }) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [shouldLoad, setShouldLoad] = useState(() => hasBrowserParams(params) || window.location.hash === "#market-browser");

  useEffect(() => {
    if (hasBrowserParams(params) || window.location.hash === "#market-browser") setShouldLoad(true);
  }, [params]);

  useEffect(() => {
    if (shouldLoad || typeof IntersectionObserver !== "function") return undefined;
    const node = containerRef.current;
    if (!node) return undefined;
    const observer = new IntersectionObserver((entries) => {
      if (!entries.some((entry) => entry.isIntersecting)) return;
      setShouldLoad(true);
      observer.disconnect();
    }, { rootMargin: "420px 0px" });
    observer.observe(node);
    return () => observer.disconnect();
  }, [shouldLoad]);

  return <div ref={containerRef} id="market-browser" className="market-browser-zone">
    {shouldLoad ? <Suspense fallback={<section className="panel market-browser-placeholder" aria-label="全市场行情" role="status"><span>全市场行情</span></section>}>
      <EquityBrowser />
    </Suspense> : <section className="panel market-browser-placeholder" aria-label="全市场行情">
      <span>全市场行情</span>
      <button className="button secondary" type="button" onClick={() => setShouldLoad(true)}>查看全市场行情（可选）</button>
    </section>}
  </div>;
}

function MarketPulseStrip({ market }: { market: MarketData }) {
  const total = Math.max(1, market.analysis.advancing + market.analysis.declining + market.analysis.unchanged);
  const breadth = market.analysis.advancing / total * 100;
  const primaryIndices = market.snapshot.indices.slice(0, 4);

  return <section className="market-pulse-strip market-pulse-airy" aria-label="大盘速览">
    <div className="pulse-breadth" aria-label="市场宽度速览">
      <article><span>上涨</span><strong className="up">{market.analysis.advancing}</strong></article>
      <article><span>下跌</span><strong className="down">{market.analysis.declining}</strong></article>
      <article><span>广度</span><strong>{percent(breadth)}</strong></article>
      <article><span>温度</span><strong>{fmt(market.analysis.score, 0)}</strong></article>
    </div>
    <div className="pulse-indices" aria-label="核心指数">
      <header><span>指数</span><small>只看核心市场</small></header>
      {primaryIndices.map((item) => <div key={item.symbol}><span>{item.name}</span><b>{fmt(item.price)}</b><i className={(item.change_pct ?? 0) >= 0 ? "up" : "down"}>{pct(item.change_pct)}</i></div>)}
    </div>
  </section>;
}

function MarketDecisionBanner({ market }: { market: MarketData }) {
  const { advancing, declining, score } = market.analysis;
  const defensive = score < 45 || declining > advancing * 1.3;
  const constructive = score >= 65 && advancing > declining;
  const tone = defensive ? "negative" : constructive ? "positive" : "caution";
  const action = defensive ? "今天以防守为主" : constructive ? "允许小仓参与强势股" : "今天只做少量试探";
  const allowed = defensive ? "只处理已持仓风险，不开新仓" : constructive ? "只参与板块和资金同时支持的前排股票" : "只选“可小仓试探”候选";
  const forbidden = defensive ? "不补仓、不抄底、不等待反弹证明判断" : "不追涨，不因为单日上涨临时加大仓位";
  const change = defensive ? "上涨股票明显多于下跌股票，且市场温度回到 45 以上" : "下跌股票明显增多，或市场温度跌破 45";

  return <section className={`market-decision-banner ${tone}`} aria-label="今天的市场决定">
    <article><span>今天怎么做</span><strong>{action}</strong><p>{allowed}</p></article>
    <div><span>不要做</span><strong>{forbidden}</strong></div>
    <div><span>什么情况改变决定</span><strong>{change}</strong></div>
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
  if (up && inflow) return "股价上涨且买入资金更多，还要看看能否持续";
  if (up && item.net_flow == null) return "股价在涨，但资金情况还不清楚";
  if (inflow) return "买入资金先增加，股价还没跟上，继续观察";
  if ((item.amount ?? 0) >= 1_000_000_000) return "成交活跃，可作板块样本";
  return "支持信息较少，先保留观察";
}

function stockLeadTarget(item: Quote) {
  const up = (item.change_pct ?? 0) > 0;
  const inflow = (item.net_flow ?? 0) > 0;

  if (up && inflow) {
    return {
      anchor: "stock-investment-advice",
      label: "可小仓试探",
      detail: "价格和买入资金同时走强；参与时仍要控制仓位和退出条件。",
    };
  }
  if (up && item.net_flow == null) {
    return {
      anchor: "stock-evidence-audit",
      label: "暂不买入",
      detail: "价格已动，资金依据不足。",
    };
  }
  if (inflow) {
    return {
      anchor: "stock-final-gate",
      label: "继续观察",
      detail: "买入资金先增加，但价格还没有确认。",
    };
  }
  if ((item.amount ?? 0) >= 1_000_000_000) {
    return {
      anchor: "stock-company-evidence",
      label: "仅作样本",
      detail: "成交活跃但方向不明确，不作为买入候选。",
    };
  }
  return {
    anchor: "stock-risk-controls",
    label: "暂不参与",
      detail: "支持信息较少，暂不操作。",
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
      <div className="sector-digest"><article><span>{suffix}涨跌</span><strong className={(data.sector.change_pct ?? 0) >= 0 ? "up" : "down"}>{pct(data.sector.change_pct)}</strong></article><article><span>资金温度</span><strong>{data.sector.net_flow == null ? "待补" : `${fmt(data.sector.net_flow / 100000000)} 亿`}</strong></article><article><span>信息完整度</span><strong>{percent(data.evidence_coverage * 100)}</strong></article></div>
      <div className="sector-summary">{data.summary.map((item) => <p key={item}>{plainLanguage(item)}</p>)}{data.missing_evidence.length > 0 && <small>还缺：{data.missing_evidence.map(plainLanguage).join("、")}</small>}</div>
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
    ? "可以小仓关注前排"
    : tone === "negative"
      ? "扩散不足，暂不参与"
      : "暂不买入";

  return <section className={`sector-review-desk ${tone}`} aria-label={`${data.sector.name}${suffix}简析`}>
    <article className="sector-review-verdict">
      <span>板块</span>
      <strong>{verdict}</strong>
      <p>{plainLanguage(data.summary[0] ?? `${data.sector.name}${suffix}还要补充价格、资金和成分股信息。`)}</p>
    </article>
    <div className="sector-review-grid">
      <article>
        <span>上涨扩散</span>
        <strong>{rising} / {total}</strong>
        <p>{percent(risingRatio)} 成分上涨。</p>
      </article>
      <article>
        <span>获得资金买入的股票</span>
        <strong>{inflow} / {total}</strong>
        <p>{data.sector.net_flow == null ? "资金情况待补。" : `${percent(inflowRatio)} 的股票买入资金更多，板块合计 ${flowAmount(data.sector.net_flow)}。`}</p>
      </article>
      <article>
        <span>领涨核心</span>
        {topGain ? <Link to={`/stocks?symbol=${topGain.symbol}`}>{topGain.name}<small>{pct(topGain.change_pct)}</small></Link> : <strong>暂无</strong>}
        <p>强于板块优先。</p>
      </article>
      <article>
        <span>资金最关注</span>
        {topFlow && topFlow.net_flow != null ? <Link to={`/stocks?symbol=${topFlow.symbol}`}>{topFlow.name}<small>{flowAmount(topFlow.net_flow)}</small></Link> : <strong>待增强</strong>}
        <p>{data.missing_evidence.length ? `待补资料：${data.missing_evidence.map(plainLanguage).join("、")}` : "筛选条件：涨幅与资金流均靠前。"}</p>
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
  const leadFlow = data?.sector_flows[0];
  const restFlows = data?.sector_flows.slice(1, 8) ?? [];
  const leadAnomaly = data?.anomalies[0];
  const restAnomalies = data?.anomalies.slice(1, 8) ?? [];

  return <section className="panel market-intelligence" aria-label="A股市场情报">
    <div className="panel-title"><span>A 股市场情报</span><small>板块资金 + 交易异动</small></div>
    {loading && <div className="capability-empty">正在读取市场情报…</div>}
    {failed && <div className="capability-warning">市场情报暂不可用，指数、广度与全市场行情仍可继续使用。</div>}
    {data && <div className="intelligence-grid">
      <div className="flow-leaders">
        <header><span>板块资金确认</span><b>{data.sector_flows.length} 个</b></header>
        {data.capabilities.sector_flows?.status === "unavailable" && <p className="capability-warning">板块资金源暂不可用。</p>}
        {leadFlow && <button className="flow-hero-card" type="button" onClick={() => onOpenSector(leadFlow.code)}>
          <em>01</em>
          <span><b>{leadFlow.name}</b><small>{pct(leadFlow.change_pct)} · 主线资金</small></span>
          <strong className={(leadFlow.net_flow ?? 0) >= 0 ? "up" : "down"}>{flowAmount(leadFlow.net_flow)}</strong>
        </button>}
        <div className="flow-leader-list">
          {restFlows.map((sector, index) => <button key={sector.code} type="button" onClick={() => onOpenSector(sector.code)}>
            <em>{String(index + 2).padStart(2, "0")}</em>
            <span>{sector.name}<small>{pct(sector.change_pct)}</small></span>
            <strong className={(sector.net_flow ?? 0) >= 0 ? "up" : "down"}>{flowAmount(sector.net_flow)}</strong>
          </button>)}
        </div>
      </div>
      <div className="anomaly-list">
        <header><span>龙虎榜观察</span><b>{data.anomalies.length} 条</b></header>
        {data.capabilities.dragon_tiger?.status === "unavailable" && <p className="capability-warning">龙虎榜源暂不可用，不能据空结果判断当天没有异动。</p>}
        {leadAnomaly && <article className="anomaly-hero-card" key={`${leadAnomaly.trade_date}-${leadAnomaly.symbol}`}>
          <time>{leadAnomaly.trade_date.slice(5)}</time>
          <div><Link to={`/stocks?symbol=${leadAnomaly.symbol}`}>{leadAnomaly.name} <small>{leadAnomaly.symbol}</small></Link><p>{leadAnomaly.reason}</p></div>
          <strong className={(leadAnomaly.net_buy ?? 0) >= 0 ? "up" : "down"}>{flowAmount(leadAnomaly.net_buy)}</strong>
        </article>}
        <div className="anomaly-rows">
          {restAnomalies.map((item, index) => <article key={`${item.trade_date}-${item.symbol}-${index}`}>
            <time>{item.trade_date.slice(5)}</time>
            <div><Link to={`/stocks?symbol=${item.symbol}`}>{item.name} <small>{item.symbol}</small></Link><p>{item.reason}</p></div>
            <strong className={(item.net_buy ?? 0) >= 0 ? "up" : "down"}>{flowAmount(item.net_buy)}</strong>
          </article>)}
        </div>
      </div>
    </div>}
  </section>;
}

const genericEventTitles = new Set(["政策与监管", "资金与风格", "公司动作", "行业催化", "风险扰动", "宏观与海外", "其他热点"]);
const genericEventTags = new Set(["政策支持", "资金风格"]);

function eventHeadline(event: MarketEvent) {
  const title = event.title.trim();
  if (!genericEventTitles.has(title)) return title;
  return plainLanguage((event.summary.split(/[。！？；]/)[0] || title).trim());
}

function eventTags(event: MarketEvent) {
  const headline = eventHeadline(event);
  return event.tags.filter((tag) => {
    const normalized = tag.trim();
    return normalized && normalized !== headline && normalized !== event.title.trim() && !genericEventTitles.has(normalized) && !genericEventTags.has(normalized);
  });
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
        <small>{cluster.count} 条 · {plainLanguage(cluster.summary)}</small>
      </article>)}
    </div>
    <div className="event-tape">
      {data.events.slice(0, 8).map((event) => <article key={event.id} className={event.sentiment}>
        <time>{formatEventTime(event.published_at)}<small>{event.source}</small></time>
        <div>
          <header>
            <h3>{event.url ? <a href={event.url} target="_blank" rel="noreferrer">{eventHeadline(event)}</a> : eventHeadline(event)}</h3>
            <b>{fmt(event.importance_score, 0)}</b>
          </header>
          <p>{plainLanguage(event.summary)}</p>
          {eventTags(event).length > 0 && <div className="event-tags">{eventTags(event).map((tag) => <span key={tag}>{tag}</span>)}</div>}
        </div>
      </article>)}
    </div>
  </>;
}

function formatEventTime(value: string): string {
  return new Date(value).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
}
