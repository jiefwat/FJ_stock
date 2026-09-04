import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { lazy, Suspense, useEffect, useState, type FormEvent } from "react";
import { Link, useLocation, useSearchParams } from "react-router-dom";

import { AsyncState } from "../../components/AsyncState";
import { PageTaskRail, WorkbenchPageHeader } from "../../components/WorkbenchPageHeader";
import { stockDecisionAction } from "../../lib/decision";
import { loadRecentResearch, rememberRecentResearch, type RecentResearch } from "../../lib/recentResearch";
import { api, fmt, pct, percent, type EvidenceDocument, type FinancialHealth, type InstrumentEvidenceResult, type Quote, type StockNewsSentiment } from "../../lib/api";
import { monitoringItem, monitoringText } from "../../lib/monitoring";
import { plainLanguage } from "../../lib/plainLanguage";
import { StockAskPanel } from "../ask/AskStockPage";

const StockTrend = lazy(() => import("./StockTrend").then((module) => ({ default: module.StockTrend })));

type ScoreFactor = {
  key: string;
  label: string;
  impact: number;
  signal: string;
  evidence: string;
  available: boolean;
};

type AnalysisDimension = {
  key: string;
  label: string;
  signal: string;
  score: number | null;
  summary: string;
  evidence: string[];
  available: boolean;
};

type InvestmentAdvice = {
  action: string;
  participation_status: "eligible" | "conditional" | "blocked";
  blockers: string[];
  position_hint: string;
  entry_plan: string;
  stop_loss: string;
  take_profit: string;
  time_horizon: string;
  confidence: number;
  rationale: string[];
  disclaimer: string;
};

type TrendForecast = {
  horizon: string;
  direction: string;
  confidence: number;
  summary: string;
  drivers: string[];
  invalidation: string;
};

type SignalValidation = {
  available: boolean;
  horizon_days: number;
  sample_count: number;
  positive_rate: number | null;
  average_return: number | null;
  worst_return: number | null;
  summary: string;
};

type ComparisonItem = {
  key: string;
  label: string;
  signal: string;
  value: string;
  benchmark: string;
  summary: string;
  percentile: number | null;
  available: boolean;
};

type Dossier = {
  quote: Quote;
  stance: string;
  stance_score: number | null;
  conclusion: string;
  evidence_coverage: number;
  score_factors: ScoreFactor[];
  analysis_dimensions: AnalysisDimension[];
  investment_advice: InvestmentAdvice;
  trend_forecast: TrendForecast;
  signal_validation: SignalValidation;
  horizontal_comparison: ComparisonItem[];
  vertical_comparison: ComparisonItem[];
  next_actions: string[];
  technical: Record<string, number | null> | null;
  bull_case: string[];
  bear_case: string[];
  invalidation: string[];
  missing_evidence: string[];
  research_evidence: string[];
  financial_health: FinancialHealth;
  news_sentiment: StockNewsSentiment;
  bars: { date: string; open: number; high: number; low: number; close: number; volume: number; amount: number }[];
};

type SearchNotice = { tone: "neutral" | "error"; message: string };
type SecondaryPanel = "drivers" | "evidence";
type DeepDossierSection = "company" | "history" | "scoring";

const stanceLabel: Record<string, string> = {
  strong_watch: "重点观察",
  watch: "观察",
  neutral: "中性",
  avoid: "回避",
  insufficient_data: "证据不足",
};

const sourcePresetLabels: Record<string, string> = {
  trend: "趋势延续",
  volume_breakout: "放量突破",
  value_rebound: "低估反弹",
  oversold_repair: "超跌修复",
};

function useDebouncedValue(value: string, delay = 220) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), delay);
    return () => window.clearTimeout(timer);
  }, [delay, value]);
  return debounced;
}

function directSymbol(value: string) {
  const normalized = value.trim().toUpperCase();
  if (/^(?:SH|SZ|BJ|HK|US)\.[A-Z0-9.]+$/.test(normalized)) return normalized;
  if (/^6\d{5}$/.test(normalized)) return `SH.${normalized}`;
  if (/^[03]\d{5}$/.test(normalized)) return `SZ.${normalized}`;
  if (/^[48]\d{5}$/.test(normalized)) return `BJ.${normalized}`;
  return null;
}

const conclusionLabels = ["投资建议", "技术面", "风险收益", "估值", "流动性", "基本面", "催化", "资金/行业", "横向对比", "纵向对比", "交易计划", "主要风险", "下一步"] as const;
const evidenceConclusionLabels = new Set<string>(["技术面", "风险收益", "估值", "流动性", "基本面", "催化", "资金/行业"]);
const dedicatedConclusionLabels = new Set<string>(["投资建议", "横向对比", "纵向对比"]);

type ConclusionSection = {
  label: string;
  content: string;
};

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function splitConclusion(conclusion: string) {
  const cleaned = conclusion.replace(/^总结论[：:]\s*/, "").trim();
  const pattern = new RegExp(`(${conclusionLabels.map(escapeRegExp).join("|")})[：:]`, "g");
  const matches = [...cleaned.matchAll(pattern)];
  if (matches.length === 0) return { overview: cleaned, sections: [] as ConclusionSection[] };

  const firstIndex = matches[0].index ?? 0;
  const overview = cleaned.slice(0, firstIndex).trim().replace(/[。；;,，]\s*$/, "");
  const sections = matches.map((match, index) => {
    const start = (match.index ?? 0) + match[0].length;
    const end = matches[index + 1]?.index ?? cleaned.length;
    return {
      label: match[1],
      content: cleaned.slice(start, end).trim().replace(/^[。；;,，\s]+/, "").replace(/\s+$/, ""),
    };
  }).filter((section) => section.content.length > 0);

  return { overview, sections };
}

function splitEvidence(content: string) {
  const parts = content.split(/[；;]/).map((item) => item.trim().replace(/[。；;]\s*$/, "")).filter(Boolean);
  return parts.length > 1 ? parts : [];
}

