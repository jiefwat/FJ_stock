import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";

import { LimitLadderPage } from "./LimitLadderPage";
import { MarketGroupPage } from "./MarketGroupPage";

const meta = {
  source: "fixture",
  observed_at: "2026-08-21T07:00:00Z",
  fetched_at: "2026-08-21T07:01:00Z",
  freshness: "fresh",
  coverage: 0.9,
  errors: [],
};

const quote = {
  symbol: "SH.600519",
  code: "600519",
  name: "贵州茅台",
  price: 1500,
  change_pct: 10,
  amount: 2_000_000_000,
  turnover_rate: 0.8,
  volume_ratio: 1.1,
  pe: 23,
  pb: 7,
  market_cap: 1_900_000_000_000,
  net_flow: 80_000_000,
  sector: "白酒",
  asset_type: "stock",
  exchange: "SH",
  price_limit_pct: 10,
};

function renderWithClient(node: ReactNode, path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[path]}>{node}</MemoryRouter></QueryClientProvider>);
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("filters concept groups, selects a group, and hands the leader to Stock Lab", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => ({
    ok: true,
    status: 200,
    json: async () => ({
      meta,
      kind: "concept",
      available: true,
      degraded: false,
      unavailable_reason: null,
      summary: "当前覆盖 2 个概念。",
      methodology: ["当前只比较最新横截面。"],
      groups: [
        {
          code: "BK100",
          name: "酿酒概念",
          kind: "concept",
          change_pct: 2.1,
          net_flow: 100_000_000,
          constituent_count: 1,
          advancing: 1,
          declining: 0,
          average_change_pct: 2.1,
          average_turnover_rate: 0.8,
          total_amount: 2_000_000_000,
          heat_score: 82,
          risk_score: 18,
          evidence_coverage: 1,
          leader: { quote, score: 88 },
          constituents: [quote],
          missing_evidence: [],
        },
        {
          code: "BK200",
          name: "机器人概念",
          kind: "concept",
          change_pct: -1.1,
          net_flow: null,
          constituent_count: 0,
          advancing: 0,
          declining: 0,
          average_change_pct: null,
          average_turnover_rate: null,
          total_amount: null,
          heat_score: 35,
          risk_score: 65,
          evidence_coverage: 0.33,
          leader: null,
          constituents: [],
          missing_evidence: ["板块资金流", "成分股"],
        },
      ],
    }),
  })));

  renderWithClient(<MarketGroupPage kind="concept" />, "/concepts");

  expect(await screen.findByRole("heading", { name: "概念分析" })).toBeInTheDocument();
  const focus = await screen.findByRole("region", { name: "酿酒概念概念焦点" });
  expect(within(focus).getByText("置信度 100% · 信息覆盖，不是上涨概率")).toBeInTheDocument();
  expect(within(focus).getAllByRole("link", { name: /贵州茅台/ })[0]).toHaveAttribute("href", expect.stringContaining("/stocks?symbol=SH.600519"));

  fireEvent.change(screen.getByLabelText("搜索概念"), { target: { value: "机器人" } });
  expect(screen.getByRole("button", { name: /机器人概念/ })).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /酿酒概念/ })).not.toBeInTheDocument();
});

