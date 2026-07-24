import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BookmarkPlus, Search, SlidersHorizontal, X } from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import {
  api,
  fmt,
  getAuthToken,
  pct,
  percent,
  type EquityExchange,
  type EquityPage,
  type EquitySort,
  type EquityViewFilters,
  type SavedEquityView,
  type SortDirection,
} from "../../lib/api";

const MONEY_UNIT = 100_000_000;
const filterParamKeys = [
  "q",
  "exchange",
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

const sortLabels: Record<EquitySort, string> = {
  amount: "成交额",
  change_pct: "涨跌幅",
  turnover_rate: "换手率",
  market_cap: "总市值",
};

type AdvancedDraft = {
  sector: string;
  minChangePct: string;
  maxChangePct: string;
  minAmount: string;
  maxAmount: string;
  minTurnoverRate: string;
  maxTurnoverRate: string;
  minMarketCap: string;
  maxMarketCap: string;
  completeOnly: boolean;
};

function numberParam(params: URLSearchParams, key: string, unit = 1): number | null {
  const raw = params.get(key);
  if (raw == null || raw.trim() === "") return null;
  const value = Number(raw);
  return Number.isFinite(value) ? value * unit : null;
}

function readFilters(params: URLSearchParams): EquityViewFilters {
  const exchange = params.get("exchange");
  const sortBy = params.get("sort_by");
  const direction = params.get("direction");
  const pageSize = Number(params.get("page_size"));
  return {
    query: params.get("q")?.trim() ?? "",
    exchange: exchange === "sh" || exchange === "sz" || exchange === "bj" ? exchange : "all",
    sector: params.get("industry")?.trim() || null,
    min_change_pct: numberParam(params, "min_change_pct"),
    max_change_pct: numberParam(params, "max_change_pct"),
    min_amount: numberParam(params, "min_amount", MONEY_UNIT),
    max_amount: numberParam(params, "max_amount", MONEY_UNIT),
    min_turnover_rate: numberParam(params, "min_turnover_rate"),
    max_turnover_rate: numberParam(params, "max_turnover_rate"),
    min_market_cap: numberParam(params, "min_market_cap", MONEY_UNIT),
    max_market_cap: numberParam(params, "max_market_cap", MONEY_UNIT),
    complete_only: params.get("complete_only") === "true",
    sort_by: sortBy === "change_pct" || sortBy === "turnover_rate" || sortBy === "market_cap" ? sortBy : "amount",
    direction: direction === "asc" ? "asc" : "desc",
    page_size: pageSize === 50 ? 50 : 25,
  };
}

function inputValue(value: number | null, unit = 1): string {
  return value == null ? "" : String(value / unit);
}

function draftFromFilters(filters: EquityViewFilters): AdvancedDraft {
  return {
    sector: filters.sector ?? "",
    minChangePct: inputValue(filters.min_change_pct),
    maxChangePct: inputValue(filters.max_change_pct),
    minAmount: inputValue(filters.min_amount, MONEY_UNIT),
    maxAmount: inputValue(filters.max_amount, MONEY_UNIT),
    minTurnoverRate: inputValue(filters.min_turnover_rate),
    maxTurnoverRate: inputValue(filters.max_turnover_rate),
    minMarketCap: inputValue(filters.min_market_cap, MONEY_UNIT),
    maxMarketCap: inputValue(filters.max_market_cap, MONEY_UNIT),
    completeOnly: filters.complete_only,
  };
}

function optionalNumber(value: string, unit = 1): number | null {
  if (!value.trim()) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed * unit : null;
}

function advancedFromDraft(draft: AdvancedDraft): Pick<EquityViewFilters,
  "sector" | "min_change_pct" | "max_change_pct" | "min_amount" | "max_amount" |
  "min_turnover_rate" | "max_turnover_rate" | "min_market_cap" | "max_market_cap" |
  "complete_only"
> {
  return {
    sector: draft.sector || null,
    min_change_pct: optionalNumber(draft.minChangePct),
    max_change_pct: optionalNumber(draft.maxChangePct),
    min_amount: optionalNumber(draft.minAmount, MONEY_UNIT),
    max_amount: optionalNumber(draft.maxAmount, MONEY_UNIT),
    min_turnover_rate: optionalNumber(draft.minTurnoverRate),
    max_turnover_rate: optionalNumber(draft.maxTurnoverRate),
    min_market_cap: optionalNumber(draft.minMarketCap, MONEY_UNIT),
    max_market_cap: optionalNumber(draft.maxMarketCap, MONEY_UNIT),
    complete_only: draft.completeOnly,
  };
}

function rangeError(filters: EquityViewFilters): string | null {
  const ranges: Array<[number | null, number | null, string]> = [
    [filters.min_change_pct, filters.max_change_pct, "涨跌幅"],
    [filters.min_amount, filters.max_amount, "成交额"],
    [filters.min_turnover_rate, filters.max_turnover_rate, "换手率"],
    [filters.min_market_cap, filters.max_market_cap, "总市值"],
  ];
  const invalid = ranges.find(([minimum, maximum]) => minimum != null && maximum != null && minimum > maximum);
  return invalid ? `${invalid[2]}下限不能高于上限。` : null;
}

function setNumber(params: URLSearchParams, key: string, value: number | null, unit = 1): void {
  if (value == null) params.delete(key);
  else params.set(key, String(value / unit));
}

function writeFilters(
  current: URLSearchParams,
  filters: EquityViewFilters,
  page = 1,
): URLSearchParams {
  const next = new URLSearchParams(current);
  filterParamKeys.forEach((key) => next.delete(key));
  if (filters.query) next.set("q", filters.query);
  if (filters.exchange !== "all") next.set("exchange", filters.exchange);
  if (filters.sector) next.set("industry", filters.sector);
  setNumber(next, "min_change_pct", filters.min_change_pct);
  setNumber(next, "max_change_pct", filters.max_change_pct);
  setNumber(next, "min_amount", filters.min_amount, MONEY_UNIT);
  setNumber(next, "max_amount", filters.max_amount, MONEY_UNIT);
  setNumber(next, "min_turnover_rate", filters.min_turnover_rate);
  setNumber(next, "max_turnover_rate", filters.max_turnover_rate);
  setNumber(next, "min_market_cap", filters.min_market_cap, MONEY_UNIT);
  setNumber(next, "max_market_cap", filters.max_market_cap, MONEY_UNIT);
  if (filters.complete_only) next.set("complete_only", "true");
  if (filters.sort_by !== "amount") next.set("sort_by", filters.sort_by);
  if (filters.direction !== "desc") next.set("direction", filters.direction);
  if (filters.page_size !== 25) next.set("page_size", String(filters.page_size));
  if (page > 1) next.set("page", String(page));
  return next;
}

function activeAdvancedCount(filters: EquityViewFilters): number {
  return [
    filters.sector,
    filters.min_change_pct,
    filters.max_change_pct,
    filters.min_amount,
    filters.max_amount,
    filters.min_turnover_rate,
    filters.max_turnover_rate,
    filters.min_market_cap,
    filters.max_market_cap,
    filters.complete_only ? true : null,
  ].filter((value) => value != null && value !== "").length;
}

export function EquityBrowser() {
  const queryClient = useQueryClient();
  const [params, setParams] = useSearchParams();
  const filters = useMemo(() => readFilters(params), [params]);
  const parsedPage = Number(params.get("page"));
  const page = Number.isInteger(parsedPage) && parsedPage > 0 ? parsedPage : 1;
  const [draftQuery, setDraftQuery] = useState(filters.query);
  const [advancedOpen, setAdvancedOpen] = useState(activeAdvancedCount(filters) > 0);
  const [advancedDraft, setAdvancedDraft] = useState(() => draftFromFilters(filters));
  const [filterError, setFilterError] = useState<string | null>(null);
  const [viewName, setViewName] = useState("");
  const [pageDraft, setPageDraft] = useState(String(page));

  const requestParams = useMemo(() => {
    const request = new URLSearchParams({
      exchange: filters.exchange,
      sort_by: filters.sort_by,
      direction: filters.direction,
      page: String(page),
      page_size: String(filters.page_size),
    });
    if (filters.query) request.set("q", filters.query);
    if (filters.sector) request.set("sector", filters.sector);
    const numericFilters: Array<[string, number | null]> = [
      ["min_change_pct", filters.min_change_pct],
      ["max_change_pct", filters.max_change_pct],
      ["min_amount", filters.min_amount],
      ["max_amount", filters.max_amount],
      ["min_turnover_rate", filters.min_turnover_rate],
      ["max_turnover_rate", filters.max_turnover_rate],
      ["min_market_cap", filters.min_market_cap],
      ["max_market_cap", filters.max_market_cap],
    ];
    numericFilters.forEach(([key, value]) => {
      if (value != null) request.set(key, String(value));
    });
    if (filters.complete_only) request.set("complete_only", "true");
    return request.toString();
  }, [filters, page]);

  const query = useQuery({
    queryKey: ["equities", requestParams],
    queryFn: () => api<EquityPage>(`/api/v1/equities?${requestParams}`),
    placeholderData: (previous) => previous,
  });
  const savedViews = useQuery({
    queryKey: ["equity-views"],
    queryFn: () => api<SavedEquityView[]>("/api/v1/equity-views"),
  });
  const createView = useMutation({
    mutationFn: () => api<SavedEquityView>("/api/v1/equity-views", {
      method: "POST",
      body: JSON.stringify({ name: viewName.trim(), filters }),
    }),
    onSuccess: () => {
      setViewName("");
      queryClient.invalidateQueries({ queryKey: ["equity-views"] });
    },
  });
  const deleteView = useMutation({
    mutationFn: (viewId: number) => api<void>(`/api/v1/equity-views/${viewId}`, { method: "DELETE" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["equity-views"] }),
  });

  const totalPages = Math.max(1, Math.ceil((query.data?.total ?? 0) / filters.page_size));
  const rangeStart = query.data?.total ? (page - 1) * filters.page_size + 1 : 0;
  const rangeEnd = Math.min(page * filters.page_size, query.data?.total ?? 0);

  useEffect(() => setPageDraft(String(page)), [page]);
  useEffect(() => setDraftQuery(filters.query), [filters.query]);

  const updateFilters = (changes: Partial<EquityViewFilters>, nextPage = 1) => {
    const nextFilters = { ...filters, ...changes };
    setFilterError(null);
    setParams(writeFilters(params, nextFilters, nextPage), { replace: true });
  };

  const submitSearch = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    updateFilters({ query: draftQuery.trim() });
  };

  const applyAdvanced = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const nextFilters = { ...filters, ...advancedFromDraft(advancedDraft) };
    const error = rangeError(nextFilters);
    if (error) {
      setFilterError(error);
      return;
    }
    updateFilters(nextFilters);
  };

  const resetAll = () => {
    const defaults = readFilters(new URLSearchParams());
    setAdvancedDraft(draftFromFilters(defaults));
    setDraftQuery("");
    setFilterError(null);
    setParams(writeFilters(params, defaults), { replace: true });
  };

  const applyView = (view: SavedEquityView) => {
    setAdvancedDraft(draftFromFilters(view.filters));
    setDraftQuery(view.filters.query);
    setAdvancedOpen(activeAdvancedCount(view.filters) > 0);
    setFilterError(null);
    setParams(writeFilters(params, view.filters), { replace: true });
  };

  const submitPage = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const requestedPage = Number.parseInt(pageDraft, 10);
    const nextPage = Number.isFinite(requestedPage)
      ? Math.min(totalPages, Math.max(1, requestedPage))
      : page;
    setPageDraft(String(nextPage));
    setParams(writeFilters(params, filters, nextPage), { replace: true });
  };

  const changePage = (nextPage: number) => {
    setParams(writeFilters(params, filters, nextPage), { replace: true });
  };

  const advancedCount = activeAdvancedCount(filters);
  const sectors = query.data?.available_sectors ?? [];

  return (
    <section className="panel equity-browser" aria-labelledby="equity-browser-title">
      <div className="panel-title">
        <span id="equity-browser-title">全市场行情</span>
        <small>多条件筛选 · 服务端排序 · 每页 {filters.page_size} 只 · 缺失数据不冒充有效值</small>
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
            <select value={filters.exchange} onChange={(event) => updateFilters({ exchange: event.target.value as EquityExchange })}>
              <option value="all">全部 A 股</option>
              <option value="sh">沪市</option>
              <option value="sz">深市</option>
              <option value="bj">北交所</option>
            </select>
          </label>
          <label>排序字段
            <select value={filters.sort_by} onChange={(event) => updateFilters({ sort_by: event.target.value as EquitySort })}>
              {Object.entries(sortLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
          </label>
          <label>排序方向
            <select value={filters.direction} onChange={(event) => updateFilters({ direction: event.target.value as SortDirection })}>
              <option value="desc">从高到低</option>
              <option value="asc">从低到高</option>
            </select>
          </label>
          <label>每页数量
            <select value={filters.page_size} onChange={(event) => updateFilters({ page_size: Number(event.target.value) as 25 | 50 })}>
              <option value="25">25 只</option>
              <option value="50">50 只</option>
            </select>
          </label>
          <button type="button" className={`filter-toggle ${advancedCount ? "active" : ""}`} aria-expanded={advancedOpen} onClick={() => setAdvancedOpen((value) => !value)}>
            <SlidersHorizontal size={14} />高级筛选{advancedCount ? ` ${advancedCount}` : ""}
          </button>
        </div>
      </div>

      {advancedOpen ? <form className="equity-advanced" onSubmit={applyAdvanced}>
        <div className="advanced-heading"><div><strong>缩小研究范围</strong><span>区间条件按 AND 组合，金额统一使用亿元。</span></div><button type="button" aria-label="关闭高级筛选" onClick={() => setAdvancedOpen(false)}><X size={15} /></button></div>
        <div className="advanced-grid">
          <label>行业
            <select value={advancedDraft.sector} onChange={(event) => setAdvancedDraft((draft) => ({ ...draft, sector: event.target.value }))}>
              <option value="">全部可用行业</option>
              {advancedDraft.sector && !sectors.includes(advancedDraft.sector) ? <option value={advancedDraft.sector}>{advancedDraft.sector}</option> : null}
              {sectors.map((sector) => <option key={sector} value={sector}>{sector}</option>)}
            </select>
          </label>
          <RangeFields label="涨跌幅" unit="%" minimum={advancedDraft.minChangePct} maximum={advancedDraft.maxChangePct} onMinimum={(value) => setAdvancedDraft((draft) => ({ ...draft, minChangePct: value }))} onMaximum={(value) => setAdvancedDraft((draft) => ({ ...draft, maxChangePct: value }))} />
          <RangeFields label="成交额" unit="亿元" minimum={advancedDraft.minAmount} maximum={advancedDraft.maxAmount} nonNegative onMinimum={(value) => setAdvancedDraft((draft) => ({ ...draft, minAmount: value }))} onMaximum={(value) => setAdvancedDraft((draft) => ({ ...draft, maxAmount: value }))} />
          <RangeFields label="换手率" unit="%" minimum={advancedDraft.minTurnoverRate} maximum={advancedDraft.maxTurnoverRate} nonNegative onMinimum={(value) => setAdvancedDraft((draft) => ({ ...draft, minTurnoverRate: value }))} onMaximum={(value) => setAdvancedDraft((draft) => ({ ...draft, maxTurnoverRate: value }))} />
          <RangeFields label="总市值" unit="亿元" minimum={advancedDraft.minMarketCap} maximum={advancedDraft.maxMarketCap} nonNegative onMinimum={(value) => setAdvancedDraft((draft) => ({ ...draft, minMarketCap: value }))} onMaximum={(value) => setAdvancedDraft((draft) => ({ ...draft, maxMarketCap: value }))} />
        </div>
        <div className="advanced-actions">
          <label className="complete-toggle"><input type="checkbox" checked={advancedDraft.completeOnly} onChange={(event) => setAdvancedDraft((draft) => ({ ...draft, completeOnly: event.target.checked }))} />仅看核心数据完整</label>
          {filterError ? <span role="alert">{filterError}</span> : <small>核心数据：价格、涨跌幅、成交额、换手率、总市值</small>}
          <button type="button" className="button secondary" onClick={resetAll}>重置全部</button>
          <button type="submit" className="button">应用筛选</button>
        </div>
      </form> : null}

      <div className="saved-view-bar">
        <div className="saved-view-list" aria-label="保存的筛选视图">
          <span><BookmarkPlus size={14} />保存视图</span>
          {savedViews.isLoading ? <small>读取中…</small> : null}
          {savedViews.data?.length === 0 ? <small>还没有保存的条件</small> : null}
          {savedViews.data?.map((view) => <div className="saved-view-chip" key={view.id}>
            <button type="button" aria-label={`应用视图 ${view.name}`} onClick={() => applyView(view)}>{view.name}</button>
            <button type="button" aria-label={`删除视图 ${view.name}`} disabled={deleteView.isPending} onClick={() => deleteView.mutate(view.id)}><X size={12} /></button>
          </div>)}
        </div>
        <form onSubmit={(event) => { event.preventDefault(); if (viewName.trim()) createView.mutate(); }}>
          <label><span className="sr-only">视图名称</span><input aria-label="视图名称" maxLength={30} value={viewName} onChange={(event) => setViewName(event.target.value)} placeholder="给当前条件命名" /></label>
          <button type="submit" className="button secondary" disabled={!viewName.trim() || createView.isPending}>保存当前视图</button>
        </form>
        {createView.isError ? <p role="alert">保存失败，名称可能已存在，请换一个名称重试。</p> : null}
        {savedViews.isError || deleteView.isError ? <p role="alert">{getAuthToken() ? "保存视图暂时不可用，行情筛选不受影响。" : "登录后可保存个人筛选视图，行情筛选仍可直接使用。"}</p> : null}
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
                <td>{item.amount == null ? "—" : `${fmt(item.amount / MONEY_UNIT)} 亿`}</td>
                <td>{item.market_cap == null ? "—" : `${fmt(item.market_cap / MONEY_UNIT)} 亿`}</td>
              </tr>)}
            </tbody>
          </table>
        </div>
        {query.data.items.length === 0 ? <div className="equity-state empty-filter"><span>当前组合条件没有匹配项。</span><button type="button" className="button secondary" onClick={resetAll}>重置全部</button></div> : null}
        <footer className="equity-pagination">
          <span aria-live="polite">{filters.query ? `“${filters.query}” · ` : ""}第 {rangeStart}–{rangeEnd} 只 / 共 {query.data.total.toLocaleString("zh-CN")} 只 · 第 {page} / {totalPages} 页</span>
          <nav className="equity-page-controls" aria-label="全市场行情分页">
            <button type="button" className="button secondary" disabled={page === 1 || query.isFetching} onClick={() => changePage(1)}>首页</button>
            <button type="button" className="button secondary" disabled={page === 1 || query.isFetching} onClick={() => changePage(Math.max(1, page - 1))}>上一页</button>
            <form className="equity-page-jump" noValidate onSubmit={submitPage}>
              <label>跳转页码
                <input type="number" min="1" max={totalPages} value={pageDraft} onChange={(event) => setPageDraft(event.target.value)} />
              </label>
              <button type="submit" className="button secondary" disabled={query.isFetching}>跳转</button>
            </form>
            <button type="button" className="button secondary" disabled={page >= totalPages || query.isFetching} onClick={() => changePage(page + 1)}>下一页</button>
            <button type="button" className="button secondary" disabled={page >= totalPages || query.isFetching} onClick={() => changePage(totalPages)}>末页</button>
          </nav>
        </footer>
      </> : null}
    </section>
  );
}

function RangeFields({
  label,
  unit,
  minimum,
  maximum,
  nonNegative = false,
  onMinimum,
  onMaximum,
}: {
  label: string;
  unit: string;
  minimum: string;
  maximum: string;
  nonNegative?: boolean;
  onMinimum: (value: string) => void;
  onMaximum: (value: string) => void;
}) {
  return <fieldset className="range-fields">
    <legend>{label}</legend>
    <label>{label}下限（{unit}）<input type="number" step="any" min={nonNegative ? 0 : undefined} value={minimum} onChange={(event) => onMinimum(event.target.value)} placeholder="不限" /></label>
    <i>—</i>
    <label>{label}上限（{unit}）<input type="number" step="any" min={nonNegative ? 0 : undefined} value={maximum} onChange={(event) => onMaximum(event.target.value)} placeholder="不限" /></label>
  </fieldset>;
}
