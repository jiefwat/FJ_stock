import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api, fmt, pct, percent, type EquityExchange, type EquityPage, type EquitySort, type SortDirection } from "../../lib/api";

const sortLabels: Record<EquitySort, string> = {
  amount: "成交额",
  change_pct: "涨跌幅",
  turnover_rate: "换手率",
  market_cap: "总市值",
};

export function EquityBrowser() {
  const [draftQuery, setDraftQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [exchange, setExchange] = useState<EquityExchange>("all");
  const [sortBy, setSortBy] = useState<EquitySort>("amount");
  const [direction, setDirection] = useState<SortDirection>("desc");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState<25 | 50>(25);
  const [pageDraft, setPageDraft] = useState("1");
  const query = useQuery({
    queryKey: ["equities", submittedQuery, exchange, sortBy, direction, page, pageSize],
    queryFn: () => {
      const params = new URLSearchParams({
        exchange,
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
  const rangeStart = query.data?.total ? (page - 1) * pageSize + 1 : 0;
  const rangeEnd = Math.min(page * pageSize, query.data?.total ?? 0);

  useEffect(() => {
    setPageDraft(String(page));
  }, [page]);

  const submitSearch = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmittedQuery(draftQuery.trim());
    setPage(1);
  };

  const submitPage = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const requestedPage = Number.parseInt(pageDraft, 10);
    const nextPage = Number.isFinite(requestedPage)
      ? Math.min(totalPages, Math.max(1, requestedPage))
      : page;
    setPageDraft(String(nextPage));
    setPage(nextPage);
  };

  return (
    <section className="panel equity-browser" aria-labelledby="equity-browser-title">
      <div className="panel-title">
        <span id="equity-browser-title">全市场行情</span>
        <small>交易所筛选 · 服务端排序 · 每页 {pageSize} 只 · 缺失数据置后</small>
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
          <label>交易所
            <select value={exchange} onChange={(event) => { setExchange(event.target.value as EquityExchange); setPage(1); }}>
              <option value="all">全部 A 股</option>
              <option value="sh">沪市</option>
              <option value="sz">深市</option>
              <option value="bj">北交所</option>
            </select>
          </label>
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
          <label>每页数量
            <select value={pageSize} onChange={(event) => { setPageSize(Number(event.target.value) as 25 | 50); setPage(1); }}>
              <option value="25">25 只</option>
              <option value="50">50 只</option>
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
          <span aria-live="polite">{submittedQuery ? `“${submittedQuery}” · ` : ""}第 {rangeStart}–{rangeEnd} 只 / 共 {query.data.total.toLocaleString("zh-CN")} 只 · 第 {page} / {totalPages} 页</span>
          <nav className="equity-page-controls" aria-label="全市场行情分页">
            <button type="button" className="button secondary" disabled={page === 1 || query.isFetching} onClick={() => setPage(1)}>首页</button>
            <button type="button" className="button secondary" disabled={page === 1 || query.isFetching} onClick={() => setPage((value) => Math.max(1, value - 1))}>上一页</button>
            <form className="equity-page-jump" noValidate onSubmit={submitPage}>
              <label>跳转页码
                <input type="number" min="1" max={totalPages} value={pageDraft} onChange={(event) => setPageDraft(event.target.value)} />
              </label>
              <button type="submit" className="button secondary" disabled={query.isFetching}>跳转</button>
            </form>
            <button type="button" className="button secondary" disabled={page >= totalPages || query.isFetching} onClick={() => setPage((value) => value + 1)}>下一页</button>
            <button type="button" className="button secondary" disabled={page >= totalPages || query.isFetching} onClick={() => setPage(totalPages)}>末页</button>
          </nav>
        </footer>
      </> : null}
    </section>
  );
}
