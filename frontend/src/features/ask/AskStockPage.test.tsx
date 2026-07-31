import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { AskStockPage } from "./AskStockPage";

const stockAnswer = {
  kind: "stock_analysis",
  question: "贵州茅台主要风险是什么",
  intent: "risk",
  symbol: "SH.600519",
  name: "贵州茅台",
  answer: "贵州茅台当前主要风险：短期波动放大。",
  evidence: ["价格仍在 MA20 上方", "估值处于同业中位"],
  risks: ["短期波动放大"],
  next_actions: ["等待下一交易日确认"],
  metrics: [
    { label: "综合分", value: "62", tone: "positive" },
    { label: "建议动作", value: "观察", tone: "positive" },
    { label: "证据覆盖", value: "80%", tone: "positive" },
    { label: "置信度", value: "70%", tone: "positive" },
    { label: "FINAL GATE", value: "进入交易计划", tone: "positive" },
    { label: "LEDGER GATE", value: "证据够用", tone: "positive" },
    { label: "最新价", value: "1500.00", tone: "neutral" },
    { label: "涨跌幅", value: "+1.20%", tone: "positive" },
  ],
  factors: [
    { label: "价格与 MA20", impact: 10, signal: "positive", evidence: "收盘价位于 20 日均线之上" },
    { label: "波动风险", impact: -4, signal: "negative", evidence: "ATR 占现价偏高" },
  ],
  holding_context: null,
  observed_at: "2026-07-25T01:00:00Z",
  source: "本地行情快照 + 确定性分析",
  disclaimer: "研究辅助信息，不构成投资建议。",
  columns: [],
  rows: [],
};

function renderPage(route = "/ask") {
  const client = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
  return render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[route]}><AskStockPage /></MemoryRouter></QueryClientProvider>);
}

function submitAsk(value: string) {
  fireEvent.change(screen.getByLabelText("继续追问"), { target: { value } });
  fireEvent.click(screen.getByRole("button", { name: "发送" }));
}

beforeEach(() => {
  const storage = new Map<string, string>([["marketdesk.accessToken", "token-ask"]]);
  const session = new Map<string, string>();
  vi.stubGlobal("localStorage", {
    getItem: (key: string) => storage.get(key) ?? null,
    setItem: (key: string, value: string) => storage.set(key, value),
    removeItem: (key: string) => storage.delete(key),
  });
  vi.stubGlobal("sessionStorage", {
    getItem: (key: string) => session.get(key) ?? null,
    setItem: (key: string, value: string) => session.set(key, value),
    removeItem: (key: string) => session.delete(key),
  });
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("submits a suggested question and renders a named-stock evidence answer", async () => {
  const requests: Array<{ body: string; auth: string }> = [];
  vi.stubGlobal("fetch", vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
    requests.push({
      body: String(init?.body),
      auth: new Headers(init?.headers).get("Authorization") ?? "",
    });
    return { ok: true, status: 200, json: async () => stockAnswer };
  }));

  renderPage();
  expect(screen.getByRole("heading", { name: "问股" })).toBeInTheDocument();
  submitAsk("贵州茅台现在主要风险是什么");

  await waitFor(() => expect(screen.getAllByText("贵州茅台现在主要风险是什么").length).toBeGreaterThanOrEqual(2));
  expect(await screen.findByText("贵州茅台当前主要风险：短期波动放大。")).toBeInTheDocument();
  expect(screen.getByText("SH.600519")).toBeInTheDocument();
  expect(screen.getByText("价格仍在 MA20 上方")).toBeInTheDocument();
  expect(screen.getAllByText("短期波动放大").length).toBeGreaterThan(0);
  expect(screen.getAllByText("等待下一交易日确认").length).toBeGreaterThan(0);
  expect(screen.getByText("本地行情快照 + 确定性分析")).toBeInTheDocument();
  expect(screen.getByText("研究辅助信息，不构成投资建议。")).toBeInTheDocument();
  expect(screen.getByText("结论")).toBeInTheDocument();
  expect(screen.queryByLabelText("问股决策闸口")).not.toBeInTheDocument();
  expect(screen.queryByLabelText("回答关键指标")).not.toBeInTheDocument();
  fireEvent.click(screen.getByText("展开更多依据"));
  expect(screen.getByLabelText("回答关键指标")).toHaveTextContent("综合分62");
  expect(screen.getByLabelText("回答关键指标")).toHaveTextContent("证据覆盖80%");
  const gate = screen.getByLabelText("问股决策闸口");
  expect(gate).toHaveTextContent("依据");
  expect(gate).toHaveTextContent("结论进入交易计划");
  expect(gate).toHaveTextContent("证据证据够用");
  expect(gate).toHaveTextContent("下一步等待下一交易日确认");
  expect(screen.getByRole("link", { name: "去看交易计划 →" })).toHaveAttribute(
    "href",
    "#/stocks?symbol=SH.600519&from=ask&name=%E8%B4%B5%E5%B7%9E%E8%8C%85%E5%8F%B0#stock-investment-advice",
  );
  expect(screen.queryByLabelText("问股复核路线")).not.toBeInTheDocument();
  expect(screen.getByText("收起依据")).toBeInTheDocument();
  expect(screen.getByText("展开评分因子")).toBeInTheDocument();
  expect(screen.getByText("价格与 MA20")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "打开个股研究" })).toHaveAttribute(
    "href",
    "#/stocks?symbol=SH.600519&from=ask&name=%E8%B4%B5%E5%B7%9E%E8%8C%85%E5%8F%B0#stock-final-gate",
  );
  expect(screen.getByRole("button", { name: "继续问估值" })).toBeInTheDocument();
  expect(requests).toEqual([{
    body: JSON.stringify({ question: "贵州茅台现在主要风险是什么" }),
    auth: "Bearer token-ask",
  }]);
});

