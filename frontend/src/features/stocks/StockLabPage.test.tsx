import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";

import { StockLabPage } from "./StockLabPage";

const dossier = {
  quote: { symbol: "SH.600519", code: "600519", name: "贵州茅台", price: 1253, change_pct: -0.48, amount: 1, turnover_rate: 1, volume_ratio: null, pe: 23, pb: 7, market_cap: 1, net_flow: null, sector: null },
  stance: "watch", stance_score: 65, evidence_coverage: 0.55,
  score_factors: [
    { key: "price_ma20", label: "价格与 MA20", impact: 10, signal: "positive", evidence: "收盘价位于 20 日均线之上", available: true },
    { key: "volatility", label: "波动风险", impact: -8, signal: "negative", evidence: "年化波动率偏高", available: true },
  ],
  technical: { ma5: 1237, ma20: 1204, ma60: 1265, rsi14: 66, volatility20: 21, support: 1168, resistance: 1259 },
  bull_case: ["收盘价位于 20 日均线之上"], bear_case: ["MA20 低于 MA60"],
  invalidation: ["跌破近 20 日支撑 1168.00"], missing_evidence: ["公告与研报增强数据"],
  bars: Array.from({ length: 65 }, (_, index) => ({ date: `2026-04-${String((index % 28) + 1).padStart(2, "0")}`, close: 1200 + index })),
};

function renderPage(watchlist: object[] = []) {
  const currentWatchlist = [...watchlist];
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (init?.method === "POST") {
      currentWatchlist.push({ id: 1, symbol: "SH.600519", name: "贵州茅台", thesis: "新逻辑", invalidation: "新失效条件", status: "new", updated_at: "2026-07-19T10:00:00Z" });
      return { ok: true, status: 201, json: async () => currentWatchlist[0] };
    }
    if (url.includes("/watchlist")) return { ok: true, status: 200, json: async () => currentWatchlist };
    if (url.includes("/search")) return { ok: true, status: 200, json: async () => [] };
    return { ok: true, status: 200, json: async () => dossier };
  }));
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={client}><MemoryRouter initialEntries={["/stocks?symbol=SH.600519"]}><StockLabPage /></MemoryRouter></QueryClientProvider>);
}

afterEach(() => vi.unstubAllGlobals());

it("shows the evidence ledger and edits the thesis before adding to watchlist", async () => {
  renderPage();

  expect(await screen.findByLabelText("价格趋势图")).toBeInTheDocument();
  expect(screen.getByText("收盘价")).toBeInTheDocument();
  expect(screen.getByText("证据覆盖 55%")).toBeInTheDocument();
  expect(screen.getByText("波动风险")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "加入观察" }));
  expect(screen.getByLabelText("研究逻辑")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("研究逻辑"), { target: { value: "等待估值与趋势共振" } });
  fireEvent.click(screen.getByRole("button", { name: "保存到观察列表" }));

  expect(await screen.findByRole("link", { name: "观察中 · 编辑记录" })).toBeInTheDocument();
  expect(screen.getByRole("status")).toHaveTextContent("已加入观察");
});

it("recognizes an existing watchlist item before another post", async () => {
  renderPage([{ id: 1, symbol: "SH.600519", name: "贵州茅台", thesis: "已有逻辑", invalidation: "已有失效条件", status: "researching", updated_at: "2026-07-19T09:00:00Z" }]);

  expect(await screen.findByRole("link", { name: "观察中 · 编辑记录" })).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "加入观察" })).not.toBeInTheDocument();
});
