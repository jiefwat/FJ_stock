#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from traceback import format_exception_only
from typing import Callable

from stock_ts.announcements import fetch_cninfo_announcements, render_announcement_markdown
from stock_ts.daily_decisions import write_decision_artifact

CommandRunner = Callable[[list[str], int], None]


@dataclass(frozen=True)
class DailyPipelineConfig:
    snapshot_path: str | Path = "data/imports/tdx_snapshots.json"
    holdings_path: str | Path = "data/portfolio/holdings.csv"
    output_dir: str | Path = "reports/daily"
    html_dir: str | Path = "reports/html"
    announcement_dir: str | Path = "reports/announcements"
    provider_name: str = "tdx-snapshot"
    candidate_limit: int = 300
    enrich_limit: int = 50
    kline_bar_count: int = 120
    stock_news_limit: int = 3
    market_news_limit: int = 20
    external_enrich_timeout: int = 300
    announcement_limit: int = 5
    python_executable: str = sys.executable
    skip_refresh: bool = False
    skip_tdx_enrich: bool = False
    skip_a_share_kline: bool = False
    skip_external_enrich: bool = False
    skip_announcements: bool = False


@dataclass(frozen=True)
class DailyPipelineResult:
    ok: bool
    status_path: Path


def run_daily_pipeline(
    config: DailyPipelineConfig,
    *,
    runner: CommandRunner | None = None,
) -> DailyPipelineResult:
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    status_path = output_dir / "pipeline.status"
    command_runner = runner or _run_command
    steps: dict[str, str] = {}

    try:
        if config.skip_refresh:
            steps["refresh"] = "skipped"
        else:
            command_runner(_refresh_command(config), 1200)
            steps["refresh"] = "ok"

        if config.skip_tdx_enrich:
            steps["tdx_enrich"] = "skipped"
        else:
            command_runner(_tdx_enrich_command(config), 600)
            steps["tdx_enrich"] = "ok"

        if config.skip_a_share_kline:
            steps["a_share_kline"] = "skipped"
        else:
            try:
                command_runner(_a_share_kline_command(config), 1200)
                steps["a_share_kline"] = "ok"
            except Exception as exc:
                steps["a_share_kline"] = f"failed:{_short_error(exc)}"

        codes = _pipeline_codes(config)
        if config.skip_external_enrich:
            steps["external_enrich"] = "skipped"
        elif codes:
            try:
                command_runner(_external_enrich_command(config, codes), config.external_enrich_timeout)
                steps["external_enrich"] = "ok"
            except Exception as exc:
                steps["external_enrich"] = f"failed:{_short_error(exc)}"
        else:
            steps["external_enrich"] = "skipped_no_codes"

        if config.skip_announcements:
            steps["announcements"] = "skipped"
        else:
            try:
                _write_announcements(config, codes[: max(config.announcement_limit, 0)])
                steps["announcements"] = "ok"
            except Exception as exc:
                steps["announcements"] = f"failed:{_short_error(exc)}"

        command_runner(_report_command(config), 180)
        steps["report"] = "ok"
        _write_pipeline_status(status_path, "ok", steps, codes, "")
        _write_pipeline_decisions(config, status_path)
        return DailyPipelineResult(ok=True, status_path=status_path)
    except Exception as exc:
        error = "".join(format_exception_only(type(exc), exc)).strip()
        _write_pipeline_status(status_path, "failed", steps, _safe_pipeline_codes(config), error)
        return DailyPipelineResult(ok=False, status_path=status_path)


def _refresh_command(config: DailyPipelineConfig) -> list[str]:
    return [
        config.python_executable,
        "scripts/refresh_tdx_snapshot.py",
        "--python",
        config.python_executable,
        "--output",
        str(config.snapshot_path),
        "--candidate-limit",
        str(config.candidate_limit),
        "--quote-only",
        "--timeout",
        "90",
    ]


def _tdx_enrich_command(config: DailyPipelineConfig) -> list[str]:
    return [
        config.python_executable,
        "scripts/refresh_tdx_snapshot.py",
        "--python",
        config.python_executable,
        "--output",
        str(config.snapshot_path),
        "--enrich-existing",
        "--enrich-limit",
        "30",
        "--bar-count",
        "20",
        "--timeout",
        "45",
    ]


def _a_share_kline_command(config: DailyPipelineConfig) -> list[str]:
    return [
        config.python_executable,
        "scripts/refresh_a_share_kline.py",
        "--snapshot",
        str(config.snapshot_path),
        "--holdings",
        str(config.holdings_path),
        "--candidate-limit",
        str(config.candidate_limit),
        "--bar-count",
        str(config.kline_bar_count),
        "--sleep",
        "1.3",
        "--retry-rate-limit",
        "1",
    ]


def _external_enrich_command(config: DailyPipelineConfig, codes: list[str]) -> list[str]:
    return [
        config.python_executable,
        "scripts/enrich_tdx_snapshot.py",
        "--snapshot",
        str(config.snapshot_path),
        "--codes",
        ",".join(codes[: max(config.enrich_limit, 0)]),
        "--bar-count",
        "120",
        "--news-limit",
        str(config.stock_news_limit),
        "--market-news-limit",
        str(config.market_news_limit),
        "--field-timeout",
        "10",
        "--request-timeout",
        "8",
        "--sleep",
        "0.1",
        "--enable-tushare-moneyflow",
        "--skip-akshare-stock-fields",
    ]


def _report_command(config: DailyPipelineConfig) -> list[str]:
    return [
        config.python_executable,
        "scripts/run_daily_analysis.py",
        "--provider",
        config.provider_name,
        "--holdings",
        str(config.holdings_path),
        "--candidate-limit",
        "20",
        "--output-dir",
        str(config.output_dir),
        "--html-dir",
        str(config.html_dir),
    ]


