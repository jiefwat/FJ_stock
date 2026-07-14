#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from stock_ts.research_engine import ResearchContext, ResearchWorkspaceService
from stock_ts.research_snapshots import ResearchSnapshotStore

TZ = timezone(timedelta(hours=8))


@dataclass(frozen=True)
class DailyResearchResult:
    ok: bool
    status: str
    status_path: Path


def run_daily_research(
    *,
    output_dir: str | Path = "reports/research",
    service: Any | None = None,
    now: datetime | None = None,
) -> DailyResearchResult:
    current = now or datetime.now(TZ)
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    store = ResearchSnapshotStore(root, clock=lambda: current)
    active_service = service or ResearchWorkspaceService(cache_ttl=0)
    modules: dict[str, str] = {}
    errors: dict[str, str] = {}

    for module in ("market", "opportunity"):
        try:
            result = active_service.research(
                module,
                ResearchContext(),
                refresh=True,
            )
        except Exception as exc:
            modules[module] = "failed"
            errors[module] = type(exc).__name__
            continue
        modules[module] = result.status
        if result.ok:
            payload = result.to_public_dict()
            payload["delivery"] = "snapshot"
            payload["stale"] = False
            store.save(module, payload)
        else:
            errors[module] = result.primary_risk[:120]

    success_count = sum(value in {"complete", "partial"} for value in modules.values())
    status = "complete" if success_count == 2 else "partial" if success_count else "failed"
    status_path = root / "daily.status.json"
    _atomic_json(
        status_path,
        {
            "status": status,
            "generated_at": current.isoformat(timespec="seconds"),
            "modules": modules,
            "errors": errors,
        },
    )
    return DailyResearchResult(ok=success_count > 0, status=status, status_path=status_path)


def _atomic_json(path: Path, payload: dict[str, object]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    temporary.replace(path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate daily market and opportunity research.")
    parser.add_argument("--output-dir", default="reports/research")
    parser.add_argument("--refresh", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_daily_research(output_dir=args.output_dir)
    print(result.status_path)
    print(result.status)
    return 0 if result.ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
