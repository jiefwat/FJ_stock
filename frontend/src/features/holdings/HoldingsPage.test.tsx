import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
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
  three_day_pnl: -2100,
  three_day_pnl_pct: -1.38,
  five_day_pnl: -3200,
  five_day_pnl_pct: -2.09,
  recent_daily_changes: [
    { date: "2026-07-22", change_pct: 0.45 },
    { date: "2026-07-23", change_pct: -0.31 },
    { date: "2026-07-24", change_pct: 1.08 },
    { date: "2026-07-27", change_pct: -0.76 },
    { date: "2026-07-28", change_pct: 0.12 },
    { date: "2026-07-29", change_pct: -0.8 },
    { date: "2026-07-30", change_pct: 0.66 },
    { date: "2026-07-31", change_pct: -0.22 },
    { date: "2026-08-03", change_pct: 0.93 },
    { date: "2026-08-04", change_pct: 1.2 },
  ],
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
  conclusion: "建议动作：减仓。不使用目标比例，按盈亏、近10日走势和资金复核，单票占比 100.0% 偏高，盈亏 +7.14% 未触发止损。建议先分批减仓，降低单票波动对整仓的影响，再复核保留理由。",
  risk_flags: ["单票占比偏高"],
  next_actions: ["复核是否需要降仓"],
};

const calmHolding = {
  ...holding,
  item: { ...holding.item, id: 2, symbol: "SZ.000001", name: "平安银行", quantity: 1000, cost_price: 11, target_weight: 0.2 },
  quote: { ...holding.quote, symbol: "SZ.000001", code: "000001", name: "平安银行", price: 11.2, change_pct: 0.2, sector: "银行" },
  market_value: 11200,
  cost_value: 11000,
  pnl: 200,
  pnl_pct: 1.82,
  day_pnl: 22,
  day_pnl_pct: 0.2,
  three_day_pnl: 65,
  three_day_pnl_pct: 0.58,
  five_day_pnl: 80,
  five_day_pnl_pct: 0.72,
  portfolio_weight: 0.07,
  drift: -0.13,
  target_market_value: 32000,
  rebalance_value: 20800,
  rebalance_quantity: 1857,
  action: "hold",
  conclusion: "持仓结论：平安银行 暂无必须处理的持仓，等待更好的复核窗口。",
  risk_flags: [],
  next_actions: ["继续观察"],
};

