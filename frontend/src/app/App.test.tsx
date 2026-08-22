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

const market = {
  snapshot: {
    meta: today.meta,
    indices: today.indices,
    sectors: today.sectors,
  },
  analysis: today.analysis,
};

const events = {
  meta: { source: "eastmoney_fast_news", observed_at: "2026-07-19T14:00:00Z", fetched_at: "2026-07-19T14:01:00Z", freshness: "fresh", coverage: 1, errors: [] },
  summary: ["央企改革与银行风格成为今天市场热点。"],
  next_actions: ["打开关联板块检查资金持续性"],
  clusters: [{ key: "policy_support", label: "政策与监管", signal: "positive", count: 1, summary: "央企增持维护市场稳定", hot_score: 86 }],
  events: [{ id: "e1", title: "两家央企宣布增持", summary: "央企继续增持股票资产。", source: "东方财富快讯", url: "https://finance.eastmoney.com/a/e1.html", published_at: "2026-07-19T13:30:00Z", related_symbols: [], related_sectors: ["央企改革"], category: "policy_support", sentiment: "positive", importance_score: 86, tags: ["央企改革"], impact: "稳定风险偏好。", action: "检查央企改革板块。" }],
};

const intelligence = {
  meta: today.meta,
  sector_flows: today.sectors,
  anomalies: [],
  capabilities: {},
};

const equityPage = {
  meta: today.meta,
  total: 1,
  page: 1,
  page_size: 25,
  exchange: "all",
  sort_by: "amount",
  direction: "desc",
  available_sectors: ["机器人"],
  items: [{
    symbol: "SH.600519",
    code: "600519",
    name: "贵州茅台",
    price: 1500,
    change_pct: 1.2,
    amount: 100,
    turnover_rate: 1,
    volume_ratio: 1,
    pe: 24,
    pb: 8,
    market_cap: 1000,
    net_flow: 100,
    sector: "白酒",
  }],
};

const preferences = {
  default_symbol: "SH.600519",
  start_page: "market",
  risk_profile: "balanced",
  morning_email_enabled: true,
};

const decisionFeed = {
  unread_count: 2,
  requires_action: [],
  monitoring: [],
  monitored_at: "2026-07-19T01:10:00Z",
};

function fixtureFor(url: string, marketPayload = market) {
  if (url.includes("/api/v1/decision-events")) return decisionFeed;
  if (url.includes("/api/v1/market-events")) return events;
  if (url.includes("/api/v1/markets/CN/intelligence")) return intelligence;
  if (url.includes("/api/v1/equity-views")) return [];
  if (url.includes("/api/v1/equities")) return equityPage;
  if (url.includes("/api/v1/market")) return marketPayload;
  return today;
}

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
    return { ok: true, json: async () => fixtureFor(url) };
  }));
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
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
          start_page: "market",
          risk_profile: "balanced",
          morning_email_enabled: true,
        }),
      };
    }
    return { ok: true, status: 200, json: async () => fixtureFor(url) };
  }));

  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "注册新账号" }));
  fireEvent.change(screen.getByLabelText("邮箱"), { target: { value: "alpha@example.com" } });
  fireEvent.change(screen.getByLabelText("昵称"), { target: { value: "Alpha" } });
  fireEvent.change(screen.getByLabelText("密码"), { target: { value: "Passw0rd-alpha" } });
  fireEvent.click(screen.getByRole("button", { name: "创建账号" }));

  expect(await screen.findByText("Alpha")).toBeInTheDocument();
  const navigation = within(screen.getByRole("navigation", { name: "主导航" }));
  expect(navigation.getByRole("link", { name: /提醒/ })).toHaveAttribute("href", "#/decisions");
  expect(await navigation.findByLabelText("2 条未读提醒")).toBeInTheDocument();
  expect(navigation.queryByRole("link", { name: "今日" })).not.toBeInTheDocument();
  expect(navigation.getByRole("link", { name: "持仓" })).toBeInTheDocument();
  expect(navigation.getByRole("link", { name: "复盘" })).toHaveAttribute("href", "#/history");
  expect(navigation.queryByRole("link", { name: "跟踪" })).not.toBeInTheDocument();
  expect(navigation.queryByRole("link", { name: "数据" })).not.toBeInTheDocument();
  await waitFor(() => {
    expect(calls.some((call) => call.url.includes("/api/v1/preferences") && call.auth === "Bearer token-alpha")).toBe(true);
    expect(calls.some((call) => call.url.includes("/api/v1/market") && call.auth === "Bearer token-alpha")).toBe(true);
  });
});

