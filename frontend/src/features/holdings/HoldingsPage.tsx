import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Save, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api, fmt, pct, percent, type HoldingDossier } from "../../lib/api";

type HoldingDraft = {
  symbol: string;
  name: string;
  quantity: string;
  cost_price: string;
  target_weight: string;
  thesis: string;
  invalidation: string;
};

const actionLabel: Record<string, string> = {
  hold: "继续持有",
  trim: "降低暴露",
  review: "补齐数据",
  exit_watch: "考虑退出",
};

function toPayload(draft: HoldingDraft) {
  return {
    symbol: draft.symbol.trim().toUpperCase(),
    name: draft.name.trim(),
    quantity: Number(draft.quantity),
    cost_price: Number(draft.cost_price),
    target_weight: Number(draft.target_weight) / 100,
    thesis: draft.thesis.trim(),
    invalidation: draft.invalidation.trim(),
  };
}

function weight(value: number | null | undefined, digits = 1) {
  return value == null ? "—" : percent(value * 100, digits);
}

function shares(value: number | null | undefined) {
  if (value == null) return "—";
  const prefix = value > 0 ? "+" : "";
  return `${prefix}${Math.round(value).toLocaleString("zh-CN")} 股`;
}

function PositionCard({ dossier, onDelete }: { dossier: HoldingDossier; onDelete: (id: number) => void }) {
  const client = useQueryClient();
  const [quantity, setQuantity] = useState(String(dossier.item.quantity));
  const [costPrice, setCostPrice] = useState(String(dossier.item.cost_price));
  const [targetWeight, setTargetWeight] = useState(String(dossier.item.target_weight * 100));
  const [thesis, setThesis] = useState(dossier.item.thesis);
  const [invalidation, setInvalidation] = useState(dossier.item.invalidation);

  useEffect(() => {
    setQuantity(String(dossier.item.quantity));
    setCostPrice(String(dossier.item.cost_price));
    setTargetWeight(String(dossier.item.target_weight * 100));
    setThesis(dossier.item.thesis);
    setInvalidation(dossier.item.invalidation);
  }, [dossier]);

  const update = useMutation({
    mutationFn: () => api<HoldingDossier>(`/api/v1/holdings/${dossier.item.id}`, {
      method: "PATCH",
      body: JSON.stringify({
        quantity: Number(quantity),
        cost_price: Number(costPrice),
        target_weight: Number(targetWeight) / 100,
        thesis,
        invalidation,
      }),
    }),
    onSuccess: () => client.invalidateQueries({ queryKey: ["holdings"] }),
  });

  const statusClass = (dossier.pnl ?? 0) >= 0 ? "up" : "down";

  return <article className={`position-card ${dossier.action}`}>
    <div className="position-card-grid">
      <section className="position-editor-panel" aria-label={`编辑持仓数据 ${dossier.item.name}`}>
        <div className="position-section-title"><span>编辑持仓数据</span><small>数量、成本、目标仓位会直接重算分析</small></div>
        <div className="position-editor compact-editor">
          <label>持仓数量<input aria-label={`持仓数量 ${dossier.item.name}`} value={quantity} onChange={(event) => { setQuantity(event.target.value); update.reset(); }} /></label>
          <label>成本价<input aria-label={`成本价 ${dossier.item.name}`} value={costPrice} onChange={(event) => { setCostPrice(event.target.value); update.reset(); }} /></label>
          <label>目标仓位 %<input aria-label={`目标仓位 ${dossier.item.name}`} value={targetWeight} onChange={(event) => { setTargetWeight(event.target.value); update.reset(); }} /></label>
          <label>持仓逻辑<textarea aria-label={`持仓逻辑 ${dossier.item.name}`} value={thesis} onChange={(event) => { setThesis(event.target.value); update.reset(); }} /></label>
          <label>失效条件<textarea aria-label={`持仓失效条件 ${dossier.item.name}`} value={invalidation} onChange={(event) => { setInvalidation(event.target.value); update.reset(); }} /></label>
        </div>
        <div className="position-editor-actions">
          {update.isSuccess && <em role="status">已保存</em>}
          {update.isError && <em className="negative" role="alert">保存失败，草稿仍在</em>}
          <button className="icon-button" type="button" aria-label={`删除持仓 ${dossier.item.name}`} onClick={() => onDelete(dossier.item.id)}><Trash2 size={16} /></button>
          <button className="button" type="button" onClick={() => update.mutate()} disabled={update.isPending}><Save size={14} />{update.isPending ? "保存中…" : "保存持仓"}</button>
        </div>
      </section>

      <section className="position-analysis-panel">
        <header>
          <div><Link to={`/stocks?symbol=${dossier.item.symbol}`}>{dossier.item.name}</Link><small>{dossier.item.symbol} · {dossier.quote.sector ?? "行业待补"} · 最近更新 {new Date(dossier.item.updated_at).toLocaleString("zh-CN", { hour12: false })}</small></div>
          <strong>{actionLabel[dossier.action] ?? dossier.action}</strong>
        </header>
        <p className="position-conclusion">{dossier.conclusion}</p>
        <div className="position-metrics position-metrics-rich">
          <div><span>当前市值</span><b>{fmt(dossier.market_value, 0)}</b></div>
          <div><span>持仓成本</span><b>{fmt(dossier.cost_value, 0)}</b></div>
          <div><span>浮动盈亏</span><b className={statusClass}>{fmt(dossier.pnl, 0)} · {pct(dossier.pnl_pct)}</b></div>
          <div><span>组合 / 目标</span><b>{weight(dossier.portfolio_weight)} / {weight(dossier.item.target_weight)}</b></div>
          <div><span>目标市值</span><b>{fmt(dossier.target_market_value, 0)}</b></div>
          <div><span>调仓股数</span><b className={(dossier.rebalance_quantity ?? 0) < 0 ? "down" : "up"}>{shares(dossier.rebalance_quantity)}</b></div>
        </div>
        <div className="position-dimensions">
          {dossier.analysis_dimensions.map((item) => <article className={`dimension-card ${item.signal}`} key={item.key}>
            <span>{item.label}</span>
            <p>{item.summary}</p>
            <small>{item.evidence.join(" · ")}</small>
          </article>)}
        </div>
        <div className="position-tags">{dossier.risk_flags.map((flag) => <i key={flag}>{flag}</i>)}</div>
        <div className="position-next">{dossier.next_actions.map((action) => <span key={action}>{action}</span>)}</div>
      </section>
    </div>
  </article>;
}