function ConclusionBrief({ dossier }: { dossier: Dossier }) {
  const brief = splitConclusion(dossier.conclusion);
  const visibleSections = brief.sections.filter((item) => !dedicatedConclusionLabels.has(item.label));
  const evidenceSections = visibleSections.filter((item) => evidenceConclusionLabels.has(item.label));
  const actionSections = visibleSections.filter((item) => !evidenceConclusionLabels.has(item.label));

  return <section className="panel stock-conclusion" aria-label="结构化总结论">
    <div className="panel-title"><span>总结论</span></div>
    <div className="conclusion-brief">
      <article className="conclusion-verdict">
        <span>当前判断</span>
        <strong>{stanceLabel[dossier.stance] ?? dossier.stance}</strong>
        <b>{dossier.stance_score == null ? "信息不足" : `${dossier.stance_score}/100`}</b>
        <em>仅供研究</em>
      </article>
      <article className="conclusion-summary">
        <span>摘要</span>
        <p>{plainLanguage(brief.overview || dossier.conclusion)}</p>
      </article>
    </div>
    {evidenceSections.length > 0 && <div className="conclusion-section">
      <h3>关键依据</h3>
      <div className="conclusion-grid">{evidenceSections.map((section) => {
        const bullets = splitEvidence(section.content);
        return <article key={section.label}>
          <span>{displayConclusionLabel(section.label)}</span>
          {bullets.length > 0 ? <ul>{bullets.map((item) => <li key={item}>{plainLanguage(item)}</li>)}</ul> : <p>{plainLanguage(section.content)}</p>}
        </article>;
      })}</div>
    </div>}
    {actionSections.length > 0 && <div className="conclusion-section conclusion-actions">
      <h3>操作纪律</h3>
      <div className="conclusion-grid action-grid">{actionSections.map((section) => {
        const bullets = splitEvidence(section.content);
        return <article key={section.label}>
          <span>{displayConclusionLabel(section.label)}</span>
          {bullets.length > 0 ? <ul>{bullets.map((item) => <li key={item}>{section.label === "下一步" ? monitoringText(item) : plainLanguage(item)}</li>)}</ul> : <p>{section.label === "下一步" ? monitoringText(section.content) : plainLanguage(section.content)}</p>}
        </article>;
      })}</div>
    </div>}
  </section>;
}


function displayConclusionLabel(label: string) {
  if (label === "交易计划") return "处理纪律";
  if (label === "投资建议") return "处理意见";
  if (label === "下一步") return "后续跟踪";
  if (label === "技术面") return "最近价格表现";
  if (label === "风险收益") return "可能收益和风险";
  if (label === "估值") return "当前价格贵不贵";
  if (label === "流动性") return "买卖是否方便";
  if (label === "基本面") return "公司经营情况";
  if (label === "催化") return "可能推动股价的消息";
  return plainLanguage(label);
}

function displayAdviceAction(action: string) {
  return stockDecisionAction(action);
}

function firstOrFallback(items: string[], fallback: string) {
  return items.find((item) => item.trim().length > 0) ?? fallback;
}

function AnalystActionMap({ dossier }: { dossier: Dossier }) {
  const cards = [
    { label: "为什么值得看", value: firstOrFallback(dossier.bull_case, "支持信息还不够，先不要急着下判断"), tone: "positive" },
    { label: "主要担心什么", value: firstOrFallback(dossier.bear_case, "暂时没有明显坏消息，但仍要留意价格起伏"), tone: "negative" },
    { label: "还缺什么信息", value: firstOrFallback(dossier.missing_evidence, "没有明显缺口，继续按现有信息观察"), tone: "neutral" },
    { label: "后续跟踪", value: monitoringText(firstOrFallback(dossier.next_actions, firstOrFallback(dossier.invalidation, "持续检查关键条件"))), tone: "action" },
  ];

  return <section className="analyst-action-map" aria-label="个股分析路径">
    <div className="map-title">
      <span>要点</span>
      <strong>核心检查</strong>
    </div>
    <div className="map-cards">{cards.map((card, index) => <article key={card.label} className={card.tone}>
      <b>{String(index + 1).padStart(2, "0")}</b>
      <span>{card.label}</span>
      <p>{plainLanguage(card.value)}</p>
    </article>)}</div>
  </section>;
}

function InvestmentAdvicePanel({ advice }: { advice: InvestmentAdvice }) {
  return <section className="investment-advice-panel" id="stock-investment-advice" aria-label="当前处理意见">
    <article className="advice-verdict">
      <span>处理意见</span>
      <strong>{displayAdviceAction(advice.action)}</strong>
      <em title="分析置信度反映证据与模型一致性，不代表上涨概率">分析置信度 {percent(advice.confidence * 100)}</em>
    </article>
    <div className="advice-plan">
      <p>{plainLanguage(advice.position_hint)}</p>
      <div className="advice-steps">
        <article><span>什么情况下考虑参与</span><p>{plainLanguage(advice.entry_plan)}</p></article>
        <article><span>什么情况下退出</span><p>{plainLanguage(advice.stop_loss)}</p></article>
        <article><span>什么时候先落袋</span><p>{plainLanguage(advice.take_profit)}</p></article>
        <article><span>复查频率</span><p>每 10 分钟 · {plainLanguage(advice.time_horizon)}</p></article>
      </div>
      {advice.rationale.length > 0 && <div className="advice-rationale"><strong>为什么这样处理</strong><ul>{advice.rationale.slice(0, 3).map((item) => <li key={item}>{plainLanguage(item)}</li>)}</ul></div>}
      <small>{plainLanguage(advice.disclaimer)}</small>
    </div>
  </section>;
}

function OpportunityReviewOutcome({ advice }: { advice: InvestmentAdvice }) {
  const upgraded = advice.action === "可小仓试错";
  const watchOnly = advice.action === "持有观察" || advice.action === "等待回踩";
  const verdict = upgraded ? "小仓复核" : watchOnly ? "仅观察" : "不参与";
  const tone = upgraded ? "positive" : watchOnly ? "caution" : "negative";
  const reason = advice.rationale[0] ?? advice.position_hint;

  return <section className={`opportunity-review-outcome ${tone}`} aria-label="线索结果">
    <div>
      <span>线索结果</span>
      <strong>{verdict}</strong>
      <p>处理意见：<b>{displayAdviceAction(advice.action)}</b></p>
    </div>
    <ol>
      <li>{plainLanguage(advice.position_hint)}</li>
      <li>{plainLanguage(reason)}</li>
      <li>按“什么情况下不再看好”执行。</li>
    </ol>
  </section>;
}


function factorCount(items: Array<{ signal: string; available?: boolean }>, signal: string) {
  return items.filter((item) => item.signal === signal && item.available !== false).length;
}

