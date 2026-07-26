import { useMutation } from "@tanstack/react-query";
import { ArrowUpRight, History, MessageSquareText, Plus, RotateCcw, Send, ShieldAlert, Sparkles } from "lucide-react";
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
  screening: "条件选股",
  portfolio: "持仓诊断",
};
const storageVersion = 1;
const maxStoredMessages = 24;
const maxStoredThreads = 12;
const followUpPrompts = [
  { label: "继续问估值", question: "那估值呢" },
  { label: "继续问趋势", question: "趋势呢" },
  { label: "继续问风险", question: "还有哪些风险" },
  { label: "仓位怎么定", question: "仓位和止损怎么定" },
];
const stockCodePattern = /\b(?:SH|SZ|BJ)?\.?\d{6}\b/i;
const followUpPrefixPattern = /^(那|它|这个|这只|该股|刚才|上面|继续|再|顺便)/;
const followUpTopicPattern = /(风险|趋势|估值|仓位|止损|止盈|支撑|压力|目标价|价格|股价|合理|多少|能买吗|能不能|要不要|可以买|可以卖|怎么样|怎么看)/;
const portfolioQuestionPattern = /(我的持仓|持仓里|持仓中|组合|账户|调仓|再平衡|仓位调整)/;
const screeningQuestionPattern = /(低估值|高股息|龙头|行业|板块|概念|题材|筛选|选股|有哪些|哪些|推荐|找|寻找|排名|排行)/;
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
type AskThread = { id: string; title: string; updatedAt: number; messages: AskMessage[] };
type AskThreadState = { activeThreadId: string; threads: AskThread[] };

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
  if (portfolioQuestionPattern.test(question)) return false;
  if (screeningQuestionPattern.test(question)) return false;
  if (followUpPrefixPattern.test(question)) return true;
  return question.length <= 16 && followUpTopicPattern.test(question);
}

function legacyStorageKey() {
  const token = getAuthToken();
  return `marketdesk.askStockThread.v${storageVersion}.${token ? token.slice(-16) : "anonymous"}`;
}

function threadStorageKey() {
  const token = getAuthToken();
  return `marketdesk.askStockThreads.v${storageVersion}.${token ? token.slice(-16) : "anonymous"}`;
}

function canUseSessionStorage() {
  return typeof sessionStorage !== "undefined" && typeof sessionStorage.getItem === "function";
}

function canUseLocalStorage() {
  return typeof localStorage !== "undefined" && typeof localStorage.getItem === "function";
}

function sanitizeMessages(messages: unknown): AskMessage[] {
  if (!Array.isArray(messages)) return [];
  return messages.filter((message): message is AskMessage => {
    if (!message || typeof message !== "object") return false;
    const candidate = message as { role?: unknown; content?: unknown; result?: unknown; retryValue?: unknown };
    if (candidate.role === "user") return typeof candidate.content === "string";
    if (candidate.role === "assistant") return typeof candidate.result === "object" && candidate.result !== null;
    if (candidate.role === "error") return typeof candidate.content === "string" && typeof candidate.retryValue === "string";
    return false;
  }).slice(-maxStoredMessages);
}

function threadTitle(messages: AskMessage[]) {
  const firstUser = messages.find((message) => message.role === "user");
  if (!firstUser || firstUser.role !== "user") return "新对话";
  return firstUser.content.length > 18 ? `${firstUser.content.slice(0, 18)}…` : firstUser.content;
}

function threadMeta(thread: AskThread) {
  const stock = latestStock(thread.messages);
  if (stock) return stockLabel(stock);
  const turns = thread.messages.filter((message) => message.role === "assistant").length;
  return turns > 0 ? `${turns} 条回答` : "未开始";
}

function createThread(messages: AskMessage[] = []): AskThread {
  return {
    id: messageId(),
    title: threadTitle(messages),
    updatedAt: Date.now(),
    messages,
  };
}

function loadLegacyMessages(): AskMessage[] {
  if (!canUseSessionStorage()) return [];
  try {
    const raw = sessionStorage.getItem(legacyStorageKey());
    if (!raw) return [];
    const parsed = JSON.parse(raw) as { version?: number; messages?: unknown };
    if (parsed.version !== storageVersion) return [];
    return sanitizeMessages(parsed.messages);
  } catch {
    return [];
  }
}

