#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from stock_ts.config import get_settings
from stock_ts.providers.base import DataProviderError


def refresh_a_share_kline_snapshot(
    snapshot_path: str | Path,
    *,
    holdings_path: str | Path | None = "data/portfolio/holdings.csv",
    codes: list[str] | None = None,
    candidate_limit: int = 300,
    bar_count: int = 120,
    sleep_seconds: float = 0.0,
    retry_rate_limit: int = 1,
    tushare_client: object | None = None,
) -> dict[str, Any]:
    """Refresh only A-share daily bars in the local TDX snapshot via Tushare."""
    path = Path(snapshot_path)
    payload = _read_json(path)
    client = tushare_client or _load_tushare()
    selected = _select_refresh_codes(
        payload,
        holdings_path=Path(holdings_path) if holdings_path else None,
        codes=codes,
        candidate_limit=candidate_limit,
    )
    now = datetime.now().isoformat(timespec="seconds")
    updated: list[str] = []
    skipped: list[dict[str, str]] = []
    failed: list[dict[str, str]] = []

    for code in selected:
        if not _is_a_share_code(code):
            skipped.append({"code": code, "reason": "not_a_share"})
            continue
        ts_code = _tushare_code(code)
        try:
            bars = _fetch_tushare_daily_bars(
                client,
                ts_code,
                limit=bar_count,
                retry_rate_limit=retry_rate_limit,
                sleep_seconds=sleep_seconds,
            )
        except Exception as exc:
            failed.append({"code": code, "reason": str(exc)[:180]})
            continue
        if not bars:
            failed.append({"code": code, "reason": "empty_daily_bars"})
            continue
        _merge_stock_payload(payload, code, bars, now)
        _merge_candidate_payload(payload, code, bars, now)
        updated.append(code)
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

    rate_limited_count = sum(
        1 for item in failed if _is_rate_limit_message(str(item.get("reason") or ""))
    )
    status = "ok"
    if failed and updated:
        status = "partial"
    elif failed and not updated:
        status = "failed"

    summary: dict[str, Any] = {
        "source": "tushare.daily",
        "status": status,
        "usable": bool(updated),
        "generated_at": now,
        "requested_count": len(selected),
        "updated_count": len(updated),
        "skipped_count": len(skipped),
        "failed_count": len(failed),
        "rate_limited_count": rate_limited_count,
        "bar_count": bar_count,
        "updated_codes": updated,
        "skipped": skipped,
        "failed": failed,
    }
    payload["kline_refresh"] = summary
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def _select_refresh_codes(
    snapshot: dict[str, Any],
    *,
    holdings_path: Path | None,
    codes: list[str] | None,
    candidate_limit: int,
) -> list[str]:
    seen: set[str] = set()
    selected: list[str] = []
    sources: list[str] = []
    if codes:
        sources.extend(codes)
    else:
        sources.extend(_holding_codes(holdings_path) if holdings_path else [])
        universe = snapshot.get("candidate_universe", snapshot.get("candidates"))
        if isinstance(universe, dict):
            for item in _as_list(universe.get("items"))[: max(candidate_limit, 0)]:
                if isinstance(item, dict):
                    sources.append(str(item.get("code") or ""))
    for source in sources:
        normalized = _normalize_code(source)
        if normalized and normalized not in seen:
            seen.add(normalized)
            selected.append(normalized)
    return selected


def _holding_codes(path: Path | None) -> list[str]:
    if path is None or not path.exists():
        return []
    with path.open(encoding="utf-8") as file:
        return [str(row.get("code") or "") for row in csv.DictReader(file)]


def _fetch_tushare_daily_bars(
    client: object,
    ts_code: str,
    *,
    limit: int,
    retry_rate_limit: int = 1,
    sleep_seconds: float = 0.0,
) -> list[dict[str, Any]]:
    attempts = max(1, retry_rate_limit + 1)
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            frame = client.daily(ts_code=ts_code, limit=limit)  # type: ignore[attr-defined]
            break
        except Exception as exc:
            last_error = exc
            if not _is_rate_limit_message(str(exc)) or attempt >= attempts - 1:
                raise
            time.sleep(max(sleep_seconds, 1.0))
    else:
        raise last_error or RuntimeError("tushare_daily_failed")
    rows = sorted(_records(frame), key=lambda row: str(row.get("trade_date") or ""))
    bars: list[dict[str, Any]] = []
    for row in rows[-limit:]:
        bars.append(
            {
                "date": _format_tushare_date(str(row.get("trade_date") or "")),
                "open": _float(row.get("open")),
                "high": _float(row.get("high")),
                "low": _float(row.get("low")),
                "close": _float(row.get("close")),
                "volume": _float(row.get("vol")) * 100,
                "amount": _optional_float(row.get("amount")),
                "pct_chg": _optional_float(row.get("pct_chg")),
            }
        )
    return [bar for bar in bars if bar["date"] and bar["close"] > 0]


