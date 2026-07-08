from pathlib import Path

from stock_ts.deep_analysis import (
    AnalysisAngle,
    BatchAnalysisReport,
    DeepStockReport,
    UpsidePotential,
    render_batch_markdown,
    render_deep_stock_markdown,
)
from stock_ts.deep_models import DailyDeepReport
from stock_ts.deep_report import render_batch_markdown as render_batch_markdown_new
from stock_ts.deep_report import render_daily_deep_markdown
from stock_ts.deep_report import render_deep_stock_markdown as render_deep_stock_markdown_new
from stock_ts.output import write_optional_text
from stock_ts.providers.sample import SampleDataProvider
from stock_ts.workflows import (
    build_batch_report,
    build_candidate_report,
    build_deep_stock_report,
    build_market_report,
    build_sector_report,
)


def test_deep_analysis_keeps_backward_compatible_public_render_imports() -> None:
    provider = SampleDataProvider()
    stock = build_deep_stock_report(provider, "600519")
    batch = build_batch_report(provider, ["600519", "300750"])

    assert isinstance(stock, DeepStockReport)
    assert isinstance(batch, BatchAnalysisReport)
    assert render_deep_stock_markdown(stock) == render_deep_stock_markdown_new(stock)
    assert render_batch_markdown(batch) == render_batch_markdown_new(batch)


def test_write_optional_text_creates_parent_and_returns_path(tmp_path: Path) -> None:
    output = tmp_path / "nested" / "report.md"

    written = write_optional_text("hello", str(output))

    assert written == output
    assert output.read_text(encoding="utf-8") == "hello"


def test_write_optional_text_returns_none_without_output() -> None:
    assert write_optional_text("hello", None) is None


def test_deep_renderers_handle_empty_debate_rounds_defensively() -> None:
    provider = SampleDataProvider()
    market = build_market_report(provider)
    sectors = build_sector_report(provider, market=market)
    candidates = build_candidate_report(provider, market=market, sectors=sectors, limit=2)
    stock = DeepStockReport(
        code="600519",
        name="贵州茅台",
        trade_date=market.trade_date,
        latest_close=1586,
        trend="震荡整理",
        risk_level="中",
        angles=[AnalysisAngle("价格趋势", 60, "中性", "测试")],
        upside=UpsidePotential(
            score=60,
            label="中性观察",
            base_case="保持观察",
            bull_case="放量转强",
            bear_case="跌破均线",
            drivers=["测试"],
            invalid_conditions=["跌破 5 日均线"],
        ),
        debate_rounds=[],
        final_conclusion="保持观察",
        action_plan=["复盘"],
        risks=["测试风险"],
        invalid_conditions=["跌破 5 日均线"],
    )

    stock_markdown = render_deep_stock_markdown(stock)
    daily_markdown = render_daily_deep_markdown(
        DailyDeepReport(
            trade_date=market.trade_date,
            market=market,
            sectors=sectors,
            candidates=candidates,
            stocks=[stock],
            portfolio=None,
            news=None,
            markdown="原始日报",
        )
    )

    assert "裁判结论" in stock_markdown
    assert "多轮对抗摘要" in daily_markdown
    assert "保持观察" in daily_markdown
