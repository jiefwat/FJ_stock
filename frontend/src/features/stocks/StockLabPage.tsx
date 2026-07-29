import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useLocation, useSearchParams } from "react-router-dom";

import { AsyncState } from "../../components/AsyncState";
import { rememberRecentResearch } from "../../lib/recentResearch";
import { api, fmt, getAuthToken, pct, percent, type EvidenceDocument, type InstrumentEvidenceResult, type Quote, type WatchlistItem } from "../../lib/api";
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

function sectionHref(location: ReturnType<typeof useLocation>, anchor: string) {
  return `${location.pathname}${location.search}#${anchor}`;
}

function ConclusionBrief({ dossier }: { dossier: Dossier }) {
  const brief = splitConclusion(dossier.conclusion);
  const visibleSections = brief.sections.filter((item) => !dedicatedConclusionLabels.has(item.label));
  const evidenceSections = visibleSections.filter((item) => evidenceConclusionLabels.has(item.label));
  const actionSections = visibleSections.filter((item) => !evidenceConclusionLabels.has(item.label));

  return <section className="panel stock-conclusion" aria-label="结构化总结论">
    <div className="panel-title"><span>总结论</span><small>由下方证据账本自动生成</small></div>
    <div className="conclusion-brief">
      <article className="conclusion-verdict">
        <span>当前判断</span>
        <strong>{stanceLabel[dossier.stance] ?? dossier.stance}</strong>
        <b>{dossier.stance_score == null ? "证据不足" : `${dossier.stance_score}/100`}</b>
        <em>不是买卖指令，只用于复盘研究</em>
      </article>
      <article className="conclusion-summary">
        <span>怎么读</span>
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
    { label: "再看风险", value: firstOrFallback(dossier.bear_case, "暂未识别主要反方证据，但仍需跟踪波动"), tone: "negative" },
    { label: "证据缺口", value: firstOrFallback(dossier.missing_evidence, "没有明显缺口，继续按当前证据复盘"), tone: "neutral" },
    { label: "下一步动作", value: firstOrFallback(dossier.next_actions, firstOrFallback(dossier.invalidation, "先设定复核节奏，再决定是否跟踪")), tone: "action" },
  ];

  return <section className="analyst-action-map" aria-label="个股分析路径">
    <div className="map-title">
      <span>研究路径</span>
      <strong>先定逻辑，再看证据，最后定动作</strong>
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
        <article><span>止盈复核</span><p>{advice.take_profit}</p></article>
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
  const verdict = upgraded ? "线索已升级为可试错" : watchOnly ? "线索仅保留观察" : "线索未升级为参与";
  const tone = upgraded ? "positive" : watchOnly ? "caution" : "negative";
  const reason = advice.rationale[0] ?? advice.position_hint;

  return <section className={`opportunity-review-outcome ${tone}`} aria-label="线索复核结果">
    <div>
      <span>线索复核结果</span>
      <strong>{verdict}</strong>
      <p>机会页只说明它值得进入短名单；当前直接建议是 <b>{advice.action}</b>。</p>
    </div>
    <ol>
      <li>{advice.position_hint}</li>
      <li>{reason}</li>
      <li>若证据账本继续转弱，以失效条件为准，不因为曾入选线索而参与。</li>
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
    return { tone: "caution", text: "先补证据，不升级仓位", detail: "覆盖或外部来源仍有缺口，先确认公告、研报和板块温度。" };
  }
  if (riskCount > supportCount) {
    return { tone: "negative", text: "反方证据占优，先守失效线", detail: "风险证据多于支持证据，复核重点放在止损和放弃条件。" };
  }
  return { tone: "positive", text: "证据够用，进入交易计划复核", detail: "支持证据占优，但最终仍要按入场、止损、止盈纪律执行。" };
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
  const gaps = dossier.missing_evidence.length > 0 ? dossier.missing_evidence : [gapCount > 0 ? "部分外部证据源未完全可用" : "暂无关键缺口，继续滚动复核"];

  return <section className={`evidence-audit-desk ${route.tone}`} id="stock-evidence-audit" aria-label="证据总账">
    <article className="audit-verdict">
      <span>LEDGER GATE</span>
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
        <span>下一步复核</span>
        <strong>{dossier.investment_advice.action}</strong>
        {(dossier.next_actions.length ? dossier.next_actions : [dossier.investment_advice.entry_plan]).slice(0, 2).map((item) => <p key={item}>→ {item}</p>)}
      </article>
    </div>
  </section>;
}

