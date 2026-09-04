import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronDown, Save, Trash2 } from "lucide-react";
import { useEffect, useMemo, useState, type KeyboardEvent, type MouseEvent } from "react";
import { Link } from "react-router-dom";

import { PageTaskRail, WorkbenchPageHeader, type WorkbenchStep } from "../../components/WorkbenchPageHeader";
import { ApiError, api, fmt, getAuthToken, pct, type HoldingDossier } from "../../lib/api";
import { holdingDecision } from "../../lib/decision";
import { plainLanguage } from "../../lib/plainLanguage";

type HoldingDraft = {
  symbol: string;
  name: string;
  quantity: string;
  cost_price: string;
  thesis: string;
  invalidation: string;
};
type HoldingSort =
  | "priority"
  | "today_drag"
  | "ten_day_drag"
  | "loss"
  | "volatility"
  | "add"
  | "risk";

type PortfolioDailyChange = {
  date: string;
  pnl: number;
  pct: number | null;
  topContributor: { name: string; pnl: number } | null;
};

const emptyDraft: HoldingDraft = {
  symbol: "",
  name: "",
  quantity: "",
  cost_price: "",
  thesis: "",
  invalidation: "",
};

const actionLabel: Record<string, string> = {
  hold: "继续持有",
  trim: "建议分批减仓",
  add_watch: "仅小幅加仓",
  review: "暂不操作",
  exit_watch: "优先减仓或止损",
};
const holdingSortOptions: Array<[HoldingSort, string]> = [
  ["priority", "综合优先"],
  ["today_drag", "今日拖累"],
  ["ten_day_drag", "10日拖累"],
  ["loss", "亏损幅度"],
  ["volatility", "波动最大"],
  ["add", "可小幅加仓"],
  ["risk", "风控优先"],
];
const HOLDING_PAGE_SIZE = 8;
const TODAY_FOCUS_LIMIT = 5;

function toPayload(draft: HoldingDraft) {
  const name = draft.name.trim();
  return {
    symbol: draft.symbol.trim().toUpperCase(),
    name,
    quantity: Number(draft.quantity),
    cost_price: Number(draft.cost_price),
    thesis: draft.thesis.trim() || `${name || "这只股票"} 持仓逻辑待补充，先按价格、资金和板块证据复核。`,
    invalidation: draft.invalidation.trim() || "跌破成本、趋势破位或基本面证据转弱时复核降仓或退出。",
  };
}

function createErrorText(error: unknown) {
  return error instanceof ApiError ? error.detail : "保存失败，请检查代码或名称是否已存在。";
}

function updateErrorText(error: unknown) {
  return error instanceof ApiError ? error.detail : "保存失败，原持仓数据未更改，请稍后重试。";
}

function signedMoney(value: number | null | undefined, digits = 0) {
  if (value == null) return "—";
  const prefix = value > 0 ? "+" : "";
  return `${prefix}${fmt(value, digits)}`;
}

