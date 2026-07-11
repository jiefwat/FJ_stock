#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from traceback import format_exception_only
from typing import Callable

from stock_ts.announcements import fetch_cninfo_announcements, render_announcement_markdown
from stock_ts.daily_decisions import write_decision_artifact
from stock_ts.data_chain import validate_data_chain

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
    tdx_bridge_python: str = ""
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
            steps["external_enrich"] = _run_external_enrichment(config, codes, command_runner)
        else:
            steps["external_enrich"] = "skipped_no_codes"

        if config.skip_announcements:
            steps["announcements"] = "skipped"
        else:
            try:
                _write_announcements(config, _announcement_codes(config, codes))
                steps["announcements"] = "ok"
            except Exception as exc:
                steps["announcements"] = f"failed:{_short_error(exc)}"

        command_runner(_report_command(config), 180)
        steps["report"] = "ok"
        data_chain = _write_data_chain_status(config, steps)
        steps["data_chain"] = str(data_chain.get("status") or "unknown")
        final_status = _pipeline_status_from_chain(data_chain)
        error = _data_chain_error_summary(data_chain) if final_status == "failed" else ""
        _write_pipeline_status(status_path, final_status, steps, codes, error, data_chain)
        _write_pipeline_decisions(config, status_path)
        return DailyPipelineResult(ok=final_status != "failed", status_path=status_path)
    except Exception as exc:
        error = "".join(format_exception_only(type(exc), exc)).strip()
        _write_pipeline_status(status_path, "failed", steps, _safe_pipeline_codes(config), error)
        return DailyPipelineResult(ok=False, status_path=status_path)


