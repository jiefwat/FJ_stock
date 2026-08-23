import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";

import { RecommendationHistoryPage } from "./RecommendationHistoryPage";

const fixture = {
  preset: "trend",
  generated_at: "2026-08-15T08:00:00Z",
  first_tracking_date: "2026-07-15",
  last_observed_at: "2026-08-15T07:00:00Z",
  summary: {
    run_count: 12,
    pick_count: 30,
    evaluated_count: 9,
    average_20d_return: 6.4,
    hit_rate_20d: 0.667,
    benchmark_win_rate_20d: 0.556,
    average_20d_excess: 3.1,
    average_current_return: 4.8,
    current_positive_rate: 0.6,
  },
  days: [{
    preset: "trend",
    trading_date: "2026-07-15",
    observed_at: "2026-07-15T07:00:00Z",
    available: true,
    unavailable_reason: null,
    summary: "趋势延续线索已冻结。",
    picks: [{
      rank: 1,
      symbol: "SZ.300750",
      name: "宁德时代",
      sector: "电池",
      entry_price: 218.6,
      current_price: 236.8,
      score: 88,
      evidence_coverage: 0.86,
      thesis: "价格、资金与历史趋势同时确认。",
      risk_flags: [],
      observed_sessions: 20,
      return_1d: 1.2,
      return_5d: 4.6,
      return_20d: 8.33,
      current_return: 8.33,
      benchmark_20d_return: 2.1,
      excess_20d_return: 6.23,
      current_benchmark_return: 2.1,
      current_excess_return: 6.23,
      peak_return: 11.2,
      max_drawdown: -3.4,
      status: "evaluated",
    }],
  }],
  methodology: [
    "每天每个策略只冻结一次前 3 只候选及当时价格。",
    "T+1、T+5、T+20 按交易日计算。",
    "20 日命中表示区间收益大于 0。",
    "统计从本功能首次启用后开始。",
  ],
};

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("shows immutable daily picks with fixed-window and benchmark performance", async () => {
  const fetchMock = vi.fn(async () => ({ ok: true, status: 200, json: async () => fixture }));
  vi.stubGlobal("fetch", fetchMock);
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });

  render(<QueryClientProvider client={client}><MemoryRouter><RecommendationHistoryPage /></MemoryRouter></QueryClientProvider>);

  expect(screen.getByRole("heading", { name: "推荐复盘" })).toBeInTheDocument();
  const overview = within(await screen.findByLabelText("历史推荐总览"));
  expect(overview.getByText("继续观察")).toBeInTheDocument();
  expect(overview.getByText("正式命中率 67%")).toBeInTheDocument();
  expect(overview.getByText("+6.40%")).toBeInTheDocument();
  expect(within(screen.getByLabelText("复盘收益分布")).getByText("正收益 1")).toBeInTheDocument();
  expect(screen.getByText("20日已验收")).toBeInTheDocument();
  expect(screen.getByLabelText("宁德时代 固定周期表现")).toHaveTextContent("T+1+1.20%T+5+4.60%T+20+8.33%至今+8.33%");
  expect(screen.getByText("+6.23%")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "宁德时代" })).toHaveAttribute("href", "/stocks?symbol=SZ.300750#stock-final-gate");
  expect(fetchMock).toHaveBeenCalledWith("/api/v1/recommendation-history?preset=trend&limit=90", expect.any(Object));
  expect(fetchMock).toHaveBeenCalledTimes(1);

  fireEvent.pointerEnter(screen.getByRole("button", { name: "资金确认" }));
  await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/v1/recommendation-history?preset=capital_confirmed&limit=90", expect.any(Object)));
  expect(fetchMock).toHaveBeenCalledTimes(2);

  fireEvent.click(screen.getByRole("button", { name: "资金确认" }));
  expect(await screen.findByText("价格、资金与历史趋势同时确认。")).toBeInTheDocument();
});

it("shows recommendation days progressively instead of rendering the full history", async () => {
  const days = Array.from({ length: 7 }, (_, index) => ({
    ...fixture.days[0],
    trading_date: `2026-07-${String(21 - index).padStart(2, "0")}`,
    picks: fixture.days[0].picks.map((pick) => ({
      ...pick,
      symbol: `SZ.${String(300750 + index).padStart(6, "0")}`,
      name: `复盘样本${index + 1}`,
    })),
  }));
  vi.stubGlobal("fetch", vi.fn(async () => ({
    ok: true,
    status: 200,
    json: async () => ({ ...fixture, days }),
  })));
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });

  render(<QueryClientProvider client={client}><MemoryRouter><RecommendationHistoryPage /></MemoryRouter></QueryClientProvider>);

  expect(await screen.findByText("复盘样本6")).toBeInTheDocument();
  expect(screen.queryByText("复盘样本7")).not.toBeInTheDocument();
  expect(screen.getByText("已显示最近 6 / 7 个交易日")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "再显示 1 天" }));
  expect(screen.getByText("复盘样本7")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "收起到最近 6 天" }));
  expect(screen.queryByText("复盘样本7")).not.toBeInTheDocument();
});