function weight(value: number | null | undefined) {
  if (value == null) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

function formatShortDate(value: string | null | undefined) {
  if (!value) return "—";
  const match = /^\d{4}-(\d{2})-(\d{2})$/.exec(value);
  if (match) return `${match[1]}-${match[2]}`;
  return value;
}

function PnlCell({ value, ratio }: { value: number | null | undefined; ratio: number | null | undefined }) {
  const statusClass = (value ?? 0) >= 0 ? "up" : "down";
  return <div className="holding-pnl-cell"><b className={statusClass}>{signedMoney(value, 0)}</b><small className={statusClass}>{pct(ratio)}</small></div>;
}

function rebalanceText(dossier: HoldingDossier) {
  return holdingDecision(dossier).summary;
}

function actionQuantity(dossier: HoldingDossier) {
  return holdingDecision(dossier).action;
}

function actionTone(dossier: HoldingDossier) {
  if (dossier.action === "add_watch") return "up";
  if (dossier.action === "trim" || dossier.action === "exit_watch") return "down";
  return "";
}

function holdingPriority(dossier: HoldingDossier) {
  const actionScore = dossier.action === "exit_watch" ? 50 : dossier.action === "trim" ? 40 : dossier.action === "review" ? 30 : dossier.action === "add_watch" ? 20 : 10;
  const lossScore = Math.max(0, -(dossier.pnl_pct ?? 0));
  const driftScore = Math.max(0, Math.abs(dossier.drift ?? 0) * 100);
  return actionScore + lossScore + driftScore + dossier.risk_flags.length * 8;
}

function compactConclusion(dossier: HoldingDossier) {
  const escapedName = dossier.item.name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return plainLanguage(dossier.conclusion
    .replace(/^持仓结论：/, "")
    .replace(/^建议动作：[^。]+。/, "")
    .replace(/再复核/g, "重新确认")
    .replace(new RegExp(`^${escapedName}\\s*`), "")
    .trim());
}

function holdingAskHref(dossier: HoldingDossier) {
  const question = `我的持仓里${dossier.item.name}风险怎么处理，要不要调仓；成本${dossier.item.cost_price}，数量${dossier.item.quantity}，盈亏${pct(dossier.pnl_pct)}，10日走势${pct(tenDayChange(dossier))}，10日贡献${signedMoney(tenDayContribution(dossier), 0)}，系统决定：${actionLabel[dossier.action] ?? dossier.action}`;
  return `/ask?symbol=${encodeURIComponent(dossier.item.symbol)}&name=${encodeURIComponent(dossier.item.name)}&from=holdings&question=${encodeURIComponent(question)}`;
}

function portfolioAskHref() {
  return `/ask?from=holdings&question=${encodeURIComponent("直接给我的整仓处理决定：每只股票继续持有、小幅加仓、分批减仓还是退出，并按优先级排序")}`;
}

function holdingDayAskHref(dossier: HoldingDossier, date: string, changePct: number | null) {
  const direction = changePct == null ? "波动" : changePct >= 0 ? "上涨" : "下跌";
  return `/ask?symbol=${encodeURIComponent(dossier.item.symbol)}&name=${encodeURIComponent(dossier.item.name)}&from=holdings&question=${encodeURIComponent(`${dossier.item.name}在${date}为什么${direction}${changePct == null ? "" : ` ${pct(changePct)}`}，这对我的持仓要怎么处理`)}`;
}

function aggregatePeriodPct(totalValue: number, pnl: number) {
  const baseValue = totalValue - pnl;
  return baseValue > 0 ? pnl / baseValue * 100 : null;
}

function sumOptional(items: HoldingDossier[], selector: (item: HoldingDossier) => number | null | undefined) {
  return items.reduce((sum, item) => sum + (selector(item) ?? 0), 0);
}

function actionSummary(items: HoldingDossier[]) {
  const trimCount = items.filter((item) => item.action === "trim" || item.action === "exit_watch").length;
  const addCount = items.filter((item) => item.action === "add_watch").length;
  const reviewCount = items.filter((item) => item.action === "review").length;
  if (trimCount || addCount || reviewCount) {
    return `${trimCount} 笔需要减仓或止损，${addCount} 笔可以小幅加仓，${reviewCount} 笔暂不操作`;
  }
  return "所有股票暂以持有观察为主";
}

function dayContribution(item: HoldingDossier, changePct: number | null | undefined) {
  if (item.market_value == null || changePct == null || changePct <= -100) return null;
  const baseValue = item.market_value / (1 + changePct / 100);
  return item.market_value - baseValue;
}

function tenDayContribution(item: HoldingDossier) {
  return (item.recent_daily_changes ?? []).reduce((sum, day) => sum + (dayContribution(item, day.change_pct) ?? 0), 0);
}

function tenDayChange(item: HoldingDossier) {
  const values = (item.recent_daily_changes ?? []).flatMap((day) => day.change_pct == null ? [] : [day.change_pct]);
  return values.length ? values.reduce((sum, value) => sum + value, 0) : null;
}

function holdingVolatility(item: HoldingDossier) {
  const values = (item.recent_daily_changes ?? []).flatMap((day) => day.change_pct == null ? [] : [Math.abs(day.change_pct)]);
  return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : 0;
}

function portfolioDailyChanges(items: HoldingDossier[], totalValue: number): PortfolioDailyChange[] {
  const dates = [...new Set(items.flatMap((item) => (item.recent_daily_changes ?? []).map((day) => day.date)))].sort().slice(-10).reverse();
  return dates.map((date) => {
    const contributions = items.flatMap((item) => {
      const day = item.recent_daily_changes?.find((change) => change.date === date);
      const pnl = dayContribution(item, day?.change_pct);
      return pnl == null ? [] : [{ name: item.item.name, pnl }];
    });
    const pnl = contributions.reduce((sum, item) => sum + item.pnl, 0);
    const topContributor = contributions.sort((left, right) => Math.abs(right.pnl) - Math.abs(left.pnl))[0] ?? null;
    return { date, pnl, pct: aggregatePeriodPct(totalValue, pnl), topContributor };
  });
}

function dominantContribution(items: HoldingDossier[], direction: "positive" | "negative") {
  const ranked = items
    .map((item) => ({ item, value: tenDayContribution(item) }))
    .filter((entry) => direction === "positive" ? entry.value > 0 : entry.value < 0)
    .sort((left, right) => direction === "positive" ? right.value - left.value : left.value - right.value);
  return ranked[0] ?? null;
}

function clampScore(value: number) {
  return Math.max(0, Math.min(100, Math.round(value)));
}

function riskScore(item: HoldingDossier) {
  const tenDay = tenDayChange(item);
  const volatility = holdingVolatility(item);
  const base = item.action === "exit_watch" ? 88 : item.action === "trim" ? 72 : item.action === "review" ? 58 : item.action === "add_watch" ? 34 : 22;
  const positionRisk = (item.portfolio_weight ?? 0) >= 0.35 ? 16 : 0;
  const lossRisk = item.pnl_pct != null && item.pnl_pct < 0 ? Math.min(18, Math.abs(item.pnl_pct) * 1.5) : 0;
  const trendRisk = tenDay != null && tenDay < 0 ? Math.min(18, Math.abs(tenDay) * 2) : tenDay != null && tenDay >= 18 ? 14 : 0;
  const flowRisk = item.quote.net_flow != null && item.quote.net_flow < 0 ? 10 : 0;
  const valuationRisk = item.quote.pe != null && item.quote.pe > 60 ? 8 : 0;
  return clampScore(base + positionRisk + lossRisk + trendRisk + flowRisk + valuationRisk + Math.min(20, volatility * 2));
}

function riskTone(score: number) {
  if (score >= 70) return "danger";
  if (score >= 45) return "warning";
  return "calm";
}

function executionPriority(item: HoldingDossier) {
  const score = riskScore(item);
  if (item.action === "exit_watch" || score >= 70) return "高";
  if (item.action === "trim" || item.action === "review" || score >= 45) return "中";
  return "低";
}

function plainRiskReason(item: HoldingDossier) {
  const tenDay = tenDayChange(item);
  if (item.risk_flags.length) return item.risk_flags.slice(0, 2).map(plainLanguage).join(" / ");
  if (tenDay != null && tenDay < 0) return `近10日下跌 ${pct(tenDay)}`;
  if (item.action === "add_watch") return "趋势还可以，但只适合小幅试探";
  return "没有明显警报，按计划观察";
}

function plainRiskAction(item: HoldingDossier) {
  return holdingDecision(item).summary;
}

function executionQueue(items: HoldingDossier[]) {
  const actionable = items.filter((item) => item.action !== "hold" || item.risk_flags.length > 0);
  const source = actionable.length ? actionable : items;
  return [...source]
    .sort((left, right) => riskScore(right) - riskScore(left) || holdingPriority(right) - holdingPriority(left))
    .slice(0, 5);
}

function portfolioSummary(items: HoldingDossier[]) {
  const totalValue = items.reduce((sum, item) => sum + (item.market_value ?? 0), 0);
  const totalCost = items.reduce((sum, item) => sum + item.cost_value, 0);
  const totalPnl = items.reduce((sum, item) => sum + (item.pnl ?? 0), 0);
  const totalPnlPct = totalCost > 0 ? totalPnl / totalCost * 100 : null;
  const totalDayPnl = sumOptional(items, (item) => item.day_pnl);
  const totalThreeDayPnl = sumOptional(items, (item) => item.three_day_pnl);
  const totalFiveDayPnl = sumOptional(items, (item) => item.five_day_pnl);
  const totalDayPnlPct = aggregatePeriodPct(totalValue, totalDayPnl);
  const totalThreeDayPnlPct = aggregatePeriodPct(totalValue, totalThreeDayPnl);
  const totalFiveDayPnlPct = aggregatePeriodPct(totalValue, totalFiveDayPnl);
  const riskFlags = [...new Set(items.flatMap((item) => item.risk_flags))];
  const trimCount = items.filter((item) => item.action === "trim" || item.action === "exit_watch").length;
  const addCount = items.filter((item) => item.action === "add_watch").length;
  const reviewCount = items.filter((item) => item.action === "review").length;
  const dailyChanges = portfolioDailyChanges(items, totalValue);
  const totalTenDayPnl = dailyChanges.reduce((sum, item) => sum + item.pnl, 0);
  const totalTenDayPnlPct = aggregatePeriodPct(totalValue, totalTenDayPnl);
  const conclusion = items.length
    ? `${items.length} 笔持仓，整仓近10日 ${pct(totalTenDayPnlPct)}，当日 ${pct(totalDayPnlPct)}；${actionSummary(items)}。`
    : "还没有持仓，先录入真实数量、成本和持仓逻辑。";
  return {
    totalValue,
    totalPnl,
    totalPnlPct,
    totalDayPnl,
    totalDayPnlPct,
    totalThreeDayPnl,
    totalThreeDayPnlPct,
    totalFiveDayPnl,
    totalFiveDayPnlPct,
    totalTenDayPnl,
    totalTenDayPnlPct,
    dailyChanges,
    topPositiveContribution: dominantContribution(items, "positive"),
    topNegativeContribution: dominantContribution(items, "negative"),
    riskFlags,
    trimCount,
    addCount,
    reviewCount,
    conclusion,
  };
}

type PortfolioSummary = ReturnType<typeof portfolioSummary>;

function isWeekendSnapshot() {
  const day = new Date().getDay();
  return day === 0 || day === 6;
}

function PortfolioMovementDeck({ summary }: { summary: PortfolioSummary }) {
  return <section className="portfolio-movement-deck" aria-label="整仓涨跌分析">
    <header>
      <span>整仓涨跌</span>
      <strong>近10日每日组合表现</strong>
      <p>{isWeekendSnapshot() ? "休市日展示最近交易日数据；" : ""}按当前持仓数量估算每日盈亏和主要贡献。</p>
    </header>
    <div className="portfolio-daily-strip" aria-label="整仓近10日每日涨跌">
      {summary.dailyChanges.length ? summary.dailyChanges.map((day) => <article key={day.date}>
        <span>{formatShortDate(day.date)}</span>
        <strong className={day.pnl >= 0 ? "up" : "down"}>{signedMoney(day.pnl, 0)}</strong>
        <small>{pct(day.pct)} · {day.topContributor ? `${day.topContributor.name} ${signedMoney(day.topContributor.pnl, 0)}` : "贡献待补"}</small>
      </article>) : <article><span>近10日</span><strong>—</strong><small>数据不足</small></article>}
    </div>
    <div className="portfolio-contribution-rank" aria-label="近10日贡献排序">
      <article><span>10日累计</span><strong className={summary.totalTenDayPnl >= 0 ? "up" : "down"}>{signedMoney(summary.totalTenDayPnl, 0)}</strong><small>{pct(summary.totalTenDayPnlPct)}</small></article>
      <article><span>最大贡献</span><strong>{summary.topPositiveContribution?.item.item.name ?? "—"}</strong><small>{signedMoney(summary.topPositiveContribution?.value, 0)}</small></article>
      <article><span>最大拖累</span><strong>{summary.topNegativeContribution?.item.item.name ?? "—"}</strong><small>{signedMoney(summary.topNegativeContribution?.value, 0)}</small></article>
    </div>
    <nav>
      <Link to={portfolioAskHref()}>解释整仓涨跌</Link>
    </nav>
  </section>;
}

function PortfolioTodayFocus({ items }: { items: HoldingDossier[] }) {
  const [showAll, setShowAll] = useState(false);
  const queue = executionQueue(items);
  if (!queue.length) return null;
  const visibleQueue = showAll ? queue : queue.slice(0, TODAY_FOCUS_LIMIT);
  const hiddenCount = queue.length - visibleQueue.length;
  return <section className="portfolio-today-focus" aria-label="今天的操作决定">
    <header>
      <div>
        <span>今天的决定</span>
        <strong>按顺序处理这几只</strong>
      </div>
    </header>
    <div className="today-focus-list">
      {visibleQueue.map((item, index) => <article key={item.item.id} className={riskTone(riskScore(item))}>
        <b>{index + 1}</b>
        <div>
          <strong>{item.item.name}</strong>
          <small>{item.item.symbol} · {item.quote.sector ?? "行业待补"}</small>
        </div>
        <span>{executionPriority(item)}</span>
        <p>{plainRiskReason(item)}</p>
        <em><strong>{actionQuantity(item)}</strong> · {plainRiskAction(item)}</em>
        <Link to={holdingAskHref(item)}>查看判断依据</Link>
      </article>)}
    </div>
    {queue.length > TODAY_FOCUS_LIMIT && <button className="portfolio-list-more" type="button" aria-expanded={showAll} onClick={() => setShowAll((current) => !current)}>{showAll ? `收起至前 ${TODAY_FOCUS_LIMIT} 项` : `再显示 ${hiddenCount} 项较低优先级决定`}</button>}
  </section>;
}

function heatClass(value: number | null | undefined) {
  if (value == null) return "";
  const magnitude = Math.min(3, Math.max(1, Math.ceil(Math.abs(value) / 2)));
  return `${value >= 0 ? "up" : "down"} heat-${magnitude}`;
}

function PortfolioStockPlan({ items }: { items: HoldingDossier[] }) {
  if (!items.length) return null;
  return <section className="portfolio-stock-plan" aria-label="整仓股票建议">
    <div className="portfolio-stock-plan-head">
      <div>
        <span>全股票分析</span>
        <strong>每只持仓是否减仓 / 加仓 · 近10日每日涨跌幅</strong>
      </div>
      <Link to={portfolioAskHref()}>查看整仓依据</Link>
    </div>
    <div className="portfolio-stock-plan-list">
      {items.map((item) => {
        const dailyChanges = (item.recent_daily_changes ?? []).slice(-10).reverse();
        return <article key={item.item.id} className={item.action}>
        <div>
          <strong>{item.item.name}</strong>
          <small>{item.item.symbol} · {item.quote.sector ?? "行业待补"} · 10日贡献 {signedMoney(tenDayContribution(item), 0)}</small>
        </div>
        <div className="stock-plan-daily-changes" aria-label={`${item.item.name} 近10日每日涨跌幅`}>
          {dailyChanges.length ? dailyChanges.map((day) => <Link className={heatClass(day.change_pct)} to={holdingDayAskHref(item, day.date, day.change_pct)} key={day.date} aria-label={`${item.item.name} ${formatShortDate(day.date)} 涨跌 ${pct(day.change_pct)}`}>
            <small>{formatShortDate(day.date)}</small>
            <b>{pct(day.change_pct)}</b>
          </Link>) : <span>
            <small>近10日</small>
            <b>—</b>
          </span>}
        </div>
      </article>;
      })}
    </div>
  </section>;
}

function sortHoldings(items: HoldingDossier[], sort: HoldingSort) {
  const actionRank = (item: HoldingDossier) => item.action === "exit_watch" ? 5 : item.action === "trim" ? 4 : item.action === "review" ? 3 : item.action === "add_watch" ? 2 : 1;
  const score = (item: HoldingDossier) => {
    if (sort === "today_drag") return -(item.day_pnl ?? 0);
    if (sort === "ten_day_drag") return -tenDayContribution(item);
    if (sort === "loss") return Math.max(0, -(item.pnl_pct ?? 0));
    if (sort === "volatility") return holdingVolatility(item);
    if (sort === "add") return item.action === "add_watch" ? 1_000 + (tenDayChange(item) ?? 0) : tenDayChange(item) ?? -100;
    if (sort === "risk") return riskScore(item);
    return holdingPriority(item);
  };
  return [...items].sort((left, right) => score(right) - score(left));
}

function PositionRow({ dossier, onDelete, deletePending }: { dossier: HoldingDossier; onDelete: (id: number, name: string) => void; deletePending: boolean }) {
  const client = useQueryClient();
  const [symbol, setSymbol] = useState(dossier.item.symbol);
  const [name, setName] = useState(dossier.item.name);
  const [quantity, setQuantity] = useState(String(dossier.item.quantity));
  const [costPrice, setCostPrice] = useState(String(dossier.item.cost_price));
  const [expanded, setExpanded] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  useEffect(() => {
    setSymbol(dossier.item.symbol);
    setName(dossier.item.name);
    setQuantity(String(dossier.item.quantity));
    setCostPrice(String(dossier.item.cost_price));
  }, [dossier]);

  const update = useMutation({
    mutationFn: () => api<HoldingDossier>(`/api/v1/holdings/${dossier.item.id}`, {
      method: "PATCH",
      body: JSON.stringify({
        symbol: symbol.trim().toUpperCase(),
        name: name.trim(),
        quantity: Number(quantity),
        cost_price: Number(costPrice),
        thesis: dossier.item.thesis,
        invalidation: dossier.item.invalidation,
      }),
    }),
    onSuccess: () => client.invalidateQueries({ queryKey: ["holdings"] }),
  });

  function toggleExpanded(event: MouseEvent<HTMLElement> | KeyboardEvent<HTMLElement>) {
    const target = event.target as HTMLElement;
    if (target.closest("a, button, input, label")) return;
    setExpanded((current) => !current);
  }

  return <article
    className={`holding-row ${dossier.action} ${expanded ? "is-expanded" : "is-collapsed"}`}
    role="listitem"
    aria-label={`${dossier.item.name} ${actionLabel[dossier.action] ?? dossier.action}`}
    aria-expanded={expanded}
    tabIndex={0}
    onClick={toggleExpanded}
    onKeyDown={(event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        toggleExpanded(event);
      }
    }}
  >
    <div className="holding-name-cell">
      <strong>{dossier.item.name}</strong>
      <small>{dossier.item.symbol} · {dossier.quote.sector ?? "行业待补"}</small>
      <div className="holding-badges">
        <span className="holding-action-pill">{actionLabel[dossier.action] ?? dossier.action}</span>
        {dossier.risk_flags.length > 0 && <span className="holding-risk-pill">{plainLanguage(dossier.risk_flags[0])}</span>}
      </div>
      <div className="holding-name-actions">
        <button className="holding-toggle-button" type="button" aria-label={`${expanded ? "收起详情" : "展开详情"} ${dossier.item.name}`} aria-expanded={expanded} onClick={() => setExpanded((current) => !current)}><ChevronDown size={14} />{expanded ? "收起" : "展开"}</button>
        {!confirmDelete ? <button className="holding-delete-button" type="button" aria-label={`删除持仓 ${dossier.item.name}`} onClick={() => setConfirmDelete(true)}><Trash2 size={14} />删除</button> : <div className="holding-delete-confirm" role="group" aria-label={`确认删除持仓 ${dossier.item.name}`}>
          <span>确定移除？</span>
          <button type="button" onClick={() => setConfirmDelete(false)} disabled={deletePending}>取消</button>
          <button className="danger" type="button" onClick={() => onDelete(dossier.item.id, dossier.item.name)} disabled={deletePending}>{deletePending ? "删除中…" : "确认删除"}</button>
        </div>}
      </div>
    </div>
    <div className="holding-conclusion-cell">
      <p>{compactConclusion(dossier)}</p>
      <em>{plainLanguage(rebalanceText(dossier))}</em>
    </div>
    {!expanded && <div className="holding-quick-metrics" aria-label={`${dossier.item.name} 摘要`}>
      <div><small>现价</small><b>{fmt(dossier.quote.price)}</b></div>
      <div><small>当日盈亏</small><PnlCell value={dossier.day_pnl} ratio={dossier.day_pnl_pct} /></div>
      <div><small>市值</small><b>{fmt(dossier.market_value, 0)}</b></div>
      <div><small>建议</small><strong className={actionTone(dossier)}>{actionQuantity(dossier)}</strong></div>
    </div>}
    {expanded && <>
    <div className="holding-pnl-block" aria-label={`${dossier.item.name} 收益拆分`}>
      <span>收益拆分</span>
      <div><small>总盈亏</small><PnlCell value={dossier.pnl} ratio={dossier.pnl_pct} /></div>
      <div><small>3日内盈亏</small><PnlCell value={dossier.three_day_pnl} ratio={dossier.three_day_pnl_pct} /></div>
      <div><small>5日内盈亏</small><PnlCell value={dossier.five_day_pnl} ratio={dossier.five_day_pnl_pct} /></div>
    </div>
    <div className="holding-target-cell">
      <div><b>{fmt(dossier.quote.price)}</b><small>现价</small></div>
      <div><b>{fmt(dossier.market_value, 0)}</b><small>持仓市值</small></div>
      <div><b>{fmt(dossier.cost_value, 0)}</b><small>持仓成本</small></div>
      <div><b>{weight(dossier.portfolio_weight)}</b><small>持仓占比</small></div>
      <div><b>{fmt(dossier.item.cost_price)}</b><small>成本价</small></div>
      <div><strong className={actionTone(dossier)}>{actionQuantity(dossier)}</strong><small>{actionLabel[dossier.action] ?? dossier.action}</small></div>
    </div>
    <div className="holding-edit-cell" aria-label={`${dossier.item.name} 快速修改`}>
      <span className="holding-edit-title">编辑持仓</span>
      <label><span>代码</span><input aria-label={`股票代码 ${dossier.item.name}`} value={symbol} onChange={(event) => { setSymbol(event.target.value); update.reset(); }} /></label>
      <label><span>名称</span><input aria-label={`股票名称 ${dossier.item.name}`} value={name} onChange={(event) => { setName(event.target.value); update.reset(); }} /></label>
      <label><span>数量</span><input aria-label={`持仓数量 ${dossier.item.name}`} value={quantity} onChange={(event) => { setQuantity(event.target.value); update.reset(); }} /></label>
      <label><span>成本</span><input aria-label={`成本价 ${dossier.item.name}`} value={costPrice} onChange={(event) => { setCostPrice(event.target.value); update.reset(); }} /></label>
    </div>
    <div className="holding-actions-cell">
      {update.isSuccess && <em role="status">已保存</em>}
      {update.isError && <em className="negative" role="alert">{updateErrorText(update.error)}</em>}
      <button className="button secondary" type="button" aria-label={`保存 ${dossier.item.name}`} onClick={() => update.mutate()} disabled={update.isPending}><Save size={13} />{update.isPending ? "保存中…" : "保存"}</button>
      <Link className="text-link" to={`/stocks?symbol=${encodeURIComponent(dossier.item.symbol)}#stock-final-gate`}>查看个股依据 →</Link>
      <Link className="text-link ask-link" to={holdingAskHref(dossier)}>追问这个决定 →</Link>
    </div>
    </>}
  </article>;
}

