import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
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

const equityPage = {
  meta: market.snapshot.meta,
  total: 27,
  page: 1,
  page_size: 25,
  exchange: "all",
  sort_by: "amount",
  direction: "desc",
  items: [
    { symbol: "SH.600519", code: "600519", name: "贵州茅台", price: 1500, change_pct: 1.2, amount: 2000000000, turnover_rate: 0.8, volume_ratio: 1.1, pe: 23, pb: 7, market_cap: 1900000000000, net_flow: 80000000, sector: "白酒" },
    { symbol: "SZ.000001", code: "000001", name: "平安银行", price: 12.5, change_pct: -0.5, amount: 1000000000, turnover_rate: 1.2, volume_ratio: null, pe: 6, pb: 0.7, market_cap: 240000000000, net_flow: null, sector: "银行" },
    { symbol: "SH.600000", code: "600000", name: "缺失样本", price: null, change_pct: null, amount: null, turnover_rate: null, volume_ratio: null, pe: null, pb: null, market_cap: null, net_flow: null, sector: null },
  ],
};

function renderPage(initialPath = "/market") {
  const requests: string[] = [];
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    requests.push(url);
    if (url.includes("/api/v1/sectors/BK1")) return { ok: true, status: 200, json: async () => sector };
    if (url.includes("/api/v1/market-events")) return { ok: true, status: 200, json: async () => events };
    if (url.includes("/api/v1/equities")) return { ok: true, status: 200, json: async () => equityPage };
    return { ok: true, status: 200, json: async () => market };
  }));
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[initialPath]}><MarketPage /></MemoryRouter></QueryClientProvider>);
  return requests;
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("opens a sector research panel with constituents and stock links", async () => {
  renderPage();

  fireEvent.click(await screen.findByRole("button", { name: /白酒/ }));

  expect(await screen.findByText("白酒板块简析")).toBeInTheDocument();
  expect(screen.getByText("市场异动雷达")).toBeInTheDocument();
  expect(screen.getByText("两家央企宣布增持")).toBeInTheDocument();
  expect(screen.getByText("政策与监管")).toBeInTheDocument();
  expect(screen.getByText("事件-板块核验矩阵")).toBeInTheDocument();
  expect(screen.getByText("价格是否确认")).toBeInTheDocument();
  expect(screen.getByText("资金是否确认")).toBeInTheDocument();
  expect(screen.getByText("主力净流入 1.00 亿，板块热度偏强。")).toBeInTheDocument();
  const detail = screen.getByText("白酒板块简析").closest("section");
  expect(detail).not.toBeNull();
  const row = within(detail as HTMLElement).getByRole("link", { name: /贵州茅台/ });
  expect(row).toHaveAttribute("href", "/stocks?symbol=SH.600519");
  expect(within(row).getByText("SH.600519")).toBeInTheDocument();
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
