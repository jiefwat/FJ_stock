from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import Candidate, IndexQuote, MarketSnapshot, NewsItem, SectorPulse


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


def _integer(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _text(value: Any, default: str = "") -> str:
    return value.strip() if isinstance(value, str) else default


def _items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _latest_bar(item: dict[str, Any], stocks: dict[str, Any]) -> tuple[float, float]:
    code = _text(item.get("code"))
    bars = _items(item.get("bars"))
    if not bars and code:
        stock = stocks.get(code, {})
        bars = _items(stock.get("bars")) if isinstance(stock, dict) else []
    if not bars:
        return 0.0, 0.0

    latest = bars[-1]
    latest_price = _number(latest.get("close"))
    pct_change = _number(latest.get("pct_chg"))
    if "pct_chg" not in latest and len(bars) > 1:
        previous = _number(bars[-2].get("close"))
        if previous:
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
    raw_stocks = payload.get("stocks", {})
    stocks = raw_stocks if isinstance(raw_stocks, dict) else {}
    candidates = []
    divergent_sectors = {sector.name for sector in sectors if sector.high_divergence}
    for item in _items(universe.get("items")):
        code = _text(item.get("code"))
        if not code:
            continue
        sector = _text(item.get("sector"), "待分类")
        latest_price, pct_change = _latest_bar(item, stocks)
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
        northbound_net_inflow=_number(market.get("northbound_net_inflow")),
        sectors=sectors,
        candidates=tuple(candidates),
        news=news,
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
