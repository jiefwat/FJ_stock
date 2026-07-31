import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";

import { StockLabPage } from "./StockLabPage";

const dossier = {
  quote: { symbol: "SH.600519", code: "600519", name: "贵州茅台", price: 1253, change_pct: -0.48, amount: 1, turnover_rate: 1, volume_ratio: null, pe: 23, pb: 7, market_cap: 1, net_flow: null, sector: null },
  stance: "neutral", stance_score: 57, evidence_coverage: 0.55,
  conclusion: "总结论：贵州茅台 当前为中性（57/100），暂不形成明确倾向，但仅供研究。投资建议：等待回踩；暂不追高，等价格回到支撑/MA20 附近再评估；入场：把 1168.63 作为跟踪放弃线，跌破后重新评估；止损：跌破 1168.63 且无法快速收回，放弃本轮跟踪；止盈：接近 1327.50 时至少复核量能、资金流和板块温度。技术面：收盘价位于 20 日均线之上；MA5 位于 MA20 之上；MA20 低于 MA60。风险收益：距压力位 0.0%，距支撑位 -12.0%，风险收益比 0.00。估值：PE 20.2，PB 6.1，PE 20.2 位于约束区间。流动性：成交额 139.0 亿，换手率 0.85%，量比暂缺。基本面：基本面质量用估值、规模和公告研报交叉验证；PE 20.2，PB 6.1，总市值 16594.8 亿。催化：催化与事件待补齐，不能只用价格波动解释上涨。资金/行业：主力净流入 +3.9 亿，资金态度偏正向；已映射到 白酒Ⅱ，需要和板块温度联动复核。横向对比：相对白酒同业涨跌强度处于约 42 分位；PE 20.2 相对白酒同业估值吸引力约 68 分位。纵向对比：过去 20 日累计涨跌 5.1%；过去 60 日累计涨跌 12.4%。交易计划：交易计划先定义放弃线、压力位和复核节奏；放弃线 1168.63，压力位 1327.50，波动率 29.1%。主要风险：MA20 低于 MA60、RSI 79.2 显示短线过热；若 跌破近 20 日支撑 1168.63 则关注理由失效。下一步：把 1168.63 作为跟踪放弃线，跌破后重新评估。仍需补齐公告与研报增强数据。",
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
  trend_forecast: {
    horizon: "未来 1-4 周",
    direction: "偏强震荡",
    confidence: 0.68,
    summary: "未来 1-4 周偏强震荡：MA5/MA20 保持多头，但上方压力位需要放量突破。",
    drivers: ["MA5/MA20 短线结构占优", "资金流仍需连续确认", "接近压力位，追高性价比一般"],
    invalidation: "跌破 1168.00 后趋势判断失效",
  },
  signal_validation: {
    available: true,
    horizon_days: 20,
    sample_count: 18,
    positive_rate: 0.67,
    average_return: 3.2,
    worst_return: -6.4,
    summary: "历史滚动样本仅作描述，不直接计入实时评分。",
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

const evidence = {
  symbol: "SH.600519",
  filings: [{
    id: "cninfo:1", kind: "filing", symbol: "SH.600519", title: "年度权益分派实施公告", category: "权益分派", publisher: "巨潮资讯", published_at: "2026-07-27T08:00:00Z", url: "https://example.com/filing", rating: null, eps_forecasts: {},
    source: { provider: "cninfo", label: "巨潮资讯", capability: "filings", source_url: "https://example.com/filing", observed_at: "2026-07-27T08:00:00Z", fetched_at: "2026-07-28T08:00:00Z", freshness: "fresh" },
  }],
  research: [{
    id: "eastmoney-report:1", kind: "research", symbol: "SH.600519", title: "渠道韧性延续，长期价值稳固", category: "白酒", publisher: "测试证券", published_at: "2026-07-26T08:00:00Z", url: "https://example.com/report.pdf", rating: "增持", eps_forecasts: { current_year: 68.2 },
    source: { provider: "eastmoney_report", label: "东方财富研报", capability: "research", source_url: "https://example.com/report.pdf", observed_at: "2026-07-26T08:00:00Z", fetched_at: "2026-07-28T08:00:00Z", freshness: "fresh" },
  }],
  themes: [{
    code: "BK0896", name: "酿酒概念", change_pct: 1.8, lead_stock: "贵州茅台",
    source: { provider: "eastmoney_theme", label: "东方财富题材归属", capability: "themes", source_url: "https://example.com/themes", observed_at: "2026-07-28T08:00:00Z", fetched_at: "2026-07-28T08:00:00Z", freshness: "fresh" },
  }],
  capabilities: {
    filings: { status: "ready", provider: "cninfo", error: null, fetched_at: "2026-07-28T08:00:00Z" },
    research: { status: "ready", provider: "eastmoney_report", error: null, fetched_at: "2026-07-28T08:00:00Z" },
    themes: { status: "ready", provider: "eastmoney_theme", error: null, fetched_at: "2026-07-28T08:00:00Z" },
  },
};

function renderPage(authenticated = true, route = "/stocks?symbol=SH.600519", evidencePayload: object = evidence) {
  const storage = new Map<string, string>();
  if (authenticated) storage.set("marketdesk.accessToken", "fixture-token");
  vi.stubGlobal("localStorage", {
    getItem: (key: string) => storage.get(key) ?? null,
    setItem: (key: string, value: string) => { storage.set(key, value); },
    removeItem: (key: string) => { storage.delete(key); },
  });
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.includes("/search")) return { ok: true, status: 200, json: async () => [] };
    if (url.includes("/evidence")) return { ok: true, status: 200, json: async () => evidencePayload };
    return { ok: true, status: 200, json: async () => dossier };
  });
  vi.stubGlobal("fetch", fetchMock);
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return {
    fetchMock,
    storage,
    ...render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[route]}><StockLabPage /></MemoryRouter></QueryClientProvider>),
  };
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("explains when a stock dossier is opened from opportunity leads", async () => {
  renderPage(true, "/stocks?symbol=SH.600519&from=opportunities&preset=trend");

  const sourceNote = within(await screen.findByLabelText("线索来源"));
  expect(sourceNote.getByText("机会")).toBeInTheDocument();
  expect(sourceNote.getByText("趋势延续")).toBeInTheDocument();
  expect(screen.queryByLabelText("线索结果")).not.toBeInTheDocument();
  expect(await screen.findByLabelText("直接投资建议")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "问股" })).toHaveAttribute(
    "href",
    "/ask?symbol=SH.600519&name=%E8%B4%B5%E5%B7%9E%E8%8C%85%E5%8F%B0&from=opportunities&preset=trend",
  );
});

