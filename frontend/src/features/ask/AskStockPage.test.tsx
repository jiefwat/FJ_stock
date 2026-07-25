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
  vi.stubGlobal("localStorage", {
    getItem: (key: string) => storage.get(key) ?? null,
    setItem: (key: string, value: string) => storage.set(key, value),
    removeItem: (key: string) => storage.delete(key),
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
  expect(screen.getByRole("heading", { name: "用问题开始研究" })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "贵州茅台现在主要风险是什么" }));

  expect(await screen.findByText("贵州茅台当前主要风险：短期波动放大。")).toBeInTheDocument();
  expect(screen.getByText("SH.600519")).toBeInTheDocument();
  expect(screen.getByText("价格仍在 MA20 上方")).toBeInTheDocument();
  expect(screen.getByText("短期波动放大")).toBeInTheDocument();
  expect(screen.getByText("等待下一交易日确认")).toBeInTheDocument();
  expect(screen.getByText("本地行情快照 + 确定性分析")).toBeInTheDocument();
  expect(screen.getByText("研究辅助信息，不构成投资建议。")).toBeInTheDocument();
  expect(requests).toEqual([{
    body: JSON.stringify({ question: "贵州茅台现在主要风险是什么" }),
    auth: "Bearer token-ask",
  }]);
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
  fireEvent.change(screen.getByLabelText("输入你的股票问题"), { target: { value: "低估值白酒股" } });
  fireEvent.click(screen.getByRole("button", { name: "开始分析" }));

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
  const input = screen.getByLabelText("输入你的股票问题");
  fireEvent.change(input, { target: { value: "低估值白酒股" } });
  fireEvent.click(screen.getByRole("button", { name: "开始分析" }));

  expect(await screen.findByRole("alert")).toHaveTextContent("问财筛选暂不可用");
  await waitFor(() => expect(input).toHaveValue("低估值白酒股"));
});