it("loads the selected group detail on demand when the catalog has no constituents", async () => {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes("/groups/concept/BK025")) {
      return {
        ok: true,
        status: 200,
        json: async () => ({
          meta,
          kind: "concept",
          available: true,
          degraded: false,
          unavailable_reason: null,
          summary: "已补齐测试概念详情。",
          methodology: [],
          groups: [{
            code: "BK025",
            name: "测试概念",
            kind: "concept",
            change_pct: 1.2,
            net_flow: 120_000_000,
            constituent_count: 1,
            advancing: 1,
            declining: 0,
            average_change_pct: 10,
            average_turnover_rate: 0.8,
            total_amount: 2_000_000_000,
            heat_score: 80,
            risk_score: 20,
            evidence_coverage: 1,
            leader: { quote, score: 88 },
            constituents: [quote],
            missing_evidence: [],
          }],
        }),
      };
    }
    return {
      ok: true,
      status: 200,
      json: async () => ({
        meta,
        kind: "concept",
        available: true,
        degraded: false,
        unavailable_reason: null,
        summary: "当前覆盖 1 个概念。",
        methodology: [],
        groups: [{
          code: "BK025",
          name: "测试概念",
          kind: "concept",
          change_pct: 1.2,
          net_flow: 120_000_000,
          constituent_count: 0,
          advancing: 0,
          declining: 0,
          average_change_pct: null,
          average_turnover_rate: null,
          total_amount: null,
          heat_score: 60,
          risk_score: 40,
          evidence_coverage: 0.67,
          leader: null,
          constituents: [],
          missing_evidence: ["成分股"],
        }],
      }),
    };
  });
  vi.stubGlobal("fetch", fetchMock);

  renderWithClient(<MarketGroupPage kind="concept" />, "/concepts?group=BK025");

  const focus = await screen.findByRole("region", { name: "测试概念概念焦点" });
  expect((await within(focus).findAllByText("贵州茅台")).length).toBeGreaterThan(0);
  expect(within(focus).getByText("上涨扩散").nextSibling).toHaveTextContent("100%");
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/v1/market-structure/groups/concept/BK025",
    expect.anything(),
  );
});

it("offers an inline retry when selected group evidence remains unavailable", async () => {
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    const isDetail = String(input).includes("/groups/concept/BK025");
    return {
      ok: true,
      status: 200,
      json: async () => ({
        meta,
        kind: "concept",
        available: true,
        degraded: isDetail,
        unavailable_reason: isDetail ? "constituent request unavailable" : null,
        summary: "板块行情可用。",
        methodology: [],
        groups: [{
          code: "BK025",
          name: "测试概念",
          kind: "concept",
          change_pct: 1.2,
          net_flow: 120_000_000,
          constituent_count: 0,
          advancing: 0,
          declining: 0,
          average_change_pct: null,
          average_turnover_rate: null,
          total_amount: null,
          heat_score: 60,
          risk_score: 40,
          evidence_coverage: 0.67,
          leader: null,
          constituents: [],
          missing_evidence: ["成分股"],
        }],
      }),
    };
  }));

  renderWithClient(<MarketGroupPage kind="concept" />, "/concepts?group=BK025");

  expect(await screen.findByText("成分股证据暂未取得")).toBeInTheDocument();
  expect(screen.getByText("板块涨跌和资金仍可参考，扩散、换手与龙头暂不能确认。")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "重试成分股证据" })).toBeInTheDocument();
});

it("switches ladder direction and keeps confidence and raw-price disclosure visible", async () => {
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    const down = String(input).includes("mode=down");
    const directionQuote = { ...quote, name: down ? "跌停样本" : "涨停样本", change_pct: down ? -10 : 10 };
    return {
      ok: true,
      status: 200,
      json: async () => ({
        meta,
        mode: down ? "down" : "up",
        available: true,
        unavailable_reason: null,
        total: 1,
        max_streak: 2,
        confidence: 0.9,
        levels: [{
          streak: 2,
          label: "2板",
          stocks: [{ quote: directionQuote, streak: 2, limit_pct: 10, one_word: true, confidence: 0.9, evidence: ["未复权日线验证"] }],
        }],
        industry_distribution: { 白酒: 1 },
        methodology: ["连续板数只使用未复权原始日线验证。", "封单金额不作推测。"],
      }),
    };
  }));

  renderWithClient(<LimitLadderPage />, "/limit-ladder");

  expect(await screen.findByText("涨停样本")).toBeInTheDocument();
  expect(screen.getByText("证据覆盖，不是上涨概率")).toBeInTheDocument();
  expect(screen.getByText("无盘口证据，不作估算")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "跌停梯队" }));
  expect(await screen.findByText("跌停样本")).toBeInTheDocument();
  const stockLink = screen.getByRole("link", { name: /跌停样本/ });
  expect(stockLink).toHaveAttribute("href", "/stocks?symbol=SH.600519&from=limit-ladder");
});

