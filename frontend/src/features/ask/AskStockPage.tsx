import { useMutation } from "@tanstack/react-query";
import { ArrowUpRight, MessageSquareText, RotateCcw, Send, ShieldAlert, Sparkles } from "lucide-react";
import { type FormEvent, type KeyboardEvent, useEffect, useMemo, useRef, useState } from "react";

import { ApiError, api, getAuthToken, type AskStockResponse } from "../../lib/api";

const prompts = [
  "贵州茅台现在主要风险是什么",
  "600519 的技术趋势怎么样",
  "平安银行的估值贵不贵",
  "我的持仓里风险最大的是哪个",
  "帮我生成调仓计划",
];

const intentLabel: Record<AskStockResponse["intent"], string> = {
  risk: "风险核对",
  trend: "趋势判断",
  valuation: "估值比较",
  action: "操作纪律",
  overview: "综合研究",
  screening: "问财筛选",
  portfolio: "持仓诊断",
};
const storageVersion = 1;
const maxStoredMessages = 24;
const followUpPrompts = [
  { label: "继续问估值", question: "那估值呢" },
  { label: "继续问趋势", question: "趋势呢" },
  { label: "继续问风险", question: "还有哪些风险" },
  { label: "仓位怎么定", question: "仓位和止损怎么定" },
];
const stockCodePattern = /\b(?:SH|SZ|BJ)?\.?\d{6}\b/i;
const followUpPrefixPattern = /^(那|它|这个|这只|该股|刚才|上面|继续|再|顺便)/;
const followUpTopicPattern = /(风险|趋势|估值|仓位|止损|支撑|压力|能买吗|怎么样)/;
const stockCodeColumnPattern = /(股票)?代码|证券代码|symbol/i;

function observedTime(value: string | null) {
  return value ? new Date(value).toLocaleString("zh-CN", { hour12: false }) : "时间未提供";
}

function percentValue(value: number | null | undefined) {
  return value == null ? "—" : `${(value * 100).toFixed(1)}%`;
}

function signedPercentValue(value: number | null | undefined) {
  if (value == null) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
}

function moneyValue(value: number | null | undefined) {
  if (value == null) return "—";
  if (Math.abs(value) >= 100_000_000) return `${(value / 100_000_000).toFixed(1)} 亿`;
  if (Math.abs(value) >= 10_000) return `${(value / 10_000).toFixed(0)} 万`;
  return value.toFixed(0);
}

type StockAnchor = { name: string; symbol: string };
type AskMessage =
  | { id: string; role: "user"; content: string; carriedStock: StockAnchor | null }
  | { id: string; role: "assistant"; result: AskStockResponse }
  | { id: string; role: "error"; content: string; retryValue: string };

function messageId() {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function stockLabel(stock: StockAnchor) {
  return `${stock.name} ${stock.symbol}`;
}

function latestStock(messages: AskMessage[]): StockAnchor | null {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const message = messages[index];
    if (message.role === "assistant" && message.result.kind === "stock_analysis" && message.result.symbol && message.result.name) {
      return { name: message.result.name, symbol: message.result.symbol };
    }
  }
  return null;
}

function shouldCarryStock(question: string, stock: StockAnchor | null) {
  if (!stock) return false;
  if (question.includes(stock.name) || question.includes(stock.symbol) || question.includes(stock.symbol.slice(-6))) return false;
  if (stockCodePattern.test(question)) return false;
  if (followUpPrefixPattern.test(question)) return true;
  return question.length <= 6 && followUpTopicPattern.test(question);
}

function storageKey() {
  const token = getAuthToken();
  return `marketdesk.askStockThread.v${storageVersion}.${token ? token.slice(-16) : "anonymous"}`;
}

function canUseSessionStorage() {
  return typeof sessionStorage !== "undefined" && typeof sessionStorage.getItem === "function";
}

function loadStoredMessages(): AskMessage[] {
  if (!canUseSessionStorage()) return [];
  try {
    const raw = sessionStorage.getItem(storageKey());
    if (!raw) return [];
    const parsed = JSON.parse(raw) as { version?: number; messages?: unknown };
    if (parsed.version !== storageVersion || !Array.isArray(parsed.messages)) return [];
    return parsed.messages.filter((message): message is AskMessage => {
      if (!message || typeof message !== "object") return false;
      const candidate = message as { role?: unknown; content?: unknown; result?: unknown; retryValue?: unknown };
      if (candidate.role === "user") return typeof candidate.content === "string";
      if (candidate.role === "assistant") return typeof candidate.result === "object" && candidate.result !== null;
      if (candidate.role === "error") return typeof candidate.content === "string" && typeof candidate.retryValue === "string";
      return false;
    }).slice(-maxStoredMessages);
  } catch {
    return [];
  }
}

function storeMessages(messages: AskMessage[]) {
  if (!canUseSessionStorage()) return;
  const key = storageKey();
  if (messages.length === 0) {
    sessionStorage.removeItem(key);
    return;
  }
  sessionStorage.setItem(key, JSON.stringify({ version: storageVersion, messages: messages.slice(-maxStoredMessages) }));
}

