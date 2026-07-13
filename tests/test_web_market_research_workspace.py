import inspect

from stock_ts import web
from stock_ts.models import IndexQuote, MarketHistoryPoint, MarketSnapshot
from stock_ts.research.evidence import EvidenceStatus
from stock_ts.research.market_regime import (
    MarketRegimeAssessment,
    MarketRegimeDimension,
    MarketScenario,
    assess_market_regime,
)
from stock_ts.webapp.market_workspace import render_market_workspace


def _assessment(*, stage: str = "进攻", degraded: bool = False) -> MarketRegimeAssessment:
    note = "仅有当日截面，不能确认趋势持续性。" if degraded else "宽度与情绪共振。"
    return MarketRegimeAssessment(
        trade_date="2026-07-13",
        stage=stage,
        risk_budget="70%-85%",
        confidence=74,
        thesis="风险偏好扩张，但需要跨期量能确认。",
        primary_risk="单日脉冲可能快速退潮。",
        supporting_evidence=("宽度比 2.10", "涨停显著多于跌停"),
        counter_evidence=(note,),
        invalidate_condition="宽度回落或主线前排破位。",
        dimensions=(
            MarketRegimeDimension(
                "趋势",
                EvidenceStatus.DEGRADED if degraded else EvidenceStatus.COMPLETE,
                "指数偏强",
                note,
                62,
                ("指数历史序列",) if degraded else (),
            ),
        ),
        scenarios=(
            MarketScenario("偏强", "宽度改善", "上调风险预算", "主线退潮"),
            MarketScenario("基准", "维持轮动", "维持预算", "宽度恶化"),
            MarketScenario("偏弱", "跌停扩散", "降低风险", "风险收敛"),
        ),
    )


def test_market_workspace_orders_decision_before_evidence() -> None:
    html = render_market_workspace(_assessment())

    assert 'data-market-stage="进攻"' in html
    assert html.index("市场状态") < html.index("趋势与宽度")
    assert html.index("最大风险") < html.index("三情景推演")
    assert "市场风险预算" in html
    assert "买卖指导" not in html


def test_market_workspace_exposes_snapshot_limitations() -> None:
    html = render_market_workspace(_assessment(degraded=True))

    assert "仅有当日截面" in html
    assert "持续增强" not in html
    assert "指数历史序列" in html


def test_market_orchestration_consumes_typed_quote_status() -> None:
    source = inspect.getsource(web._render_compact_market_module)

    assert "quality.quote_status" in source
    assert '"数据已滞后" in warning' not in source


def test_market_workspace_renders_cross_period_evidence() -> None:
    history = [
        MarketHistoryPoint(
            f"2026-07-{10 + index:02d}",
            2000 + index * 300,
            2800 - index * 250,
            (2000 + index * 300) / (2800 - index * 250),
            50 + index * 5,
            24 - index * 4,
            9000 + index * 600,
        )
        for index in range(3)
    ]
    market = MarketSnapshot(
        trade_date="2026-07-12",
        heat_score=58,
        breadth_ratio=1.2,
        summary="测试",
        regime="轮动",
        indices=[IndexQuote("000001", "上证指数", 3500, 0.5, 10200)],
        top_sectors=[("机器人", 2.1)],
        dimensions=[],
        opportunities=[],
        risks=[],
        tomorrow_watch=[],
        limit_up_count=60,
        limit_down_count=16,
        advancing_count=2600,
        declining_count=2200,
        history=history,
    )

    html = render_market_workspace(assess_market_regime(market))

    assert "近 3 个交易日" in html
    assert "流动性代理" in html
