import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
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
  observed_at: "2026-07-25T01:00:00Z",
  source: "本地行情快照 + 确定性分析",
  disclaimer: "研究辅助信息，不构成投资建议。",
  columns: [],
  rows: [],
};

function renderPage() {
  const client = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
  return render(<QueryClientProvider client={client}><AskStockPage /></QueryClientProvider>);
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
  expect(screen.getByRole("heading", { name: "问股对话" })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "贵州茅台现在主要风险是什么" }));

  await waitFor(() => expect(screen.getAllByText("贵州茅台现在主要风险是什么").length).toBeGreaterThanOrEqual(2));
  expect(await screen.findByText("贵州茅台当前主要风险：短期波动放大。")).toBeInTheDocument();
  expect(screen.getByText("SH.600519")).toBeInTheDocument();
  expect(screen.getByText("价格仍在 MA20 上方")).toBeInTheDocument();
  expect(screen.getByText("短期波动放大")).toBeInTheDocument();
  expect(screen.getByText("等待下一交易日确认")).toBeInTheDocument();
  expect(screen.getByText("本地行情快照 + 确定性分析")).toBeInTheDocument();
  expect(screen.getByText("研究辅助信息，不构成投资建议。")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "打开个股研究" })).toHaveAttribute("href", "#/stocks?symbol=SH.600519");
  expect(screen.getByRole("button", { name: "继续问估值" })).toBeInTheDocument();
  expect(requests).toEqual([{
    body: JSON.stringify({ question: "贵州茅台现在主要风险是什么" }),
    auth: "Bearer token-ask",
  }]);
});

it("keeps multiple turns and carries the previous stock into a follow-up", async () => {
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
        answer: parsed.question.includes("估值") ? "贵州茅台估值处于合理偏高区间。" : stockAnswer.answer,
        intent: parsed.question.includes("估值") ? "valuation" : "risk",
      }),
    };
  }));

  renderPage();
  fireEvent.click(screen.getByRole("button", { name: "贵州茅台现在主要风险是什么" }));
  expect(await screen.findByText("贵州茅台当前主要风险：短期波动放大。")).toBeInTheDocument();

  fireEvent.change(screen.getByLabelText("继续追问"), { target: { value: "那估值呢" } });
  fireEvent.click(screen.getByRole("button", { name: "发送" }));

  expect(await screen.findByText("贵州茅台估值处于合理偏高区间。")).toBeInTheDocument();
  expect(screen.getByText("那估值呢")).toBeInTheDocument();
  expect(screen.getByText("沿用上文：贵州茅台 SH.600519")).toBeInTheDocument();
  expect(requests).toEqual(["贵州茅台现在主要风险是什么", "贵州茅台 那估值呢"]);
});

it("restores the current tab conversation for the same session", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => ({ ok: true, status: 200, json: async () => stockAnswer })));

  const { unmount } = renderPage();
  fireEvent.click(screen.getByRole("button", { name: "贵州茅台现在主要风险是什么" }));
  expect(await screen.findByText("贵州茅台当前主要风险：短期波动放大。")).toBeInTheDocument();
  unmount();

  renderPage();
  expect(screen.getAllByText("贵州茅台现在主要风险是什么").length).toBeGreaterThanOrEqual(2);
  expect(screen.getByText("贵州茅台当前主要风险：短期波动放大。")).toBeInTheDocument();
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
      return { ok: false, status: 503, json: async () => ({ detail: "问财筛选暂不可用，请在问题中包含一个 A 股股票名称或代码。" }) };
    }
    return { ok: true, status: 200, json: async () => stockAnswer };
  }));

  renderPage();
  const input = screen.getByLabelText("继续追问");
  fireEvent.change(input, { target: { value: "低估值白酒股" } });
  fireEvent.keyDown(input, { key: "Enter", shiftKey: true });
  expect(input).toHaveValue("低估值白酒股");
  fireEvent.keyDown(input, { key: "Enter" });

  expect(await screen.findByRole("alert")).toHaveTextContent("问财筛选暂不可用");
  fireEvent.click(screen.getByRole("button", { name: "重试" }));

  expect(await screen.findByText("贵州茅台当前主要风险：短期波动放大。")).toBeInTheDocument();
  expect(requests).toEqual(["低估值白酒股", "低估值白酒股"]);
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
      answer: "问财语义筛选返回 1 个候选结果。",
      source: "问财语义筛选（可选增强）",
      columns: ["股票代码", "股票简称", "市盈率"],
      rows: [{ 股票代码: "600519", 股票简称: "贵州茅台", 市盈率: 23 }],
    }),
  })));

  renderPage();
  fireEvent.change(screen.getByLabelText("继续追问"), { target: { value: "低估值白酒股" } });
  fireEvent.click(screen.getByRole("button", { name: "发送" }));

  expect(await screen.findByText("问财语义筛选返回 1 个候选结果。")).toBeInTheDocument();
  expect(screen.getByRole("columnheader", { name: "市盈率" })).toBeInTheDocument();
  expect(screen.getByRole("cell", { name: "贵州茅台" })).toBeInTheDocument();
});

it("keeps the question and shows the backend unavailable detail", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => ({
    ok: false,
    status: 503,
    json: async () => ({ detail: "问财筛选暂不可用，请在问题中包含一个 A 股股票名称或代码。" }),
  })));

  renderPage();
  const input = screen.getByLabelText("继续追问");
  fireEvent.change(input, { target: { value: "低估值白酒股" } });
  fireEvent.click(screen.getByRole("button", { name: "发送" }));

  expect(await screen.findByRole("alert")).toHaveTextContent("问财筛选暂不可用");
  await waitFor(() => expect(input).toHaveValue("低估值白酒股"));
});
