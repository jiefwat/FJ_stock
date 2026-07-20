import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";

import { StockLabPage } from "./StockLabPage";

const dossier = {
  quote: { symbol: "SH.600519", code: "600519", name: "贵州茅台", price: 1253, change_pct: -0.48, amount: 1, turnover_rate: 1, volume_ratio: null, pe: 23, pb: 7, market_cap: 1, net_flow: null, sector: null },
  stance: "neutral", stance_score: 57, evidence_coverage: 0.55,
  conclusion: "总结论：贵州茅台 当前为中性（57/100），暂不形成明确倾向，但不是买卖指令。投资建议：等待回踩；暂不追高，等价格回到支撑/MA20 附近再评估；入场：把 1168.63 作为跟踪放弃线，跌破后重新评估；止损：跌破 1168.63 且无法快速收回，放弃本轮跟踪；止盈：接近 1327.50 时至少复核量能、资金流和板块温度。技术面：收盘价位于 20 日均线之上；MA5 位于 MA20 之上；MA20 低于 MA60。风险收益：距压力位 0.0%，距支撑位 -12.0%，风险收益比 0.00。估值：PE 20.2，PB 6.1，PE 20.2 位于约束区间。流动性：成交额 139.0 亿，换手率 0.85%，量比暂缺。基本面：基本面质量用估值、规模和公告研报交叉验证；PE 20.2，PB 6.1，总市值 16594.8 亿。催化：催化与事件待补齐，不能只用价格波动解释上涨。资金/行业：主力净流入 +3.9 亿，资金态度偏正向；已映射到 白酒Ⅱ，需要和板块温度联动复核。横向对比：相对白酒同业涨跌强度处于约 42 分位；PE 20.2 相对白酒同业估值吸引力约 68 分位。纵向对比：过去 20 日累计涨跌 5.1%；过去 60 日累计涨跌 12.4%。交易计划：交易计划先定义放弃线、压力位和复核节奏；放弃线 1168.63，压力位 1327.50，波动率 29.1%。主要风险：MA20 低于 MA60、RSI 79.2 显示短线过热；若 跌破近 20 日支撑 1168.63 则关注理由失效。下一步：把 1168.63 作为跟踪放弃线，跌破后重新评估。仍需补齐公告与研报增强数据。",
  score_factors: [
    { key: "price_ma20", label: "价格与 MA20", impact: 10, signal: "positive", evidence: "收盘价位于 20 日均线之上", available: true },
    { key: "volatility", label: "波动风险", impact: -8, signal: "negative", evidence: "年化波动率偏高", available: true },
  ],
  technical: { ma5: 1237, ma20: 1204, ma60: 1265, rsi14: 66, volatility20: 21, support: 1168, resistance: 1259 },
  bull_case: ["收盘价位于 20 日均线之上"], bear_case: ["MA20 低于 MA60"],
  invalidation: ["跌破近 20 日支撑 1168.00"], missing_evidence: [],
  research_evidence: ["近三十日有分红相关公告", "研报关注现金流与渠道库存"],
  analysis_dimensions: [
    { key: "trend", label: "趋势结构", signal: "positive", score: 75, summary: "价格站上 MA20，短线趋势占优", evidence: ["MA5 位于 MA20 之上"] },
    { key: "risk_reward", label: "风险收益", signal: "neutral", score: 52, summary: "距离压力位 1.2%，距离支撑位 6.8%，风险收益比一般", evidence: ["上方压力 1259", "下方支撑 1168"] },
    { key: "valuation", label: "估值与流动性", signal: "positive", score: 66, summary: "PE 23.0，成交额可支撑跟踪", evidence: ["PE 位于约束区间", "成交额 8.5 亿"] },
    { key: "fundamental_quality", label: "基本面质量", signal: "positive", score: 68, summary: "现金流与盈利质量需要结合公告复核", evidence: ["分红稳定", "渠道库存修复"] },
    { key: "catalyst", label: "催化与事件", signal: "neutral", score: 60, summary: "公告和研报给出可跟踪催化", evidence: ["分红公告", "渠道库存研报"] },
    { key: "risk_controls", label: "交易计划", signal: "neutral", score: 58, summary: "先定义复核节奏和失效条件", evidence: ["回踩不破 MA20", "跌破支撑退出"] },
  ],
  investment_advice: {
    action: "等待回踩",
    position_hint: "暂不追高，等价格回到支撑/MA20 附近再评估",
    entry_plan: "把 1168.63 作为跟踪放弃线，跌破后重新评估",
    stop_loss: "跌破 1168.63 且无法快速收回，放弃本轮跟踪",
    take_profit: "接近 1327.50 时至少复核量能、资金流和板块温度",
    time_horizon: "1-4 周滚动复盘，跌破放弃线或证据恶化立即重评",
    confidence: 0.62,
    rationale: ["趋势结构中性", "横向同业估值一般", "过去 60 日累计涨跌 12.4%"],
    disclaimer: "研究建议不是保证收益，不能替代你的风险承受能力判断。",
  },
  horizontal_comparison: [
    { key: "sector_change_rank", label: "涨跌强弱", signal: "neutral", value: "-0.48%", benchmark: "白酒同业", summary: "相对行业涨跌强度处于约 42 分位", percentile: 42, available: true },
    { key: "sector_pe_position", label: "估值位置", signal: "positive", value: "PE 20.2", benchmark: "白酒同业 PE 中位 28.1", summary: "PE 20.2 相对行业估值吸引力约 68 分位", percentile: 68, available: true },
  ],
  vertical_comparison: [
    { key: "return_20d", label: "20日收益", signal: "positive", value: "5.1%", benchmark: "自身过去 20 日", summary: "过去 20 日累计涨跌 5.1%", percentile: null, available: true },
    { key: "return_60d", label: "60日收益", signal: "positive", value: "12.4%", benchmark: "自身过去 60 日", summary: "过去 60 日累计涨跌 12.4%", percentile: null, available: true },
    { key: "range_position_60d", label: "60日区间位置", signal: "neutral", value: "73%", benchmark: "自身 60 日价格区间", summary: "现价处于过去 60 日价格区间约 73% 位置", percentile: 73, available: true },
  ],
  next_actions: ["等回踩不破 MA20", "补齐公告与研报", "复核基本面质量", "跟踪催化兑现"],
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
  return render(<QueryClientProvider client={client}><MemoryRouter initialEntries={["/stocks?symbol=SH.600519"]}><StockLabPage /></MemoryRouter></QueryClientProvider>);
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("shows the evidence ledger and edits the thesis before adding to watchlist", async () => {
  renderPage();

  expect(await screen.findByLabelText("价格趋势图")).toBeInTheDocument();
  expect(screen.getByText("收盘价")).toBeInTheDocument();
  expect(screen.getByText("证据覆盖 55%")).toBeInTheDocument();
  expect(screen.getByText("总结论")).toBeInTheDocument();
  expect(screen.getAllByText(/不是买卖指令/).length).toBeGreaterThan(0);
  expect(screen.getByText("波动风险")).toBeInTheDocument();
  expect(screen.getByText("语义研究增强")).toBeInTheDocument();
  expect(screen.getByText(/近三十日有分红相关公告/)).toBeInTheDocument();
  expect(screen.getByText("分析拆解")).toBeInTheDocument();
  expect(screen.getByText("趋势结构")).toBeInTheDocument();
  expect(screen.getAllByText("风险收益").length).toBeGreaterThan(0);
  expect(screen.getByText("基本面质量")).toBeInTheDocument();
  expect(screen.getByText("催化与事件")).toBeInTheDocument();
  expect(screen.getAllByText("交易计划").length).toBeGreaterThan(0);
  expect(screen.getByText("下一步看什么")).toBeInTheDocument();
  expect(screen.queryByText(/iWenCai|WenCai|问财/i)).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "加入跟踪" }));
  expect(screen.getByLabelText("关注理由")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("关注理由"), { target: { value: "等待估值与趋势共振" } });
  fireEvent.click(screen.getByRole("button", { name: "保存到跟踪清单" }));

  expect(await screen.findByRole("link", { name: "已跟踪 · 编辑记录" })).toBeInTheDocument();
  expect(screen.getByRole("status")).toHaveTextContent("已加入跟踪");
});

