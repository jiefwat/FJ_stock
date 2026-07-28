import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { DataCenterPage } from "./DataCenterPage";

afterEach(() => vi.unstubAllGlobals());

it("shows audit timestamps and confirms a manual refresh", async () => {
  const meta = { source: "sina+tencent", observed_at: "2026-07-17T07:00:00Z", fetched_at: "2026-07-19T09:00:00Z", freshness: "delayed", coverage: 1, errors: [] };
  vi.stubGlobal("fetch", vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
    if (init?.method === "POST") return { ok: true, status: 200, json: async () => ({ status: "ok", meta: { ...meta, fetched_at: "2026-07-19T10:00:00Z" } }) };
    return { ok: true, status: 200, json: async () => ({ providers: {
      sina: { status: "ready", required: true },
      cninfo_filings: { status: "ready", required: false, description: "巨潮公告元数据" },
      eastmoney_research: { status: "partial", required: false, description: "东方财富研报元数据", error: "timeout" },
      eastmoney_themes: { status: "ready", required: false, description: "东方财富题材归属" },
      eastmoney_dragon_tiger: { status: "empty", required: false, description: "东方财富龙虎榜" },
      cls_fast_news: { status: "not_checked", required: false, description: "财联社快讯备源" },
    }, snapshot: meta }) };
  }));
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });

  render(<QueryClientProvider client={client}><DataCenterPage /></QueryClientProvider>);

  expect(await screen.findByText("行情时间")).toBeInTheDocument();
  expect(screen.getByText("公司公告")).toBeInTheDocument();
  expect(screen.getByText("机构研报")).toBeInTheDocument();
  expect(screen.getByText("题材归属")).toBeInTheDocument();
  expect(screen.getByText("龙虎榜观察")).toBeInTheDocument();
  expect(screen.getByText("快讯独立备源")).toBeInTheDocument();
  expect(screen.getByText(/外部证据不直接改变评分/)).toBeInTheDocument();
  expect(screen.queryByText(/iWenCai|WenCai|问财/i)).not.toBeInTheDocument();
  expect(screen.getByText("更新时间")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "刷新核心数据" }));

  expect(await screen.findByText(/刷新完成/)).toBeInTheDocument();
  expect(screen.getByRole("status")).toHaveTextContent("更新时间");
});