export function HoldingsPage() {
  const client = useQueryClient();
  const [draft, setDraft] = useState<HoldingDraft>(emptyDraft);
  const [createNotice, setCreateNotice] = useState("");
  const [deleteNotice, setDeleteNotice] = useState<{ tone: "success" | "error"; message: string } | null>(null);
  const [sort, setSort] = useState<HoldingSort>("priority");
  const [visibleHoldingCount, setVisibleHoldingCount] = useState(HOLDING_PAGE_SIZE);
  const [showCreate, setShowCreate] = useState(false);
  const authScope = getAuthToken()?.slice(-16) ?? "anonymous";
  const query = useQuery({
    queryKey: ["holdings", "page", authScope],
    queryFn: () => api<HoldingDossier[]>("/api/v1/holdings"),
    retry: false,
    refetchInterval: 600_000,
    refetchIntervalInBackground: true,
  });
  const holdings = query.data ?? [];
  const orderedHoldings = useMemo(() => sortHoldings(holdings, sort), [holdings, sort]);
  const visibleHoldings = orderedHoldings.slice(0, visibleHoldingCount);
  const hiddenHoldingCount = Math.max(0, orderedHoldings.length - visibleHoldings.length);
  const summary = useMemo(() => portfolioSummary(holdings), [holdings]);
  const create = useMutation({
    mutationFn: () => api<HoldingDossier>("/api/v1/holdings", { method: "POST", body: JSON.stringify(toPayload(draft)) }),
    onSuccess: (created) => {
      const alreadyListed = holdings.some((item) => item.item.id === created.item.id || item.item.symbol === created.item.symbol);
      setDraft(emptyDraft);
      setCreateNotice(alreadyListed ? "这只股票已在持仓列表，未新增；已清空表单，可直接输入第二只。" : "已加入持仓，表单已清空。");
      setShowCreate(false);
      client.invalidateQueries({ queryKey: ["holdings"] });
    },
  });
  const remove = useMutation({
    mutationFn: ({ id }: { id: number; name: string }) => api(`/api/v1/holdings/${id}`, { method: "DELETE" }),
    onMutate: async ({ id }) => {
      setDeleteNotice(null);
      await client.cancelQueries({ queryKey: ["holdings", "page", authScope] });
      const previous = client.getQueryData<HoldingDossier[]>(["holdings", "page", authScope]);
      client.setQueryData<HoldingDossier[]>(["holdings", "page", authScope], (current) => current?.filter((item) => item.item.id !== id) ?? []);
      return { previous };
    },
    onSuccess: (_data, { name }) => setDeleteNotice({ tone: "success", message: `已删除 ${name}，之后不会再生成这只股票的持仓减仓提醒。` }),
    onError: (_error, _variables, context) => {
      if (context?.previous) client.setQueryData(["holdings", "page", authScope], context.previous);
      setDeleteNotice({ tone: "error", message: "删除失败，持仓已恢复，请稍后重试。" });
    },
    onSettled: () => client.invalidateQueries({ queryKey: ["holdings"] }),
  });

  useEffect(() => setVisibleHoldingCount(HOLDING_PAGE_SIZE), [sort]);

  function resetCreateDraft() {
    setDraft(emptyDraft);
    setCreateNotice("表单已清空，可以输入第二只股票。");
    create.reset();
  }

  function updateCreateName(name: string) {
    const symbol = draft.symbol.trim().toUpperCase();
    const wasDefaultMoutai = symbol === "SH.600519" && draft.name.trim() === "贵州茅台";
    setDraft({ ...draft, name, symbol: wasDefaultMoutai && name.trim() !== "贵州茅台" ? "" : draft.symbol });
    setCreateNotice("");
    create.reset();
  }

  const pageHeader = (steps: WorkbenchStep[]) => <>
    <WorkbenchPageHeader
      title="持仓"
      status={<div className="holdings-header-state"><span>真实持仓</span><strong>{query.data ? `${holdings.length} 只` : "读取中"}</strong><small>候选不会混入调仓建议</small></div>}
    />
    <PageTaskRail label="持仓" steps={steps} />
  </>;

  if (query.isError) {
    const hasToken = Boolean(getAuthToken());
    return <>
      {pageHeader([{ id: "holdings-access", label: "恢复访问", detail: "重新登录后读取组合" }])}
      <section id="holdings-access" className="panel personal-auth-gate" role="alert">
        <span>{hasToken ? "登录状态已失效" : "请先登录后查看个人持仓"}</span>
        <p>{hasToken ? "请重新登录。个人数据不会跨账号展示。" : "登录后仅显示当前账号的组合。"}</p>
      </section>
    </>;
  }

  if (query.isLoading) {
    return <>
      {pageHeader([{ id: "holdings-access", label: "读取组合", detail: "只加载当前账号" }])}
      <section id="holdings-access" className="panel holdings-loading" role="status">正在读取当前账号的真实持仓…</section>
    </>;
  }

  const createForm = <form id="holdings-create" aria-label="登记持仓" autoComplete="off" className="panel holding-create compact-create" onSubmit={(event) => { event.preventDefault(); setCreateNotice(""); create.mutate(); }}>
    <div className="panel-title"><span>登记持仓</span><button className="button secondary" type="button" onClick={resetCreateDraft}>清空表单</button></div>
    <p className="holding-create-help">代码和名称任选其一即可识别股票；数量、成本用于计算真实盈亏和调仓优先级。</p>
    <label>代码<input autoComplete="off" placeholder="如 SZ.000001 / HK.00700 / US.AAPL" value={draft.symbol} onChange={(event) => { setDraft({ ...draft, symbol: event.target.value }); setCreateNotice(""); create.reset(); }} /></label>
    <label>名称<input autoComplete="off" placeholder="如 平安银行 / 腾讯控股 / 苹果" value={draft.name} onChange={(event) => updateCreateName(event.target.value)} /></label>
    <label>数量<input autoComplete="off" placeholder="如 1000" value={draft.quantity} onChange={(event) => { setDraft({ ...draft, quantity: event.target.value }); setCreateNotice(""); create.reset(); }} /></label>
    <label>成本<input autoComplete="off" placeholder="如 11.20" value={draft.cost_price} onChange={(event) => { setDraft({ ...draft, cost_price: event.target.value }); setCreateNotice(""); create.reset(); }} /></label>
    <label>持仓逻辑<input autoComplete="off" placeholder="写下这笔持仓为什么值得留在组合里" value={draft.thesis} onChange={(event) => { setDraft({ ...draft, thesis: event.target.value }); setCreateNotice(""); create.reset(); }} /></label>
    <label>什么情况下减仓或退出<input autoComplete="off" placeholder="写下什么情况下必须降仓或退出" value={draft.invalidation} onChange={(event) => { setDraft({ ...draft, invalidation: event.target.value }); setCreateNotice(""); create.reset(); }} /></label>
    <button className="button" disabled={create.isPending}>{create.isPending ? "保存中…" : "加入持仓"}</button>
    {createNotice && <p className="form-success" role="status">{createNotice}</p>}
    {create.isError && <p className="form-error" role="alert">{createErrorText(create.error)}</p>}
  </form>;

  if (holdings.length === 0) {
    return <>
      {pageHeader([
        { id: "holdings-start", label: "确认边界", detail: "没有持仓就不生成减仓" },
        { id: "holdings-create", label: "录入持仓", detail: "数量、成本与退出条件" },
      ])}
      <section id="holdings-start" className="holding-onboarding holding-empty-start" aria-label="开始管理真实持仓">
        <header><h2>添加持仓</h2></header>
        {!showCreate ? <button className="button holding-first-action" type="button" onClick={() => setShowCreate(true)}>添加第一只持仓</button> : createForm}
      </section>
    </>;
  }

  return <>
    {pageHeader([
      { id: "holdings-overview", label: "组合结论", detail: "先看风险和今日动作" },
      { id: "holdings-positions", label: "逐只处理", detail: "按优先级查看持仓" },
      { id: "holdings-add", label: "维护组合", detail: "补录新的真实持仓" },
    ])}
    <section id="holdings-overview" className="portfolio-overview panel" aria-label="组合总览">
      <div className="panel-title"><span>组合</span></div>
      <div className="portfolio-hero-line">
        <article><span>组合市值</span><strong>{fmt(summary.totalValue, 0)}</strong></article>
        <article><span>浮动盈亏</span><strong className={summary.totalPnl >= 0 ? "up" : "down"}>{signedMoney(summary.totalPnl, 0)}</strong><small>收益率 {pct(summary.totalPnlPct)}</small></article>
        <article><span>持仓数量</span><strong>{holdings.length}</strong></article>
        <article><span>调仓信号</span><strong>{summary.trimCount + summary.addCount + summary.reviewCount}</strong><small>{summary.trimCount} 减 / {summary.addCount} 加</small></article>
      </div>
      <div className="portfolio-conclusion">
        <span>结论</span>
        <p>{plainLanguage(summary.conclusion)}</p>
        {summary.riskFlags.length > 0 && <div>{summary.riskFlags.slice(0, 4).map((flag) => <i key={flag}>{plainLanguage(flag)}</i>)}</div>}
      </div>
      <PortfolioMovementDeck summary={summary} />
      <PortfolioTodayFocus items={orderedHoldings} />
      {orderedHoldings.length > 0 && <details className="portfolio-detail-drawer"><summary><span>全持仓近 10 日走势</span><small>{orderedHoldings.length} 只股票 · 按需展开，减少页面长度</small></summary><PortfolioStockPlan items={orderedHoldings} /></details>}
    </section>

    <section id="holdings-positions" className="panel holdings-table-panel">
      <div className="panel-title"><span>持仓列表</span><small>{holdings.length} 笔</small></div>
      <div className="holding-sort-bar" aria-label="持仓排序">
        {holdingSortOptions.map(([value, label]) => <button
          key={value}
          type="button"
          className={sort === value ? "active" : ""}
          onClick={() => setSort(value)}
        >{label}</button>)}
      </div>
      {deleteNotice ? <p className={`holding-delete-notice ${deleteNotice.tone}`} role={deleteNotice.tone === "error" ? "alert" : "status"}>{deleteNotice.message}</p> : null}
      <div className="holdings-list" role="list" aria-label="持仓清单">
        {visibleHoldings.map((item) => <PositionRow key={item.item.id} dossier={item} onDelete={(id, name) => remove.mutate({ id, name })} deletePending={remove.isPending && remove.variables?.id === item.item.id} />)}
      </div>
      {holdings.length > HOLDING_PAGE_SIZE && <div className="holdings-list-controls"><span>已显示 {visibleHoldings.length} / {holdings.length} 笔持仓</span><div>{visibleHoldingCount > HOLDING_PAGE_SIZE && <button type="button" onClick={() => setVisibleHoldingCount(HOLDING_PAGE_SIZE)}>收起</button>}{hiddenHoldingCount > 0 && <button className="primary" type="button" onClick={() => setVisibleHoldingCount((current) => current + HOLDING_PAGE_SIZE)}>再显示 {Math.min(HOLDING_PAGE_SIZE, hiddenHoldingCount)} 笔</button>}</div></div>}
    </section>

    <details id="holdings-add" className="holding-create-drawer" onToggle={(event) => { if (event.currentTarget.open) resetCreateDraft(); }}>
      <summary>新增持仓</summary>
      {createForm}
    </details>
  </>;
}
