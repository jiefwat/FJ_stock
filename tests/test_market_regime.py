from dataclasses import replace

from stock_ts.models import IndexQuote, MarketHistoryPoint, MarketSnapshot
from stock_ts.research.evidence import EvidenceStatus
from stock_ts.research.market_regime import assess_market_regime


def _market(
    *,
    heat: int,
    advancing: int,
    declining: int,
    limit_down: int,
    amount: float = 5000,
) -> MarketSnapshot:
    return MarketSnapshot(
        trade_date="2026-07-13",
        heat_score=heat,
        breadth_ratio=advancing / max(declining, 1),
        summary="测试市场",
        regime="震荡",
        indices=[IndexQuote("000001", "上证指数", 3500, 1.1, amount)],
        top_sectors=[("机器人", 3.2)],
        dimensions=[],
        opportunities=[],
        risks=[],
        tomorrow_watch=[],
        limit_up_count=70,
        limit_down_count=limit_down,
        advancing_count=advancing,
        declining_count=declining,
    )


def _history(count: int) -> list[MarketHistoryPoint]:
    return [
        MarketHistoryPoint(
            trade_date=f"2026-07-{8 + index:02d}",
            advancing=1800 + index * 250,
            declining=2800 - index * 200,
            breadth_ratio=(1800 + index * 250) / (2800 - index * 200),
            limit_up=45 + index * 5,
            limit_down=25 - index * 3,
            amount=9000 + index * 500,
        )
        for index in range(count)
    ]


def _market_with_history(
    history: list[MarketHistoryPoint],
    *,
    heat: int = 58,
    limit_down: int = 12,
) -> MarketSnapshot:
    return replace(
        _market(heat=heat, advancing=2600, declining=2300, limit_down=limit_down),
        history=history,
    )


def test_assessment_identifies_attack_regime_with_counter_evidence() -> None:
    result = assess_market_regime(
        _market(heat=76, advancing=3900, declining=1100, limit_down=4)
    )

    assert result.stage == "进攻"
    assert result.risk_budget == "70%-85%"
    assert result.confidence >= 70
    assert len(result.supporting_evidence) >= 2
    assert result.counter_evidence
    assert result.invalidate_condition
    assert {item.name for item in result.dimensions} == {
        "趋势",
        "宽度",
        "流动性",
        "风格",
        "情绪",
    }


def test_assessment_blocks_when_quote_is_stale() -> None:
    result = assess_market_regime(
        _market(heat=76, advancing=3900, declining=1100, limit_down=4),
        quote_status=EvidenceStatus.STALE,
    )

    assert result.stage == "数据暂停"
    assert result.risk_budget == "0%"
    assert result.confidence == 0
    assert "行情已过期" in result.primary_risk


def test_assessment_does_not_claim_cross_period_trend_from_one_snapshot() -> None:
    result = assess_market_regime(
        _market(heat=58, advancing=2600, declining=2300, limit_down=12)
    )

    trend = next(item for item in result.dimensions if item.name == "趋势")
    liquidity = next(item for item in result.dimensions if item.name == "流动性")
    assert trend.status == EvidenceStatus.DEGRADED
    assert liquidity.status == EvidenceStatus.DEGRADED
    assert "仅有当日截面" in trend.evidence
    assert "仅有当日截面" in liquidity.evidence


def test_assessment_always_builds_three_testable_scenarios() -> None:
    result = assess_market_regime(
        _market(heat=42, advancing=1200, declining=3500, limit_down=35)
    )

    assert result.stage == "风险释放"
    assert [item.name for item in result.scenarios] == ["偏强", "基准", "偏弱"]
    assert all(item.trigger and item.action and item.invalidation for item in result.scenarios)


def test_extreme_limit_down_risk_overrides_rotation() -> None:
    result = assess_market_regime(
        _market(heat=60, advancing=2500, declining=2500, limit_down=80)
    )

    assert result.stage == "风险释放"
    assert result.risk_budget == "10%-30%"


def test_contradictory_high_heat_risk_release_reduces_confidence() -> None:
    conflicted = assess_market_regime(
        _market(heat=60, advancing=2500, declining=2500, limit_down=80)
    )
    consistent = assess_market_regime(
        _market(heat=40, advancing=1000, declining=3000, limit_down=80)
    )

    assert conflicted.stage == consistent.stage == "风险释放"
    assert conflicted.confidence < consistent.confidence


def test_one_market_history_point_keeps_single_day_limitations() -> None:
    result = assess_market_regime(_market_with_history(_history(1)))
    breadth = next(item for item in result.dimensions if item.name == "宽度")
    liquidity = next(item for item in result.dimensions if item.name == "流动性")

    assert breadth.status == EvidenceStatus.DEGRADED
    assert liquidity.status == EvidenceStatus.DEGRADED
    assert "仅有当日截面" in breadth.evidence


def test_three_market_history_points_create_cross_period_evidence() -> None:
    result = assess_market_regime(_market_with_history(_history(3)))
    breadth = next(item for item in result.dimensions if item.name == "宽度")
    liquidity = next(item for item in result.dimensions if item.name == "流动性")

    assert breadth.status == EvidenceStatus.COMPLETE
    assert liquidity.status == EvidenceStatus.COMPLETE
    assert "近 3 个交易日" in breadth.evidence
    assert "流动性代理" in liquidity.evidence
    assert "跌停" in breadth.evidence


def test_positive_history_never_overrides_current_extreme_risk() -> None:
    result = assess_market_regime(
        _market_with_history(_history(5), heat=60, limit_down=80)
    )

    assert result.stage == "风险释放"
    assert result.risk_budget == "10%-30%"
