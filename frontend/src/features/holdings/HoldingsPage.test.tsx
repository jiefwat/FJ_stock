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
  analysis_dimensions: [
    { key: "position", label: "持仓规模", signal: "neutral", summary: "持仓数量 100 股，当前市值 150,000", evidence: ["现价 1500"] },
    { key: "cost", label: "成本盈亏", signal: "positive", summary: "成本价 1400，浮盈 7.14%", evidence: ["浮盈 10,000"] },
    { key: "rebalance", label: "调仓建议", signal: "negative", summary: "高于目标仓位，建议减仓约 60 股", evidence: ["目标市值 60,000"] },
    { key: "liquidity", label: "流动性承载", signal: "positive", summary: "成交额可承载调仓", evidence: ["成交额充足"] },
    { key: "valuation", label: "估值安全垫", signal: "neutral", summary: "PE 与 PB 需要结合行业比较", evidence: ["PE 23", "PB 7"] },
  ],
  action: "trim",
  conclusion: "建议动作：减仓。分析维度：仓位偏离、成本风控、估值、流动性、板块资金、持仓逻辑。原因：仓位明显高于目标、成本风险未触发强制处理、估值需要结合行业比较、流动性中性、资金净流入、持仓逻辑已记录，可进入个股页复核证据。建议先减仓约 60 股，回到目标仓位后再复核保留理由。",
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

  const list = await screen.findByRole("list", { name: "持仓清单" });

  expect(screen.getByText("组合总览")).toBeInTheDocument();
  expect(screen.getByText("组合结论")).toBeInTheDocument();
  expect(screen.getByText(/1 笔持仓/)).toBeInTheDocument();
  expect(screen.getByText(/需要复核 1 笔/)).toBeInTheDocument();
  expect(screen.getAllByText(/组合占比高于目标/).length).toBeGreaterThan(0);

  const row = within(list).getByRole("listitem", { name: /贵州茅台/ });
  expect(within(row).getByText("贵州茅台")).toBeInTheDocument();
  expect(within(row).getByText("减仓")).toBeInTheDocument();
  expect(within(row).getByText(/分析维度：仓位偏离、成本风控、估值、流动性、板块资金、持仓逻辑/)).toBeInTheDocument();
  expect(within(row).getByText(/建议先减仓约 60 股/)).toBeInTheDocument();
  expect(within(row).queryByText(/当前盈利/)).not.toBeInTheDocument();
  expect(within(row).getByText("收益拆分")).toBeInTheDocument();
  expect(within(row).getByText("总盈亏")).toBeInTheDocument();
  expect(within(row).getByText("单日盈亏")).toBeInTheDocument();
  expect(within(row).getByText("近5日盈亏")).toBeInTheDocument();
  expect(within(row).getByText(/10,000/)).toBeInTheDocument();
  expect(within(row).getByText("+1,780")).toBeInTheDocument();
  expect(within(row).getByText("-3,200")).toBeInTheDocument();
  expect(within(row).getByRole("link", { name: "个股分析 →" })).toHaveAttribute("href", "/stocks?symbol=SH.600519");

  expect(screen.queryByText("编辑持仓数据")).not.toBeInTheDocument();
  expect(screen.queryByText("流动性承载")).not.toBeInTheDocument();
  expect(screen.queryByText("估值安全垫")).not.toBeInTheDocument();
});

it("keeps editing lightweight from the list row", async () => {
  renderPage();

  const list = await screen.findByRole("list", { name: "持仓清单" });
  const row = within(list).getByRole("listitem", { name: /贵州茅台/ });
  fireEvent.change(within(row).getByLabelText("持仓数量 贵州茅台"), { target: { value: "80" } });
  fireEvent.change(within(row).getByLabelText("成本价 贵州茅台"), { target: { value: "1420" } });
  fireEvent.click(within(row).getByRole("button", { name: "保存 贵州茅台" }));

  expect(await screen.findByText("已保存")).toBeInTheDocument();
});

it("does not show an add signal when the holding action is exit review", async () => {
  const exitHolding = {
    ...holding,
    item: { ...holding.item, id: 2, name: "风控样本", symbol: "SH.600002", quantity: 4300, cost_price: 5.7226, target_weight: 0.125 },
    market_value: 16039,
    pnl: -8568,
    pnl_pct: -34.82,
    day_pnl: -1204,
    day_pnl_pct: -6.98,
    five_day_pnl: -2021,
    five_day_pnl_pct: -11.19,
    portfolio_weight: 0.059,
    drift: -0.066,
    rebalance_quantity: 4756,
    action: "exit_watch",
    conclusion: "建议动作：减仓/退出复核。分析维度：仓位偏离、成本风控、估值、流动性、板块资金、持仓逻辑。原因：成本风控已触发。暂停补仓，先做退出复核。",
    risk_flags: ["亏损超过 10%"],
  };
  vi.stubGlobal("fetch", vi.fn(async () => ({ ok: true, status: 200, json: async () => [exitHolding] })));
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={client}><MemoryRouter><HoldingsPage /></MemoryRouter></QueryClientProvider>);

  const list = await screen.findByRole("list", { name: "持仓清单" });
  const row = within(list).getByRole("listitem", { name: /风控样本/ });

  expect(within(row).getByText("退出复核")).toBeInTheDocument();
  expect(within(row).getAllByText(/暂停补仓/).length).toBeGreaterThan(0);
  expect(within(row).queryByText(/可加仓/)).not.toBeInTheDocument();
  expect(within(row).queryByText(/\+4,756 股/)).not.toBeInTheDocument();
});
