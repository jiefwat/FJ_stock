import { History, MessageSquareText, Plus, RotateCcw, Send, ShieldAlert } from "lucide-react";
import { type FormEvent, type KeyboardEvent, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { PageTaskRail, WorkbenchPageHeader } from "../../components/WorkbenchPageHeader";
import { ApiError, getAuthToken, type AskStockConversationMessage, type AskStockResponse, type AskStockSourceContext as AskStockSourcePayload } from "../../lib/api";
import { holdingDecision } from "../../lib/decision";
import { monitoringItem } from "../../lib/monitoring";
import { plainLanguage } from "../../lib/plainLanguage";
import { rememberRecentResearch } from "../../lib/recentResearch";

type AskPlaybookScene = {
  intent: AskStockResponse["intent"];
  label: string;
  detail: string;
  example: string;
  question: (stock: StockAnchor | null) => string;
};

const askPlaybookScenes: AskPlaybookScene[] = [
  {
    intent: "movement",
    label: "异动后怎么做",
    detail: "大涨或大跌后，直接判断买入、持有、减仓还是退出。",
    example: "大业股份大跌后现在怎么处理",
    question: (stock) => `${stock?.name ?? "大业股份"}大跌后现在应该买、持有还是卖`,
  },
  {
    intent: "fundamental",
    label: "经营是否支持持有",
    detail: "把财报、现金流和公告翻译成继续持有或放弃的决定。",
    example: "贵州茅台的经营情况还支持持有吗",
    question: (stock) => `${stock?.name ?? "贵州茅台"}的经营情况还支持持有吗，直接给结论`,
  },
  {
    intent: "catalyst",
    label: "利好消息",
    detail: "看公告、机构报告、热门题材和板块是否一起走强；没有可靠信息就明确说未确认。",
    example: "贵州茅台有什么公告催化",
    question: (stock) => `${stock?.name ?? "贵州茅台"}有什么公告催化`,
  },
  {
    intent: "risk",
    label: "什么情况退出",
    detail: "直接给应该减仓或放弃的价格与条件。",
    example: "贵州茅台什么情况下应该退出",
    question: (stock) => `${stock?.name ?? "贵州茅台"}什么情况下应该减仓或退出`,
  },
  {
    intent: "action",
    label: "操作纪律",
    detail: "仓位、止损、止盈、入场约束；不给承诺式目标价。",
    example: "贵州茅台仓位和止损怎么定",
    question: (stock) => `${stock?.name ?? "贵州茅台"}仓位和止损怎么定`,
  },
  {
    intent: "portfolio",
    label: "今天先处理谁",
    detail: "读取当前账号持仓，直接给出今天的调仓顺序。",
    example: "我的组合今天先处理哪只，分别怎么做",
    question: () => "我的组合今天先处理哪只，分别怎么做",
  },
];

const intentLabel: Record<AskStockResponse["intent"], string> = {
  risk: "风险核对",
  trend: "趋势判断",
  valuation: "价格贵不贵",
  fundamental: "公司经营",
  catalyst: "利好消息",
  action: "操作纪律",
  movement: "异动解释",
  overview: "综合研究",
  screening: "条件选股",
  portfolio: "持仓诊断",
};
const storageVersion = 1;
const maxStoredMessages = 24;
const maxStoredThreads = 12;
const followUpPrompts = [
  { label: "现在能不能买", question: "现在能不能买，直接给我结论" },
  { label: "已经持有怎么办", question: "如果已经持有，现在怎么处理" },
  { label: "什么价格放弃", question: "跌到什么价格应该放弃" },
  { label: "仓位怎么定", question: "仓位和止损怎么定" },
];
const compactPlaybookIntents = new Set<AskStockResponse["intent"]>(["risk", "movement", "fundamental", "portfolio"]);
const stockCodePattern = /\b(?:SH|SZ|BJ)?\.?\d{6}\b/i;
const followUpPrefixPattern = /^(那|它|这个|这只|该股|刚才|上面|继续|再|顺便)/;
const followUpTopicPattern = /(风险|趋势|估值|基本面|财报|业绩|利润|营收|现金流|负债|公告|研报|消息|催化|题材|龙虎榜|仓位|止损|止盈|支撑|压力|目标价|价格|股价|合理|多少|为什么|为啥|怎么跌|怎么涨|大跌|大涨|异动|发生了什么|能买吗|能不能|要不要|可以买|可以卖|怎么样|怎么看)/;
const portfolioQuestionPattern = /(我的持仓|持仓里|持仓中|组合|账户|调仓|再平衡|仓位调整)/;
const screeningQuestionPattern = /(低估值|高股息|龙头|行业|板块|概念|题材|筛选|选股|有哪些|哪些|推荐|找|寻找|排名|排行)/;
const stockCodeColumnPattern = /(股票)?代码|证券代码|symbol/i;
const contextualReferencePattern = /(它|这只|该股|这个标的|这条线索|这家公司)/;
const sourcePresetLabels: Record<string, string> = {
  trend: "趋势延续",
  volume_breakout: "放量突破",
  value_rebound: "低估反弹",
  oversold_repair: "超跌修复",
};

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
type AskRequestPayload = {
  question: string;
  context: StockAnchor | null;
  conversation: AskStockConversationMessage[];
  sourceContext: AskSourceContext | null;
};
type AskSourceContext = {
  stock: StockAnchor | null;
  label: string;
  detail: string;
  origin: string;
  promptSeeds: string[];
  backHref?: string;
  backLabel?: string;
};
type AskMessage =
  | { id: string; role: "user"; content: string; carriedStock: StockAnchor | null }
  | { id: string; role: "assistant"; result: AskStockResponse }
  | { id: string; role: "assistant_stream"; content: string }
  | { id: string; role: "error"; content: string; retryValue: string };
type AskThread = { id: string; title: string; updatedAt: number; messages: AskMessage[] };
type AskThreadState = { activeThreadId: string; threads: AskThread[] };

function messageId() {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function stockLabel(stock: StockAnchor) {
  return `${stock.name} ${stock.symbol}`;
}

function safeParam(params: URLSearchParams, key: string) {
  return (params.get(key) ?? "").trim();
}

function sourceStockFrom(params: URLSearchParams): StockAnchor | null {
  const symbol = safeParam(params, "symbol");
  const name = safeParam(params, "name") || symbol;
  if (!symbol && !name) return null;
  return { symbol, name };
}

function requestConversation(messages: AskMessage[]): AskStockConversationMessage[] {
  return messages.flatMap<AskStockConversationMessage>((message) => {
    if (message.role === "user") return [{ role: "user" as const, content: message.content }];
    if (message.role === "assistant") return [{ role: "assistant" as const, content: message.result.answer }];
    return [];
  }).slice(-8);
}

function askRequestBody(payload: AskRequestPayload) {
  return JSON.stringify({
    question: payload.question,
    ...(payload.context ? { context_symbol: payload.context.symbol, context_name: payload.context.name } : {}),
    ...(payload.conversation.length > 0 ? { conversation: payload.conversation } : {}),
    ...(payload.sourceContext ? { source_context: requestSourceContext(payload.sourceContext) } : {}),
  });
}

async function askStock(payload: AskRequestPayload): Promise<AskStockResponse> {
  const headers = new Headers({ "Content-Type": "application/json" });
  const token = getAuthToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch("/api/v1/ask-stock", {
    method: "POST",
    headers,
    body: askRequestBody(payload),
  });
  if (!response.ok) {
    let detail = `请求失败 (${response.status})`;
    try {
      const body = await response.json() as { detail?: unknown };
      if (typeof body.detail === "string" && body.detail.trim()) detail = body.detail;
    } catch {
      // Keep the status fallback when the backend did not return JSON.
    }
    throw new ApiError(response.status, detail);
  }
  return response.json() as Promise<AskStockResponse>;
}

async function streamAskStock(
  payload: AskRequestPayload,
  handlers: { onDelta: (text: string) => void; onStatus: (message: string) => void },
): Promise<AskStockResponse> {
  const headers = new Headers({ "Content-Type": "application/json" });
  const token = getAuthToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch("/api/v1/ask-stock/stream", {
    method: "POST",
    headers,
    body: askRequestBody(payload),
  });
  if (!response.ok) {
    let detail = `请求失败 (${response.status})`;
    try {
      const body = await response.json() as { detail?: unknown };
      if (typeof body.detail === "string" && body.detail.trim()) detail = body.detail;
    } catch {
      // Keep the status fallback when the stream could not return JSON.
    }
    throw new ApiError(response.status, detail);
  }
  if (!response.body) return response.json() as Promise<AskStockResponse>;

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finalResult: AskStockResponse | null = null;

  const handleBlock = (block: string) => {
    const lines = block.split(/\r?\n/);
    const event = lines.find((line) => line.startsWith("event:"))?.slice(6).trim() ?? "message";
    const data = lines.filter((line) => line.startsWith("data:")).map((line) => line.slice(5).trim()).join("\n");
    if (!data) return;
    const parsed = JSON.parse(data) as { text?: unknown; message?: unknown; result?: AskStockResponse; detail?: unknown };
    if (event === "delta" && typeof parsed.text === "string") handlers.onDelta(parsed.text);
    if (event === "status" && typeof parsed.message === "string") handlers.onStatus(parsed.message);
    if (event === "final" && parsed.result) finalResult = parsed.result;
    if (event === "error") throw new ApiError(503, typeof parsed.detail === "string" ? parsed.detail : "问股请求失败，请稍后重试。");
  };

  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });
    const blocks = buffer.split(/\n\n/);
    buffer = blocks.pop() ?? "";
    for (const block of blocks) handleBlock(block);
    if (done) break;
  }
  if (buffer.trim()) handleBlock(buffer);
  if (!finalResult) throw new ApiError(504, "问股没有返回结果，请重试。");
  return finalResult;
}

