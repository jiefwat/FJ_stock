import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { DataCenterPage } from "./DataCenterPage";

afterEach(() => vi.unstubAllGlobals());

it("shows audit timestamps and confirms a manual refresh", async () => {
  const meta = { source: "sina+tencent", observed_at: "2026-07-17T07:00:00Z", fetched_at: "2026-07-19T09:00:00Z", freshness: "delayed", coverage: 1, errors: [] };
  vi.stubGlobal("fetch", vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
    if (init?.method === "POST") return { ok: true, status: 200, json: async () => ({ status: "ok", meta: { ...meta, fetched_at: "2026-07-19T10:00:00Z" } }) };
    return { ok: true, status: 200, json: async () => ({ providers: { sina: { status: "ready", required: true } }, snapshot: meta }) };
  }));
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });

  render(<QueryClientProvider client={client}><DataCenterPage /></QueryClientProvider>);

  expect(await screen.findByText("数据时间")).toBeInTheDocument();
  expect(screen.getByText("抓取时间")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "刷新核心数据" }));

  expect(await screen.findByText(/刷新完成/)).toBeInTheDocument();
});
