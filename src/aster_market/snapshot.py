from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import (
    Candidate,
    FlowSnapshot,
    IndexQuote,
    MarketSnapshot,
    NewsItem,
    PriceBar,
    SectorPulse,
    StockProfile,
    ValuationSnapshot,
)


@dataclass(frozen=True)
class SnapshotResult:
    status: str
    message: str
    snapshot: MarketSnapshot | None


def _number(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _optional_number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _integer(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _text(value: Any, default: str = "") -> str:
    if not isinstance(value, str):
        return default
    normalized = value.strip()
    return normalized or default


def _items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _parse_bars(value: Any) -> tuple[PriceBar, ...]:
    bars = []
    for item in _items(value):
        close = _optional_number(item.get("close"))
        date = _text(item.get("date"))
        if close is None or not date:
            continue
        bars.append(
            PriceBar(
                date=date,
                open=_optional_number(item.get("open")),
                high=_optional_number(item.get("high")),
                low=_optional_number(item.get("low")),
                close=close,
                volume=_optional_number(item.get("volume")),
                pct_change=_optional_number(item.get("pct_chg", item.get("pct_change"))),
            )
        )
    return tuple(sorted(bars, key=lambda bar: bar.date))


def _parse_events(value: Any) -> tuple[NewsItem, ...]:
    return tuple(
        NewsItem(
            published_at=_text(item.get("date", item.get("published_at"))),
            source=_text(item.get("source"), "来源未标注"),
            title=_text(item.get("title"), "未命名事件"),
            summary=_text(item.get("summary", item.get("content"))),
        )
        for item in _items(value)
    )


def _merge_stock_items(
    raw_stocks: dict[str, Any], candidate_items: list[dict[str, Any]]
) -> tuple[StockProfile, ...]:
    merged: dict[str, dict[str, Any]] = {
        str(code): dict(item)
        for code, item in raw_stocks.items()
        if isinstance(item, dict)
    }
    for candidate in candidate_items:
        code = _text(candidate.get("code"))
        if not code:
            continue
        base = merged.setdefault(code, {})
        for key in ("code", "name", "sector", "price_reliable", "bar_source"):
            if candidate.get(key) is not None:
                base[key] = candidate[key]
        candidate_bars = _items(candidate.get("bars"))
        base_bars = _items(base.get("bars"))
        if len(candidate_bars) > len(base_bars):
            base["bars"] = candidate_bars

    profiles = []
    for fallback_code, item in merged.items():
        code = _text(item.get("code"), fallback_code)
        bars = _parse_bars(item.get("bars"))
        if not code or not bars:
            continue
        raw_valuation = item.get("valuation", {})
        valuation = raw_valuation if isinstance(raw_valuation, dict) else {}
        raw_flow = item.get("fund_flow_detail", {})
        flow = raw_flow if isinstance(raw_flow, dict) else {}
        raw_quality = item.get("data_quality", {})
        quality = raw_quality if isinstance(raw_quality, dict) else {}
        missing_fields = quality.get("missing_fields", [])
        profiles.append(
            StockProfile(
                code=code,
                name=_text(item.get("name"), code),
                sector=_text(item.get("sector"), "待分类"),
                bars=bars,
                valuation=ValuationSnapshot(
                    pe_ttm=_optional_number(valuation.get("pe_ttm", item.get("pe_ttm"))),
                    pb=_optional_number(valuation.get("pb")),
                    ps=_optional_number(valuation.get("ps")),
                    total_market_value=_optional_number(valuation.get("total_mv")),
                ),
                flow=FlowSnapshot(
                    amount_yuan=_optional_number(flow.get("amount_yuan")),
                    turnover_rate=_optional_number(
                        flow.get("turnover_rate", item.get("turnover_rate"))
                    ),
                    inside_volume=_optional_number(flow.get("inside_dish_hand")),
                    outside_volume=_optional_number(flow.get("outer_disc_hand")),
                ),
                price_reliable=item.get("price_reliable") is not False,
                data_quality=_text(quality.get("data_quality"), "有限"),
                primary_source=_text(
                    quality.get("primary_source", item.get("bar_source")), "来源未标注"
                ),
                missing_fields=tuple(
                    _text(field) for field in missing_fields if isinstance(field, str)
                ),
                events=_parse_events(item.get("news_items")),
            )
        )
    return tuple(sorted(profiles, key=lambda stock: stock.code))


def _latest_bar(
    item: dict[str, Any], stocks: dict[str, Any]
) -> tuple[float | None, float | None]:
    code = _text(item.get("code"))
    bars = _items(item.get("bars"))
    if not bars and code:
        stock = stocks.get(code, {})
        bars = _items(stock.get("bars")) if isinstance(stock, dict) else []
    if not bars:
        return None, None

    latest = bars[-1]
    latest_price = _optional_number(latest.get("close"))
    pct_change = _optional_number(latest.get("pct_chg"))
    if "pct_chg" not in latest and len(bars) > 1:
        previous = _optional_number(bars[-2].get("close"))
        if latest_price is not None and previous:
            pct_change = (latest_price - previous) / previous * 100
    return latest_price, pct_change


def _parse_snapshot(payload: dict[str, Any]) -> MarketSnapshot:
    market = payload.get("market")
    if not isinstance(market, dict):
        raise ValueError("market must be an object")

    trade_date = _text(market.get("trade_date"))
    generated_at = _text(payload.get("generated_at"))
    if not trade_date or not generated_at:
        raise ValueError("trade_date and generated_at are required")

    indices = tuple(
        IndexQuote(
            name=_text(item.get("name"), "未命名指数"),
            code=_text(item.get("code")),
            value=_number(item.get("close", item.get("value"))),
            pct_change=_number(item.get("pct_chg", item.get("pct_change"))),
        )
        for item in _items(market.get("indices"))
    )

    sectors = tuple(
        SectorPulse(
            name=_text(item.get("name"), "未命名主题"),
            pct_change=_number(item.get("pct_chg", item.get("pct_change"))),
            advancing_ratio=_number(item.get("advancing_ratio")),
            amount_change=_number(item.get("amount_change")),
            consecutive_days=_integer(item.get("consecutive_days")),
            high_divergence=bool(item.get("high_divergence", False)),
        )
        for item in _items(payload.get("sectors"))
    )

    raw_universe = payload.get("candidate_universe", {})
    universe = raw_universe if isinstance(raw_universe, dict) else {}
    candidate_items = _items(universe.get("items"))
    raw_stocks = payload.get("stocks", {})
    stocks = raw_stocks if isinstance(raw_stocks, dict) else {}
    candidates = []
    divergent_sectors = {sector.name for sector in sectors if sector.high_divergence}
    for item in candidate_items:
        code = _text(item.get("code"))
        if not code:
            continue
        sector = _text(item.get("sector"), "待分类")
        latest_price, pct_change = _latest_bar(item, stocks)
        if latest_price is None:
            continue
        candidates.append(
            Candidate(
                code=code,
                name=_text(item.get("name"), code),
                sector=sector,
                pct_change=pct_change,
                latest_price=latest_price,
                reason=f"进入当日候选池 · {sector}",
                risk=(
                    "主题分歧较高，等待确认"
                    if sector in divergent_sectors
                    else "观察，不是买点"
                ),
            )
        )

    news = tuple(
        NewsItem(
            published_at=_text(item.get("date", item.get("published_at"))),
            source=_text(item.get("source"), "来源未标注"),
            title=_text(item.get("title"), "未命名事件"),
            summary=_text(item.get("summary")),
        )
        for item in _items(payload.get("market_news"))
    )

    return MarketSnapshot(
        trade_date=trade_date,
        generated_at=generated_at,
        source=_text(payload.get("source"), "未标注来源"),
        indices=indices,
        advancing=_integer(market.get("advancing")),
        declining=_integer(market.get("declining")),
        limit_up=_integer(market.get("limit_up")),
        limit_down=_integer(market.get("limit_down")),
        northbound_net_inflow=_optional_number(market.get("northbound_net_inflow")),
        sectors=sectors,
        candidates=tuple(candidates),
        news=news,
        stocks=_merge_stock_items(stocks, candidate_items),
    )


def load_snapshot(path: Path) -> SnapshotResult:
    if not path.is_file():
        return SnapshotResult("unavailable", f"行情快照不存在：{path}", None)

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("root must be an object")
        snapshot = _parse_snapshot(payload)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, TypeError):
        return SnapshotResult("unavailable", "行情快照格式无效，当前不展示市场数据", None)

    return SnapshotResult("ready", "行情快照已就绪", snapshot)
