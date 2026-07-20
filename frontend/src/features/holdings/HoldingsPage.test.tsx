import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";

import { HoldingsPage } from "./HoldingsPage";

const holding = {
  item: {
    id: 1,
    symbol: "SH.600519",
    name: "贵州茅台",
    quantity: 100,
    cost_price: 1400,
    target_weight: 0.4,
    thesis: "现金流稳定",
    invalidation: "跌破成本",
    status: "holding",
    created_at: "2026-07-18T09:00:00Z",
    updated_at: "2026-07-19T09:00:00Z",
  },
  quote: { symbol: "SH.600519", code: "600519", name: "贵州茅台", price: 1500, change_pct: 1.2, amount: 1, turnover_rate: 1, volume_ratio: null, pe: 23, pb: 7, market_cap: 1, net_flow: 80000000, sector: "白酒" },
  market_value: 150000,
  cost_value: 140000,
  pnl: 10000,
  pnl_pct: 7.14,
  portfolio_weight: 1,
  drift: 0.6,
  target_market_value: 60000,
  rebalance_value: -90000,
  rebalance_quantity: -60,
  break_even_price: 1400,
  price_gap_to_cost_pct: 7.14,
  analysis_dimensions: [
    { key: "position", label: "持仓规模", signal: "neutral", summary: "持仓数量 100 股，当前市值 150,000", evidence: ["现价 1500"] },
    { key: "cost", label: "成本盈亏", signal: "positive", summary: "成本价 1400，浮盈 7.14%", evidence: ["浮盈 10,000"] },
    { key: "rebalance", label: "调仓建议", signal: "negative", summary: "高于目标仓位，建议减仓约 60 股", evidence: ["目标市值 60,000"] },
    { key: "liquidity", label: "流动性承载", signal: "positive", summary: "成交额可承载调仓", evidence: ["成交额充足"] },
    { key: "valuation", label: "估值安全垫", signal: "neutral", summary: "PE 与 PB 需要结合行业比较", evidence: ["PE 23", "PB 7"] },
  ],
  action: "trim",
  conclusion: "持仓结论：贵州茅台 当前盈利 7.14%，组合占比高于目标，建议降低暴露；持仓逻辑：现金流稳定。",
  risk_flags: ["组合占比高于目标"],
  next_actions: ["复核是否需要降仓"],
};

function renderPage() {
  vi.stubGlobal("fetch", vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
    if (init?.method === "PATCH") {
      const body = JSON.parse(String(init.body));
      return { ok: true, status: 200, json: async () => ({ ...holding, item: { ...holding.item, ...body, updated_at: "2026-07-19T10:00:00Z" }, conclusion: "持仓结论：贵州茅台 已更新持仓逻辑，继续观察。" }) };
    }
    return { ok: true, status: 200, json: async () => [holding] };
  }));
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });

  render(<QueryClientProvider client={client}><MemoryRouter><HoldingsPage /></MemoryRouter></QueryClientProvider>);
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("shows portfolio overview and a compact holdings list with stock-analysis jumps", async () => {
  renderPage();

  const table = await screen.findByRole("table", { name: "持仓列表" });

  expect(screen.getByText("组合总览")).toBeInTheDocument();
  expect(screen.getByText("组合结论")).toBeInTheDocument();
  expect(screen.getByText(/1 笔持仓/)).toBeInTheDocument();
  expect(screen.getByText(/需要复核 1 笔/)).toBeInTheDocument();
  expect(screen.getAllByText(/组合占比高于目标/).length).toBeGreaterThan(0);

  const row = within(table).getByRole("row", { name: /贵州茅台/ });
  expect(within(row).getByText("贵州茅台")).toBeInTheDocument();
  expect(within(row).getByText("降低暴露")).toBeInTheDocument();
  expect(within(row).getByText(/当前盈利 7.14%/)).toBeInTheDocument();
  expect(within(row).getByText(/建议减仓约 60 股/)).toBeInTheDocument();
  expect(within(row).getByRole("link", { name: "个股分析 →" })).toHaveAttribute("href", "/stocks?symbol=SH.600519");

  expect(screen.queryByText("编辑持仓数据")).not.toBeInTheDocument();
  expect(screen.queryByText("流动性承载")).not.toBeInTheDocument();
  expect(screen.queryByText("估值安全垫")).not.toBeInTheDocument();
});

it("keeps editing lightweight from the list row", async () => {
  renderPage();

  const table = await screen.findByRole("table", { name: "持仓列表" });
  const row = within(table).getByRole("row", { name: /贵州茅台/ });
  fireEvent.change(within(row).getByLabelText("持仓数量 贵州茅台"), { target: { value: "80" } });
  fireEvent.change(within(row).getByLabelText("成本价 贵州茅台"), { target: { value: "1420" } });
  fireEvent.click(within(row).getByRole("button", { name: "保存 贵州茅台" }));

  expect(await screen.findByText("已保存")).toBeInTheDocument();
});