it("formats the generated stock conclusion into a scannable analyst brief", async () => {
  const { container } = renderPage();

  const brief = within(await screen.findByLabelText("结构化总结论"));
  expect(brief.getByText("当前判断")).toBeInTheDocument();
  expect(brief.getByText("中性")).toBeInTheDocument();
  expect(brief.getByText("57/100")).toBeInTheDocument();
  expect(brief.getByText("怎么读")).toBeInTheDocument();
  const readSummary = brief.getByText(/暂不形成明确倾向/);
  expect(readSummary).toBeInTheDocument();
  expect(readSummary).not.toHaveTextContent("投资建议");
  expect(readSummary).not.toHaveTextContent("横向对比");
  expect(readSummary).not.toHaveTextContent("纵向对比");
  expect(brief.getByText("关键依据")).toBeInTheDocument();
  expect(brief.getByText("技术面")).toBeInTheDocument();
  expect(brief.getByText("风险收益")).toBeInTheDocument();
  expect(brief.getByText("估值")).toBeInTheDocument();
  expect(brief.getByText("流动性")).toBeInTheDocument();
  expect(brief.getByText("基本面")).toBeInTheDocument();
  expect(brief.getByText("催化")).toBeInTheDocument();
  expect(brief.getByText("资金/行业")).toBeInTheDocument();
  expect(brief.getByText("操作纪律")).toBeInTheDocument();
  expect(brief.getByText("交易计划")).toBeInTheDocument();
  expect(brief.getByText("主要风险")).toBeInTheDocument();
  expect(brief.getByText("下一步")).toBeInTheDocument();
  expect(container.querySelector(".stock-conclusion > p")).not.toBeInTheDocument();
});

