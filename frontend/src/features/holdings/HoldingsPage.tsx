import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Save, Trash2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { api, fmt, getAuthToken, pct, percent, type HoldingDossier } from "../../lib/api";

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
  hold: "持有",
  trim: "减仓",
  add_watch: "可加仓",
  review: "补齐数据",
  exit_watch: "退出复核",
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

function signedMoney(value: number | null | undefined, digits = 0) {
  if (value == null) return "—";
  const prefix = value > 0 ? "+" : "";
  return `${prefix}${fmt(value, digits)}`;
}

function PnlCell({ value, ratio }: { value: number | null | undefined; ratio: number | null | undefined }) {
  const statusClass = (value ?? 0) >= 0 ? "up" : "down";
  return <div className="holding-pnl-cell"><b className={statusClass}>{signedMoney(value, 0)}</b><small className={statusClass}>{pct(ratio)}</small></div>;
}

function rebalanceText(dossier: HoldingDossier) {
  const quantity = dossier.rebalance_quantity;
  if (dossier.action === "exit_watch" && (quantity ?? 0) > 0) return "暂停补仓，先退出复核";
  if (dossier.action === "review") return "先补齐数据，不调仓";
  if (dossier.action === "hold" && (quantity ?? 0) > 0) return "未触发加仓条件";
  if (quantity == null) return "调仓待价格确认";
  const rounded = Math.abs(Math.round(quantity));
  if (rounded === 0) return "接近目标仓位";
  return quantity < 0 ? `建议减仓约 ${rounded.toLocaleString("zh-CN")} 股` : `可加仓约 ${rounded.toLocaleString("zh-CN")} 股`;
}

function actionQuantity(dossier: HoldingDossier) {
  if (dossier.action === "exit_watch" && (dossier.rebalance_quantity ?? 0) > 0) return "暂停补仓";
  if (dossier.action === "review") return "待确认";
  if (dossier.action === "hold" && (dossier.rebalance_quantity ?? 0) > 0) return "不追高";
  return shares(dossier.rebalance_quantity);
}

function actionTone(dossier: HoldingDossier) {
  if (dossier.action === "add_watch") return "up";
  if (dossier.action === "trim" || dossier.action === "exit_watch") return "down";
  return "";
}

function compactConclusion(dossier: HoldingDossier) {
  const escapedName = dossier.item.name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return dossier.conclusion
    .replace(/^持仓结论：/, "")
    .replace(new RegExp(`^${escapedName}\\s*`), "")
    .trim();
}

function portfolioSummary(items: HoldingDossier[]) {
  const totalValue = items.reduce((sum, item) => sum + (item.market_value ?? 0), 0);
  const totalCost = items.reduce((sum, item) => sum + item.cost_value, 0);
  const totalPnl = items.reduce((sum, item) => sum + (item.pnl ?? 0), 0);
  const totalPnlPct = totalCost > 0 ? totalPnl / totalCost * 100 : null;
  const reviewItems = items.filter((item) => item.action !== "hold" || Math.abs(item.rebalance_quantity ?? 0) > 1);
  const riskFlags = [...new Set(items.flatMap((item) => item.risk_flags))];
  const conclusion = items.length
    ? `${items.length} 笔持仓，${reviewItems.length ? `需要复核 ${reviewItems.length} 笔` : "暂无必须处理的持仓"}；${riskFlags[0] ?? "组合暴露接近目标"}。`
    : "还没有持仓，先录入真实数量、成本和目标仓位。";
  return { totalValue, totalPnl, totalPnlPct, reviewItems, riskFlags, conclusion };
}