function requestSourceContext(context: AskSourceContext | null): AskStockSourcePayload | null {
  if (!context) return null;
  return {
    origin: context.origin,
    label: context.label,
    detail: context.detail,
    ...(context.stock ? { stock: context.stock } : {}),
  };
}

function askSourceContext(params: URLSearchParams): AskSourceContext | null {
  const from = safeParam(params, "from");
  const stock = sourceStockFrom(params);
  const boardName = safeParam(params, "boardName");
  const boardType = safeParam(params, "boardType") || "板块";
  const preset = safeParam(params, "preset");
  const presetLabel = sourcePresetLabels[preset] ?? preset;
  const inboundQuestion = safeParam(params, "question");
  const holdingBridge = from === "holdings";

  if (from === "market") {
    return {
      stock,
      origin: "板块",
      label: boardName ? `${boardName}${boardType}` : "板块问题",
      detail: stock
        ? `默认围绕 ${stockLabel(stock)} 追问。`
        : "可以追问板块资金和前排样本。",
      promptSeeds: ["为什么它是板块前排样本", "板块资金是否确认它", "它的失效条件是什么"],
    };
  }

  if (holdingBridge) {
    return {
      stock,
      origin: "持仓",
      label: stock ? `处理${stockLabel(stock)}这笔持仓` : "处理账户组合",
      detail: stock
        ? "从持仓处理台带入上下文；优先回答这笔仓位的风险、偏离和调仓顺序。"
        : "从持仓处理台带入上下文；优先回答组合风险、集中度和今天先处理谁。",
      promptSeeds: stock
        ? ["我的持仓里这只要先减仓吗", "我的持仓里这只如果风险触发怎么调仓", "它在组合里是不是太重"]
        : ["我的持仓里风险最大的是哪个", "我的组合今天先处理哪只持仓", "帮我生成调仓计划"],
      backHref: "#/holdings",
      backLabel: "回到持仓处理 →",
    };
  }

  if (from === "opportunities") {
    return {
      stock,
      origin: "候选",
      label: "候选线索",
      detail: stock
        ? `默认围绕 ${stockLabel(stock)} 追问。`
        : "给出是否参与、仓位和放弃条件。",
      promptSeeds: [
        presetLabel ? `这条${presetLabel}线索现在能不能买` : "这条候选线索现在能不能买",
        "如果已经持有，现在怎么处理",
        "什么情况应该放弃",
      ],
    };
  }

  if (stock) {
    return {
      stock,
      origin: "个股",
      label: `围绕${stockLabel(stock)}继续问`,
      detail: "短句追问会自动带上这只股票。",
      promptSeeds: ["现在能不能买", "如果已经持有怎么处理", "什么价格应该放弃"],
    };
  }

  return null;
}

