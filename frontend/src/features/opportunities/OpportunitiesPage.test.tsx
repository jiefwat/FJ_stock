import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
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
      summary: "趋势延续线索策略当前可运行，样本压力适中，适合先做短名单。",
      rules: ["涨幅 0.5% 至 7%", "成交额至少 3 亿元"],
      funnel: { universe: 5527, excluded: 5350, ranked: 177 },
      diagnostics: [
        { key: "market_fit", label: "市场适配", signal: "neutral", score: 58, summary: "市场偏谨慎，线索需要扣减环境分", evidence: ["环境扣分 8"] },
        { key: "selection_pressure", label: "筛选压力", signal: "positive", score: 72, summary: "线索率 3.2%，短名单足够收敛", evidence: ["177 / 5527"] },
      ],
      next_actions: ["先核对前 10 名的资金和板块证据", "风险收益不足的线索不追高"],
      candidates: [{
        quote: { symbol: "SZ.002396", code: "002396", name: "星网锐捷", price: 18.8, change_pct: 3.2, amount: 680000000, turnover_rate: 5.2, volume_ratio: 1.8, pe: 32, pb: 2.6, market_cap: 12000000000, net_flow: 26000000, sector: "通信设备" },
        base_score: 86,
        context_penalty: 8,
        score: 64,
        upside_score: 64,
        upside_label: "有弹性待确认",
        upside_summary: "有弹性待确认：上涨评分 64/100，趋势温和但市场扣分。风险：市场环境扣 8 分；催化仍需确认。",
        upside_drivers: ["当日涨幅 3.2% 未明显过热", "主动资金净流入 +2600 万"],
        upside_risks: ["市场环境扣 8 分", "催化仍需公告、业绩或研报确认"],
        evidence_coverage: 0.82,
        components: [{ key: "trend", label: "价格趋势", raw_value: 3.2, score: 77, weight: 0.25, weighted_score: 19.25 }],
        dimensions: [
          { key: "trigger", label: "触发逻辑", signal: "positive", score: 76, summary: "温和上涨且成交额达标", evidence: ["涨幅 3.2%", "成交额 6.8 亿"] },
          { key: "history_confirmation", label: "历史确认", signal: "neutral", score: 62, summary: "历史确认需复核：20日趋势 +5.2%，MA20偏离 +9.1%，未明显追高。", evidence: ["20日趋势 +5.2%", "MA20偏离 +9.1%"] },
          { key: "risk_control", label: "风险控制", signal: "neutral", score: 55, summary: "需要避免追高", evidence: ["环境扣分 8"] },
          { key: "capital_flow", label: "资金态度", signal: "positive", score: 71, summary: "资金净流入确认", evidence: ["净流入 2600 万"] },
          { key: "sector_context", label: "板块位置", signal: "neutral", score: 58, summary: "通信设备板块需要联动复核", evidence: ["通信设备"] },
          { key: "catalyst_check", label: "催化核验", signal: "missing", score: null, summary: "公告和研报催化待补齐", evidence: ["公告待读", "研报待补"] },
        ],
        history_check: {
          available: true,
          lookback_days: 120,
          score: 62,
          trend_20d_pct: 5.2,
          trend_60d_pct: 12.4,
          ma20_gap_pct: 9.1,
          volatility_20d: 32.6,
          max_drawdown_60d: 11.8,
          volume_ratio_20d: 1.3,
          summary: "历史确认需复核：20日趋势 +5.2%，MA20偏离 +9.1%，未明显追高。",
          evidence: ["20日趋势 +5.2%", "60日趋势 +12.4%", "MA20偏离 +9.1%", "量能 1.3x"],
          risk_flags: [],
        },
        thesis: "趋势延续线索：价格温和走强，流动性可验证；是否参与以个股证据账本为准。",
        invalidation: ["跌回策略涨幅区间外", "成交额低于策略门槛"],
        next_actions: ["打开个股证据账本复核均线与资金", "写清参与条件和放弃条件"],
        risk_flags: ["市场偏弱"],
      }, {
        quote: { symbol: "SZ.300750", code: "300750", name: "宁德时代", price: 218.6, change_pct: 4.1, amount: 12800000000, turnover_rate: 3.8, volume_ratio: 1.9, pe: 24, pb: 4.2, market_cap: 950000000000, net_flow: 690000000, sector: "电池" },
        base_score: 88,
        context_penalty: 0,
        score: 88,
        upside_score: 88,
        upside_label: "高概率延续",
        upside_summary: "高概率延续：上涨评分 88/100，趋势、资金、买点质量同时较强。风险：催化仍需确认。",
        upside_drivers: ["趋势持续性 76/100，未来上涨线索更强", "距 MA20 +5.1%，买点不拥挤", "主动资金净流入 +6.9 亿"],
        upside_risks: ["催化仍需公告、业绩或研报确认"],
        evidence_coverage: 0.86,
        components: [{ key: "trend", label: "价格趋势", raw_value: 4.1, score: 89, weight: 0.25, weighted_score: 22.25 }],
        dimensions: [
          { key: "trigger", label: "触发逻辑", signal: "positive", score: 88, summary: "趋势和成交同步改善", evidence: ["涨幅 4.1%", "成交额 128 亿"] },
          { key: "history_confirmation", label: "历史确认", signal: "positive", score: 76, summary: "历史确认通过：20日趋势 +8.4%，MA20偏离 +5.1%，未明显追高。", evidence: ["20日趋势 +8.4%", "60日趋势 +16.2%", "MA20偏离 +5.1%"] },
          { key: "risk_control", label: "风险控制", signal: "positive", score: 68, summary: "环境没有扣分", evidence: ["环境扣分 0"] },
        ],
        history_check: {
          available: true,
          lookback_days: 120,
          score: 76,
          trend_20d_pct: 8.4,
          trend_60d_pct: 16.2,
          ma20_gap_pct: 5.1,
          volatility_20d: 28,
          max_drawdown_60d: 9.5,
          volume_ratio_20d: 1.4,
          summary: "历史确认通过：20日趋势 +8.4%，MA20偏离 +5.1%，未明显追高。",
          evidence: ["20日趋势 +8.4%", "60日趋势 +16.2%", "MA20偏离 +5.1%", "量能 1.4x"],
          risk_flags: [],
        },
        thesis: "趋势延续线索：价格和资金同步走强；是否参与以个股证据账本为准。",
        invalidation: ["放量失败", "跌回策略涨幅区间外"],
        next_actions: ["打开个股证据账本复核均线与资金"],
        risk_flags: [],
      }],
      excluded: [{ reasons: ["strategy_mismatch"] }],
    }),
  })));
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });

  render(<QueryClientProvider client={client}><MemoryRouter><OpportunitiesPage /></MemoryRouter></QueryClientProvider>);

  expect(await screen.findByText("机会")).toBeInTheDocument();
  expect(screen.queryByText("策略诊断")).not.toBeInTheDocument();
  expect(within(await screen.findByLabelText("机会线索队列")).getByText("优先")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /最可能上涨\s*宁德时代/ })).toHaveAttribute("href", "/stocks?symbol=SZ.300750&from=opportunities&preset=trend");
  const queueActions = within(screen.getByLabelText("第一候选快捷动作"));
  expect(queueActions.getByRole("link", { name: "打开个股" })).toHaveAttribute("href", "/stocks?symbol=SZ.300750&from=opportunities&preset=trend");
  expect(queueActions.getByRole("link", { name: "问升级" })).toHaveAttribute("href", "/ask?symbol=SZ.300750&name=%E5%AE%81%E5%BE%B7%E6%97%B6%E4%BB%A3&from=opportunities&preset=trend&question=%E5%AE%81%E5%BE%B7%E6%97%B6%E4%BB%A3%E8%BF%99%E6%9D%A1%E8%B6%8B%E5%8A%BF%E5%BB%B6%E7%BB%AD%E7%BA%BF%E7%B4%A2%E8%83%BD%E5%8D%87%E7%BA%A7%E5%90%97");
  expect(queueActions.getByRole("link", { name: "问风险" })).toHaveAttribute("href", "/ask?symbol=SZ.300750&name=%E5%AE%81%E5%BE%B7%E6%97%B6%E4%BB%A3&from=opportunities&preset=trend&question=%E5%AE%81%E5%BE%B7%E6%97%B6%E4%BB%A3%E8%BF%99%E6%9D%A1%E7%BA%BF%E7%B4%A2%E4%B8%BB%E8%A6%81%E9%A3%8E%E9%99%A9%E6%98%AF%E4%BB%80%E4%B9%88");
  expect(screen.queryByRole("button", { name: "队列筛选优先线索 1" })).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: /全部\s*2/ })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /优先\s*1/ })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /观察\s*1/ })).toBeInTheDocument();
  expect(screen.getAllByText("观察").length).toBeGreaterThanOrEqual(1);
  expect(screen.getAllByText("优先").length).toBeGreaterThanOrEqual(1);
  expect(screen.queryByRole("link", { name: "看个股 →" })).not.toBeInTheDocument();
  expect(screen.queryByText("市场适配")).not.toBeInTheDocument();
  expect(screen.queryByText("筛选压力")).not.toBeInTheDocument();
  expect(screen.getAllByText("全部").length).toBeGreaterThanOrEqual(1);
  expect(screen.getByRole("button", { name: /星网锐捷/ })).toHaveAttribute("aria-expanded", "false");
  expect(screen.queryByText("历史K线")).not.toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: /星网锐捷/ }));
  expect(screen.getByRole("button", { name: /星网锐捷/ })).toHaveAttribute("aria-expanded", "true");
  const starActions = within(screen.getByLabelText("星网锐捷 线索快捷动作"));
  expect(starActions.getByRole("link", { name: "看个股 →" })).toHaveAttribute("href", "/stocks?symbol=SZ.002396&from=opportunities&preset=trend");
  expect(starActions.getByRole("link", { name: "问线索能否升级 →" })).toHaveAttribute("href", "/ask?symbol=SZ.002396&name=%E6%98%9F%E7%BD%91%E9%94%90%E6%8D%B7&from=opportunities&preset=trend&question=%E6%98%9F%E7%BD%91%E9%94%90%E6%8D%B7%E8%BF%99%E6%9D%A1%E8%B6%8B%E5%8A%BF%E5%BB%B6%E7%BB%AD%E7%BA%BF%E7%B4%A2%E8%83%BD%E5%8D%87%E7%BA%A7%E5%90%97");
  expect(starActions.getByRole("link", { name: "问风险 →" })).toHaveAttribute("href", "/ask?symbol=SZ.002396&name=%E6%98%9F%E7%BD%91%E9%94%90%E6%8D%B7&from=opportunities&preset=trend&question=%E6%98%9F%E7%BD%91%E9%94%90%E6%8D%B7%E8%BF%99%E6%9D%A1%E7%BA%BF%E7%B4%A2%E4%B8%BB%E8%A6%81%E9%A3%8E%E9%99%A9%E6%98%AF%E4%BB%80%E4%B9%88");
  expect(screen.getAllByText("上涨评分").length).toBeGreaterThanOrEqual(1);
  expect(screen.getAllByText("为什么可能涨").length).toBeGreaterThanOrEqual(1);
  expect(screen.getAllByText("还差什么确认").length).toBeGreaterThanOrEqual(1);
  expect(screen.getAllByText("历史K线").length).toBeGreaterThanOrEqual(1);
  expect(screen.getAllByText("20日趋势").length).toBeGreaterThanOrEqual(1);
  expect(screen.getAllByText("60日趋势").length).toBeGreaterThanOrEqual(1);
  expect(screen.getAllByText("MA20偏离").length).toBeGreaterThanOrEqual(1);
  expect(screen.getByText("更多依据")).toBeInTheDocument();
  fireEvent.click(screen.getByText("更多依据"));
  expect(screen.getAllByText("触发逻辑").length).toBeGreaterThanOrEqual(1);
  expect(screen.getAllByText("风险控制").length).toBeGreaterThanOrEqual(1);
  expect(screen.getByText("资金态度")).toBeInTheDocument();
  expect(screen.getByText("板块位置")).toBeInTheDocument();
  expect(screen.getByText("催化核验")).toBeInTheDocument();
  expect(screen.getAllByText("线索理由").length).toBeGreaterThanOrEqual(1);
  expect(screen.getAllByText(/趋势延续线索/).length).toBeGreaterThanOrEqual(1);
  expect(screen.getAllByText("失效条件").length).toBeGreaterThanOrEqual(1);
  expect(screen.getAllByText(/跌回策略涨幅区间外/).length).toBeGreaterThanOrEqual(1);

  fireEvent.click(screen.getByRole("button", { name: /优先\s*1/ }));
  expect(screen.getAllByText("优先").length).toBeGreaterThanOrEqual(1);
  expect(screen.getAllByText("宁德时代").length).toBeGreaterThanOrEqual(1);
  fireEvent.click(screen.getByRole("button", { name: /宁德时代/ }));
  expect(within(screen.getByLabelText("宁德时代 线索快捷动作")).getByRole("link", { name: "看个股 →" })).toHaveAttribute("href", "/stocks?symbol=SZ.300750&from=opportunities&preset=trend");
  expect(screen.queryByText("星网锐捷")).not.toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: /观察\s*1/ }));
  expect(screen.getAllByText("观察").length).toBeGreaterThanOrEqual(1);
  expect(screen.getByText("星网锐捷")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: /星网锐捷/ }));
  expect(within(screen.getByLabelText("星网锐捷 线索快捷动作")).getByRole("link", { name: "看个股 →" })).toHaveAttribute("href", "/stocks?symbol=SZ.002396&from=opportunities&preset=trend");
});

it("offers only effective primary strategies instead of data-blocked presets", async () => {
  const fetchMock = vi.fn(async () => ({
    ok: true,
    status: 200,
    json: async () => ({
      preset: "trend",
      available: true,
      unavailable_reason: null,
      summary: "当前线索策略可运行。",
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
    "/api/v1/opportunities?preset=volume_breakout&limit=20",
    expect.any(Object),
  );
});
