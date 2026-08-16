from marketdesk.models import DecisionPresentation, RankedCandidate


def candidate_decision(candidate: RankedCandidate) -> DecisionPresentation:
    history = candidate.history_check
    history_risk = bool(history and history.risk_flags) or bool(
        history and history.score is not None and history.score < 45
    )
    history_confirmed = history is None or (
        history.available
        and history.score is not None
        and history.score >= 65
        and not history.risk_flags
    )
    if history_risk:
        return DecisionPresentation(
            action="暂不参与",
            summary="过去价格涨得偏急、起伏较大或从高点回落较多。",
            severity="info",
            user_required=False,
            reason_code="candidate_history_risk",
            layer="high_risk",
        )
    if (
        candidate.evidence_coverage < 0.65
        or len(candidate.risk_flags) >= 3
        or candidate.context_penalty >= 15
    ):
        return DecisionPresentation(
            action="暂不参与",
            summary="信息不够完整，或当前市场环境不支持参与。",
            severity="info",
            user_required=False,
            reason_code="candidate_evidence_or_market_risk",
            layer="high_risk",
        )
    if (
        candidate.upside_score >= 75
        and candidate.evidence_coverage >= 0.75
        and candidate.context_penalty == 0
        and history_confirmed
    ):
        return DecisionPresentation(
            action="可小仓试探",
            summary="参考分、历史表现和信息完整度均靠前，限小仓执行。",
            severity="action",
            user_required=True,
            reason_code="candidate_trial_ready",
            layer="priority",
        )
    if candidate.upside_score < 60 or candidate.context_penalty > 0:
        return DecisionPresentation(
            action="暂不买入",
            summary="当前市场环境或可能收益与风险不支持参与。",
            severity="info",
            user_required=False,
            reason_code="candidate_wait",
            layer="watch_only",
        )
    return DecisionPresentation(
        action="仅观察",
        summary="方向有一定支持，但关键资料还没有达到参与标准。",
        severity="info",
        user_required=False,
        reason_code="candidate_watch",
        layer="review",
    )


def holding_decision(action: str) -> DecisionPresentation:
    decisions = {
        "hold": DecisionPresentation(
            action="继续持有",
            summary="当前未触发调仓条件。",
            severity="info",
            user_required=False,
            reason_code="holding_hold",
        ),
        "add_watch": DecisionPresentation(
            action="仅小幅加仓",
            summary="条件相对有利，但只适合小步执行并设置退出条件。",
            severity="action",
            user_required=True,
            reason_code="holding_add_watch",
        ),
        "trim": DecisionPresentation(
            action="建议分批减仓",
            summary="先降低仓位，减少单只股票对整仓的影响。",
            severity="high",
            user_required=True,
            reason_code="holding_trim",
        ),
        "exit_watch": DecisionPresentation(
            action="优先减仓或止损",
            summary="已经触发风险条件，不建议继续补仓或等待反弹。",
            severity="critical",
            user_required=True,
            reason_code="holding_exit_watch",
        ),
        "review": DecisionPresentation(
            action="暂不操作",
            summary="缺少成本、数量或持有原因，补齐后再给调仓决定。",
            severity="info",
            user_required=False,
            reason_code="holding_review",
        ),
    }
    return decisions.get(action, decisions["review"])
