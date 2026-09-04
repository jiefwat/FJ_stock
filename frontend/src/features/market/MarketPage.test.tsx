import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router-dom";
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

const dashboard = {
  meta: market.snapshot.meta,
  score: 58,
  regime: "balanced",
  confidence: 0.95,
  breadth_pct: 60.78,
  capital_inflow_pct: 54.2,
  total_turnover: 1_250_000_000_000,
  limit_up_count: 42,
  limit_down_count: 6,
  distribution: [
    { key: "strong_down", label: "≤ -5%", count: 90, tone: "strong_down" },
    { key: "down", label: "-5% ~ -1%", count: 1100, tone: "down" },
    { key: "flat", label: "-1% ~ 1%", count: 1500, tone: "flat" },
    { key: "up", label: "1% ~ 5%", count: 2000, tone: "up" },
    { key: "strong_up", label: "≥ 5%", count: 410, tone: "strong_up" },
  ],
  strongest_sectors: market.snapshot.sectors,
  weakest_sectors: [{ code: "BK2", name: "银行", change_pct: -1.2, net_flow: -100000000 }],
  activity_leaders: [
    { symbol: "SH.600519", code: "600519", name: "贵州茅台", price: 1500, change_pct: 1.2, amount: 2000000000, turnover_rate: 0.8, volume_ratio: 1.1, pe: 23, pb: 7, market_cap: 1900000000000, net_flow: 80000000, sector: "白酒" },
  ],
  missing_evidence: [],
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

const theme = {
  sector: { code: "BK0896", name: "酿酒概念", change_pct: 1.8, net_flow: null },
  summary: ["题材涨跌 1.80%，热度中性，资金流仍待增强源确认。"],
  evidence_coverage: 2 / 3,
  missing_evidence: ["板块资金流"],
  constituents: [
    { symbol: "SH.600519", code: "600519", name: "贵州茅台", price: 1500, change_pct: 1.2, amount: 2000000000, turnover_rate: 0.8, volume_ratio: 1.1, pe: 23, pb: 7, market_cap: 1900000000000, net_flow: null, sector: "酿酒概念" },
  ],
};

const flowSector = {
  sector: { code: "BK1031", name: "电力设备", change_pct: 2.4, net_flow: 6466000000 },
  summary: ["主力净流入 64.66 亿，板块热度偏强。"],
  evidence_coverage: 1,
  missing_evidence: [],
  constituents: [
    { symbol: "SZ.002475", code: "002475", name: "立讯精密", price: 42.5, change_pct: 9.99, amount: 2000000000, turnover_rate: 8.5, volume_ratio: 1.1, pe: 23, pb: 7, market_cap: 1900000000000, net_flow: 120000000, sector: "电力设备" },
    { symbol: "SZ.300750", code: "300750", name: "宁德时代", price: 188.2, change_pct: -1.25, amount: 5200000000, turnover_rate: 2.4, volume_ratio: 0.9, pe: 18, pb: 4, market_cap: 890000000000, net_flow: -30000000, sector: "电力设备" },
    { symbol: "SZ.300274", code: "300274", name: "阳光电源", price: 92.8, change_pct: 12.4, amount: 1100000000, turnover_rate: 5.2, volume_ratio: 1.7, pe: 22, pb: 5, market_cap: 210000000000, net_flow: 50000000, sector: "电力设备" },
  ],
};

const events = {
  meta: { source: "eastmoney_fast_news", observed_at: "2026-07-19T14:00:00Z", fetched_at: "2026-07-19T14:01:00Z", freshness: "fresh", coverage: 1, errors: [] },
  summary: ["央企改革出现政策支持信号，银行板块受到资金关注。"],
  next_actions: ["打开关联板块检查资金持续性", "补读公告/政策原文再判断"],
  clusters: [
    { key: "policy_support", label: "政策与监管", signal: "positive", count: 1, summary: "央企增持维护市场稳定", hot_score: 86 },
    { key: "capital_style", label: "资金与风格", signal: "neutral", count: 1, summary: "低波资金关注银行", hot_score: 72 },
  ],
  events: [
    { id: "e1", title: "两家央企宣布增持", summary: "中国国新、中国诚通继续增持央企和科技企业股票。", source: "东方财富快讯", url: "https://finance.eastmoney.com/a/e1.html", published_at: "2026-07-19T13:30:00Z", related_symbols: ["SH.600519"], related_sectors: ["央企改革"], category: "policy_support", sentiment: "positive", importance_score: 86, tags: ["央企改革", "增持"], impact: "稳定风险偏好，利好央企和核心资产。", action: "回到板块温度页检查央企改革。" },
    { id: "e2", title: "资金与风格", summary: "近期市场风格剧烈波动，低波稳健型资金关注银行板块。", source: "东方财富快讯", url: "https://finance.eastmoney.com/a/e2.html", published_at: "2026-07-19T13:20:00Z", related_symbols: ["SH.600351"], related_sectors: ["银行"], category: "capital_style", sentiment: "neutral", importance_score: 72, tags: ["资金与风格", "资金风格", "银行"], impact: "提示市场风格切换。", action: "对照涨跌家数和成交额。" },
  ],
};

const intelligence = {
  meta: { source: "eastmoney_sector_flow+eastmoney_dragon_tiger", observed_at: "2026-07-28T07:00:00Z", fetched_at: "2026-07-28T08:00:00Z", freshness: "fresh", coverage: 1, errors: [] },
  sector_flows: [
    { code: "BK1031", name: "电力设备", change_pct: 2.4, net_flow: 6466000000 },
    { code: "BK0475", name: "银行", change_pct: 0.8, net_flow: 1210000000 },
  ],
  anomalies: [{
    symbol: "SZ.002475", name: "立讯精密", trade_date: "2026-07-25", reason: "日涨幅偏离值达 7%", close: 42.5, change_pct: 9.99, net_buy: 120000000, buy_amount: 350000000, sell_amount: 230000000, turnover_rate: 8.5,
    source: { provider: "eastmoney_datacenter", label: "东方财富龙虎榜", capability: "dragon_tiger", source_url: "https://data.eastmoney.com/stock/lhb.html", observed_at: "2026-07-25T07:00:00Z", fetched_at: "2026-07-28T08:00:00Z", freshness: "delayed" },
  }],
  capabilities: {
    sector_flows: { status: "ready", provider: "eastmoney_sector_flow", error: null, fetched_at: "2026-07-28T08:00:00Z" },
    dragon_tiger: { status: "ready", provider: "eastmoney_datacenter", error: null, fetched_at: "2026-07-28T08:00:00Z" },
  },
};

const equityPage = {
  meta: market.snapshot.meta,
  total: 27,
  page: 1,
  page_size: 25,
  exchange: "all",
  sort_by: "amount",
  direction: "desc",
  available_sectors: ["白酒", "银行"],
  items: [
    { symbol: "SH.600519", code: "600519", name: "贵州茅台", price: 1500, change_pct: 1.2, amount: 2000000000, turnover_rate: 0.8, volume_ratio: 1.1, pe: 23, pb: 7, market_cap: 1900000000000, net_flow: 80000000, sector: "白酒" },
    { symbol: "SZ.000001", code: "000001", name: "平安银行", price: 12.5, change_pct: -0.5, amount: 1000000000, turnover_rate: 1.2, volume_ratio: null, pe: 6, pb: 0.7, market_cap: 240000000000, net_flow: null, sector: "银行" },
    { symbol: "SH.600000", code: "600000", name: "缺失样本", price: null, change_pct: null, amount: null, turnover_rate: null, volume_ratio: null, pe: null, pb: null, market_cap: null, net_flow: null, sector: null },
  ],
};

const requestBodies: unknown[] = [];

function LocationProbe() {
  const location = useLocation();
  return <output data-testid="location-search">{location.search}</output>;
}

function renderPage(initialPath = "/market") {
  const requests: string[] = [];
  let savedViews = [{
    id: 7,
    name: "白酒放量",
    filters: {
      query: "",
      exchange: "sh",
      sector: "白酒",
      min_change_pct: 1,
      max_change_pct: null,
      min_amount: 1_000_000_000,
      max_amount: null,
      min_turnover_rate: null,
      max_turnover_rate: null,
      min_market_cap: null,
      max_market_cap: null,
      complete_only: true,
      sort_by: "amount",
      direction: "desc",
      page_size: 25,
    },
    created_at: "2026-07-24T01:00:00Z",
    updated_at: "2026-07-24T01:00:00Z",
  }];
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    requests.push(url);
    if (init?.body) requestBodies.push(JSON.parse(String(init.body)));
    if (url.includes("/api/v1/equity-views")) {
      if (init?.method === "POST") {
        const payload = requestBodies.at(-1) as { name: string; filters: typeof savedViews[number]["filters"] };
        const created = { id: 8, ...payload, created_at: "2026-07-24T02:00:00Z", updated_at: "2026-07-24T02:00:00Z" };
        savedViews = [created, ...savedViews];
        return { ok: true, status: 201, json: async () => created };
      }
      if (init?.method === "DELETE") {
        const id = Number(url.split("/").at(-1));
        savedViews = savedViews.filter((view) => view.id !== id);
        return { ok: true, status: 204, json: async () => undefined };
      }
      return { ok: true, status: 200, json: async () => savedViews };
    }
    if (url.includes("/api/v1/sectors/BK1031")) return { ok: true, status: 200, json: async () => flowSector };
    if (url.includes("/api/v1/sectors/BK1")) return { ok: true, status: 200, json: async () => sector };
    if (url.includes("/api/v1/themes/BK0896")) return { ok: true, status: 200, json: async () => theme };
    if (url.includes("/api/v1/market-events")) return { ok: true, status: 200, json: async () => events };
    if (url.includes("/api/v1/markets/CN/intelligence")) return { ok: true, status: 200, json: async () => intelligence };
    if (url.includes("/api/v1/equities")) return { ok: true, status: 200, json: async () => equityPage };
    if (url.includes("/api/v1/market-structure/dashboard")) return { ok: true, status: 200, json: async () => dashboard };
    return { ok: true, status: 200, json: async () => market };
  }));
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[initialPath]}><MarketPage /><LocationProbe /></MemoryRouter></QueryClientProvider>);
  return requests;
}