it("streams answer text before the final Ask Stock payload arrives", async () => {
  const encoder = new TextEncoder();
  let controller: ReadableStreamDefaultController<Uint8Array> | null = null;
  vi.stubGlobal("fetch", vi.fn(async () => new Response(
    new ReadableStream<Uint8Array>({
      start(nextController) {
        controller = nextController;
      },
    }),
    { status: 200, headers: { "content-type": "text/event-stream" } },
  )));

  renderPage();
  submitAsk("贵州茅台现在主要风险是什么");

  expect(await screen.findByText("读取行情...")).toBeInTheDocument();
  await act(async () => {
    controller?.enqueue(encoder.encode('event: status\ndata: {"message":"联网检索"}\n\n'));
  });
  expect(await screen.findByText("联网检索...")).toBeInTheDocument();
  await act(async () => {
    controller?.enqueue(encoder.encode('event: delta\ndata: {"text":"结论：短线先看量能。"}\n\n'));
  });
  expect(await screen.findByText("结论：短线先看量能。")).toBeInTheDocument();
  await act(async () => {
    controller?.enqueue(encoder.encode(`event: final\ndata: ${JSON.stringify({ result: stockAnswer })}\n\n`));
    controller?.close();
  });

  expect(await screen.findByText("贵州茅台当前主要风险：短期波动放大。")).toBeInTheDocument();
  expect(screen.queryByText("结论：短线先看量能。")).not.toBeInTheDocument();
});

it("uses market board context for focused Ask Stock prompts", async () => {
  const requests: string[] = [];
  vi.stubGlobal("fetch", vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
    const parsed = JSON.parse(String(init?.body)) as { question: string };
    requests.push(parsed.question);
    return { ok: true, status: 200, json: async () => ({ ...stockAnswer, question: parsed.question }) };
  }));

  renderPage("/ask?symbol=SH.600519&name=贵州茅台&from=market&board=BK1&boardName=白酒&boardType=板块");

  expect(screen.getByLabelText("问股来源上下文")).toHaveTextContent("板块");
  expect(screen.getByLabelText("问股来源上下文")).toHaveTextContent("白酒板块");
  expect(screen.getByLabelText("问股来源上下文")).toHaveTextContent("默认围绕 贵州茅台 SH.600519 追问");
  expect(screen.getByRole("link", { name: "回到个股 →" })).toHaveAttribute("href", "#/stocks?symbol=SH.600519");
  fireEvent.click(screen.getByRole("button", { name: "为什么它是板块前排样本" }));

  expect(await screen.findByText("贵州茅台当前主要风险：短期波动放大。")).toBeInTheDocument();
  expect(screen.getByText("沿用上文：贵州茅台 SH.600519")).toBeInTheDocument();
  expect(requests).toEqual(["为什么它是板块前排样本"]);
});

