from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def build_decision_artifact(markdown: str, *, pipeline_status: str = "") -> dict[str, Any]:
    """Build the compact decision contract used by mobile email and the home page."""
    positions = _position_records(markdown)
    red, yellow, green = _traffic_lights(markdown, positions)
    return {
        "schema_version": 1,
        "trade_date": _trade_date(markdown),
        "market": {
            "summary": _market_summary(markdown),
        },
        "traffic_lights": {
            "red": red,
            "yellow": yellow,
            "green": green,
        },
        "opportunities": _candidate_entries(markdown, limit=10),
        "data_limits": _data_limits(pipeline_status),
    }


def write_decision_artifact(
    markdown: str,
    path: str | Path,
    *,
    pipeline_status: str = "",
) -> dict[str, Any]:
    artifact = build_decision_artifact(markdown, pipeline_status=pipeline_status)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return artifact


def read_decision_artifact(path: str | Path) -> dict[str, Any]:
    target = Path(path)
    if not target.exists():
        return {}
    try:
        data = json.loads(target.read_text(encoding="utf-8", errors="ignore"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _trade_date(markdown: str) -> str:
    match = re.search(r"（(\d{4}-\d{2}-\d{2})）", markdown)
    return match.group(1) if match else "最近交易日"


def _market_summary(markdown: str) -> str:
    market = _first_section(markdown, ["## 每日大盘情况", "## 每日大盘分析", "## A股大盘"])
    first = _first_content_line(market)
    if first:
        return first
    conclusion = _section(markdown, "## 深度结论")
    first = _first_content_line(conclusion)
    return first or "未读取到大盘结论"


def _traffic_lights(
    markdown: str,
    positions: list[dict[str, Any]],
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    red: list[dict[str, str]] = []
    yellow: list[dict[str, str]] = []
    green: list[dict[str, str]] = []
    for item in positions:
        name = str(item["name"])
        trend = str(item["trend"])
        risk = str(item["risk"])
        is_profit = bool(item["is_profit"])
        is_loss = bool(item["is_loss"])
        if risk == "高" or (is_profit and trend == "下降趋势"):
            red.append(_traffic_item(name, "不加仓；反弹优先锁利润/降风险", item))
        elif is_profit and trend == "上升趋势":
            green.append(_traffic_item(name, "持有跟踪；跌破纪律线再减", item))
        elif is_loss or trend == "下降趋势" or risk == "中":
            yellow.append(_traffic_item(name, "只看修复确认；不补亏不追高", item))
    if not red and not yellow and not green:
        red.extend(
            {
                "name": name,
                "action": "不加仓；反弹优先锁利润/降风险",
                "reason": "日报标记为弱势或高风险持仓",
            }
            for name in _weak_holding_names_from_summary(markdown)
        )
    return red, yellow, green


def _traffic_item(name: str, action: str, source: dict[str, Any]) -> dict[str, str]:
    reason = f"趋势 {source['trend']}，风险 {source['risk']}"
    pnl = str(source.get("pnl") or "")
    if pnl:
        reason += f"，盈亏 {pnl}"
    return {"name": name, "action": action, "reason": reason}


def _position_records(markdown: str) -> list[dict[str, Any]]:
    detail = _section(markdown, "## 持仓明细", max_lines=120)
    if not detail:
        detail = _first_section(markdown, ["## 每日持仓分析", "## 持仓分析"], max_lines=120)
    records: list[dict[str, Any]] = []
    for item in _content_items(detail):
        parsed = _parse_stock_line(item)
        if not parsed:
            continue
        name, _code, detail_text = parsed
        trend = _extract_field(detail_text, "趋势") or "未识别"
        risk = _extract_field(detail_text, "风险") or "未识别"
        records.append(
            {
                "name": name,
                "trend": trend,
                "risk": risk,
                "is_profit": "盈亏 -" not in detail_text
                and re.search(r"盈亏 [0-9]", detail_text) is not None,
                "is_loss": "盈亏 -" in detail_text,
                "pnl": _extract_position_pnl(detail_text),
            }
        )
    return records


def _candidate_entries(markdown: str, *, limit: int) -> list[dict[str, str]]:
    section = _section(markdown, "## 候选观察票", max_lines=limit * 4 + 20)
    if not section:
        section = _section(markdown, "## 候选股票", max_lines=limit * 4 + 20)
    if not section:
        section = _section(markdown, "## 候选股票池摘要", max_lines=limit * 4 + 20)
    entries: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for raw_line in section.splitlines():
        line = raw_line.strip()
        match = re.match(
            r"(?P<rank>\d+)[.、]\s*(?P<name>.+?)（(?P<code>[0-9A-Za-z]{5,6})(?:，(?P<sector>[^）]+))?）：(?P<summary>.+)",
            line,
        )
        if match:
            if current:
                entries.append(_complete_candidate_entry(current))
            current = {
                "name": _clean_stock_name(match.group("name")),
                "code": _normalize_code(match.group("code")),
                "sector": (match.group("sector") or "未识别板块").strip(),
                "summary": match.group("summary").strip(),
                "reason": "",
                "risk": "",
                "action": "",
            }
            continue
        if current is None:
            continue
        stripped = _strip_bullet(line)
        if stripped.startswith("入选理由："):
            current["reason"] = stripped.removeprefix("入选理由：").strip()
        elif stripped.startswith("风险提示："):
            current["risk"] = stripped.removeprefix("风险提示：").strip()
        elif stripped.startswith("观察条件："):
            current["action"] = stripped.removeprefix("观察条件：").strip()
    if current:
        entries.append(_complete_candidate_entry(current))
    return _deduplicate_entries(entries)[:limit]


def _complete_candidate_entry(entry: dict[str, str]) -> dict[str, str]:
    return {
        "name": entry.get("name") or "未识别股票",
        "code": entry.get("code") or "",
        "sector": entry.get("sector") or "未识别板块",
        "reason": entry.get("reason") or entry.get("summary") or "入选理由待补充",
        "risk": entry.get("risk") or "等待盘中确认",
        "action": entry.get("action") or "只观察，不追高；开盘承接确认后再看",
    }


def _data_limits(status_text: str) -> list[str]:
    status = _parse_status(status_text)
    limits: list[str] = []
    external = str(status.get("external_enrich", ""))
    kline = str(status.get("a_share_kline", ""))
    if external.startswith(("failed", "partial")):
        limits.extend(["资金面判断不可信", "消息催化判断不可信"])
    if kline.startswith("failed"):
        limits.append("K线不完整，不做趋势突破判断")
    elif kline.startswith("partial"):
        limits.append("部分K线缺失，相关个股只做观察")
    return limits


def _section(markdown: str, heading: str, *, max_lines: int = 80) -> str:
    lines = markdown.splitlines()
    capture = False
    captured: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped == heading:
            capture = True
            continue
        if capture and stripped.startswith("#"):
            break
        if capture and stripped:
            captured.append(stripped)
        if len(captured) >= max_lines:
            break
    return "\n".join(captured)


def _first_section(markdown: str, headings: list[str], *, max_lines: int = 80) -> str:
    for heading in headings:
        content = _section(markdown, heading, max_lines=max_lines)
        if content:
            return content
    return ""


def _content_items(content: str) -> list[str]:
    return [_strip_bullet(line) for line in content.splitlines() if line.strip()]


def _first_content_line(content: str) -> str:
    for item in _content_items(content):
        if item:
            return item
    return ""


def _strip_bullet(text: str) -> str:
    stripped = text.strip()
    for prefix in ("- ", "* "):
        if stripped.startswith(prefix):
            return stripped[len(prefix) :].strip()
    if len(stripped) > 3 and stripped[0].isdigit() and stripped[1] in {".", "、"}:
        return stripped[2:].strip()
    return stripped


def _parse_stock_line(text: str) -> tuple[str, str, str] | None:
    match = re.match(
        r"(?:\d+[.、]\s*)?(?P<name>.+?)（(?P<code>[0-9A-Za-z]{5,6})(?:，[^）]*)?）：(?P<detail>.+)",
        _strip_bullet(text),
    )
    if not match:
        return None
    return (
        _clean_stock_name(match.group("name")),
        _normalize_code(match.group("code")),
        match.group("detail").strip(),
    )


def _extract_field(text: str, label: str) -> str:
    match = re.search(rf"{label}\s*([^，。；\s]+)", text)
    return match.group(1).strip() if match else ""


def _extract_position_pnl(detail: str) -> str:
    match = re.search(r"盈亏\s*([^，]+(?:（[^）]+）)?)", detail)
    return match.group(1).strip() if match else ""


def _weak_holding_names_from_summary(markdown: str) -> list[str]:
    names: list[str] = []
    for match in re.finditer(r"弱势或高风险持仓：([^\n。；]+)", markdown):
        for raw_name in re.split(r"[、,，]", match.group(1)):
            name = raw_name.strip().strip("：:。；;")
            if not name or _looks_like_summary_phrase(name):
                continue
            names.append(name)
    return list(dict.fromkeys(names))


def _looks_like_summary_phrase(text: str) -> bool:
    summary_keywords = ("持仓", "大盘", "环境", "需要", "降低", "回撤", "先处理")
    return any(keyword in text for keyword in summary_keywords) or len(text) > 12


def _clean_stock_name(raw: str) -> str:
    cleaned = re.sub(r"^\s*(?:[-*]\s*)?\d+[.、]\s*", "", raw.strip())
    return cleaned.strip()


def _normalize_code(code: str) -> str:
    return code.strip().lower().removeprefix("sh").removeprefix("sz").split("，", 1)[0].strip()


def _deduplicate_entries(entries: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    unique: list[dict[str, str]] = []
    for entry in entries:
        key = entry.get("code") or entry.get("name") or ""
        normalized = _normalize_code(key) if entry.get("code") else key.strip().lower()
        if normalized and normalized in seen:
            continue
        if normalized:
            seen.add(normalized)
        unique.append(entry)
    return unique


def _parse_status(status_text: str) -> dict[str, str]:
    status: dict[str, str] = {}
    for line in status_text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() != "codes":
            status[key.strip()] = value.strip()
    return status