async function openMarketBrowser() {
  fireEvent.click(await screen.findByRole("button", { name: "加载全市场行情" }));
  const browser = await screen.findByRole("region", { name: "全市场行情" });
  await within(browser).findByLabelText("搜索全市场");
  return browser;
}

afterEach(() => {
  cleanup();
  requestBodies.length = 0;
  vi.unstubAllGlobals();
});

it("opens a sector research panel with constituents and stock links", async () => {
  renderPage();

  fireEvent.click(await screen.findByRole("button", { name: /白酒/ }));

  expect(await screen.findByText("白酒板块简析")).toBeInTheDocument();
  const reviewDesk = within(await screen.findByLabelText("白酒板块简析"));
  expect(reviewDesk.getByText("板块")).toBeInTheDocument();
  expect(reviewDesk.getByText("可以小仓关注前排")).toBeInTheDocument();
  expect(reviewDesk.getByText("上涨扩散")).toBeInTheDocument();
  expect(reviewDesk.getByText("获得资金买入的股票")).toBeInTheDocument();
  expect(reviewDesk.getByText("领涨核心")).toBeInTheDocument();
  expect(reviewDesk.getByText("资金最关注")).toBeInTheDocument();
  expect(reviewDesk.getAllByRole("link", { name: /贵州茅台/ })[0]).toHaveAttribute("href", "/stocks?symbol=SH.600519");
  expect(screen.getByText("市场异动")).toBeInTheDocument();
  expect(screen.getByText("两家央企宣布增持")).toBeInTheDocument();
  expect(screen.getByText("政策与监管")).toBeInTheDocument();
  const eventRadar = within(screen.getByRole("region", { name: "市场异动" }));
  expect(eventRadar.getByText("近期市场风格剧烈价格起伏，低波稳健型资金关注银行板块")).toBeInTheDocument();
  expect(eventRadar.queryByText("可能影响")).not.toBeInTheDocument();
  expect(eventRadar.queryByText("下一步")).not.toBeInTheDocument();
  expect(eventRadar.queryByRole("link", { name: "SH.600351" })).not.toBeInTheDocument();
  expect(eventRadar.queryByText("资金风格")).not.toBeInTheDocument();
  expect(screen.queryByText("事件-板块核验矩阵")).not.toBeInTheDocument();
  expect(screen.queryByText("价格是否确认")).not.toBeInTheDocument();
  expect(screen.queryByText("资金是否确认")).not.toBeInTheDocument();
  expect(screen.getAllByText("大额买入资金比卖出资金多 1.00 亿，板块热度偏强。").length).toBeGreaterThan(0);
  const detail = screen.getByText("白酒板块简析").closest("section");
  expect(detail).not.toBeNull();
  const constituents = (detail as HTMLElement).querySelector(".sector-constituents");
  expect(constituents).not.toBeNull();
  const handoff = within(await screen.findByLabelText("白酒板块优先个股线索"));
  expect(handoff.getByText("个股")).toBeInTheDocument();
  expect(handoff.getByText("优先个股")).toBeInTheDocument();
  expect(handoff.getByText(/股价上涨且买入资金更多/)).toBeInTheDocument();
  expect(handoff.getByText("可小仓试探")).toBeInTheDocument();
  expect(handoff.queryByText(/先看入场/)).toBeNull();
  expect(handoff.getByRole("link", { name: /贵州茅台/ })).toHaveAttribute("href", "/stocks?symbol=SH.600519&from=market&board=BK1&boardName=%E7%99%BD%E9%85%92&boardType=%E6%9D%BF%E5%9D%97#stock-investment-advice");
  const row = within(constituents as HTMLElement).getByRole("link", { name: /贵州茅台/ });
  expect(row).toHaveAttribute("href", "/stocks?symbol=SH.600519&from=market&board=BK1&boardName=%E7%99%BD%E9%85%92&boardType=%E6%9D%BF%E5%9D%97#stock-investment-advice");
  expect(within(row).getByText("SH.600519")).toBeInTheDocument();
  expect(within(row).getByText(/股价上涨且买入资金更多/)).toBeInTheDocument();
  expect(within(row).getByText("可小仓试探")).toBeInTheDocument();
});

