import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";

import { WatchlistPage } from "./WatchlistPage";

afterEach(() => vi.unstubAllGlobals());

it("edits and saves an auditable research note", async () => {
  const item = { id: 1, symbol: "SH.600519", name: "贵州茅台", thesis: "现金流稳定", invalidation: "趋势破位", status: "researching", created_at: "2026-07-18T09:00:00Z", updated_at: "2026-07-19T09:00:00Z" };
  const bars = [
    { date: "2026-07-17", close: 1600 },
    { date: "2026-07-18", close: 1620 },
    { date: "2026-07-19", close: 1612 },
  ];
  vi.stubGlobal("fetch", vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(_input);
    if (init?.method === "PATCH") {
      const body = JSON.parse(String(init.body));
      return { ok: true, status: 200, json: async () => ({ ...item, ...body, updated_at: "2026-07-19T10:00:00Z" }) };
    }
    if (path.includes("/api/v1/stocks/SH.600519")) {
      return { ok: true, status: 200, json: async () => ({ quote: { symbol: "SH.600519", name: "贵州茅台", price: 1612 }, bars }) };
    }
    return { ok: true, status: 200, json: async () => [item] };
  }));
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });

  render(<QueryClientProvider client={client}><MemoryRouter><WatchlistPage /></MemoryRouter></QueryClientProvider>);

  expect(await screen.findByText("跟踪清单")).toBeInTheDocument();
  expect(screen.getByText(/没买或还没决定买/)).toBeInTheDocument();
  expect(screen.getByText("跟踪不是买入信号")).toBeInTheDocument();
  expect(screen.getByText("先放进来")).toBeInTheDocument();
  expect(await screen.findByText("加入跟踪后的走势")).toBeInTheDocument();
  expect(await screen.findByRole("img", { name: "价格趋势图" })).toBeInTheDocument();
  expect(screen.getByText("加入跟踪")).toBeInTheDocument();
  expect(screen.getByText(/圆点为加入跟踪日/)).toBeInTheDocument();
  expect(screen.getByText(/跟踪后表现/)).toBeInTheDocument();
  expect(await screen.findByRole("link", { name: "贵州茅台" })).toHaveAttribute("href", "/stocks?symbol=SH.600519&from=watchlist#stock-final-gate");
  expect(screen.getByRole("link", { name: "打开完整个股分析" })).toHaveAttribute("href", "/stocks?symbol=SH.600519&from=watchlist#stock-final-gate");
  const actions = within(screen.getByLabelText("贵州茅台 跟踪复核动作"));
  expect(actions.getByRole("link", { name: "复核 FINAL GATE" })).toHaveAttribute("href", "/stocks?symbol=SH.600519&from=watchlist#stock-final-gate");
  expect(actions.getByRole("link", { name: "问是否继续跟" })).toHaveAttribute("href", "/ask?symbol=SH.600519&name=%E8%B4%B5%E5%B7%9E%E8%8C%85%E5%8F%B0&from=watchlist&question=%E8%B4%B5%E5%B7%9E%E8%8C%85%E5%8F%B0%E8%BF%98%E5%80%BC%E5%BE%97%E7%BB%A7%E7%BB%AD%E8%B7%9F%E8%B8%AA%E5%90%97");
  expect(actions.getByRole("link", { name: "问失效条件" })).toHaveAttribute("href", "/ask?symbol=SH.600519&name=%E8%B4%B5%E5%B7%9E%E8%8C%85%E5%8F%B0&from=watchlist&question=%E8%B4%B5%E5%B7%9E%E8%8C%85%E5%8F%B0%E8%BF%99%E6%9D%A1%E8%B7%9F%E8%B8%AA%E8%AE%B0%E5%BD%95%E7%9A%84%E5%A4%B1%E6%95%88%E6%9D%A1%E4%BB%B6%E6%98%AF%E4%BB%80%E4%B9%88");
  fireEvent.change(screen.getByLabelText("关注理由 贵州茅台"), { target: { value: "等待估值回落" } });
  fireEvent.click(screen.getByRole("button", { name: "保存跟踪记录" }));

  expect(await screen.findByText("已保存")).toBeInTheDocument();
});