it("sends focused stock context for short manual follow-up questions", async () => {
  const requests: Array<{ question: string; context_symbol?: string; context_name?: string; source_context?: unknown }> = [];
  vi.stubGlobal("fetch", vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
    const parsed = JSON.parse(String(init?.body)) as { question: string; context_symbol?: string; context_name?: string; source_context?: unknown };
    requests.push(parsed);
    return {
      ok: true,
      status: 200,
      json: async () => ({
        ...stockAnswer,
        question: parsed.question,
        intent: "movement",
        answer: "结论：贵州茅台近期下跌优先看价格破位、量能和板块温度。",
      }),
    };
  }));

  renderPage("/ask?symbol=SH.600519&name=贵州茅台&from=market&board=BK1&boardName=白酒&boardType=板块");

  fireEvent.change(screen.getByLabelText("继续追问"), { target: { value: "为什么最近大跌" } });
  fireEvent.click(screen.getByRole("button", { name: "发送" }));

  expect(await screen.findByText("结论：贵州茅台近期下跌优先看价格破位、量能和板块温度。")).toBeInTheDocument();
  expect(screen.getByText("沿用上文：贵州茅台 SH.600519")).toBeInTheDocument();
  expect(requests).toEqual([{
    question: "为什么最近大跌",
    context_symbol: "SH.600519",
    context_name: "贵州茅台",
    source_context: {
      origin: "板块",
      label: "白酒板块",
      detail: "默认围绕 贵州茅台 SH.600519 追问。",
      stock: { symbol: "SH.600519", name: "贵州茅台" },
    },
  }]);
});

it("prefers the source stock over stale history for short handoff questions", async () => {
  localStorage.setItem("marketdesk.askStockThreads.v1.token-ask", JSON.stringify({
    version: 1,
    activeThreadId: "old-moutai",
    threads: [{
      id: "old-moutai",
      title: "贵州茅台现在主要风险是什么",
      updatedAt: Date.now() - 60_000,
      messages: [
        { id: "u-old", role: "user", content: "贵州茅台现在主要风险是什么", carriedStock: null },
        { id: "a-old", role: "assistant", result: stockAnswer },
      ],
    }],
  }));
  const requests: Array<{ question: string; context_symbol?: string; context_name?: string; source_context?: unknown }> = [];
  vi.stubGlobal("fetch", vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
    const parsed = JSON.parse(String(init?.body)) as { question: string; context_symbol?: string; context_name?: string; source_context?: unknown };
    requests.push(parsed);
    return {
      ok: true,
      status: 200,
      json: async () => ({
        ...stockAnswer,
        question: parsed.question,
        symbol: "SZ.300750",
        name: "宁德时代",
        intent: "movement",
        answer: "结论：宁德时代近期下跌先看新能源板块温度和资金撤退。",
      }),
    };
  }));

  renderPage("/ask?symbol=SZ.300750&name=宁德时代&from=opportunities&preset=trend");

  expect(screen.getByText("正在围绕 宁德时代 SZ.300750 追问")).toBeInTheDocument();
  expect(screen.getByText("围绕 宁德时代 SZ.300750 生成")).toBeInTheDocument();
  expect(screen.getByText("最近宁德时代怎么大跌")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("继续追问"), { target: { value: "为什么最近大跌" } });
  fireEvent.click(screen.getByRole("button", { name: "发送" }));

  expect(await screen.findByText("结论：宁德时代近期下跌先看新能源板块温度和资金撤退。")).toBeInTheDocument();
  expect(screen.getByText("沿用上文：宁德时代 SZ.300750")).toBeInTheDocument();
  expect(requests).toEqual([{
    question: "为什么最近大跌",
    context_symbol: "SZ.300750",
    context_name: "宁德时代",
    source_context: {
      origin: "机会",
      label: "机会线索",
      detail: "默认围绕 宁德时代 SZ.300750 追问。",
      stock: { symbol: "SZ.300750", name: "宁德时代" },
    },
  }]);
});

it("uses opportunity context for lead upgrade prompts", async () => {
  const requests: string[] = [];
  vi.stubGlobal("fetch", vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
    const parsed = JSON.parse(String(init?.body)) as { question: string };
    requests.push(parsed.question);
    return {
      ok: true,
      status: 200,
      json: async () => ({ ...stockAnswer, symbol: "SZ.300750", name: "宁德时代", question: parsed.question, answer: "宁德时代这条线索仍需补齐资金确认。" }),
    };
  }));

  renderPage("/ask?symbol=SZ.300750&name=宁德时代&from=opportunities&preset=trend");

  expect(screen.getByLabelText("问股来源上下文")).toHaveTextContent("机会");
  expect(screen.getByLabelText("问股来源上下文")).toHaveTextContent("机会线索");
  expect(screen.getByRole("button", { name: "这条趋势延续线索能升级吗" })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "这条趋势延续线索能升级吗" }));

  expect(await screen.findByText("宁德时代这条线索仍需补齐资金确认。")).toBeInTheDocument();
  expect(requests).toEqual(["这条趋势延续线索能升级吗"]);
});

