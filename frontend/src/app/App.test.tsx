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
  window.location.hash = "";
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

it("keeps the application unmounted before login", () => {
  const requests: string[] = [];
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    requests.push(String(input));
    return { ok: true, status: 200, json: async () => today };
  }));

  render(<App />);
  expect(screen.getByRole("heading", { name: "登录 Market Desk" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "登录" })).toBeInTheDocument();
  expect(screen.queryByRole("navigation", { name: "主导航" })).not.toBeInTheDocument();
  expect(screen.queryByText("市场状态")).not.toBeInTheDocument();
  expect(requests).toEqual([]);
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
  fireEvent.click(screen.getByRole("button", { name: "注册新账号" }));
  fireEvent.change(screen.getByLabelText("邮箱"), { target: { value: "alpha@example.com" } });
  fireEvent.change(screen.getByLabelText("昵称"), { target: { value: "Alpha" } });
  fireEvent.change(screen.getByLabelText("密码"), { target: { value: "Passw0rd-alpha" } });
  fireEvent.click(screen.getByRole("button", { name: "创建账号" }));

  expect(await screen.findByText("Alpha")).toBeInTheDocument();
  expect(screen.getByRole("navigation", { name: "主导航" })).toBeInTheDocument();
  await waitFor(() => {
    expect(calls.some((call) => call.url.includes("/api/v1/preferences") && call.auth === "Bearer token-alpha")).toBe(true);
    expect(calls.some((call) => call.url.includes("/api/v1/today") && call.auth === "Bearer token-alpha")).toBe(true);
  });
});

it("rejects an expired session without mounting business routes", async () => {
  localStorage.setItem("marketdesk.accessToken", "expired-token");
  const calls: string[] = [];
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    calls.push(url);
    return { ok: false, status: 401, json: async () => ({ detail: "invalid or expired token" }) };
  }));

  render(<App />);

  expect(await screen.findByRole("heading", { name: "登录 Market Desk" })).toBeInTheDocument();
  expect(screen.queryByRole("navigation", { name: "主导航" })).not.toBeInTheDocument();
  expect(calls).toEqual(["/api/v1/auth/me"]);
  expect(localStorage.getItem("marketdesk.accessToken")).toBeNull();
});

it("restores a valid session and removes the shell on logout", async () => {
  localStorage.setItem("marketdesk.accessToken", "token-existing");
  const calls: Array<{ url: string; auth: string }> = [];
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const headers = new Headers(init?.headers);
    calls.push({ url, auth: headers.get("Authorization") ?? "" });
    if (url.includes("/api/v1/auth/me")) {
      return { ok: true, status: 200, json: async () => ({ id: 7, email: "owner@example.com", display_name: "Owner", created_at: "2026-07-25T01:00:00Z", updated_at: "2026-07-25T01:00:00Z" }) };
    }
    if (url.includes("/api/v1/preferences")) {
      return { ok: true, status: 200, json: async () => ({ default_symbol: "SH.600519", start_page: "today", risk_profile: "balanced", morning_email_enabled: true }) };
    }
    if (url.includes("/api/v1/auth/logout")) {
      return { ok: true, status: 204, json: async () => ({}) };
    }
    return { ok: true, status: 200, json: async () => url.includes("/api/v1/market-events") ? events : today };
  }));

  render(<App />);

  expect(await screen.findByText("市场状态")).toBeInTheDocument();
  expect(screen.getByRole("navigation", { name: "主导航" })).toBeInTheDocument();
  expect(calls[0]).toEqual({ url: "/api/v1/auth/me", auth: "Bearer token-existing" });
  fireEvent.click(screen.getByText("Owner"));
  fireEvent.click(screen.getByRole("button", { name: "退出账号" }));
  expect(screen.getByRole("heading", { name: "登录 Market Desk" })).toBeInTheDocument();
  expect(screen.queryByRole("navigation", { name: "主导航" })).not.toBeInTheDocument();
  expect(localStorage.getItem("marketdesk.accessToken")).toBeNull();
});

it("shows market observation time separately from the latest refresh time", async () => {
  localStorage.setItem("marketdesk.accessToken", "token-refresh");
  let refreshed = false;
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.includes("/api/v1/auth/me")) {
      return { ok: true, status: 200, json: async () => ({ id: 9, email: "refresh@example.com", display_name: "Refresh User", created_at: "2026-07-25T01:00:00Z", updated_at: "2026-07-25T01:00:00Z" }) };
    }
    if (url.includes("/api/v1/preferences")) {
      return { ok: true, status: 200, json: async () => ({ default_symbol: "SH.600519", start_page: "today", risk_profile: "balanced", morning_email_enabled: true }) };
    }
    if (url.includes("/api/v1/refresh") && init?.method === "POST") {
      refreshed = true;
      return { ok: true, status: 200, json: async () => ({ status: "ok", meta: { ...today.meta, fetched_at: "2030-01-02T03:04:05Z" } }) };
    }
    if (url.includes("/api/v1/market-events")) {
      return { ok: true, status: 200, json: async () => events };
    }
    return {
      ok: true,
      status: 200,
      json: async () => ({
        ...today,
        meta: { ...today.meta, fetched_at: refreshed ? "2030-01-02T03:04:05Z" : today.meta.fetched_at },
      }),
    };
  }));

  render(<App />);

  expect(await screen.findByText(/行情时间/)).toBeInTheDocument();
  expect(screen.getByText(/更新/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "刷新" }));

  await waitFor(() => expect(screen.getByText(/2030/)).toBeInTheDocument());
  expect(screen.getByText(/行情时间/)).toBeInTheDocument();
});

it("keeps the Ask Stock route behind the authenticated shell", async () => {
  localStorage.setItem("marketdesk.accessToken", "token-ask-route");
  window.location.hash = "#/ask";
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes("/api/v1/auth/me")) {
      return { ok: true, status: 200, json: async () => ({ id: 8, email: "ask@example.com", display_name: "Ask User", created_at: "2026-07-25T01:00:00Z", updated_at: "2026-07-25T01:00:00Z" }) };
    }
    if (url.includes("/api/v1/preferences")) {
      return { ok: true, status: 200, json: async () => ({ default_symbol: "SH.600519", start_page: "today", risk_profile: "balanced", morning_email_enabled: true }) };
    }
    return { ok: true, status: 200, json: async () => today };
  }));

  render(<App />);

  expect(await screen.findByRole("heading", { name: "问股对话" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "问股" })).toHaveClass("active");
});
