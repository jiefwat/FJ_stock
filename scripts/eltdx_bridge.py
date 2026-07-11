#!/usr/bin/env python3.11
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from typing import Any

from eltdx import TdxClient, to_jsonable

EXCHANGE_BOARD_NAMES = {
    "sse_star_market",
    "szse_chinext",
    "sse_main_board",
    "szse_main_board",
    "bse_listed_stock",
    "科创板",
    "创业板",
    "沪市主板",
    "深市主板",
    "主板",
    "北交所",
    "沪深A股",
}
NON_THEME_TOPIC_NAMES = {
    "近期强势",
    "近期弱势",
    "最近情绪指数",
    "昨日上榜",
    "昨日首板",
    "昨日涨停",
    "昨日连板",
    "今日涨停",
    "密集调研",
    "拟减持",
    "绩优股",
    "社保重仓",
    "保险重仓",
    "养老金持股",
    "股权激励",
    "两年新股",
    "非周期股",
    "人民币贬值受益",
    "含可转债",
    "次新股",
}


def main() -> int:
    if len(sys.argv) < 2:
        raise SystemExit("missing operation")
    op = sys.argv[1]
    payload = json.loads(sys.stdin.read() or "{}")
    timeout = float(payload.get("timeout", 8.0))
    with TdxClient(timeout=timeout) as client:
        if op == "market":
            result = build_market_snapshot(client, payload)
        elif op == "stock":
            result = build_stock_snapshot(client, payload)
        elif op == "candidate_universe":
            result = build_candidate_universe(client, payload)
        elif op == "candidate_enrichment":
            result = build_candidate_enrichment(client, payload)
        elif op == "sectors":
            result = build_sector_snapshot(client, payload)
        else:
            raise SystemExit(f"unknown operation: {op}")
    json.dump(result, sys.stdout, ensure_ascii=False)
    return 0


def build_market_snapshot(client: TdxClient, payload: dict[str, Any]) -> dict[str, Any]:
    codes = client.get_a_share_codes_all()
    quote_rows = _quote_rows(client, codes)
    index_rows, trade_date = _index_rows(client)
    index_map = {str(row.get("code", "")): row for row in index_rows}
    index_order = ["000001", "399001", "399006"]
    latest_rows = sorted(quote_rows, key=_change_pct, reverse=True)
    sector_rows = _aggregate_sector_rows(
        client,
        latest_rows[:12],
        sector_limit=int(payload.get("sector_limit", 10)),
    )
    valid_quote_rows = [row for row in quote_rows if _has_valid_trade_price(row)]
    advancing = sum(1 for row in valid_quote_rows if _change_pct(row) > 0)
    declining = sum(1 for row in valid_quote_rows if _change_pct(row) < 0)
    limit_up = sum(1 for row in valid_quote_rows if _change_pct(row) >= 9.8)
    limit_down = sum(1 for row in valid_quote_rows if _change_pct(row) <= -9.8)
    limit_down_rows = sorted(
        [row for row in valid_quote_rows if _change_pct(row) <= -9.8],
        key=_change_pct,
    )[: int(payload.get("limit_down_detail_limit", 50))]
    return {
        "trade_date": trade_date,
        "indices": [
            {
                "code": code,
                "name": _index_name(code),
                "close": float(index_map.get(code, {}).get("last_price", 0.0)),
                "pct_chg": _change_pct(index_map.get(code, {})),
                "amount": float(index_map.get(code, {}).get("amount", 0.0)) / 100000000,
            }
            for code in index_order
        ],
        "advancing": advancing,
        "declining": declining,
        "limit_up": limit_up,
        "limit_down": limit_down,
        "limit_down_details": [
            _limit_down_detail_from_quote_row(row) for row in limit_down_rows
        ],
        "top_sectors": sector_rows,
        "northbound_net_inflow": None,
    }


def build_stock_snapshot(client: TdxClient, payload: dict[str, Any]) -> dict[str, Any]:
    code = str(payload["code"]).strip()
    profile = _single_profile(client, [code])
    row = profile["rows"][0]
    kline = to_jsonable(client.get_kline(code, "day", count=int(payload.get("bar_count", 80))))
    bars = [_simplify_bar(bar) for bar in kline.get("bars", [])]
    if not bars:
        bars = _synthetic_bars(float(row.get("last_price", 0.0)), _change_pct(row))
    return {
        "code": code,
        "name": row.get("name") or code,
        "bars": bars,
        "fund_flow": None,
        "pe_ttm": None,
    }


