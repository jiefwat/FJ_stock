import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
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

const holdingRisk = {
  item: { id: 1, symbol: "SH.600519", name: "贵州茅台", quantity: 100, cost_price: 1400, target_weight: 0.4, thesis: "现金流稳定", invalidation: "跌破成本", status: "holding", created_at: "2026-07-18T09:00:00Z", updated_at: "2026-07-19T09:00:00Z" },
  quote: { symbol: "SH.600519", code: "600519", name: "贵州茅台", price: 1500, change_pct: 1.2, amount: 1, turnover_rate: 1, volume_ratio: null, pe: 23, pb: 7, market_cap: 1, net_flow: 80000000, sector: "白酒" },
  market_value: 150000,
  cost_value: 140000,
  pnl: 10000,
  pnl_pct: 7.14,
  day_pnl: 1780,
  day_pnl_pct: 1.2,
  five_day_pnl: -3200,
  five_day_pnl_pct: -2.09,
  portfolio_weight: 1,
  drift: 0.6,
  target_market_value: 60000,
  rebalance_value: -90000,
  rebalance_quantity: -60,
  break_even_price: 1400,
  price_gap_to_cost_pct: 7.14,
  analysis_dimensions: [],
  action: "trim",
  conclusion: "建议动作：减仓。仓位明显高于目标，先降回目标仓位。",
  risk_flags: ["组合占比高于目标"],
  next_actions: ["复核是否需要降仓"],
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
  expect(screen.getByRole("heading", { name: "登录 StockTS" })).toBeInTheDocument();
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
  const navigation = within(screen.getByRole("navigation", { name: "主导航" }));
  expect(navigation.getByRole("link", { name: "今日" })).toBeInTheDocument();
  expect(navigation.getByRole("link", { name: "持仓" })).toBeInTheDocument();
  expect(navigation.queryByRole("link", { name: "跟踪" })).not.toBeInTheDocument();
  expect(navigation.queryByRole("link", { name: "数据" })).not.toBeInTheDocument();
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

  expect(await screen.findByRole("heading", { name: "登录 StockTS" })).toBeInTheDocument();
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
  const openingDesk = within(await screen.findByLabelText("今日开盘执行台"));
  expect(openingDesk.getByText("今日")).toBeInTheDocument();
  expect(openingDesk.getByText("可以找机会")).toBeInTheDocument();
  expect(openingDesk.getByText("市场")).toBeInTheDocument();
  expect(openingDesk.getByText("机会")).toBeInTheDocument();
  expect(openingDesk.getByText("等待候选收敛")).toBeInTheDocument();
  expect(openingDesk.getByText("风险")).toBeInTheDocument();
  expect(openingDesk.getByRole("link", { name: /01\s*市场/ })).toHaveAttribute("href", "#/opportunities");
  expect(screen.getByRole("navigation", { name: "主导航" })).toBeInTheDocument();
  expect(calls[0]).toEqual({ url: "/api/v1/auth/me", auth: "Bearer token-existing" });
  fireEvent.click(screen.getByText("Owner"));
  fireEvent.click(screen.getByRole("button", { name: "退出账号" }));
  expect(screen.getByRole("heading", { name: "登录 StockTS" })).toBeInTheDocument();
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

it("adds a global research router for stock search and Ask Stock handoff", async () => {
  localStorage.setItem("marketdesk.accessToken", "token-command");
  const calls: Array<{ url: string; auth: string }> = [];
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const headers = new Headers(init?.headers);
    calls.push({ url, auth: headers.get("Authorization") ?? "" });
    if (url.includes("/api/v1/auth/me")) {
      return { ok: true, status: 200, json: async () => ({ id: 10, email: "command@example.com", display_name: "Command User", created_at: "2026-07-25T01:00:00Z", updated_at: "2026-07-25T01:00:00Z" }) };
    }
    if (url.includes("/api/v1/preferences")) {
      return { ok: true, status: 200, json: async () => ({ default_symbol: "SH.600519", start_page: "today", risk_profile: "balanced", morning_email_enabled: true }) };
    }
    if (url.includes("/api/v1/search")) {
      return { ok: true, status: 200, json: async () => [{ symbol: "SH.600519", code: "600519", name: "贵州茅台", price: 1500, change_pct: 1.2, amount: 100, turnover_rate: 1, volume_ratio: 1, pe: 24, pb: 8, market_cap: 1000, net_flow: 100, sector: "白酒" }] };
    }
    return { ok: true, status: 200, json: async () => url.includes("/api/v1/market-events") ? events : today };
  }));

  render(<App />);
  expect(await screen.findByText("市场状态")).toBeInTheDocument();
  fireEvent.keyDown(window, { key: "k", metaKey: true });
  const input = screen.getByLabelText("搜索股票或输入问题");
  expect(input).toHaveFocus();
  expect(screen.getByText("搜索")).toBeInTheDocument();
  fireEvent.change(input, { target: { value: "茅台" } });

  const stockResult = (await screen.findAllByRole("button", { name: /贵州茅台/ }))[0];
  expect(stockResult).toBeInTheDocument();
  expect(stockResult).toHaveTextContent("SH.600519");
  expect(stockResult).toHaveTextContent("白酒");
  expect(screen.getByRole("link", { name: "交给问股判断" })).toHaveAttribute("href", "#/ask?question=%E8%8C%85%E5%8F%B0");
  expect(calls.some((call) => call.url.includes("/api/v1/search?q=%E8%8C%85%E5%8F%B0") && call.auth === "Bearer token-command")).toBe(true);
});

