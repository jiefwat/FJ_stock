#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from stock_ts.news_intelligence import classify_news_item, is_market_relevant_news

DEFAULT_SOURCE = "longbridge.mcp"


def import_market_intelligence(
    snapshot: str | Path,
    inputs: list[str | Path],
    *,
    source: str = DEFAULT_SOURCE,
    fetched_at: str | None = None,
    limit: int = 80,
) -> dict[str, Any]:
    snapshot_path = Path(snapshot)
    payload = _read_snapshot(snapshot_path)
    fetched_at = fetched_at or datetime.now(timezone.utc).isoformat()
    existing = [item for item in _as_list(payload.get("market_news")) if isinstance(item, dict)]
    seen = {_dedupe_key(item) for item in existing if _dedupe_key(item)}

    parsed: list[dict[str, Any]] = []
    skipped = 0
    for input_path in inputs:
        raw_payload = json.loads(Path(input_path).read_text(encoding="utf-8"))
        for item in parse_market_intelligence_payload(
            raw_payload,
            source=source,
            fetched_at=fetched_at,
        ):
            key = _dedupe_key(item)
            if not key or key in seen:
                skipped += 1
                continue
            seen.add(key)
            parsed.append(item)
            if len(parsed) >= limit:
                break
        if len(parsed) >= limit:
            break

    payload["market_news"] = existing + parsed
    payload["mcp_market_news_refresh"] = {
        "source": source,
        "generated_at": fetched_at,
        "input_files": [str(Path(item)) for item in inputs],
        "imported_count": len(parsed),
        "skipped_count": skipped,
        "total_market_news_count": len(payload["market_news"]),
        "supported_formats": [
            "longbridge.news",
            "longbridge.top_movers",
            "longbridge.market_temperature",
            "longbridge.finance_calendar",
            "generic_json_news",
        ],
    }
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "snapshot": str(snapshot_path),
        "source": source,
        "imported_count": len(parsed),
        "skipped_count": skipped,
        "total_market_news_count": len(payload["market_news"]),
    }


def parse_market_intelligence_payload(
    payload: Any,
    *,
    source: str = DEFAULT_SOURCE,
    fetched_at: str | None = None,
) -> list[dict[str, Any]]:
    fetched_at = fetched_at or datetime.now(timezone.utc).isoformat()
    rows = _unwrap_mcp_text(payload)
    parsed: list[dict[str, Any]] = []
    if isinstance(rows, list):
        for row in rows:
            parsed.extend(
                parse_market_intelligence_payload(row, source=source, fetched_at=fetched_at)
            )
        return _dedupe_payloads(parsed)
    if not isinstance(rows, dict):
        return []
    if isinstance(rows.get("events"), list):
        return _dedupe_payloads(
            _top_mover_to_payload(row, source=source, fetched_at=fetched_at)
            for row in rows["events"]
            if isinstance(row, dict)
        )
    if _is_market_temperature(rows):
        item = _market_temperature_to_payload(rows, source=source, fetched_at=fetched_at)
        return [item] if item else []
    if isinstance(rows.get("list"), list):
        return _dedupe_payloads(_calendar_to_payloads(rows, source=source, fetched_at=fetched_at))
    if _looks_like_news_row(rows):
        item = _news_row_to_payload(rows, source=source, fetched_at=fetched_at)
        return [item] if item else []
    nested = rows.get("items") or rows.get("data") or rows.get("news") or rows.get("news_list")
    if nested is not None:
        return parse_market_intelligence_payload(nested, source=source, fetched_at=fetched_at)
    return []


def _news_row_to_payload(
    row: dict[str, Any], *, source: str, fetched_at: str
) -> dict[str, Any] | None:
    title = _text(row, "title", "新闻标题", "content")
    if not title:
        return None
    summary = _text(row, "summary", "description", "desc", "摘要", "新闻内容")
    if not _is_relevant_news(title, summary):
        return None
    published_at = _text(row, "published_at", "publish_time", "publish_at", "date", "发布时间")
    classification = classify_news_item(title, summary)
    return _payload(
        title=title,
        summary=summary,
        url=_text(row, "url", "link", "新闻链接"),
        source=_text(row, "source", "source_name", "文章来源") or _source_name(source, "新闻"),
        published_at=published_at,
        fetched_at=fetched_at,
        market=_market_code(row.get("market") or "CN"),
        scope_type=str(row.get("scope_type") or "market"),
        symbols=_symbols_from_row(row),
        sentiment=classification.sentiment,
        risk_tags=classification.risk_tags,
        catalyst_tags=classification.catalyst_tags,
    )