it("explains when a stock dossier is opened from a market board", async () => {
  renderPage(true, "/stocks?symbol=SH.600519&from=market&board=BK1&boardName=白酒&boardType=板块");

  const sourceNote = within(await screen.findByLabelText("板块来源"));
  expect(sourceNote.getByText("白酒")).toBeInTheDocument();
  expect(sourceNote.getByText("板块")).toBeInTheDocument();
  expect(await screen.findByLabelText("依据")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "问股" })).toHaveAttribute(
    "href",
    "/ask?symbol=SH.600519&name=%E8%B4%B5%E5%B7%9E%E8%8C%85%E5%8F%B0&from=market&board=BK1&boardName=%E7%99%BD%E9%85%92&boardType=%E6%9D%BF%E5%9D%97",
  );
});

it("shows the evidence ledger and keeps Ask Stock as the primary action", async () => {
  renderPage();

  expect(await screen.findByText("贵州茅台")).toBeInTheDocument();
  expect(screen.getByText("等待回踩")).toBeInTheDocument();
  expect(screen.getByText(/证据 55%/)).toBeInTheDocument();
  const audit = within(await screen.findByLabelText("依据"));
  expect(screen.getByLabelText("依据")).toHaveAttribute("id", "stock-evidence-audit");
  expect(audit.getByText("为什么")).toBeInTheDocument();
  expect(audit.getByText("趋势结构中性")).toBeInTheDocument();
  expect(screen.queryByText("分析拆解")).not.toBeVisible();
  fireEvent.click(screen.getByText("明细"));
  expect(await screen.findByLabelText("价格趋势图")).toBeInTheDocument();
  expect(screen.getByText("评分明细")).toBeInTheDocument();
  expect(screen.getByText("波动风险")).toBeInTheDocument();
  expect(screen.getByText("语义研究")).toBeInTheDocument();
  expect(screen.getAllByText(/近三十日有分红相关公告/).length).toBeGreaterThan(0);
  expect(screen.queryByText(/iWenCai|WenCai|问财/i)).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: "问股" })).toHaveAttribute(
    "href",
    "/ask?symbol=SH.600519&name=%E8%B4%B5%E5%B7%9E%E8%8C%85%E5%8F%B0&from=stock",
  );
  expect(screen.queryByRole("button", { name: "加入跟踪" })).not.toBeInTheDocument();
  expect(screen.queryByText("保存到跟踪清单")).not.toBeInTheDocument();
});