it("uses holdings context for portfolio treatment handoffs", async () => {
  const requests: string[] = [];
  vi.stubGlobal("fetch", vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
    const parsed = JSON.parse(String(init?.body)) as { question: string };
    requests.push(parsed.question);
    return {
      ok: true,
      status: 200,
      json: async () => ({
        ...stockAnswer,
        kind: "portfolio_analysis",
        intent: "portfolio",
        symbol: null,
        name: null,
        question: parsed.question,
        answer: "结论：这笔持仓先按减仓复核，不急着补仓。",
        evidence: ["组合占比高于目标"],
        risks: ["持仓偏离目标仓位"],
        next_actions: ["先复核调仓顺序"],
      }),
    };
  }));

  renderPage("/ask?symbol=SH.600519&name=贵州茅台&from=holdings&question=我的持仓里贵州茅台风险怎么处理，要不要调仓");

  const context = screen.getByLabelText("问股来源上下文");
  expect(context).toHaveTextContent("持仓");
  expect(context).toHaveTextContent("处理贵州茅台 SH.600519这笔持仓");
  expect(context).toHaveTextContent("优先回答这笔仓位的风险、偏离和调仓顺序");
  expect(within(context).getByRole("link", { name: "回到持仓处理 →" })).toHaveAttribute("href", "#/holdings");
  expect(within(context).getByRole("button", { name: "我的持仓里这只要先减仓吗" })).toBeInTheDocument();
  expect(await screen.findByText("结论：这笔持仓先按减仓复核，不急着补仓。")).toBeInTheDocument();

  fireEvent.click(within(context).getByRole("button", { name: "我的持仓里这只要先减仓吗" }));

  await waitFor(() => expect(requests).toEqual([
    "我的持仓里贵州茅台风险怎么处理，要不要调仓",
    "我的持仓里这只要先减仓吗",
  ]));
});

it("routes users through the Ask Stock playbook before submitting", async () => {
  const requests: string[] = [];
  vi.stubGlobal("fetch", vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
    const parsed = JSON.parse(String(init?.body)) as { question: string };
    requests.push(parsed.question);
    return {
      ok: true,
      status: 200,
      json: async () => ({
        ...stockAnswer,
        question: parsed.question,
        intent: "movement",
        symbol: "SH.603278",
        name: "大业股份",
        answer: "结论：大业股份近期下跌先按行情结构解释，近5日跌幅偏大。",
        evidence: ["近5日涨跌幅 -18.40%"],
        risks: ["价格低于 MA20"],
        next_actions: ["核对最近公告和所属板块新闻"],
      }),
    };
  }));

  renderPage();

  const playbook = screen.getByLabelText("问股场景路由");
  const thread = screen.getByLabelText("问股对话记录");
  expect(playbook).toHaveTextContent("常用问题");
  expect(playbook).toHaveTextContent("基本面");
  expect(playbook).toHaveTextContent("持仓诊断");
  expect(playbook.compareDocumentPosition(thread) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  fireEvent.click(within(playbook).getByRole("button", { name: /异动解释/ }));

  expect(await screen.findByText(/大业股份近期下跌/)).toBeInTheDocument();
  expect(screen.getAllByText("异动解释").length).toBeGreaterThan(0);
  expect(screen.getByText("近5日涨跌幅 -18.40%")).toBeInTheDocument();
  expect(requests).toEqual(["最近大业股份怎么大跌"]);
});

it("lets users resend an interrupted question-only thread", async () => {
  localStorage.setItem("marketdesk.askStockThreads.v1.token-ask", JSON.stringify({
    version: 1,
    activeThreadId: "interrupted",
    threads: [{
      id: "interrupted",
      title: "大业股份最大的风险是什么",
      updatedAt: Date.now(),
      messages: [
        { id: "u-interrupted", role: "user", content: "大业股份最大的风险是什么", carriedStock: null },
      ],
    }],
  }));
  const requests: string[] = [];
  vi.stubGlobal("fetch", vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
    const parsed = JSON.parse(String(init?.body)) as { question: string };
    requests.push(parsed.question);
    return {
      ok: true,
      status: 200,
      json: async () => ({
        ...stockAnswer,
        kind: "llm_answer",
        intent: "risk",
        symbol: "SH.603278",
        name: "大业股份",
        question: parsed.question,
        answer: "大业股份最大风险是业绩亏损和行业竞争加剧。",
        source: "联网大模型问答",
      }),
    };
  }));

  renderPage();

  const history = screen.getByLabelText("历史对话");
  expect(history).toHaveTextContent("待回答");
  expect(screen.getByRole("status")).toHaveTextContent("没有收到回答");
  fireEvent.click(screen.getByRole("button", { name: "重新发送" }));

  expect(await screen.findByText("大业股份最大风险是业绩亏损和行业竞争加剧。")).toBeInTheDocument();
  expect(requests).toEqual(["大业股份最大的风险是什么"]);
});