def _is_rate_limit_message(message: str) -> bool:
    lowered = message.lower()
    return "频率超限" in message or "rate limit" in lowered or "too many" in lowered


def _merge_stock_payload(
    snapshot: dict[str, Any], code: str, bars: list[dict[str, Any]], now: str
) -> None:
    stocks = snapshot.setdefault("stocks", {})
    if not isinstance(stocks, dict):
        snapshot["stocks"] = stocks = {}
    stock = stocks.setdefault(code, {})
    if not isinstance(stock, dict):
        stock = {}
        stocks[code] = stock
    stock.update(
        {
            "bars": bars,
            "bar_source": "tushare.daily",
            "price_reliable": True,
            "kline_refreshed_at": now,
        }
    )


def _merge_candidate_payload(
    snapshot: dict[str, Any],
    code: str,
    bars: list[dict[str, Any]],
    now: str,
) -> None:
    universe = snapshot.get("candidate_universe", snapshot.get("candidates"))
    if not isinstance(universe, dict):
        return
    items = universe.get("items", [])
    if not isinstance(items, list):
        return
    for item in items:
        if isinstance(item, dict) and _normalize_code(str(item.get("code") or "")) == code:
            item.update(
                {
                    "bars": bars,
                    "bar_source": "tushare.daily",
                    "price_reliable": True,
                    "kline_refreshed_at": now,
                }
            )


def _load_tushare() -> object:
    token = get_settings().tushare_token.strip()
    if not token:
        raise DataProviderError("Tushare token is missing. Set TUSHARE_TOKEN first.")
    try:
        import tushare as ts  # type: ignore[import-not-found]
    except ImportError as exc:
        raise DataProviderError("Tushare is not installed. Run: pip install tushare") from exc
    try:
        return ts.pro_api(token, timeout=12)
    except TypeError:
        return ts.pro_api(token)


def _records(frame: object) -> list[dict[str, Any]]:
    if frame is None or bool(getattr(frame, "empty", False)):
        return []
    if hasattr(frame, "to_dict"):
        return [dict(item) for item in frame.to_dict("records")]  # type: ignore[call-arg]
    if hasattr(frame, "iterrows"):
        return [dict(row) for _, row in frame.iterrows()]  # type: ignore[attr-defined]
    if isinstance(frame, list):
        return [dict(item) for item in frame if isinstance(item, dict)]
    return []


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _normalize_code(code: object) -> str:
    text = str(code).strip().upper()
    if text.endswith((".SH", ".SZ", ".BJ")):
        text = text[:6]
    digits = "".join(ch for ch in text if ch.isdigit())
    return digits if len(digits) in {5, 6} else ""


def _is_a_share_code(code: str) -> bool:
    if len(code) != 6:
        return False
    if code.startswith(("200", "900")):
        return False
    return code.startswith(
        (
            "000",
            "001",
            "002",
            "003",
            "300",
            "301",
            "600",
            "601",
            "603",
            "605",
            "688",
            "689",
            "920",
            "4",
            "8",
        )
    )


def _tushare_code(code: str) -> str:
    if code.startswith(("600", "601", "603", "605", "688", "689", "900")):
        return f"{code}.SH"
    if code.startswith(("920", "4", "8")):
        return f"{code}.BJ"
    return f"{code}.SZ"


def _format_tushare_date(value: str) -> str:
    text = value.strip()
    if len(text) == 8 and text.isdigit():
        return f"{text[:4]}-{text[4:6]}-{text[6:8]}"
    return text


def _float(value: object) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0


def _optional_float(value: object) -> float | None:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _parse_codes(value: str) -> list[str] | None:
    codes = [item.strip() for item in value.split(",") if item.strip()]
    return codes or None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Refresh A-share daily K-line bars with Tushare.")
    parser.add_argument("--snapshot", default="data/imports/tdx_snapshots.json")
    parser.add_argument("--holdings", default="data/portfolio/holdings.csv")
    parser.add_argument("--codes", default="")
    parser.add_argument("--candidate-limit", type=int, default=300)
    parser.add_argument("--bar-count", type=int, default=120)
    parser.add_argument(
        "--sleep", type=float, default=1.3, help="Seconds to sleep between Tushare calls."
    )
    parser.add_argument("--retry-rate-limit", type=int, default=1)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = refresh_a_share_kline_snapshot(
        args.snapshot,
        holdings_path=args.holdings,
        codes=_parse_codes(args.codes),
        candidate_limit=args.candidate_limit,
        bar_count=args.bar_count,
        sleep_seconds=args.sleep,
        retry_rate_limit=args.retry_rate_limit,
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if summary["usable"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