it("shows cited filings, research reports, and themes without changing the score", async () => {
  const { container } = renderPage();

  await screen.findByText("明细");
  expect(container.querySelector(".stock-deep-dossier")).not.toHaveAttribute("open");
  fireEvent.click(screen.getByText("明细"));
  expect(container.querySelector(".stock-deep-dossier")).toHaveAttribute("open");

  const panel = within(await screen.findByLabelText("公司证据包"));
  expect(screen.getByLabelText("公司证据包")).toHaveAttribute("id", "stock-company-evidence");
  expect(panel.getByText("年度权益分派实施公告")).toBeInTheDocument();
  expect(panel.getByRole("link", { name: "年度权益分派实施公告" })).toHaveAttribute("href", "https://example.com/filing");
  expect(panel.getByText("渠道韧性延续，长期价值稳固")).toBeInTheDocument();
  expect(panel.getByText(/测试证券 · 增持 · 白酒/)).toBeInTheDocument();
  expect(panel.getByText("酿酒概念")).toBeInTheDocument();
  expect(panel.getByRole("link", { name: /酿酒概念/ })).toHaveAttribute(
    "href",
    "/market?theme=BK0896&themeName=%E9%85%BF%E9%85%92%E6%A6%82%E5%BF%B5&themeChange=1.8",
  );
  expect(panel.queryByText(/仅作研究上下文/)).not.toBeInTheDocument();
  expect(screen.getAllByText("57/100").length).toBeGreaterThan(0);
});

it("opens the compact evidence package automatically for deep evidence anchors", async () => {
  const { container } = renderPage(true, "/stocks?symbol=SH.600519#stock-company-evidence");

  await screen.findByText("明细");
  expect(container.querySelector(".stock-deep-dossier")).toHaveAttribute("open");
  expect(await screen.findByLabelText("公司证据包")).toHaveAttribute("id", "stock-company-evidence");
});

it("keeps available evidence visible when one source is unavailable", async () => {
  renderPage(true, "/stocks?symbol=SH.600519", {
    ...evidence,
    research: [],
    capabilities: {
      ...evidence.capabilities,
      research: { status: "unavailable", provider: "eastmoney_report", error: "upstream timeout", fetched_at: "2026-07-28T08:00:00Z" },
    },
  });

  const panel = within(await screen.findByLabelText("公司证据包"));
  expect(panel.getByText("年度权益分派实施公告")).toBeInTheDocument();
  expect(panel.getByText("研报源暂不可用，公告与题材仍可继续核验。")).toBeInTheDocument();
});