def _pipeline_codes(config: DailyPipelineConfig) -> list[str]:
    seen: set[str] = set()
    codes: list[str] = []
    for code in _holding_codes(Path(config.holdings_path)) + _candidate_codes(
        Path(config.snapshot_path)
    ):
        normalized = _normalize_code(code)
        if normalized and normalized not in seen:
            seen.add(normalized)
            codes.append(normalized)
        if len(codes) >= max(config.enrich_limit, 0):
            break
    return codes


def _safe_pipeline_codes(config: DailyPipelineConfig) -> list[str]:
    try:
        return _pipeline_codes(config)
    except Exception:
        return []


def _holding_codes(path: Path) -> list[str]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as file:
        return [row.get("code", "") for row in csv.DictReader(file)]


def _candidate_codes(path: Path) -> list[str]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    universe = payload.get("candidate_universe", {})
    items = universe.get("items", []) if isinstance(universe, dict) else []
    return [
        str(item.get("code") or "")
        for item in items
        if isinstance(item, dict) and item.get("code")
    ]


def _write_announcements(config: DailyPipelineConfig, codes: list[str]) -> None:
    out_dir = Path(config.announcement_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    blocks = [
        "# StockTS 公告事件快照",
        "",
        f"生成时间：{datetime.now().isoformat(timespec='seconds')}",
        "",
    ]
    for code in codes:
        try:
            report = fetch_cninfo_announcements(code, limit=config.announcement_limit)
            markdown = render_announcement_markdown(report)
            (out_dir / f"{code}.md").write_text(markdown, encoding="utf-8")
            blocks.extend([f"## {code}", "", f"- 返回公告：{len(report.items)}", f"- 风险事件：{len(report.risk_events)}", ""])
        except Exception as exc:
            blocks.extend([f"## {code}", "", f"- 公告抓取失败：{exc}", ""])
    (out_dir / "latest.md").write_text("\n".join(blocks).strip() + "\n", encoding="utf-8")


def _write_pipeline_decisions(config: DailyPipelineConfig, status_path: Path) -> None:
    out_dir = Path(config.output_dir)
    markdown_path = out_dir / "latest.md"
    if not markdown_path.exists():
        return
    status_text = status_path.read_text(encoding="utf-8", errors="ignore") if status_path.exists() else ""
    write_decision_artifact(
        markdown_path.read_text(encoding="utf-8", errors="ignore"),
        out_dir / "latest_decisions.json",
        pipeline_status=status_text,
    )


def _write_pipeline_status(
    path: Path,
    status: str,
    steps: dict[str, str],
    codes: list[str],
    error: str,
) -> None:
    lines = [
        f"status={status}",
        f"generated_at={datetime.now().isoformat(timespec='seconds')}",
        f"codes={','.join(codes)}",
    ]
    lines.extend(f"{key}={value}" for key, value in steps.items())
    if error:
        lines.append(f"error={error}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _short_error(exc: Exception) -> str:
    return "".join(format_exception_only(type(exc), exc)).strip().replace("\n", " ")[:180]


def _normalize_code(code: str) -> str:
    digits = "".join(ch for ch in str(code).strip() if ch.isdigit())
    if len(digits) == 5:
        return digits
    return digits[:6] if len(digits) >= 6 else ""


def _run_command(command: list[str], timeout_seconds: int) -> None:
    subprocess.run(command, check=True, timeout=timeout_seconds)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the full StockTS daily data pipeline.")
    parser.add_argument("--snapshot", default="data/imports/tdx_snapshots.json")
    parser.add_argument("--holdings", default="data/portfolio/holdings.csv")
    parser.add_argument("--output-dir", default="reports/daily")
    parser.add_argument("--html-dir", default="reports/html")
    parser.add_argument("--announcement-dir", default="reports/announcements")
    parser.add_argument("--provider", default="tdx-snapshot")
    parser.add_argument("--candidate-limit", type=int, default=300)
    parser.add_argument("--enrich-limit", type=int, default=50)
    parser.add_argument("--kline-bar-count", type=int, default=120)
    parser.add_argument("--stock-news-limit", type=int, default=3)
    parser.add_argument("--market-news-limit", type=int, default=20)
    parser.add_argument("--external-enrich-timeout", type=int, default=300)
    parser.add_argument("--announcement-limit", type=int, default=5)
    parser.add_argument("--python", default=sys.executable, dest="python_executable")
    parser.add_argument("--skip-refresh", action="store_true")
    parser.add_argument("--skip-tdx-enrich", action="store_true")
    parser.add_argument("--skip-a-share-kline", action="store_true")
    parser.add_argument("--skip-external-enrich", action="store_true")
    parser.add_argument("--skip-announcements", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_daily_pipeline(
        DailyPipelineConfig(
            snapshot_path=args.snapshot,
            holdings_path=args.holdings,
            output_dir=args.output_dir,
            html_dir=args.html_dir,
            announcement_dir=args.announcement_dir,
            provider_name=args.provider,
            candidate_limit=args.candidate_limit,
            enrich_limit=args.enrich_limit,
            kline_bar_count=args.kline_bar_count,
            stock_news_limit=args.stock_news_limit,
            market_news_limit=args.market_news_limit,
            external_enrich_timeout=args.external_enrich_timeout,
            announcement_limit=args.announcement_limit,
            python_executable=args.python_executable,
            skip_refresh=args.skip_refresh,
            skip_tdx_enrich=args.skip_tdx_enrich,
            skip_a_share_kline=args.skip_a_share_kline,
            skip_external_enrich=args.skip_external_enrich,
            skip_announcements=args.skip_announcements,
        )
    )
    print(result.status_path)
    return 0 if result.ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