function sourceGapCount(evidence?: InstrumentEvidenceResult) {
  if (!evidence) return 0;
  return Object.values(evidence.capabilities).filter((item) => item.status === "unavailable" || item.status === "partial").length;
}

function participationRoute(dossier: Dossier) {
  const advice = dossier.investment_advice;
  if (advice.participation_status === "blocked") {
    return { tone: "negative", text: "先解除阻断", detail: advice.blockers[0] ?? "当前不满足新增仓位条件。" };
  }
  if (advice.participation_status === "eligible") {
    return { tone: "positive", text: "按计划试仓", detail: advice.position_hint };
  }
  return { tone: "caution", text: "等条件满足", detail: advice.entry_plan };
}

function EvidenceAuditDesk({ dossier, evidence }: { dossier: Dossier; evidence?: InstrumentEvidenceResult }) {
  const route = participationRoute(dossier);
  const supportCount = factorCount(dossier.score_factors, "positive") + dossier.bull_case.length;
  const riskCount = factorCount(dossier.score_factors, "negative") + dossier.bear_case.length;
  const gapCount = dossier.missing_evidence.length + sourceGapCount(evidence);
  const confirmers = [
    firstOrFallback(dossier.bull_case, "价格、资金或基本面支撑仍待确认"),
    firstOrFallback(dossier.research_evidence, "外部研究证据仍待补充"),
  ];
  const risks = [
    firstOrFallback(dossier.bear_case, "暂未识别主要反方证据"),
    firstOrFallback(dossier.invalidation, dossier.investment_advice.stop_loss),
  ];
  const gaps = dossier.missing_evidence.length > 0 ? dossier.missing_evidence : [gapCount > 0 ? "部分外部证据源未完全可用" : "暂无关键缺口，继续观察"];

  return <section className={`evidence-audit-desk ${route.tone}`} id="stock-evidence-audit" aria-label="依据">
    <article className="audit-verdict">
      <span>证据</span>
      <strong>{route.text}</strong>
      <p>{route.detail}</p>
      <small>覆盖 {percent(dossier.evidence_coverage * 100)} · 支持 {supportCount} · 反方 {riskCount} · 缺口 {gapCount}</small>
    </article>
    <div className="audit-ledger-grid">
      <article>
        <span>支持证据</span>
        <strong>{supportCount} 项</strong>
        {confirmers.map((item) => <p key={item}>＋ {item}</p>)}
      </article>
      <article>
        <span>反方证据</span>
        <strong>{riskCount} 项</strong>
        {risks.map((item) => <p key={item}>－ {item}</p>)}
      </article>
      <article>
        <span>证据缺口</span>
        <strong>{gapCount} 项</strong>
        {gaps.slice(0, 2).map((item) => <p key={item}>… {item}</p>)}
      </article>
      <article>
        <span>后续跟踪</span>
        <strong>{dossier.investment_advice.action}</strong>
        {(dossier.next_actions.length ? dossier.next_actions : [dossier.investment_advice.entry_plan]).slice(0, 2).map((item) => <p key={item}>● {monitoringText(item)}</p>)}
      </article>
    </div>
  </section>;
}

function TrendForecastPanel({ forecast }: { forecast: TrendForecast }) {
  return <section className="trend-forecast-panel" aria-label="未来趋势判断">
    <article className="trend-forecast-verdict">
      <span>未来趋势</span>
      <strong>{forecast.direction}</strong>
      <em>{forecast.horizon}</em>
      <b title="趋势置信度不代表上涨概率">趋势置信度 {percent(forecast.confidence * 100)}</b>
    </article>
    <div className="trend-forecast-body">
      <p>{plainLanguage(forecast.summary)}</p>
      <div className="trend-forecast-grid">
        {forecast.drivers.map((item) => <span key={item}>{plainLanguage(item)}</span>)}
      </div>
      <small>{plainLanguage(forecast.invalidation)}</small>
    </div>
  </section>;
}

function SignalValidationPanel({ validation }: { validation: SignalValidation }) {
  return <section className="panel signal-validation-panel" aria-label="历史信号验证">
    <div className="panel-title">
      <span>历史信号验证</span>
      <small>同类技术条件 · {validation.horizon_days} 个交易日后</small>
    </div>
    {validation.available ? <div className="signal-validation-metrics">
      <article><span>历史样本</span><strong>{validation.sample_count} 个样本</strong></article>
      <article><span>上涨比例</span><strong>{percent((validation.positive_rate ?? 0) * 100)}</strong></article>
      <article><span>平均收益</span><strong>{pct(validation.average_return)}</strong></article>
      <article><span>最差收益</span><strong>{pct(validation.worst_return)}</strong></article>
    </div> : <div className="signal-validation-empty">样本不足，暂不展示统计结论。</div>}
    <p>{validation.summary}</p>
  </section>;
}

function ComparisonSection({ horizontal, vertical }: { horizontal: ComparisonItem[]; vertical: ComparisonItem[] }) {
  const renderItems = (items: ComparisonItem[]) => items.map((item) => <article key={item.key} className={item.signal}>
    <header><span>{item.label}</span><strong>{item.value}</strong></header>
    <p>{item.summary}</p>
    <small>{item.benchmark}{item.percentile == null ? "" : ` · ${fmt(item.percentile, 0)}分位`}</small>
  </article>);

  return <section className="panel comparison-panel" aria-label="横向纵向对比">
    <div className="panel-title"><span>横向 / 纵向对比</span><small>同业位置 + 自身历史一起看</small></div>
    <div className="comparison-columns">
      <div>
        <h3>横向对比</h3>
        <div className="comparison-list">{renderItems(horizontal)}</div>
      </div>
      <div>
        <h3>纵向对比</h3>
        <div className="comparison-list">{renderItems(vertical)}</div>
      </div>
    </div>
  </section>;
}

function evidenceDate(value: string) {
  return new Date(value).toLocaleDateString("zh-CN", { month: "2-digit", day: "2-digit" });
}

function themeHref(theme: { code: string; name: string; change_pct: number | null }) {
  const params = new URLSearchParams({ theme: theme.code, themeName: theme.name });
  if (theme.change_pct != null) params.set("themeChange", String(theme.change_pct));
  return `/market?${params.toString()}`;
}

function actionTone(action: string) {
  if (/回避|不参与|先降风险/.test(action)) return "negative";
  if (/试错|观察|等待/.test(action)) return "caution";
  return "positive";
}

