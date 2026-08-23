import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { AsyncState } from "../../components/AsyncState";
import { DataStamp } from "../../components/DataStamp";
import { api, fmt, pct, percent, type LimitLadderResult } from "../../lib/api";

type Direction = "up" | "down";
type BoardFilter = "all" | "one_word" | "main" | "growth" | "star" | "beijing";
const INITIAL_STOCKS_PER_LEVEL = 12;
const INITIAL_INDUSTRIES = 12;

function boardOf(code: string, exchange?: string | null): Exclude<BoardFilter, "all" | "one_word"> {
  if (exchange === "BJ") return "beijing";
  if (code.startsWith("688")) return "star";
  if (code.startsWith("300") || code.startsWith("301")) return "growth";
  return "main";
}

export function LimitLadderPage() {
  const [mode, setMode] = useState<Direction>("up");
  const [industry, setIndustry] = useState("all");
  const [board, setBoard] = useState<BoardFilter>("all");
  const [expandedLevels, setExpandedLevels] = useState<number[]>([]);
  const [showAllIndustries, setShowAllIndustries] = useState(false);
  const query = useQuery({
    queryKey: ["market-structure", "limit-ladder", mode],
    queryFn: () => api<LimitLadderResult>(`/api/v1/market-structure/limit-ladder?mode=${mode}`),
    staleTime: 60_000,
  });
  const levels = useMemo(() => (query.data?.levels ?? []).map((level) => ({
    ...level,
    stocks: level.stocks.filter((item) => (industry === "all" || (item.quote.sector ?? "行业待补") === industry) && (board === "all" || (board === "one_word" ? item.one_word === true : boardOf(item.quote.code, item.quote.exchange) === board))),
  })).filter((level) => level.stocks.length > 0), [query.data?.levels, industry, board]);
  const industries = Object.keys(query.data?.industry_distribution ?? {});

  useEffect(() => {
    setExpandedLevels([]);
    setShowAllIndustries(false);
  }, [mode, industry, board]);

  const toggleLevel = (streak: number) => setExpandedLevels((current) => current.includes(streak)
    ? current.filter((item) => item !== streak)
    : [...current, streak]);

  return <>
    <header className="page-head structure-page-head"><div><span className="eyebrow">LIMIT STRUCTURE</span><h1>连板梯队</h1><p>用未复权日线验证连续涨跌停；缺少历史规则时明确降级。</p></div>{query.data && <DataStamp meta={query.data.meta} />}</header>
    <section className="ladder-toolbar" aria-label="连板筛选">
      <div className="direction-switch"><button className={mode === "up" ? "active up-mode" : ""} onClick={() => setMode("up")}>涨停梯队</button><button className={mode === "down" ? "active down-mode" : ""} onClick={() => setMode("down")}>跌停梯队</button></div>
      <label>行业<select value={industry} onChange={(event) => setIndustry(event.target.value)}><option value="all">全部行业</option>{industries.map((item) => <option key={item}>{item}</option>)}</select></label>
      <label>板块 / 状态<select value={board} onChange={(event) => setBoard(event.target.value as BoardFilter)}><option value="all">全部</option><option value="one_word">只看一字</option><option value="main">主板</option><option value="growth">创业板</option><option value="star">科创板</option><option value="beijing">北交所</option></select></label>
    </section>
    <AsyncState loading={query.isLoading} error={query.error as Error | null}>{query.data && <>
      {!query.data.available && <section className="structure-unavailable"><strong>连板数据暂不可用</strong><p>{query.data.unavailable_reason ?? "当前快照缺少涨跌停识别证据，请稍后重试。"}</p></section>}
      <section className={`ladder-summary ${mode}`} aria-label="梯队摘要"><article><span>{mode === "up" ? "涨停股票" : "跌停股票"}</span><strong>{query.data.total}</strong></article><article><span>最高梯队</span><strong>{query.data.max_streak ? `${query.data.max_streak} 板` : "无"}</strong></article><article><span>分析置信度</span><strong>{percent(query.data.confidence * 100)}</strong><small>证据覆盖，不是上涨概率</small></article><article><span>封单数据</span><strong>不可用</strong><small>无盘口证据，不作估算</small></article></section>
      {query.data.available && (levels.length ? <section className="ladder-board" aria-label={`${mode === "up" ? "涨停" : "跌停"}梯队列表`}>{levels.map((level) => {
        const expanded = expandedLevels.includes(level.streak);
        const visibleStocks = expanded ? level.stocks : level.stocks.slice(0, INITIAL_STOCKS_PER_LEVEL);
        const hiddenCount = level.stocks.length - visibleStocks.length;
        return <article key={level.streak} className="ladder-column">
          <header><div><span>{level.label}</span><small>{level.streak === 1 ? "首次触及价格限制" : `连续 ${level.streak} 个交易日触及价格限制`}</small></div><strong>{level.stocks.length}</strong></header>
          <div className="ladder-stock-grid">{visibleStocks.map((item) => <Link key={item.quote.symbol} to={`/stocks?symbol=${encodeURIComponent(item.quote.symbol)}&from=limit-ladder`}><div><span><strong>{item.quote.name}</strong><small>{item.quote.symbol} · {item.quote.sector ?? "行业待补"}</small></span><b className={mode === "up" ? "up" : "down"}>{pct(item.quote.change_pct)}</b></div><p>{item.one_word == null ? "一字状态待原始日线" : item.one_word ? "一字板" : "非一字"}<em>{item.limit_pct.toFixed(0)}% 价格限制</em></p><footer><span>置信 {percent(item.confidence * 100)}</span><b>{item.quote.amount == null ? "成交 N/A" : `${fmt(item.quote.amount / 100_000_000)} 亿成交`}</b></footer></Link>)}</div>
          {level.stocks.length > INITIAL_STOCKS_PER_LEVEL && <button className="ladder-expand" type="button" aria-expanded={expanded} onClick={() => toggleLevel(level.streak)}>{expanded ? `收起至前 ${INITIAL_STOCKS_PER_LEVEL} 只` : `再显示 ${hiddenCount} 只`}<span>{expanded ? "减少滚动" : `当前显示 ${visibleStocks.length} / ${level.stocks.length}`}</span></button>}
        </article>;
      })}</section> : <section className="structure-empty"><strong>当前筛选没有{mode === "up" ? "涨停" : "跌停"}股票</strong><p>这是真实空结果；可切换方向或清除行业、板块筛选。</p></section>)}
      <section className="ladder-industry"><header><strong>行业分布</strong><small>用于发现梯队扩散，不等于参与建议</small></header><div>{Object.entries(query.data.industry_distribution).slice(0, showAllIndustries ? undefined : INITIAL_INDUSTRIES).map(([name, count]) => <button key={name} className={industry === name ? "active" : ""} onClick={() => setIndustry(industry === name ? "all" : name)}><span>{name}</span><strong>{count}</strong></button>)}</div>{industries.length > INITIAL_INDUSTRIES && <button className="ladder-industry-more" type="button" aria-expanded={showAllIndustries} onClick={() => setShowAllIndustries((current) => !current)}>{showAllIndustries ? "收起行业" : `查看全部 ${industries.length} 个行业`}</button>}</section>
      <details className="structure-method"><summary>计算口径与降级说明</summary>{query.data.methodology.map((item) => <p key={item}>{item}</p>)}</details>
    </>}</AsyncState>
  </>;
}
