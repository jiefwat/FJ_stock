#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import fcntl
import hashlib
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from pathlib import Path
from traceback import format_exception_only
from typing import Callable, TextIO
from uuid import uuid4
from zoneinfo import ZoneInfo

from stock_ts.announcements import fetch_cninfo_announcements, render_announcement_markdown
from stock_ts.daily_decisions import write_decision_artifact
from stock_ts.data_chain import validate_data_chain

CommandRunner = Callable[[list[str], int], None]
BEIJING_TZ = ZoneInfo("Asia/Shanghai")


@dataclass(frozen=True)
class DailyPipelineConfig:
    snapshot_path: str | Path = "data/imports/tdx_snapshots.json"
    holdings_path: str | Path = "data/portfolio/holdings.csv"
    output_dir: str | Path = "reports/daily"
    html_dir: str | Path = "reports/html"
    announcement_dir: str | Path = "reports/announcements"
    research_output_dir: str | Path = "reports/research"
    provider_name: str = "tdx-snapshot"
    candidate_limit: int = 500
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
    skip_research: bool = False


@dataclass(frozen=True)
class DailyPipelineResult:
    ok: bool
    status_path: Path


def run_daily_pipeline(
    config: DailyPipelineConfig,
    *,
    runner: CommandRunner | None = None,
    now: datetime | None = None,
) -> DailyPipelineResult:
    started_at = _beijing_time(now)
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    status_path = output_dir / "pipeline.status"
    command_runner = runner or _run_command
    steps: dict[str, str] = {}
    published_snapshot_path = Path(config.snapshot_path)
    lock_handle = _acquire_pipeline_lock(published_snapshot_path)
    if lock_handle is None:
        return DailyPipelineResult(ok=False, status_path=status_path)
    previous_snapshot = (
        published_snapshot_path.read_bytes() if published_snapshot_path.exists() else None
    )
    pipeline_run_id = _pipeline_run_id(started_at)
    staging_snapshot_path = _staging_snapshot_path(
        published_snapshot_path, pipeline_run_id
    )
    staging_output_dir = _staging_directory(Path(config.output_dir), pipeline_run_id)
    staging_html_dir = _staging_directory(Path(config.html_dir), pipeline_run_id)
    staging_announcement_dir = _staging_directory(
        Path(config.announcement_dir), pipeline_run_id
    )
    work_config = replace(
        config,
        snapshot_path=staging_snapshot_path,
        output_dir=staging_output_dir,
        html_dir=staging_html_dir,
        announcement_dir=staging_announcement_dir,
    )

    try:
        _prepare_staging_snapshot(staging_snapshot_path, previous_snapshot)
        if work_config.skip_refresh:
            steps["refresh"] = "skipped"
        else:
            command_runner(_refresh_command(work_config), 1200)
            steps["refresh"] = "ok"

        if work_config.skip_tdx_enrich:
            steps["tdx_enrich"] = "skipped"
        else:
            command_runner(_tdx_enrich_command(work_config), 600)
            steps["tdx_enrich"] = "ok"

        if work_config.skip_a_share_kline:
            steps["a_share_kline"] = "skipped"
        else:
            try:
                command_runner(
                    _a_share_kline_command(work_config),
                    _a_share_kline_timeout(work_config),
                )
                steps["a_share_kline"] = "ok"
            except Exception as exc:
                steps["a_share_kline"] = f"failed:{_short_error(exc)}"

        codes = _pipeline_codes(work_config)
        if work_config.skip_external_enrich:
            steps["external_enrich"] = "skipped"
        elif codes:
            steps["external_enrich"] = _run_external_enrichment(
                work_config, codes, command_runner
            )
        else:
            steps["external_enrich"] = "skipped_no_codes"

        if work_config.skip_announcements:
            steps["announcements"] = "skipped"
        else:
            try:
                _write_announcements(
                    work_config, _announcement_codes(work_config, codes)
                )
                steps["announcements"] = "ok"
            except Exception as exc:
                steps["announcements"] = f"failed:{_short_error(exc)}"

        command_runner(_report_command(work_config), 180)
        steps["report"] = "ok"
        data_chain = _write_data_chain_status(
            work_config,
            steps,
            now=_data_validation_time(started_at),
        )
        steps["data_chain"] = str(data_chain.get("status") or "unknown")
        final_status = _pipeline_status_from_chain(data_chain)
        error = _data_chain_error_summary(data_chain) if final_status == "failed" else ""
        completed_at = _completion_time(now)
        if final_status == "failed":
            metadata = _pipeline_run_metadata(
                config, started_at, completed_at
            ) | {"pipeline_run_id": pipeline_run_id}
            _write_pipeline_status(
                status_path,
                final_status,
                steps,
                codes,
                error,
                data_chain,
                metadata=metadata,
            )
            return DailyPipelineResult(ok=False, status_path=status_path)

        _stamp_staging_snapshot(staging_snapshot_path, pipeline_run_id, completed_at)
        staging_snapshot_path.replace(published_snapshot_path)
        _normalize_artifact_status_paths(
            staging_output_dir=staging_output_dir,
            published_output_dir=Path(config.output_dir),
            staging_html_dir=staging_html_dir,
            published_html_dir=Path(config.html_dir),
        )
        _publish_staged_directory(staging_output_dir, Path(config.output_dir))
        _publish_staged_directory(staging_html_dir, Path(config.html_dir))
        _publish_staged_directory(
            staging_announcement_dir, Path(config.announcement_dir)
        )
        metadata = _pipeline_run_metadata(config, started_at, completed_at) | {
            "pipeline_run_id": pipeline_run_id,
            "snapshot_version": pipeline_run_id,
            "snapshot_fingerprint": _snapshot_fingerprint(published_snapshot_path),
        }
        _write_pipeline_status(
            status_path,
            final_status,
            steps,
            codes,
            error,
            data_chain,
            metadata=metadata,
        )
        if config.skip_research:
            steps["research"] = "skipped"
        else:
            try:
                command_runner(_research_command(config), 600)
                steps["research"] = "ok"
            except Exception as exc:
                steps["research"] = f"failed:{_short_error(exc)}"
                final_status = "degraded"
        _write_pipeline_status(
            status_path,
            final_status,
            steps,
            codes,
            error,
            data_chain,
            metadata=metadata,
        )
        _write_pipeline_decisions(config, status_path)
        return DailyPipelineResult(ok=final_status != "failed", status_path=status_path)
    except Exception as exc:
        error = "".join(format_exception_only(type(exc), exc)).strip()
        completed_at = _completion_time(now)
        metadata = _pipeline_run_metadata(config, started_at, completed_at) | {
            "pipeline_run_id": pipeline_run_id
        }
        _write_pipeline_status(
            status_path,
            "failed",
            steps,
            _safe_pipeline_codes(config),
            error,
            metadata=metadata,
        )
        return DailyPipelineResult(ok=False, status_path=status_path)
    finally:
        staging_snapshot_path.unlink(missing_ok=True)
        for path in (
            staging_output_dir,
            staging_html_dir,
            staging_announcement_dir,
        ):
            shutil.rmtree(path, ignore_errors=True)
        _release_pipeline_lock(lock_handle)


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