def _top_mover_to_payload(
    row: dict[str, Any], *, source: str, fetched_at: str
) -> dict[str, Any] | None:
    stock = row.get("stock") if isinstance(row.get("stock"), dict) else {}
    name = _text(stock, "name", "full_name", "symbol")
    symbol = _text(stock, "symbol", "code")
    reason = _text(row, "alert_reason") or "价格异动"
    if not name:
        return None
    title = f"{name}异动：{reason}"
    labels = ", ".join(str(item) for item in _as_list(stock.get("labels")) if item)
    change = _text(stock, "change")
    summary_parts = [part for part in [labels, f"涨跌幅 {change}" if change else ""] if part]
    summary = "；".join(summary_parts) or reason
    if not _is_relevant_news(title, summary):
        return None
    classification = classify_news_item(title, summary)
    market = _market_code(stock.get("market") or row.get("market") or "")
    return _payload(
        title=title,
        summary=summary,
        url=_text(row, "url"),
        source=_source_name(source, "市场异动"),
        published_at=_text(row, "timestamp", "updated_at"),
        fetched_at=fetched_at,
        market=market or "global",
        scope_type="market_event",
        symbols=[symbol] if symbol else [],
        sentiment=classification.sentiment,
        risk_tags=classification.risk_tags,
        catalyst_tags=classification.catalyst_tags,
    )


def _market_temperature_to_payload(
    row: dict[str, Any], *, source: str, fetched_at: str
) -> dict[str, Any] | None:
    market = _market_code(row.get("market") or "CN") or "cn"
    temperature = _text(row, "temperature")
    description = _text(row, "description")
    if not temperature:
        return None
    title = f"Longbridge {market.upper()}市场温度 {temperature}：{description or '无描述'}"
    summary = "；".join(
        part
        for part in [
            f"估值温度 {row.get('valuation')}" if row.get("valuation") not in {None, ""} else "",
            f"情绪温度 {row.get('sentiment')}" if row.get("sentiment") not in {None, ""} else "",
        ]
        if part
    )
    temp_value = _float_or_none(row.get("temperature"))
    if temp_value and temp_value >= 60:
        sentiment = "positive"
    elif temp_value and temp_value <= 35:
        sentiment = "negative"
    else:
        sentiment = "neutral"
    return _payload(
        title=title,
        summary=summary,
        url="",
        source=_source_name(source, "市场温度"),
        published_at=_text(row, "timestamp", "updated_at"),
        fetched_at=fetched_at,
        market=market,
        scope_type="market_sentiment",
        symbols=[],
        sentiment=sentiment,
        risk_tags=[] if sentiment != "negative" else ["市场情绪降温"],
        catalyst_tags=[] if sentiment != "positive" else ["风险偏好升温"],
    )


