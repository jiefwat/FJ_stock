#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from stock_ts.models import DailyBar
from stock_ts.prediction_feedback import (
    PredictionInput,
    PredictionStore,
    build_feedback_section,
)
from stock_ts.providers.tdx_snapshot_provider import TdxSnapshotProvider
from stock_ts.research_contract import RESEARCH_CONTRACT_VERSION
from stock_ts.research_engine import ResearchContext, ResearchWorkspaceService
from stock_ts.research_fallback import build_local_research
from stock_ts.research_fusion import fuse_research_results
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
    snapshot_path: str | Path = "data/imports/tdx_snapshots.json",
    prediction_db: str | Path = "data/research/predictions.sqlite3",
    feedback_summary_path: str | Path | None = None,
    pipeline_status_path: str | Path = "reports/daily/pipeline.status",
) -> DailyResearchResult:
    current = now or datetime.now(TZ)
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    store = ResearchSnapshotStore(root, clock=lambda: current)
    active_service = service or ResearchWorkspaceService(cache_ttl=0)
    modules: dict[str, str] = {}
    errors: dict[str, str] = {}
    snapshot_file = Path(snapshot_path)
    snapshot = _read_json(snapshot_file)
    snapshot_fingerprint = _fingerprint(snapshot_file)
    snapshot_version = str(snapshot.get("snapshot_version") or "")
    pipeline_status = _read_status(Path(pipeline_status_path))
    published_version = str(pipeline_status.get("snapshot_version") or "")
    if published_version and snapshot_version != published_version:
        status_path = root / "daily.status.json"
        _atomic_json(
            status_path,
            {
                "status": "skipped",
                "generated_at": current.isoformat(timespec="seconds"),
                "modules": {},
                "errors": {"snapshot_version": "published snapshot changed"},
                "prediction_count": 0,
                "evaluated_count": 0,
                "feedback_sample_count": 0,
                "source_snapshot_version": snapshot_version,
            },
        )
        return DailyResearchResult(ok=False, status="skipped", status_path=status_path)
    prediction_store = PredictionStore(prediction_db)
    prediction_count = 0
    evaluated_count = 0
    try:
        _record_market_benchmark(prediction_store, snapshot)
        evaluated_count = _evaluate_pending_predictions(prediction_store, snapshot)
    except Exception as exc:
        errors["prediction_evaluation"] = type(exc).__name__

    for module in ("market", "opportunity"):
        local_result = _build_local_result(module, snapshot_file)
        try:
            enriched_result = active_service.research(
                module,
                ResearchContext(),
                refresh=True,
            )
        except Exception as exc:
            errors[f"{module}_enrichment"] = type(exc).__name__
            if local_result is None:
                modules[module] = "failed"
                continue
            result = local_result
        else:
            result = enriched_result
            if local_result is not None and (
                module == "opportunity"
                and _opportunity_result_requires_local_gate(enriched_result)
            ):
                result = local_result
            elif local_result is not None:
                result = fuse_research_results(local_result, enriched_result)
            elif module == "opportunity":
                result = _prefer_local_opportunity_gate(enriched_result, snapshot_file)
        modules[module] = result.status
        if result.ok:
            current_version = str(
                _read_status(Path(pipeline_status_path)).get("snapshot_version") or ""
            )
            if current_version and current_version != snapshot_version:
                modules[module] = "skipped"
                errors["snapshot_version"] = "published snapshot changed"
                break
            payload = result.to_public_dict()
            payload["evidence_delivery"] = str(payload.get("delivery") or "live")
            payload["delivery"] = "snapshot"
            payload["data_label"] = "最新一致快照"
            payload["stale"] = False
            payload["source_snapshot_fingerprint"] = snapshot_fingerprint
            payload["source_snapshot_version"] = snapshot_version
            payload["source_snapshot_generated_at"] = str(
                snapshot.get("generated_at") or ""
            )
            market = snapshot.get("market")
            payload["source_market_trade_date"] = str(
                market.get("trade_date") if isinstance(market, dict) else ""
            )
            payload_version = str(payload.get("research_contract_version") or "")
            if payload_version and payload_version != RESEARCH_CONTRACT_VERSION:
                raise ValueError("研究快照协议版本不兼容。")
            payload["research_contract_version"] = RESEARCH_CONTRACT_VERSION
            if module == "opportunity":
                try:
                    prediction_count = _record_opportunity_predictions(
                        prediction_store,
                        payload,
                        snapshot=snapshot,
                        snapshot_fingerprint=snapshot_fingerprint,
                        created_at=current.isoformat(timespec="seconds"),
                    )
                    _append_feedback_section(payload, prediction_store)
                except Exception as exc:
                    errors["prediction_recording"] = type(exc).__name__
            store.save(module, payload)
        else:
            errors[module] = result.primary_risk[:120]

    summary = prediction_store.summary(horizon=3)
    summary_path = (
        Path(feedback_summary_path)
        if feedback_summary_path
        else root / "feedback_summary.json"
    )
    _atomic_json(summary_path, summary.to_public_dict())
    success_count = sum(value in {"complete", "partial"} for value in modules.values())
    status = (
        "complete"
        if success_count == 2 and not errors
        else "partial" if success_count else "failed"
    )
    status_path = root / "daily.status.json"
    _atomic_json(
        status_path,
        {
            "status": status,
            "generated_at": current.isoformat(timespec="seconds"),
            "modules": modules,
            "errors": errors,
            "prediction_count": prediction_count,
            "evaluated_count": evaluated_count,
            "feedback_sample_count": summary.sample_count,
            "source_snapshot_version": snapshot_version,
        },
    )
    return DailyResearchResult(ok=success_count > 0, status=status, status_path=status_path)