it("auto-submits a question passed from the global research router", async () => {
  const requests: string[] = [];
  vi.stubGlobal("fetch", vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
    const parsed = JSON.parse(String(init?.body)) as { question: string };
    requests.push(parsed.question);
    return {
      ok: true,
      status: 200,
      json: async () => ({
        ...stockAnswer,
        question: parsed.question,
        intent: "fundamental",
        answer: "结论：贵州茅台基本面要先看现金流、利润质量和最新公告。",
      }),
    };
  }));

  renderPage("/ask?question=贵州茅台基本面怎么样");

  expect(await screen.findByText("结论：贵州茅台基本面要先看现金流、利润质量和最新公告。")).toBeInTheDocument();
  expect(screen.getAllByText("贵州茅台基本面怎么样").length).toBeGreaterThanOrEqual(1);
  expect(requests).toEqual(["贵州茅台基本面怎么样"]);
});

it("keeps multiple turns and carries the previous stock into a follow-up", async () => {
  const requests: Array<{ question: string; conversation?: Array<{ role: string; content: string }>; context_symbol?: string; context_name?: string }> = [];
  vi.stubGlobal("fetch", vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
    const parsed = JSON.parse(String(init?.body)) as { question: string; conversation?: Array<{ role: string; content: string }>; context_symbol?: string; context_name?: string };
    requests.push(parsed);
    return {
      ok: true,
      status: 200,
      json: async () => ({
        ...stockAnswer,
        question: parsed.question,
        answer: parsed.question.includes("估值") ? "贵州茅台估值处于合理偏高区间。" : stockAnswer.answer,
        intent: parsed.question.includes("估值") ? "valuation" : "risk",
      }),
    };
  }));

  renderPage();
  submitAsk("贵州茅台现在主要风险是什么");
  expect(await screen.findByText("贵州茅台当前主要风险：短期波动放大。")).toBeInTheDocument();

  fireEvent.change(screen.getByLabelText("继续追问"), { target: { value: "那估值呢" } });
  fireEvent.click(screen.getByRole("button", { name: "发送" }));

  expect(await screen.findByText("贵州茅台估值处于合理偏高区间。")).toBeInTheDocument();
  expect(screen.getByText("那估值呢")).toBeInTheDocument();
  expect(screen.getByText("沿用上文：贵州茅台 SH.600519")).toBeInTheDocument();
  expect(requests[0]).toEqual({ question: "贵州茅台现在主要风险是什么" });
  expect(requests[1]).toEqual({
    question: "那估值呢",
    context_symbol: "SH.600519",
    context_name: "贵州茅台",
    conversation: [
      { role: "user", content: "贵州茅台现在主要风险是什么" },
      { role: "assistant", content: "贵州茅台当前主要风险：短期波动放大。" },
    ],
  });
});

it("carries the previous stock for natural follow-up questions without provider wording", async () => {
  const requests: string[] = [];
  vi.stubGlobal("fetch", vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
    const parsed = JSON.parse(String(init?.body)) as { question: string };
    requests.push(parsed.question);
    return {
      ok: true,
      status: 200,
      json: async () => ({
        ...stockAnswer,
        question: parsed.question,
        answer: parsed.question.includes("多少合理") ? "贵州茅台合理仓位应先按风险预算控制。" : stockAnswer.answer,
        intent: parsed.question.includes("多少合理") ? "action" : "risk",
      }),
    };
  }));

  renderPage();
  submitAsk("贵州茅台现在主要风险是什么");
  expect(await screen.findByText("贵州茅台当前主要风险：短期波动放大。")).toBeInTheDocument();

  fireEvent.change(screen.getByLabelText("继续追问"), { target: { value: "你觉得多少合理" } });
  fireEvent.click(screen.getByRole("button", { name: "发送" }));

  expect(await screen.findByText("贵州茅台合理仓位应先按风险预算控制。")).toBeInTheDocument();
  expect(screen.getByText("沿用上文：贵州茅台 SH.600519")).toBeInTheDocument();
  expect(screen.queryByText(/问财/i)).not.toBeInTheDocument();
  expect(requests).toEqual(["贵州茅台现在主要风险是什么", "你觉得多少合理"]);
});