it("opens the authenticated decision center without mounting it outside the session gate", async () => {
  localStorage.setItem("marketdesk.accessToken", "token-decisions");
  window.location.hash = "#/decisions";
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes("/api/v1/auth/me")) {
      return { ok: true, status: 200, json: async () => ({ id: 18, email: "decision@example.com", display_name: "Decision User", created_at: "2026-07-25T01:00:00Z", updated_at: "2026-07-25T01:00:00Z" }) };
    }
    if (url.includes("/api/v1/preferences")) return { ok: true, status: 200, json: async () => preferences };
    return { ok: true, status: 200, json: async () => fixtureFor(url) };
  }));

  render(<App />);

  expect(await screen.findByRole("heading", { name: "变化提醒" })).toBeInTheDocument();
  expect(await screen.findByText("没有需要你处理的变化")).toBeInTheDocument();
  expect(screen.getByRole("navigation", { name: "主导航" })).toBeInTheDocument();
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
      return { ok: true, status: 200, json: async () => preferences };
    }
    if (url.includes("/api/v1/auth/logout")) {
      return { ok: true, status: 204, json: async () => ({}) };
    }
    return { ok: true, status: 200, json: async () => fixtureFor(url) };
  }));

  render(<App />);

  expect(await screen.findByRole("heading", { name: "市场" })).toBeInTheDocument();
  expect(screen.queryByRole("link", { name: "今日" })).not.toBeInTheDocument();
  expect(screen.getByLabelText("大盘速览")).toBeInTheDocument();
  expect(screen.getByRole("navigation", { name: "主导航" })).toBeInTheDocument();
  expect(calls[0]).toEqual({ url: "/api/v1/auth/me", auth: "Bearer token-existing" });
  await waitFor(() => expect(calls.some((call) => call.url === "/api/v1/market")).toBe(true));
  fireEvent.click(screen.getByText("Owner"));
  expect(document.querySelector(".account-menu")).toHaveAttribute("open");
  fireEvent.keyDown(document, { key: "Escape" });
  expect(document.querySelector(".account-menu")).not.toHaveAttribute("open");
  fireEvent.click(screen.getByText("Owner"));
  fireEvent.click(screen.getByRole("button", { name: "退出账号" }));
  expect(screen.getByRole("heading", { name: "登录 StockTS" })).toBeInTheDocument();
  expect(screen.queryByRole("navigation", { name: "主导航" })).not.toBeInTheDocument();
  expect(localStorage.getItem("marketdesk.accessToken")).toBeNull();
});

it("auto switches the shell to mobile layout for phone media", async () => {
  localStorage.setItem("marketdesk.accessToken", "token-mobile");
  vi.stubGlobal("matchMedia", vi.fn((query: string) => ({
    matches: query.includes("max-width: 767px"),
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(() => false),
  } satisfies MediaQueryList)));
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes("/api/v1/auth/me")) {
      return { ok: true, status: 200, json: async () => ({ id: 12, email: "mobile@example.com", display_name: "Mobile User", created_at: "2026-07-25T01:00:00Z", updated_at: "2026-07-25T01:00:00Z" }) };
    }
    if (url.includes("/api/v1/preferences")) {
      return { ok: true, status: 200, json: async () => preferences };
    }
    return { ok: true, status: 200, json: async () => fixtureFor(url) };
  }));

  render(<App />);

  expect(await screen.findByRole("heading", { name: "市场" })).toBeInTheDocument();
  expect(document.body.dataset.deviceMode).toBe("mobile");
  expect(document.querySelector(".app-shell")).toHaveAttribute("data-device-mode", "mobile");
  expect(document.querySelector(".app-shell")).toHaveClass("mobile-shell");
  expect(screen.getByRole("navigation", { name: "主导航" })).toBeInTheDocument();
});

