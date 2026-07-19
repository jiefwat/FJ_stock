import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";

import { MarketPage } from "./MarketPage";

const market = {
  snapshot: {
    meta: { source: "fixture", observed_at: "2026-07-19T01:00:00Z", fetched_at: "2026-07-19T01:01:00Z", freshness: "fresh", coverage: 0.96, errors: [] },
    indices: [{ symbol: "SH.000001", name: "上证指数", price: 3764.15, change_pct: -3.05, amount: 100 }],
    sectors: [{ code: "BK1", name: "白酒", change_pct: 1.4, net_flow: 100000000 }],
  },
  analysis: { score: 58, regime: "balanced", confidence: 0.95, advancing: 3100, declining: 1900, unchanged: 100, factors: [] },
};

const sector = {
  sector: { code: "BK1", name: "白酒", change_pct: 1.4, net_flow: 100000000 },
  summary: ["主力净流入 1.00 亿，板块热度偏强。"],
  evidence_coverage: 1,
  missing_evidence: [],
  constituents: [
    { symbol: "SH.600519", code: "600519", name: "贵州茅台", price: 1500, change_pct: 1.2, amount: 2000000000, turnover_rate: 0.8, volume_ratio: 1.1, pe: 23, pb: 7, market_cap: 1900000000000, net_flow: 80000000, sector: "白酒" },
  ],
};

function renderPage(initialPath = "/market") {
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes("/api/v1/sectors/BK1")) return { ok: true, status: 200, json: async () => sector };
    return { ok: true, status: 200, json: async () => market };
  }));
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[initialPath]}><MarketPage /></MemoryRouter></QueryClientProvider>);
}

afterEach(() => vi.unstubAllGlobals());

it("opens a sector research panel with constituents and stock links", async () => {
  renderPage();

  fireEvent.click(await screen.findByRole("button", { name: /白酒/ }));

  expect(await screen.findByText("白酒板块简析")).toBeInTheDocument();
  expect(screen.getByText("主力净流入 1.00 亿，板块热度偏强。")).toBeInTheDocument();
  const row = screen.getByRole("link", { name: /贵州茅台/ });
  expect(row).toHaveAttribute("href", "/stocks?symbol=SH.600519");
  expect(within(row).getByText("SH.600519")).toBeInTheDocument();
});