function compactActionLabel(action: string) {
  const value = action.trim();
  if (/已有仓位|可继续持有/.test(value)) return "继续持有";
  if (/控制仓位|试探/.test(value)) return "可小仓试探";
  if (/回避|不参与|先降风险/.test(value)) return "暂不参与";
  return value.length > 10 ? `${value.slice(0, 10)}…` : value;
}

function dimensionSummary(dossier: Dossier, key: string, fallback: string) {
  return dossier.analysis_dimensions.find((item) => item.key === key)?.summary ?? fallback;
}

function StockFocusBoard({ dossier, evidence }: { dossier: Dossier; evidence?: InstrumentEvidenceResult }) {
  const quote = dossier.quote;
  const tone = dossier.investment_advice.participation_status === "blocked" ? "negative" : actionTone(dossier.investment_advice.action);
  const firstTheme = evidence?.themes[0];
  const sectorName = quote.sector ?? firstTheme?.name ?? "板块待确认";
  const sectorLink = firstTheme ? themeHref(firstTheme) : quote.sector ? `/market?industry=${encodeURIComponent(quote.sector)}` : "/market";
  const actionLabel = compactActionLabel(displayAdviceAction(dossier.investment_advice.action));

  return <section className={`stock-focus-board stock-focus-redesign ${tone}`} id="stock-final-gate" aria-label="个股结论">
    <header className="stock-focus-identity">
      <div><span>{quote.symbol} · <Link className="stock-sector-link" aria-label={`查看${sectorName}板块`} to={sectorLink}>{sectorName}</Link></span><h2>{quote.name}</h2></div>
      <p>{fmt(quote.price)} <b className={(quote.change_pct ?? 0) >= 0 ? "up" : "down"}>{pct(quote.change_pct)}</b></p>
    </header>
    <div className="stock-chart-first">
      <aside className="stock-quick-brief">
        <article className="stock-verdict-card">
          <span>结论</span>
          <strong>{actionLabel}</strong>
          {actionLabel !== displayAdviceAction(dossier.investment_advice.action) ? <small className="stock-action-full">{displayAdviceAction(dossier.investment_advice.action)}</small> : null}
          <div className="stock-brief-metrics">
            <small><span>证据质量</span><b>{percent(dossier.investment_advice.confidence * 100)} / {percent(dossier.evidence_coverage * 100)}</b></small>
          </div>
          <small className="stock-brief-coverage">分析置信度 / 证据完整度，不代表上涨概率</small>
        </article>
        <section className="stock-action-sheet" id="stock-investment-advice" aria-label="当前处理意见">
          {dossier.investment_advice.participation_status === "blocked" && dossier.investment_advice.blockers.length > 0 ? <section className="stock-current-blocker" aria-label="当前阻断条件">
            <span>当前阻断条件</span>
            <strong>先不新增仓位</strong>
            <ul>{dossier.investment_advice.blockers.slice(0, 2).map((item) => <li key={item}>{plainLanguage(item)}</li>)}</ul>
          </section> : null}
          <div>
            <span>处理纪律</span>
            <p>{plainLanguage(dossier.investment_advice.position_hint)}</p>
          </div>
          <details className="stock-condition-disclosure">
            <summary><span>操作条件</span><strong>参与、停止与兑现</strong><small>展开</small></summary>
            <dl>
              <div><dt>触发参与</dt><dd>{plainLanguage(dossier.investment_advice.entry_plan)}</dd></div>
              <div><dt>停止跟踪</dt><dd>{plainLanguage(dossier.investment_advice.stop_loss)}</dd></div>
              <div><dt>复核兑现</dt><dd>{plainLanguage(dossier.investment_advice.take_profit)}</dd></div>
            </dl>
          </details>
        </section>
      </aside>
    </div>
  </section>;
}

function StockDecisionDeck({ dossier, evidence }: { dossier: Dossier; evidence?: InstrumentEvidenceResult }) {
  const firstTheme = evidence?.themes[0];
  const sectorName = dossier.quote.sector ?? firstTheme?.name ?? "板块待确认";
  const sectorLink = firstTheme ? themeHref(firstTheme) : dossier.quote.sector ? `/market?industry=${encodeURIComponent(dossier.quote.sector)}` : "/market";
  const tone = actionTone(dossier.investment_advice.action);
  const invalidation = firstOrFallback(dossier.invalidation, dossier.investment_advice.stop_loss);
  const nextAction = monitoringText(firstOrFallback(dossier.next_actions, dossier.investment_advice.entry_plan));
  const missing = firstOrFallback(dossier.missing_evidence, "暂无关键缺口");

  return <section className={`stock-decision-deck ${tone}`} id="stock-final-gate" aria-label="个股结论">
    <article className="decision-primary">
      <span>结论</span>
      <strong>{dossier.investment_advice.action}</strong>
      <p>{plainLanguage(dossier.investment_advice.position_hint)}</p>
      <small>分析置信度 {percent(dossier.investment_advice.confidence * 100)}（非上涨概率） · 证据完整度 {percent(dossier.evidence_coverage * 100)}</small>
    </article>
    <div className="decision-cards">
      <article>
        <span>板块</span>
        <strong>{sectorName}</strong>
          <Link to={sectorLink}>看板块</Link>
      </article>
      <article>
        <span>什么情况下不再看好</span>
        <strong>{plainLanguage(invalidation)}</strong>
        </article>
      <article>
        <span>监控项</span>
        <strong>{plainLanguage(nextAction)}</strong>
        <p>{plainLanguage(missing)}</p>
      </article>
    </div>
  </section>;
}

function EvidenceDocuments({ title, items, unavailable }: { title: string; items: EvidenceDocument[]; unavailable: boolean }) {
  return <div className="company-evidence-stream">
    <header><span>{title}</span><b>{items.length} 条</b></header>
    {unavailable && <p className="capability-warning">{title === "机构研报" ? "研报源暂不可用，公告与题材仍可继续核验。" : "公告源暂不可用，研报与题材仍可继续核验。"}</p>}
    {!unavailable && items.length === 0 && <p className="capability-empty">当前没有返回可用记录，不代表没有历史资料。</p>}
    {items.map((item) => <article key={item.id}>
      <time>{evidenceDate(item.published_at)}</time>
      <div>
        <a href={item.url} target="_blank" rel="noreferrer">{item.title}</a>
        <small>{item.publisher}{item.rating ? ` · ${item.rating}` : ""} · {item.category}</small>
      </div>
      <em className={item.source.freshness}>{item.source.label}</em>
    </article>)}
  </div>;
}