def _a_share_kline_timeout(config: DailyPipelineConfig) -> int:
    # The refresh is deliberately rate-limited, so the timeout must scale with scope.
    return max(1200, min(3600, max(config.candidate_limit, 0) * 4))


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
        "--snapshot",
        str(config.snapshot_path),
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


def _research_command(config: DailyPipelineConfig) -> list[str]:
    return [
        config.python_executable,
        "scripts/run_daily_research.py",
        "--output-dir",
        str(config.research_output_dir),
        "--snapshot",
        str(config.snapshot_path),
        "--pipeline-status",
        str(Path(config.output_dir) / "pipeline.status"),
        "--refresh",
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
    sources = {
        str(item)
        for item in stock.get("data_sources", [])
        if item and not str(item).endswith(".announcement")
    }
    sources.add(f"{report.source}.announcement")
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
    sources = {
        str(row.get("source") or "")
        for code in codes
        for row in (
            stocks.get(code, {}).get("announcements", [])
            if isinstance(stocks, dict) and isinstance(stocks.get(code), dict)
            else []
        )
        if isinstance(row, dict) and row.get("source")
    }
    snapshot["announcement_refresh"] = {
        "source": ",".join(sorted(sources)) if sources else "none",
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


def _write_data_chain_status(
    config: DailyPipelineConfig,
    steps: dict[str, str],
    *,
    now: datetime | None = None,
) -> dict:
    return validate_data_chain(
        snapshot_path=config.snapshot_path,
        holdings_path=config.holdings_path,
        output_path=Path(config.output_dir) / "data_chain_status.json",
        pipeline_steps=steps,
        trust_snapshot_expected_trade_date=steps.get("a_share_kline") == "ok",
        now=now,
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
    metadata: dict[str, str] | None = None,
) -> None:
    run_metadata = metadata or {}
    generated_at = run_metadata.get("completed_at") or datetime.now().isoformat(
        timespec="seconds"
    )
    lines = [
        f"status={status}",
        f"generated_at={generated_at}",
    ]
    lines.extend(
        f"{key}={run_metadata.get(key, '')}"
        for key in (
            "scheduled_at",
            "started_at",
            "completed_at",
            "session_name",
            "intraday",
            "market_trade_date",
            "data_as_of",
            "scanned_count",
            "enriched_count",
            "eligible_count",
            "pipeline_run_id",
            "snapshot_version",
            "snapshot_fingerprint",
        )
        if key in run_metadata
    )
    lines.append(f"codes={','.join(codes)}")
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


def _beijing_time(value: datetime | None) -> datetime:
    current = value or datetime.now(BEIJING_TZ)
    if current.tzinfo is None:
        return current.replace(tzinfo=BEIJING_TZ)
    return current.astimezone(BEIJING_TZ)


def _completion_time(started_override: datetime | None) -> datetime:
    if started_override is not None:
        return _beijing_time(started_override)
    return datetime.now(BEIJING_TZ)


def _refresh_session(current: datetime) -> tuple[str, bool]:
    session_name = {
        7: "morning",
        9: "preopen",
        13: "midday",
        15: "close",
    }.get(current.hour, "manual")
    return session_name, session_name == "midday"


def _data_validation_time(current: datetime) -> datetime:
    # Intraday quotes are current, but the latest complete daily bar closes at 15:30.
    if (current.hour, current.minute) < (15, 30):
        return current - timedelta(days=1)
    return current


def _pipeline_run_metadata(
    config: DailyPipelineConfig,
    started_at: datetime,
    completed_at: datetime,
) -> dict[str, str]:
    session_name, intraday = _refresh_session(started_at)
    scheduled_at = started_at.replace(minute=0, second=0, microsecond=0)
    snapshot = _read_snapshot_payload(Path(config.snapshot_path))
    market = snapshot.get("market") if isinstance(snapshot, dict) else None
    market = market if isinstance(market, dict) else {}
    universe = snapshot.get("candidate_universe") if isinstance(snapshot, dict) else None
    universe = universe if isinstance(universe, dict) else {}
    market_trade_date = str(market.get("trade_date") or "").strip()[:10]
    data_as_of = str(
        snapshot.get("generated_at")
        or market.get("generated_at")
        or market_trade_date
        or ""
    ).strip()
    return {
        "scheduled_at": scheduled_at.isoformat(timespec="seconds"),
        "started_at": started_at.isoformat(timespec="seconds"),
        "completed_at": completed_at.isoformat(timespec="seconds"),
        "session_name": session_name,
        "intraday": str(intraday).lower(),
        "market_trade_date": market_trade_date,
        "data_as_of": data_as_of,
        "scanned_count": _metadata_count(universe, "scanned_count"),
        "enriched_count": _metadata_count(universe, "enriched_count"),
        "eligible_count": _metadata_count(universe, "eligible_count"),
        "snapshot_version": str(snapshot.get("snapshot_version") or ""),
    }


def _pipeline_run_id(started_at: datetime) -> str:
    return f"{started_at:%Y%m%dT%H%M%S}-{uuid4().hex[:8]}"


def _staging_snapshot_path(published: Path, pipeline_run_id: str) -> Path:
    return published.parent / f".{published.name}.{pipeline_run_id}.staging"


def _staging_directory(published: Path, pipeline_run_id: str) -> Path:
    return published.parent / f".{published.name}.{pipeline_run_id}.staging"


def _prepare_staging_snapshot(path: Path, previous: bytes | None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if previous is not None:
        path.write_bytes(previous)


def _stamp_staging_snapshot(path: Path, version: str, published_at: datetime) -> None:
    payload = _read_snapshot_payload(path)
    if not payload:
        raise ValueError("staging snapshot is empty")
    payload["snapshot_version"] = version
    payload["published_at"] = published_at.isoformat(timespec="seconds")
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _snapshot_fingerprint(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def _publish_staged_directory(staging: Path, published: Path) -> None:
    if not staging.exists():
        return
    for source in sorted(path for path in staging.rglob("*") if path.is_file()):
        destination = published / source.relative_to(staging)
        destination.parent.mkdir(parents=True, exist_ok=True)
        source.replace(destination)


def _normalize_artifact_status_paths(
    *,
    staging_output_dir: Path,
    published_output_dir: Path,
    staging_html_dir: Path,
    published_html_dir: Path,
) -> None:
    status_path = staging_output_dir / "latest.status"
    if not status_path.exists():
        return
    text = status_path.read_text(encoding="utf-8", errors="ignore")
    text = text.replace(str(staging_output_dir), str(published_output_dir))
    text = text.replace(str(staging_html_dir), str(published_html_dir))
    status_path.write_text(text, encoding="utf-8")


def _pipeline_lock_path(snapshot_path: Path) -> Path:
    return snapshot_path.parent / f".{snapshot_path.name}.pipeline.lock"


def _acquire_pipeline_lock(snapshot_path: Path) -> TextIO | None:
    lock_path = _pipeline_lock_path(snapshot_path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("a+", encoding="utf-8")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        return None
    return handle


def _release_pipeline_lock(handle: TextIO) -> None:
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    finally:
        handle.close()


def _metadata_count(payload: dict, key: str) -> str:
    value = payload.get(key)
    try:
        return str(max(0, int(value)))
    except (TypeError, ValueError):
        return "0"


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
    parser.add_argument("--research-output-dir", default="reports/research")
    parser.add_argument("--provider", default="tdx-snapshot")
    parser.add_argument("--candidate-limit", type=int, default=500)
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
    parser.add_argument("--skip-research", action="store_true")
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
            research_output_dir=args.research_output_dir,
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
            skip_research=args.skip_research,
        )
    )
    print(result.status_path)
    return 0 if result.ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
