import { ArrowUpRight, Gauge, Radar, ShieldAlert } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { AsyncState } from "../../components/AsyncState";
import { DataStamp } from "../../components/DataStamp";
import { api, fmt, pct, percent, type TodayData } from "../../lib/api";

const regimeLabel: Record<string, string> = { risk_off: "防守", cautious: "谨慎", balanced: "均衡", risk_on: "积极" };
const actionRoutes = ["/market", "/market", "/opportunities"];

export function TodayPage() {
  const query = useQuery({ queryKey: ["today"], queryFn: () => api<TodayData>("/api/v1/today") });
  return <AsyncState loading={query.isLoading} error={query.error as Error | null}>{query.data && <>
    <header className="page-head reveal">
      <div><p className="eyebrow">TODAY / 决策起点</p><h1>先判断环境，<br /><em>再寻找机会。</em></h1></div>
      <DataStamp meta={query.data.meta} />
    </header>
    <section className="risk-rail reveal delay-1">
      <div className="rail-score"><span>{fmt(query.data.analysis.score, 0)}</span><small>/ 100 市场温度</small></div>
      <div className="rail-track"><i style={{ width: `${query.data.analysis.score}%` }} /></div>
      <div className="rail-cell"><Gauge size={18} /><span>市场状态</span><strong>{regimeLabel[query.data.analysis.regime]}</strong></div>
      <div className="rail-cell"><ShieldAlert size={18} /><span>风险控制参考</span><strong>{query.data.risk_budget}%</strong></div>
      <div className="rail-cell"><Radar size={18} /><span>证据完整度</span><strong>{percent(query.data.analysis.confidence * 100)}</strong></div>
    </section>
    <p className="risk-caption">风险控制参考用于研究分层，不是仓位或交易建议。机会分会根据当前市场环境自动扣减。</p>
    <section className="market-evidence-strip"><div><span>为什么是这个市场状态</span><small>已按可用数据重新分配权重</small></div>{query.data.analysis.factors.filter((factor) => factor.available).slice(0, 3).map((factor) => <article key={factor.key}><span>{factor.label}</span><strong>{fmt(factor.score, 0)}</strong><small>{factor.evidence}</small></article>)}</section>
    <div className="dashboard-grid reveal delay-2">
      <section className="panel index-panel"><div className="panel-title"><span>指数脊柱</span><Link to="/market">展开市场 <ArrowUpRight size={14} /></Link></div><div className="index-list">{query.data.indices.map((index) => <article key={index.symbol}><span>{index.name}</span><strong>{fmt(index.price)}</strong><b className={(index.change_pct ?? 0) >= 0 ? "up" : "down"}>{pct(index.change_pct)}</b></article>)}</div></section>
      <section className="panel actions-panel"><div className="panel-title"><span>今天先做什么</span><small>按顺序推进</small></div><ol>{query.data.next_actions.map((action, index) => <li key={action}><Link to={actionRoutes[index] ?? "/opportunities"}><i>{index + 1}</i><span>{action}</span><ArrowUpRight size={14} /></Link></li>)}</ol></section>
      <section className="panel sector-panel"><div className="panel-title"><span>板块温度</span><Link to="/opportunities">进入机会漏斗</Link></div><div className="sector-strip">{query.data.sectors.map((sector) => <div key={sector.code} className={(sector.change_pct ?? 0) >= 0 ? "heat-up" : "heat-down"}><span>{sector.name}</span><strong>{pct(sector.change_pct)}</strong></div>)}</div></section>
      <section className="panel candidate-panel"><div className="panel-title"><span>优先核对</span><small>已计入市场环境扣分</small></div>{query.data.top_opportunities.length ? query.data.top_opportunities.map((item) => <Link className="candidate-row" key={item.quote.symbol} to={`/stocks?symbol=${item.quote.symbol}`}><span><b>{item.quote.name}</b><small>{item.quote.symbol}</small></span><strong>{fmt(item.score, 0)}</strong><i>{pct(item.quote.change_pct)}</i></Link>) : <div className="empty">当前没有通过全部门槛的候选。先查看市场风险与排除原因。</div>}</section>
    </div>
  </>}</AsyncState>;
}