def build_candidate_universe(client: TdxClient, payload: dict[str, Any]) -> dict[str, Any]:
    codes = client.get_a_share_codes_all()
    quote_rows = _quote_rows(client, codes)
    ranked_rows = sorted(quote_rows, key=_change_pct, reverse=True)
    limit = int(payload.get("limit", 120))
    trade_date = _trade_date_from_kline(client, "sh000001", kind="index")
    if bool(payload.get("quote_only", False)):
        rows = ranked_rows[:limit]
        return {
            "trade_date": trade_date,
            "scope": "all_a_share",
            "scanned_count": len(quote_rows),
            "prefiltered_count": len(rows),
            "returned_count": len(rows),
            "bar_source": "tdx_quote_preclose",
            "selection_method": "全市场行情分页扫描后，按最新涨跌幅生成行情截面预筛候选。",
            "items": [_candidate_from_quote_row(row, trade_date) for row in rows],
        }
    rows = ranked_rows[: max(limit * 4, 80)]
    profiles = _single_profile(
        client,
        [str(row.get("full_code") or row.get("code")) for row in rows],
    )
    profile_map = {row.get("code"): row for row in profiles["rows"]}
    items = []
    bar_count = int(payload.get("bar_count", 20))
    for row in rows:
        if len(items) >= limit:
            break
        code = str(row.get("code", ""))
        profile = profile_map.get(code, {})
        bars = _stock_bars(client, code, count=bar_count)
        if len(bars) < 2:
            continue
        topic = _primary_topic_name(client, code, fallback=row.get("board") or "沪深A股")
        if _is_exchange_board_name(topic):
            topic = "未识别主题"
        items.append(
            {
                "code": code,
                "name": profile.get("name") or row.get("name") or code,
                "sector": topic,
                "bars": bars,
                "fund_flow": None,
                "turnover_rate": float(profile.get("turnover_rate") or 0.0),
                "amount": float(row.get("amount", 0.0)) / 100000000,
                "pe_ttm": None,
            }
        )
    return {
        "trade_date": trade_date,
        "scope": "all_a_share",
        "scanned_count": len(quote_rows),
        "prefiltered_count": len(rows),
        "returned_count": len(items),
        "selection_method": "全市场行情分页扫描后，按涨跌幅预筛，再为候选补真实日线和主题。",
        "items": items,
    }


def build_candidate_enrichment(client: TdxClient, payload: dict[str, Any]) -> dict[str, Any]:
    source_items = [
        item for item in payload.get("items", []) if isinstance(item, dict) and item.get("code")
    ]
    bar_count = int(payload.get("bar_count", 20))
    codes = [str(item.get("code")).strip() for item in source_items]
    try:
        profiles = _single_profile(client, codes) if codes else {"rows": []}
    except Exception:
        profiles = {"rows": []}
    profile_map = {str(row.get("code") or ""): row for row in profiles["rows"]}
    enriched_items: list[dict[str, Any]] = []
    for item in source_items:
        code = str(item.get("code") or "").strip()
        if not code:
            continue
        bars = _stock_bars(client, code, count=bar_count)
        if not bars:
            continue
        profile = profile_map.get(code, {})
        fallback_topic = str(item.get("sector") or profile.get("board") or "未识别主题")
        topic = _primary_topic_name(client, code, fallback=fallback_topic)
        if _is_exchange_board_name(topic):
            topic = "未识别主题"
        enriched_items.append(
            {
                **item,
                "code": code,
                "name": profile.get("name") or item.get("name") or code,
                "sector": topic,
                "bars": bars,
                "turnover_rate": float(
                    profile.get("turnover_rate") or item.get("turnover_rate") or 0.0
                ),
                "bar_source": "tdx_daily",
                "price_reliable": True,
            }
        )
    return {
        "enriched_count": len(enriched_items),
        "enrichment_method": "按现有候选代码批量补真实日线和主题。",
        "items": enriched_items,
    }


def build_sector_snapshot(client: TdxClient, payload: dict[str, Any]) -> dict[str, Any]:
    codes = client.get_a_share_codes_all()
    quote_rows = _quote_rows(client, codes)
    ranked_rows = sorted(quote_rows, key=_change_pct, reverse=True)
    sector_limit = int(payload.get("limit", 10))
    aggregated = _aggregate_sector_rows(client, ranked_rows[:20], sector_limit=sector_limit)
    return {
        "trade_date": _trade_date_from_kline(client, "sh000001", kind="index"),
        "sectors": [
            {
                "name": item[0],
                "pct_chg": item[1],
                "advancing_ratio": item[2],
                "amount_change": item[3],
                "fund_flow": None,
                "consecutive_days": 1,
                "limit_up_count": item[4],
                "high_divergence": item[5],
            }
            for item in aggregated
        ],
    }


