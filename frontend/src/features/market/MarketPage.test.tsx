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
    return { ok: true, status: 200, json: async () => market };
  }));
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[initialPath]}><MarketPage /><LocationProbe /></MemoryRouter></QueryClientProvider>);
  return requests;
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
  const reviewDesk = within(await screen.findByLabelText("白酒板块复核工作台"));
  expect(reviewDesk.getByText("BOARD GATE")).toBeInTheDocument();
  expect(reviewDesk.getByText("主线可继续复核")).toBeInTheDocument();
  expect(reviewDesk.getByText("上涨扩散")).toBeInTheDocument();
  expect(reviewDesk.getByText("净流入扩散")).toBeInTheDocument();
  expect(reviewDesk.getByText("领涨核心")).toBeInTheDocument();
  expect(reviewDesk.getByText("资金核心")).toBeInTheDocument();
  expect(reviewDesk.getAllByRole("link", { name: /贵州茅台/ })[0]).toHaveAttribute("href", "/stocks?symbol=SH.600519");
  expect(screen.getByText("市场异动雷达")).toBeInTheDocument();
  expect(screen.getByText("两家央企宣布增持")).toBeInTheDocument();
  expect(screen.getByText("政策与监管")).toBeInTheDocument();
  expect(screen.getByText("事件-板块核验矩阵")).toBeInTheDocument();
  expect(screen.getByText("价格是否确认")).toBeInTheDocument();
  expect(screen.getByText("资金是否确认")).toBeInTheDocument();
  expect(screen.getAllByText("主力净流入 1.00 亿，板块热度偏强。").length).toBeGreaterThan(0);
  const detail = screen.getByText("白酒板块简析").closest("section");
  expect(detail).not.toBeNull();
  const constituents = (detail as HTMLElement).querySelector(".sector-constituents");
  expect(constituents).not.toBeNull();
  const handoff = within(await screen.findByLabelText("白酒板块优先个股线索"));
  expect(handoff.getByText("STOCK HANDOFF")).toBeInTheDocument();
  expect(handoff.getByText("优先点开这几只")).toBeInTheDocument();
  expect(handoff.getByText(/价格与资金同向/)).toBeInTheDocument();
  expect(handoff.getByText("先看交易计划")).toBeInTheDocument();
  expect(handoff.getByText(/先复核入场/)).toBeInTheDocument();
  expect(handoff.getByRole("link", { name: /贵州茅台/ })).toHaveAttribute("href", "/stocks?symbol=SH.600519&from=market&board=BK1&boardName=%E7%99%BD%E9%85%92&boardType=%E6%9D%BF%E5%9D%97#stock-investment-advice");
  const row = within(constituents as HTMLElement).getByRole("link", { name: /贵州茅台/ });
  expect(row).toHaveAttribute("href", "/stocks?symbol=SH.600519&from=market&board=BK1&boardName=%E7%99%BD%E9%85%92&boardType=%E6%9D%BF%E5%9D%97#stock-investment-advice");
  expect(within(row).getByText("SH.600519")).toBeInTheDocument();
  expect(within(row).getByText(/价格与资金同向/)).toBeInTheDocument();
  expect(within(row).getByText("先看交易计划")).toBeInTheDocument();
});