function StockReviewRail({ dossier, evidence, location }: { dossier: Dossier; evidence?: InstrumentEvidenceResult; location: ReturnType<typeof useLocation> }) {
  const route = evidenceRoute(dossier, evidence);
  const docsCount = (evidence?.filings.length ?? 0) + (evidence?.research.length ?? 0);
  const items = [
    {
      code: "01",
      label: "FINAL GATE",
      value: dossier.investment_advice.action,
      detail: "先判断是否值得继续复核",
      anchor: "stock-final-gate",
    },
    {
      code: "02",
      label: "LEDGER GATE",
      value: route.text,
      detail: `覆盖 ${percent(dossier.evidence_coverage * 100)}，先看支持/反方/缺口`,
      anchor: "stock-evidence-audit",
    },
    {
      code: "03",
      label: "交易计划",
      value: dossier.investment_advice.entry_plan,
      detail: "把动作落到入场、止损、止盈",
      anchor: "stock-investment-advice",
    },
    {
      code: "04",
      label: "公告研报",
      value: docsCount > 0 ? `${docsCount} 条外部证据` : "外部证据待补",
      detail: "只作上下文，不改写确定性评分",
      anchor: "stock-company-evidence",
    },
    {
      code: "05",
      label: "风控条件",
      value: firstOrFallback(dossier.invalidation, dossier.investment_advice.stop_loss),
      detail: "最后确认放弃线和反方证据",
      anchor: "stock-risk-controls",
    },
  ];

  return <section className="stock-review-rail" aria-label="个股复核路线">
    <div>
      <span>REVIEW ROUTE</span>
      <strong>按这条顺序读</strong>
      <p>先过闸口，再看证据，最后落到交易纪律。</p>
    </div>
    <nav aria-label="个股复核区块导航">
      {items.map((item) => <Link key={item.anchor} to={sectionHref(location, item.anchor)}>
        <b>{item.code}</b>
        <span>{item.label}</span>
        <strong>{item.value}</strong>
        <small>{item.detail}</small>
      </Link>)}
    </nav>
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

function StockDecisionDeck({ dossier, evidence }: { dossier: Dossier; evidence?: InstrumentEvidenceResult }) {
  const firstTheme = evidence?.themes[0];
  const sectorName = dossier.quote.sector ?? firstTheme?.name ?? "板块待确认";
  const sectorLink = firstTheme ? themeHref(firstTheme) : dossier.quote.sector ? `/market?industry=${encodeURIComponent(dossier.quote.sector)}` : "/market";
  const tone = actionTone(dossier.investment_advice.action);
  const invalidation = firstOrFallback(dossier.invalidation, dossier.investment_advice.stop_loss);
  const nextAction = firstOrFallback(dossier.next_actions, dossier.investment_advice.entry_plan);
  const missing = firstOrFallback(dossier.missing_evidence, "暂无关键缺口，继续按证据账本复核");

  return <section className={`stock-decision-deck ${tone}`} id="stock-final-gate" aria-label="个股复核作战台">
    <article className="decision-primary">
      <span>FINAL GATE</span>
      <strong>{dossier.investment_advice.action}</strong>
      <p>{dossier.investment_advice.position_hint}</p>
      <small>置信度 {percent(dossier.investment_advice.confidence * 100)} · 证据覆盖 {percent(dossier.evidence_coverage * 100)}</small>
    </article>
    <div className="decision-cards">
      <article>
        <span>先看板块</span>
        <strong>{sectorName}</strong>
        <p>个股动作必须和板块温度、资金扩散一起确认。</p>
        <Link to={sectorLink}>打开板块/题材</Link>
      </article>
      <article>
        <span>失效条件</span>
        <strong>{invalidation}</strong>
        <p>跌破或证据恶化时，先退出复核，不用新理由补旧逻辑。</p>
      </article>
      <article>
        <span>下一步</span>
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
      intent: "RISK",
      detail: "只问失效条件、利空和必须放弃的场景。",
      question: `${name}现在主要风险是什么`,
    },
    {
      label: "问异动",
      intent: "MOVE",
      detail: "先量化 1/5/20 日涨跌，再解释量能和结构。",
      question: `最近${name}怎么大跌`,
    },
    {
      label: "问基本面",
      intent: "QUALITY",
      detail: "把财报、现金流、估值和公告缺口分开说。",
      question: `${name}基本面怎么样`,
    },
    {
      label: "问催化",
      intent: "CATALYST",
      detail: "只看已验证公告、研报、题材和龙虎榜线索。",
      question: `${name}有什么公告催化`,
    },
  ];

  return <section className="stock-ask-router" aria-label="个股问股快捷入口">
    <div>
      <span>ASK NEXT</span>
      <strong>把这份证据，继续问成结论</strong>
      <p>不用复制股票名；每个入口都会带上当前股票和来源上下文。</p>
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
    <div className="panel-title"><span>公告 / 研报 / 题材</span><small>有出处的外部证据 · 不进入确定性评分</small></div>
    <p className="evidence-boundary">公告、机构观点和题材归属仅作研究上下文，不直接改写评分；点击标题回到原始来源核验。</p>
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
      <span>完整证据包</span>
      <strong>展开技术图、公告研报、分析拆解和原始账本</strong>
      <small>核心结论已经在上方；这里保留可追溯细节。</small>
    </summary>
    <div className="stock-deep-stack">
      <SignalValidationPanel validation={dossier.signal_validation} />
      <ComparisonSection horizontal={dossier.horizontal_comparison} vertical={dossier.vertical_comparison} />
      <AnalystActionMap dossier={dossier} />
      <ConclusionBrief dossier={dossier} />
      <CompanyEvidencePanel data={evidence} loading={evidenceLoading} failed={evidenceFailed} />
      {dossier.analysis_dimensions.length > 0 && <section className="panel analysis-breakdown">
        <div className="panel-title"><span>分析拆解</span><small>趋势、风险收益、估值、流动性、资金和行业一起看</small></div>
        <div className="dimension-grid">{dossier.analysis_dimensions.map((item) => <article key={item.key} className={item.signal}>
          <header><span>{item.label}</span><strong>{item.score == null ? "缺数据" : `${fmt(item.score, 0)}/100`}</strong></header>
          <p>{item.summary}</p>
          <ul>{item.evidence.map((evidence) => <li key={evidence}>{evidence}</li>)}</ul>
        </article>)}</div>
      </section>}
      {dossier.next_actions.length > 0 && <section className="panel next-actions-panel">
        <div className="panel-title"><span>下一步看什么</span><small>把结论变成可复盘动作</small></div>
        <ol>{dossier.next_actions.map((item) => <li key={item}>{item}</li>)}</ol>
      </section>}
      <StockTrend bars={dossier.bars} />
      <section className="panel evidence-ledger" id="stock-score-ledger">
        <div className="panel-title"><span>证据账本</span><small>所有加减分都来自下列事实</small></div>
        <div className="ledger-list">{dossier.score_factors.map((factor) => <article key={factor.key} className={factor.signal}><span>{factor.label}</span><p>{factor.evidence}</p><strong>{factor.available ? `${factor.impact > 0 ? "+" : ""}${factor.impact}` : "未计入"}</strong></article>)}</div>
      </section>
      {dossier.research_evidence.length > 0 && <section className="panel research-evidence"><div className="panel-title"><span>语义研究增强</span><small>只作为证据补充，不直接改写评分</small></div>{dossier.research_evidence.map((item) => <p key={item}>＋ {item}</p>)}</section>}
      <div className="evidence-grid"><section className="panel"><div className="panel-title"><span>技术结构</span></div><div className="metric-grid">{dossier.technical ? Object.entries(dossier.technical).map(([key, value]) => <div key={key}><span>{key.toUpperCase()}</span><strong>{fmt(value)}</strong></div>) : <div className="empty">历史行情不足，不能生成技术判断。</div>}</div></section><section className="panel thesis" id="stock-risk-controls"><div><h3>支持证据</h3>{dossier.bull_case.map((item) => <p key={item} className="positive">＋ {item}</p>)}</div><div><h3>反方证据</h3>{dossier.bear_case.map((item) => <p key={item} className="negative">－ {item}</p>)}</div><div><h3>失效条件</h3>{dossier.invalidation.map((item) => <p key={item}>× {item}</p>)}</div><div><h3>仍缺什么</h3>{dossier.missing_evidence.map((item) => <p key={item}>… {item}</p>)}</div></section></div>
    </div>
  </details>;
}

