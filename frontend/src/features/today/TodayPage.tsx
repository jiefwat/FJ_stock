import { ArrowUpRight, Gauge, Radar, ShieldAlert } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { AsyncState } from "../../components/AsyncState";
import { DataStamp } from "../../components/DataStamp";
import { api, fmt, pct, percent, type MarketEventResult, type TodayData } from "../../lib/api";

const regimeLabel: Record<string, string> = { risk_off: "防守", cautious: "谨慎", balanced: "均衡", risk_on: "积极" };
const actionRoutes = ["/market", "/market", "/opportunities"];

export function TodayPage() {
  const query = useQuery({ queryKey: ["today"], queryFn: () => api<TodayData>("/api/v1/today") });
  const eventsQuery = useQuery({ queryKey: ["market-events", "today"], queryFn: () => api<MarketEventResult>("/api/v1/market-events?limit=8") });
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
    <section className="panel today-events reveal delay-2">
      <div className="panel-title"><span>今日市场异动</span><Link to="/market">查看完整雷达 <ArrowUpRight size={14} /></Link></div>
      <AsyncState loading={eventsQuery.isLoading} error={eventsQuery.error as Error | null}>
        {eventsQuery.data && <div className="today-event-board">
          <div className="today-event-main">
            <span>{eventsQuery.data.clusters[0]?.label ?? "新闻雷达"}</span>
            <strong>{eventsQuery.data.events[0]?.title ?? "暂无异动新闻"}</strong>
            <p>{eventsQuery.data.summary[0] ?? "先以指数、板块温度、资金流确认今天的市场主线。"}</p>
          </div>
          <div className="today-event-list">
            {eventsQuery.data.events.slice(1, 4).map((event) => <Link key={event.id} to="/market">
              <span>{new Date(event.published_at).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" })}</span>
              <b>{event.title}</b>
              <small>{event.impact}</small>
            </Link>)}
            {eventsQuery.data.events.length <= 1 && eventsQuery.data.next_actions.slice(0, 2).map((action) => <Link key={action} to="/market">
              <span>复盘</span>
              <b>{action}</b>
              <small>把新闻和板块温度、资金流、个股证据放在一起确认。</small>
            </Link>)}
          </div>
        </div>}
      </AsyncState>
    </section>
    {eventsQuery.data && <section className="panel daily-playbook reveal delay-2">
      <div className="panel-title"><span>今日投研路线图</span><small>把信息变成动作，不追着噪音跑</small></div>
      <div className="playbook-grid">
        <article>
          <span>先看主线</span>
          <strong>{eventsQuery.data.clusters[0]?.label ?? regimeLabel[query.data.analysis.regime]}</strong>
          <p>{eventsQuery.data.summary[0] ?? "先判断指数强弱、板块扩散和成交额是否配合。"}</p>
          <Link to="/market">去大盘核验 →</Link>
        </article>
        <article>
          <span>风险哨兵</span>
          <strong>{riskHeadline(eventsQuery.data) ?? `${regimeLabel[query.data.analysis.regime]}环境`}</strong>
          <p>{riskBrief(eventsQuery.data, query.data.analysis.regime)}</p>
          <Link to="/holdings">检查持仓暴露 →</Link>
        </article>
        <article>
          <span>机会入口</span>
          <strong>{query.data.top_opportunities[0]?.quote.name ?? "先等候选收敛"}</strong>
          <p>{query.data.top_opportunities[0] ? "只看新闻还不够，下一步要打开候选股的证据账本，确认趋势、资金、估值和失效条件。" : "当前候选不足时，先复核市场状态，不强行找机会。"}</p>
          <Link to="/opportunities">打开机会漏斗 →</Link>
        </article>
        <article>
          <span>复盘清单</span>
          <strong>收盘前再问三句</strong>
          <p>热点有没有扩散？资金有没有持续？持仓和候选有没有被风险新闻影响？三项不齐，不把新闻当结论。</p>
          <Link to="/watchlist">整理跟踪清单 →</Link>
        </article>
      </div>
    </section>}
    <div className="dashboard-grid reveal delay-2">
      <section className="panel index-panel"><div className="panel-title"><span>指数脊柱</span><Link to="/market">展开市场 <ArrowUpRight size={14} /></Link></div><div className="index-list">{query.data.indices.map((index) => <article key={index.symbol}><span>{index.name}</span><strong>{fmt(index.price)}</strong><b className={(index.change_pct ?? 0) >= 0 ? "up" : "down"}>{pct(index.change_pct)}</b></article>)}</div></section>
      <section className="panel actions-panel"><div className="panel-title"><span>今天先做什么</span><small>按顺序推进</small></div><ol>{query.data.next_actions.map((action, index) => <li key={action}><Link to={actionRoutes[index] ?? "/opportunities"}><i>{index + 1}</i><span>{action}</span><ArrowUpRight size={14} /></Link></li>)}</ol></section>
      <section className="panel sector-panel"><div className="panel-title"><span>板块温度</span><Link to="/opportunities">进入机会漏斗</Link></div><div className="sector-strip">{query.data.sectors.map((sector) => <Link key={sector.code} to={`/market?sector=${sector.code}`} className={(sector.change_pct ?? 0) >= 0 ? "heat-up" : "heat-down"}><span>{sector.name}</span><strong>{pct(sector.change_pct)}</strong></Link>)}</div></section>
      <section className="panel candidate-panel"><div className="panel-title"><span>优先核对</span><small>已计入市场环境扣分</small></div>{query.data.top_opportunities.length ? query.data.top_opportunities.map((item) => <Link className="candidate-row" key={item.quote.symbol} to={`/stocks?symbol=${item.quote.symbol}`}><span><b>{item.quote.name}</b><small>{item.quote.symbol}</small></span><strong>{fmt(item.score, 0)}</strong><i>{pct(item.quote.change_pct)}</i></Link>) : <div className="empty">当前没有通过全部门槛的候选。先查看市场风险与排除原因。</div>}</section>
    </div>
  </>}</AsyncState>;
}

function riskHeadline(data: MarketEventResult): string | null {
  return data.events.find((event) => event.sentiment === "negative" || event.category === "risk_alert")?.title ?? null;
}

function riskBrief(data: MarketEventResult, regime: string): string {
  const event = data.events.find((item) => item.sentiment === "negative" || item.category === "risk_alert");
  if (event) return event.impact;
  if (regime === "risk_off" || regime === "cautious") return "市场环境偏防守，先降低候选优先级，避免把单一热点理解成可持续主线。";
  return "暂未识别到强风险新闻，但仍要检查涨幅过大、资金背离和公告缺口。";
}