function CompanyEvidencePanel({ data, loading, failed }: { data?: InstrumentEvidenceResult; loading: boolean; failed: boolean }) {
  const filingsUnavailable = data?.capabilities.filings?.status === "unavailable";
  const researchUnavailable = data?.capabilities.research?.status === "unavailable";
  return <section className="panel company-evidence" id="stock-company-evidence" aria-label="公司证据包">
    <div className="panel-title"><span>公告 / 研报 / 题材</span></div>
    {loading && <div className="capability-empty">正在读取公告与研报元数据…</div>}
    {failed && <div className="capability-warning">公司证据接口暂不可用，价格、技术结构和原有分析仍可继续使用。</div>}
    {data && <>
      <div className="theme-row"><span>题材归属</span>{data.themes.length ? data.themes.slice(0, 12).map((theme) => <Link key={theme.code} to={themeHref(theme)}>{theme.name}<small>{pct(theme.change_pct)}</small></Link>) : <em>{data.capabilities.themes?.status === "unavailable" ? "题材源暂不可用" : "暂无题材映射"}</em>}</div>
      <div className="company-evidence-grid">
        <EvidenceDocuments title="公司公告" items={data.filings} unavailable={filingsUnavailable} />
        <EvidenceDocuments title="机构研报" items={data.research} unavailable={researchUnavailable} />
      </div>
    </>}
  </section>;
}

function StockDecisionDrivers({ dossier, open, onOpenChange }: { dossier: Dossier; open: boolean; onOpenChange: (open: boolean) => void }) {
  const financial = dossier.financial_health;
  const news = dossier.news_sentiment;
  const hasPriceHistory = dossier.bars.length >= 2;
  const latest = financial.periods[0];
  const latestNews = news.items[0];
  const invalidation = firstOrFallback(dossier.invalidation, dossier.investment_advice.stop_loss);

  return <details id="stock-decision-drivers" className="decision-driver-disclosure stock-secondary-disclosure" aria-label="四维决策依据" open={open}>
    <summary onClick={(event) => { event.preventDefault(); onOpenChange(!open); }}>
      <span>补充判断依据</span>
      <strong>公司、消息、价格与失效条件</strong>
      <small>按需展开</small>
    </summary>
    <section className="stock-intelligence-grid decision-driver-grid">
      <article className={`stock-intelligence-card ${financial.available ? "ready" : "unavailable"}`}>
      <header><span>公司经营</span><b>{financial.score == null ? "未评分" : `${fmt(financial.score, 0)}/100`}</b></header>
      <strong>{financial.conclusion}</strong>
      {latest ? <p>{latest.report_label} · 利润同比 {pct(latest.net_profit_yoy)}</p> : <p>暂无可用报告期</p>}
      {financial.risks[0] && <small>{financial.risks[0]}</small>}
    </article>
    <article className={`stock-intelligence-card ${news.hard_risk_count > 0 ? "risk" : news.available ? "ready" : "unavailable"}`}>
      <header><span>消息风险</span><b>近 {news.window_days} 天</b></header>
      <strong>{news.conclusion}</strong>
      {latestNews ? <a href={latestNews.url} target="_blank" rel="noreferrer">{latestNews.title}</a> : <p>暂无可用报道</p>}
    </article>
    <article className="stock-intelligence-card ready">
      <header><span>价格状态</span><b>{dossier.trend_forecast.horizon}</b></header>
      <strong>{dossier.trend_forecast.direction}</strong>
      <p>{plainLanguage(dossier.trend_forecast.summary)}</p>
    </article>
      <article className="stock-intelligence-card decision-change">
      <header><span>改变决定</span><b>自动监控</b></header>
      <strong>{plainLanguage(invalidation)}</strong>
      <p>{monitoringText(firstOrFallback(dossier.next_actions, invalidation))}</p>
      </article>
    </section>
    <details className="stock-price-disclosure">
      <summary><span>价格走势</span><strong>{hasPriceHistory ? "查看近期趋势图" : "历史行情暂缺"}</strong><small>按需展开</small></summary>
      <section className="stock-chart-area" aria-label="价格走势">
        {hasPriceHistory ? <Suspense fallback={<section className="trend-panel compact trend-loading" role="status">正在绘制走势…</section>}>
          <StockTrend bars={dossier.bars} compact />
        </Suspense> : <p className="stock-history-gap">历史行情暂缺，先按风险和处理纪律执行。</p>}
      </section>
    </details>
  </details>;
}

function StockIntelligenceDetails({ dossier }: { dossier: Dossier }) {
  const financial = dossier.financial_health;
  const news = dossier.news_sentiment;
  return <section className="panel stock-intelligence-details" aria-label="财务与新闻明细">
    <div>
      <h3>财报期间明细</h3>
      {financial.periods.length ? financial.periods.map((period) => <article key={period.report_date}>
        <header><strong>{period.report_label}</strong><span>{period.report_type}</span></header>
        <p>营收同比 {pct(period.revenue_yoy)} · 利润同比 {pct(period.net_profit_yoy)} · ROE {percent(period.roe, 2)}</p>
        <small>现金回收 {percent(period.cash_receipts_to_revenue, 2)} · 负债率 {percent(period.debt_to_assets, 2)}</small>
      </article>) : <p className="capability-empty">{financial.conclusion}</p>}
    </div>
    <div>
      <h3>近{news.window_days}天新闻明细</h3>
      {news.items.length ? news.items.map((item) => <article key={item.id} className={item.hard_risk ? "risk" : item.sentiment}>
        <header><a href={item.url} target="_blank" rel="noreferrer">{item.title}</a><time>{evidenceDate(item.published_at)}</time></header>
        <p>{item.summary || item.media}</p>
        <small>{item.media}{item.hard_risk_terms.length ? ` · ${item.hard_risk_terms.join(" / ")}` : ""}</small>
      </article>) : <p className="capability-empty">{news.conclusion}</p>}
    </div>
  </section>;
}

