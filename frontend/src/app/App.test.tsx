import { render, screen } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";

import { App } from "./App";

const today = {
  meta: { source: "fixture", observed_at: "2026-07-19T01:00:00Z", fetched_at: "2026-07-19T01:01:00Z", freshness: "fresh", coverage: 0.96, errors: [] },
  analysis: { score: 58, regime: "balanced", confidence: 0.95, advancing: 3100, declining: 1900, unchanged: 100, factors: [] },
  indices: [{ symbol: "SH.000001", name: "上证指数", price: 3764.15, change_pct: -3.05, amount: 100 }],
  sectors: [{ code: "BK1", name: "机器人", change_pct: 2.8, net_flow: 100 }],
  top_opportunities: [], risk_budget: 60,
  next_actions: ["核对市场广度与指数趋势", "查看强势板块的持续性", "打开候选股证据链"],
};

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn(async () => ({ ok: true, json: async () => today })));
});

it("shows the market state, next actions, and data time", async () => {
  render(<App />);
  expect(await screen.findByText("市场状态")).toBeInTheDocument();
  expect(screen.getByText("今天先做什么")).toBeInTheDocument();
  expect(screen.getByText(/数据时间/)).toBeInTheDocument();
  expect(screen.getByRole("navigation", { name: "主导航" })).toBeInTheDocument();
});