it("shows one-snapshot market structure evidence and research shortcuts", async () => {
  renderPage();

  const board = await screen.findByRole("region", { name: "市场量化看板" });
  expect(within(board).getByText("所有指标使用同一交易快照")).toBeInTheDocument();
  const metrics = within(board).getByRole("region", { name: "核心市场指标" });
  expect(within(metrics).getByText("来自 5100 只有效样本")).toBeInTheDocument();
  expect(within(board).getByText("61%")).toBeInTheDocument();
  expect(within(board).getByText("42")).toBeInTheDocument();
  expect(within(board).getByRole("article", { name: "1% ~ 5%：2000 只" })).toBeInTheDocument();
  const leads = within(board).getByRole("complementary", { name: "市场结构线索" });
  const sectors = within(leads).getByRole("region", { name: "板块强弱排行" });
  const activity = within(leads).getByRole("region", { name: "成交活跃个股" });
  expect(within(sectors).getByRole("link", { name: /白酒/ })).toHaveAttribute("href", "/market?sector=BK1");
  expect(within(activity).getByRole("link", { name: /贵州茅台/ })).toHaveAttribute("href", "/stocks?symbol=SH.600519&from=market-dashboard");
  expect(within(board).getByRole("link", { name: "连板梯队" })).toHaveAttribute("href", "/limit-ladder");
  expect(within(board).getByRole("link", { name: "概念分析" })).toHaveAttribute("href", "/concepts");
  expect(within(board).getByRole("link", { name: "行业分析" })).toHaveAttribute("href", "/industries");
});