function latestStock(messages: AskMessage[]): StockAnchor | null {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const message = messages[index];
    if (message.role === "assistant" && message.result.symbol && message.result.name) {
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

function shouldCarrySourceStock(question: string, stock: StockAnchor | null) {
  if (!stock) return false;
  if (question.includes(stock.name) || question.includes(stock.symbol) || question.includes(stock.symbol.slice(-6))) return false;
  if (stockCodePattern.test(question)) return false;
  if (portfolioQuestionPattern.test(question)) return false;
  if (screeningQuestionPattern.test(question) && !contextualReferencePattern.test(question)) return false;
  if (contextualReferencePattern.test(question)) return true;
  if (followUpPrefixPattern.test(question)) return true;
  return question.length <= 16 && followUpTopicPattern.test(question);
}

function shouldSendContextStock(question: string, stock: StockAnchor | null) {
  if (!stock) return false;
  if (question.includes(stock.name) || question.includes(stock.symbol) || question.includes(stock.symbol.slice(-6))) return true;
  if (stockCodePattern.test(question)) return false;
  if (screeningQuestionPattern.test(question) && !contextualReferencePattern.test(question)) return false;
  if (contextualReferencePattern.test(question)) return true;
  if (followUpPrefixPattern.test(question)) return true;
  return question.length <= 20 && followUpTopicPattern.test(question);
}

function stockContextForQuestion(
  question: string,
  activeStock: StockAnchor | null,
  sourceStock: StockAnchor | null,
  forceSourceStock = false,
) {
  if (forceSourceStock && sourceStock) return sourceStock;
  if (shouldCarrySourceStock(question, sourceStock)) return sourceStock;
  if (shouldCarryStock(question, activeStock)) return activeStock;
  if (shouldSendContextStock(question, sourceStock)) return sourceStock;
  if (shouldSendContextStock(question, activeStock)) return activeStock;
  return null;
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
  const last = thread.messages.at(-1);
  if (last?.role === "error") return "失败";
  if (last?.role === "assistant_stream") return "生成中";
  if (last?.role === "user") return "待回答";
  const stock = latestStock(thread.messages);
  if (stock) return stockLabel(stock);
  const turns = thread.messages.filter((message) => message.role === "assistant").length;
  return turns > 0 ? `${turns} 条回答` : "新对话";
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
    .map((thread) => ({
      ...thread,
      messages: thread.messages.filter((message) => message.role !== "assistant_stream"),
    }))
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

function trailingUnansweredUser(messages: AskMessage[]) {
  const last = messages.at(-1);
  return last?.role === "user" ? last : null;
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
  const global = raw.match(/^(HK)\.?\s*(\d{1,5})$/) ?? raw.match(/^(US)\.?\s*([A-Z][A-Z0-9.-]{0,14})$/);
  if (global) return global[1] === "HK" ? `HK.${global[2].padStart(5, "0")}` : `US.${global[2]}`;
  const prefixed = raw.match(/^(SH|SZ|BJ)\.?\s*(\d{6})$/);
  if (prefixed) return `${prefixed[1]}.${prefixed[2]}`;
  const hk = raw.match(/^\d{1,5}$/);
  if (hk) return `HK.${raw.padStart(5, "0")}`;
  const plain = raw.match(/^\d{6}$/);
  if (!plain) return null;
  if (raw.startsWith("6")) return `SH.${raw}`;
  if (raw.startsWith("0") || raw.startsWith("3")) return `SZ.${raw}`;
  if (raw.startsWith("4") || raw.startsWith("8") || raw.startsWith("9")) return `BJ.${raw}`;
  return null;
}

function renderScreenCell(column: string, value: unknown) {
  const text = String(value ?? "—");
  if (column === "动作") return displayAction(text);
  if (!stockCodeColumnPattern.test(column)) return text;
  const symbol = symbolFromCode(value);
  if (!symbol) return text;
  return <a className="ask-table-link" href={`#/stocks?symbol=${encodeURIComponent(symbol)}`}>{text}</a>;
}

function EvidenceList({ title, items, tone }: { title: string; items: string[]; tone: string }) {
  if (items.length === 0) return null;
  return <section className={`ask-list ${tone}`}>
    <h3>{title}</h3>
    <ol>{items.map((item) => <li key={item}>{displayAskText(item)}</li>)}</ol>
  </section>;
}

function AskMetrics({ result }: { result: AskStockResponse }) {
  const metrics = result.metrics ?? [];
  if (metrics.length === 0) return null;
  return <div className="ask-metrics" aria-label="回答关键指标">
    {metrics.map((metric) => <span className={`ask-metric ${metric.tone}`} key={metric.label}>
      <small>{displayAskText(metric.label)}</small>
      <b>{displayAskText(metric.value)}</b>
    </span>)}
  </div>;
}

function displayAction(value: string | null | undefined) {
  if (!value) return "—";
  if (["hold", "trim", "add_watch", "review", "exit_watch"].includes(value)) return holdingDecision(value).action;
  return value;
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
    <span>10日走势 {signedPercentValue(holding.ten_day_change_pct)}</span>
    <span>10日贡献 {moneyValue(holding.ten_day_contribution)}</span>
    <span>动作 {displayAction(holding.action)}</span>
    {holding.risk_flags.length > 0 ? <small>风险：{holding.risk_flags.map(plainLanguage).join(" / ")}</small> : null}
  </aside>;
}

function metricByLabel(result: AskStockResponse, label: string) {
  return (result.metrics ?? []).find((metric) => metric.label === label) ?? null;
}

function stockResearchHref(result: AskStockResponse, anchor = "stock-final-gate") {
  if (!result.symbol) return "#/stocks";
  const params = new URLSearchParams({ symbol: result.symbol, from: "ask" });
  if (result.name) params.set("name", result.name);
  return `#/stocks?${params.toString()}#${anchor}`;
}

function gateReviewRoute(result: AskStockResponse) {
  const finalGate = metricByLabel(result, "FINAL GATE")?.value ?? "";
  const ledgerGate = metricByLabel(result, "LEDGER GATE")?.value ?? "";
  if (/反方|失效|守/.test(`${finalGate}${ledgerGate}`)) {
    return { anchor: "stock-risk-controls", label: "查看退出条件", detail: "主要风险和退出条件已核对。" };
  }
  if (/补|不足|缺口/.test(`${finalGate}${ledgerGate}`)) {
    return { anchor: "stock-company-evidence", label: "查看缺失资料", detail: "待补公告、研报和题材来源。" };
  }
  if (/交易|够用|计划/.test(`${finalGate}${ledgerGate}`)) {
    return { anchor: "stock-investment-advice", label: "查看价格与仓位", detail: "参与条件、止损和止盈已经整理好。" };
  }
  return { anchor: "stock-evidence-audit", label: "查看判断依据", detail: "支持、主要担心和缺失信息已经整理好。" };
}

function AskGateBrief({ result, embedded = false }: { result: AskStockResponse; embedded?: boolean }) {
  if (result.kind !== "stock_analysis") return null;
  const finalGate = metricByLabel(result, "FINAL GATE");
  const ledgerGate = metricByLabel(result, "LEDGER GATE");
  if (!finalGate || !ledgerGate) return null;
  const action = metricByLabel(result, "建议动作");
  const coverage = metricByLabel(result, "证据覆盖");
  const nextCheck = monitoringItem(result.next_actions[0] ?? "持续补齐依据并更新判断");
  const route = gateReviewRoute(result);

  return <section className="ask-gate-brief" aria-label="问股决策闸口">
    <div>
      <span>当前决定</span>
      <strong>现在怎么做</strong>
      {!embedded ? <a className="ask-gate-link" href={stockResearchHref(result, route.anchor)}>{route.label} →</a> : null}
    </div>
    <article className={finalGate.tone}>
      <small>结论</small>
      <b>{displayAskText(finalGate.value)}</b>
      <p>{displayAskText(action ? `当前动作：${action.value}` : "先看处理意见，再定仓位。")}</p>
    </article>
    <article className={ledgerGate.tone}>
      <small>证据</small>
      <b>{displayAskText(ledgerGate.value)}</b>
      <p>{displayAskText(coverage ? `信息完整度：${coverage.value}` : "先确认为什么值得看、主要担心和还缺的信息。")}</p>
    </article>
    <article className="neutral">
      <small>{nextCheck.label}</small>
      <b>{displayAskText(nextCheck.text)}</b>
      <p>{nextCheck.owner === "system" ? "后续核对自动更新。" : displayAskText(route.detail)}</p>
    </article>
  </section>;
}

function AskFactors({ result }: { result: AskStockResponse }) {
  const factors = result.factors ?? [];
  if (factors.length === 0) return null;
  return <details className="ask-factors">
    <summary>展开依据明细</summary>
    <div>
      {factors.map((factor) => <article className={`ask-factor ${factor.signal}`} key={`${factor.label}-${factor.evidence}`}>
        <b>{factor.impact > 0 ? `+${factor.impact}` : factor.impact}</b>
        <span>{displayAskText(factor.label)}</span>
        <p>{displayAskText(factor.evidence)}</p>
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

function displayAskText(value: string) {
  return plainLanguage(value
    .replace(/联网大模型问答|联网问答/g, "智能分析")
    .replace(/联网检索/g, "资料核对")
    .replace(/联网结论\s*[：:]/g, "结论：")
    .replace(/联网依据/g, "依据")
    .replace(/联网研究/g, "研究")
    .replace(/已检索/g, "已核对")
    .replace(/检索/g, "核对")
    .replace(/联网/g, "")
    .replace(/：：/g, "：")
    .trim());
}

function displayAskList(items: string[]) {
  return items.map(displayAskText);
}

function displayMonitoringList(items: string[]) {
  return items.map((item) => {
    const monitor = monitoringItem(displayAskText(item));
    return monitor.owner === "user" ? `${monitor.label}：${monitor.text}` : monitor.text;
  });
}

function displayAskSource(source: string) {
  return displayAskText(source) || "智能分析";
}

function confidenceLabel(value: number | null | undefined) {
  return value == null ? "分析置信度待补" : `分析置信度 ${Math.round(value * 100)}%（非上涨概率）`;
}

function AskResultHeader({ result, fallbackTitle, embedded = false }: { result: AskStockResponse; fallbackTitle: string; embedded?: boolean }) {
  return <header className="ask-result-head">
    <div>
      <span>{intentLabel[result.intent]}</span>
      <h2>{result.name ?? fallbackTitle}</h2>
      {result.symbol && <b>{result.symbol}</b>}
    </div>
    <div className="ask-provenance">
      <span>{displayAskSource(result.source)}</span>
      <b>{confidenceLabel(result.confidence)}</b>
      <small>行情时间 {observedTime(result.observed_at)}</small>
      {result.symbol && !embedded ? <a className="ask-stock-link" href={stockResearchHref(result)}>查看完整依据</a> : null}
    </div>
  </header>;
}

export function AskResult({ result, embedded = false }: { result: AskStockResponse; embedded?: boolean }) {
  const stockAnalysis = result.kind === "stock_analysis";
  const namedSkillAnswer = result.kind === "llm_answer" && Boolean(result.symbol && result.name);
  const [supportOpen, setSupportOpen] = useState(false);
  const fallbackTitle = result.kind === "portfolio_analysis" ? "账户组合" : result.kind === "llm_answer" ? "智能分析" : "自然语言选股";
  const sourceLabel = displayAskSource(result.source);
  if (result.kind === "llm_answer") {
    return <section className="ask-result ask-result-chat" aria-live="polite">
      {namedSkillAnswer ? <AskResultHeader result={result} fallbackTitle={fallbackTitle} embedded={embedded} /> : null}
      <article className="ask-answer">
        <p>{displayAskText(result.answer)}</p>
      </article>
      <div className="ask-evidence-grid ask-answer-evidence" aria-label="回答依据与行动">
        <EvidenceList title="判断依据" items={displayAskList(result.evidence)} tone="evidence" />
        <EvidenceList title="主要风险" items={displayAskList(result.risks)} tone="risk" />
        <EvidenceList title="后续跟踪" items={displayMonitoringList(result.next_actions)} tone="action" />
      </div>
      {!namedSkillAnswer ? <footer className="ask-answer-foot">
        <span><i>{sourceLabel}</i><b> · {confidenceLabel(result.confidence)}</b></span>
        {result.symbol && !embedded ? <a className="ask-stock-link" href={stockResearchHref(result)}>查看完整依据</a> : null}
      </footer> : null}
    </section>;
  }
  return <section className="ask-result" aria-live="polite">
    <AskResultHeader result={result} fallbackTitle={fallbackTitle} embedded={embedded} />
    <article className="ask-answer">
      <span>结论</span>
      <p>{displayAskText(result.answer)}</p>
    </article>
    {stockAnalysis ? <AskGateBrief result={result} embedded={embedded} /> : null}
    <HoldingContext result={result} />
    <AskRowsTable result={result} />
    <div className="ask-evidence-grid">
      <EvidenceList title="判断依据" items={displayAskList(result.evidence)} tone="evidence" />
      <EvidenceList title="主要风险" items={displayAskList(result.risks)} tone="risk" />
      <EvidenceList title="后续跟踪" items={displayMonitoringList(result.next_actions)} tone="action" />
    </div>
    {stockAnalysis ? <section className="ask-support-package">
      <button className="ask-support-toggle" type="button" aria-expanded={supportOpen} onClick={() => setSupportOpen((open) => !open)}>
        {supportOpen ? <><span>收起专业明细</span><span className="compat-copy">收起更多依据</span></> : <><span>专业明细</span><span className="compat-copy">展开更多依据</span></>}
      </button>
      {supportOpen && <>
        <AskMetrics result={result} />
        <AskFactors result={result} />
      </>}
    </section> : <>
      <AskMetrics result={result} />
      <AskFactors result={result} />
    </>}
    <p className="ask-disclaimer"><ShieldAlert size={14} />{displayAskText(result.disclaimer)}</p>
  </section>;
}

type StockQuestionTurn = {
  id: string;
  question: string;
  result: AskStockResponse;
};

const stockQuickQuestions = [
  { label: "现在能不能买", question: (name: string) => `${name}现在能不能买，直接给我结论` },
  { label: "持仓怎么处理", question: (name: string) => `如果已经持有${name}，现在怎么处理` },
  { label: "什么价格放弃", question: (name: string) => `${name}跌到什么价格应该放弃` },
  { label: "什么会改变决定", question: (name: string) => `${name}出现什么变化会改变当前决定` },
];

export function StockAskPanel({ symbol, name }: StockAnchor) {
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState<StockQuestionTurn[]>([]);
  const [pendingQuestion, setPendingQuestion] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    setQuestion("");
    setTurns([]);
    setPendingQuestion("");
    setError("");
  }, [symbol]);

  const ask = async (value: string) => {
    const normalized = value.trim();
    if (normalized.length < 2 || pendingQuestion) return;
    setQuestion("");
    setError("");
    setPendingQuestion(normalized);
    try {
      const result = await askStock({
        question: normalized,
        context: { symbol, name },
        conversation: turns.flatMap<AskStockConversationMessage>((turn) => [
          { role: "user", content: turn.question },
          { role: "assistant", content: turn.result.answer },
        ]).slice(-8),
        sourceContext: null,
      });
      setTurns((current) => [...current, { id: messageId(), question: normalized, result }]);
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.detail : "暂时没有收到回答，请稍后重试。");
      setQuestion(normalized);
    } finally {
      setPendingQuestion("");
    }
  };

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void ask(question);
  };
  const latest = turns.at(-1) ?? null;
  const history = turns.slice(0, -1).reverse();

  return <section id="stock-questions" className="stock-inline-ask" aria-label="继续问这只股票">
    <header>
      <div><span>继续研究</span><h3>继续问 {name}</h3></div>
      <p>直接回答当前问题；结论、关键依据、风险和下一步会自动展开。</p>
    </header>
    <nav aria-label="个股常用问题">
      {stockQuickQuestions.map((item) => <button type="button" key={item.label} onClick={() => void ask(item.question(name))} disabled={Boolean(pendingQuestion)}>{item.label}</button>)}
    </nav>
    {history.length > 0 ? <details className="stock-ask-history">
      <summary>历史追问 <b>{history.length}</b></summary>
      <div>{history.map((turn) => <details key={turn.id}>
        <summary>{turn.question}</summary>
        <AskResult result={turn.result} embedded />
      </details>)}</div>
    </details> : null}
    {latest ? <article className="stock-ask-latest" aria-label="最新追问回答">
      <header><span>你的问题</span><strong>{latest.question}</strong><small>最新回答 · 已展开</small></header>
      <AskResult result={latest.result} embedded />
    </article> : null}
    {pendingQuestion ? <div className="stock-ask-pending" role="status"><i /><span>正在核对行情、证据与风险</span><strong>{pendingQuestion}</strong></div> : null}
    {error ? <div className="stock-ask-error" role="alert"><span>{error}</span><button type="button" onClick={() => void ask(question)}>重试</button></div> : null}
    <form className="stock-ask-composer" aria-label="个股追问输入" onSubmit={submit}>
      <label htmlFor="stock-ask-question">继续问当前股票</label>
      <div>
        <textarea
          id="stock-ask-question"
          value={question}
          maxLength={160}
          rows={2}
          placeholder={`例如：${name}现在最大的风险是什么？`}
          onChange={(event) => setQuestion(event.target.value)}
          onKeyDown={(event) => {
            if (event.key !== "Enter" || event.shiftKey) return;
            event.preventDefault();
            void ask(question);
          }}
        />
        <button type="submit" disabled={Boolean(pendingQuestion) || question.trim().length < 2}><Send size={16} />{pendingQuestion ? "分析中" : "发送"}</button>
      </div>
      <small>{symbol} · Enter 发送，Shift + Enter 换行</small>
    </form>
  </section>;
}

export function AskStockPage() {
  const [searchParams] = useSearchParams();
  const [question, setQuestion] = useState("");
  const [threadState, setThreadState] = useState<AskThreadState>(() => loadThreadState());
  const [streaming, setStreaming] = useState(false);
  const threadEndRef = useRef<HTMLDivElement | null>(null);
  const inboundQuestionRef = useRef<string | null>(null);
  const activeThread = useMemo(() => activeThreadFrom(threadState), [threadState]);
  const messages = activeThread.messages;
  const activeStock = useMemo(() => latestStock(messages), [messages]);
  const sourceContext = useMemo(() => askSourceContext(searchParams), [searchParams]);
  const focusStock = sourceContext?.stock ?? activeStock ?? null;
  const unresolvedQuestion = !streaming ? trailingUnansweredUser(messages) : null;
  const visibleThreads = useMemo(
    () => sortedThreads(threadState.threads).filter((thread) => shouldShowThread(thread, threadState.activeThreadId)),
    [threadState],
  );

  useEffect(() => {
    if (!focusStock) return;
    rememberRecentResearch({ ...focusStock, sector: null });
  }, [focusStock?.name, focusStock?.symbol]);

  useEffect(() => {
    const frame = window.requestAnimationFrame(() => {
      if (typeof threadEndRef.current?.scrollIntoView === "function") {
        threadEndRef.current.scrollIntoView({ block: "end" });
      }
    });
    return () => window.cancelAnimationFrame(frame);
  }, [activeThread.id, messages.length, streaming]);

  useEffect(() => {
    if (streaming) return;
    saveIfUseful(threadState);
    removeLegacyThread();
  }, [streaming, threadState]);

  const submitQuestion = async (value: string, options: { forceSourceStock?: boolean } = {}) => {
    const normalized = value.trim();
    if (normalized.length < 2 || streaming) return;

    const threadId = activeThread.id;
    const carriedStock = stockContextForQuestion(
      normalized,
      activeStock,
      sourceContext?.stock ?? null,
      options.forceSourceStock,
    );
    const requestQuestion = normalized;
    const requestContext = carriedStock;
    const conversationContext = sourceContext?.stock && activeStock?.symbol !== sourceContext.stock.symbol
      ? []
      : requestConversation(messages);
    const streamId = messageId();
    setThreadState((current) => updateThreadMessages(current, threadId, (currentMessages) => [
      ...currentMessages,
      { id: messageId(), role: "user", content: normalized, carriedStock },
      { id: streamId, role: "assistant_stream", content: "读取行情..." },
    ]));
    setQuestion("");
    setStreaming(true);

    try {
      const payload = {
        question: requestQuestion,
        context: requestContext,
        conversation: conversationContext,
        sourceContext,
      };
      const result = await streamAskStock(payload, {
        onDelta: (text) => {
          setThreadState((current) => updateThreadMessages(current, threadId, (currentMessages) => (
            currentMessages.map((message) => (
              message.role === "assistant_stream" && message.id === streamId
                ? { ...message, content: displayAskText(`${message.content.endsWith("...") ? "" : message.content}${text}`) }
                : message
            ))
          )));
        },
        onStatus: (message) => {
          setThreadState((current) => updateThreadMessages(current, threadId, (currentMessages) => (
            currentMessages.map((item) => (
              item.role === "assistant_stream" && item.id === streamId && item.content.endsWith("...")
                ? { ...item, content: `${displayAskText(message)}...` }
                : item
            ))
          )));
        },
      }).catch(async () => {
        setThreadState((current) => updateThreadMessages(current, threadId, (currentMessages) => (
          currentMessages.map((item) => (
            item.role === "assistant_stream" && item.id === streamId
              ? { ...item, content: "流式回答中断，正在切换普通请求..." }
              : item
          ))
        )));
        return askStock(payload);
      });
      if (result.symbol && result.name) {
        rememberRecentResearch({ symbol: result.symbol, name: result.name, sector: null });
      }
      setThreadState((current) => updateThreadMessages(current, threadId, (currentMessages) => [
        ...currentMessages.filter((message) => !(message.role === "assistant_stream" && message.id === streamId)),
        { id: messageId(), role: "assistant", result },
      ]));
    } catch (error) {
      const detail = error instanceof ApiError ? error.detail : "问股请求失败，请稍后重试。";
      setThreadState((current) => updateThreadMessages(current, threadId, (currentMessages) => [
        ...currentMessages.filter((message) => !(message.role === "assistant_stream" && message.id === streamId)),
        { id: messageId(), role: "error", content: displayAskText(detail), retryValue: requestQuestion },
      ]));
      setQuestion(value);
    } finally {
      setStreaming(false);
    }
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    void submitQuestion(question);
  };

  useEffect(() => {
    const inboundQuestion = safeParam(searchParams, "question");
    if (inboundQuestion.length < 2 || inboundQuestionRef.current === inboundQuestion) return;
    inboundQuestionRef.current = inboundQuestion;
    setQuestion(inboundQuestion);
    void submitQuestion(inboundQuestion);
  }, [searchParams]);

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

  const resendUnanswered = (message: Extract<AskMessage, { role: "user" }>) => {
    setThreadState((current) => updateThreadMessages(current, activeThread.id, (currentMessages) => (
      currentMessages.filter((item) => item.id !== message.id)
    )));
    void submitQuestion(message.content);
  };

  return <>
    <WorkbenchPageHeader
      title="研究问答"
      status={<div className={`ask-header-state ${focusStock ? "active" : ""}`}><span>对话对象</span><strong>{focusStock ? stockLabel(focusStock) : "尚未指定股票"}</strong><small>{focusStock ? "追问会沿用当前股票" : "可问股票、板块或组合"}</small></div>}
    />
    <PageTaskRail label="研究问答" steps={[
      { id: "ask-session", label: "确认对象", detail: "避免追问串股" },
      { id: "ask-quick", label: "选择问题", detail: "从高频决策场景开始" },
      { id: "ask-thread", label: "核对回答", detail: "结论、置信度与证据" },
      { id: "ask-composer", label: "继续追问", detail: "沿用当前上下文" },
    ]} />
    <section className="ask-chat-layout">
      <div className="ask-chat-main">
        <header id="ask-session" className="ask-chat-top">
          <div>
            <strong>当前对话</strong>
          </div>
          <nav aria-label="问股对话操作">
            <button type="button" onClick={newThread} disabled={streaming} aria-label="新建问股对话"><Plus size={13} />新对话</button>
            <button type="button" onClick={clearThread} disabled={messages.length === 0 || streaming}><RotateCcw size={14} />清空</button>
            <details className="ask-history-menu" aria-label="历史对话">
              <summary><History size={15} />历史</summary>
              <div>
                {visibleThreads.map((thread) => (
                  <article className={`ask-history-row ${thread.id === activeThread.id ? "active" : ""}`} key={thread.id}>
                    <button
                      type="button"
                      className="ask-history-item"
                      onClick={() => openThread(thread.id)}
                      disabled={streaming}
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
                      disabled={streaming}
                      aria-label={`删除历史对话：${thread.title}`}
                    >×</button> : null}
                  </article>
                ))}
              </div>
            </details>
          </nav>
        </header>
        {sourceContext ? <section className="ask-source-context" aria-label="问股来源上下文">
          <header>
            <span>{sourceContext.origin}</span>
            <strong>{sourceContext.label}</strong>
          </header>
          <p>{sourceContext.detail}</p>
          {sourceContext.stock || sourceContext.backHref ? <a href={sourceContext.backHref ?? `#/stocks?symbol=${encodeURIComponent(sourceContext.stock?.symbol ?? "")}`}>{sourceContext.backLabel ?? "回到个股 →"}</a> : null}
          <div>
            {sourceContext.promptSeeds.map((prompt) => <button
              type="button"
              key={prompt}
              onClick={() => void submitQuestion(prompt, { forceSourceStock: true })}
              disabled={streaming}
            >{prompt}</button>)}
          </div>
        </section> : null}
        <section id="ask-quick" className="ask-playbook compact ask-main-playbook" aria-label="问股场景路由">
          <header>
            <span>快捷</span>
            <strong>常用问题</strong>
          </header>
          <div>
            {askPlaybookScenes.filter((scene) => compactPlaybookIntents.has(scene.intent)).map((scene) => {
              const nextQuestion = scene.question(focusStock);
              return <button
                type="button"
                key={scene.intent}
                onClick={() => void submitQuestion(nextQuestion)}
                disabled={streaming}
              >
                <span>{intentLabel[scene.intent]}</span>
                <strong>{scene.label}</strong>
                <em>{focusStock ? nextQuestion : scene.example}</em>
              </button>;
            })}
          </div>
        </section>
        <section id="ask-thread" className="ask-thread panel" aria-label="问股对话记录">
          {messages.length === 0 ? <div className="ask-thread-empty">
            <MessageSquareText size={28} />
            <strong>直接问股票、板块或持仓</strong>
          </div> : messages.map((message) => {
            if (message.role === "user") {
              return <article className="ask-message user" key={message.id}>
                <div><span>你</span><p>{message.content}</p>{message.carriedStock ? <small>沿用上文：{stockLabel(message.carriedStock)}</small> : null}</div>
              </article>;
            }
            if (message.role === "error") {
              return <article className="ask-message error" key={message.id} role="alert">
                <span>{message.content}</span>
                <button type="button" onClick={() => void submitQuestion(message.retryValue)} disabled={streaming}>重试</button>
              </article>;
            }
            if (message.role === "assistant_stream") {
              return <article className="ask-message assistant pending streaming" key={message.id}>
                <span>问股</span>
                <p>{message.content}</p>
              </article>;
            }
            return <article className="ask-message assistant" key={message.id}>
              <span>问股</span>
              <AskResult result={message.result} />
              {message.result.kind === "stock_analysis" || (message.result.kind === "llm_answer" && message.result.symbol && message.result.name) ? <div className="ask-followups" aria-label="追问建议">
                {followUpPrompts.map((prompt) => <button type="button" key={prompt.label} onClick={() => void submitQuestion(prompt.question)} disabled={streaming}>{prompt.label}</button>)}
              </div> : null}
            </article>;
          })}
          {unresolvedQuestion ? <article className="ask-message unresolved" role="status">
            <span>没有收到回答，可能是刷新或网络中断。</span>
            <button type="button" onClick={() => resendUnanswered(unresolvedQuestion)}>重新发送</button>
          </article> : null}
          <div ref={threadEndRef} />
        </section>
        <form id="ask-composer" className="ask-chat-composer panel" onSubmit={submit}>
          <label htmlFor="ask-question">继续追问</label>
          <div>
            <textarea
              id="ask-question"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              onKeyDown={handleComposerKeyDown}
              maxLength={160}
              placeholder={focusStock ? `继续问 ${focusStock.name}：例如 那估值呢` : "例如：贵州茅台现在主要风险是什么"}
            />
            <button className="button ask-submit" type="submit" disabled={streaming || question.trim().length < 2}>
              <Send size={16} />{streaming ? "分析中" : "发送"}
            </button>
          </div>
          <small>{question.length}/160{focusStock ? ` · ${stockLabel(focusStock)}` : ""}</small>
        </form>
      </div>
    </section>
  </>;
}