it("shows recent research shortcuts in the global router", async () => {
  localStorage.setItem("marketdesk.accessToken", "token-recent");
  localStorage.setItem("marketdesk.recentResearch.v1.token-recent", JSON.stringify({
    version: 1,
    items: [{ symbol: "SH.600519", name: "贵州茅台", sector: "白酒", updatedAt: 1 }],
  }));
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes("/api/v1/auth/me")) {
      return { ok: true, status: 200, json: async () => ({ id: 11, email: "recent@example.com", display_name: "Recent User", created_at: "2026-07-25T01:00:00Z", updated_at: "2026-07-25T01:00:00Z" }) };
    }
    if (url.includes("/api/v1/preferences")) {
      return { ok: true, status: 200, json: async () => ({ default_symbol: "SH.600519", start_page: "today", risk_profile: "balanced", morning_email_enabled: true }) };
    }
    return { ok: true, status: 200, json: async () => url.includes("/api/v1/market-events") ? events : today };
  }));

  render(<App />);
  expect(await screen.findByText("市场状态")).toBeInTheDocument();
  fireEvent.focus(screen.getByLabelText("搜索股票或输入问题"));

  const recent = within(screen.getByLabelText("最近研究"));
  expect(recent.getByText("贵州茅台")).toBeInTheDocument();
  expect(recent.getByText("SH.600519")).toBeInTheDocument();
  expect(recent.getByRole("link", { name: "问风险" })).toHaveAttribute("href", "#/ask?symbol=SH.600519&name=%E8%B4%B5%E5%B7%9E%E8%8C%85%E5%8F%B0&question=%E8%B4%B5%E5%B7%9E%E8%8C%85%E5%8F%B0%E7%8E%B0%E5%9C%A8%E4%B8%BB%E8%A6%81%E9%A3%8E%E9%99%A9%E6%98%AF%E4%BB%80%E4%B9%88");
  expect(recent.getByRole("link", { name: "问异动" })).toHaveAttribute("href", "#/ask?symbol=SH.600519&name=%E8%B4%B5%E5%B7%9E%E8%8C%85%E5%8F%B0&question=%E6%9C%80%E8%BF%91%E8%B4%B5%E5%B7%9E%E8%8C%85%E5%8F%B0%E6%80%8E%E4%B9%88%E5%A4%A7%E8%B7%8C");
});