function StockDeepDossier({
  dossier,
  evidence,
  evidenceLoading,
  evidenceFailed,
  open,
  openSection,
  onOpenChange,
  onOpenSectionChange,
  onOpenEvidence,
}: {
  dossier: Dossier;
  evidence?: InstrumentEvidenceResult;
  evidenceLoading: boolean;
  evidenceFailed: boolean;
  open: boolean;
  openSection: DeepDossierSection | null;
  onOpenChange: (open: boolean) => void;
  onOpenSectionChange: (section: DeepDossierSection | null) => void;
  onOpenEvidence: () => void;
}) {
  return <details id="stock-deep-evidence" className="stock-deep-dossier" open={open}>
    <summary onClick={(event) => {
      event.preventDefault();
      const nextOpen = !open;
      onOpenChange(nextOpen);
      if (nextOpen) onOpenEvidence();
    }}>
      <span>查看专业数据</span>
      <strong>专业数据与来源</strong>
      <small>财报 · 新闻 · 历史样本 · 评分明细</small>
    </summary>
    {open ? <div className="stock-deep-stack">
      <header className="stock-deep-directory-head"><span>明细目录</span><strong>选择一组查看，其他内容保持收起</strong></header>
      <details className="stock-dossier-group" open={openSection === "company"}>
        <summary onClick={(event) => { event.preventDefault(); onOpenSectionChange(openSection === "company" ? null : "company"); }}>
          <em>01</em><span><strong>公司与消息</strong><small>财报、新闻、公告和研报</small></span>
        </summary>
        {openSection === "company" ? <div className="stock-dossier-group-content">
          <StockIntelligenceDetails dossier={dossier} />
          <CompanyEvidencePanel data={evidence} loading={evidenceLoading} failed={evidenceFailed} />
        </div> : null}
      </details>
      <details className="stock-dossier-group" open={openSection === "history"}>
        <summary onClick={(event) => { event.preventDefault(); onOpenSectionChange(openSection === "history" ? null : "history"); }}>
          <em>02</em><span><strong>比较与历史</strong><small>历史样本、同行和自身对比</small></span>
        </summary>
        {openSection === "history" ? <div className="stock-dossier-group-content">
          <SignalValidationPanel validation={dossier.signal_validation} />
          <ComparisonSection horizontal={dossier.horizontal_comparison} vertical={dossier.vertical_comparison} />
        </div> : null}
      </details>
      <details className="stock-dossier-group" open={openSection === "scoring"}>
        <summary onClick={(event) => { event.preventDefault(); onOpenSectionChange(openSection === "scoring" ? null : "scoring"); }}>
          <em>03</em><span><strong>模型与风控</strong><small>结论拆解、评分、技术和失效条件</small></span>
        </summary>
        {openSection === "scoring" ? <div className="stock-dossier-group-content">
          <AnalystActionMap dossier={dossier} />
          <ConclusionBrief dossier={dossier} />
          {dossier.analysis_dimensions.length > 0 && <section className="panel analysis-breakdown">
            <div className="panel-title"><span>分析拆解</span></div>
            <div className="dimension-grid">{dossier.analysis_dimensions.map((item) => <article key={item.key} className={item.signal}>
              <header><span>{item.label}</span><strong>{item.score == null ? "缺数据" : `${fmt(item.score, 0)}/100`}</strong></header>
              <p>{item.summary}</p>
              <ul>{item.evidence.map((itemEvidence) => <li key={itemEvidence}>{itemEvidence}</li>)}</ul>
            </article>)}</div>
          </section>}
          {dossier.next_actions.length > 0 && <section className="panel next-actions-panel">
            <div className="panel-title"><span>后续跟踪</span></div>
            <ol className="monitoring-action-list">{dossier.next_actions.map((item) => {
              const monitor = monitoringItem(item);
              return <li key={item} className={monitor.owner}><b>{monitor.label}</b><span>{monitor.text}</span></li>;
            })}</ol>
          </section>}
          <section className="panel evidence-ledger" id="stock-score-ledger">
            <div className="panel-title"><span>评分明细</span></div>
            <div className="ledger-list">{dossier.score_factors.map((factor) => <article key={factor.key} className={factor.signal}><span>{factor.label}</span><p>{factor.evidence}</p><strong>{factor.available ? `${factor.impact > 0 ? "+" : ""}${factor.impact}` : "未计入"}</strong></article>)}</div>
          </section>
          {dossier.research_evidence.length > 0 && <section className="panel research-evidence"><div className="panel-title"><span>语义研究</span></div>{dossier.research_evidence.map((item) => <p key={item}>＋ {item}</p>)}</section>}
          <div className="evidence-grid"><section className="panel"><div className="panel-title"><span>技术结构</span></div><div className="metric-grid">{dossier.technical ? Object.entries(dossier.technical).map(([key, value]) => <div key={key}><span>{key.toUpperCase()}</span><strong>{fmt(value)}</strong></div>) : <div className="empty">历史行情不足，不能生成技术判断。</div>}</div></section><section className="panel thesis" id="stock-risk-controls"><div><h3>支持证据</h3>{dossier.bull_case.map((item) => <p key={item} className="positive">＋ {item}</p>)}</div><div><h3>反方证据</h3>{dossier.bear_case.map((item) => <p key={item} className="negative">－ {item}</p>)}</div><div><h3>失效条件</h3>{dossier.invalidation.map((item) => <p key={item}>× {item}</p>)}</div><div><h3>仍缺什么</h3>{dossier.missing_evidence.map((item) => <p key={item}>… {item}</p>)}</div></section></div>
        </div> : null}
      </details>
    </div> : null}
  </details>;
}