def _calendar_to_payloads(
    rows: dict[str, Any], *, source: str, fetched_at: str
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for day in _as_list(rows.get("list")):
        if not isinstance(day, dict):
            continue
        for info in _as_list(day.get("infos")):
            if not isinstance(info, dict):
                continue
            content = _text(info, "content")
            if not content:
                continue
            market = _market_code(info.get("market") or "CN") or "cn"
            title = f"宏观日历：{content}"
            kv = [
                f"{item.get('key')} {item.get('value')}"
                for item in _as_list(info.get("data_kv"))
                if isinstance(item, dict) and item.get("key")
            ]
            summary = "；".join(kv)
            classification = classify_news_item(title, summary)
            items.append(
                _payload(
                    title=title,
                    summary=summary,
                    url="",
                    source=_source_name(source, "财经日历"),
                    published_at=_text(info, "datetime") or str(day.get("date") or ""),
                    fetched_at=fetched_at,
                    market=market,
                    scope_type="macro_event",
                    symbols=[],
                    sentiment=classification.sentiment,
                    risk_tags=classification.risk_tags,
                    catalyst_tags=classification.catalyst_tags,
                )
            )
    return items


def _payload(
    *,
    title: str,
    summary: str,
    url: str,
    source: str,
    published_at: str,
    fetched_at: str,
    market: str,
    scope_type: str,
    symbols: list[str],
    sentiment: str,
    risk_tags: list[str],
    catalyst_tags: list[str],
) -> dict[str, Any]:
    date_value = (published_at or fetched_at)[:10]
    return {
        "date": date_value,
        "source": source,
        "title": title,
        "summary": summary,
        "url": url,
        "sentiment": sentiment,
        "risk_tags": list(risk_tags),
        "catalyst_tags": list(catalyst_tags),
        "market": market,
        "scope_type": scope_type,
        "symbols": list(symbols),
        "published_at": published_at,
        "fetched_at": fetched_at,
    }


def _unwrap_mcp_text(payload: Any) -> Any:
    if (
        isinstance(payload, dict)
        and payload.get("type") == "text"
        and isinstance(payload.get("text"), str)
    ):
        try:
            return json.loads(payload["text"])
        except json.JSONDecodeError:
            return payload
    return payload


def _looks_like_news_row(row: dict[str, Any]) -> bool:
    return any(key in row for key in ["title", "新闻标题", "content"]) and any(
        key in row for key in ["description", "summary", "url", "published_at", "date"]
    )


def _is_market_temperature(row: dict[str, Any]) -> bool:
    return "temperature" in row and ("valuation" in row or "sentiment" in row)


def _is_relevant_news(title: str, summary: str) -> bool:
    if is_market_relevant_news(title, summary):
        return True
    text = f"{title} {summary}".upper()
    english_keywords = [
        "A-SHARE",
        "A SHARE",
        "STAR 50",
        "SEMICONDUCTOR",
        "HANG SENG",
        "ETF",
        "NORTHBOUND",
        "TURNOVER",
        "CHINA",
        "CHINESE",
        "ROBOTS",
        "ROBOT",
        "AI",
        "CHIP",
    ]
    return any(keyword in text for keyword in english_keywords)


def _dedupe_payloads(items: Any) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        key = _dedupe_key(item)
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _dedupe_key(item: dict[str, Any]) -> str:
    return str(item.get("url") or _normalize_title(str(item.get("title") or ""))).strip()


def _normalize_title(title: str) -> str:
    return re.sub(r"\s+", "", title.strip().lower())


def _source_name(source: str, kind: str) -> str:
    return f"{source}.{kind}"


def _market_code(value: Any) -> str:
    raw = str(value or "").strip().lower()
    return {"cn": "cn", "hk": "hk", "us": "us", "sg": "sg"}.get(raw, raw)


def _symbols_from_row(row: dict[str, Any]) -> list[str]:
    raw = row.get("related_symbols") or row.get("symbols") or row.get("codes") or []
    if isinstance(raw, str):
        return [item for item in re.findall(r"\d{5,6}|[A-Z]{1,6}\.(?:US|HK|SH|SZ)", raw) if item]
    if isinstance(raw, list):
        symbols: list[str] = []
        for item in raw:
            if isinstance(item, dict):
                value = item.get("symbol") or item.get("code")
            else:
                value = item
            if value not in {None, ""}:
                symbols.append(str(value))
        return symbols
    return []


def _text(row: Any, *keys: str) -> str:
    if not isinstance(row, dict):
        return ""
    for key in keys:
        value = row.get(key)
        if value not in {None, ""}:
            return str(value).strip()
    return ""


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _read_snapshot(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Import MCP market news/events into the StockTS TDX snapshot."
    )
    parser.add_argument("--snapshot", default="data/imports/tdx_snapshots.json")
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument("--limit", type=int, default=80)
    parser.add_argument("inputs", nargs="+", help="JSON files exported from MCP tools")
    args = parser.parse_args(argv)
    summary = import_market_intelligence(
        args.snapshot,
        [Path(item) for item in args.inputs],
        source=args.source,
        limit=args.limit,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
