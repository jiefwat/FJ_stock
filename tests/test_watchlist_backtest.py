import os
import sys
from pathlib import Path
from subprocess import run

from stock_ts.backtest import backtest_moving_average, render_backtest_markdown
from stock_ts.imports import load_price_bars_csv
from stock_ts.providers.sample import SampleDataProvider
from stock_ts.watchlist import build_watchlist_report, load_watchlist, render_watchlist_markdown


def cli_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    return env


def write_watchlist(path: Path) -> None:
    path.write_text(
        "stocks:\n"
        "  - code: 600519\n"
        "    name: 贵州茅台\n"
        "    sector: 白酒\n"
        "    tags: 核心资产,消费\n"
        "    thesis: 测试消费龙头观察逻辑\n"
        "    alert_price_below: 1500\n"
        "    alert_score_below: 60\n"
        "  - code: 300750\n"
        "    name: 宁德时代\n"
        "    sector: 新能源车\n"
        "    tags: 成长,新能源\n"
        "    thesis: 测试高景气方向观察逻辑\n",
        encoding="utf-8",
    )


def test_watchlist_loader_supports_yaml_like_research_fields(tmp_path: Path) -> None:
    path = tmp_path / "watchlist.yaml"
    write_watchlist(path)

    watchlist = load_watchlist(path)

    assert [item.code for item in watchlist.stocks] == ["600519", "300750"]
    assert watchlist.stocks[0].tags == ["核心资产", "消费"]
    assert watchlist.stocks[0].thesis == "测试消费龙头观察逻辑"
    assert watchlist.stocks[0].alert_price_below == 1500


def test_watchlist_report_combines_deep_ranking_and_alerts(tmp_path: Path) -> None:
    path = tmp_path / "watchlist.yaml"
    write_watchlist(path)

    report = build_watchlist_report(SampleDataProvider(), path)
    markdown = render_watchlist_markdown(report)

    assert "自选股研究工作台" in markdown
    assert "批量深度排序" in markdown
    assert "提醒检查" in markdown
    assert "贵州茅台" in markdown
    assert "宁德时代" in markdown
    assert "测试消费龙头观察逻辑" in markdown
    assert "不构成投资建议" in markdown


def test_moving_average_backtest_returns_metrics_and_trades(tmp_path: Path) -> None:
    path = tmp_path / "prices.csv"
    path.write_text(
        "date,open,high,low,close,volume\n"
        "2026-05-01,10,10.2,9.8,10,1000\n"
        "2026-05-02,10,10.7,9.9,10.5,1100\n"
        "2026-05-03,10.5,11.2,10.4,11,1300\n"
        "2026-05-04,11,11.5,10.8,11.3,1400\n"
        "2026-05-05,11.3,11.6,10.9,11.1,1500\n"
        "2026-05-06,11.1,11.2,10.4,10.6,1800\n"
        "2026-05-07,10.6,10.8,10.0,10.2,1900\n"
        "2026-05-08,10.2,10.5,9.7,9.9,2100\n",
        encoding="utf-8",
    )

    report = backtest_moving_average(
        "688001",
        "示例科技",
        load_price_bars_csv(path),
        fast_window=2,
        slow_window=3,
        initial_cash=100000,
    )
    markdown = render_backtest_markdown(report)

    assert report.code == "688001"
    assert report.total_return_pct != 0
    assert report.max_drawdown_pct <= 0
    assert report.trades
    assert "轻量均线回测" in markdown
    assert "最大回撤" in markdown
    assert "不构成投资建议" in markdown


def test_cli_watchlist_and_backtest_write_reports(tmp_path: Path) -> None:
    watchlist_path = tmp_path / "watchlist.yaml"
    write_watchlist(watchlist_path)
    watchlist_output = tmp_path / "watchlist.md"
    backtest_output = tmp_path / "backtest.md"

    watchlist = run(
        [
            sys.executable,
            "-m",
            "stock_ts.cli",
            "watchlist",
            str(watchlist_path),
            "--provider",
            "sample",
            "--output",
            str(watchlist_output),
        ],
        capture_output=True,
        text=True,
        check=False,
        env=cli_env(),
    )
    backtest = run(
        [
            sys.executable,
            "-m",
            "stock_ts.cli",
            "backtest",
            "data/imports/sample_prices.csv",
            "--code",
            "688001",
            "--name",
            "示例科技",
            "--fast",
            "2",
            "--slow",
            "4",
            "--output",
            str(backtest_output),
        ],
        capture_output=True,
        text=True,
        check=False,
        env=cli_env(),
    )

    assert watchlist.returncode == 0
    assert backtest.returncode == 0
    assert "自选股研究工作台" in watchlist_output.read_text(encoding="utf-8")
    assert "轻量均线回测" in backtest_output.read_text(encoding="utf-8")