function PositionRow({ dossier, onDelete }: { dossier: HoldingDossier; onDelete: (id: number) => void }) {
  const client = useQueryClient();
  const [quantity, setQuantity] = useState(String(dossier.item.quantity));
  const [costPrice, setCostPrice] = useState(String(dossier.item.cost_price));
  const [targetWeight, setTargetWeight] = useState(String(dossier.item.target_weight * 100));

  useEffect(() => {
    setQuantity(String(dossier.item.quantity));
    setCostPrice(String(dossier.item.cost_price));
    setTargetWeight(String(dossier.item.target_weight * 100));
  }, [dossier]);

  const update = useMutation({
    mutationFn: () => api<HoldingDossier>(`/api/v1/holdings/${dossier.item.id}`, {
      method: "PATCH",
      body: JSON.stringify({
        quantity: Number(quantity),
        cost_price: Number(costPrice),
        target_weight: Number(targetWeight) / 100,
        thesis: dossier.item.thesis,
        invalidation: dossier.item.invalidation,
      }),
    }),
    onSuccess: () => client.invalidateQueries({ queryKey: ["holdings"] }),
  });

  return <article className={`holding-row ${dossier.action}`} role="listitem" aria-label={`${dossier.item.name} ${actionLabel[dossier.action] ?? dossier.action}`}>
    <div className="holding-name-cell">
      <strong>{dossier.item.name}</strong>
      <small>{dossier.item.symbol} · {dossier.quote.sector ?? "行业待补"}</small>
      {dossier.risk_flags.length > 0 && <span>{dossier.risk_flags[0]}</span>}
    </div>
    <div className="holding-conclusion-cell">
      <p>{compactConclusion(dossier)}</p>
      <em>{rebalanceText(dossier)}</em>
    </div>
    <div className="holding-pnl-block" aria-label={`${dossier.item.name} 收益拆分`}>
      <span>收益拆分</span>
      <div><small>总盈亏</small><PnlCell value={dossier.pnl} ratio={dossier.pnl_pct} /></div>
      <div><small>单日盈亏</small><PnlCell value={dossier.day_pnl} ratio={dossier.day_pnl_pct} /></div>
      <div><small>近5日盈亏</small><PnlCell value={dossier.five_day_pnl} ratio={dossier.five_day_pnl_pct} /></div>
    </div>
    <div className="holding-target-cell">
      <b>{fmt(dossier.market_value, 0)}</b><small>当前市值</small>
      <b>{weight(dossier.portfolio_weight)}</b><small>目标 {weight(dossier.item.target_weight)}</small>
      <strong className={actionTone(dossier)}>{actionQuantity(dossier)}</strong><small>{actionLabel[dossier.action] ?? dossier.action}</small>
    </div>
    <div className="holding-edit-cell" aria-label={`${dossier.item.name} 快速修改`}>
      <input aria-label={`持仓数量 ${dossier.item.name}`} value={quantity} onChange={(event) => { setQuantity(event.target.value); update.reset(); }} />
      <input aria-label={`成本价 ${dossier.item.name}`} value={costPrice} onChange={(event) => { setCostPrice(event.target.value); update.reset(); }} />
      <input aria-label={`目标仓位 ${dossier.item.name}`} value={targetWeight} onChange={(event) => { setTargetWeight(event.target.value); update.reset(); }} />
    </div>
    <div className="holding-actions-cell">
      {update.isSuccess && <em role="status">已保存</em>}
      {update.isError && <em className="negative" role="alert">保存失败</em>}
      <button className="icon-button" type="button" aria-label={`删除持仓 ${dossier.item.name}`} onClick={() => onDelete(dossier.item.id)}><Trash2 size={15} /></button>
      <button className="button secondary" type="button" aria-label={`保存 ${dossier.item.name}`} onClick={() => update.mutate()} disabled={update.isPending}><Save size={13} />保存</button>
      <Link className="text-link" to={`/stocks?symbol=${dossier.item.symbol}`}>个股分析 →</Link>
    </div>
  </article>;
}

