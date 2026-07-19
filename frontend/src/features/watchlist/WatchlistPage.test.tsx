import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";

import { WatchlistPage } from "./WatchlistPage";

afterEach(() => vi.unstubAllGlobals());

it("edits and saves an auditable research note", async () => {
  const item = { id: 1, symbol: "SH.600519", name: "贵州茅台", thesis: "现金流稳定", invalidation: "趋势破位", status: "researching", created_at: "2026-07-18T09:00:00Z", updated_at: "2026-07-19T09:00:00Z" };
  vi.stubGlobal("fetch", vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
    if (init?.method === "PATCH") {
      const body = JSON.parse(String(init.body));
      return { ok: true, status: 200, json: async () => ({ ...item, ...body, updated_at: "2026-07-19T10:00:00Z" }) };
    }
    return { ok: true, status: 200, json: async () => [item] };
  }));
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });

  render(<QueryClientProvider client={client}><MemoryRouter><WatchlistPage /></MemoryRouter></QueryClientProvider>);

  expect(await screen.findByRole("link", { name: "贵州茅台" })).toHaveAttribute("href", "/stocks?symbol=SH.600519");
  fireEvent.change(screen.getByLabelText("研究逻辑 贵州茅台"), { target: { value: "等待估值回落" } });
  fireEvent.click(screen.getByRole("button", { name: "保存研究记录" }));

  expect(await screen.findByText("已保存")).toBeInTheDocument();
});
