from stock_ts.models import DailyBar, StockRawData
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
