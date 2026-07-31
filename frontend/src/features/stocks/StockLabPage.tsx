import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useLocation, useSearchParams } from "react-router-dom";

import { AsyncState } from "../../components/AsyncState";
import { rememberRecentResearch } from "../../lib/recentResearch";
import { api, fmt, pct, percent, type EvidenceDocument, type InstrumentEvidenceResult, type Quote } from "../../lib/api";
import { StockTrend } from "./StockTrend";

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
  bars: { date: string; close: number }[];
};

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

function askHref(dossier: Dossier, params: URLSearchParams, question?: string) {
  const askParams = new URLSearchParams({
    symbol: dossier.quote.symbol,
    name: dossier.quote.name,
    from: params.get("from") ?? "stock",
  });
  if (question) askParams.set("question", question);
  ["preset", "board", "boardName", "boardType"].forEach((key) => {
    const value = params.get(key);
    if (value) askParams.set(key, value);
  });
  return `/ask?${askParams.toString()}`;
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
        <b>{dossier.stance_score == null ? "证据不足" : `${dossier.stance_score}/100`}</b>
        <em>仅供研究</em>
      </article>
      <article className="conclusion-summary">
        <span>摘要</span>
        <p>{brief.overview || dossier.conclusion}</p>
      </article>
    </div>
    {evidenceSections.length > 0 && <div className="conclusion-section">
      <h3>关键依据</h3>
      <div className="conclusion-grid">{evidenceSections.map((section) => {
        const bullets = splitEvidence(section.content);
        return <article key={section.label}>
          <span>{section.label}</span>
          {bullets.length > 0 ? <ul>{bullets.map((item) => <li key={item}>{item}</li>)}</ul> : <p>{section.content}</p>}
        </article>;
      })}</div>
    </div>}
    {actionSections.length > 0 && <div className="conclusion-section conclusion-actions">
      <h3>操作纪律</h3>
      <div className="conclusion-grid action-grid">{actionSections.map((section) => {
        const bullets = splitEvidence(section.content);
        return <article key={section.label}>
          <span>{section.label}</span>
          {bullets.length > 0 ? <ul>{bullets.map((item) => <li key={item}>{item}</li>)}</ul> : <p>{section.content}</p>}
        </article>;
      })}</div>
    </div>}
  </section>;
}

function firstOrFallback(items: string[], fallback: string) {
  return items.find((item) => item.trim().length > 0) ?? fallback;
}

function AnalystActionMap({ dossier }: { dossier: Dossier }) {
  const cards = [
    { label: "先看支撑", value: firstOrFallback(dossier.bull_case, "支撑证据不足，先不要急着下判断"), tone: "positive" },
    { label: "再看风险", value: firstOrFallback(dossier.bear_case, "暂未识别主要反方依据，但仍需观察波动"), tone: "negative" },
    { label: "证据缺口", value: firstOrFallback(dossier.missing_evidence, "没有明显缺口，继续按当前证据复盘"), tone: "neutral" },
    { label: "下一步动作", value: firstOrFallback(dossier.next_actions, firstOrFallback(dossier.invalidation, "先设定观察节奏")), tone: "action" },
  ];

  return <section className="analyst-action-map" aria-label="个股分析路径">
    <div className="map-title">
      <span>要点</span>
      <strong>核心检查</strong>
    </div>
    <div className="map-cards">{cards.map((card, index) => <article key={card.label} className={card.tone}>
      <b>{String(index + 1).padStart(2, "0")}</b>
      <span>{card.label}</span>
      <p>{card.value}</p>
    </article>)}</div>
  </section>;
}

