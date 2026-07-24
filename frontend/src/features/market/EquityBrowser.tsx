import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";

import { api, fmt, pct, percent, type EquityPage, type EquitySort, type SortDirection } from "../../lib/api";

const sortLabels: Record<EquitySort, string> = {
  amount: "成交额",
  change_pct: "涨跌幅",
  turnover_rate: "换手率",
  market_cap: "总市值",
};

export function EquityBrowser() {
  const [draftQuery, setDraftQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [sortBy, setSortBy] = useState<EquitySort>("amount");
  const [direction, setDirection] = useState<SortDirection>("desc");
  const [page, setPage] = useState(1);
  const pageSize = 25;
  const query = useQuery({
    queryKey: ["equities", submittedQuery, sortBy, direction, page],
    queryFn: () => {
      const params = new URLSearchParams({
        sort_by: sortBy,
        direction,
        page: String(page),
        page_size: String(pageSize),
      });
      if (submittedQuery) params.set("q", submittedQuery);
      return api<EquityPage>(`/api/v1/equities?${params.toString()}`);
    },
    placeholderData: (previous) => previous,
  });
  const totalPages = Math.max(1, Math.ceil((query.data?.total ?? 0) / pageSize));

  const submitSearch = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmittedQuery(draftQuery.trim());
    setPage(1);
  };

  return (
    <section className="panel equity-browser" aria-labelledby="equity-browser-title">
      <div className="panel-title">
        <span id="equity-browser-title">全市场行情</span>
        <small>服务端排序 · 每页最多 {pageSize} 只 · 缺失数据置后</small>
      </div>
      <div className="equity-toolbar">
        <form className="equity-search" onSubmit={submitSearch}>
          <label>
            <span>搜索全市场</span>
            <div><Search size={15} /><input type="search" value={draftQuery} onChange={(event) => setDraftQuery(event.target.value)} placeholder="输入代码或名称" /></div>
          </label>
          <button type="submit" className="button">搜索</button>
        </form>
        <div className="equity-rank-controls">
          <label>排序字段
            <select value={sortBy} onChange={(event) => { setSortBy(event.target.value as EquitySort); setPage(1); }}>
              {Object.entries(sortLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
          </label>
          <label>排序方向
            <select value={direction} onChange={(event) => { setDirection(event.target.value as SortDirection); setPage(1); }}>
              <option value="desc">从高到低</option>
              <option value="asc">从低到高</option>
            </select>
          </label>
        </div>
      </div>

      {query.isLoading ? <div className="equity-state" role="status">正在读取全市场行情…</div> : null}
      {query.isError && !query.data ? <div className="equity-state error" role="alert">全市场行情暂时不可用，市场汇总与板块分析仍可继续使用。</div> : null}
      {query.data ? <>
        <div className="equity-table-wrap">
          <table className="equity-table">
            <thead><tr><th>股票</th><th>最新价</th><th>涨跌幅</th><th>换手率</th><th>成交额</th><th>总市值</th></tr></thead>
            <tbody>
              {query.data.items.map((item) => <tr key={item.symbol}>
                <td><Link to={`/stocks?symbol=${item.symbol}`}><strong>{item.name}</strong><small>{item.symbol}</small></Link></td>
                <td>{fmt(item.price)}</td>
                <td className={item.change_pct == null ? undefined : item.change_pct >= 0 ? "up" : "down"}>{pct(item.change_pct)}</td>
                <td>{percent(item.turnover_rate, 2)}</td>
                <td>{item.amount == null ? "—" : `${fmt(item.amount / 100000000)} 亿`}</td>
                <td>{item.market_cap == null ? "—" : `${fmt(item.market_cap / 100000000)} 亿`}</td>
              </tr>)}
            </tbody>
          </table>
        </div>
        {query.data.items.length === 0 ? <div className="equity-state">没有找到匹配股票，请检查代码或名称。</div> : null}
        <footer className="equity-pagination">
          <span>{submittedQuery ? `“${submittedQuery}” · ` : ""}共 {query.data.total.toLocaleString("zh-CN")} 只 · 第 {page} / {totalPages} 页</span>
          <div>
            <button type="button" className="button secondary" disabled={page === 1 || query.isFetching} onClick={() => setPage((value) => Math.max(1, value - 1))}>上一页</button>
            <button type="button" className="button secondary" disabled={page >= totalPages || query.isFetching} onClick={() => setPage((value) => value + 1)}>下一页</button>
          </div>
        </footer>
      </> : null}
    </section>
  );
}
