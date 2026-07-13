import inspect
from dataclasses import replace

from stock_ts import web
from stock_ts.models import DailyBar, FundamentalPeriod, StockRawData, ValuationPoint
from stock_ts.research.evidence import EvidenceStatus, ResearchInputQuality
from stock_ts.research.stock_memo import build_stock_research_memo
from stock_ts.webapp.stock_workspace import render_stock_workspace


def _raw(*, complete: bool) -> StockRawData:
    return StockRawData(
        code="600000",
        name="示例银行",
        bars=[
            DailyBar("2026-07-10", 10, 10.2, 9.8, 10, 900),
            DailyBar("2026-07-11", 10, 10.5, 9.9, 10.2, 1200),
        ],
        pe_ttm=6.5,
        valuation={
            "pb": 0.7,
            **({"pe_percentile": 25} if complete else {}),
            "source": "tushare",
            "date": "2026-07-11",
        },
        fundamental_metrics=(
            {
                "date": "2026-03-31",
                "revenue_yoy": 18.0,
                "net_profit_yoy": 24.0,
                "roe": 16.0,
                "source": "tushare.fina_indicator",
            }
            if complete
            else {}
        ),
        announcements=(
            [{"date": "2026-07-10", "title": "季度经营公告"}] if complete else []
        ),
        data_sources=["tdx", "tushare"],
    )


def test_stock_workspace_leads_with_thesis_not_score() -> None:
    html = render_stock_workspace(build_stock_research_memo(_raw(complete=True)))

    assert html.index("研究结论") < html.index("六类证据")
    assert html.index("核心矛盾") < html.index("交易计划")
    assert "机会评分" not in html
    assert "乐观情景" in html
    assert "基准情景" in html
    assert "悲观情景" in html


def test_stock_workspace_shows_missing_blocks_without_false_confidence() -> None:
    html = render_stock_workspace(build_stock_research_memo(_raw(complete=False)))

    assert "技术性观察" in html
    assert "缺少历史分位或行业对比" in html
    assert "投资逻辑成立" not in html
    assert "低估" not in html
    assert "missing" in html


def test_stock_workspace_surfaces_stale_quote_pause() -> None:
    memo = build_stock_research_memo(
        _raw(complete=True),
        input_quality=ResearchInputQuality(
            quote_status=EvidenceStatus.STALE,
            blockers=("行情日期落后",),
        ),
    )

    html = render_stock_workspace(memo)

    assert 'data-research-status="数据暂停"' in html
    assert "置信度 0/100" in html
    assert "刷新最近交易日行情后重新评估" in html
    assert "等待技术触发后再分配风险预算" not in html


def test_stock_orchestration_passes_typed_input_quality() -> None:
    source = inspect.getsource(web._render_compact_stock_module)

    assert "quality.quote_status" in source
    assert "input_quality=" in source


def test_stock_workspace_renders_cross_period_financial_and_valuation_evidence() -> None:
    fundamentals = [
        FundamentalPeriod(
            date=period_date,
            source="fixture",
            revenue_yoy=revenue,
            net_profit_yoy=profit,
            roe=14 + index,
            gross_margin=30 + index,
            debt_to_assets=45 - index,
            ocf_to_profit=1 + index / 10,
        )
        for index, (period_date, revenue, profit) in enumerate(
            [
                ("2026-03-31", 18, 24),
                ("2025-12-31", 12, 14),
                ("2025-09-30", 8, 9),
            ]
        )
    ]
    valuations = [
        ValuationPoint(f"2026-06-{index + 1:02d}", "fixture", 10 + index, 2, 3)
        for index in range(20)
    ]
    raw = replace(
        _raw(complete=True),
        pe_ttm=18,
        valuation={"pe_ttm": 18},
        fundamental_metrics={},
        fundamental_history=fundamentals,
        valuation_history=valuations,
    )

    html = render_stock_workspace(build_stock_research_memo(raw))

    assert "财务 3 期" in html
    assert "基于 20 个观察点" in html
    assert "连续改善" in html