function symbolFromCode(value: unknown) {
  const raw = String(value ?? "").trim().toUpperCase();
  const prefixed = raw.match(/^(SH|SZ|BJ)\.?\s*(\d{6})$/);
  if (prefixed) return `${prefixed[1]}.${prefixed[2]}`;
  const plain = raw.match(/^\d{6}$/);
  if (!plain) return null;
  if (raw.startsWith("6")) return `SH.${raw}`;
  if (raw.startsWith("0") || raw.startsWith("3")) return `SZ.${raw}`;
  if (raw.startsWith("4") || raw.startsWith("8") || raw.startsWith("9")) return `BJ.${raw}`;
  return null;
}

function renderScreenCell(column: string, value: unknown) {
  const text = String(value ?? "—");
  if (!stockCodeColumnPattern.test(column)) return text;
  const symbol = symbolFromCode(value);
  if (!symbol) return text;
  return <a className="ask-table-link" href={`#/stocks?symbol=${encodeURIComponent(symbol)}`}>{text}</a>;
}

function EvidenceList({ title, items, tone }: { title: string; items: string[]; tone: string }) {
  if (items.length === 0) return null;
  return <section className={`ask-list ${tone}`}>
    <h3>{title}</h3>
    <ol>{items.map((item) => <li key={item}>{item}</li>)}</ol>
  </section>;
}

function AskMetrics({ result }: { result: AskStockResponse }) {
  const metrics = result.metrics ?? [];
  if (metrics.length === 0) return null;
  return <div className="ask-metrics" aria-label="回答关键指标">
    {metrics.map((metric) => <span className={`ask-metric ${metric.tone}`} key={metric.label}>
      <small>{metric.label}</small>
      <b>{metric.value}</b>
    </span>)}
  </div>;
}

function HoldingContext({ result }: { result: AskStockResponse }) {
  const holding = result.holding_context;
  if (!holding?.owned) return null;
  return <aside className="ask-holding-context" aria-label="个人持仓上下文">
    <strong>个人持仓上下文</strong>
    <span>数量 {holding.quantity ?? "—"} 股</span>
    <span>成本 {holding.cost_price?.toFixed(2) ?? "—"}</span>
    <span>市值 {moneyValue(holding.market_value)}</span>
    <span>盈亏 {signedPercentValue(holding.pnl_pct)}</span>
    <span>组合占比 {percentValue(holding.portfolio_weight)}</span>
    <span>动作 {holding.action ?? "—"}</span>
    {holding.risk_flags.length > 0 ? <small>风险：{holding.risk_flags.join(" / ")}</small> : null}
  </aside>;
}

function AskFactors({ result }: { result: AskStockResponse }) {
  const factors = result.factors ?? [];
  if (factors.length === 0) return null;
  return <details className="ask-factors">
    <summary>展开评分因子</summary>
    <div>
      {factors.map((factor) => <article className={`ask-factor ${factor.signal}`} key={`${factor.label}-${factor.evidence}`}>
        <b>{factor.impact > 0 ? `+${factor.impact}` : factor.impact}</b>
        <span>{factor.label}</span>
        <p>{factor.evidence}</p>
      </article>)}
    </div>
  </details>;
}

function AskRowsTable({ result }: { result: AskStockResponse }) {
  if (result.rows.length === 0) return null;
  return <div className="ask-table-wrap">
    <table className="ask-table">
      <thead><tr>{result.columns.map((column) => <th key={column}>{column}</th>)}</tr></thead>
      <tbody>{result.rows.map((row, index) => <tr key={`${index}-${String(row[result.columns[0]])}`}>
        {result.columns.map((column) => <td key={column}>{renderScreenCell(column, row[column])}</td>)}
      </tr>)}</tbody>
    </table>
  </div>;
}