it("opens a theme research panel from Stock Lab theme links", async () => {
  const requests = renderPage("/market?theme=BK0896&themeName=酿酒概念&themeChange=1.8");

  expect(await screen.findByText("酿酒概念题材简析")).toBeInTheDocument();
  const reviewDesk = within(await screen.findByLabelText("酿酒概念题材简析"));
  expect(reviewDesk.getByText("暂不买入")).toBeInTheDocument();
  expect(reviewDesk.getByText(/资金情况待补/)).toBeInTheDocument();
  expect(reviewDesk.getByText("待补资料：板块资金流")).toBeInTheDocument();
  await waitFor(() => expect(requests.some((url) => url.includes("/api/v1/themes/BK0896"))).toBe(true));
  expect(requests.some((url) => url.includes("name=%E9%85%BF%E9%85%92%E6%A6%82%E5%BF%B5"))).toBe(true);
  const detail = screen.getByText("酿酒概念题材简析").closest("section");
  expect(detail).not.toBeNull();
  expect(within(detail as HTMLElement).getByText("题材涨跌")).toBeInTheDocument();
  const constituents = (detail as HTMLElement).querySelector(".sector-constituents");
  expect(constituents).not.toBeNull();
  const handoff = within(await screen.findByLabelText("酿酒概念题材优先个股线索"));
  expect(handoff.getByText(/股价在涨，但资金情况还不清楚/)).toBeInTheDocument();
  expect(handoff.getByText("暂不买入")).toBeInTheDocument();
  expect(within(constituents as HTMLElement).getByRole("link", { name: /贵州茅台/ })).toHaveAttribute("href", "/stocks?symbol=SH.600519&from=market&board=BK0896&boardName=%E9%85%BF%E9%85%92%E6%A6%82%E5%BF%B5&boardType=%E9%A2%98%E6%9D%90#stock-evidence-audit");
  expect(within(detail as HTMLElement).getAllByText("还缺：板块资金流").length).toBeGreaterThan(0);
});

