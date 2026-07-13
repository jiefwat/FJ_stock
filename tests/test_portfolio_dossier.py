from __future__ import annotations

from stock_ts.models import (
    Holding,
    IndexQuote,
    MarketSnapshot,
    PortfolioAnalysisReport,
    PositionAnalysis,
)
from stock_ts.portfolio_advice import PortfolioAdvice, PositionAdvice
from stock_ts.research.evidence import EvidenceStatus
from stock_ts.research.market_regime import assess_market_regime
from stock_ts.research.portfolio_dossier import build_portfolio_dossier


def _market() -> MarketSnapshot:
    return MarketSnapshot(
        trade_date="2026-07-13",
        heat_score=62,
        breadth_ratio=1.2,
        summary="结构轮动",
        regime="震荡轮动",
        indices=[IndexQuote("000001", "上证指数", 3500, 0.6, 5200)],
        top_sectors=[("机器人", 2.2)],
        dimensions=[],
        opportunities=[],
        risks=[],
        tomorrow_watch=[],
        limit_up_count=58,
        limit_down_count=8,
        advancing_count=3000,
        declining_count=2400,
    )


def _position(
    code: str,
    name: str,
    *,
    weight: float,
    pnl_ratio: float,
    trend: str,
    risk: str,
    sector: str,
    cost: float = 10.0,
) -> PositionAnalysis:
    latest = cost * (1 + pnl_ratio / 100) if cost > 0 else 8.0
    return PositionAnalysis(
        holding=Holding(code, name, 1000, cost, sector),
        latest_price=latest,
        previous_close=latest * 0.99,
        market_value=latest * 1000,
        cost_value=cost * 1000,
        daily_pnl=latest * 10,
        daily_pnl_ratio=1.0,
        pnl=(latest - cost) * 1000 if cost > 0 else 0.0,
        pnl_ratio=pnl_ratio,
        weight=weight,
        trend=trend,
        risk_level=risk,
        observations=[],
    )


def _portfolio() -> PortfolioAnalysisReport:
    positions = [
        _position(
            "600001",
            "风险股份",
            weight=0.46,
            pnl_ratio=-18,
            trend="下降趋势",
            risk="高",
            sector="机器人",
        ),
        _position(
            "600002",
            "稳健股份",
            weight=0.32,
            pnl_ratio=8,
            trend="上升趋势",
            risk="中",
            sector="机器人",
        ),
        _position(
            "600003",
            "缺成本股份",
            weight=0.22,
            pnl_ratio=0,
            trend="震荡趋势",
            risk="中",
            sector="半导体",
            cost=0,
        ),
    ]
    return PortfolioAnalysisReport(
        trade_date="2026-07-13",
        total_market_value=sum(item.market_value for item in positions),
        total_cost=sum(item.cost_value for item in positions),
        total_pnl=sum(item.pnl for item in positions),
        total_pnl_ratio=-6.5,
        daily_pnl=320.0,
        health_score=38,
        cash_position_note="现金未录入",
        top_position_weight=0.46,
        sector_weights=[("机器人", 0.78), ("半导体", 0.22)],
        positions=positions,
        risk_alerts=["单票集中度偏高"],
        market_alignment=[],
        action_checklist=[],
    )


def _advice() -> PortfolioAdvice:
    return PortfolioAdvice(
        holdings_path="data/portfolio/holdings.csv",
        transactions_path="data/portfolio/transactions.csv",
        holdings_template="code,name,shares,cost_price,sector,note",
        overall_action="先降集中度，再谈进攻",
        target_cash="30%-50%",
        position_overview=[],
        portfolio_actions=[],
        position_advices=[
            PositionAdvice(
                "600001",
                "风险股份",
                "降仓",
                0.46,
                "0%-10%",
                -12000,
                7.5,
                9.5,
                "下降趋势且风险高",
                "跌破 7.50 继续降低风险",
            ),
            PositionAdvice(
                "600002",
                "稳健股份",
                "持有",
                0.32,
                "27%-35%",
                0,
                9.8,
                12.0,
                "趋势向上但行业集中",
                "行业扩散转弱时复核",
            ),
            PositionAdvice(
                "600003",
                "缺成本股份",
                "持有观察",
                0.22,
                "19%-25%",
                0,
                7.2,
                9.0,
                "成本缺失，证据不完整",
                "补录成本后复核",
            ),
        ],
        add_holding_steps=[],
    )


def test_portfolio_queue_prioritizes_risk_before_hold() -> None:
    dossier = build_portfolio_dossier(
        _portfolio(),
        _advice(),
        market=assess_market_regime(_market()),
        quote_status=EvidenceStatus.COMPLETE,
    )

    assert dossier.verdict.state == "风险收缩"
    assert dossier.queue[0].state == "必须处理"
    assert dossier.queue[0].code == "600001"
    assert dossier.queue[-1].state == "重点观察"
    assert any(item.severity == "critical" for item in dossier.exposures)
    missing_cost = next(item for item in dossier.queue if item.code == "600003")
    assert missing_cost.cost_context == "成本待补录"


def test_stale_quote_suppresses_numeric_portfolio_actions() -> None:
    dossier = build_portfolio_dossier(
        _portfolio(),
        _advice(),
        market=assess_market_regime(_market(), quote_status=EvidenceStatus.STALE),
        quote_status=EvidenceStatus.STALE,
    )

    assert dossier.verdict.state == "数据暂停"
    assert dossier.verdict.confidence == 0
    assert all(item.state == "待补数据" for item in dossier.queue)
    assert all(item.trigger == "待刷新" for item in dossier.queue)
    assert all(
        "现价待刷新" in item.cost_context or item.cost_context == "成本待补录"
        for item in dossier.queue
    )
    assert all("行情时效未通过" in item.reason for item in dossier.queue)
    assert [item.label for item in dossier.metrics] == [
        "账本成本",
        "持仓数量",
        "第一大仓位（历史）",
        "最高行业暴露（历史）",
        "行情状态",
    ]
    assert all("盈亏" not in item.label and "市值" not in item.label for item in dossier.metrics)
    assert all(item.target_range == "待刷新" for item in dossier.boundaries)
    assert all(item.invalidation == "待刷新" for item in dossier.boundaries)


def test_market_zero_risk_budget_cannot_be_relaxed_by_portfolio_advice() -> None:
    dossier = build_portfolio_dossier(
        _portfolio(),
        _advice(),
        market=assess_market_regime(_market(), quote_status=EvidenceStatus.BLOCKED),
        quote_status=EvidenceStatus.COMPLETE,
    )

    assert dossier.verdict.state == "数据暂停"
    assert dossier.verdict.risk_budget == "0%"
    assert "价格动作待刷新" in dossier.verdict.action