it("surfaces recent research on the Today desk", async () => {
  localStorage.setItem("marketdesk.accessToken", "today-recent");
  localStorage.setItem("marketdesk.recentResearch.v1.today-recent", JSON.stringify({
    version: 1,
    items: [{ symbol: "SH.600519", name: "贵州茅台", sector: "白酒", updatedAt: 1 }],
  }));
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes("/api/v1/auth/me")) {
      return { ok: true, status: 200, json: async () => ({ id: 12, email: "today@example.com", display_name: "Today User", created_at: "2026-07-25T01:00:00Z", updated_at: "2026-07-25T01:00:00Z" }) };
    }
    if (url.includes("/api/v1/preferences")) {
      return { ok: true, status: 200, json: async () => ({ default_symbol: "SH.600519", start_page: "today", risk_profile: "balanced", morning_email_enabled: true }) };
    }
    return { ok: true, status: 200, json: async () => url.includes("/api/v1/market-events") ? events : today };
  }));

  render(<App />);

  const continueDesk = within(await screen.findByLabelText("继续研究"));
  expect(continueDesk.getByText("CONTINUE")).toBeInTheDocument();
  expect(continueDesk.getByRole("link", { name: /贵州茅台/ })).toHaveAttribute("href", "#/stocks?symbol=SH.600519#stock-final-gate");
  expect(continueDesk.getByRole("link", { name: "问风险" })).toHaveAttribute("href", "#/ask?symbol=SH.600519&name=%E8%B4%B5%E5%B7%9E%E8%8C%85%E5%8F%B0&from=today&question=%E8%B4%B5%E5%B7%9E%E8%8C%85%E5%8F%B0%E7%8E%B0%E5%9C%A8%E4%B8%BB%E8%A6%81%E9%A3%8E%E9%99%A9%E6%98%AF%E4%BB%80%E4%B9%88");
  expect(continueDesk.getByRole("link", { name: "问异动" })).toHaveAttribute("href", "#/ask?symbol=SH.600519&name=%E8%B4%B5%E5%B7%9E%E8%8C%85%E5%8F%B0&from=today&question=%E6%9C%80%E8%BF%91%E8%B4%B5%E5%B7%9E%E8%8C%85%E5%8F%B0%E6%80%8E%E4%B9%88%E5%A4%A7%E8%B7%8C");
  expect(continueDesk.getByRole("link", { name: "问基本面" })).toHaveAttribute("href", "#/ask?symbol=SH.600519&name=%E8%B4%B5%E5%B7%9E%E8%8C%85%E5%8F%B0&from=today&question=%E8%B4%B5%E5%B7%9E%E8%8C%85%E5%8F%B0%E5%9F%BA%E6%9C%AC%E9%9D%A2%E6%80%8E%E4%B9%88%E6%A0%B7");
});

it("shows a holdings risk sentinel on Today when positions need action", async () => {
  localStorage.setItem("marketdesk.accessToken", "token-holding-risk");
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes("/api/v1/auth/me")) {
      return { ok: true, status: 200, json: async () => ({ id: 13, email: "risk@example.com", display_name: "Risk User", created_at: "2026-07-25T01:00:00Z", updated_at: "2026-07-25T01:00:00Z" }) };
    }
    if (url.includes("/api/v1/preferences")) {
      return { ok: true, status: 200, json: async () => ({ default_symbol: "SH.600519", start_page: "today", risk_profile: "balanced", morning_email_enabled: true }) };
    }
    if (url.includes("/api/v1/holdings")) {
      return { ok: true, status: 200, json: async () => [holdingRisk] };
    }
    return { ok: true, status: 200, json: async () => url.includes("/api/v1/market-events") ? events : today };
  }));

  render(<App />);

  const sentinel = within(await screen.findByLabelText("持仓风险哨兵"));
  expect(sentinel.getByText("持仓风险")).toBeInTheDocument();
  expect(sentinel.getByText("贵州茅台")).toBeInTheDocument();
  expect(sentinel.getByText("组合占比高于目标")).toBeInTheDocument();
  expect(sentinel.getByText(/需要减仓 · 待处理 1 笔/)).toBeInTheDocument();
  expect(sentinel.getByText("150,000")).toBeInTheDocument();
  expect(sentinel.getByText("10,000")).toBeInTheDocument();
  expect(sentinel.getByText("+7.14%")).toBeInTheDocument();
  expect(sentinel.getByRole("link", { name: "处理持仓" })).toHaveAttribute("href", "#/holdings");
  expect(sentinel.getByRole("link", { name: "看个股" })).toHaveAttribute("href", "#/stocks?symbol=SH.600519#stock-final-gate");
  expect(sentinel.getByRole("link", { name: "问持仓" })).toHaveAttribute("href", "#/ask?symbol=SH.600519&name=%E8%B4%B5%E5%B7%9E%E8%8C%85%E5%8F%B0&from=today&question=%E6%88%91%E7%9A%84%E6%8C%81%E4%BB%93%E9%87%8C%E8%B4%B5%E5%B7%9E%E8%8C%85%E5%8F%B0%E9%A3%8E%E9%99%A9%E6%80%8E%E4%B9%88%E5%A4%84%E7%90%86%EF%BC%8C%E8%A6%81%E4%B8%8D%E8%A6%81%E8%B0%83%E4%BB%93");
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

  expect(await screen.findByRole("heading", { name: "问股" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "问股" })).toHaveClass("active");
});
