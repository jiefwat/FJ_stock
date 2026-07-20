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

const events = {
  meta: { source: "eastmoney_fast_news", observed_at: "2026-07-19T14:00:00Z", fetched_at: "2026-07-19T14:01:00Z", freshness: "fresh", coverage: 1, errors: [] },
  summary: ["央企改革与银行风格成为今天市场热点。"],
  next_actions: ["打开关联板块检查资金持续性"],
  clusters: [{ key: "policy_support", label: "政策与监管", signal: "positive", count: 1, summary: "央企增持维护市场稳定", hot_score: 86 }],
  events: [{ id: "e1", title: "两家央企宣布增持", summary: "央企继续增持股票资产。", source: "东方财富快讯", url: "https://finance.eastmoney.com/a/e1.html", published_at: "2026-07-19T13:30:00Z", related_symbols: [], related_sectors: ["央企改革"], category: "policy_support", sentiment: "positive", importance_score: 86, tags: ["央企改革"], impact: "稳定风险偏好。", action: "检查央企改革板块。" }],
};

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    return { ok: true, json: async () => url.includes("/api/v1/market-events") ? events : today };
  }));
});

it("shows the market state, next actions, and data time", async () => {
  render(<App />);
  expect(await screen.findByText("市场状态")).toBeInTheDocument();
  expect(screen.getByText("今天先做什么")).toBeInTheDocument();
  expect(screen.getByText("今日市场异动")).toBeInTheDocument();
  expect(screen.getByText("两家央企宣布增持")).toBeInTheDocument();
  expect(screen.getByText("今日投研路线图")).toBeInTheDocument();
  expect(screen.getByText("先看主线")).toBeInTheDocument();
  expect(screen.getByText("风险哨兵")).toBeInTheDocument();
  expect(screen.getByText("复盘清单")).toBeInTheDocument();
  expect(screen.getByText(/数据时间/)).toBeInTheDocument();
  expect(screen.getByRole("navigation", { name: "主导航" })).toBeInTheDocument();
});
