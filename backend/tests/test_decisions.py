from marketdesk.analysis.decisions import candidate_decision, holding_decision
from marketdesk.models import EquityQuote, OpportunityHistoryCheck, RankedCandidate


def candidate(**overrides: object) -> RankedCandidate:
    values: dict[str, object] = {
        "quote": EquityQuote(symbol="SZ.000001", code="000001", name="示例", price=10),
        "base_score": 80,
        "context_penalty": 0,
        "score": 80,
        "upside_score": 80,
        "evidence_coverage": 0.82,
        "components": [],
        "history_check": OpportunityHistoryCheck(
            available=True,
            lookback_days=120,
            score=72,
            summary="历史表现稳定",
        ),
    }
    values.update(overrides)
    return RankedCandidate.model_validate(values)


def test_candidate_decision_uses_direct_participation_vocabulary() -> None:
    assert candidate_decision(candidate()).action == "可小仓试探"
    assert candidate_decision(candidate(context_penalty=8, upside_score=64)).action == "暂不买入"
    assert candidate_decision(candidate(evidence_coverage=0.5)).action == "暂不参与"


def test_candidate_history_risk_blocks_participation() -> None:
    history = OpportunityHistoryCheck(
        available=True,
        lookback_days=120,
        score=70,
        summary="价格波动偏大",
        risk_flags=["短期涨幅偏急"],
    )

    decision = candidate_decision(candidate(history_check=history))

    assert decision.action == "暂不参与"
    assert decision.reason_code == "candidate_history_risk"
    assert decision.layer == "high_risk"


def test_holding_decision_marks_only_trade_changes_as_actionable() -> None:
    assert holding_decision("hold").model_dump() == {
        "action": "继续持有",
        "summary": "当前未触发调仓条件。",
        "severity": "info",
        "user_required": False,
        "reason_code": "holding_hold",
        "layer": None,
    }
    assert holding_decision("exit_watch").severity == "critical"
    assert holding_decision("exit_watch").user_required is True
    assert holding_decision("trim").severity == "high"
    assert holding_decision("add_watch").severity == "action"