it("uses the tablet rail without falling back to the phone shell", async () => {
  localStorage.setItem("marketdesk.accessToken", "token-tablet");
  vi.stubGlobal("matchMedia", vi.fn((query: string) => ({
    matches: query.includes("min-width: 768px"),
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(() => false),
  } satisfies MediaQueryList)));
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes("/api/v1/auth/me")) {
      return { ok: true, status: 200, json: async () => ({ id: 14, email: "tablet@example.com", display_name: "Tablet User", created_at: "2026-07-25T01:00:00Z", updated_at: "2026-07-25T01:00:00Z" }) };
    }
    if (url.includes("/api/v1/preferences")) {
      return { ok: true, status: 200, json: async () => preferences };
    }
    return { ok: true, status: 200, json: async () => fixtureFor(url) };
  }));

  render(<App />);

  expect(await screen.findByRole("heading", { name: "市场" })).toBeInTheDocument();
  expect(document.body.dataset.deviceMode).toBe("tablet");
  expect(document.querySelector(".app-shell")).toHaveAttribute("data-device-mode", "tablet");
  expect(document.querySelector(".app-shell")).toHaveClass("tablet-shell");
  expect(document.querySelector(".app-shell")).not.toHaveClass("mobile-shell");
});

it("groups the workspace navigation and persists the collapsed desktop rail", async () => {
  localStorage.setItem("marketdesk.accessToken", "token-rail");
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes("/api/v1/auth/me")) {
      return { ok: true, status: 200, json: async () => ({ id: 15, email: "rail@example.com", display_name: "Rail User", created_at: "2026-08-22T01:00:00Z", updated_at: "2026-08-22T01:00:00Z" }) };
    }
    if (url.includes("/api/v1/preferences")) {
      return { ok: true, status: 200, json: async () => preferences };
    }
    return { ok: true, status: 200, json: async () => fixtureFor(url) };
  }));

  render(<App />);

  expect(await screen.findByRole("heading", { name: "市场" })).toBeInTheDocument();
  const navigation = screen.getByRole("navigation", { name: "主导航" });
  expect(within(navigation).getByRole("region", { name: "决策台" })).toBeInTheDocument();
  expect(within(navigation).getByRole("region", { name: "研究" })).toBeInTheDocument();
  expect(within(navigation).getByRole("region", { name: "市场结构" })).toBeInTheDocument();
  expect(within(navigation).getByRole("region", { name: "验证" })).toBeInTheDocument();
  expect(screen.getByText("先判断环境，再选择研究方向")).toBeInTheDocument();

  const railToggle = screen.getByRole("button", { name: "收起侧边栏" });
  expect(railToggle).toHaveAttribute("aria-expanded", "true");
  fireEvent.click(railToggle);
  expect(document.querySelector(".app-shell")).toHaveClass("rail-collapsed");
  expect(screen.getByRole("button", { name: "展开侧边栏" })).toHaveAttribute("aria-expanded", "false");
  expect(localStorage.getItem("stockts:rail")).toBe("compact");
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
      return { ok: true, status: 200, json: async () => preferences };
    }
    if (url.includes("/api/v1/refresh") && init?.method === "POST") {
      refreshed = true;
      return { ok: true, status: 200, json: async () => ({ status: "ok", meta: { ...today.meta, fetched_at: "2030-01-02T03:04:05Z" } }) };
    }
    const refreshedMarket = {
      ...market,
      snapshot: {
        ...market.snapshot,
        meta: { ...today.meta, fetched_at: refreshed ? "2030-01-02T03:04:05Z" : today.meta.fetched_at },
      },
    };
    return {
      ok: true,
      status: 200,
      json: async () => fixtureFor(url, refreshedMarket),
    };
  }));

  render(<App />);

  expect(await screen.findByText(/行情时间/)).toBeInTheDocument();
  expect(screen.getByText(/更新/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "刷新" }));

  expect(await screen.findByText(/全站数据已同步 · 更新于 .*2030/)).toBeInTheDocument();
  expect(screen.getByText(/行情时间/)).toBeInTheDocument();
});