function renderPage(items = [holding]) {
  vi.stubGlobal("fetch", vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
    if (init?.method === "PATCH") {
      const body = JSON.parse(String(init.body));
      return { ok: true, status: 200, json: async () => ({ ...holding, item: { ...holding.item, ...body, updated_at: "2026-07-19T10:00:00Z" }, conclusion: "持仓结论：贵州茅台 已更新持仓逻辑，继续观察。" }) };
    }
    return { ok: true, status: 200, json: async () => items };
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

  expect(screen.getByText("组合")).toBeInTheDocument();
  expect(screen.getByText("结论")).toBeInTheDocument();
  expect(screen.getByText(/1 笔持仓/)).toBeInTheDocument();
  expect(screen.getByText("调仓信号")).toBeInTheDocument();
  expect(screen.getByText("1 减 / 0 加")).toBeInTheDocument();
  expect(screen.getByText(/整仓近10日 \+2.35%，当日 \+1.20%/)).toBeInTheDocument();
  expect(screen.getAllByText(/单票占比偏高/).length).toBeGreaterThan(0);
  const movementDeck = within(screen.getByLabelText("整仓涨跌分析"));
  expect(movementDeck.getByText("整仓涨跌")).toBeInTheDocument();
  expect(movementDeck.getByText("近10日每日组合表现")).toBeInTheDocument();
  expect(movementDeck.getByText("10日累计")).toBeInTheDocument();
  expect(movementDeck.getByText("最大贡献")).toBeInTheDocument();
  expect(movementDeck.getByText("最大拖累")).toBeInTheDocument();
  expect(within(screen.getByLabelText("整仓近10日每日涨跌")).getByText("08-04")).toBeInTheDocument();
  expect(movementDeck.getByRole("link", { name: "查看整仓解释（可选）" }).getAttribute("href")).toContain("question=");
  expect(screen.queryByLabelText("下跌会亏多少")).not.toBeInTheDocument();
  const todayFocus = within(screen.getByLabelText("今天的操作决定"));
  expect(todayFocus.getByText("今天的决定")).toBeInTheDocument();
  expect(todayFocus.getByText("按顺序处理这几只")).toBeInTheDocument();
  expect(todayFocus.getByText("贵州茅台")).toBeInTheDocument();
  expect(todayFocus.getByText("高")).toBeInTheDocument();
  expect(todayFocus.getByText(/建议分批减仓/)).toBeInTheDocument();
  expect(screen.queryByLabelText("风险提醒")).not.toBeInTheDocument();

  const stockPlan = within(screen.getByLabelText("整仓股票建议"));
  expect(stockPlan.getByText("全股票分析")).toBeInTheDocument();
  expect(stockPlan.getByText(/每只持仓是否减仓 \/ 加仓/)).toBeInTheDocument();
  expect(stockPlan.queryByText("仓位或盈利偏高，复核是否分批减仓")).not.toBeInTheDocument();
  const dailyChanges = within(stockPlan.getByLabelText("贵州茅台 近10日每日涨跌幅"));
  const dailyDates = dailyChanges.getAllByText(/\d{2}-\d{2}/).map((node) => node.textContent);
  expect(dailyDates.slice(0, 3)).toEqual(["08-04", "08-03", "07-31"]);
  expect(dailyDates.at(-1)).toBe("07-22");
  expect(dailyChanges.getByText("-0.80%")).toBeInTheDocument();
  expect(dailyChanges.getByText("+1.20%")).toBeInTheDocument();
  expect(stockPlan.queryByText("3日")).not.toBeInTheDocument();
  expect(stockPlan.queryByText("5日")).not.toBeInTheDocument();
  expect(stockPlan.getByRole("link", { name: "查看整仓依据（可选）" }).getAttribute("href")).toContain("question=");

  const row = within(list).getByRole("listitem", { name: /贵州茅台/ });
  expect(within(row).getByText("贵州茅台")).toBeInTheDocument();
  expect(within(row).getAllByText("建议分批减仓").length).toBeGreaterThan(0);
  expect(within(row).getByRole("button", { name: "展开详情 贵州茅台" })).toBeInTheDocument();
  expect(row).toHaveAttribute("aria-expanded", "false");
  expect(within(row).getByText(/单票占比 100.0% 偏高/)).toBeInTheDocument();
  expect(within(row).getByText("当日盈亏")).toBeInTheDocument();
  expect(within(row).getByText("+1,780")).toBeInTheDocument();
  expect(within(row).getByText("+1.20%")).toBeInTheDocument();
  expect(within(row).queryByText("总盈亏")).not.toBeInTheDocument();
  expect(within(row).queryByText("收益拆分")).not.toBeInTheDocument();
  expect(within(row).queryByText("编辑持仓")).not.toBeInTheDocument();
  expect(within(row).queryByRole("link", { name: "看个股 →" })).not.toBeInTheDocument();
  expect(within(row).queryByText(/分析维度/)).not.toBeInTheDocument();
  expect(within(row).getByText(/建议先分批减仓/)).toBeInTheDocument();
  expect(within(row).queryByText(/当前盈利/)).not.toBeInTheDocument();

  fireEvent.click(row);
  expect(row).toHaveAttribute("aria-expanded", "true");
  expect(within(row).getByText("收益拆分")).toBeInTheDocument();
  expect(within(row).getByText("总盈亏")).toBeInTheDocument();
  expect(within(row).getByText("3日内盈亏")).toBeInTheDocument();
  expect(within(row).getByText("5日内盈亏")).toBeInTheDocument();
  expect(within(row).queryByText("当日盈亏")).not.toBeInTheDocument();
  expect(within(row).queryByText("单日盈亏")).not.toBeInTheDocument();
  expect(within(row).getByText(/10,000/)).toBeInTheDocument();
  expect(within(row).getByText("+7.14%")).toBeInTheDocument();
  expect(within(row).getByText("-2,100")).toBeInTheDocument();
  expect(within(row).getByText("-1.38%")).toBeInTheDocument();
  expect(within(row).getByText("-3,200")).toBeInTheDocument();
  expect(within(row).getByText("-2.09%")).toBeInTheDocument();
  expect(within(row).getByText("现价")).toBeInTheDocument();
  expect(within(row).getByText("1,500")).toBeInTheDocument();
  expect(within(row).getByText("持仓市值")).toBeInTheDocument();
  expect(within(row).getByText("持仓成本")).toBeInTheDocument();
  expect(within(row).getByText("持仓占比")).toBeInTheDocument();
  expect(within(row).getByText("100.0%")).toBeInTheDocument();
  expect(within(row).queryByText("目标市值")).not.toBeInTheDocument();
  expect(within(row).queryByText("差额")).not.toBeInTheDocument();
  expect(within(row).queryByText("目标 40.0%")).not.toBeInTheDocument();
  expect(within(row).getByRole("link", { name: "查看个股依据 →" })).toHaveAttribute("href", "/stocks?symbol=SH.600519#stock-final-gate");
  const askHoldingHref = within(row).getByRole("link", { name: "追问这个决定 →" }).getAttribute("href") ?? "";
  expect(askHoldingHref).toContain("/ask?symbol=SH.600519");
  expect(decodeURIComponent(askHoldingHref)).toContain("10日走势+2.35%");
  expect(decodeURIComponent(askHoldingHref)).toContain("10日贡献+3,443");
  expect(within(row).getByRole("button", { name: "删除持仓 贵州茅台" })).toHaveTextContent("删除");

  expect(screen.queryByText("编辑持仓数据")).not.toBeInTheDocument();
  expect(screen.queryByText("流动性承载")).not.toBeInTheDocument();
  expect(screen.queryByText("估值安全垫")).not.toBeInTheDocument();
});

