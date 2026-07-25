import { useMutation } from "@tanstack/react-query";
import { ArrowUpRight, MessageSquareText, SearchCheck, ShieldAlert } from "lucide-react";
import { type FormEvent, useState } from "react";

import { ApiError, api, type AskStockResponse } from "../../lib/api";

const prompts = [
  "贵州茅台现在主要风险是什么",
  "600519 的技术趋势怎么样",
  "平安银行的估值贵不贵",
  "五粮液的仓位和止损怎么定",
];

const intentLabel: Record<AskStockResponse["intent"], string> = {
  risk: "风险核对",
  trend: "趋势判断",
  valuation: "估值比较",
  action: "操作纪律",
  overview: "综合研究",
  screening: "问财筛选",
};

function observedTime(value: string | null) {
  return value ? new Date(value).toLocaleString("zh-CN", { hour12: false }) : "时间未提供";
}

function EvidenceList({ title, items, tone }: { title: string; items: string[]; tone: string }) {
  if (items.length === 0) return null;
  return <section className={`ask-list ${tone}`}>
    <h3>{title}</h3>
    <ol>{items.map((item) => <li key={item}>{item}</li>)}</ol>
  </section>;
}

function AskResult({ result }: { result: AskStockResponse }) {
  return <section className="ask-result" aria-live="polite">
    <header className="ask-result-head">
      <div>
        <span>{intentLabel[result.intent]}</span>
        <h2>{result.name ?? "自然语言选股"}</h2>
        {result.symbol && <b>{result.symbol}</b>}
      </div>
      <div className="ask-provenance">
        <span>{result.source}</span>
        <small>数据时间 {observedTime(result.observed_at)}</small>
      </div>
    </header>
    <article className="ask-answer">
      <span>回答</span>
      <p>{result.answer}</p>
    </article>
    {result.kind === "semantic_screen" && result.rows.length > 0 && <div className="ask-table-wrap">
      <table className="ask-table">
        <thead><tr>{result.columns.map((column) => <th key={column}>{column}</th>)}</tr></thead>
        <tbody>{result.rows.map((row, index) => <tr key={`${index}-${String(row[result.columns[0]])}`}>
          {result.columns.map((column) => <td key={column}>{String(row[column] ?? "—")}</td>)}
        </tr>)}</tbody>
      </table>
    </div>}
    <div className="ask-evidence-grid">
      <EvidenceList title="判断依据" items={result.evidence} tone="evidence" />
      <EvidenceList title="主要风险" items={result.risks} tone="risk" />
      <EvidenceList title="下一步" items={result.next_actions} tone="action" />
    </div>
    <p className="ask-disclaimer"><ShieldAlert size={14} />{result.disclaimer}</p>
  </section>;
}

export function AskStockPage() {
  const [question, setQuestion] = useState("");
  const ask = useMutation({
    mutationFn: (value: string) => api<AskStockResponse>("/api/v1/ask-stock", {
      method: "POST",
      body: JSON.stringify({ question: value }),
    }),
  });

  const submitQuestion = (value: string) => {
    const normalized = value.trim();
    setQuestion(value);
    if (normalized.length >= 2) ask.mutate(normalized);
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    submitQuestion(question);
  };

  const error = ask.error instanceof ApiError ? ask.error.detail : ask.isError ? "问股请求失败，请稍后重试。" : null;

  return <>
    <header className="page-head ask-page-head">
      <div><p className="eyebrow">ASK STOCK · EVIDENCE FIRST</p><h1>用问题开始研究</h1></div>
      <div className="data-stamp"><MessageSquareText size={14} />本地分析优先 · 问财可选增强</div>
    </header>
    <section className="ask-composer panel">
      <div className="ask-composer-copy">
        <span>一次只研究一只股票</span>
        <p>输入股票名称或六位代码，系统会从当前行情、技术证据、估值和风险纪律中组织回答。</p>
      </div>
      <form onSubmit={submit}>
        <label htmlFor="ask-question">输入你的股票问题</label>
        <div>
          <textarea
            id="ask-question"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            maxLength={160}
            placeholder="例如：贵州茅台现在主要风险是什么"
          />
          <button className="button ask-submit" type="submit" disabled={ask.isPending || question.trim().length < 2}>
            <SearchCheck size={16} />{ask.isPending ? "分析中" : "开始分析"}
          </button>
        </div>
        <small>{question.length}/160 · 回答不会绕过现有确定性分析</small>
      </form>
      <div className="ask-prompts" aria-label="问题示例">
        {prompts.map((prompt) => <button type="button" key={prompt} onClick={() => submitQuestion(prompt)} disabled={ask.isPending}>
          <span>{prompt}</span><ArrowUpRight size={14} />
        </button>)}
      </div>
    </section>
    {error && <p className="ask-error" role="alert">{error}</p>}
    {ask.data && <AskResult result={ask.data} />}
  </>;
}
