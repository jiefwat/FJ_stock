import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { AsyncState } from "../../components/AsyncState";
import { DataStamp } from "../../components/DataStamp";
import { api, fmt, pct, percent, type Analysis, type IndexQuote, type Meta, type Sector, type SectorDossier } from "../../lib/api";

type MarketData = { snapshot: { meta: Meta; indices: IndexQuote[]; sectors: Sector[] }; analysis: Analysis };

export function MarketPage() {
  const [showAllSectors, setShowAllSectors] = useState(false);
  const [params, setParams] = useSearchParams();
  const selectedSector = params.get("sector");
  const query = useQuery({ queryKey: ["market"], queryFn: () => api<MarketData>("/api/v1/market") });
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
    <section className="panel"><div className="panel-title"><span>板块热度</span><small>点击板块查看成分股和简析</small></div><div className="sector-grid">{query.data.snapshot.sectors.slice(0, showAllSectors ? undefined : 12).map((item) => <button key={item.code} className={`sector-card ${selectedSector === item.code ? "active" : ""}`} onClick={() => openSector(item.code)}><span>{item.name}</span><strong className={(item.change_pct ?? 0) >= 0 ? "up" : "down"}>{pct(item.change_pct)}</strong><small>{item.net_flow == null ? "资金流待增强" : `净流入 ${fmt(item.net_flow / 100000000)} 亿`}</small></button>)}</div><div className="panel-actions"><button className="text-button" onClick={() => setShowAllSectors((value) => !value)}>{showAllSectors ? "收起板块" : `查看全部 ${query.data.snapshot.sectors.length} 个板块`}</button><Link className="button" to="/opportunities">按当前市场找机会 →</Link></div></section>
    {selectedSector && <section className="panel sector-detail"><AsyncState loading={sectorQuery.isLoading} error={sectorQuery.error as Error | null}>{sectorQuery.data && <>
      <div className="sector-detail-head"><div><span>SECTOR DOSSIER</span><h2>{sectorQuery.data.sector.name}板块简析</h2></div><button className="text-button" onClick={() => setParams({})}>关闭</button></div>
      <div className="sector-digest"><article><span>板块涨跌</span><strong className={(sectorQuery.data.sector.change_pct ?? 0) >= 0 ? "up" : "down"}>{pct(sectorQuery.data.sector.change_pct)}</strong></article><article><span>资金温度</span><strong>{sectorQuery.data.sector.net_flow == null ? "待增强" : `${fmt(sectorQuery.data.sector.net_flow / 100000000)} 亿`}</strong></article><article><span>证据覆盖</span><strong>{percent(sectorQuery.data.evidence_coverage * 100)}</strong></article></div>
      <div className="sector-summary">{sectorQuery.data.summary.map((item) => <p key={item}>{item}</p>)}{sectorQuery.data.missing_evidence.length > 0 && <small>缺口：{sectorQuery.data.missing_evidence.join("、")}</small>}</div>
      <div className="sector-constituents">{sectorQuery.data.constituents.map((item) => <Link key={item.symbol} to={`/stocks?symbol=${item.symbol}`}><span><b>{item.name}</b><small>{item.symbol}</small></span><strong className={(item.change_pct ?? 0) >= 0 ? "up" : "down"}>{pct(item.change_pct)}</strong><em>{item.net_flow == null ? `成交 ${fmt((item.amount ?? 0) / 100000000)} 亿` : `净流 ${fmt(item.net_flow / 100000000)} 亿`}</em></Link>)}</div>
    </>}</AsyncState></section>}
  </>}</AsyncState>;
}