function loadThreadState(): AskThreadState {
  if (canUseLocalStorage()) {
    try {
      const raw = localStorage.getItem(threadStorageKey());
      if (raw) {
        const parsed = JSON.parse(raw) as { version?: number; activeThreadId?: unknown; threads?: unknown };
        const threads = Array.isArray(parsed.threads)
          ? parsed.threads.map((item): AskThread | null => {
            if (!item || typeof item !== "object") return null;
            const candidate = item as { id?: unknown; title?: unknown; updatedAt?: unknown; messages?: unknown };
            if (typeof candidate.id !== "string") return null;
            const messages = sanitizeMessages(candidate.messages);
            return {
              id: candidate.id,
              title: typeof candidate.title === "string" && candidate.title.trim() ? candidate.title : threadTitle(messages),
              updatedAt: typeof candidate.updatedAt === "number" ? candidate.updatedAt : Date.now(),
              messages,
            };
          }).filter((item): item is AskThread => item !== null)
          : [];
        if (parsed.version === storageVersion && threads.length > 0) {
          const activeThreadId = typeof parsed.activeThreadId === "string" && threads.some((thread) => thread.id === parsed.activeThreadId)
            ? parsed.activeThreadId
            : threads[0].id;
          return { activeThreadId, threads };
        }
      }
    } catch {
      // Ignore malformed local history and fall back to a fresh conversation.
    }
  }

  const migrated = loadLegacyMessages();
  const thread = createThread(migrated);
  return { activeThreadId: thread.id, threads: [thread] };
}

function storeThreadState(state: AskThreadState) {
  if (!canUseLocalStorage()) return;
  const threads = state.threads
    .filter((thread) => thread.messages.length > 0 || thread.id === state.activeThreadId)
    .sort((left, right) => right.updatedAt - left.updatedAt)
    .slice(0, maxStoredThreads);
  localStorage.setItem(threadStorageKey(), JSON.stringify({
    version: storageVersion,
    activeThreadId: state.activeThreadId,
    threads,
  }));
}

function trimThreads(threads: AskThread[], activeThreadId: string) {
  return threads
    .filter((thread) => thread.messages.length > 0 || thread.id === activeThreadId)
    .sort((left, right) => right.updatedAt - left.updatedAt)
    .slice(0, maxStoredThreads);
}

function updateThreadMessages(state: AskThreadState, threadId: string, updater: (messages: AskMessage[]) => AskMessage[]) {
  const fallback = state.threads[0] ?? createThread();
  const threads = state.threads.map((thread) => {
    if (thread.id !== threadId) return thread;
    const messages = updater(thread.messages).slice(-maxStoredMessages);
    return {
      ...thread,
      messages,
      title: threadTitle(messages),
      updatedAt: Date.now(),
    };
  });
  if (!threads.some((thread) => thread.id === threadId)) {
    const messages = updater([]).slice(-maxStoredMessages);
    threads.push({ ...fallback, id: threadId, messages, title: threadTitle(messages), updatedAt: Date.now() });
  }
  return { ...state, threads: trimThreads(threads, state.activeThreadId) };
}

function activeThreadFrom(state: AskThreadState) {
  return state.threads.find((thread) => thread.id === state.activeThreadId) ?? state.threads[0] ?? createThread();
}

function removeLegacyThread() {
  if (!canUseSessionStorage() || typeof sessionStorage.removeItem !== "function") return;
  sessionStorage.removeItem(legacyStorageKey());
}

function clearEmptyDraftThread(state: AskThreadState) {
  const active = activeThreadFrom(state);
  if (active.messages.length > 0) return state;
  const remaining = state.threads.filter((thread) => thread.id !== active.id);
  if (remaining.length === 0) return state;
  return { activeThreadId: remaining[0].id, threads: remaining };
}

function startFreshThread(state: AskThreadState) {
  const cleaned = clearEmptyDraftThread(state);
  const thread = createThread();
  return {
    activeThreadId: thread.id,
    threads: trimThreads([thread, ...cleaned.threads], thread.id),
  };
}

function resetActiveThread(state: AskThreadState) {
  const thread = activeThreadFrom(state);
  if (thread.messages.length === 0) return state;
  const empty = { ...thread, title: "新对话", updatedAt: Date.now(), messages: [] };
  return { ...state, threads: trimThreads([empty, ...state.threads.filter((item) => item.id !== thread.id)], thread.id) };
}

function removeThread(state: AskThreadState, threadId: string) {
  const remaining = state.threads.filter((thread) => thread.id !== threadId);
  if (remaining.length === 0) {
    const thread = createThread();
    return { activeThreadId: thread.id, threads: [thread] };
  }
  const activeThreadId = state.activeThreadId === threadId ? remaining[0].id : state.activeThreadId;
  return { activeThreadId, threads: remaining };
}

function restoreThread(state: AskThreadState, threadId: string) {
  if (!state.threads.some((thread) => thread.id === threadId)) return state;
  return clearEmptyDraftThread({ ...state, activeThreadId: threadId });
}

function sortedThreads(threads: AskThread[]) {
  return [...threads].sort((left, right) => right.updatedAt - left.updatedAt);
}