it("surfaces an analyst action map before the deep evidence sections", async () => {
  renderPage();

  const actionMapElement = await screen.findByLabelText("个股分析路径");
  const actionMap = within(actionMapElement);
  expect(actionMap.getByText("先看支撑")).toBeInTheDocument();
  expect(actionMap.getByText("收盘价位于 20 日均线之上")).toBeInTheDocument();
  expect(actionMap.getByText("再看风险")).toBeInTheDocument();
  expect(actionMap.getByText("MA20 低于 MA60")).toBeInTheDocument();
  expect(actionMap.getByText("证据缺口")).toBeInTheDocument();
  expect(actionMap.getByText("没有明显缺口，继续按当前证据复盘")).toBeInTheDocument();
  expect(actionMap.getByText("下一步动作")).toBeInTheDocument();
  expect(actionMap.getByText("等回踩不破 MA20")).toBeInTheDocument();
  const conclusion = await screen.findByLabelText("结构化总结论");
  expect(actionMapElement.compareDocumentPosition(conclusion) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
});

it("shows direct investment advice with horizontal and vertical comparisons", async () => {
  renderPage();

  const advice = within(await screen.findByLabelText("直接投资建议"));
  expect(advice.getByText("等待回踩")).toBeInTheDocument();
  expect(advice.getByText(/暂不追高/)).toBeInTheDocument();
  expect(advice.getByText("入场计划")).toBeInTheDocument();
  expect(advice.getByText("止损纪律")).toBeInTheDocument();
  expect(advice.getByText("止盈复核")).toBeInTheDocument();
  expect(advice.getByText(/研究建议不是保证收益/)).toBeInTheDocument();

  const comparison = within(await screen.findByLabelText("横向纵向对比"));
  expect(comparison.getByText("横向对比")).toBeInTheDocument();
  expect(comparison.getByText("涨跌强弱")).toBeInTheDocument();
  expect(comparison.getByText("估值位置")).toBeInTheDocument();
  expect(comparison.getByText(/相对行业涨跌强度/)).toBeInTheDocument();
  expect(comparison.getByText("纵向对比")).toBeInTheDocument();
  expect(comparison.getByText("20日收益")).toBeInTheDocument();
  expect(comparison.getByText("60日区间位置")).toBeInTheDocument();
  expect(comparison.getAllByText(/过去 60 日/).length).toBeGreaterThan(0);

  const adviceSection = await screen.findByLabelText("直接投资建议");
  const comparisonSection = await screen.findByLabelText("横向纵向对比");
  const conclusionSection = await screen.findByLabelText("结构化总结论");
  expect(adviceSection.compareDocumentPosition(comparisonSection) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(comparisonSection.compareDocumentPosition(conclusionSection) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
});

it("recognizes an existing watchlist item before another post", async () => {
  renderPage([{ id: 1, symbol: "SH.600519", name: "贵州茅台", thesis: "已有逻辑", invalidation: "已有失效条件", status: "researching", updated_at: "2026-07-19T09:00:00Z" }]);

  expect(await screen.findByRole("link", { name: "已跟踪 · 编辑记录" })).toBeInTheDocument();
  await waitFor(() => expect(screen.queryByRole("button", { name: "加入跟踪" })).not.toBeInTheDocument());
});