it("orders holdings by action priority before the calmer rows", async () => {
  renderPage([calmHolding, holding]);

  const rows = within(await screen.findByRole("list", { name: "持仓清单" })).getAllByRole("listitem");

  expect(rows[0]).toHaveAccessibleName(/贵州茅台/);
  expect(rows[1]).toHaveAccessibleName(/平安银行/);
});

it("keeps editing lightweight from the list row", async () => {
  renderPage();

  const list = await screen.findByRole("list", { name: "持仓清单" });
  const row = within(list).getByRole("listitem", { name: /贵州茅台/ });
  fireEvent.click(within(row).getByRole("button", { name: "展开详情 贵州茅台" }));
  expect(within(row).getByText("编辑持仓")).toBeInTheDocument();
  fireEvent.change(within(row).getByLabelText("持仓数量 贵州茅台"), { target: { value: "80" } });
  fireEvent.change(within(row).getByLabelText("成本价 贵州茅台"), { target: { value: "1420" } });
  fireEvent.click(within(row).getByRole("button", { name: "保存 贵州茅台" }));

  expect(await screen.findByText("已保存")).toBeInTheDocument();
});

it("deletes a holding from the visible row actions", async () => {
  const deletes: string[] = [];
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    if (init?.method === "DELETE") {
      deletes.push(String(input));
      return { ok: true, status: 204, json: async () => undefined };
    }
    return { ok: true, status: 200, json: async () => [holding] };
  }));
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={client}><MemoryRouter><HoldingsPage /></MemoryRouter></QueryClientProvider>);

  const row = within(await screen.findByRole("list", { name: "持仓清单" })).getByRole("listitem", { name: /贵州茅台/ });
  fireEvent.click(within(row).getByRole("button", { name: "删除持仓 贵州茅台" }));
  expect(deletes).toEqual([]);
  fireEvent.click(within(row).getByRole("button", { name: "确认删除" }));

  await waitFor(() => expect(deletes).toEqual(["/api/v1/holdings/1"]));
  expect(await screen.findByText("已删除 贵州茅台，之后不会再生成这只股票的持仓减仓提醒。")).toBeInTheDocument();
});