def _quote_rows(client: TdxClient, codes: list[str]) -> list[dict[str, Any]]:
    table = to_jsonable(client.helpers.quote_table(codes))
    return list(table.get("rows", []))


def _single_profile(
    client: TdxClient,
    codes: list[str],
    *,
    batch_size: int = 80,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    size = max(1, batch_size)
    for start in range(0, len(codes), size):
        batch = codes[start : start + size]
        table = to_jsonable(
            client.helpers.stock_profile_table(
                batch,
                include_security=True,
                include_finance=False,
            )
        )
        rows.extend(list(table.get("rows", [])))
    return {"rows": rows}


def _candidate_from_quote_row(row: dict[str, Any], trade_date: str) -> dict[str, Any]:
    close = float(row.get("last_price", 0.0))
    pre_close = float(row.get("pre_close_price", 0.0))
    if pre_close <= 0:
        pre_close = close
    code = str(row.get("code", ""))
    topic = str(row.get("board") or "").strip()
    if _is_exchange_board_name(topic):
        topic = "未识别主题"
    return {
        "code": code,
        "name": row.get("name") or code,
        "sector": topic or "未识别主题",
        "bars": [
            {
                "date": f"{trade_date}-pre",
                "open": pre_close,
                "high": pre_close,
                "low": pre_close,
                "close": pre_close,
                "volume": 0.0,
            },
            {
                "date": trade_date,
                "open": float(row.get("open", close)),
                "high": float(row.get("high", close)),
                "low": float(row.get("low", close)),
                "close": close,
                "volume": float(row.get("vol", 0.0)),
            },
        ],
        "fund_flow": None,
        "turnover_rate": float(row.get("turnover") or row.get("turnover_rate") or 0.0),
        "amount": float(row.get("amount", 0.0)) / 100000000,
        "pe_ttm": None,
        "price_reliable": True,
    }


def _index_rows(client: TdxClient) -> tuple[list[dict[str, Any]], str]:
    index_codes = ["sh000001", "sz399001", "sz399006"]
    rows = _quote_rows(client, index_codes)
    trade_date = _trade_date_from_kline(client, "sh000001", kind="index")
    return rows, trade_date


def _index_name(code: str) -> str:
    return {
        "000001": "上证指数",
        "399001": "深证成指",
        "399006": "创业板指",
    }.get(code, code)


def _trade_date_from_kline(client: TdxClient, code: str, *, kind: str) -> str:
    kline = to_jsonable(client.get_kline(code, "day", count=1, kind=kind))
    bars = kline.get("bars", [])
    if not bars:
        return "latest"
    raw = str(bars[-1].get("time", ""))
    if len(raw) >= 10:
        return raw[:10]
    return "latest"


def _stock_bars(
    client: TdxClient,
    code: str,
    *,
    count: int,
) -> list[dict[str, Any]]:
    try:
        kline = to_jsonable(client.get_kline(code, "day", count=count))
    except Exception:
        kline = {}
    return [_simplify_bar(bar) for bar in kline.get("bars", [])]


def _change_pct(row: dict[str, Any]) -> float:
    close = float(row.get("last_price", 0.0))
    pre_close = float(row.get("pre_close_price", 0.0))
    if close <= 0 or pre_close <= 0:
        return 0.0
    return (close - pre_close) / pre_close * 100


def _has_valid_trade_price(row: dict[str, Any]) -> bool:
    return float(row.get("last_price", 0.0) or 0.0) > 0 and float(
        row.get("pre_close_price", 0.0) or 0.0
    ) > 0


def _simplify_bar(bar: dict[str, Any]) -> dict[str, Any]:
    time = str(bar.get("time", ""))
    return {
        "date": time[:10] if len(time) >= 10 else time,
        "open": float(bar.get("open", 0.0)),
        "high": float(bar.get("high", 0.0)),
        "low": float(bar.get("low", 0.0)),
        "close": float(bar.get("close", 0.0)),
        "volume": float(bar.get("volume_wire_value") or bar.get("volume", 0.0)),
    }


def _synthetic_bars(
    latest_close: float,
    pct_change: float,
    count: int = 10,
) -> list[dict[str, Any]]:
    previous = latest_close / (1 + pct_change / 100) if pct_change != -100 else latest_close
    bars = []
    total = max(count - 1, 1)
    for index in range(count):
        weight = index / total
        close = previous * (1 - weight) + latest_close * weight
        bars.append(
            {
                "date": f"latest-{count - 1 - index}",
                "open": close * 0.995,
                "high": close * 1.012,
                "low": close * 0.988,
                "close": close,
                "volume": 1000 + index * 100,
            }
        )
    return bars


def _primary_topic_name(client: TdxClient, code: str, *, fallback: str) -> str:
    try:
        topics = to_jsonable(client.helpers.stock_topics(code)).get("topics", [])
    except Exception:
        return fallback
    if not topics:
        return fallback
    return _select_primary_topic_name(topics, fallback=fallback)


def _select_primary_topic_name(topics: list[dict[str, Any]], *, fallback: str) -> str:
    ranked: list[tuple[tuple[int, float, int], str]] = []
    for index, topic in enumerate(topics):
        name = str(topic.get("topic_name") or "").strip()
        if not name or _is_exchange_board_name(name) or _is_non_theme_topic_name(name):
            continue
        category = topic.get("category_raw")
        category_score = 2 if category == 2 else 1 if category is None else 0
        if category_score <= 0:
            continue
        relation = float(topic.get("relation_level") or 0.0)
        ranked.append(((category_score, relation, -index), name))
    if not ranked:
        return fallback
    ranked.sort(reverse=True)
    return ranked[0][1]


def _is_exchange_board_name(name: object) -> bool:
    return str(name or "").strip() in EXCHANGE_BOARD_NAMES


def _is_non_theme_topic_name(name: object) -> bool:
    value = str(name or "").strip()
    if value in NON_THEME_TOPIC_NAMES:
        return True
    return re.fullmatch(r"通达信\d+", value) is not None


def _aggregate_sector_rows(
    client: TdxClient,
    rows: list[dict[str, Any]],
    *,
    sector_limit: int,
) -> list[list[Any]]:
    buckets: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "count": 0,
            "pct_sum": 0.0,
            "amount_sum": 0.0,
            "positive": 0,
            "limit_up": 0,
            "hot": False,
            "abnormal": False,
        }
    )
    for row in rows:
        code = str(row.get("code", ""))
        raw_pct_change = _change_pct(row)
        pct_change = _sector_sample_pct(raw_pct_change)
        topic = _primary_topic_name(client, code, fallback=str(row.get("board") or "沪深A股"))
        if _is_exchange_board_name(topic):
            continue
        bucket = buckets[topic]
        bucket["count"] += 1
        bucket["pct_sum"] += pct_change
        bucket["amount_sum"] += float(row.get("amount", 0.0)) / 100000000
        bucket["positive"] += 1 if pct_change > 0 else 0
        bucket["limit_up"] += 1 if pct_change >= 9.8 else 0
        bucket["hot"] = bucket["hot"] or pct_change >= 6
        bucket["abnormal"] = bucket["abnormal"] or pct_change != raw_pct_change
    ranked = sorted(
        buckets.items(),
        key=lambda item: (
            item[1]["count"],
            item[1]["pct_sum"] / max(item[1]["count"], 1),
        ),
        reverse=True,
    )
    top_items: list[list[Any]] = []
    for name, data in ranked[:sector_limit]:
        count = max(int(data["count"]), 1)
        top_items.append(
            [
                name,
                round(float(data["pct_sum"]) / count, 2),
                round(float(data["positive"]) / count, 2),
                round(float(data["amount_sum"]) / count, 2),
                int(data["limit_up"]),
                bool(data["hot"] or data["abnormal"]),
            ]
        )
    return top_items


def _sector_sample_pct(pct_change: float) -> float:
    if abs(pct_change) > 20.5:
        return 0.0
    return pct_change


def _limit_down_detail_from_quote_row(row: dict[str, Any]) -> dict[str, Any]:
    pct_change = _change_pct(row)
    return {
        "code": str(row.get("code") or row.get("full_code") or ""),
        "name": str(row.get("name") or row.get("code") or ""),
        "sector": str(row.get("board") or "未识别主题"),
        "latest_close": float(row.get("last_price", 0.0)),
        "pct_chg": pct_change,
        "reason": _limit_down_reason(pct_change),
    }


def _limit_down_reason(pct_change: float) -> str:
    if pct_change <= -19.5:
        return "20cm 跌停或极端退潮"
    if pct_change <= -9.8:
        return "跌停封板风险"
    return "大幅下跌"


if __name__ == "__main__":
    raise SystemExit(main())