export function StockLabPage() {
  const client = useQueryClient();
  const authenticated = Boolean(getAuthToken());
  const location = useLocation();
  const [params, setParams] = useSearchParams();
  const [term, setTerm] = useState(params.get("symbol") ?? "600519");
  const [symbol, setSymbol] = useState(params.get("symbol") ?? "SH.600519");
  const [matches, setMatches] = useState<Quote[]>([]);
  const [composerOpen, setComposerOpen] = useState(false);
  const fromOpportunity = params.get("from") === "opportunities";
  const fromMarketBoard = params.get("from") === "market";
  const sourcePreset = params.get("preset") ?? "";
  const sourcePresetLabel = sourcePresetLabels[sourcePreset];
  const sourceBoardName = params.get("boardName") ?? "";
  const sourceBoardType = params.get("boardType") ?? "板块";
  const [thesis, setThesis] = useState("");
  const [invalidation, setInvalidation] = useState("");

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
  const watchlist = useQuery({
    queryKey: ["watchlist"],
    queryFn: () => api<WatchlistItem[]>("/api/v1/watchlist"),
    enabled: authenticated,
  });
  const existing = watchlist.data?.find((item) => item.symbol === symbol);
  const deepDossierOpen = ["#stock-company-evidence", "#stock-risk-controls", "#stock-score-ledger"].includes(location.hash);
  const addWatch = useMutation({
    mutationFn: (dossier: Dossier) => api<WatchlistItem>("/api/v1/watchlist", {
      method: "POST",
      body: JSON.stringify({
        symbol: dossier.quote.symbol,
        name: dossier.quote.name,
        thesis,
        invalidation,
      }),
    }),
    onSuccess: () => {
      setComposerOpen(false);
      client.invalidateQueries({ queryKey: ["watchlist"] });
    },
  });

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
    setThesis(query.data.bull_case[0] ?? `关注理由：${query.data.stance}`);
    setInvalidation(query.data.invalidation[0] ?? "关注理由不成立");
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
    setComposerOpen(false);
    addWatch.reset();
  };

  return <>
    <header className="page-head compact"><div><p className="eyebrow">STOCK LAB / 个股研究</p><h1>一只股票，<em>一条证据链。</em></h1></div></header>
    <div className="stock-search"><Search size={18} /><input value={term} onChange={(event) => setTerm(event.target.value)} placeholder="输入股票代码或名称" aria-label="搜索股票" />{matches.length > 0 && <div className="search-results">{matches.map((item) => <button key={item.symbol} onClick={() => choose(item)}><b>{item.name}</b><span>{item.symbol}</span></button>)}</div>}</div>
    {fromOpportunity && <section className="stock-source-note" aria-label="线索复核说明"><strong>来自机会选股的研究线索</strong><span>线索页只负责短名单排序；此页的直接建议和证据账本才用于判断是否参与。</span>{sourcePresetLabel && <small>来源策略：{sourcePresetLabel}</small>}</section>}
      {fromMarketBoard && <section className="stock-source-note" aria-label="板块复核说明"><strong>来自{sourceBoardName || "板块"}{sourceBoardType}复核</strong><span>板块页只说明它是前排样本；此页继续用 FINAL GATE 和证据总账判断是否值得跟踪。</span>{sourceBoardName && <small>来源：{sourceBoardName}{sourceBoardType}</small>}</section>}
    <AsyncState loading={query.isLoading} error={query.error as Error | null}>{query.data && <>
      <section className="stock-hero">
        <div><span>{query.data.quote.symbol} · {query.data.quote.sector ?? "行业待补"}</span><h2>{query.data.quote.name}</h2><p>{fmt(query.data.quote.price)} <b className={(query.data.quote.change_pct ?? 0) >= 0 ? "up" : "down"}>{pct(query.data.quote.change_pct)}</b></p></div>
        <div className="stance"><small>研究立场</small><strong>{stanceLabel[query.data.stance] ?? query.data.stance}</strong><span>{query.data.stance_score == null ? "证据不足" : `${query.data.stance_score}/100`}</span><em>证据覆盖 {percent(query.data.evidence_coverage * 100)}</em>{existing ? <Link className="watch-button" to="/watchlist">已跟踪 · 编辑记录</Link> : authenticated ? <button className="watch-button" onClick={() => setComposerOpen(true)} disabled={composerOpen || addWatch.isSuccess}>{addWatch.isSuccess ? "已加入跟踪" : "加入跟踪"}</button> : <button className="watch-button" disabled>登录后加入跟踪</button>}<Link className="watch-button ask-stock-entry" to={askHref(query.data, params)}>带着证据去问股</Link></div>
      </section>
      {fromOpportunity && <OpportunityReviewOutcome advice={query.data.investment_advice} />}
      <StockReviewRail dossier={query.data} evidence={evidenceQuery.data} location={location} />
      <StockDecisionDeck dossier={query.data} evidence={evidenceQuery.data} />
      <StockAskRouter dossier={query.data} params={params} />
      <EvidenceAuditDesk dossier={query.data} evidence={evidenceQuery.data} />
      <InvestmentAdvicePanel advice={query.data.investment_advice} />
      <TrendForecastPanel forecast={query.data.trend_forecast} />
      <StockDeepDossier dossier={query.data} evidence={evidenceQuery.data} evidenceLoading={evidenceQuery.isLoading} evidenceFailed={evidenceQuery.isError} open={deepDossierOpen} />
      {addWatch.isSuccess && <p className="save-confirmation" role="status">已加入跟踪 · 关注理由已经保存</p>}
      {composerOpen && !existing && <form className="watch-composer" onSubmit={(event) => { event.preventDefault(); addWatch.mutate(query.data!); }}>
        <div><span>先说清楚为什么要盯它</span><small>跟踪不是买入，只是把“值得继续看”的理由记下来。</small></div>
        <label>关注理由<textarea aria-label="关注理由" value={thesis} onChange={(event) => setThesis(event.target.value)} required /></label>
        <label>放弃条件<textarea aria-label="放弃条件" value={invalidation} onChange={(event) => setInvalidation(event.target.value)} required /></label>
        <div className="composer-actions"><button type="button" className="button secondary" onClick={() => setComposerOpen(false)}>取消</button><button className="button" disabled={addWatch.isPending}>{addWatch.isPending ? "保存中…" : "保存到跟踪清单"}</button></div>
        {addWatch.isError && <p className="form-error">保存失败，跟踪理由仍保留，请重试。</p>}
      </form>}
    </>}</AsyncState>
  </>;
}