export function StockLabPage() {
  const location = useLocation();
  const [params, setParams] = useSearchParams();
  const requestedSymbol = params.get("symbol")?.trim().toUpperCase() ?? "";
  const [term, setTerm] = useState(requestedSymbol);
  const [symbol, setSymbol] = useState(requestedSymbol);
  const [switcherOpen, setSwitcherOpen] = useState(false);
  const [selectedSearchValue, setSelectedSearchValue] = useState(requestedSymbol);
  const [loadEvidence, setLoadEvidence] = useState(false);
  const deepDossierOpen = ["#stock-company-evidence", "#stock-risk-controls", "#stock-score-ledger"].includes(location.hash);
  const linkedDeepSection: DeepDossierSection | null = location.hash === "#stock-company-evidence"
    ? "company"
    : ["#stock-risk-controls", "#stock-score-ledger"].includes(location.hash) ? "scoring" : null;
  const [openPanel, setOpenPanel] = useState<SecondaryPanel | null>(deepDossierOpen ? "evidence" : null);
  const [openDeepSection, setOpenDeepSection] = useState<DeepDossierSection | null>(linkedDeepSection);
  const [matches, setMatches] = useState<Quote[]>([]);
  const [highlightedMatch, setHighlightedMatch] = useState(-1);
  const [searchNotice, setSearchNotice] = useState<SearchNotice | null>(null);
  const [recent, setRecent] = useState<RecentResearch[]>(() => loadRecentResearch());
  const debouncedTerm = useDebouncedValue(term);
  const fromOpportunity = params.get("from") === "opportunities";
  const fromMarketBoard = params.get("from") === "market";
  const sourcePreset = params.get("preset") ?? "";
  const sourcePresetLabel = sourcePresetLabels[sourcePreset];
  const sourceBoardName = params.get("boardName") ?? "";
  const sourceBoardType = params.get("boardType") ?? "板块";

  const query = useQuery({
    queryKey: ["stock", symbol],
    queryFn: () => api<Dossier>(`/api/v1/stocks/${symbol}`),
    enabled: Boolean(symbol),
    staleTime: 600_000,
    refetchInterval: 600_000,
    refetchIntervalInBackground: true,
  });
  const evidenceQuery = useQuery({
    queryKey: ["instrument-evidence", symbol],
    queryFn: () => api<InstrumentEvidenceResult>(`/api/v1/instruments/${symbol}/evidence?limit=20`),
    enabled: Boolean(symbol) && loadEvidence,
    staleTime: 300_000,
  });

  useEffect(() => {
    if (requestedSymbol === symbol) return;
    setSymbol(requestedSymbol);
    setTerm(requestedSymbol);
    setSelectedSearchValue(requestedSymbol);
    setMatches([]);
    setHighlightedMatch(-1);
    setSearchNotice(null);
    setLoadEvidence(false);
    setSwitcherOpen(false);
  }, [requestedSymbol, symbol]);

  useEffect(() => {
    setLoadEvidence(deepDossierOpen);
    setOpenPanel(deepDossierOpen ? "evidence" : null);
    setOpenDeepSection(linkedDeepSection);
  }, [deepDossierOpen, linkedDeepSection, symbol]);

  useEffect(() => {
    const normalizedTerm = debouncedTerm.trim();
    if (normalizedTerm.length < 2 || normalizedTerm.toUpperCase() === selectedSearchValue.toUpperCase() || /^(?:SH|SZ|BJ|HK|US)\.[A-Z0-9.]+$/i.test(normalizedTerm)) {
      setMatches([]);
      setHighlightedMatch(-1);
      setSearchNotice(null);
      return undefined;
    }
    const currentQuote = query.data?.quote;
    if (currentQuote && [currentQuote.symbol, currentQuote.code, currentQuote.name].some((value) => value.toUpperCase() === normalizedTerm.toUpperCase())) {
      setMatches([]);
      setHighlightedMatch(-1);
      setSearchNotice(null);
      return undefined;
    }
    let ignore = false;
    setSearchNotice({ tone: "neutral", message: "正在查找股票…" });
    api<Quote[]>(`/api/v1/search?q=${encodeURIComponent(normalizedTerm)}`)
      .then((items) => {
        if (ignore) return;
        setMatches(items);
        setHighlightedMatch(-1);
        setSearchNotice(items.length
          ? { tone: "neutral", message: `找到 ${items.length} 只股票，请选择后开始分析。` }
          : { tone: "error", message: "没有找到匹配股票，请检查名称或代码。" });
      })
      .catch(() => {
        if (!ignore) {
          setMatches([]);
          setHighlightedMatch(-1);
          setSearchNotice({ tone: "error", message: "股票搜索暂时不可用，请稍后重试。" });
        }
      });
    return () => { ignore = true; };
  }, [debouncedTerm, query.data?.quote, selectedSearchValue]);

  useEffect(() => {
    if (!query.data) return;
    setTerm(query.data.quote.name);
    setSelectedSearchValue(query.data.quote.name);
    setRecent(rememberRecentResearch(query.data.quote));
  }, [query.data]);

  useEffect(() => {
    if (!query.data || !location.hash) return;
    const targetId = location.hash.slice(1);
    const runAfterPaint = window.requestAnimationFrame ?? ((callback: FrameRequestCallback) => window.setTimeout(callback, 0));
    runAfterPaint(() => {
      const target = document.getElementById(targetId);
      if (typeof target?.scrollIntoView === "function") {
        target.scrollIntoView({ block: "start" });
      }
    });
  }, [location.hash, query.data]);

  const choose = (quote: Quote) => {
    setSymbol(quote.symbol);
    setTerm(quote.name);
    setSelectedSearchValue(quote.name);
    setMatches([]);
    setHighlightedMatch(-1);
    setSearchNotice(null);
    setLoadEvidence(false);
    setSwitcherOpen(false);
    setParams({ symbol: quote.symbol });
  };

  const chooseSymbol = (nextSymbol: string, label = nextSymbol) => {
    setSymbol(nextSymbol);
    setTerm(label);
    setSelectedSearchValue(label);
    setMatches([]);
    setHighlightedMatch(-1);
    setSearchNotice(null);
    setLoadEvidence(false);
    setSwitcherOpen(false);
    setParams({ symbol: nextSymbol });
  };

  const submitSearch = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const value = term.trim();
    if (!value) {
      setSearchNotice({ tone: "error", message: "请输入股票名称或代码。" });
      return;
    }
    const normalized = directSymbol(value);
    if (normalized) {
      chooseSymbol(normalized);
      return;
    }
    const exact = matches.find((item) => [item.symbol, item.code, item.name].some((candidate) => candidate.toUpperCase() === value.toUpperCase()));
    if (exact) {
      choose(exact);
      return;
    }
    try {
      setSearchNotice({ tone: "neutral", message: "正在查找股票…" });
      const items = await api<Quote[]>(`/api/v1/search?q=${encodeURIComponent(value)}`);
      setMatches(items);
      setHighlightedMatch(-1);
      if (items.length === 1) choose(items[0]);
      else setSearchNotice(items.length
        ? { tone: "neutral", message: `找到 ${items.length} 只股票，请选择后开始分析。` }
        : { tone: "error", message: "没有找到匹配股票，请检查名称或代码。" });
    } catch {
      setMatches([]);
      setSearchNotice({ tone: "error", message: "股票搜索暂时不可用，请稍后重试。" });
    }
  };

  return <>
    <WorkbenchPageHeader
      title="个股"
      status={symbol ? undefined : <div className="stock-header-state neutral"><span>当前标的</span><strong>尚未选择</strong><small>不会默认分析茅台</small></div>}
    />
    <PageTaskRail label="个股" className="stock-page-task-rail" steps={symbol ? [
      { id: "stock-final-gate", label: "结论", detail: "动作与仓位纪律" },
      { id: "stock-decision-drivers", label: "依据", detail: "公司、消息与价格" },
      { id: "stock-questions", label: "追问", detail: "影响决定的问题" },
      { id: "stock-deep-evidence", label: "明细", detail: "财报、来源与评分" },
    ] : [
      { id: "stock-select", label: "选择股票", detail: "名称或代码均可" },
      { id: "stock-start", label: "选择来源", detail: "最近查看或市场线索" },
    ]} />
    <div id="stock-select" className={`stock-control-row ${symbol ? "stock-switcher-compact" : ""}`}>
      {symbol ? <button
        type="button"
        className="stock-switcher-toggle"
        aria-expanded={switcherOpen}
        aria-controls="stock-switcher-search"
        onClick={() => setSwitcherOpen((current) => !current)}
      >
        <Search size={16} aria-hidden="true" />
        <span>切换股票</span>
        <small>{query.data?.quote.name ?? symbol} · {symbol}</small>
      </button> : null}
      {(!symbol || switcherOpen) ? <form id="stock-switcher-search" className="stock-search" role="search" aria-label="选择股票进行分析" onSubmit={submitSearch}>
        <Search size={18} aria-hidden="true" />
        <input role="combobox" autoFocus={Boolean(symbol)} value={term} onFocus={(event) => { if (symbol) event.currentTarget.select(); }} onChange={(event) => { setTerm(event.target.value); setSelectedSearchValue(""); setHighlightedMatch(-1); setSearchNotice(null); }} onKeyDown={(event) => {
          if (event.key === "Escape") {
            setMatches([]);
            setHighlightedMatch(-1);
            setSearchNotice(null);
            if (symbol) setSwitcherOpen(false);
          } else if (matches.length > 0 && event.key === "ArrowDown") {
            event.preventDefault();
            setHighlightedMatch((current) => current >= matches.length - 1 ? 0 : current + 1);
          } else if (matches.length > 0 && event.key === "ArrowUp") {
            event.preventDefault();
            setHighlightedMatch((current) => current <= 0 ? matches.length - 1 : current - 1);
          } else if (event.key === "Enter" && highlightedMatch >= 0 && matches[highlightedMatch]) {
            event.preventDefault();
            choose(matches[highlightedMatch]);
          }
        }} placeholder="输入股票代码或名称，如 600519 / HK.00700 / US.AAPL" aria-label="搜索股票" aria-autocomplete="list" aria-controls="stock-search-results" aria-activedescendant={highlightedMatch >= 0 ? `stock-search-option-${highlightedMatch}` : undefined} aria-describedby={searchNotice ? "stock-search-feedback" : undefined} aria-expanded={matches.length > 0} />
        <button type="submit" className="stock-search-submit">分析</button>
        {matches.length > 0 && <div className="search-results" id="stock-search-results" role="listbox" aria-label="股票搜索结果">{matches.map((item, index) => <button type="button" role="option" aria-selected={highlightedMatch === index} id={`stock-search-option-${index}`} className={highlightedMatch === index ? "active" : ""} key={item.symbol} onMouseEnter={() => setHighlightedMatch(index)} onClick={() => choose(item)}><b>{item.name}</b><span>{item.symbol}</span></button>)}</div>}
      </form> : null}
      {fromOpportunity && <section className="stock-source-note compact" aria-label="线索来源"><strong>候选</strong>{sourcePresetLabel && <small>{sourcePresetLabel}</small>}</section>}
      {fromMarketBoard && <section className="stock-source-note compact" aria-label="板块来源"><strong>{sourceBoardName || "板块"}</strong><small>{sourceBoardType}</small></section>}
    </div>
    {searchNotice ? <p className={`stock-search-notice ${searchNotice.tone}`} id="stock-search-feedback" role={searchNotice.tone === "error" ? "alert" : "status"}>{searchNotice.message}</p> : null}
    {!symbol ? <section id="stock-start" className="stock-start-state" aria-label="开始股票分析">
      <h2>选择股票</h2>
      {recent.length > 0 ? <div><strong>最近查看</strong><nav>{recent.map((item) => <button type="button" key={item.symbol} onClick={() => chooseSymbol(item.symbol, item.name)}><b>{item.name}</b><small>{item.symbol}{item.sector ? ` · ${item.sector}` : ""}</small></button>)}</nav></div> : null}
      <div className="stock-start-routes"><nav><Link to="/opportunities"><b>今日候选</b></Link><Link to="/limit-ladder"><b>连板梯队</b></Link></nav></div>
    </section> : null}
    <AsyncState loading={query.isLoading} loadingText={`正在核对 ${term || symbol} 的行情、财务与风险…`} error={query.error as Error | null} onRetry={() => void query.refetch()}>{query.data && <>
    <StockFocusBoard dossier={query.data} evidence={evidenceQuery.data} />
      <section className="stock-section-directory" aria-label="个股分析目录">
        <StockDecisionDrivers dossier={query.data} open={openPanel === "drivers"} onOpenChange={(open) => setOpenPanel(open ? "drivers" : null)} />
        <StockAskPanel key={query.data.quote.symbol} symbol={query.data.quote.symbol} name={query.data.quote.name} />
        <StockDeepDossier
          dossier={query.data}
          evidence={evidenceQuery.data}
          evidenceLoading={evidenceQuery.isLoading}
          evidenceFailed={evidenceQuery.isError}
          open={openPanel === "evidence"}
          openSection={openDeepSection}
          onOpenChange={(open) => {
            setOpenPanel(open ? "evidence" : null);
            if (!open) setOpenDeepSection(null);
          }}
          onOpenSectionChange={setOpenDeepSection}
          onOpenEvidence={() => setLoadEvidence(true)}
        />
      </section>
    </>}</AsyncState>
  </>;
}