it("scrolls directly to the selected theme dossier when landing from deep links", async () => {
  const scrollIntoView = vi.fn();
  const original = Element.prototype.scrollIntoView;
  Element.prototype.scrollIntoView = scrollIntoView;

  try {
    renderPage("/market?theme=BK0896&themeName=酿酒概念&themeChange=1.8");

    await screen.findByText("酿酒概念题材简析");
    await waitFor(() => expect(scrollIntoView).toHaveBeenCalledWith({ behavior: "smooth", block: "start" }));
  } finally {
    Element.prototype.scrollIntoView = original;
  }
});

it("renders sourced sector flows and dragon-tiger observations as market intelligence", async () => {
  renderPage();

  expect(screen.queryByRole("navigation", { name: "大盘页阅读顺序" })).not.toBeInTheDocument();
  expect(screen.queryByLabelText("市场概览")).not.toBeInTheDocument();

  expect(screen.queryByLabelText("市场广度")).not.toBeInTheDocument();
  const pulse = within(await screen.findByLabelText("大盘速览"));
  expect(pulse.getByText("广度")).toBeInTheDocument();
  expect(pulse.getByText("61%")).toBeInTheDocument();
  expect(pulse.getByText("温度")).toBeInTheDocument();
  expect(pulse.getByText("上证指数")).toBeInTheDocument();
  expect(pulse.queryByText("评分证据")).not.toBeInTheDocument();
  expect(screen.getByLabelText("板块与资金主线")).toBeInTheDocument();

  const panel = within(await screen.findByLabelText("A股市场情报"));
  expect(panel.getByText("板块资金确认")).toBeInTheDocument();
  expect(panel.getByText("电力设备")).toBeInTheDocument();
  expect(panel.getByText("+64.66 亿")).toBeInTheDocument();
  expect(panel.getByText("龙虎榜观察")).toBeInTheDocument();
  expect(panel.getByRole("link", { name: /立讯精密/ })).toHaveAttribute("href", "/stocks?symbol=SZ.002475");
  expect(panel.getByText(/日涨幅偏离值达 7%/)).toBeInTheDocument();

  const boardZone = screen.getByRole("region", { name: "板块和题材工作区" });
  const eventRadar = screen.getByRole("region", { name: "市场异动" });
  const browser = screen.getByText("全市场行情").closest("section");
  expect(boardZone.compareDocumentPosition(eventRadar) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(eventRadar.compareDocumentPosition(browser as HTMLElement) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
});

it("opens sector details from market intelligence flow leaders", async () => {
  const requests = renderPage();

  const panel = within(await screen.findByLabelText("A股市场情报"));
  fireEvent.click(panel.getByRole("button", { name: /电力设备/ }));

  expect(await screen.findByText("电力设备板块简析")).toBeInTheDocument();
  await waitFor(() => expect(requests.some((url) => url.includes("/api/v1/sectors/BK1031"))).toBe(true));
  const detail = screen.getByText("电力设备板块简析").closest("section");
  expect(detail).not.toBeNull();
  expect(within(detail as HTMLElement).getAllByText("大额买入资金比卖出资金多 64.66 亿，板块热度偏强。").length).toBeGreaterThan(0);
  const constituents = (detail as HTMLElement).querySelector(".sector-constituents");
  expect(constituents).not.toBeNull();
  const handoff = within(await screen.findByLabelText("电力设备板块优先个股线索"));
  expect(handoff.getByText("优先个股")).toBeInTheDocument();
  expect(handoff.getAllByText("可小仓试探").length).toBeGreaterThan(0);
  expect(within(constituents as HTMLElement).getByRole("link", { name: /立讯精密/ })).toHaveAttribute("href", "/stocks?symbol=SZ.002475&from=market&board=BK1031&boardName=%E7%94%B5%E5%8A%9B%E8%AE%BE%E5%A4%87&boardType=%E6%9D%BF%E5%9D%97#stock-investment-advice");
});

it("sorts and filters dossier constituents like a compact screener", async () => {
  renderPage();

  const panel = within(await screen.findByLabelText("A股市场情报"));
  fireEvent.click(panel.getByRole("button", { name: /电力设备/ }));

  const detail = (await screen.findByText("电力设备板块简析")).closest("section");
  expect(detail).not.toBeNull();
  const scoped = within(detail as HTMLElement);
  const constituents = (detail as HTMLElement).querySelector(".sector-constituents");
  expect(constituents).not.toBeNull();
  const constituentScope = within(constituents as HTMLElement);
  expect(scoped.getByText("显示 3 / 3")).toBeInTheDocument();
  expect(constituentScope.getAllByRole("link").map((row) => row.textContent)).toEqual([
    expect.stringContaining("立讯精密"),
    expect.stringContaining("阳光电源"),
    expect.stringContaining("宁德时代"),
  ]);

  fireEvent.change(scoped.getByLabelText("详情排序"), { target: { value: "change_pct" } });
  expect(constituentScope.getAllByRole("link")[0]).toHaveTextContent("阳光电源");

  fireEvent.change(scoped.getByLabelText("详情排序"), { target: { value: "amount" } });
  expect(constituentScope.getAllByRole("link")[0]).toHaveTextContent("宁德时代");

  fireEvent.change(scoped.getByLabelText("详情范围"), { target: { value: "net_inflow" } });
  expect(constituentScope.queryByRole("link", { name: /宁德时代/ })).not.toBeInTheDocument();
  expect(scoped.getByText("显示 2 / 3")).toBeInTheDocument();

  fireEvent.change(scoped.getByLabelText("详情范围"), { target: { value: "up" } });
  expect(constituentScope.queryByRole("link", { name: /宁德时代/ })).not.toBeInTheDocument();
  expect(constituentScope.getAllByRole("link")).toHaveLength(2);
});

it("browses, ranks, and searches the full market without loading every quote", async () => {
  const requests = renderPage();

  const browser = await openMarketBrowser();
  expect(await within(browser).findByRole("link", { name: /贵州茅台/ })).toHaveAttribute(
    "href",
    "/stocks?symbol=SH.600519",
  );
  const missingRow = within(browser).getByRole("link", { name: /缺失样本/ }).closest("tr");
  expect(missingRow?.children[2]).not.toHaveClass("up");
  expect(missingRow?.children[2]).not.toHaveClass("down");

  expect(within(browser).queryByLabelText("交易所")).not.toBeInTheDocument();
  expect(within(browser).queryByLabelText("排序字段")).not.toBeInTheDocument();
  expect(within(browser).queryByLabelText("排序方向")).not.toBeInTheDocument();
  expect(within(browser).queryByLabelText("每页数量")).not.toBeInTheDocument();
  expect(within(browser).getByText("高级筛选")).toBeInTheDocument();
  expect(within(browser).getByLabelText("行业")).toBeInTheDocument();
  expect(within(browser).getByLabelText("成交额不低于（亿元）")).toBeInTheDocument();

  fireEvent.change(screen.getByLabelText("搜索全市场"), { target: { value: "茅台" } });
  fireEvent.click(screen.getByRole("button", { name: "搜索" }));
  await waitFor(() => expect(requests.some((url) => url.includes("q=%E8%8C%85%E5%8F%B0"))).toBe(true));
  await waitFor(() => expect(screen.getByRole("button", { name: "下一页" })).toBeEnabled());

  fireEvent.click(screen.getByRole("button", { name: "下一页" }));
  await waitFor(() => expect(requests.some((url) => url.includes("page=2"))).toBe(true));
});

it("jumps across the full result set without secondary toolbar filters", async () => {
  const requests = renderPage();

  const browser = await openMarketBrowser();
  expect(within(browser).queryByLabelText("交易所")).not.toBeInTheDocument();
  expect(within(browser).queryByLabelText("排序字段")).not.toBeInTheDocument();
  expect(within(browser).queryByLabelText("排序方向")).not.toBeInTheDocument();
  expect(within(browser).queryByLabelText("每页数量")).not.toBeInTheDocument();
  await waitFor(() => expect(screen.getByRole("button", { name: "跳转" })).toBeEnabled());

  fireEvent.change(screen.getByLabelText("跳转页码"), { target: { value: "999" } });
  fireEvent.click(screen.getByRole("button", { name: "跳转" }));
  await waitFor(() => expect(requests.some((url) => url.includes("exchange=all") && url.includes("page=2"))).toBe(true));
  await waitFor(() => expect(screen.getByRole("button", { name: "首页" })).toBeEnabled());

  fireEvent.click(screen.getByRole("button", { name: "首页" }));
  await waitFor(() => expect(screen.getByLabelText("跳转页码")).toHaveValue(1));
  await waitFor(() => expect(screen.getByRole("button", { name: "末页" })).toBeEnabled());

  const lastPageRequests = requests.filter((url) => url.includes("page=2")).length;
  fireEvent.click(screen.getByRole("button", { name: "末页" }));
  await waitFor(() => expect(requests.filter((url) => url.includes("page=2")).length).toBeGreaterThan(lastPageRequests));
});

it("restores advanced filters from the URL and sends normalized server units", async () => {
  const requests = renderPage(
    "/market?industry=%E7%99%BD%E9%85%92&min_change_pct=1&min_amount=15&complete_only=true",
  );

  expect(await screen.findByLabelText("行业")).toHaveValue("白酒");
  expect(screen.getByLabelText("涨跌幅不低于（%）")).toHaveValue(1);
  expect(screen.getByLabelText("成交额不低于（亿元）")).toHaveValue(15);
  expect(screen.getByLabelText("核心数据完整")).toBeChecked();
  expect(screen.queryByLabelText("总市值下限（亿元）")).not.toBeInTheDocument();
  await waitFor(() => expect(requests.some((url) => url.includes("min_amount=1500000000"))).toBe(true));

  fireEvent.change(screen.getByLabelText("换手率不低于（%）"), { target: { value: "3.5" } });
  fireEvent.click(screen.getByRole("button", { name: "应用筛选" }));

  await waitFor(() => expect(requests.some((url) => url.includes("min_turnover_rate=3.5") && !url.includes("min_market_cap"))).toBe(true));
  expect(screen.getByTestId("location-search")).toHaveTextContent("min_turnover_rate=3.5");

  fireEvent.click(screen.getByRole("button", { name: "重置全部" }));
  await waitFor(() => expect(screen.getByTestId("location-search")).toHaveTextContent(/^$/));
});

it("applies, creates, and deletes reusable saved views", async () => {
  const requests = renderPage();

  await openMarketBrowser();
  fireEvent.click(await screen.findByRole("button", { name: "应用视图 白酒放量" }));
  await waitFor(() => expect(requests.some((url) => url.includes("sector=%E7%99%BD%E9%85%92") && url.includes("page=1"))).toBe(true));
  expect(screen.queryByLabelText("交易所")).not.toBeInTheDocument();
  expect(await screen.findByLabelText("行业")).toHaveValue("白酒");
  expect(screen.getByLabelText("核心数据完整")).toBeChecked();

  fireEvent.change(screen.getByLabelText("视图名称"), { target: { value: "我的白酒池" } });
  fireEvent.click(screen.getByRole("button", { name: "保存当前视图" }));
  await waitFor(() => expect(requestBodies.some((body) => (body as { name?: string }).name === "我的白酒池")).toBe(true));
  expect(await screen.findByRole("button", { name: "应用视图 我的白酒池" })).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "删除视图 我的白酒池" }));
  await waitFor(() => expect(screen.queryByRole("button", { name: "应用视图 我的白酒池" })).not.toBeInTheDocument());
});
