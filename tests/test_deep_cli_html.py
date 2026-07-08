import os
import sys
from pathlib import Path
from subprocess import run

from stock_ts.html_report import render_deep_stock_html
from stock_ts.providers.sample import SampleDataProvider
from stock_ts.workflows import build_deep_stock_report


def cli_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    return env


def test_html_renderer_outputs_structured_single_file_report() -> None:
    report = build_deep_stock_report(SampleDataProvider(), "600519")

    html = render_deep_stock_html(report)

    assert "<html" in html
    assert "StockTS 深度分析" in html
    assert 'class="debate-card"' in html
    assert "未来上涨潜力" in html
    assert "不构成投资建议" in html
    assert "https://cdn" not in html
    assert "<script src=" not in html


def test_cli_stock_deep_writes_markdown_and_html(tmp_path: Path) -> None:
    output = tmp_path / "stock-deep.md"
    html = tmp_path / "stock-deep.html"

    result = run(
        [
            sys.executable,
            "-m",
            "stock_ts.cli",
            "stock-deep",
            "600519",
            "--provider",
            "sample",
            "--html",
            str(html),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=False,
        env=cli_env(),
    )

    assert result.returncode == 0
    assert output.exists()
    assert html.exists()
    assert "多角度深度分析" in output.read_text(encoding="utf-8")
    assert "StockTS 深度分析" in html.read_text(encoding="utf-8")


def test_cli_batch_writes_comparison_markdown_and_html(tmp_path: Path) -> None:
    output = tmp_path / "batch.md"
    html = tmp_path / "batch.html"

    result = run(
        [
            sys.executable,
            "-m",
            "stock_ts.cli",
            "batch",
            "600519,000001,300750",
            "--provider",
            "sample",
            "--html",
            str(html),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=False,
        env=cli_env(),
    )

    assert result.returncode == 0
    text = output.read_text(encoding="utf-8")
    assert "批量个股深度对比" in text
    assert "600519" in text
    assert "000001" in text
    assert "300750" in text
    assert "StockTS 批量深度分析" in html.read_text(encoding="utf-8")


def test_cli_daily_deep_includes_market_sector_portfolio_news_and_html(tmp_path: Path) -> None:
    output = tmp_path / "daily-deep.md"
    html = tmp_path / "daily-deep.html"

    result = run(
        [
            sys.executable,
            "-m",
            "stock_ts.cli",
            "daily-deep",
            "--provider",
            "sample",
            "--transactions",
            "data/portfolio/transactions.csv",
            "--news",
            "data/imports/news.csv",
            "--candidate-limit",
            "5",
            "--html",
            str(html),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=False,
        env=cli_env(),
    )

    assert result.returncode == 0
    text = output.read_text(encoding="utf-8")
    assert "StockTS 每日深度复盘" in text
    assert "每日大盘情况" in text
    assert "## 今日重点" in text
    assert "## 研究运行卡" not in text
    assert "Shadow Account" not in text
    assert "持仓：健康度" in text
    assert "板块情况" in text
    assert "持仓分析" in text
    assert "新闻舆情" in text
    assert "多轮对抗摘要" in text
    assert "技术分析师" in text
    assert "多头研究员" in text
    assert "空头研究员" in text
    assert "风控经理" in text
    assert "组合经理" in text
    assert "StockTS 每日深度复盘" in html.read_text(encoding="utf-8")


def test_daily_deep_stock_observation_uses_evidence_not_template_phrases(tmp_path: Path) -> None:
    output = tmp_path / "daily-deep.md"
    result = run(
        [
            sys.executable,
            "-m",
            "stock_ts.cli",
            "daily-deep",
            "--provider",
            "sample",
            "--transactions",
            "data/portfolio/transactions.csv",
            "--candidate-limit",
            "5",
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=False,
        env=cli_env(),
    )

    assert result.returncode == 0
    text = output.read_text(encoding="utf-8")
    assert "## 个股深度观察" in text
    assert "当前信号不足或风险约束较多" not in text
    assert "处于中性偏强观察区" not in text
    assert "不适合给出确定性判断" not in text
    assert "主要矛盾" in text
    assert "失效条件" in text
