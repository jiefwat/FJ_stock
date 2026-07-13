from stock_ts.models import (
    DailyBar,
    FundamentalPeriod,
    Holding,
    StockRawData,
    ValuationPoint,
)
from stock_ts.research.evidence import EvidenceStatus, ResearchInputQuality
from stock_ts.research.stock_memo import build_stock_research_memo


def _raw_stock(**changes) -> StockRawData:
    values = dict(
        code="600000",
        name="示例银行",
        bars=[
            DailyBar("2026-07-10", 10, 10.2, 9.8, 10, 900),
            DailyBar("2026-07-11", 10, 10.5, 9.9, 10.2, 1200),
        ],
        pe_ttm=6.5,
        valuation={"pb": 0.7, "source": "tushare", "date": "2026-07-11"},
        fundamental_metrics={},
        announcements=[],
        data_sources=["tdx", "tushare"],
    )
    values.update(changes)
    return StockRawData(**values)


def _fundamental_history(values: list[tuple[float, float]]) -> list[FundamentalPeriod]:
    dates = ["2025-09-30", "2025-12-31", "2026-03-31"][-len(values) :]
    chronological = [
        FundamentalPeriod(
            date=period_date,
            source="fixture",
            revenue_yoy=revenue,
            net_profit_yoy=profit,
            roe=12 + index,
            gross_margin=30 + index,
            debt_to_assets=45 - index,
            ocf_to_profit=1 + index / 10,
        )
        for index, (period_date, (revenue, profit)) in enumerate(zip(dates, values))
    ]
    return list(reversed(chronological))


def _valuation_history(count: int) -> list[ValuationPoint]:
    return [
        ValuationPoint(
            date=f"2026-06-{index + 1:02d}",
            source="fixture",
            pe_ttm=10 + index,
            pb=2.0,
            ps=3.0,
        )
        for index in range(count)
    ]


def test_memo_does_not_call_absolute_multiples_undervalued() -> None:
    memo = build_stock_research_memo(_raw_stock())

    assert memo.verdict.status == "技术性观察"
    assert "低估" not in memo.valuation.conclusion
    assert "缺少历史分位或行业对比" in memo.valuation.limitations


def test_memo_uses_complete_financial_quality_fields() -> None:
    memo = build_stock_research_memo(
        _raw_stock(
            fundamental_metrics={
                "date": "2026-03-31",
                "revenue_yoy": 18.0,
                "net_profit_yoy": 24.0,
                "roe": 16.0,
                "gross_margin": 32.0,
                "debt_to_assets": 42.0,
                "ocf_to_profit": 1.2,
                "source": "tushare.fina_indicator",
            },
            announcements=[{"date": "2026-07-10", "title": "季度经营公告"}],
            valuation={
                "pb": 0.7,
                "pe_percentile": 25,
                "source": "tushare",
                "date": "2026-07-11",
            },
        )
    )

    assert "盈利增速高于收入增速" in memo.quality.conclusion
    assert any(item.block == "经营质量" for item in memo.evidence)
    assert memo.verdict.status != "技术性观察"


def test_single_financial_period_does_not_claim_trend_improvement() -> None:
    memo = build_stock_research_memo(
        _raw_stock(
            fundamental_metrics={
                "date": "2026-03-31",
                "revenue_yoy": 18.0,
                "net_profit_yoy": 24.0,
                "source": "tushare.fina_indicator",
            }
        )
    )

    assert "趋势改善" not in memo.quality.conclusion
    assert "单期数据" in memo.quality.limitations


def test_title_only_announcement_scan_keeps_manual_review_warning() -> None:
    memo = build_stock_research_memo(
        _raw_stock(announcements=[{"date": "2026-07-10", "title": "关于股东减持的公告"}])
    )

    assert "未代替原文复核" in memo.events.limitations


def test_no_holding_never_invents_cost_advantage_or_reduce_action() -> None:
    memo = build_stock_research_memo(_raw_stock(), holding=None)
    holding_memo = build_stock_research_memo(
        _raw_stock(),
        holding=Holding("600000", "示例银行", 100, 11.0, "银行"),
    )

    assert "未持仓" in memo.portfolio.conclusion
    assert "成本优势" not in memo.portfolio.conclusion
    assert "减仓" not in memo.portfolio.conclusion
    assert "成本 11.00" in holding_memo.portfolio.conclusion


def test_memo_has_three_scenarios_and_auditable_missing_blocks() -> None:
    memo = build_stock_research_memo(_raw_stock())

    assert [item.name for item in memo.scenarios] == ["乐观", "基准", "悲观"]
    assert all(item.premises and item.signals and item.invalidation for item in memo.scenarios)
    valuation = next(item for item in memo.evidence if item.block == "估值")
    fundamentals = next(item for item in memo.evidence if item.block == "经营质量")
    assert valuation.status == EvidenceStatus.DEGRADED
    assert fundamentals.status == EvidenceStatus.MISSING


def test_stale_quote_pauses_stock_research() -> None:
    memo = build_stock_research_memo(
        _raw_stock(),
        input_quality=ResearchInputQuality(
            quote_status=EvidenceStatus.STALE,
            blockers=("个股 K 线仍停留在旧交易日",),
        ),
    )

    assert memo.verdict.status == "数据暂停"
    assert memo.verdict.confidence == 0
    assert "旧交易日" in memo.verdict.strongest_counter_evidence
    assert all("暂停" in scenario.action for scenario in memo.scenarios)