it("restores the current tab conversation for the same session", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => ({ ok: true, status: 200, json: async () => stockAnswer })));

  const { unmount } = renderPage();
  submitAsk("贵州茅台现在主要风险是什么");
  expect(await screen.findByText("贵州茅台当前主要风险：短期波动放大。")).toBeInTheDocument();
  unmount();

  renderPage();
  expect(screen.getAllByText("贵州茅台现在主要风险是什么").length).toBeGreaterThanOrEqual(2);
  expect(screen.getByText("贵州茅台当前主要风险：短期波动放大。")).toBeInTheDocument();
  expect(screen.getByText("正在围绕 贵州茅台 SH.600519 追问")).toBeInTheDocument();
});

it("keeps separate left-side history conversations and switches between them", async () => {
  vi.stubGlobal("fetch", vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
    const parsed = JSON.parse(String(init?.body)) as { question: string };
    const isPingan = parsed.question.includes("平安银行");
    return {
      ok: true,
      status: 200,
      json: async () => ({
        ...stockAnswer,
        question: parsed.question,
        symbol: isPingan ? "SZ.000001" : "SH.600519",
        name: isPingan ? "平安银行" : "贵州茅台",
        answer: isPingan ? "平安银行估值不贵，但要看息差风险。" : "贵州茅台风险来自估值和需求节奏。",
        intent: isPingan ? "valuation" : "risk",
      }),
    };
  }));

  renderPage();
  expect(screen.getByLabelText("历史对话")).toHaveTextContent("新对话");
  submitAsk("贵州茅台现在主要风险是什么");
  expect(await screen.findByText("贵州茅台风险来自估值和需求节奏。")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "打开历史对话：贵州茅台现在主要风险是什么" })).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "新建问股对话" }));
  expect(screen.queryByText("贵州茅台风险来自估值和需求节奏。")).not.toBeInTheDocument();
  submitAsk("平安银行的估值贵不贵");
  expect(await screen.findByText("平安银行估值不贵，但要看息差风险。")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "打开历史对话：平安银行的估值贵不贵" })).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "打开历史对话：贵州茅台现在主要风险是什么" }));

  expect(screen.getByText("贵州茅台风险来自估值和需求节奏。")).toBeInTheDocument();
  expect(screen.queryByText("平安银行估值不贵，但要看息差风险。")).not.toBeInTheDocument();
  expect(screen.getByText("正在围绕 贵州茅台 SH.600519 追问")).toBeInTheDocument();
});

it("sends with Enter, keeps Shift Enter as a newline, and retries failed turns", async () => {
  const requests: string[] = [];
  let failed = false;
  vi.stubGlobal("fetch", vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
    const parsed = JSON.parse(String(init?.body)) as { question: string };
    requests.push(parsed.question);
    if (!failed) {
      failed = true;
      return { ok: false, status: 503, json: async () => ({ detail: "条件选股增强暂不可用；你也可以在问题中包含一个 A 股股票名称或代码继续分析。" }) };
    }
    return { ok: true, status: 200, json: async () => stockAnswer };
  }));

  renderPage();
  const input = screen.getByLabelText("继续追问");
  fireEvent.change(input, { target: { value: "低估值白酒股" } });
  fireEvent.keyDown(input, { key: "Enter", shiftKey: true });
  expect(input).toHaveValue("低估值白酒股");
  fireEvent.keyDown(input, { key: "Enter" });

  expect(await screen.findByRole("alert")).toHaveTextContent("条件选股增强暂不可用");
  expect(screen.queryByText(/问财/i)).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "重试" }));

  expect(await screen.findByText("贵州茅台当前主要风险：短期波动放大。")).toBeInTheDocument();
  expect(requests).toEqual(["低估值白酒股", "低估值白酒股"]);
});

it("renders personal holding context when the answer includes account data", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => ({
    ok: true,
    status: 200,
    json: async () => ({
      ...stockAnswer,
      answer: "贵州茅台当前建议为持有观察。结合你的账户持仓：当前持有 10 股。",
      metrics: [
        { label: "综合分", value: "72", tone: "positive" },
        { label: "建议动作", value: "持有观察", tone: "positive" },
        { label: "证据覆盖", value: "90%", tone: "positive" },
        { label: "置信度", value: "82%", tone: "positive" },
        { label: "持仓盈亏", value: "+7.14%", tone: "positive" },
        { label: "组合占比", value: "50%", tone: "neutral" },
      ],
      holding_context: {
        owned: true,
        quantity: 10,
        cost_price: 1400,
        market_value: 15000,
        pnl_pct: 7.14,
        portfolio_weight: 0.5,
        drift: 0,
        action: "hold",
        risk_flags: ["资金净流出"],
      },
    }),
  })));

  renderPage();
  fireEvent.change(screen.getByLabelText("继续追问"), { target: { value: "我持有的贵州茅台要减仓吗" } });
  fireEvent.click(screen.getByRole("button", { name: "发送" }));

  expect(await screen.findByLabelText("个人持仓上下文")).toHaveTextContent("数量 10 股");
  expect(screen.getByLabelText("个人持仓上下文")).toHaveTextContent("盈亏 +7.14%");
  fireEvent.click(screen.getByText("展开更多依据"));
  expect(screen.getByLabelText("回答关键指标")).toHaveTextContent("持仓盈亏+7.14%");
});