it("opens a theme research panel from Stock Lab theme links", async () => {
  const requests = renderPage("/market?theme=BK0896&themeName=酿酒概念&themeChange=1.8");

  expect(await screen.findByText("酿酒概念题材简析")).toBeInTheDocument();
  const reviewDesk = within(await screen.findByLabelText("酿酒概念题材复核工作台"));
  expect(reviewDesk.getByText("只看前排，等待确认")).toBeInTheDocument();
  expect(reviewDesk.getByText(/资金证据待增强/)).toBeInTheDocument();
  expect(reviewDesk.getByText("缺口：板块资金流")).toBeInTheDocument();
  await waitFor(() => expect(requests.some((url) => url.includes("/api/v1/themes/BK0896"))).toBe(true));
  expect(requests.some((url) => url.includes("name=%E9%85%BF%E9%85%92%E6%A6%82%E5%BF%B5"))).toBe(true);
  const detail = screen.getByText("酿酒概念题材简析").closest("section");
  expect(detail).not.toBeNull();
  expect(within(detail as HTMLElement).getByText("题材涨跌")).toBeInTheDocument();
  const constituents = (detail as HTMLElement).querySelector(".sector-constituents");
  expect(constituents).not.toBeNull();
  const handoff = within(await screen.findByLabelText("酿酒概念题材优先个股线索"));
  expect(handoff.getByText(/价格走强但资金缺口待补/)).toBeInTheDocument();
  expect(handoff.getByText("先看证据总账")).toBeInTheDocument();
  expect(within(constituents as HTMLElement).getByRole("link", { name: /贵州茅台/ })).toHaveAttribute("href", "/stocks?symbol=SH.600519&from=market&board=BK0896&boardName=%E9%85%BF%E9%85%92%E6%A6%82%E5%BF%B5&boardType=%E9%A2%98%E6%9D%90#stock-evidence-audit");
  expect(within(detail as HTMLElement).getAllByText("缺口：板块资金流").length).toBeGreaterThan(0);
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

  const command = within(await screen.findByLabelText("市场作战台"));
  expect(command.getByText("MARKET PULSE · 大盘执行台")).toBeInTheDocument();
  expect(command.getByText("MARKET GATE")).toBeInTheDocument();
  expect(command.getByText("均衡 · 58/100")).toBeInTheDocument();
  expect(command.getAllByText("允许复核机会").length).toBeGreaterThan(0);
  expect(command.getByText("盘面三问")).toBeInTheDocument();
  expect(command.getByText("宽度够不够：够")).toBeInTheDocument();
  expect(command.getByText("主线清不清：电力设备")).toBeInTheDocument();
  expect(command.getByText("风险挡不挡：不挡")).toBeInTheDocument();
  expect(command.getByText("今日路线")).toBeInTheDocument();
  expect(command.getByText(/广度占优/)).toBeInTheDocument();
  expect(command.getByText("资金主线")).toBeInTheDocument();
  expect(command.getByRole("button", { name: "电力设备" })).toBeInTheDocument();
  expect(command.getByText("事件风险")).toBeInTheDocument();
  expect(command.getByText(/央企改革出现政策支持信号/)).toBeInTheDocument();
  expect(command.getByText("下一步 · 执行指令")).toBeInTheDocument();
  expect(command.getByText("ORDER TAPE")).toBeInTheDocument();
  expect(command.getByRole("link", { name: "进入机会漏斗" })).toHaveAttribute("href", "/opportunities");

  const panel = within(await screen.findByLabelText("A股市场情报"));
  expect(panel.getByText("板块资金确认")).toBeInTheDocument();
  expect(panel.getByText("电力设备")).toBeInTheDocument();
  expect(panel.getByText("+64.66 亿")).toBeInTheDocument();
  expect(panel.getByText("龙虎榜观察")).toBeInTheDocument();
  expect(panel.getByRole("link", { name: /立讯精密/ })).toHaveAttribute("href", "/stocks?symbol=SZ.002475");
  expect(panel.getByText(/日涨幅偏离值达 7%/)).toBeInTheDocument();
  expect(panel.getByText(/供应商算法与交易异动仅作展示/)).toBeInTheDocument();
});

it("opens sector details from market intelligence flow leaders", async () => {
  const requests = renderPage();

  const panel = within(await screen.findByLabelText("A股市场情报"));
  fireEvent.click(panel.getByRole("button", { name: /电力设备/ }));

  expect(await screen.findByText("电力设备板块简析")).toBeInTheDocument();
  await waitFor(() => expect(requests.some((url) => url.includes("/api/v1/sectors/BK1031"))).toBe(true));
  const detail = screen.getByText("电力设备板块简析").closest("section");
  expect(detail).not.toBeNull();
  expect(within(detail as HTMLElement).getAllByText("主力净流入 64.66 亿，板块热度偏强。").length).toBeGreaterThan(0);
  const constituents = (detail as HTMLElement).querySelector(".sector-constituents");
  expect(constituents).not.toBeNull();
  const handoff = within(await screen.findByLabelText("电力设备板块优先个股线索"));
  expect(handoff.getByText(/优先点开这几只/)).toBeInTheDocument();
  expect(handoff.getAllByText("先看交易计划").length).toBeGreaterThan(0);
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

  const title = await screen.findByText("全市场行情");
  const browser = title.closest("section");
  expect(browser).not.toBeNull();
  expect(await within(browser as HTMLElement).findByRole("link", { name: /贵州茅台/ })).toHaveAttribute(
    "href",
    "/stocks?symbol=SH.600519",
  );
  const missingRow = within(browser as HTMLElement).getByRole("link", { name: /缺失样本/ }).closest("tr");
  expect(missingRow?.children[2]).not.toHaveClass("up");
  expect(missingRow?.children[2]).not.toHaveClass("down");

  fireEvent.change(screen.getByLabelText("排序字段"), { target: { value: "change_pct" } });
  await waitFor(() => expect(requests.some((url) => url.includes("sort_by=change_pct"))).toBe(true));

  fireEvent.change(screen.getByLabelText("搜索全市场"), { target: { value: "茅台" } });
  fireEvent.click(screen.getByRole("button", { name: "搜索" }));
  await waitFor(() => expect(requests.some((url) => url.includes("q=%E8%8C%85%E5%8F%B0"))).toBe(true));

  fireEvent.click(screen.getByRole("button", { name: "下一页" }));
  await waitFor(() => expect(requests.some((url) => url.includes("page=2"))).toBe(true));
});

