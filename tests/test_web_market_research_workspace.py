import inspect
from dataclasses import replace

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


def test_market_workspace_has_one_ordered_five_step_decision_rail() -> None:
    html = render_market_workspace(_assessment())

    assert html.count('data-primary-market-verdict="true"') == 1
    assert html.count('class="market-decision-rail-step') == 5
    labels = ["当前市场阶段", "进攻确认", "仓位预算", "降级触发", "重新评估"]
    assert [html.index(label) for label in labels] == sorted(
        html.index(label) for label in labels
    )
    assert html.index("核心判断") < html.index("五步风险决策轨道")
    assert html.index("五步风险决策轨道") < html.index("趋势与宽度")


def test_market_workspace_uses_three_session_playbook_and_preserves_details() -> None:
    html = render_market_workspace(
        _assessment(),
        distribution_html="DISTRIBUTION-EVIDENCE",
        sectors_html="MAINLINE-EVIDENCE",
        intraday_detail_html="INTRADAY-DETAIL-EVIDENCE",
        close_html="CLOSE-REVIEW-EVIDENCE",
    )

    assert html.count('class="market-session-phase') == 3
    phase_labels = ["盘前框架", "盘中验证", "收盘复核"]
    assert [html.index(label) for label in phase_labels] == sorted(
        html.index(label) for label in phase_labels
    )
    live_phase_start = html.index('class="market-session-phase phase-live"')
    assert html.index("核心判断") < live_phase_start
    assert html.index("三情景推演") < live_phase_start
    assert "DISTRIBUTION-EVIDENCE" in html
    assert "MAINLINE-EVIDENCE" in html
    assert '<details class="market-evidence essence-evidence">' in html
    assert "大盘证据" in html
    assert html.index("INTRADAY-DETAIL-EVIDENCE") < html.index(
        "CLOSE-REVIEW-EVIDENCE"
    )
    details_start = html.index('<details class="market-evidence essence-evidence">')
    details_tag_end = html.index(">", details_start)
    assert " open" not in html[details_start:details_tag_end]


def test_stale_market_rail_pauses_every_step_and_hides_old_triggers() -> None:
    stale = replace(
        _assessment(),
        stage="数据暂停",
        risk_budget="0%",
        confidence=0,
        thesis="行情时效未通过，暂停按当前盘面形成市场判断。",
        primary_risk="行情已过期，任何进攻性结论都可能基于错误时点。",
        supporting_evidence=("数据质量闸门已阻断",),
        counter_evidence=("等待最近交易日行情后重新评估",),
        invalidate_condition="最近交易日行情、宽度和指数数据刷新并通过校验。",
    )

    html = render_market_workspace(stale)
    rail = html.split('data-market-rail-state="paused"', 1)[1].split(
        "趋势与宽度", 1
    )[0]

    assert rail.count('class="market-decision-rail-step') == 5
    assert rail.count("暂停") + rail.count("刷新") >= 5
    assert "70%-85%" not in rail
    assert "宽度回落或主线前排破位" not in rail


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
