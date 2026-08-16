import type { Candidate, DecisionPresentation as ApiDecisionPresentation, HoldingDossier } from "./api";

export type DecisionTone = "positive" | "caution" | "negative" | "neutral";

export type DecisionPresentation = {
  action: string;
  summary: string;
  tone: DecisionTone;
  userRequired: boolean;
};

export type OpportunityDecision = DecisionPresentation & {
  layer: "priority" | "review" | "watch_only" | "high_risk";
};

function candidateScore(candidate: Candidate) {
  return candidate.upside_score ?? candidate.score;
}

function contractTone(decision: ApiDecisionPresentation): DecisionTone {
  if (decision.layer === "high_risk" || decision.severity === "critical") return "negative";
  if (decision.severity === "high" || decision.layer === "watch_only") return "caution";
  if (decision.severity === "action") return "positive";
  return "neutral";
}

export function opportunityDecision(candidate: Candidate): OpportunityDecision {
  if (candidate.decision) {
    return {
      action: candidate.decision.action,
      summary: candidate.decision.summary,
      tone: contractTone(candidate.decision),
      userRequired: candidate.decision.user_required,
      layer: candidate.decision.layer ?? "review",
    };
  }
  const history = candidate.history_check;
  const historyRisk = Boolean(history?.risk_flags.length) || (history?.score != null && history.score < 45);
  const historyConfirmed = !history || (history.available && history.score != null && history.score >= 65 && history.risk_flags.length === 0);

  if (historyRisk) {
    return {
      action: "暂不参与",
      summary: "过去价格涨得偏急、起伏较大或从高点回落较多。",
      tone: "negative",
      userRequired: false,
      layer: "high_risk",
    };
  }
  if (candidate.evidence_coverage < 0.65 || candidate.risk_flags.length >= 3 || candidate.context_penalty >= 15) {
    return {
      action: "暂不参与",
      summary: "信息不够完整，或当前市场环境不支持参与。",
      tone: "negative",
      userRequired: false,
      layer: "high_risk",
    };
  }
  if (candidateScore(candidate) >= 75 && candidate.evidence_coverage >= 0.75 && candidate.context_penalty === 0 && historyConfirmed) {
    return {
      action: "可小仓试探",
      summary: "参考分、历史表现和信息完整度均靠前，限小仓执行。",
      tone: "positive",
      userRequired: true,
      layer: "priority",
    };
  }
  if (candidateScore(candidate) < 60 || candidate.context_penalty > 0) {
    return {
      action: "暂不买入",
      summary: "当前市场环境或可能收益与风险不支持参与。",
      tone: "caution",
      userRequired: false,
      layer: "watch_only",
    };
  }
  return {
    action: "仅观察",
    summary: "方向有一定支持，但关键资料还没有达到参与标准。",
    tone: "neutral",
    userRequired: false,
    layer: "review",
  };
}

export function holdingDecision(input: HoldingDossier | HoldingDossier["action"]): DecisionPresentation {
  if (typeof input !== "string" && input.decision) {
    return {
      action: input.decision.action,
      summary: input.decision.summary,
      tone: contractTone(input.decision),
      userRequired: input.decision.user_required,
    };
  }
  const action = typeof input === "string" ? input : input.action;
  const decisions: Record<string, DecisionPresentation> = {
    hold: {
      action: "继续持有",
      summary: "当前未触发调仓条件。",
      tone: "neutral",
      userRequired: false,
    },
    add_watch: {
      action: "仅小幅加仓",
      summary: "条件相对有利，但只适合小步执行并设置退出条件。",
      tone: "positive",
      userRequired: true,
    },
    trim: {
      action: "建议分批减仓",
      summary: "先降低仓位，减少单只股票对整仓的影响。",
      tone: "caution",
      userRequired: true,
    },
    exit_watch: {
      action: "优先减仓或止损",
      summary: "已经触发风险条件，不建议继续补仓或等待反弹。",
      tone: "negative",
      userRequired: true,
    },
    review: {
      action: "暂不操作",
      summary: "缺少成本、数量或持有原因，补齐后再给调仓决定。",
      tone: "caution",
      userRequired: false,
    },
  };
  return decisions[action] ?? decisions.review;
}

export function stockDecisionAction(action: string): string {
  const decisions: Record<string, string> = {
    可小仓试错: "可小仓试探",
    持有观察: "仅观察",
    等待回踩: "暂不买入",
    暂不参与: "暂不参与",
  };
  return decisions[action] ?? action;
}