it("filters exchanges and jumps across the full result set", async () => {
  const requests = renderPage();

  await screen.findByText("全市场行情");
  fireEvent.change(screen.getByLabelText("交易所"), { target: { value: "bj" } });
  await waitFor(() => expect(requests.some((url) => url.includes("exchange=bj") && url.includes("page=1"))).toBe(true));
  await waitFor(() => expect(screen.getByRole("button", { name: "跳转" })).toBeEnabled());

  fireEvent.change(screen.getByLabelText("跳转页码"), { target: { value: "999" } });
  fireEvent.click(screen.getByRole("button", { name: "跳转" }));
  await waitFor(() => expect(requests.some((url) => url.includes("exchange=bj") && url.includes("page=2"))).toBe(true));
  await waitFor(() => expect(screen.getByRole("button", { name: "首页" })).toBeEnabled());

  fireEvent.click(screen.getByRole("button", { name: "首页" }));
  await waitFor(() => expect(screen.getByLabelText("跳转页码")).toHaveValue(1));
  await waitFor(() => expect(screen.getByRole("button", { name: "末页" })).toBeEnabled());

  const lastPageRequests = requests.filter((url) => url.includes("page=2")).length;
  fireEvent.click(screen.getByRole("button", { name: "末页" }));
  await waitFor(() => expect(requests.filter((url) => url.includes("page=2")).length).toBeGreaterThan(lastPageRequests));

  fireEvent.change(screen.getByLabelText("每页数量"), { target: { value: "50" } });
  await waitFor(() => expect(requests.some((url) => url.includes("page_size=50") && url.includes("page=1"))).toBe(true));
});

it("restores advanced filters from the URL and sends normalized server units", async () => {
  const requests = renderPage(
    "/market?industry=%E7%99%BD%E9%85%92&min_change_pct=1&min_amount=15&complete_only=true",
  );

  expect(await screen.findByLabelText("行业")).toHaveValue("白酒");
  expect(screen.getByLabelText("涨跌幅下限（%）")).toHaveValue(1);
  expect(screen.getByLabelText("成交额下限（亿元）")).toHaveValue(15);
  expect(screen.getByLabelText("仅看核心数据完整")).toBeChecked();
  await waitFor(() => expect(requests.some((url) => url.includes("min_amount=1500000000"))).toBe(true));

  fireEvent.change(screen.getByLabelText("换手率上限（%）"), { target: { value: "3.5" } });
  fireEvent.change(screen.getByLabelText("总市值下限（亿元）"), { target: { value: "100" } });
  fireEvent.click(screen.getByRole("button", { name: "应用筛选" }));

  await waitFor(() => expect(requests.some((url) => url.includes("max_turnover_rate=3.5") && url.includes("min_market_cap=10000000000"))).toBe(true));
  expect(screen.getByTestId("location-search")).toHaveTextContent("max_turnover_rate=3.5");

  fireEvent.click(screen.getByRole("button", { name: "重置全部" }));
  await waitFor(() => expect(screen.getByTestId("location-search")).toHaveTextContent(/^$/));
});

it("applies, creates, and deletes reusable saved views", async () => {
  const requests = renderPage();

  fireEvent.click(await screen.findByRole("button", { name: "应用视图 白酒放量" }));
  await waitFor(() => expect(requests.some((url) => url.includes("sector=%E7%99%BD%E9%85%92") && url.includes("page=1"))).toBe(true));
  expect(screen.getByLabelText("交易所")).toHaveValue("sh");

  fireEvent.change(screen.getByLabelText("视图名称"), { target: { value: "我的白酒池" } });
  fireEvent.click(screen.getByRole("button", { name: "保存当前视图" }));
  await waitFor(() => expect(requestBodies.some((body) => (body as { name?: string }).name === "我的白酒池")).toBe(true));
  expect(await screen.findByRole("button", { name: "应用视图 我的白酒池" })).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "删除视图 我的白酒池" }));
  await waitFor(() => expect(screen.queryByRole("button", { name: "应用视图 我的白酒池" })).not.toBeInTheDocument());
});
