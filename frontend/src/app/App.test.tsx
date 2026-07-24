import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

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
  const storage = new Map<string, string>();
  vi.stubGlobal("localStorage", {
    getItem: (key: string) => storage.get(key) ?? null,
    setItem: (key: string, value: string) => storage.set(key, value),
    removeItem: (key: string) => storage.delete(key),
    clear: () => storage.clear(),
  });
  localStorage.clear();
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    return { ok: true, json: async () => url.includes("/api/v1/market-events") ? events : today };
  }));
});

afterEach(() => {
  cleanup();
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

it("registers a user and sends the auth token with personal requests", async () => {
  const calls: Array<{ url: string; auth: string }> = [];
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const headers = new Headers(init?.headers);
    calls.push({ url, auth: headers.get("Authorization") ?? "" });
    if (url.includes("/api/v1/auth/me")) {
      return { ok: false, status: 401, json: async () => ({ detail: "missing" }) };
    }
    if (url.includes("/api/v1/auth/register")) {
      return {
        ok: true,
        status: 201,
        json: async () => ({
          access_token: "token-alpha",
          token_type: "bearer",
          user: {
            id: 2,
            email: "alpha@example.com",
            display_name: "Alpha",
            created_at: "2026-07-21T01:00:00Z",
            updated_at: "2026-07-21T01:00:00Z",
          },
        }),
      };
    }
    if (url.includes("/api/v1/preferences")) {
      return {
        ok: true,
        status: 200,
        json: async () => ({
          default_symbol: "SH.600519",
          start_page: "today",
          risk_profile: "balanced",
          morning_email_enabled: true,
        }),
      };
    }
    return { ok: true, status: 200, json: async () => url.includes("/api/v1/market-events") ? events : today };
  }));

  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: "注册/登录" }));
  fireEvent.click(screen.getByRole("button", { name: "注册新账号" }));
  fireEvent.change(screen.getByLabelText("邮箱"), { target: { value: "alpha@example.com" } });
  fireEvent.change(screen.getByLabelText("昵称"), { target: { value: "Alpha" } });
  fireEvent.change(screen.getByLabelText("密码"), { target: { value: "Passw0rd-alpha" } });
  fireEvent.click(screen.getByRole("button", { name: "创建账号" }));

  expect(await screen.findByText("Alpha")).toBeInTheDocument();
  await waitFor(() => {
    expect(calls.some((call) => call.url.includes("/api/v1/preferences") && call.auth === "Bearer token-alpha")).toBe(true);
  });
});

it("does not expose the default portfolio before login", async () => {
  window.location.hash = "#/holdings";
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes("/api/v1/holdings")) {
      return { ok: false, status: 401, json: async () => ({ detail: "authentication required" }) };
    }
    return { ok: true, status: 200, json: async () => today };
  }));

  render(<App />);

  expect(await screen.findByText("请先登录后查看个人持仓")).toBeInTheDocument();
  expect(screen.queryByRole("list", { name: "持仓清单" })).not.toBeInTheDocument();
});