it("bounds long ladder levels and lets the user reveal or collapse the rest", async () => {
  const stocks = Array.from({ length: 14 }, (_, index) => ({
    quote: {
      ...quote,
      symbol: `SH.${String(600000 + index).padStart(6, "0")}`,
      code: String(600000 + index).padStart(6, "0"),
      name: `涨停样本${index + 1}`,
    },
    streak: 1,
    limit_pct: 10,
    one_word: false,
    confidence: 0.9,
    evidence: ["未复权日线验证"],
  }));
  vi.stubGlobal("fetch", vi.fn(async () => ({
    ok: true,
    status: 200,
    json: async () => ({
      meta,
      mode: "up",
      available: true,
      unavailable_reason: null,
      total: stocks.length,
      max_streak: 1,
      confidence: 0.9,
      levels: [{ streak: 1, label: "首板", stocks }],
      industry_distribution: { 白酒: stocks.length },
      methodology: ["连续板数只使用未复权原始日线验证。"],
    }),
  })));

  renderWithClient(<LimitLadderPage />, "/limit-ladder");

  expect(await screen.findByText("涨停样本12")).toBeInTheDocument();
  expect(screen.queryByText("涨停样本13")).not.toBeInTheDocument();
  const expand = screen.getByRole("button", { name: /再显示 2 只/ });
  expect(expand).toHaveAttribute("aria-expanded", "false");

  fireEvent.click(expand);
  expect(screen.getByText("涨停样本14")).toBeInTheDocument();
  const collapse = screen.getByRole("button", { name: /收起至前 12 只/ });
  expect(collapse).toHaveAttribute("aria-expanded", "true");

  fireEvent.click(collapse);
  expect(screen.queryByText("涨停样本13")).not.toBeInTheDocument();
});

it("bounds a long constituent list and resets it when the selected group changes", async () => {
  const constituents = Array.from({ length: 13 }, (_, index) => ({
    ...quote,
    symbol: `SH.${String(600100 + index).padStart(6, "0")}`,
    code: String(600100 + index).padStart(6, "0"),
    name: `概念成分${index + 1}`,
  }));
  vi.stubGlobal("fetch", vi.fn(async () => ({
    ok: true,
    status: 200,
    json: async () => ({
      meta,
      kind: "concept",
      available: true,
      degraded: false,
      unavailable_reason: null,
      summary: "当前覆盖 2 个概念。",
      methodology: ["当前只比较最新横截面。"],
      groups: [
        {
          code: "BK100",
          name: "长名单概念",
          kind: "concept",
          change_pct: 2.1,
          net_flow: 100_000_000,
          constituent_count: constituents.length,
          advancing: constituents.length,
          declining: 0,
          average_change_pct: 2.1,
          average_turnover_rate: 0.8,
          total_amount: 2_000_000_000,
          heat_score: 82,
          risk_score: 18,
          evidence_coverage: 1,
          leader: { quote: constituents[0], score: 88 },
          constituents,
          missing_evidence: [],
        },
        {
          code: "BK200",
          name: "短名单概念",
          kind: "concept",
          change_pct: 0.5,
          net_flow: 10_000_000,
          constituent_count: 1,
          advancing: 1,
          declining: 0,
          average_change_pct: 0.5,
          average_turnover_rate: 0.5,
          total_amount: 100_000_000,
          heat_score: 50,
          risk_score: 30,
          evidence_coverage: 0.8,
          leader: null,
          constituents: [quote],
          missing_evidence: [],
        },
      ],
    }),
  })));

  renderWithClient(<MarketGroupPage kind="concept" />, "/concepts");

  expect(await screen.findByText("概念成分12")).toBeInTheDocument();
  expect(screen.queryByText("概念成分13")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: /再显示 1 只成分股/ }));
  expect(screen.getByText("概念成分13")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: /短名单概念/ }));
  expect(await screen.findByRole("region", { name: "短名单概念概念焦点" })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: /长名单概念/ }));
  expect(await screen.findByRole("region", { name: "长名单概念概念焦点" })).toBeInTheDocument();
  expect(screen.queryByText("概念成分13")).not.toBeInTheDocument();
});
