import os
import sys
from pathlib import Path
from subprocess import run
from threading import Barrier

from stock_ts.analysis import analyze_market, analyze_portfolio
from stock_ts.models import DailyBar, Holding, StockRawData
from stock_ts.portfolio import load_holdings_csv
from stock_ts.providers.sample import SampleDataProvider
from stock_ts.report import render_daily_markdown, render_portfolio_markdown
from stock_ts.web import render_page


def cli_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    return env


def test_market_analysis_exposes_multiple_dimensions() -> None:
    market = analyze_market(SampleDataProvider().fetch_market())

    dimension_names = {item.name for item in market.dimensions}

    assert {"指数趋势", "市场广度", "短线情绪", "资金流", "板块强度", "风险状态"} <= dimension_names
    assert market.regime in {"强势进攻", "震荡轮动", "防守退潮"}
    assert len(market.tomorrow_watch) >= 3


def test_load_holdings_csv_and_portfolio_analysis(tmp_path: Path) -> None:
    holdings_file = tmp_path / "holdings.csv"
    holdings_file.write_text(
        "code,name,shares,cost_price,sector,note\n"
        "600519,贵州茅台,100,1500,白酒,核心观察\n"
        "000001,平安银行,2000,10.5,银行,低估值观察\n",
        encoding="utf-8",
    )

    holdings = load_holdings_csv(holdings_file)
    report = analyze_portfolio(
        holdings, SampleDataProvider(), analyze_market(SampleDataProvider().fetch_market())
    )

    assert holdings[0] == Holding(
        code="600519",
        name="贵州茅台",
        shares=100,
        cost_price=1500.0,
        sector="白酒",
        note="核心观察",
    )
    assert report.total_market_value > 0
    assert report.total_pnl != 0
    assert 0 <= report.health_score <= 100
    assert report.positions[0].weight > 0
    assert report.risk_alerts
    assert "组合健康度" in render_portfolio_markdown(report)


def test_portfolio_analysis_flags_concentration_and_market_fit() -> None:
    provider = SampleDataProvider()
    holdings = [
        Holding(code="600519", name="贵州茅台", shares=500, cost_price=1500, sector="白酒"),
        Holding(code="000001", name="平安银行", shares=100, cost_price=10.5, sector="银行"),
    ]

    report = analyze_portfolio(holdings, provider, analyze_market(provider.fetch_market()))

    assert report.top_position_weight > 0.7
    assert any("单票仓位" in item for item in report.risk_alerts)
    assert any("市场主线" in item for item in report.market_alignment)


def test_portfolio_analysis_uses_previous_close_for_daily_pnl() -> None:
    class FixedPriceProvider(SampleDataProvider):
        def fetch_stock(self, code: str) -> StockRawData:
            return StockRawData(
                code=code,
                name="测试股票",
                bars=[
                    DailyBar(
                        date="2026-06-19",
                        open=9.8,
                        high=10.2,
                        low=9.7,
                        close=10.0,
                        volume=1000,
                    ),
                    DailyBar(
                        date="2026-06-20",
                        open=10.1,
                        high=11.2,
                        low=10.0,
                        close=11.0,
                        volume=1200,
                    ),
                ],
            )

    provider = FixedPriceProvider()
    report = analyze_portfolio(
        [Holding(code="000001", name="测试股票", shares=200, cost_price=8, sector="测试")],
        provider,
        analyze_market(provider.fetch_market()),
    )

    position = report.positions[0]
    assert position.latest_price == 11.0
    assert position.previous_close == 10.0
    assert position.daily_pnl == 200.0
    assert position.daily_pnl_ratio == 10.0
    assert report.daily_pnl == 200.0


def test_portfolio_analysis_fetches_holdings_concurrently() -> None:
    class BarrierProvider(SampleDataProvider):
        def __init__(self) -> None:
            self.barrier = Barrier(3, timeout=0.3)

        def fetch_stock(self, code: str) -> StockRawData:
            self.barrier.wait()
            return StockRawData(
                code=code,
                name=code,
                bars=[
                    DailyBar(
                        date="2026-06-13",
                        open=10.0,
                        high=10.5,
                        low=9.8,
                        close=10.2,
                        volume=1000,
                    )
                ],
            )

    provider = BarrierProvider()
    holdings = [
        Holding(code="600519", name="贵州茅台", shares=100, cost_price=1500, sector="白酒"),
        Holding(code="000001", name="平安银行", shares=100, cost_price=10.5, sector="银行"),
        Holding(code="300750", name="宁德时代", shares=100, cost_price=180, sector="电池"),
    ]

    report = analyze_portfolio(
        holdings,
        provider,
        analyze_market(SampleDataProvider().fetch_market()),
    )

    assert len(report.positions) == 3


def test_daily_markdown_combines_market_and_portfolio() -> None:
    provider = SampleDataProvider()
    market = analyze_market(provider.fetch_market())
    portfolio = analyze_portfolio(
        [Holding(code="600519", name="贵州茅台", shares=100, cost_price=1500, sector="白酒")],
        provider,
        market,
    )

    markdown = render_daily_markdown(market, portfolio)

    assert "# StockTS 每日复盘" in markdown
    assert "## 每日大盘分析" in markdown
    assert "## 每日持仓分析" in markdown
    assert "不构成投资建议" in markdown


def test_cli_generates_portfolio_and_daily_reports(tmp_path: Path) -> None:
    holdings_file = tmp_path / "holdings.csv"
    daily_output = tmp_path / "daily.md"
    holdings_file.write_text(
        "code,name,shares,cost_price,sector,note\n600519,贵州茅台,100,1500,白酒,核心观察\n",
        encoding="utf-8",
    )

    portfolio = run(
        [
            sys.executable,
            "-m",
            "stock_ts.cli",
            "portfolio",
            "--provider",
            "sample",
            "--holdings",
            str(holdings_file),
        ],
        capture_output=True,
        text=True,
        check=False,
        env=cli_env(),
    )
    daily = run(
        [
            sys.executable,
            "-m",
            "stock_ts.cli",
            "daily",
            "--provider",
            "sample",
            "--holdings",
            str(holdings_file),
            "--output",
            str(daily_output),
        ],
        capture_output=True,
        text=True,
        check=False,
        env=cli_env(),
    )

    assert portfolio.returncode == 0
    assert "# 每日持仓分析" in portfolio.stdout
    assert daily.returncode == 0
    assert daily_output.exists()
    assert "# StockTS 每日复盘" in daily_output.read_text(encoding="utf-8")


def test_web_page_contains_market_portfolio_stock_and_report_sections() -> None:
    html = render_page(stock_code="600519", holdings_path="data/portfolio/holdings.csv")

    assert "每日大盘" in html
    assert "我的持仓" in html
    assert "个股分析" in html
    assert "热点机会" in html
    assert "组合风控结论" in html