def _build_local_result(module: str, snapshot_path: Path) -> Any | None:
    if not snapshot_path.exists():
        return None
    try:
        result = build_local_research(
            module,
            ResearchContext(),
            provider=TdxSnapshotProvider(snapshot_path),
        )
        return result if result.module == module else None
    except Exception:
        return None


def _prefer_local_opportunity_gate(result: Any, snapshot_path: Path) -> Any:
    if not _opportunity_result_requires_local_gate(result) or not snapshot_path.exists():
        return result
    try:
        return build_local_research(
            "opportunity",
            ResearchContext(),
            provider=TdxSnapshotProvider(snapshot_path),
        )
    except Exception:
        return result


def _opportunity_result_requires_local_gate(result: Any) -> bool:
    themes: tuple[Any, ...] = ()
    candidates: tuple[Any, ...] = ()
    for section in result.module_sections:
        if section.key == "opportunity-themes":
            themes = section.items
        if section.key == "opportunity-candidates":
            candidates = section.items
    if result.status == "partial" and not candidates:
        return True
    if not themes:
        return False
    candidate_themes = {
        _theme_key(item.label) for item in candidates if _theme_key(item.label)
    }
    return any(_theme_key(theme.name) not in candidate_themes for theme in themes)


def _theme_key(value: object) -> str:
    return "".join(str(value or "").lower().split())


def _atomic_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    temporary.replace(path)


