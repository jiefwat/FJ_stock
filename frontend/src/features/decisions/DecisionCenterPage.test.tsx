import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";

import type { DecisionEvent, DecisionEventFeed } from "../../lib/api";
import { DecisionCenterPage } from "./DecisionCenterPage";

const actionable: DecisionEvent = {
  id: 12,
  source: "holding",
  subject_key: "1",
  symbol: "SZ.002517",
  name: "恺英网络",
  strategy: null,
  previous_action: "继续持有",
  action: "优先减仓或止损",
  summary: "已经触发风险条件，不建议继续补仓或等待反弹。",
  severity: "critical",
  user_required: true,
  reason_code: "holding_exit_watch",
  confidence: 0.82,
  href: "/holdings?symbol=SZ.002517",
  observed_at: "2026-08-16T01:10:00Z",
  created_at: "2026-08-16T01:10:01Z",
  read_at: null,
  email_status: "sent",
  email_attempts: 1,
  email_error: null,
  email_sent_at: "2026-08-16T01:11:00Z",
};

const monitoring: DecisionEvent = {
  ...actionable,
  id: 13,
  source: "opportunity",
  subject_key: "trend",
  strategy: "trend",
  previous_action: "仅观察",
  action: "暂不买入",
  summary: "当前市场环境或可能收益与风险不支持参与。",
  severity: "info",
  user_required: false,
  href: "/stocks?symbol=SZ.002517&from=opportunities&preset=trend",
  email_status: "not_required",
  email_attempts: 0,
  email_sent_at: null,
};

function renderPage(feed: DecisionEventFeed = {
  unread_count: 2,
  requires_action: [actionable],
  monitoring: [monitoring],
  monitored_at: "2026-08-16T01:10:00Z",
}) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (init?.method === "POST") {
      return { ok: true, status: 200, json: async () => ({ ...actionable, read_at: "2026-08-16T01:12:00Z" }) };
    }
    return { ok: true, status: 200, json: async () => feed };
  });
  vi.stubGlobal("fetch", fetchMock);
  vi.stubGlobal("localStorage", {
    getItem: () => "fixture-token",
    setItem: vi.fn(),
    removeItem: vi.fn(),
  });
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return {
    fetchMock,
    ...render(<QueryClientProvider client={client}><MemoryRouter><DecisionCenterPage /></MemoryRouter></QueryClientProvider>),
  };
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("leads with direct actions and keeps monitoring changes separate", async () => {
  const { fetchMock } = renderPage();

  expect(await screen.findByRole("heading", { name: "变化提醒" })).toBeInTheDocument();
  const required = within(await screen.findByLabelText("需要处理"));
  expect(required.getByText("优先减仓或止损")).toBeInTheDocument();
  expect(required.getByText("之前：继续持有")).toBeInTheDocument();
  expect(required.getByText("证据较充分 · 82%")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "自动记录" })).toBeInTheDocument();
  expect(screen.getByText("暂不买入")).toBeInTheDocument();

  fireEvent.click(required.getByRole("link", { name: "查看恺英网络原因：优先减仓或止损" }));
  await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
    "/api/v1/decision-events/12/read",
    expect.objectContaining({ method: "POST" }),
  ));
});

it("shows a no-work empty state when the system has nothing actionable", async () => {
  renderPage({ unread_count: 0, requires_action: [], monitoring: [], monitored_at: null });

  expect(await screen.findByText("没有需要你处理的变化")).toBeInTheDocument();
  expect(screen.queryByText(/请检查|请复核|请刷新/)).not.toBeInTheDocument();
});

it("filters reminders by category and read state", async () => {
  renderPage();
  fireEvent.click(await screen.findByRole("button", { name: "候选变化 1" }));
  expect(screen.queryByText("优先减仓或止损")).not.toBeInTheDocument();
  expect(screen.getByText("暂不买入")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "已读" }));
  expect(screen.getByText("当前筛选下没有提醒")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "清除筛选" }));
  expect(screen.getByText("优先减仓或止损")).toBeInTheDocument();
});
