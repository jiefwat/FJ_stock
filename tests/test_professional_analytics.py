from stock_ts.analysis import analyze_stock
from stock_ts.models import (
    CandidateStockRawData,
    DailyBar,
    IndexQuote,
    MarketSnapshot,
    NewsItem,
    SectorAnalysis,
    SectorAnalysisReport,
    StockRawData,
)
from stock_ts.professional_analytics import (
    build_market_pulse,
    build_stock_evidence_matrix,
)


def _candidate(code: str, name: str, sector: str, previous: float, latest: float):
    return CandidateStockRawData(
        code=code,
        name=name,
        sector=sector,
        bars=[
            DailyBar("2026-07-14", previous, previous, previous, previous, 1000),
            DailyBar("2026-07-15", latest, latest, latest, latest, 1800),
        ],
    )


def _market(**overrides) -> MarketSnapshot:
    values = {
        "trade_date": "2026-07-15",
        "heat_score": 68,
        "breadth_ratio": 1.5,
        "summary": "市场结构偏强",
        "regime": "震荡轮动",
        "indices": [IndexQuote("000001", "上证指数", 3500, 0.8, 5000)],
        "top_sectors": [("机器人", 2.8)],
        "dimensions": [],
        "opportunities": [],
        "risks": [],
        "tomorrow_watch": [],
        "limit_up_count": 50,
        "limit_down_count": 12,
        "advancing_count": 3000,
        "declining_count": 2000,
        "unchanged_count": 0,
    }
    values.update(overrides)
    return MarketSnapshot(**values)


def _sectors(*items: SectorAnalysis) -> SectorAnalysisReport:
    return SectorAnalysisReport(
        trade_date="2026-07-15",
        sectors=list(items),
        market_mainline=[item.name for item in items[:3]],
        rotation_notes=[],
        risk_notes=[],
    )


def test_market_pulse_calculates_participation_extremes_and_regime() -> None:
    sectors = _sectors(
        SectorAnalysis(
            name="机器人",
            pct_chg=2.8,
            heat_score=76,
            advancing_ratio=0.72,
            amount_change=18.0,
            limit_up_count=5,
            continuity="连续走强",
            fund_status="资金活跃",
            rotation_status="主线",
            risk="高位分化",
        )
    )
    candidates = [
        _candidate("300001", "机器人甲", "机器人", 10, 10.4),
        _candidate("300002", "机器人乙", "机器人", 20, 21.0),
        _candidate("300003", "算力甲", "算力", 10, 10.7),
        _candidate("600001", "白酒甲", "白酒", 10, 9.3),
    ]

    pulse = build_market_pulse(_market(), sectors, candidates)

    assert pulse.advance_ratio == 0.60
    assert pulse.breadth_ratio == 1.5
    assert pulse.limit_balance == 26
    assert pulse.extreme_up_count == 3
    assert pulse.extreme_down_count == 1
    assert pulse.confirmed_theme_count == 1
    assert pulse.coverage == 100
    assert pulse.regime == "constructive"
    assert pulse.risk_budget == "50%-70%"
    assert {metric.key for metric in pulse.metrics} >= {
        "participation",
        "breadth",
        "limit_balance",
        "extreme_spread",
        "theme_participation",
        "coverage",
    }


def test_market_pulse_zero_data_enters_hard_risk_off_gate() -> None:
    pulse = build_market_pulse(
        _market(
            indices=[],
            heat_score=0,
            breadth_ratio=0,
            limit_up_count=0,
            limit_down_count=0,
            advancing_count=0,
            declining_count=0,
            unchanged_count=0,
        ),
        _sectors(),
        [],
    )

    assert pulse.advance_ratio == 0
    assert pulse.breadth_ratio == 0
    assert pulse.coverage == 0
    assert pulse.regime == "risk_off"
    assert pulse.risk_budget == "0%"
    assert pulse.hard_gate_reasons


def _stock_raw(*, negative_event: bool = False) -> StockRawData:
    bars = [
        DailyBar(
            date=f"2026-06-{day:02d}",
            open=10 + day * 0.08,
            high=10.5 + day * 0.1,
            low=9.8 + day * 0.06,
            close=10 + day * 0.12,
            volume=1000 + day * 100,
        )
        for day in range(1, 25)
    ]
    title = "公司收到监管立案调查通知" if negative_event else "公司订单稳步增长"
    sentiment = "negative" if negative_event else "positive"
    return StockRawData(
        code="603278",
        name="大业股份",
        bars=bars,
        fund_flow=1.8,
        pe_ttm=22.0,
        valuation={"pb": 2.1},
        fundamental_metrics={
            "roe": 12.4,
            "revenue_yoy": 18.0,
            "net_profit_yoy": 25.0,
        },
        fund_flow_detail={"main_net_inflow": 1.8},
        news_items=[NewsItem("2026-07-15", "公开信息", title, title, sentiment=sentiment)],
        announcements=[{"date": "2026-07-15", "title": title}],
        data_sources=["local_snapshot"],
    )


def test_stock_evidence_matrix_separates_support_counter_and_conditions() -> None:
    raw = _stock_raw()
    report = analyze_stock(raw)

    matrix = build_stock_evidence_matrix(raw, report)

    assert len(matrix.dimensions) == 8
    assert matrix.decision_label == report.decision.verdict
    assert matrix.action == report.decision.today_action
    assert matrix.strengthen_condition == report.decision.strengthen_condition
    assert matrix.invalidation_condition == report.decision.exit_condition
    assert all(item.supporting_evidence for item in matrix.dimensions)
    assert all(item.counter_evidence for item in matrix.dimensions)
    assert all(
        item.confidence in {"high", "medium", "low", "blocked"}
        for item in matrix.dimensions
    )
    assert all(
        item.coverage in {"ready", "partial", "stale", "missing"}
        for item in matrix.dimensions
    )


def test_stock_material_negative_event_blocks_aggressive_decision() -> None:
    raw = _stock_raw(negative_event=True)
    report = analyze_stock(raw)

    matrix = build_stock_evidence_matrix(raw, report)

    assert matrix.decision_label != "谨慎进攻"
    assert matrix.confidence == "blocked"
    assert any("重大负面事件" in reason for reason in matrix.hard_gate_reasons)
    event = next(item for item in matrix.dimensions if item.name == "消息事件")
    assert event.confidence == "blocked"
    assert any("立案" in evidence for evidence in event.counter_evidence)
