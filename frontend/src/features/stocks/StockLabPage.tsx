import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { AsyncState } from "../../components/AsyncState";
import { api, fmt, pct, percent, type Quote, type WatchlistItem } from "../../lib/api";
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
  return <section className="investment-advice-panel" aria-label="直接投资建议">
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
      {advice.rationale.length > 0 && <ul>{advice.rationale.map((item) => <li key={item}>{item}</li>)}</ul>}
      <small>{advice.disclaimer}</small>
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

export function StockLabPage() {
  const client = useQueryClient();
  const [params, setParams] = useSearchParams();
  const [term, setTerm] = useState(params.get("symbol") ?? "600519");
  const [symbol, setSymbol] = useState(params.get("symbol") ?? "SH.600519");
  const [matches, setMatches] = useState<Quote[]>([]);
  const [composerOpen, setComposerOpen] = useState(false);
  const [thesis, setThesis] = useState("");
  const [invalidation, setInvalidation] = useState("");

  const query = useQuery({
    queryKey: ["stock", symbol],
    queryFn: () => api<Dossier>(`/api/v1/stocks/${symbol}`),
    enabled: Boolean(symbol),
  });
  const watchlist = useQuery({
    queryKey: ["watchlist"],
    queryFn: () => api<WatchlistItem[]>("/api/v1/watchlist"),
  });
  const existing = watchlist.data?.find((item) => item.symbol === symbol);
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
    setThesis(query.data.bull_case[0] ?? `关注理由：${query.data.stance}`);
    setInvalidation(query.data.invalidation[0] ?? "关注理由不成立");
  }, [query.data]);

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
    <AsyncState loading={query.isLoading} error={query.error as Error | null}>{query.data && <>
      <section className="stock-hero">
        <div><span>{query.data.quote.symbol} · {query.data.quote.sector ?? "行业待补"}</span><h2>{query.data.quote.name}</h2><p>{fmt(query.data.quote.price)} <b className={(query.data.quote.change_pct ?? 0) >= 0 ? "up" : "down"}>{pct(query.data.quote.change_pct)}</b></p></div>
        <div className="stance"><small>研究立场</small><strong>{stanceLabel[query.data.stance] ?? query.data.stance}</strong><span>{query.data.stance_score == null ? "证据不足" : `${query.data.stance_score}/100`}</span><em>证据覆盖 {percent(query.data.evidence_coverage * 100)}</em>{existing ? <Link className="watch-button" to="/watchlist">已跟踪 · 编辑记录</Link> : <button className="watch-button" onClick={() => setComposerOpen(true)} disabled={composerOpen || addWatch.isSuccess}>{addWatch.isSuccess ? "已加入跟踪" : "加入跟踪"}</button>}</div>
      </section>
      <InvestmentAdvicePanel advice={query.data.investment_advice} />
      <TrendForecastPanel forecast={query.data.trend_forecast} />
      <ComparisonSection horizontal={query.data.horizontal_comparison} vertical={query.data.vertical_comparison} />
      <AnalystActionMap dossier={query.data} />
      <ConclusionBrief dossier={query.data} />
      {query.data.analysis_dimensions.length > 0 && <section className="panel analysis-breakdown">
        <div className="panel-title"><span>分析拆解</span><small>趋势、风险收益、估值、流动性、资金和行业一起看</small></div>
        <div className="dimension-grid">{query.data.analysis_dimensions.map((item) => <article key={item.key} className={item.signal}>
          <header><span>{item.label}</span><strong>{item.score == null ? "缺数据" : `${fmt(item.score, 0)}/100`}</strong></header>
          <p>{item.summary}</p>
          <ul>{item.evidence.map((evidence) => <li key={evidence}>{evidence}</li>)}</ul>
        </article>)}</div>
      </section>}
      {query.data.next_actions.length > 0 && <section className="panel next-actions-panel">
        <div className="panel-title"><span>下一步看什么</span><small>把结论变成可复盘动作</small></div>
        <ol>{query.data.next_actions.map((item) => <li key={item}>{item}</li>)}</ol>
      </section>}
      {addWatch.isSuccess && <p className="save-confirmation" role="status">已加入跟踪 · 关注理由已经保存</p>}
      {composerOpen && !existing && <form className="watch-composer" onSubmit={(event) => { event.preventDefault(); addWatch.mutate(query.data!); }}>
        <div><span>先说清楚为什么要盯它</span><small>跟踪不是买入，只是把“值得继续看”的理由记下来。</small></div>
        <label>关注理由<textarea aria-label="关注理由" value={thesis} onChange={(event) => setThesis(event.target.value)} required /></label>
        <label>放弃条件<textarea aria-label="放弃条件" value={invalidation} onChange={(event) => setInvalidation(event.target.value)} required /></label>
        <div className="composer-actions"><button type="button" className="button secondary" onClick={() => setComposerOpen(false)}>取消</button><button className="button" disabled={addWatch.isPending}>{addWatch.isPending ? "保存中…" : "保存到跟踪清单"}</button></div>
        {addWatch.isError && <p className="form-error">保存失败，跟踪理由仍保留，请重试。</p>}
      </form>}
      <StockTrend bars={query.data.bars} />
      <section className="panel evidence-ledger">
        <div className="panel-title"><span>证据账本</span><small>所有加减分都来自下列事实</small></div>
        <div className="ledger-list">{query.data.score_factors.map((factor) => <article key={factor.key} className={factor.signal}><span>{factor.label}</span><p>{factor.evidence}</p><strong>{factor.available ? `${factor.impact > 0 ? "+" : ""}${factor.impact}` : "未计入"}</strong></article>)}</div>
      </section>
      {query.data.research_evidence.length > 0 && <section className="panel research-evidence"><div className="panel-title"><span>语义研究增强</span><small>只作为证据补充，不直接改写评分</small></div>{query.data.research_evidence.map((item) => <p key={item}>＋ {item}</p>)}</section>}
      <div className="evidence-grid"><section className="panel"><div className="panel-title"><span>技术结构</span></div><div className="metric-grid">{query.data.technical ? Object.entries(query.data.technical).map(([key, value]) => <div key={key}><span>{key.toUpperCase()}</span><strong>{fmt(value)}</strong></div>) : <div className="empty">历史行情不足，不能生成技术判断。</div>}</div></section><section className="panel thesis"><div><h3>支持证据</h3>{query.data.bull_case.map((item) => <p key={item} className="positive">＋ {item}</p>)}</div><div><h3>反方证据</h3>{query.data.bear_case.map((item) => <p key={item} className="negative">－ {item}</p>)}</div><div><h3>失效条件</h3>{query.data.invalidation.map((item) => <p key={item}>× {item}</p>)}</div><div><h3>仍缺什么</h3>{query.data.missing_evidence.map((item) => <p key={item}>… {item}</p>)}</div></section></div>
    </>}</AsyncState>
  </>;
}