def _refresh_command(config: DailyPipelineConfig) -> list[str]:
    return [
        config.python_executable,
        "scripts/refresh_tdx_snapshot.py",
        "--python",
        _tdx_bridge_python(config),
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
        _tdx_bridge_python(config),
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


def _tdx_bridge_python(config: DailyPipelineConfig) -> str:
    explicit = config.tdx_bridge_python or os.getenv("STOCK_TS_TDX_BRIDGE_PYTHON", "").strip()
    if explicit:
        return explicit
    for executable in [config.python_executable, "python3.11", "python3.12", "python3"]:
        if executable and _python_can_import_eltdx(executable):
            return executable
    return "python3.11"


def _python_can_import_eltdx(executable: str) -> bool:
    try:
        result = subprocess.run(
            [executable, "-c", "import eltdx"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def _run_external_enrichment(
    config: DailyPipelineConfig,
    codes: list[str],
    command_runner: CommandRunner,
) -> str:
    commands = _external_enrich_commands(config, codes)
    if not commands:
        return "skipped_no_codes"

    failures: list[str] = []
    success_count = 0
    timeout = max(120, min(config.external_enrich_timeout, 360))
    for command in commands:
        try:
            command_runner(command, timeout)
            success_count += 1
        except Exception as exc:
            failures.append(_short_error(exc))
    if not failures:
        return "ok"
    first_error = failures[0]
    if success_count:
        return f"partial:{success_count}/{len(commands)} chunks ok; {first_error}"
    return f"failed:{first_error}"


def _external_enrich_commands(config: DailyPipelineConfig, codes: list[str]) -> list[list[str]]:
    enrich_limit = max(config.enrich_limit, 0)
    if enrich_limit == 0:
        return []
    code_set = set(codes)
    holdings = [
        code for code in _holding_codes(Path(config.holdings_path)) if code in code_set
    ]
    commands: list[list[str]] = []
    if holdings:
        # Holdings are the user-facing priority: include AKShare news/fund/valuation fields.
        commands.append(
            _external_enrich_command(
                config,
                holdings[:enrich_limit],
                akshare_stock_fields=True,
            )
        )
    holding_set = set(holdings)
    remaining = [code for code in codes if code not in holding_set]
    for chunk in _chunks(remaining[:enrich_limit], 10):
        commands.append(_external_enrich_command(config, chunk, akshare_stock_fields=False))
    if not commands and codes:
        commands.append(_external_enrich_command(config, codes, akshare_stock_fields=True))
    return commands


def _external_enrich_command(
    config: DailyPipelineConfig,
    codes: list[str],
    *,
    akshare_stock_fields: bool,
) -> list[str]:
    command = [
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
        "8" if akshare_stock_fields else "10",
        "--request-timeout",
        "6" if akshare_stock_fields else "8",
        "--sleep",
        "0",
        "--enable-tushare-moneyflow",
    ]
    if not akshare_stock_fields:
        command.append("--skip-akshare-stock-fields")
    return command


def _chunks(items: list[str], size: int) -> list[list[str]]:
    chunk_size = max(1, size)
    return [items[index : index + chunk_size] for index in range(0, len(items), chunk_size)]


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


def _announcement_codes(config: DailyPipelineConfig, codes: list[str]) -> list[str]:
    code_set = set(codes)
    holdings = [
        _normalize_code(code)
        for code in _holding_codes(Path(config.holdings_path))
        if _normalize_code(code)
    ]
    selected = [code for code in holdings if not code_set or code in code_set]
    if selected:
        return selected
    return codes[: max(config.enrich_limit, 0)]


def _write_announcements(config: DailyPipelineConfig, codes: list[str]) -> None:
    out_dir = Path(config.announcement_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = Path(config.snapshot_path)
    snapshot = _read_snapshot_payload(snapshot_path)
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
            _write_announcement_report_to_snapshot(snapshot, code, report)
            blocks.extend(
                [
                    f"## {code}",
                    "",
                    f"- 返回公告：{len(report.items)}",
                    f"- 风险事件：{len(report.risk_events)}",
                    "",
                ]
            )
        except Exception as exc:
            blocks.extend([f"## {code}", "", f"- 公告抓取失败：{exc}", ""])
    _write_announcement_refresh_metadata(snapshot, codes)
    (out_dir / "latest.md").write_text("\n".join(blocks).strip() + "\n", encoding="utf-8")
    if snapshot:
        snapshot_path.write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8"
        )


def _read_snapshot_payload(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_announcement_report_to_snapshot(snapshot: dict, code: str, report) -> None:
    if not snapshot:
        return
    stocks = snapshot.setdefault("stocks", {})
    if not isinstance(stocks, dict):
        return
    stock = stocks.setdefault(code, {"name": code})
    if not isinstance(stock, dict):
        return
    stock["announcements"] = [
        {
            "code": item.code or code,
            "name": item.name,
            "title": item.title,
            "date": item.date,
            "url": item.url,
            "risk_flags": list(item.risk_flags),
            "source": report.source,
        }
        for item in report.items
    ]
    sources = set(str(item) for item in stock.get("data_sources", []) if item)
    sources.add("cninfo.announcement")
    stock["data_sources"] = sorted(sources)


def _write_announcement_refresh_metadata(snapshot: dict, codes: list[str]) -> None:
    if not snapshot:
        return
    stocks = snapshot.get("stocks", {})
    updated_count = 0
    if isinstance(stocks, dict):
        for code in codes:
            stock = stocks.get(code)
            if isinstance(stock, dict) and stock.get("announcements"):
                updated_count += 1
    snapshot["announcement_refresh"] = {
        "source": "cninfo",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "requested_count": len(codes),
        "updated_count": updated_count,
        "failed_count": max(0, len(codes) - updated_count),
    }


def _write_pipeline_decisions(config: DailyPipelineConfig, status_path: Path) -> None:
    out_dir = Path(config.output_dir)
    markdown_path = out_dir / "latest.md"
    if not markdown_path.exists():
        return
    status_text = (
        status_path.read_text(encoding="utf-8", errors="ignore") if status_path.exists() else ""
    )
    write_decision_artifact(
        markdown_path.read_text(encoding="utf-8", errors="ignore"),
        out_dir / "latest_decisions.json",
        pipeline_status=status_text,
    )


def _write_data_chain_status(config: DailyPipelineConfig, steps: dict[str, str]) -> dict:
    return validate_data_chain(
        snapshot_path=config.snapshot_path,
        holdings_path=config.holdings_path,
        output_path=Path(config.output_dir) / "data_chain_status.json",
        pipeline_steps=steps,
    )


def _pipeline_status_from_chain(data_chain: dict) -> str:
    status = str(data_chain.get("status") or "")
    if status == "failed":
        return "failed"
    if status == "warn":
        return "degraded"
    return "ok"


def _data_chain_error_summary(data_chain: dict) -> str:
    blockers = data_chain.get("blockers")
    if not isinstance(blockers, list) or not blockers:
        return ""
    return "; ".join(str(item) for item in blockers[:5])


def _write_pipeline_status(
    path: Path,
    status: str,
    steps: dict[str, str],
    codes: list[str],
    error: str,
    data_chain: dict | None = None,
) -> None:
    lines = [
        f"status={status}",
        f"generated_at={datetime.now().isoformat(timespec='seconds')}",
        f"codes={','.join(codes)}",
    ]
    lines.extend(f"{key}={value}" for key, value in steps.items())
    if data_chain:
        blockers = data_chain.get("blockers")
        warnings = data_chain.get("warnings")
        if isinstance(blockers, list) and blockers:
            lines.append("data_chain_blockers=" + "; ".join(str(item) for item in blockers[:8]))
        if isinstance(warnings, list) and warnings:
            lines.append("data_chain_warnings=" + "; ".join(str(item) for item in warnings[:8]))
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
    parser.add_argument(
        "--tdx-bridge-python",
        default=os.getenv("STOCK_TS_TDX_BRIDGE_PYTHON", "").strip(),
        help="Python executable that has eltdx installed; defaults to python3.11.",
    )
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
            tdx_bridge_python=args.tdx_bridge_python,
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
