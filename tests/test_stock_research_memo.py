from stock_ts.models import DailyBar, Holding, StockRawData
from stock_ts.research.evidence import EvidenceStatus
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