function shouldShowThread(thread: AskThread, activeThreadId: string) {
  return thread.messages.length > 0 || thread.id === activeThreadId;
}

function clearStoredThreads() {
  if (!canUseLocalStorage() || typeof localStorage.removeItem !== "function") return;
  localStorage.removeItem(threadStorageKey());
}

function isThreadStateEmpty(state: AskThreadState) {
  return state.threads.every((thread) => thread.messages.length === 0);
}

function saveIfUseful(state: AskThreadState) {
  if (isThreadStateEmpty(state)) {
    clearStoredThreads();
    return;
  }
  storeThreadState(state);
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
        <small>行情时间 {observedTime(result.observed_at)}</small>
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
  const [threadState, setThreadState] = useState<AskThreadState>(() => loadThreadState());
  const threadEndRef = useRef<HTMLDivElement | null>(null);
  const ask = useMutation({
    mutationFn: (value: string) => api<AskStockResponse>("/api/v1/ask-stock", {
      method: "POST",
      body: JSON.stringify({ question: value }),
    }),
  });
  const activeThread = useMemo(() => activeThreadFrom(threadState), [threadState]);
  const messages = activeThread.messages;
  const activeStock = useMemo(() => latestStock(messages), [messages]);
  const visibleThreads = useMemo(
    () => sortedThreads(threadState.threads).filter((thread) => shouldShowThread(thread, threadState.activeThreadId)),
    [threadState],
  );

  useEffect(() => {
    if (typeof threadEndRef.current?.scrollIntoView === "function") {
      threadEndRef.current.scrollIntoView({ block: "end" });
    }
  }, [activeThread.id, messages, ask.isPending]);

  useEffect(() => {
    saveIfUseful(threadState);
    removeLegacyThread();
  }, [threadState]);

  const submitQuestion = async (value: string) => {
    const normalized = value.trim();
    if (normalized.length < 2 || ask.isPending) return;

    const threadId = activeThread.id;
    const carriedStock = shouldCarryStock(normalized, activeStock) ? activeStock : null;
    const requestQuestion = carriedStock ? `${carriedStock.name} ${normalized}` : normalized;
    setThreadState((current) => updateThreadMessages(current, threadId, (currentMessages) => [
      ...currentMessages,
      { id: messageId(), role: "user", content: normalized, carriedStock },
    ]));
    setQuestion("");

    try {
      const result = await ask.mutateAsync(requestQuestion);
      setThreadState((current) => updateThreadMessages(current, threadId, (currentMessages) => [
        ...currentMessages,
        { id: messageId(), role: "assistant", result },
      ]));
    } catch (error) {
      const detail = error instanceof ApiError ? error.detail : "问股请求失败，请稍后重试。";
      setThreadState((current) => updateThreadMessages(current, threadId, (currentMessages) => [
        ...currentMessages,
        { id: messageId(), role: "error", content: detail, retryValue: requestQuestion },
      ]));
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
    setThreadState((current) => resetActiveThread(current));
    setQuestion("");
  };

  const newThread = () => {
    setThreadState((current) => startFreshThread(current));
    setQuestion("");
  };

  const openThread = (threadId: string) => {
    setThreadState((current) => restoreThread(current, threadId));
    setQuestion("");
  };

  const deleteThread = (threadId: string) => {
    setThreadState((current) => removeThread(current, threadId));
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
        <section className="ask-history" aria-label="历史对话">
          <header>
            <span><History size={15} />历史对话</span>
            <button type="button" onClick={newThread} disabled={ask.isPending} aria-label="新建问股对话"><Plus size={13} />新对话</button>
          </header>
          <div>
            {visibleThreads.map((thread) => (
              <article className={`ask-history-row ${thread.id === activeThread.id ? "active" : ""}`} key={thread.id}>
                <button
                  type="button"
                  className="ask-history-item"
                  onClick={() => openThread(thread.id)}
                  disabled={ask.isPending}
                  aria-current={thread.id === activeThread.id ? "true" : undefined}
                  aria-label={`打开历史对话：${thread.title}`}
                >
                  <strong>{thread.title}</strong>
                  <small>{threadMeta(thread)}</small>
                </button>
                {thread.messages.length > 0 ? <button
                  type="button"
                  className="ask-history-delete"
                  onClick={() => deleteThread(thread.id)}
                  disabled={ask.isPending}
                  aria-label={`删除历史对话：${thread.title}`}
                >×</button> : null}
              </article>
            ))}
          </div>
        </section>
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
          <small>{question.length}/160 · {activeStock ? `上文股票 ${stockLabel(activeStock)}` : "支持单股研究、账户持仓诊断；宽泛选股可走条件选股增强"}</small>
        </form>
      </div>
    </section>
  </>;
}