it("renders portfolio analysis rows with Stock Lab links", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => ({
    ok: true,
    status: 200,
    json: async () => ({
      ...stockAnswer,
      kind: "portfolio_analysis",
      intent: "portfolio",
      symbol: null,
      name: null,
      answer: "当前组合最需要先复核的是 贵州茅台（SH.600519）。",
      source: "账户持仓 + 本地行情快照 + 确定性分析",
      metrics: [
        { label: "持仓数量", value: "1", tone: "neutral" },
        { label: "总市值", value: "1.5 万", tone: "neutral" },
        { label: "最大单票", value: "50%", tone: "negative" },
        { label: "行业集中", value: "50%", tone: "neutral" },
        { label: "风险持仓", value: "1", tone: "negative" },
        { label: "最需复核", value: "贵州茅台", tone: "negative" },
      ],
      factors: [
        { label: "最大单票集中度", impact: -10, signal: "negative", evidence: "最大单票占比 50%，超过 35% 需要复核分散度。" },
      ],
      columns: ["股票代码", "股票简称", "行业", "组合占比", "目标仓位", "偏离", "盈亏", "动作", "风险"],
      rows: [{ 股票代码: "SH.600519", 股票简称: "贵州茅台", 行业: "白酒", 组合占比: "50%", 目标仓位: "30%", 偏离: "+20.0%", 盈亏: "-11.76%", 动作: "exit_watch", 风险: "亏损超过 10%" }],
    }),
  })));

  renderPage();
  fireEvent.change(screen.getByLabelText("继续追问"), { target: { value: "我的持仓里风险最大的是哪个" } });
  fireEvent.click(screen.getByRole("button", { name: "发送" }));

  expect(await screen.findByText("账户组合")).toBeInTheDocument();
  expect(screen.getByLabelText("回答关键指标")).toHaveTextContent("持仓数量1");
  expect(screen.getByLabelText("回答关键指标")).toHaveTextContent("最大单票50%");
  expect(screen.getByRole("link", { name: "SH.600519" })).toHaveAttribute("href", "#/stocks?symbol=SH.600519");
  expect(screen.getByRole("columnheader", { name: "目标仓位" })).toBeInTheDocument();
  expect(screen.getByRole("cell", { name: "+20.0%" })).toBeInTheDocument();
  expect(screen.getByText("最大单票集中度")).toBeInTheDocument();
  expect(screen.getByRole("cell", { name: "亏损超过 10%" })).toBeInTheDocument();
});

it("renders rebalance plan rows and priority evidence", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => ({
    ok: true,
    status: 200,
    json: async () => ({
      ...stockAnswer,
      kind: "portfolio_analysis",
      intent: "portfolio",
      symbol: null,
      name: null,
      answer: "调仓计划先处理 贵州茅台（SH.600519）：当前占比 54%，目标 20%，偏离金额 -1.0 万，建议股数 -8 股。",
      source: "账户持仓 + 本地行情快照 + 确定性分析",
      metrics: [
        { label: "持仓数量", value: "3", tone: "neutral" },
        { label: "总市值", value: "2 万", tone: "neutral" },
        { label: "需调仓", value: "3", tone: "negative" },
        { label: "净调整", value: "0", tone: "positive" },
        { label: "最大单票", value: "54%", tone: "negative" },
        { label: "行业集中", value: "54%", tone: "negative" },
        { label: "风险持仓", value: "3", tone: "negative" },
        { label: "最需复核", value: "贵州茅台", tone: "negative" },
      ],
      factors: [
        { label: "调仓执行量", impact: -6, signal: "negative", evidence: "3 个持仓偏离金额超过 1,000 元。" },
      ],
      columns: ["股票代码", "股票简称", "行业", "组合占比", "目标仓位", "偏离", "偏离金额", "建议股数", "优先级", "动作", "风险"],
      rows: [{ 股票代码: "SH.600519", 股票简称: "贵州茅台", 行业: "白酒", 组合占比: "54%", 目标仓位: "20%", 偏离: "+33.9%", 偏离金额: "-1.0 万", 建议股数: "-8 股", 优先级: "高", 动作: "exit_watch", 风险: "组合占比高于目标" }],
    }),
  })));

  renderPage();
  submitAsk("帮我生成调仓计划");

  expect(await screen.findByText(/调仓计划先处理/)).toBeInTheDocument();
  expect(screen.getByLabelText("回答关键指标")).toHaveTextContent("需调仓3");
  expect(screen.getByRole("columnheader", { name: "建议股数" })).toBeInTheDocument();
  expect(screen.getByRole("cell", { name: "-8 股" })).toBeInTheDocument();
  expect(screen.getByRole("cell", { name: "高" })).toBeInTheDocument();
  expect(screen.getByText("调仓执行量")).toBeInTheDocument();
});