export function HoldingsPage() {
  const client = useQueryClient();
  const [draft, setDraft] = useState<HoldingDraft>({ symbol: "SH.600519", name: "贵州茅台", quantity: "100", cost_price: "1400", target_weight: "20", thesis: "写下这笔持仓为什么还值得留在组合里", invalidation: "写下什么情况下必须降仓或退出" });
  const query = useQuery({ queryKey: ["holdings"], queryFn: () => api<HoldingDossier[]>("/api/v1/holdings"), retry: false });
  const holdings = query.data ?? [];
  const summary = useMemo(() => portfolioSummary(holdings), [holdings]);
  const create = useMutation({
    mutationFn: () => api<HoldingDossier>("/api/v1/holdings", { method: "POST", body: JSON.stringify(toPayload(draft)) }),
    onSuccess: () => client.invalidateQueries({ queryKey: ["holdings"] }),
  });
  const remove = useMutation({
    mutationFn: (id: number) => api(`/api/v1/holdings/${id}`, { method: "DELETE" }),
    onSuccess: () => client.invalidateQueries({ queryKey: ["holdings"] }),
  });

  if (query.isError) {
    const hasToken = Boolean(getAuthToken());
    return <>
      <header className="page-head"><div><p className="eyebrow">PORTFOLIO / 持仓分析</p><h1>组合给判断，<br /><em>个股进清单。</em></h1></div></header>
      <section className="panel personal-auth-gate" role="alert">
        <span>{hasToken ? "登录状态已失效" : "请先登录后查看个人持仓"}</span>
        <p>{hasToken ? "请退出后重新登录，系统不会回退展示其他账号的数据。" : "持仓属于个人数据。登录后这里只会显示当前账号自己的组合。"}</p>
      </section>
    </>;
  }

  return <>
    <header className="page-head"><div><p className="eyebrow">PORTFOLIO / 持仓分析</p><h1>组合给判断，<br /><em>个股进清单。</em></h1></div></header>
    <section className="portfolio-overview panel" aria-label="组合总览">
      <div className="panel-title"><span>组合总览</span><small>整体分析只回答：风险在哪里，今天先处理谁</small></div>
      <div className="portfolio-hero-line">
        <article><span>组合市值</span><strong>{fmt(summary.totalValue, 0)}</strong></article>
        <article><span>浮动盈亏</span><strong className={summary.totalPnl >= 0 ? "up" : "down"}>{fmt(summary.totalPnl, 0)} · {pct(summary.totalPnlPct)}</strong></article>
        <article><span>持仓数量</span><strong>{holdings.length}</strong></article>
        <article><span>需复核</span><strong>{summary.reviewItems.length}</strong></article>
      </div>
      <div className="portfolio-conclusion">
        <span>组合结论</span>
        <p>{summary.conclusion}</p>
        {summary.riskFlags.length > 0 && <div>{summary.riskFlags.slice(0, 4).map((flag) => <i key={flag}>{flag}</i>)}</div>}
      </div>
    </section>

    <section className="panel holdings-table-panel">
      <div className="panel-title"><span>持仓列表</span><small>{holdings.length} 笔 · 每行只放结论、仓位和跳板</small></div>
      {holdings.length ? <div className="holdings-list" role="list" aria-label="持仓清单">
        {holdings.map((item) => <PositionRow key={item.item.id} dossier={item} onDelete={(id) => remove.mutate(id)} />)}
      </div> : <div className="empty">还没有持仓。先新增一笔，系统会在上方生成组合结论，并在列表里给每只股票一个处理动作。</div>}
    </section>

    <details className="holding-create-drawer">
      <summary>新增持仓</summary>
      <form className="panel holding-create compact-create" onSubmit={(event) => { event.preventDefault(); create.mutate(); }}>
        <div className="panel-title"><span>登记一笔持仓</span><small>保存后回到列表，不生成额外报告</small></div>
        <label>代码<input value={draft.symbol} onChange={(event) => setDraft({ ...draft, symbol: event.target.value })} /></label>
        <label>名称<input value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} /></label>
        <label>数量<input value={draft.quantity} onChange={(event) => setDraft({ ...draft, quantity: event.target.value })} /></label>
        <label>成本<input value={draft.cost_price} onChange={(event) => setDraft({ ...draft, cost_price: event.target.value })} /></label>
        <label>目标 %<input value={draft.target_weight} onChange={(event) => setDraft({ ...draft, target_weight: event.target.value })} /></label>
        <label>持仓逻辑<input value={draft.thesis} onChange={(event) => setDraft({ ...draft, thesis: event.target.value })} /></label>
        <label>失效条件<input value={draft.invalidation} onChange={(event) => setDraft({ ...draft, invalidation: event.target.value })} /></label>
        <button className="button" disabled={create.isPending}>{create.isPending ? "保存中…" : "加入持仓"}</button>
        {create.isError && <p className="form-error">保存失败，请检查代码是否已存在。</p>}
      </form>
    </details>
  </>;
}