export function HoldingsPage() {
  const client = useQueryClient();
  const [draft, setDraft] = useState<HoldingDraft>({ symbol: "SH.600519", name: "贵州茅台", quantity: "100", cost_price: "1400", target_weight: "20", thesis: "写下这笔持仓为什么还值得留在组合里", invalidation: "写下什么情况下必须降仓或退出" });
  const query = useQuery({ queryKey: ["holdings"], queryFn: () => api<HoldingDossier[]>("/api/v1/holdings") });
  const create = useMutation({
    mutationFn: () => api<HoldingDossier>("/api/v1/holdings", { method: "POST", body: JSON.stringify(toPayload(draft)) }),
    onSuccess: () => client.invalidateQueries({ queryKey: ["holdings"] }),
  });
  const remove = useMutation({
    mutationFn: (id: number) => api(`/api/v1/holdings/${id}`, { method: "DELETE" }),
    onSuccess: () => client.invalidateQueries({ queryKey: ["holdings"] }),
  });
  const totalValue = query.data?.reduce((sum, item) => sum + (item.market_value ?? 0), 0) ?? 0;
  const totalCost = query.data?.reduce((sum, item) => sum + item.cost_value, 0) ?? 0;
  const totalPnl = query.data?.reduce((sum, item) => sum + (item.pnl ?? 0), 0) ?? 0;
  const totalPnlPct = totalCost > 0 ? totalPnl / totalCost * 100 : null;
  const rebalanceCount = query.data?.filter((item) => item.action !== "hold" || Math.abs(item.rebalance_quantity ?? 0) > 1).length ?? 0;

  return <>
    <header className="page-head"><div><p className="eyebrow">PORTFOLIO / 持仓分析</p><h1>个股持仓工作台，<br /><em>先改数量成本，再看结论。</em></h1></div></header>
    <section className="position-brief">
      <div><span>组合市值</span><strong>{fmt(totalValue, 0)}</strong></div>
      <div><span>浮动盈亏</span><strong className={totalPnl >= 0 ? "up" : "down"}>{fmt(totalPnl, 0)} · {pct(totalPnlPct)}</strong></div>
      <div><span>需复核持仓</span><strong>{rebalanceCount}</strong></div>
    </section>
    <form className="panel holding-create" onSubmit={(event) => { event.preventDefault(); create.mutate(); }}>
      <div className="panel-title"><span>新增持仓</span><small>填入个股持仓数、成本价、目标仓位，保存后生成持仓分析</small></div>
      <label>代码<input value={draft.symbol} onChange={(event) => setDraft({ ...draft, symbol: event.target.value })} /></label>
      <label>名称<input value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} /></label>
      <label>持仓数量<input value={draft.quantity} onChange={(event) => setDraft({ ...draft, quantity: event.target.value })} /></label>
      <label>成本价<input value={draft.cost_price} onChange={(event) => setDraft({ ...draft, cost_price: event.target.value })} /></label>
      <label>目标仓位 %<input value={draft.target_weight} onChange={(event) => setDraft({ ...draft, target_weight: event.target.value })} /></label>
      <label>持仓逻辑<textarea value={draft.thesis} onChange={(event) => setDraft({ ...draft, thesis: event.target.value })} /></label>
      <label>失效条件<textarea value={draft.invalidation} onChange={(event) => setDraft({ ...draft, invalidation: event.target.value })} /></label>
      <button className="button" disabled={create.isPending}>{create.isPending ? "保存中…" : "加入持仓分析"}</button>
      {create.isError && <p className="form-error">保存失败，请检查代码是否已存在。</p>}
    </form>
    <section className="panel"><div className="panel-title"><span>个股持仓工作台</span><small>{query.data?.length ?? 0} 笔 · 修改数量、成本或目标仓位后主动保存</small></div>{query.data?.length ? <div className="position-list">{query.data.map((item) => <PositionCard key={item.item.id} dossier={item} onDelete={(id) => remove.mutate(id)} />)}</div> : <div className="empty">还没有持仓。先新增一笔，系统会把持仓数、成本、浮盈亏、目标仓位和调仓股数连成一条分析链。</div>}</section>
  </>;
}
