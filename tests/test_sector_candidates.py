import os
import sys
from pathlib import Path
from subprocess import run

from stock_ts.analysis import analyze_candidates, analyze_market, analyze_sectors
from stock_ts.providers.sample import SampleDataProvider
from stock_ts.report import (
    render_candidate_pool_markdown,
    render_daily_markdown,
    render_sector_markdown,
)
from stock_ts.web import render_page


def cli_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    return env


def test_sector_analysis_reports_heat_rotation_and_risks() -> None:
    provider = SampleDataProvider()
    report = analyze_sectors(provider.fetch_sectors())

    assert report.trade_date == "2026-06-05"
    assert len(report.sectors) >= 8
    assert report.sectors[0].heat_score >= report.sectors[-1].heat_score
    assert report.market_mainline
    assert any("持续性" in item for item in report.rotation_notes)
    assert any("风险" in item or "分歧" in item for item in report.risk_notes)

    markdown = render_sector_markdown(report)
    assert "# 每日板块情况" in markdown
    assert "## 板块热度榜" in markdown
    assert "## 轮动与持续性" in markdown


def test_candidate_analysis_returns_top20_with_reasons_risks_and_watch_conditions() -> None:
    provider = SampleDataProvider()
    market = analyze_market(provider.fetch_market())
    sectors = analyze_sectors(provider.fetch_sectors())
    report = analyze_candidates(
        provider.fetch_candidate_universe(),
        sectors,
        market,
        limit=20,
    )

    assert len(report.candidates) == 20
    assert report.candidates[0].score >= report.candidates[-1].score
    assert all(candidate.reasons for candidate in report.candidates)
    assert all(candidate.risks for candidate in report.candidates)
    assert all(candidate.watch_conditions for candidate in report.candidates)
    markdown = render_candidate_pool_markdown(report)
    assert "不构成投资建议" in markdown
    assert "候选股票池 Top 20" in markdown
    assert "## 排序方法" not in markdown
    assert "## 观察重点" in markdown


def test_daily_report_includes_sectors_and_candidates() -> None:
    provider = SampleDataProvider()
    market = analyze_market(provider.fetch_market())
    sectors = analyze_sectors(provider.fetch_sectors())
    candidates = analyze_candidates(provider.fetch_candidate_universe(), sectors, market, limit=20)

    markdown = render_daily_markdown(market, sectors=sectors, candidates=candidates)

    assert "## 每日板块情况" in markdown
    assert "## 候选股票池 Top 20" in markdown
    assert "不构成投资建议" in markdown


def test_cli_outputs_sectors_and_candidates(tmp_path: Path) -> None:
    sector_output = tmp_path / "sectors.md"
    candidate_output = tmp_path / "candidates.md"

    sectors = run(
        [
            sys.executable,
            "-m",
            "stock_ts.cli",
            "sectors",
            "--provider",
            "sample",
            "--output",
            str(sector_output),
        ],
        capture_output=True,
        text=True,
        check=False,
        env=cli_env(),
    )
    candidates = run(
        [
            sys.executable,
            "-m",
            "stock_ts.cli",
            "candidates",
            "--provider",
            "sample",
            "--limit",
            "20",
            "--output",
            str(candidate_output),
        ],
        capture_output=True,
        text=True,
        check=False,
        env=cli_env(),
    )

    assert sectors.returncode == 0
    assert candidates.returncode == 0
    assert "每日板块情况" in sector_output.read_text(encoding="utf-8")
    candidate_text = candidate_output.read_text(encoding="utf-8")
    assert "候选股票池 Top 20" in candidate_text
    assert candidate_text.count("观察条件") >= 20


def test_web_page_contains_sector_and_candidate_sections() -> None:
    html = render_page(stock_code="600519", holdings_path="data/portfolio/holdings.csv")

    assert "主线板块" in html
    assert "主题强弱榜" in html
    assert "强势个股" in html
    assert "轮动路径" not in html
