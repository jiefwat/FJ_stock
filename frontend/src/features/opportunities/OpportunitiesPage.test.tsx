import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";

import { OpportunitiesPage } from "./OpportunitiesPage";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("shows professional strategy diagnostics and candidate decision cards", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => ({
    ok: true,
    status: 200,
    json: async () => ({
      preset: "trend",
      available: true,
      unavailable_reason: null,
      summary: "趋势延续策略当前可运行，样本压力适中，适合先做短名单。",
      rules: ["涨幅 0.5% 至 7%", "成交额至少 3 亿元"],
      funnel: { universe: 5527, excluded: 5350, ranked: 177 },
      diagnostics: [
        { key: "market_fit", label: "市场适配", signal: "neutral", score: 58, summary: "市场偏谨慎，候选需要扣减环境分", evidence: ["环境扣分 8"] },
        { key: "selection_pressure", label: "筛选压力", signal: "positive", score: 72, summary: "入选率 3.2%，短名单足够收敛", evidence: ["177 / 5527"] },
      ],
      next_actions: ["先核对前 10 名的资金和板块证据", "风险收益不足的候选不追高"],
      candidates: [{
        quote: { symbol: "SZ.002396", code: "002396", name: "星网锐捷", price: 18.8, change_pct: 3.2, amount: 680000000, turnover_rate: 5.2, volume_ratio: 1.8, pe: 32, pb: 2.6, market_cap: 12000000000, net_flow: 26000000, sector: "通信设备" },
        base_score: 86,
        context_penalty: 8,
        score: 78,
        evidence_coverage: 0.82,
        components: [{ key: "trend", label: "价格趋势", raw_value: 3.2, score: 77, weight: 0.25, weighted_score: 19.25 }],
        dimensions: [
          { key: "trigger", label: "触发逻辑", signal: "positive", score: 76, summary: "温和上涨且成交额达标", evidence: ["涨幅 3.2%", "成交额 6.8 亿"] },
          { key: "risk_control", label: "风险控制", signal: "neutral", score: 55, summary: "需要避免追高", evidence: ["环境扣分 8"] },
          { key: "capital_flow", label: "资金态度", signal: "positive", score: 71, summary: "资金净流入确认", evidence: ["净流入 2600 万"] },
          { key: "sector_context", label: "板块位置", signal: "neutral", score: 58, summary: "通信设备板块需要联动复核", evidence: ["通信设备"] },
          { key: "catalyst_check", label: "催化核验", signal: "missing", score: null, summary: "公告和研报催化待补齐", evidence: ["公告待读", "研报待补"] },
        ],
        thesis: "趋势延续候选：价格温和走强，流动性可验证。",
        invalidation: ["跌回策略涨幅区间外", "成交额低于策略门槛"],
        next_actions: ["打开个股证据账本复核均线与资金", "加入跟踪前写清关注理由"],
        risk_flags: ["市场偏弱"],
      }],
      excluded: [{ reasons: ["strategy_mismatch"] }],
    }),
  })));
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });

  render(<QueryClientProvider client={client}><MemoryRouter><OpportunitiesPage /></MemoryRouter></QueryClientProvider>);

  expect(await screen.findByText("策略诊断")).toBeInTheDocument();
  expect(screen.getByText("市场适配")).toBeInTheDocument();
  expect(screen.getByText("筛选压力")).toBeInTheDocument();
  expect(screen.getByText("机会处理清单")).toBeInTheDocument();
  expect(screen.getByText("触发逻辑")).toBeInTheDocument();
  expect(screen.getByText("风险控制")).toBeInTheDocument();
  expect(screen.getByText("资金态度")).toBeInTheDocument();
  expect(screen.getByText("板块位置")).toBeInTheDocument();
  expect(screen.getByText("催化核验")).toBeInTheDocument();
  expect(screen.getByText("入选理由")).toBeInTheDocument();
  expect(screen.getByText(/趋势延续候选/)).toBeInTheDocument();
  expect(screen.getByText("失效条件")).toBeInTheDocument();
  expect(screen.getByText(/跌回策略涨幅区间外/)).toBeInTheDocument();
});

it("offers only effective primary strategies instead of data-blocked presets", async () => {
  const fetchMock = vi.fn(async () => ({
    ok: true,
    status: 200,
    json: async () => ({
      preset: "trend",
      available: true,
      unavailable_reason: null,
      summary: "当前策略可运行。",
      rules: ["使用当前行情字段"],
      funnel: { universe: 5527, excluded: 5400, ranked: 127 },
      diagnostics: [],
      next_actions: ["打开个股证据账本复核"],
      candidates: [],
      excluded: [],
    }),
  }));
  vi.stubGlobal("fetch", fetchMock);
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });

  render(<QueryClientProvider client={client}><MemoryRouter><OpportunitiesPage /></MemoryRouter></QueryClientProvider>);

  expect(await screen.findByRole("button", { name: "趋势延续" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "放量突破" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "低估反弹" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "超跌修复" })).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "板块改善" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "资金确认" })).not.toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "放量突破" }));
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/v1/opportunities?preset=volume_breakout",
    expect.any(Object),
  );
});
