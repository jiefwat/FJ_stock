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

type Dossier = {
  quote: Quote;
  stance: string;
  stance_score: number | null;
  evidence_coverage: number;
  score_factors: ScoreFactor[];
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
    setThesis(query.data.bull_case[0] ?? `研究立场：${query.data.stance}`);
    setInvalidation(query.data.invalidation[0] ?? "核心研究逻辑失效");
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
        <div className="stance"><small>研究立场</small><strong>{stanceLabel[query.data.stance] ?? query.data.stance}</strong><span>{query.data.stance_score == null ? "证据不足" : `${query.data.stance_score}/100`}</span><em>证据覆盖 {percent(query.data.evidence_coverage * 100)}</em>{existing ? <Link className="watch-button" to="/watchlist">观察中 · 编辑记录</Link> : <button className="watch-button" onClick={() => setComposerOpen(true)} disabled={composerOpen || addWatch.isSuccess}>{addWatch.isSuccess ? "已加入观察" : "加入观察"}</button>}</div>
      </section>
      {addWatch.isSuccess && <p className="save-confirmation" role="status">已加入观察 · 研究逻辑已经保存</p>}
      {composerOpen && !existing && <form className="watch-composer" onSubmit={(event) => { event.preventDefault(); addWatch.mutate(query.data!); }}>
        <div><span>保存前先写清楚判断</span><small>系统已填入默认证据，你可以直接修改。</small></div>
        <label>研究逻辑<textarea aria-label="研究逻辑" value={thesis} onChange={(event) => setThesis(event.target.value)} required /></label>
        <label>失效条件<textarea aria-label="失效条件" value={invalidation} onChange={(event) => setInvalidation(event.target.value)} required /></label>
        <div className="composer-actions"><button type="button" className="button secondary" onClick={() => setComposerOpen(false)}>取消</button><button className="button" disabled={addWatch.isPending}>{addWatch.isPending ? "保存中…" : "保存到观察列表"}</button></div>
        {addWatch.isError && <p className="form-error">保存失败，研究记录仍保留，请重试。</p>}
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
