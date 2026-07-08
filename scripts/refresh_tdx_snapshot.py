#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

BridgeRunner = Callable[[str, dict[str, object], str], dict[str, Any]]


def refresh_snapshot(
    output: str | Path,
    *,
    python_executable: str | None = None,
    candidate_limit: int = 300,
    bar_count: int = 20,
    quote_only: bool = False,
    timeout: float = 20.0,
    runner: BridgeRunner | None = None,
) -> dict[str, int | str]:
    output_path = Path(output)
    bridge_runner = runner or run_bridge
    python_executable = python_executable or default_bridge_python()
    existing = _read_existing_snapshot(output_path)
    market = bridge_runner("market", {"timeout": timeout}, python_executable)
    sectors = bridge_runner("sectors", {"timeout": timeout, "limit": 20}, python_executable)
    candidates = bridge_runner(
        "candidate_universe",
        {
            "timeout": timeout,
            "limit": candidate_limit,
            "bar_count": bar_count,
            "quote_only": quote_only,
        },
        python_executable,
    )
    snapshot = {
        **existing,
        "source": "tdx-mcp-eltdx-bridge",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "market": market,
        "sectors": sectors.get("sectors", sectors),
        "candidate_universe": candidates,
        "stocks": existing.get("stocks", {}),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    items = candidates.get("items", []) if isinstance(candidates, dict) else []
    return {
        "output": str(output_path),
        "scanned_count": int(candidates.get("scanned_count", 0)),
        "candidate_count": len(items) if isinstance(items, list) else 0,
    }


def enrich_existing_snapshot(
    output: str | Path,
    *,
    python_executable: str | None = None,
    enrich_limit: int = 30,
    enrich_start: int = 0,
    bar_count: int = 20,
    timeout: float = 20.0,
    runner: BridgeRunner | None = None,
) -> dict[str, int | str]:
    output_path = Path(output)
    bridge_runner = runner or run_bridge
    python_executable = python_executable or default_bridge_python()
    snapshot = _read_existing_snapshot(output_path)
    universe = _candidate_universe_dict(snapshot)
    items = _candidate_items(universe)
    start = max(enrich_start, 0)
    limit = max(enrich_limit, 0)
    selected = items[start : start + limit] if limit else []
    now = datetime.now(timezone.utc).isoformat()

    try:
        enrichment = bridge_runner(
            "candidate_enrichment",
            {
                "timeout": timeout,
                "bar_count": bar_count,
                "items": selected,
            },
            python_executable,
        )
        enriched_items = _candidate_items(enrichment)
        universe["items"] = _merge_enriched_items(items, enriched_items)
        universe["enrichment_status"] = _enrichment_status(
            _count_enriched_items(universe["items"]),
            len(items),
        )
        universe["enrichment_error"] = ""
    except Exception as exc:  # Keep the fast quote snapshot usable if enrichment fails.
        universe["items"] = items
        universe["enrichment_status"] = "failed"
        universe["enrichment_error"] = str(exc)[:240]

    universe["returned_count"] = int(universe.get("returned_count") or len(items))
    universe["enriched_count"] = _count_enriched_items(universe["items"])
    universe["enrichment_method"] = (
        "前排候选已补真实日线/主题，其余为行情截面。"
        if universe["enriched_count"]
        else "尚未补真实日线/主题，当前为行情截面。"
    )
    universe["enriched_at"] = now
    snapshot["candidate_universe"] = universe
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "output": str(output_path),
        "candidate_count": len(items),
        "enriched_count": int(universe["enriched_count"]),
        "enrichment_status": str(universe["enrichment_status"]),
    }


def run_bridge(
    operation: str,
    payload: dict[str, object],
    python_executable: str,
) -> dict[str, Any]:
    script = Path(__file__).with_name("eltdx_bridge.py")
    result = subprocess.run(
        [python_executable, str(script), operation],
        input=json.dumps(payload, ensure_ascii=False),
        capture_output=True,
        text=True,
        check=False,
        timeout=bridge_process_timeout(float(payload.get("timeout", 20.0))),
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"TDX bridge {operation} failed: {detail}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"TDX bridge {operation} returned invalid JSON") from exc


def bridge_process_timeout(request_timeout: float) -> float:
    return max(request_timeout * 4, request_timeout + 60, 120)


def default_bridge_python() -> str:
    return os.getenv("STOCK_TS_ELTDX_PYTHON") or os.getenv("STOCK_TS_TDX_PYTHON") or sys.executable


def _read_existing_snapshot(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _candidate_universe_dict(snapshot: dict[str, Any]) -> dict[str, Any]:
    universe = snapshot.get("candidate_universe", snapshot.get("candidates"))
    if isinstance(universe, dict):
        return dict(universe)
    return {"items": []}


def _candidate_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    items = payload.get("items", [])
    return [dict(item) for item in items if isinstance(item, dict)] if isinstance(items, list) else []


def _merge_enriched_items(
    existing_items: list[dict[str, Any]],
    enriched_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_code = {
        str(item.get("code") or "").strip(): item
        for item in enriched_items
        if str(item.get("code") or "").strip()
    }
    merged: list[dict[str, Any]] = []
    for item in existing_items:
        code = str(item.get("code") or "").strip()
        enriched = by_code.get(code)
        merged.append({**item, **enriched} if enriched else item)
    return merged


def _count_enriched_items(items: list[dict[str, Any]]) -> int:
    return sum(1 for item in items if item.get("bar_source") == "tdx_daily")


def _enrichment_status(enriched_count: int, total_count: int) -> str:
    if enriched_count <= 0:
        return "none"
    if total_count > 0 and enriched_count >= total_count:
        return "full"
    return "partial"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Refresh StockTS TDX snapshot from eltdx bridge.")
    parser.add_argument("--output", default="data/imports/tdx_snapshots.json")
    parser.add_argument("--python", default=default_bridge_python(), dest="python_executable")
    parser.add_argument("--candidate-limit", type=int, default=300)
    parser.add_argument("--bar-count", type=int, default=20)
    parser.add_argument("--quote-only", action="store_true", help="Use full-market quote snapshot without per-stock kline/topic enrichment.")
    parser.add_argument("--enrich-existing", action="store_true", help="Enrich the existing candidate snapshot instead of refreshing market/sector data.")
    parser.add_argument("--enrich-limit", type=int, default=30)
    parser.add_argument("--enrich-start", type=int, default=0)
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args(argv)
    if args.enrich_existing:
        summary = enrich_existing_snapshot(
            args.output,
            python_executable=args.python_executable,
            enrich_limit=args.enrich_limit,
            enrich_start=args.enrich_start,
            bar_count=args.bar_count,
            timeout=args.timeout,
        )
    else:
        summary = refresh_snapshot(
            args.output,
            python_executable=args.python_executable,
            candidate_limit=args.candidate_limit,
            bar_count=args.bar_count,
            quote_only=args.quote_only,
            timeout=args.timeout,
        )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