it("keeps refresh failures visible without clearing the current workspace", async () => {
  localStorage.setItem("marketdesk.accessToken", "token-refresh-error");
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes("/api/v1/auth/me")) {
      return { ok: true, status: 200, json: async () => ({ id: 13, email: "error@example.com", display_name: "Error User", created_at: "2026-07-25T01:00:00Z", updated_at: "2026-07-25T01:00:00Z" }) };
    }
    if (url.includes("/api/v1/preferences")) {
      return { ok: true, status: 200, json: async () => preferences };
    }
    if (url.includes("/api/v1/refresh")) {
      return { ok: false, status: 503, json: async () => ({ detail: "provider unavailable" }) };
    }
    return { ok: true, status: 200, json: async () => fixtureFor(url) };
  }));

  render(<App />);
  expect(await screen.findByRole("heading", { name: "市场" })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "刷新" }));

  expect(await screen.findByRole("alert")).toHaveTextContent("刷新失败，请稍后重试");
  expect(screen.getByRole("heading", { name: "市场" })).toBeInTheDocument();
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
      return { ok: true, status: 200, json: async () => preferences };
    }
    if (url.includes("/api/v1/search")) {
      return { ok: true, status: 200, json: async () => [{ symbol: "SH.600519", code: "600519", name: "贵州茅台", price: 1500, change_pct: 1.2, amount: 100, turnover_rate: 1, volume_ratio: 1, pe: 24, pb: 8, market_cap: 1000, net_flow: 100, sector: "白酒" }] };
    }
    return { ok: true, status: 200, json: async () => fixtureFor(url) };
  }));

  render(<App />);
  expect(await screen.findByRole("heading", { name: "市场" })).toBeInTheDocument();
  fireEvent.keyDown(window, { key: "k", metaKey: true });
  const input = screen.getByLabelText("搜索股票或输入问题");
  expect(input).toHaveFocus();
  expect(input).toHaveAttribute("aria-expanded", "true");
  expect(screen.getAllByText("搜索").length).toBeGreaterThan(0);
  fireEvent.change(input, { target: { value: "茅台" } });

  const stockResult = await screen.findByRole("option", { name: /贵州茅台/ });
  expect(stockResult).toBeInTheDocument();
  expect(stockResult).toHaveTextContent("SH.600519");
  expect(stockResult).toHaveTextContent("白酒");
  expect(screen.getByRole("link", { name: "直接给我决定" })).toHaveAttribute("href", "#/ask?question=%E8%8C%85%E5%8F%B0");
  fireEvent.keyDown(input, { key: "ArrowDown" });
  expect(stockResult).toHaveAttribute("aria-selected", "true");
  fireEvent.keyDown(input, { key: "Escape" });
  expect(input).toHaveAttribute("aria-expanded", "false");
  fireEvent.focus(input);
  fireEvent.keyDown(input, { key: "ArrowDown" });
  fireEvent.keyDown(input, { key: "Enter" });
  expect(window.location.hash).toContain("/stocks?symbol=SH.600519");
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
      return { ok: true, status: 200, json: async () => preferences };
    }
    return { ok: true, status: 200, json: async () => fixtureFor(url) };
  }));

  render(<App />);
  expect(await screen.findByRole("heading", { name: "市场" })).toBeInTheDocument();
  fireEvent.focus(screen.getByLabelText("搜索股票或输入问题"));

  const recent = within(screen.getByLabelText("最近研究"));
  expect(recent.getByText("贵州茅台")).toBeInTheDocument();
  expect(recent.getByText("SH.600519")).toBeInTheDocument();
  expect(recent.getByRole("link", { name: "现在能不能买" })).toHaveAttribute("href", "#/ask?symbol=SH.600519&name=%E8%B4%B5%E5%B7%9E%E8%8C%85%E5%8F%B0&question=%E8%B4%B5%E5%B7%9E%E8%8C%85%E5%8F%B0%E7%8E%B0%E5%9C%A8%E8%83%BD%E4%B8%8D%E8%83%BD%E4%B9%B0%EF%BC%8C%E7%9B%B4%E6%8E%A5%E7%BB%99%E6%88%91%E7%BB%93%E8%AE%BA");
  expect(recent.getByRole("link", { name: "已经持有怎么办" })).toHaveAttribute("href", "#/ask?symbol=SH.600519&name=%E8%B4%B5%E5%B7%9E%E8%8C%85%E5%8F%B0&question=%E5%A6%82%E6%9E%9C%E5%B7%B2%E7%BB%8F%E6%8C%81%E6%9C%89%E8%B4%B5%E5%B7%9E%E8%8C%85%E5%8F%B0%EF%BC%8C%E7%8E%B0%E5%9C%A8%E6%80%8E%E4%B9%88%E5%A4%84%E7%90%86");
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
      return { ok: true, status: 200, json: async () => preferences };
    }
    return { ok: true, status: 200, json: async () => today };
  }));

  render(<App />);

  expect(await screen.findByRole("heading", { name: "问股" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "问股" })).toHaveClass("active");
});