it("sends edited stock code and name from the holding row", async () => {
  const patchBodies: unknown[] = [];
  vi.stubGlobal("fetch", vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
    if (init?.method === "PATCH") {
      const body = JSON.parse(String(init.body));
      patchBodies.push(body);
      return { ok: true, status: 200, json: async () => ({ ...calmHolding, item: { ...calmHolding.item, ...body, symbol: "SZ.002457", name: "青龙管业" } }) };
    }
    return { ok: true, status: 200, json: async () => [holding] };
  }));
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={client}><MemoryRouter><HoldingsPage /></MemoryRouter></QueryClientProvider>);

  const row = within(await screen.findByRole("list", { name: "持仓清单" })).getByRole("listitem", { name: /贵州茅台/ });
  fireEvent.click(within(row).getByRole("button", { name: "展开详情 贵州茅台" }));
  fireEvent.change(within(row).getByLabelText("股票代码 贵州茅台"), { target: { value: "SZ.002457" } });
  fireEvent.change(within(row).getByLabelText("股票名称 贵州茅台"), { target: { value: "青龙管业" } });
  fireEvent.click(within(row).getByRole("button", { name: "保存 贵州茅台" }));

  await waitFor(() => expect(patchBodies).toEqual([
    expect.objectContaining({ symbol: "SZ.002457", name: "青龙管业" }),
  ]));
});

it("starts the create form empty so name-only additions do not reuse a default symbol", async () => {
  const requests: unknown[] = [];
  vi.stubGlobal("fetch", vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
    if (init?.method === "POST") {
      requests.push(JSON.parse(String(init.body)));
      return { ok: true, status: 201, json: async () => calmHolding };
    }
    return { ok: true, status: 200, json: async () => [] };
  }));
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={client}><MemoryRouter><HoldingsPage /></MemoryRouter></QueryClientProvider>);

  await screen.findByRole("heading", { name: "先录入真实持仓，系统才会生成调仓判断" });
  expect(screen.queryByLabelText("组合总览")).not.toBeInTheDocument();
  expect(screen.queryByLabelText("持仓排序")).not.toBeInTheDocument();
  const form = within(screen.getByRole("form", { name: "登记持仓" }));
  expect(form.getByLabelText("代码")).toHaveValue("");
  expect(form.getByLabelText("名称")).toHaveValue("");

  fireEvent.change(form.getByLabelText("名称"), { target: { value: "青龙管业" } });
  fireEvent.change(form.getByLabelText("数量"), { target: { value: "1000" } });
  fireEvent.change(form.getByLabelText("成本"), { target: { value: "10" } });
  fireEvent.change(form.getByLabelText("持仓逻辑"), { target: { value: "水泥建材修复观察" } });
  fireEvent.change(form.getByLabelText("什么情况下减仓或退出"), { target: { value: "跌破支撑" } });
  fireEvent.click(form.getByRole("button", { name: "加入持仓" }));

  await waitFor(() => expect(requests).toEqual([
    {
      symbol: "",
      name: "青龙管业",
      quantity: 1000,
      cost_price: 10,
      thesis: "水泥建材修复观察",
      invalidation: "跌破支撑",
    },
  ]));
  await waitFor(() => expect(form.getByLabelText("名称")).toHaveValue(""));
});

it("clears stale default create values before adding another holding", async () => {
  const requests: unknown[] = [];
  vi.stubGlobal("fetch", vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
    if (init?.method === "POST") {
      requests.push(JSON.parse(String(init.body)));
      return { ok: true, status: 201, json: async () => calmHolding };
    }
    return { ok: true, status: 200, json: async () => [holding] };
  }));
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={client}><MemoryRouter><HoldingsPage /></MemoryRouter></QueryClientProvider>);

  await screen.findByRole("list", { name: "持仓清单" });
  const form = within(screen.getByRole("form", { name: "登记持仓" }));
  fireEvent.change(form.getByLabelText("代码"), { target: { value: "SH.600519" } });
  fireEvent.change(form.getByLabelText("名称"), { target: { value: "贵州茅台" } });
  fireEvent.change(form.getByLabelText("名称"), { target: { value: "平安银行" } });
  fireEvent.change(form.getByLabelText("数量"), { target: { value: "2000" } });
  fireEvent.change(form.getByLabelText("成本"), { target: { value: "11" } });
  fireEvent.change(form.getByLabelText("持仓逻辑"), { target: { value: "低波红利观察" } });
  fireEvent.change(form.getByLabelText("什么情况下减仓或退出"), { target: { value: "银行板块走弱" } });
  fireEvent.click(form.getByRole("button", { name: "加入持仓" }));

  await waitFor(() => expect(requests).toEqual([
    expect.objectContaining({ symbol: "", name: "平安银行" }),
  ]));
});