it("renders bounded semantic screening rows", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => ({
    ok: true,
    status: 200,
    json: async () => ({
      ...stockAnswer,
      kind: "semantic_screen",
      intent: "screening",
      symbol: null,
      name: null,
      answer: "条件选股增强返回 1 个候选结果。",
      source: "条件选股增强（可选）",
      metrics: [
        { label: "候选数量", value: "1", tone: "neutral" },
        { label: "增强来源", value: "条件选股", tone: "neutral" },
      ],
      columns: ["股票代码", "股票简称", "市盈率"],
      rows: [{ 股票代码: "600519", 股票简称: "贵州茅台", 市盈率: 23 }],
    }),
  })));

  renderPage();
  fireEvent.change(screen.getByLabelText("继续追问"), { target: { value: "低估值白酒股" } });
  fireEvent.click(screen.getByRole("button", { name: "发送" }));

  expect(await screen.findByText("条件选股增强返回 1 个候选结果。")).toBeInTheDocument();
  expect(screen.getByLabelText("回答关键指标")).toHaveTextContent("候选数量1");
  expect(screen.getByLabelText("回答关键指标")).toHaveTextContent("增强来源条件选股");
  expect(screen.queryByText(/问财/i)).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: "600519" })).toHaveAttribute("href", "#/stocks?symbol=SH.600519");
  expect(screen.getByRole("columnheader", { name: "市盈率" })).toBeInTheDocument();
  expect(screen.getByRole("cell", { name: "贵州茅台" })).toBeInTheDocument();
});

it("renders a concise web LLM answer without deterministic review rails", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => ({
    ok: true,
    status: 200,
    json: async () => ({
      ...stockAnswer,
      kind: "llm_answer",
      intent: "overview",
      symbol: null,
      name: null,
      answer: "联网结论：白酒板块今天先看公告、消费数据和资金回流。",
      evidence: ["已检索最新公开信息。"],
      risks: ["信息仍可能滞后。"],
      next_actions: ["回到个股研究页复核。"],
      source: "联网大模型问答",
      metrics: [{ label: "回答模式", value: "联网问答", tone: "neutral" }],
    }),
  })));

  renderPage();
  fireEvent.change(screen.getByLabelText("继续追问"), { target: { value: "白酒板块今天怎么看" } });
  fireEvent.click(screen.getByRole("button", { name: "发送" }));

  expect(await screen.findByText("联网结论：白酒板块今天先看公告、消费数据和资金回流。")).toBeInTheDocument();
  expect(screen.getByText("联网大模型问答")).toBeInTheDocument();
  expect(screen.getByText("依据 / 风险 / 下一步")).toBeInTheDocument();
  expect(screen.queryByLabelText("回答关键指标")).not.toBeInTheDocument();
  expect(screen.queryByLabelText("问股复核路线")).not.toBeInTheDocument();
});

it("keeps the question and shows the backend unavailable detail", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => ({
    ok: false,
    status: 503,
    json: async () => ({ detail: "条件选股增强暂不可用；你也可以在问题中包含一个 A 股股票名称或代码继续分析。" }),
  })));

  renderPage();
  const input = screen.getByLabelText("继续追问");
  fireEvent.change(input, { target: { value: "低估值白酒股" } });
  fireEvent.click(screen.getByRole("button", { name: "发送" }));

  expect(await screen.findByRole("alert")).toHaveTextContent("条件选股增强暂不可用");
  expect(screen.queryByText(/问财/i)).not.toBeInTheDocument();
  await waitFor(() => expect(input).toHaveValue("低估值白酒股"));
});
