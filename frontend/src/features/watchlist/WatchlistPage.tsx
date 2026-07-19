import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Save, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api, type WatchlistItem } from "../../lib/api";

function ResearchCard({ item, onDelete }: { item: WatchlistItem; onDelete: (id: number) => void }) {
  const client = useQueryClient();
  const [status, setStatus] = useState(item.status);
  const [thesis, setThesis] = useState(item.thesis);
  const [invalidation, setInvalidation] = useState(item.invalidation);
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

  return <article className="research-card">
    <header><div><Link to={`/stocks?symbol=${item.symbol}`}>{item.name}</Link><small>{item.symbol}</small></div><label>研究状态<select value={status} onChange={(event) => { setStatus(event.target.value); update.reset(); }}><option value="new">新建</option><option value="researching">研究中</option><option value="waiting">等待</option><option value="invalidated">已失效</option><option value="archived">归档</option></select></label></header>
    <div className="journal-fields">
      <label>研究逻辑<textarea aria-label={`研究逻辑 ${item.name}`} value={thesis} onChange={(event) => { setThesis(event.target.value); update.reset(); }} /></label>
      <label>失效条件<textarea aria-label={`失效条件 ${item.name}`} value={invalidation} onChange={(event) => { setInvalidation(event.target.value); update.reset(); }} /></label>
    </div>
    <footer><span>最近更新 {new Date(item.updated_at).toLocaleString("zh-CN", { hour12: false })}</span><div>{update.isSuccess && <em role="status">已保存</em>}{update.isError && <em className="negative" role="alert">保存失败，草稿仍在</em>}<button className="icon-button" aria-label={`删除 ${item.name}`} onClick={() => onDelete(item.id)}><Trash2 size={16} /></button><button className="button" onClick={() => update.mutate()} disabled={update.isPending}><Save size={14} />{update.isPending ? "保存中…" : "保存研究记录"}</button></div></footer>
  </article>;
}

export function WatchlistPage() {
  const client = useQueryClient();
  const query = useQuery({ queryKey: ["watchlist"], queryFn: () => api<WatchlistItem[]>("/api/v1/watchlist") });
  const remove = useMutation({
    mutationFn: (id: number) => api(`/api/v1/watchlist/${id}`, { method: "DELETE" }),
    onSuccess: () => client.invalidateQueries({ queryKey: ["watchlist"] }),
  });
  return <>
    <header className="page-head"><div><p className="eyebrow">WATCHLIST / 研究清单</p><h1>记录判断，<br /><em>也记录何时认错。</em></h1></div></header>
    <section className="panel"><div className="panel-title"><span>研究台账</span><small>{query.data?.length ?? 0} 项 · 修改后主动保存</small></div>{query.data?.length ? <div className="research-journal">{query.data.map((item) => <ResearchCard key={item.id} item={item} onDelete={(id) => remove.mutate(id)} />)}</div> : <div className="empty">还没有观察项。从“机会”或“个股研究”确认正反证据后，再建立第一条研究记录。</div>}</section>
  </>;
}
