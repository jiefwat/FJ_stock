import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";

import { AsyncState } from "../../components/AsyncState";
import { DataStamp } from "../../components/DataStamp";
import { api, fmt, pct, percent, type Analysis, type IndexQuote, type Meta, type Sector } from "../../lib/api";

type MarketData = { snapshot: { meta: Meta; indices: IndexQuote[]; sectors: Sector[] }; analysis: Analysis };

export function MarketPage() {
  const [showAllSectors, setShowAllSectors] = useState(false);
  const query = useQuery({ queryKey: ["market"], queryFn: () => api<MarketData>("/api/v1/market") });
  return <AsyncState loading={query.isLoading} error={query.error as Error | null}>{query.data && <>
    <header className="page-head"><div><p className="eyebrow">MARKET / 全市场体检</p><h1>市场不是一个点数，<br /><em>而是一组证据。</em></h1></div><DataStamp meta={query.data.snapshot.meta} /></header>
    <section className="breadth-board"><div><span>上涨</span><strong className="up">{query.data.analysis.advancing}</strong></div><div><span>下跌</span><strong className="down">{query.data.analysis.declining}</strong></div><div><span>平盘</span><strong>{query.data.analysis.unchanged}</strong></div><div><span>综合温度</span><strong>{fmt(query.data.analysis.score, 0)}</strong></div></section>
    <div className="two-column"><section className="panel"><div className="panel-title"><span>指数</span></div><div className="market-table">{query.data.snapshot.indices.map((item) => <div key={item.symbol}><span>{item.name}</span><b>{fmt(item.price)}</b><i className={(item.change_pct ?? 0) >= 0 ? "up" : "down"}>{pct(item.change_pct)}</i></div>)}</div></section><section className="panel"><div className="panel-title"><span>评分证据</span><small>分数 · 权重 · 事实</small></div><div className="factor-ledger">{query.data.analysis.factors.map((factor) => <article key={factor.key} className={factor.available ? "available" : "missing"}><span>{factor.label}<small>{factor.evidence}</small></span><strong>{factor.available ? fmt(factor.score, 0) : "未计入"}</strong><em>{factor.available ? `权重 ${percent(factor.weight * 100)}` : "权重 0%"}</em></article>)}</div></section></div>
    <section className="panel"><div className="panel-title"><span>板块热度</span><small>默认展示前 12 个，避免信息淹没</small></div><div className="sector-grid">{query.data.snapshot.sectors.slice(0, showAllSectors ? undefined : 12).map((item) => <article key={item.code}><span>{item.name}</span><strong className={(item.change_pct ?? 0) >= 0 ? "up" : "down"}>{pct(item.change_pct)}</strong><small>{item.net_flow == null ? "资金数据暂缺" : `净流入 ${fmt(item.net_flow / 100000000)} 亿`}</small></article>)}</div><div className="panel-actions"><button className="text-button" onClick={() => setShowAllSectors((value) => !value)}>{showAllSectors ? "收起板块" : `查看全部 ${query.data.snapshot.sectors.length} 个板块`}</button><Link className="button" to="/opportunities">按当前市场找机会 →</Link></div></section>
  </>}</AsyncState>;
}
