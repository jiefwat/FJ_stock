import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Save, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api, fmt, getAuthToken, pct, type WatchlistItem } from "../../lib/api";
import { StockTrend } from "../stocks/StockTrend";

type WatchTrendDossier = {
  bars: { date: string; close: number }[];
};

function trendReview(bars: WatchTrendDossier["bars"], trackedAt: string): string | null {
  const validBars = bars.filter((bar) => Number.isFinite(bar.close));
  if (validBars.length < 2) return null;
  const target = trackedAt.slice(0, 10);
  const startIndex = validBars.findIndex((bar) => bar.date >= target);
  const index = startIndex >= 0 ? startIndex : validBars.length - 1;
  const start = validBars[index];
  const latest = validBars.at(-1)!;
  const segment = validBars.slice(index);
  const high = Math.max(...segment.map((bar) => bar.close));
  const low = Math.min(...segment.map((bar) => bar.close));
  const move = ((latest.close - start.close) / start.close) * 100;
  const direction = Math.abs(move) < 0.5 ? "基本横盘" : move > 0 ? "上涨" : "下跌";
  return `跟踪后表现：从 ${start.date} 的 ${fmt(start.close)} 到 ${latest.date} 的 ${fmt(latest.close)}，${direction} ${pct(move)}；期间高点 ${fmt(high)}、低点 ${fmt(low)}。`;
}

function ResearchCard({ item, onDelete }: { item: WatchlistItem; onDelete: (id: number) => void }) {
  const client = useQueryClient();
  const [status, setStatus] = useState(item.status);
  const [thesis, setThesis] = useState(item.thesis);
  const [invalidation, setInvalidation] = useState(item.invalidation);
  const trackedAt = item.created_at ?? item.updated_at;
  const trend = useQuery({
    queryKey: ["watchlist-trend", item.symbol],
    queryFn: () => api<WatchTrendDossier>(`/api/v1/stocks/${item.symbol}`),
    enabled: Boolean(item.symbol),
  });

  useEffect(() => {
    setStatus(item.status);
    setThesis(item.thesis);
    setInvalidation(item.invalidation);
  }, [item]);
  const update = useMutation({
    mutationFn: () => api<WatchlistItem>(`/api/v1/watchlist/${item.id}`, {
      method: "PATCH",
      body: JSON.stringify({ status, thesis, invalidation }),
    }),
    onSuccess: () => client.invalidateQueries({ queryKey: ["watchlist"] }),
  });
  const review = trend.data ? trendReview(trend.data.bars, trackedAt) : null;

  return <article className="research-card">
    <header><div><Link to={`/stocks?symbol=${item.symbol}`}>{item.name}</Link><small>{item.symbol}</small></div><label>跟踪状态<select value={status} onChange={(event) => { setStatus(event.target.value); update.reset(); }}><option value="new">刚加入</option><option value="researching">继续跟</option><option value="waiting">等条件</option><option value="invalidated">理由失效</option><option value="archived">已归档</option></select></label></header>
    <div className="journal-fields">
      <label>关注理由<textarea aria-label={`关注理由 ${item.name}`} placeholder="一句话写清：为什么值得继续看？" value={thesis} onChange={(event) => { setThesis(event.target.value); update.reset(); }} /></label>
      <label>放弃条件<textarea aria-label={`放弃条件 ${item.name}`} placeholder="一句话写清：什么情况就不看了？" value={invalidation} onChange={(event) => { setInvalidation(event.target.value); update.reset(); }} /></label>
    </div>
    <section className="watch-trend">
      <div className="watch-trend-head">
        <div><span>加入跟踪后的走势</span><small>圆点会标在你加入跟踪附近的交易日</small></div>
        <Link to={`/stocks?symbol=${item.symbol}`}>打开完整个股分析</Link>
      </div>
      {trend.isLoading && <p className="watch-trend-state">走势加载中…</p>}
      {trend.isError && <p className="watch-trend-state negative">走势暂时加载失败，备注仍可编辑。</p>}
      {trend.data && <>
        {review && <p className="watch-trend-review">{review}</p>}
        <StockTrend bars={trend.data.bars} marker={{ date: trackedAt, label: "加入跟踪" }} compact />
      </>}
    </section>
    <footer><span>最近更新 {new Date(item.updated_at).toLocaleString("zh-CN", { hour12: false })}</span><div>{update.isSuccess && <em role="status">已保存</em>}{update.isError && <em className="negative" role="alert">保存失败，草稿仍在</em>}<button className="icon-button" aria-label={`删除 ${item.name}`} onClick={() => onDelete(item.id)}><Trash2 size={16} /></button><button className="button" onClick={() => update.mutate()} disabled={update.isPending}><Save size={14} />{update.isPending ? "保存中…" : "保存跟踪记录"}</button></div></footer>
  </article>;
}

export function WatchlistPage() {
  const client = useQueryClient();
  const query = useQuery({ queryKey: ["watchlist"], queryFn: () => api<WatchlistItem[]>("/api/v1/watchlist"), retry: false });
  const remove = useMutation({
    mutationFn: (id: number) => api(`/api/v1/watchlist/${id}`, { method: "DELETE" }),
    onSuccess: () => client.invalidateQueries({ queryKey: ["watchlist"] }),
  });
  if (query.isError) {
    const hasToken = Boolean(getAuthToken());
    return <>
      <header className="page-head"><div><p className="eyebrow">WATCHLIST / 跟踪清单</p><h1>没买或还没决定买，<br /><em>先放这里盯着。</em></h1></div></header>
      <section className="panel personal-auth-gate" role="alert">
        <span>{hasToken ? "登录状态已失效" : "请先登录后查看个人跟踪清单"}</span>
        <p>{hasToken ? "请退出后重新登录，系统不会回退展示其他账号的数据。" : "跟踪清单属于个人数据。登录后这里只会显示当前账号自己的记录。"}</p>
      </section>
    </>;
  }
  return <>
    <header className="page-head"><div><p className="eyebrow">WATCHLIST / 跟踪清单</p><h1>没买或还没决定买，<br /><em>先放这里盯着。</em></h1></div></header>
    <section className="panel watchlist-guide"><div className="panel-title"><span>这个模块是干嘛的？</span><small>跟踪不是买入信号</small></div><p>这里放“暂时不买、但值得继续看”的股票。它像一个提醒本：先把想法放下，等条件成熟再决定要不要研究更深。</p><div className="tracking-steps"><div><b>1</b><strong>先放进来</strong><span>在个股页点“加入跟踪”，只是记录，不代表买入。</span></div><div><b>2</b><strong>写两句话</strong><span>为什么关注它？什么情况就放弃？越短越好。</span></div><div><b>3</b><strong>定期清理</strong><span>理由还在就继续跟；理由失效就归档。</span></div></div></section>
    <section className="panel"><div className="panel-title"><span>跟踪清单</span><small>{query.data?.length ?? 0} 项 · 修改后主动保存</small></div>{query.data?.length ? <div className="research-journal">{query.data.map((item) => <ResearchCard key={item.id} item={item} onDelete={(id) => remove.mutate(id)} />)}</div> : <div className="empty">还没有跟踪项。看到一只感兴趣但还没决定的股票，去 <Link to="/stocks">个股</Link> 点“加入跟踪”，先把理由记下来。</div>}</section>
  </>;
}