def test_metadata_only_fundamentals_and_blank_events_do_not_improve_verdict() -> None:
    memo = build_stock_research_memo(
        _raw_stock(
            fundamental_metrics={"source": "tushare", "date": "2026-03-31"},
            valuation={"pe_percentile": 20},
            announcements=[{"title": "  "}],
        )
    )

    assert memo.verdict.status == "技术性观察"
    quality = next(item for item in memo.evidence if item.block == "经营质量")
    events = next(item for item in memo.evidence if item.block == "新闻公告")
    assert quality.status == EvidenceStatus.MISSING
    assert events.status == EvidenceStatus.MISSING


def test_invalid_valuation_reference_does_not_count_as_comparable() -> None:
    memo = build_stock_research_memo(
        _raw_stock(
            fundamental_metrics={"revenue_yoy": 12.0},
            valuation={"pe_percentile": 120},
            announcements=[],
        )
    )

    assert memo.verdict.status == "技术性观察"
    assert "历史分位 120" not in memo.valuation.conclusion


def test_valid_complete_inputs_remain_conditional_research() -> None:
    memo = build_stock_research_memo(
        _raw_stock(
            fundamental_metrics={
                "revenue_yoy": 18.0,
                "net_profit_yoy": 24.0,
                "roe": 16.0,
                "gross_margin": 32.0,
                "debt_to_assets": 42.0,
                "ocf_to_profit": 1.2,
                "source": "tushare.fina_indicator",
                "date": "2026-03-31",
            },
            valuation={"pe_percentile": 25, "source": "tushare"},
            announcements=[{"title": "季度经营公告"}],
        )
    )

    assert memo.verdict.status == "条件研究"
    assert memo.verdict.confidence > 0


def test_one_financial_period_never_claims_trend() -> None:
    history = _fundamental_history([(12, 18)])
    memo = build_stock_research_memo(
        _raw_stock(
            fundamental_metrics={},
            fundamental_history=history,
        )
    )

    assert "连续改善" not in memo.quality.conclusion
    assert "财务 1 期" in memo.quality.limitations


def test_three_improving_periods_support_improvement_statement() -> None:
    history = _fundamental_history([(8, 9), (12, 14), (18, 24)])
    memo = build_stock_research_memo(
        _raw_stock(
            fundamental_metrics={},
            fundamental_history=history,
        )
    )

    assert "连续改善" in memo.quality.conclusion
    quality_evidence = next(item for item in memo.evidence if item.block == "经营质量")
    assert "财务 3 期" in quality_evidence.detail


def test_revenue_profit_divergence_is_not_overall_improvement() -> None:
    history = _fundamental_history([(18, 8), (14, 12), (10, 20)])
    memo = build_stock_research_memo(
        _raw_stock(
            fundamental_metrics={},
            fundamental_history=history,
        )
    )

    assert "分化" in memo.quality.conclusion
    assert "连续改善" not in memo.quality.conclusion


def test_nineteen_pe_points_do_not_create_history_percentile() -> None:
    memo = build_stock_research_memo(
        _raw_stock(
            pe_ttm=18,
            valuation={"pe_ttm": 18},
            valuation_history=_valuation_history(19),
        )
    )

    assert "估值历史积累中 19/20" in memo.valuation.limitations
    assert "历史分位" not in memo.valuation.conclusion


def test_twenty_pe_points_create_descriptive_history_percentile() -> None:
    memo = build_stock_research_memo(
        _raw_stock(
            pe_ttm=18,
            valuation={"pe_ttm": 18},
            valuation_history=_valuation_history(20),
        )
    )

    assert "基于 20 个观察点" in memo.valuation.conclusion
    assert "低估" not in memo.valuation.conclusion
    assert "高估" not in memo.valuation.conclusion


def test_duplicate_valuation_dates_do_not_inflate_sample_count() -> None:
    duplicate_points = [
        ValuationPoint("2026-06-01", "fixture", 10 + index, 2, 3)
        for index in range(20)
    ]
    memo = build_stock_research_memo(
        _raw_stock(
            pe_ttm=18,
            valuation={"pe_ttm": 18},
            valuation_history=duplicate_points,
        )
    )

    assert "估值历史积累中 1/20" in memo.valuation.limitations
    assert "历史分位" not in memo.valuation.conclusion


def test_stale_quote_still_overrides_complete_history() -> None:
    memo = build_stock_research_memo(
        _raw_stock(
            fundamental_metrics={},
            fundamental_history=_fundamental_history([(8, 9), (12, 14), (18, 24)]),
            valuation={"pe_ttm": 18},
            valuation_history=_valuation_history(20),
        ),
        input_quality=ResearchInputQuality(
            quote_status=EvidenceStatus.STALE,
            fundamental_coverage=1.0,
            valuation_comparable=True,
            event_status=EvidenceStatus.COMPLETE,
        ),
    )

    assert memo.verdict.status == "数据暂停"
    assert memo.verdict.confidence == 0
