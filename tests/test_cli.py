import os
import sys
from pathlib import Path
from subprocess import run


def cli_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    return env


def test_cli_generates_market_report_to_stdout() -> None:
    result = run(
        [sys.executable, "-m", "stock_ts.cli", "market", "--provider", "sample"],
        capture_output=True,
        text=True,
        check=False,
        env=cli_env(),
    )

    assert result.returncode == 0
    assert "# 每日大盘分析" in result.stdout
    assert "市场温度" in result.stdout


def test_cli_writes_stock_report_file(tmp_path: Path) -> None:
    output = tmp_path / "stock.md"

    result = run(
        [
            sys.executable,
            "-m",
            "stock_ts.cli",
            "stock",
            "600519",
            "--provider",
            "sample",
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
    assert "个股分析" in output.read_text(encoding="utf-8")