it("shows duplicate feedback and clears the form when an existing holding is submitted", async () => {
  vi.stubGlobal("fetch", vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
    if (init?.method === "POST") {
      return { ok: true, status: 201, json: async () => holding };
    }
    return { ok: true, status: 200, json: async () => [holding] };
  }));
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={client}><MemoryRouter><HoldingsPage /></MemoryRouter></QueryClientProvider>);

  await screen.findByRole("list", { name: "持仓清单" });
  const form = within(screen.getByRole("form", { name: "登记持仓" }));
  fireEvent.change(form.getByLabelText("代码"), { target: { value: "SH.600519" } });
  fireEvent.change(form.getByLabelText("名称"), { target: { value: "贵州茅台" } });
  fireEvent.change(form.getByLabelText("数量"), { target: { value: "100" } });
  fireEvent.change(form.getByLabelText("成本"), { target: { value: "1400" } });
  fireEvent.change(form.getByLabelText("持仓逻辑"), { target: { value: "重复提交" } });
  fireEvent.change(form.getByLabelText("什么情况下减仓或退出"), { target: { value: "重复提交" } });
  fireEvent.click(form.getByRole("button", { name: "加入持仓" }));

  expect(await screen.findByText("这只股票已在持仓列表，未新增；已清空表单，可直接输入第二只。")).toBeInTheDocument();
  await waitFor(() => expect(form.getByLabelText("代码")).toHaveValue(""));
});

it("fills default research notes when optional create fields are left empty", async () => {
  const requests: unknown[] = [];
  vi.stubGlobal("fetch", vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
    if (init?.method === "POST") {
      requests.push(JSON.parse(String(init.body)));
      return { ok: true, status: 201, json: async () => calmHolding };
    }
    return { ok: true, status: 200, json: async () => [] };
  }));
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={client}><MemoryRouter><HoldingsPage /></MemoryRouter></QueryClientProvider>);

  const form = within(await screen.findByRole("form", { name: "登记持仓" }));
  fireEvent.change(form.getByLabelText("名称"), { target: { value: "大金重工" } });
  fireEvent.change(form.getByLabelText("数量"), { target: { value: "800" } });
  fireEvent.change(form.getByLabelText("成本"), { target: { value: "76.5740" } });
  fireEvent.click(form.getByRole("button", { name: "加入持仓" }));

  await waitFor(() => expect(requests).toEqual([
    expect.objectContaining({
      name: "大金重工",
      thesis: "大金重工 持仓逻辑待补充，先按价格、资金和板块证据复核。",
      invalidation: "跌破成本、趋势破位或基本面证据转弱时复核降仓或退出。",
    }),
  ]));
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
    conclusion: "建议动作：风控复核。亏损 -34.82% 已触发风控，风控优先。建议先做风控复核。",
    risk_flags: ["亏损超过 10%"],
  };
  vi.stubGlobal("fetch", vi.fn(async () => ({ ok: true, status: 200, json: async () => [exitHolding] })));
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={client}><MemoryRouter><HoldingsPage /></MemoryRouter></QueryClientProvider>);

  const list = await screen.findByRole("list", { name: "持仓清单" });
  const row = within(list).getByRole("listitem", { name: /风控样本/ });

  expect(within(row).getAllByText("优先减仓或止损").length).toBeGreaterThan(0);
  expect(within(row).queryByText("退出观察")).not.toBeInTheDocument();
  expect(within(row).getAllByText(/已触发风控|风控优先/).length).toBeGreaterThan(0);
  expect(within(row).queryByText(/加仓复核/)).not.toBeInTheDocument();
  expect(within(row).queryByText(/\+4,756 股/)).not.toBeInTheDocument();
});
