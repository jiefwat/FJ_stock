import { expect, it } from "vitest";

import type { Candidate } from "./api";
import { holdingDecision, opportunityDecision, stockDecisionAction } from "./decision";

function candidate(overrides: Partial<Candidate> = {}): Candidate {
  return {
    quote: { symbol: "SZ.000001", code: "000001", name: "示例", price: 10, change_pct: 2, amount: 1_000_000_000, turnover_rate: 2, volume_ratio: 1.2, pe: 15, pb: 1.5, market_cap: 100_000_000_000, net_flow: 10_000_000, sector: "银行" },
    base_score: 80,
    context_penalty: 0,
    score: 80,
    upside_score: 80,
    evidence_coverage: 0.82,
    components: [],
    dimensions: [],
    thesis: "测试",
    invalidation: [],
    next_actions: [],
    risk_flags: [],
    history_check: { available: true, lookback_days: 120, score: 72, trend_20d_pct: 5, trend_60d_pct: 10, ma20_gap_pct: 3, volatility_20d: 20, max_drawdown_60d: 8, volume_ratio_20d: 1.2, summary: "稳定", evidence: [], risk_flags: [] },
    ...overrides,
  };
}

it("turns candidate scores into direct participation decisions", () => {
  expect(opportunityDecision(candidate())).toMatchObject({ action: "可小仓试探", layer: "priority", userRequired: true });
  expect(opportunityDecision(candidate({ context_penalty: 8, upside_score: 64 }))).toMatchObject({ action: "暂不买入", layer: "watch_only", userRequired: false });
  expect(opportunityDecision(candidate({ evidence_coverage: 0.5 }))).toMatchObject({ action: "暂不参与", layer: "high_risk" });
});

it("uses the server-owned decision wording when it is available", () => {
  expect(opportunityDecision(candidate({
    decision: {
      action: "服务器决定",
      summary: "服务器说明",
      severity: "action",
      user_required: true,
      reason_code: "fixture",
      layer: "priority",
    },
  }))).toMatchObject({ action: "服务器决定", summary: "服务器说明", tone: "positive" });
});

it("turns holding analysis codes into executable user-facing decisions", () => {
  expect(holdingDecision("hold").action).toBe("继续持有");
  expect(holdingDecision("add_watch").action).toBe("仅小幅加仓");
  expect(holdingDecision("trim").action).toBe("建议分批减仓");
  expect(holdingDecision("exit_watch").action).toBe("优先减仓或止损");
  expect(holdingDecision("review").action).toBe("暂不操作");
});

it("keeps Stock Lab candidate decisions separate from holding language", () => {
  expect(stockDecisionAction("可小仓试错")).toBe("可小仓试探");
  expect(stockDecisionAction("持有观察")).toBe("仅观察");
  expect(stockDecisionAction("等待回踩")).toBe("暂不买入");
  expect(stockDecisionAction("暂不参与")).toBe("暂不参与");
});