function AskResult({ result }: { result: AskStockResponse }) {
  return <section className="ask-result" aria-live="polite">
    <header className="ask-result-head">
      <div>
        <span>{intentLabel[result.intent]}</span>
        <h2>{result.name ?? (result.kind === "portfolio_analysis" ? "账户组合" : "自然语言选股")}</h2>
        {result.symbol && <b>{result.symbol}</b>}
      </div>
      <div className="ask-provenance">
        <span>{result.source}</span>
        <small>数据时间 {observedTime(result.observed_at)}</small>
        {result.symbol ? <a className="ask-stock-link" href={`#/stocks?symbol=${encodeURIComponent(result.symbol)}`}>打开个股研究</a> : null}
      </div>
    </header>
    <AskMetrics result={result} />
    <HoldingContext result={result} />
    <article className="ask-answer">
      <span>回答</span>
      <p>{result.answer}</p>
    </article>
    <AskRowsTable result={result} />
    <AskFactors result={result} />
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
  const [messages, setMessages] = useState<AskMessage[]>(() => loadStoredMessages());
  const threadEndRef = useRef<HTMLDivElement | null>(null);
  const ask = useMutation({
    mutationFn: (value: string) => api<AskStockResponse>("/api/v1/ask-stock", {
      method: "POST",
      body: JSON.stringify({ question: value }),
    }),
  });
  const activeStock = useMemo(() => latestStock(messages), [messages]);

  useEffect(() => {
    if (typeof threadEndRef.current?.scrollIntoView === "function") {
      threadEndRef.current.scrollIntoView({ block: "end" });
    }
  }, [messages, ask.isPending]);

  useEffect(() => {
    storeMessages(messages);
  }, [messages]);

  const submitQuestion = async (value: string) => {
    const normalized = value.trim();
    if (normalized.length < 2 || ask.isPending) return;

    const carriedStock = shouldCarryStock(normalized, activeStock) ? activeStock : null;
    const requestQuestion = carriedStock ? `${carriedStock.name} ${normalized}` : normalized;
    setMessages((current) => [...current, { id: messageId(), role: "user", content: normalized, carriedStock }]);
    setQuestion("");

    try {
      const result = await ask.mutateAsync(requestQuestion);
      setMessages((current) => [...current, { id: messageId(), role: "assistant", result }]);
    } catch (error) {
      const detail = error instanceof ApiError ? error.detail : "问股请求失败，请稍后重试。";
      setMessages((current) => [...current, { id: messageId(), role: "error", content: detail, retryValue: requestQuestion }]);
      setQuestion(value);
    }
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    void submitQuestion(question);
  };

  const handleComposerKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key !== "Enter" || event.shiftKey) return;
    event.preventDefault();
    void submitQuestion(question);
  };

  const clearThread = () => {
    setMessages([]);
    setQuestion("");
  };

  return <>
    <header className="page-head ask-page-head">
      <div><p className="eyebrow">ASK STOCK · CONVERSATION</p><h1>问股对话</h1></div>
      <div className="data-stamp"><MessageSquareText size={14} />本地分析优先 · 可连续追问</div>
    </header>
    <section className="ask-chat-layout">
      <aside className="ask-context panel">
        <div>
          <span><Sparkles size={15} />对话上下文</span>
          <p>{activeStock ? `正在围绕 ${stockLabel(activeStock)} 追问` : "先问一只股票，或直接问“我的持仓里风险最大的是哪个”。"}</p>
        </div>
        <div className="ask-prompts" aria-label="问题示例">
          {prompts.map((prompt) => <button type="button" key={prompt} onClick={() => void submitQuestion(prompt)} disabled={ask.isPending}>
            <span>{prompt}</span><ArrowUpRight size={14} />
          </button>)}
        </div>
        <button className="ask-reset" type="button" onClick={clearThread} disabled={messages.length === 0 || ask.isPending}>
          <RotateCcw size={14} />清空对话
        </button>
      </aside>
      <div className="ask-chat-main">
        <section className="ask-thread panel" aria-label="问股对话记录">
          {messages.length === 0 ? <div className="ask-thread-empty">
            <MessageSquareText size={28} />
            <strong>从一个股票问题开始</strong>
            <p>后续可以直接问“那估值呢”“风险呢”“仓位怎么定”，也可以问“我的持仓里风险最大的是哪个”。</p>
          </div> : messages.map((message) => {
            if (message.role === "user") {
              return <article className="ask-message user" key={message.id}>
                <div><span>你</span><p>{message.content}</p>{message.carriedStock ? <small>沿用上文：{stockLabel(message.carriedStock)}</small> : null}</div>
              </article>;
            }
            if (message.role === "error") {
              return <article className="ask-message error" key={message.id} role="alert">
                <span>{message.content}</span>
                <button type="button" onClick={() => void submitQuestion(message.retryValue)} disabled={ask.isPending}>重试</button>
              </article>;
            }
            return <article className="ask-message assistant" key={message.id}>
              <span>Market Desk</span>
              <AskResult result={message.result} />
              {message.result.kind === "stock_analysis" ? <div className="ask-followups" aria-label="追问建议">
                {followUpPrompts.map((prompt) => <button type="button" key={prompt.label} onClick={() => void submitQuestion(prompt.question)} disabled={ask.isPending}>{prompt.label}</button>)}
              </div> : null}
            </article>;
          })}
          {ask.isPending ? <article className="ask-message assistant pending"><span>Market Desk</span><p>正在整理行情证据...</p></article> : null}
          <div ref={threadEndRef} />
        </section>
        <form className="ask-chat-composer panel" onSubmit={submit}>
          <label htmlFor="ask-question">继续追问</label>
          <div>
            <textarea
              id="ask-question"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              onKeyDown={handleComposerKeyDown}
              maxLength={160}
              placeholder={activeStock ? `继续问 ${activeStock.name}：例如 那估值呢` : "例如：贵州茅台现在主要风险是什么"}
            />
            <button className="button ask-submit" type="submit" disabled={ask.isPending || question.trim().length < 2}>
              <Send size={16} />{ask.isPending ? "分析中" : "发送"}
            </button>
          </div>
          <small>{question.length}/160 · {activeStock ? `上文股票 ${stockLabel(activeStock)}` : "支持单股研究、账户持仓诊断；宽泛选股会走可选问财增强"}</small>
        </form>
      </div>
    </section>
  </>;
}
