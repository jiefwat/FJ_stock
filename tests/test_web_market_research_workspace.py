import inspect

from stock_ts import web
from stock_ts.research.evidence import EvidenceStatus
from stock_ts.research.market_regime import (
    MarketRegimeAssessment,
    MarketRegimeDimension,
    MarketScenario,
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