function InvestmentAdvicePanel({ advice }: { advice: InvestmentAdvice }) {
  return <section className="investment-advice-panel" id="stock-investment-advice" aria-label="直接投资建议">
    <article className="advice-verdict">
      <span>直接建议</span>
      <strong>{advice.action}</strong>
      <em>置信度 {percent(advice.confidence * 100)}</em>
    </article>
    <div className="advice-plan">
      <p>{advice.position_hint}</p>
      <div className="advice-steps">
        <article><span>入场计划</span><p>{advice.entry_plan}</p></article>
        <article><span>止损纪律</span><p>{advice.stop_loss}</p></article>
        <article><span>止盈检查</span><p>{advice.take_profit}</p></article>
        <article><span>复盘周期</span><p>{advice.time_horizon}</p></article>
      </div>
      {advice.rationale.length > 0 && <div className="advice-rationale"><strong>为什么是这个建议</strong><ul>{advice.rationale.slice(0, 3).map((item) => <li key={item}>{item}</li>)}</ul></div>}
      <small>{advice.disclaimer}</small>
    </div>
  </section>;
}

function OpportunityReviewOutcome({ advice }: { advice: InvestmentAdvice }) {
  const upgraded = advice.action === "可小仓试错";
  const watchOnly = advice.action === "持有观察" || advice.action === "等待回踩";
  const verdict = upgraded ? "可试错" : watchOnly ? "仅观察" : "不参与";
  const tone = upgraded ? "positive" : watchOnly ? "caution" : "negative";
  const reason = advice.rationale[0] ?? advice.position_hint;

  return <section className={`opportunity-review-outcome ${tone}`} aria-label="线索结果">
    <div>
      <span>线索结果</span>
      <strong>{verdict}</strong>
      <p>当前建议：<b>{advice.action}</b></p>
    </div>
    <ol>
      <li>{advice.position_hint}</li>
      <li>{reason}</li>
      <li>按失效条件执行。</li>
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

function evidenceRoute(dossier: Dossier, evidence?: InstrumentEvidenceResult) {
  const riskCount = factorCount(dossier.score_factors, "negative") + dossier.bear_case.length;
  const supportCount = factorCount(dossier.score_factors, "positive") + dossier.bull_case.length;
  const gapCount = dossier.missing_evidence.length + sourceGapCount(evidence);

  if (dossier.evidence_coverage < 0.6 || gapCount >= 2) {
    return { tone: "caution", text: "补证据", detail: "公告、研报或板块仍有缺口。" };
  }
  if (riskCount > supportCount) {
    return { tone: "negative", text: "守失效线", detail: "反方多于支持。" };
  }
  return { tone: "positive", text: "看交易计划", detail: "支持多于反方。" };
}

function EvidenceAuditDesk({ dossier, evidence }: { dossier: Dossier; evidence?: InstrumentEvidenceResult }) {
  const route = evidenceRoute(dossier, evidence);
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
        <span>动作</span>
        <strong>{dossier.investment_advice.action}</strong>
        {(dossier.next_actions.length ? dossier.next_actions : [dossier.investment_advice.entry_plan]).slice(0, 2).map((item) => <p key={item}>→ {item}</p>)}
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
      <b>置信度 {percent(forecast.confidence * 100)}</b>
    </article>
    <div className="trend-forecast-body">
      <p>{forecast.summary}</p>
      <div className="trend-forecast-grid">
        {forecast.drivers.map((item) => <span key={item}>{item}</span>)}
      </div>
      <small>{forecast.invalidation}</small>
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

function compactItems(items: string[], fallback: string, max = 3) {
  const values = items.map((item) => item.trim()).filter(Boolean);
  return (values.length ? values : [fallback]).slice(0, max);
}

function StockFocusBoard({ dossier, evidence, params }: { dossier: Dossier; evidence?: InstrumentEvidenceResult; params: URLSearchParams }) {
  const quote = dossier.quote;
  const tone = actionTone(dossier.investment_advice.action);
  const route = evidenceRoute(dossier, evidence);
  const firstTheme = evidence?.themes[0];
  const sectorName = quote.sector ?? firstTheme?.name ?? "板块待确认";
  const sectorLink = firstTheme ? themeHref(firstTheme) : quote.sector ? `/market?industry=${encodeURIComponent(quote.sector)}` : "/market";
  const reasons = compactItems(
    [...dossier.investment_advice.rationale, ...dossier.trend_forecast.drivers, ...dossier.bull_case],
    "暂无足够优势证据，先观察。",
  );
  const risks = compactItems(
    [...dossier.bear_case, ...dossier.invalidation, ...dossier.missing_evidence],
    "暂无明确反方，但仍按止损线执行。",
  );

  return <section className={`stock-focus-board stock-focus-redesign ${tone}`} id="stock-final-gate" aria-label="个股结论">
    <header className="stock-focus-hero">
      <div className="stock-identity">
        <span>{quote.symbol} · {sectorName}</span>
        <h2>{quote.name}</h2>
        <p>{fmt(quote.price)} <b className={(quote.change_pct ?? 0) >= 0 ? "up" : "down"}>{pct(quote.change_pct)}</b></p>
      </div>
      <article className="stock-verdict-card">
        <span>结论</span>
        <strong>{dossier.investment_advice.action}</strong>
        <small>置信 {percent(dossier.investment_advice.confidence * 100)} · 证据 {percent(dossier.evidence_coverage * 100)}</small>
      </article>
      <div className="stock-focus-metrics">
        <span>趋势 <b>{dossier.trend_forecast.direction}</b></span>
        <span>置信 <b>{percent(dossier.investment_advice.confidence * 100)}</b></span>
        <span>证据 <b>{percent(dossier.evidence_coverage * 100)}</b></span>
      </div>
    </header>

    <section className="stock-action-sheet" id="stock-investment-advice" aria-label="直接投资建议">
      <div>
        <span>怎么做</span>
        <p>{dossier.investment_advice.position_hint}</p>
      </div>
      <dl>
        <div><dt>入场</dt><dd>{dossier.investment_advice.entry_plan}</dd></div>
        <div><dt>止损</dt><dd>{dossier.investment_advice.stop_loss}</dd></div>
        <div><dt>止盈</dt><dd>{dossier.investment_advice.take_profit}</dd></div>
      </dl>
    </section>

    <div className="stock-focus-content">
      <section className="focus-card" id="stock-evidence-audit" aria-label="依据">
        <span>为什么</span>
        <ul>{reasons.map((item) => <li key={item}>{item}</li>)}</ul>
      </section>
      <section className="focus-card">
        <span>风险</span>
        <ul>{risks.map((item) => <li key={item}>{item}</li>)}</ul>
      </section>
      <section className="focus-card" aria-label="未来趋势判断">
        <span>趋势</span>
        <strong>{dossier.trend_forecast.direction}</strong>
        <p>{route.text}</p>
      </section>
    </div>

    <footer className="stock-focus-actions">
      <Link to={sectorLink}>看板块</Link>
      <Link to={askHref(dossier, params)}>问股</Link>
    </footer>
  </section>;
}

function StockDecisionDeck({ dossier, evidence }: { dossier: Dossier; evidence?: InstrumentEvidenceResult }) {
  const firstTheme = evidence?.themes[0];
  const sectorName = dossier.quote.sector ?? firstTheme?.name ?? "板块待确认";
  const sectorLink = firstTheme ? themeHref(firstTheme) : dossier.quote.sector ? `/market?industry=${encodeURIComponent(dossier.quote.sector)}` : "/market";
  const tone = actionTone(dossier.investment_advice.action);
  const invalidation = firstOrFallback(dossier.invalidation, dossier.investment_advice.stop_loss);
  const nextAction = firstOrFallback(dossier.next_actions, dossier.investment_advice.entry_plan);
  const missing = firstOrFallback(dossier.missing_evidence, "暂无关键缺口");

  return <section className={`stock-decision-deck ${tone}`} id="stock-final-gate" aria-label="个股结论">
    <article className="decision-primary">
      <span>结论</span>
      <strong>{dossier.investment_advice.action}</strong>
      <p>{dossier.investment_advice.position_hint}</p>
      <small>置信度 {percent(dossier.investment_advice.confidence * 100)} · 证据覆盖 {percent(dossier.evidence_coverage * 100)}</small>
    </article>
    <div className="decision-cards">
      <article>
        <span>板块</span>
        <strong>{sectorName}</strong>
          <Link to={sectorLink}>看板块</Link>
      </article>
      <article>
        <span>失效条件</span>
        <strong>{invalidation}</strong>
        </article>
      <article>
        <span>动作</span>
        <strong>{nextAction}</strong>
        <p>{missing}</p>
      </article>
    </div>
  </section>;
}

function StockAskRouter({ dossier, params }: { dossier: Dossier; params: URLSearchParams }) {
  const name = dossier.quote.name;
  const routes = [
    {
      label: "问风险",
      intent: "风险",
      detail: "失效条件、利空。",
      question: `${name}现在主要风险是什么`,
    },
    {
      label: "问异动",
      intent: "异动",
      detail: "涨跌、量能、结构。",
      question: `最近${name}怎么大跌`,
    },
    {
      label: "问基本面",
      intent: "基本面",
      detail: "财报、现金流、估值。",
      question: `${name}基本面怎么样`,
    },
    {
      label: "问催化",
      intent: "催化",
      detail: "公告、研报、题材。",
      question: `${name}有什么公告催化`,
    },
  ];

  return <section className="stock-ask-router" aria-label="个股问股快捷入口">
    <div>
      <span>问股</span>
      <strong>继续问</strong>
    </div>
    <nav>
      {routes.map((route) => <Link key={route.intent} to={askHref(dossier, params, route.question)}>
        <b>{route.intent}</b>
        <strong>{route.label}</strong>
        <small>{route.detail}</small>
      </Link>)}
    </nav>
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

function StockDeepDossier({
  dossier,
  evidence,
  evidenceLoading,
  evidenceFailed,
  open,
}: {
  dossier: Dossier;
  evidence?: InstrumentEvidenceResult;
  evidenceLoading: boolean;
  evidenceFailed: boolean;
  open: boolean;
}) {
  return <details className="stock-deep-dossier" open={open}>
    <summary>
      <span>更多数据</span>
      <strong>明细</strong>
    </summary>
    <div className="stock-deep-stack">
      <SignalValidationPanel validation={dossier.signal_validation} />
      <ComparisonSection horizontal={dossier.horizontal_comparison} vertical={dossier.vertical_comparison} />
      <AnalystActionMap dossier={dossier} />
      <ConclusionBrief dossier={dossier} />
      <CompanyEvidencePanel data={evidence} loading={evidenceLoading} failed={evidenceFailed} />
      {dossier.analysis_dimensions.length > 0 && <section className="panel analysis-breakdown">
        <div className="panel-title"><span>分析拆解</span></div>
        <div className="dimension-grid">{dossier.analysis_dimensions.map((item) => <article key={item.key} className={item.signal}>
          <header><span>{item.label}</span><strong>{item.score == null ? "缺数据" : `${fmt(item.score, 0)}/100`}</strong></header>
          <p>{item.summary}</p>
          <ul>{item.evidence.map((evidence) => <li key={evidence}>{evidence}</li>)}</ul>
        </article>)}</div>
      </section>}
      {dossier.next_actions.length > 0 && <section className="panel next-actions-panel">
        <div className="panel-title"><span>动作</span></div>
        <ol>{dossier.next_actions.map((item) => <li key={item}>{item}</li>)}</ol>
      </section>}
      <StockTrend bars={dossier.bars} />
      <section className="panel evidence-ledger" id="stock-score-ledger">
        <div className="panel-title"><span>评分明细</span></div>
        <div className="ledger-list">{dossier.score_factors.map((factor) => <article key={factor.key} className={factor.signal}><span>{factor.label}</span><p>{factor.evidence}</p><strong>{factor.available ? `${factor.impact > 0 ? "+" : ""}${factor.impact}` : "未计入"}</strong></article>)}</div>
      </section>
      {dossier.research_evidence.length > 0 && <section className="panel research-evidence"><div className="panel-title"><span>语义研究</span></div>{dossier.research_evidence.map((item) => <p key={item}>＋ {item}</p>)}</section>}
      <div className="evidence-grid"><section className="panel"><div className="panel-title"><span>技术结构</span></div><div className="metric-grid">{dossier.technical ? Object.entries(dossier.technical).map(([key, value]) => <div key={key}><span>{key.toUpperCase()}</span><strong>{fmt(value)}</strong></div>) : <div className="empty">历史行情不足，不能生成技术判断。</div>}</div></section><section className="panel thesis" id="stock-risk-controls"><div><h3>支持证据</h3>{dossier.bull_case.map((item) => <p key={item} className="positive">＋ {item}</p>)}</div><div><h3>反方证据</h3>{dossier.bear_case.map((item) => <p key={item} className="negative">－ {item}</p>)}</div><div><h3>失效条件</h3>{dossier.invalidation.map((item) => <p key={item}>× {item}</p>)}</div><div><h3>仍缺什么</h3>{dossier.missing_evidence.map((item) => <p key={item}>… {item}</p>)}</div></section></div>
    </div>
  </details>;
}

export function StockLabPage() {
  const location = useLocation();
  const [params, setParams] = useSearchParams();
  const [term, setTerm] = useState(params.get("symbol") ?? "600519");
  const [symbol, setSymbol] = useState(params.get("symbol") ?? "SH.600519");
  const [matches, setMatches] = useState<Quote[]>([]);
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
  });
  const evidenceQuery = useQuery({
    queryKey: ["instrument-evidence", symbol],
    queryFn: () => api<InstrumentEvidenceResult>(`/api/v1/instruments/${symbol}/evidence?limit=20`),
    enabled: Boolean(symbol),
  });
  const deepDossierOpen = ["#stock-company-evidence", "#stock-risk-controls", "#stock-score-ledger"].includes(location.hash);

  useEffect(() => {
    if (term.length >= 2) {
      api<Quote[]>(`/api/v1/search?q=${encodeURIComponent(term)}`)
        .then(setMatches)
        .catch(() => setMatches([]));
    }
  }, [term]);

  useEffect(() => {
    if (!query.data) return;
    rememberRecentResearch(query.data.quote);
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
    setMatches([]);
    setParams({ symbol: quote.symbol });
  };

  return <>
    <header className="page-head compact stock-page-head"><div><h1>个股</h1></div></header>
    <div className="stock-control-row">
      <div className="stock-search"><Search size={18} /><input value={term} onChange={(event) => setTerm(event.target.value)} placeholder="输入股票代码或名称" aria-label="搜索股票" />{matches.length > 0 && <div className="search-results">{matches.map((item) => <button key={item.symbol} onClick={() => choose(item)}><b>{item.name}</b><span>{item.symbol}</span></button>)}</div>}</div>
      {fromOpportunity && <section className="stock-source-note compact" aria-label="线索来源"><strong>机会</strong>{sourcePresetLabel && <small>{sourcePresetLabel}</small>}</section>}
      {fromMarketBoard && <section className="stock-source-note compact" aria-label="板块来源"><strong>{sourceBoardName || "板块"}</strong><small>{sourceBoardType}</small></section>}
    </div>
    <AsyncState loading={query.isLoading} error={query.error as Error | null}>{query.data && <>
      <StockFocusBoard dossier={query.data} evidence={evidenceQuery.data} params={params} />
      <StockAskRouter dossier={query.data} params={params} />
      <StockDeepDossier dossier={query.data} evidence={evidenceQuery.data} evidenceLoading={evidenceQuery.isLoading} evidenceFailed={evidenceQuery.isError} open={deepDossierOpen} />
    </>}</AsyncState>
  </>;
}
