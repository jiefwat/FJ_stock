from __future__ import annotations

import csv
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

REQUIRED_PIPELINE_STEPS = [
    "refresh",
    "tdx_enrich",
    "a_share_kline",
    "external_enrich",
    "announcements",
    "report",
]


def validate_data_chain(
    *,
    snapshot_path: str | Path,
    holdings_path: str | Path,
    output_path: str | Path | None = None,
    pipeline_steps: dict[str, str] | None = None,
    trust_snapshot_expected_trade_date: bool = True,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Validate the reusable data chain that feeds all four Web modules."""

    current = now or datetime.now()
    snapshot = _read_json(Path(snapshot_path))
    snapshot_expected = (
        _snapshot_expected_trade_date(snapshot)
        if trust_snapshot_expected_trade_date
        else ""
    )
    expected_trade_date = snapshot_expected or _expected_latest_trade_date(current)
    holdings = _read_holding_codes(Path(holdings_path))
    steps = pipeline_steps or {}

    modules = {
        "automation": _validate_automation(steps),
        "market": _validate_market(snapshot, expected_trade_date),
        "portfolio": _validate_portfolio(snapshot, holdings, expected_trade_date),
        "stock": _validate_stock(snapshot, holdings, expected_trade_date),
        "opportunities": _validate_opportunities(snapshot, expected_trade_date),
    }

    blockers = _dedupe(
        item
        for module in modules.values()
        for item in module.get("blockers", [])
        if isinstance(item, str) and item
    )
    warnings = _dedupe(
        item
        for module in modules.values()
        for item in module.get("warnings", [])
        if isinstance(item, str) and item
    )
    status = "failed" if blockers else "warn" if warnings else "ok"
    result: dict[str, Any] = {
        "schema_version": 1,
        "generated_at": current.isoformat(timespec="seconds"),
        "expected_trade_date": expected_trade_date,
        "status": status,
        "blockers": blockers,
        "warnings": warnings,
        "modules": modules,
    }
    if output_path is not None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def _validate_automation(steps: dict[str, str]) -> dict[str, Any]:
    blockers: list[str] = []
    warnings: list[str] = []
    for step in REQUIRED_PIPELINE_STEPS:
        value = str(steps.get(step, "missing"))
        if value == "ok":
            continue
        message = f"{step}={value}"
        if step in {"refresh", "report"} and (
            value == "missing" or value.startswith("failed")
        ):
            blockers.append(f"自动任务关键步骤失败：{message}")
        else:
            warnings.append(f"自动任务未完整：{message}")
    return _module_result("automation", blockers, warnings, steps=dict(steps))


def _validate_market(snapshot: dict[str, Any], expected: str) -> dict[str, Any]:
    market = snapshot.get("market") if isinstance(snapshot, dict) else {}
    market = market if isinstance(market, dict) else {}
    blockers: list[str] = []
    warnings: list[str] = []
    trade_date = str(market.get("trade_date") or "")
    indices = _as_list(market.get("indices"))
    top_sectors = _as_list(market.get("top_sectors")) or _as_list(snapshot.get("sectors"))
    market_news = _as_list(snapshot.get("market_news"))
    if not trade_date:
        blockers.append("大盘缺少交易日期")
    elif _is_before(trade_date, expected):
        blockers.append(f"大盘行情滞后：最新 {trade_date}，应至少 {expected}")
    if not indices:
        blockers.append("大盘缺少指数行情")
    if not top_sectors:
        warnings.append("大盘缺少板块方向")
    if not market_news:
        warnings.append("市场新闻/舆情未采集")
    return _module_result(
        "market",
        blockers,
        warnings,
        trade_date=trade_date,
        coverage={
            "indices": len(indices),
            "top_sectors": len(top_sectors),
            "market_news": len(market_news),
        },
    )


def _validate_portfolio(
    snapshot: dict[str, Any], holdings: list[str], expected: str
) -> dict[str, Any]:
    stocks = snapshot.get("stocks") if isinstance(snapshot, dict) else {}
    stocks = stocks if isinstance(stocks, dict) else {}
    blockers: list[str] = []
    warnings: list[str] = []
    complete = 0
    available = 0
    for code in holdings:
        payload = _stock_payload(stocks, code)
        if not payload:
            blockers.append(f"持仓 {code} 未进入快照")
            continue
        available += 1
        kline_blockers, kline_warnings = _stock_kline_gaps(payload, code, expected, prefix="持仓")
        blockers.extend(kline_blockers)
        warnings.extend(kline_warnings)
        context_gaps = _context_gaps(payload)
        if context_gaps:
            warnings.append(f"持仓 {code} 缺少{'、'.join(context_gaps)}")
        elif not kline_blockers and not kline_warnings:
            complete += 1
    if not holdings:
        warnings.append("未读取到持仓账本")
    return _module_result(
        "portfolio",
        blockers,
        warnings,
        coverage={"holdings": len(holdings), "available": available, "complete": complete},
    )


def _validate_stock(
    snapshot: dict[str, Any], holdings: list[str], expected: str
) -> dict[str, Any]:
    stocks = snapshot.get("stocks") if isinstance(snapshot, dict) else {}
    stocks = stocks if isinstance(stocks, dict) else {}
    focus_codes = holdings[:10] or list(stocks.keys())[:5]
    blockers: list[str] = []
    warnings: list[str] = []
    complete = 0
    for code in focus_codes:
        payload = _stock_payload(stocks, code)
        if not payload:
            blockers.append(f"个股分析 {code} 未进入快照")
            continue
        stock_blockers, stock_warnings = _stock_kline_gaps(
            payload, code, expected, prefix="个股分析"
        )
        blockers.extend(stock_blockers)
        warnings.extend(stock_warnings)
        context_gaps = _context_gaps(payload)
        if context_gaps:
            warnings.append(f"个股分析 {code} 缺少{'、'.join(context_gaps)}")
        elif not stock_blockers and not stock_warnings:
            complete += 1
    return _module_result(
        "stock",
        blockers,
        warnings,
        coverage={"checked": len(focus_codes), "complete": complete},
    )


def _validate_opportunities(snapshot: dict[str, Any], expected: str) -> dict[str, Any]:
    universe_payload = snapshot.get("candidate_universe", snapshot.get("candidates"))
    if isinstance(universe_payload, dict):
        items = _as_list(universe_payload.get("items"))
    else:
        items = _as_list(universe_payload)
    blockers: list[str] = []
    warnings: list[str] = []
    if not items:
        blockers.append("热点机会缺少候选池")
    missing_bars = 0
    stale_bars = 0
    missing_theme = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        latest = _latest_bar_date(item)
        if not latest:
            missing_bars += 1
        elif _is_before(latest, expected):
            stale_bars += 1
        if not _first_present(item.get("theme"), item.get("sector"), item.get("industry")):
            missing_theme += 1
    if missing_bars:
        blockers.append(f"热点机会候选池 {missing_bars}/{len(items)} 缺少K线")
    if stale_bars:
        blockers.append(f"热点机会候选池 {stale_bars}/{len(items)} K线滞后")
    if missing_theme:
        warnings.append(f"热点机会候选池 {missing_theme}/{len(items)} 缺少板块/题材标签")
    if items and not _has_market_movers(snapshot, items):
        warnings.append("市场异动未接入：缺少MCP异动事件或候选池价格异动")
    return _module_result(
        "opportunities",
        blockers,
        warnings,
        coverage={"candidates": len(items), "missing_bars": missing_bars, "stale_bars": stale_bars},
    )


def _module_result(
    name: str, blockers: list[str], warnings: list[str], **extra: Any
) -> dict[str, Any]:
    status = "failed" if blockers else "warn" if warnings else "ok"
    return {
        "name": name,
        "status": status,
        "blockers": _dedupe(blockers),
        "warnings": _dedupe(warnings),
        **extra,
    }


def _stock_kline_gaps(
    payload: dict[str, Any], code: str, expected: str, *, prefix: str
) -> tuple[list[str], list[str]]:
    latest = _latest_bar_date(payload)
    if not latest:
        return [f"{prefix} {code} 缺少K线"], []
    if _is_before(latest, expected):
        if _is_hk_code(code):
            return [], [f"{prefix} 港股 {code} K线滞后：最新 {latest}，应至少 {expected}"]
        return [f"{prefix} {code} K线滞后：最新 {latest}，应至少 {expected}"], []
    return [], []


def _is_hk_code(code: str) -> bool:
    return len(_normalize_code(code)) == 5


def _context_gaps(payload: dict[str, Any]) -> list[str]:
    gaps: list[str] = []
    if not _has_block(payload, "fundamental_metrics") and not _has_block(payload, "valuation"):
        gaps.append("基本面")
    if not _has_block(payload, "fund_flow_detail") and payload.get("fund_flow") in {None, ""}:
        gaps.append("资金面")
    if not _has_block(payload, "news_items"):
        gaps.append("个股新闻")
    if not _has_block(payload, "announcements"):
        gaps.append("公告")
    return gaps


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_holding_codes(path: Path) -> list[str]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as file:
        return [_normalize_code(row.get("code", "")) for row in csv.DictReader(file)]


def _stock_payload(stocks: dict[str, Any], code: str) -> dict[str, Any]:
    normalized = _normalize_code(code)
    payload = stocks.get(normalized) or stocks.get(code)
    return payload if isinstance(payload, dict) else {}


def _latest_bar_date(payload: dict[str, Any]) -> str:
    bars = _as_list(payload.get("bars"))
    dates = [
        str(item.get("date") or "")[:10]
        for item in bars
        if isinstance(item, dict) and item.get("date")
    ]
    return max(dates, default="")


def _has_payload_block(item: object) -> bool:
    if isinstance(item, list):
        return bool(item)
    if isinstance(item, dict):
        return bool(item)
    return item not in {None, "", 0}


def _has_block(payload: dict[str, Any], key: str) -> bool:
    return _has_payload_block(payload.get(key))


def _has_market_movers(snapshot: dict[str, Any], candidates: list[Any]) -> bool:
    for item in _as_list(snapshot.get("market_news")):
        if not isinstance(item, dict):
            continue
        text = f"{item.get('source', '')} {item.get('title', '')} {item.get('summary', '')}"
        if any(marker in text for marker in ["异动", "mover", "top_movers", "市场温度"]):
            return True
    for item in candidates:
        if not isinstance(item, dict):
            continue
        try:
            if abs(float(item.get("pct_chg", 0))) >= 5:
                return True
        except (TypeError, ValueError):
            continue
    return False


def _expected_latest_trade_date(now: datetime) -> str:
    day = now.date()
    while day.weekday() >= 5:
        day -= timedelta(days=1)
    return day.isoformat()


def _snapshot_expected_trade_date(snapshot: dict[str, Any]) -> str:
    refresh = snapshot.get("kline_refresh")
    if not isinstance(refresh, dict):
        return ""
    value = str(refresh.get("expected_trade_date") or "")[:10]
    try:
        return datetime.fromisoformat(value).date().isoformat()
    except ValueError:
        return ""


def _is_before(value: str, expected: str) -> bool:
    return bool(value and expected and value[:10] < expected)


def _first_present(*values: object) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _as_list(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


def _normalize_code(code: object) -> str:
    digits = "".join(ch for ch in str(code).strip() if ch.isdigit())
    if len(digits) == 5:
        return digits
    return digits[:6] if len(digits) >= 6 else ""


def _dedupe(items: list[str] | Any) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