def _read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_status(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    return {
        key: value
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines()
        if "=" in line
        for key, value in [line.split("=", 1)]
    }


def _fingerprint(path: Path) -> str:
    if not path.exists():
        return "missing"
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def _record_market_benchmark(store: PredictionStore, snapshot: dict[str, object]) -> None:
    market = snapshot.get("market")
    if not isinstance(market, dict):
        return
    trade_date = str(market.get("trade_date") or "")
    indices = market.get("indices")
    if not isinstance(indices, list):
        return
    benchmark = next(
        (
            item
            for item in indices
            if isinstance(item, dict) and str(item.get("code") or "") == "000001"
        ),
        None,
    )
    if not isinstance(benchmark, dict):
        return
    try:
        close = float(benchmark.get("close") or 0)
    except (TypeError, ValueError):
        return
    store.record_benchmark_close("000001", trade_date, close)


def _evaluate_pending_predictions(
    store: PredictionStore,
    snapshot: dict[str, object],
) -> int:
    stocks = snapshot.get("stocks")
    if not isinstance(stocks, dict):
        return 0
    evaluated = 0
    for prediction in store.pending_predictions():
        raw = stocks.get(prediction.subject_code)
        if not isinstance(raw, dict):
            continue
        stock_bars = _daily_bars(raw.get("bars"))
        benchmark_bars = store.benchmark_bars(prediction.benchmark_code)
        evaluated += len(
            store.evaluate_prediction(
                prediction.prediction_id,
                stock_bars=stock_bars,
                benchmark_bars=benchmark_bars,
            )
        )
    return evaluated


def _daily_bars(value: object) -> list[DailyBar]:
    if not isinstance(value, list):
        return []
    bars: list[DailyBar] = []
    for row in value:
        if not isinstance(row, dict):
            continue
        try:
            bars.append(
                DailyBar(
                    date=str(row.get("date") or ""),
                    open=float(row.get("open") or 0),
                    high=float(row.get("high") or 0),
                    low=float(row.get("low") or 0),
                    close=float(row.get("close") or 0),
                    volume=float(row.get("volume") or 0),
                )
            )
        except (TypeError, ValueError):
            continue
    return sorted((bar for bar in bars if bar.date and bar.close > 0), key=lambda bar: bar.date)


def _record_opportunity_predictions(
    store: PredictionStore,
    payload: dict[str, object],
    *,
    snapshot: dict[str, object],
    snapshot_fingerprint: str,
    created_at: str,
) -> int:
    stocks = snapshot.get("stocks")
    if not isinstance(stocks, dict):
        return 0
    sections = payload.get("module_sections")
    if not isinstance(sections, list):
        return 0
    section = next(
        (
            item
            for item in sections
            if isinstance(item, dict) and item.get("key") == "opportunity-candidates"
        ),
        None,
    )
    if not isinstance(section, dict) or not isinstance(section.get("items"), list):
        return 0
    recorded = 0
    for item in section["items"][:10]:
        if not isinstance(item, dict):
            continue
        facts = item.get("facts")
        if not isinstance(facts, list):
            continue
        fact_map = {
            str(fact.get("label") or ""): str(fact.get("value") or "")
            for fact in facts
            if isinstance(fact, dict)
        }
        stage = fact_map.get("阶段判断", "")
        if stage not in {"可进入投资候选", "等待确认"}:
            continue
        code = _stock_code(item.get("code"))
        raw = stocks.get(code)
        bars = _daily_bars(raw.get("bars") if isinstance(raw, dict) else None)
        requested_as_of = str(payload.get("as_of") or "")[:10]
        baseline = next(
            (
                bar
                for bar in reversed(bars)
                if not requested_as_of or bar.date <= requested_as_of
            ),
            None,
        )
        if baseline is None:
            continue
        data_as_of = baseline.date
        prediction_id = store.record(
            PredictionInput(
                baseline_trade_date=data_as_of,
                baseline_price=baseline.close,
                subject_code=code,
                subject_name=str(item.get("name") or code),
                theme=str(item.get("label") or "主题待确认"),
                stage=stage,
                score=_score_value(fact_map.get("持续性评分", "0")),
                confidence="高" if _score_value(fact_map.get("持续性评分", "0")) >= 80 else "中",
                support=fact_map.get("入选原因", str(item.get("summary") or "")),
                counter_evidence=str(item.get("risk") or ""),
                confirmation=fact_map.get("确认条件", "待确认"),
                invalidation=fact_map.get("失效条件", "待确认"),
                data_as_of=data_as_of,
                evidence_as_of=data_as_of,
                snapshot_fingerprint=snapshot_fingerprint,
                created_at=created_at,
            )
        )
        if not any(
            isinstance(fact, dict) and fact.get("label") == "预测编号" for fact in facts
        ):
            facts.append({"label": "预测编号", "value": prediction_id})
        recorded += 1
    return recorded


def _stock_code(value: object) -> str:
    digits = "".join(character for character in str(value or "") if character.isdigit())
    return digits[:6] if len(digits) >= 6 else digits


def _score_value(value: str) -> int:
    match = re.search(r"\d+", str(value or ""))
    return int(match.group(0)) if match else 0


def _append_feedback_section(
    payload: dict[str, object],
    store: PredictionStore,
) -> None:
    sections = payload.setdefault("module_sections", [])
    if not isinstance(sections, list):
        return
    sections[:] = [
        item
        for item in sections
        if not isinstance(item, dict) or item.get("key") != "opportunity-feedback"
    ]
    sections.append(build_feedback_section(store.summary(horizon=3)))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate daily market and opportunity research.")
    parser.add_argument("--output-dir", default="reports/research")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--snapshot", default="data/imports/tdx_snapshots.json")
    parser.add_argument("--prediction-db", default="data/research/predictions.sqlite3")
    parser.add_argument("--feedback-summary", default="reports/research/feedback_summary.json")
    parser.add_argument("--pipeline-status", default="reports/daily/pipeline.status")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_daily_research(
        output_dir=args.output_dir,
        snapshot_path=args.snapshot,
        prediction_db=args.prediction_db,
        feedback_summary_path=args.feedback_summary,
        pipeline_status_path=args.pipeline_status,
    )
    print(result.status_path)
    print(result.status)
    return 0 if result.ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