it("opens the stock from the latest Ask Stock answer instead of stale research", async () => {
  localStorage.setItem("marketdesk.accessToken", "token-ask-handoff");
  localStorage.setItem("marketdesk.recentResearch.v1.ask-handoff", JSON.stringify({
    version: 1,
    items: [{ symbol: "SH.600519", name: "贵州茅台", sector: "白酒", updatedAt: 1 }],
  }));
  window.location.hash = "#/ask";
  const answer = {
    kind: "llm_answer",
    question: "宁德时代现在主要风险是什么",
    intent: "risk",
    symbol: "SZ.300750",
    name: "宁德时代",
    answer: "宁德时代当前主要风险需要结合价格与行业景气核对。",
    evidence: [],
    risks: [],
    next_actions: [],
    metrics: [],
    factors: [],
    holding_context: null,
    observed_at: "2026-08-22T01:00:00Z",
    confidence: 0.72,
    source: "金融分析 Skill + 本地证据",
    disclaimer: "研究辅助信息，不构成投资建议。",
    columns: [],
    rows: [],
  };
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes("/api/v1/auth/me")) {
      return { ok: true, status: 200, json: async () => ({ id: 12, email: "handoff@example.com", display_name: "Handoff User", created_at: "2026-08-22T01:00:00Z", updated_at: "2026-08-22T01:00:00Z" }) };
    }
    if (url.includes("/api/v1/preferences")) {
      return { ok: true, status: 200, json: async () => preferences };
    }
    if (url.includes("/api/v1/ask-stock")) {
      return { ok: true, status: 200, json: async () => answer };
    }
    return { ok: true, status: 200, json: async () => fixtureFor(url) };
  }));

  render(<App />);
  expect(await screen.findByRole("heading", { name: "问股" })).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("继续追问"), { target: { value: "宁德时代现在主要风险是什么" } });
  fireEvent.click(screen.getByRole("button", { name: "发送" }));

  expect(await screen.findByText("宁德时代当前主要风险需要结合价格与行业景气核对。")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("link", { name: "个股" }));
  expect(window.location.hash).toContain("/stocks?symbol=SZ.300750");
  expect(window.location.hash).not.toContain("SH.600519");
});