it("formats the generated stock conclusion into a scannable analyst brief", async () => {
  const { container } = renderPage();

  const brief = within(await screen.findByLabelText("结构化总结论"));
  expect(brief.getByText("当前判断")).toBeInTheDocument();
  expect(brief.getByText("中性")).toBeInTheDocument();
  expect(brief.getByText("57/100")).toBeInTheDocument();
  expect(brief.getByText("摘要")).toBeInTheDocument();
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

  expect(screen.queryByLabelText("个股复核路线")).not.toBeInTheDocument();

  const deck = within(await screen.findByLabelText("个股结论"));
  expect(screen.getByLabelText("个股结论")).toHaveAttribute("id", "stock-final-gate");
  expect(deck.getByText("贵州茅台")).toBeInTheDocument();
  expect(deck.getByText("等待回踩")).toBeInTheDocument();
  expect(deck.getByText("置信")).toBeInTheDocument();
  expect(deck.getAllByText("趋势").length).toBeGreaterThan(0);
  expect(deck.getByText("怎么做")).toBeInTheDocument();
  expect(deck.getByText("为什么")).toBeInTheDocument();
  expect(deck.getByText("风险")).toBeInTheDocument();
  await waitFor(() => expect(deck.getByRole("link", { name: "看板块" })).toHaveAttribute(
    "href",
    "/market?theme=BK0896&themeName=%E9%85%BF%E9%85%92%E6%A6%82%E5%BF%B5&themeChange=1.8",
  ));

  const advice = within(await screen.findByLabelText("直接投资建议"));
  expect(screen.getByLabelText("直接投资建议")).toHaveAttribute("id", "stock-investment-advice");
  expect(advice.getByText(/暂不追高/)).toBeInTheDocument();
  expect(advice.getByText("入场")).toBeInTheDocument();
  expect(advice.getByText("止损")).toBeInTheDocument();
  expect(advice.getByText("止盈")).toBeInTheDocument();

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
  expect(screen.getByText("明细")).toBeInTheDocument();
  expect(comparisonSection.compareDocumentPosition(conclusionSection) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
});

it("shows a future trend forecast before detailed evidence", async () => {
  renderPage();

  const forecast = within(await screen.findByLabelText("未来趋势判断"));
  expect(forecast.getByText("偏强震荡")).toBeInTheDocument();

  const forecastSection = await screen.findByLabelText("未来趋势判断");
  const auditSection = await screen.findByLabelText("依据");
  fireEvent.click(screen.getByText("明细"));
  const evidenceLedger = await screen.findByText("评分明细");
  expect(auditSection.compareDocumentPosition(forecastSection) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(forecastSection.compareDocumentPosition(evidenceLedger) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
});

it("offers intent-aware Ask Stock shortcuts after the final gate", async () => {
  renderPage();

  const router = within(await screen.findByLabelText("个股问股快捷入口"));
  expect(router.getByText("问股")).toBeInTheDocument();
  expect(router.getByText("继续问")).toBeInTheDocument();
  expect(router.getByRole("link", { name: /问风险/ })).toHaveAttribute(
    "href",
    `/ask?${new URLSearchParams({ symbol: "SH.600519", name: "贵州茅台", from: "stock", question: "贵州茅台现在主要风险是什么" }).toString()}`,
  );
  expect(router.getByRole("link", { name: /问异动/ })).toHaveAttribute(
    "href",
    `/ask?${new URLSearchParams({ symbol: "SH.600519", name: "贵州茅台", from: "stock", question: "最近贵州茅台怎么大跌" }).toString()}`,
  );
  expect(router.getByRole("link", { name: /问基本面/ })).toHaveAttribute(
    "href",
    `/ask?${new URLSearchParams({ symbol: "SH.600519", name: "贵州茅台", from: "stock", question: "贵州茅台基本面怎么样" }).toString()}`,
  );
  expect(router.getByRole("link", { name: /问催化/ })).toHaveAttribute(
    "href",
    `/ask?${new URLSearchParams({ symbol: "SH.600519", name: "贵州茅台", from: "stock", question: "贵州茅台有什么公告催化" }).toString()}`,
  );

  const finalGate = await screen.findByLabelText("个股结论");
  const askRouter = await screen.findByLabelText("个股问股快捷入口");
  const details = await screen.findByText("明细");
  expect(finalGate.compareDocumentPosition(askRouter) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(askRouter.compareDocumentPosition(details) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
});

it("shows descriptive historical validation without changing the page structure", async () => {
  renderPage();

  const validationElement = await screen.findByLabelText("历史信号验证");
  const validation = within(validationElement);
  expect(validation.getByText("18 个样本")).toBeInTheDocument();
  expect(validation.getByText("67%")).toBeInTheDocument();
  expect(validation.getByText("+3.20%")).toBeInTheDocument();
  expect(validation.getByText("-6.40%")).toBeInTheDocument();
  expect(validation.getByText(/不直接计入实时评分/)).toBeInTheDocument();

  const forecast = await screen.findByLabelText("未来趋势判断");
  const comparison = await screen.findByLabelText("横向纵向对比");
  expect(
    forecast.compareDocumentPosition(validationElement) & Node.DOCUMENT_POSITION_FOLLOWING,
  ).toBeTruthy();
  expect(
    validationElement.compareDocumentPosition(comparison) & Node.DOCUMENT_POSITION_FOLLOWING,
  ).toBeTruthy();
});

it("does not request the removed watchlist module before login", async () => {
  const { fetchMock } = renderPage(false);

  expect(await screen.findByText("贵州茅台")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "登录后加入跟踪" })).not.toBeInTheDocument();
  await waitFor(() => {
    expect(fetchMock.mock.calls.some(([input]) => String(input).includes("/watchlist"))).toBe(false);
  });
});

it("remembers the opened stock for the global research router", async () => {
  const { storage } = renderPage();

  expect(await screen.findByText("贵州茅台")).toBeInTheDocument();
  await waitFor(() => {
    const raw = storage.get("marketdesk.recentResearch.v1.fixture-token");
    expect(raw).toBeTruthy();
    const parsed = JSON.parse(raw ?? "{}") as { items?: Array<{ symbol: string; name: string }> };
    expect(parsed.items?.[0]).toMatchObject({ symbol: "SH.600519", name: "贵州茅台" });
  });
});
