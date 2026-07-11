from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from stock_ts.models import (
    CandidateStockRawData,
    DailyBar,
    IndexQuote,
    LimitDownStock,
    MarketRawData,
    NewsItem,
    SectorRawData,
    StockRawData,
)
from stock_ts.providers.base import DataProviderError, StockDataProvider
from stock_ts.sector_labels import localize_theme_name


class TdxSnapshotProvider(StockDataProvider):
    """Read TDX MCP/exported snapshots from local JSON without sample fallbacks."""

    def __init__(self, snapshot_path: str | Path | None = None) -> None:
        self.snapshot_path = Path(
            snapshot_path
            or os.getenv("STOCK_TS_TDX_SNAPSHOT_PATH")
            or "data/imports/tdx_snapshots.json"
        )
        self._payload_cache: dict[str, Any] | None = None

    def fetch_stock(self, code: str) -> StockRawData:
        normalized = code.strip()
        payload = self._read_payload()
        stock_payload = payload.get("stocks", {}).get(normalized)
        if not isinstance(stock_payload, dict):
            stock_payload = _candidate_stock_payload(payload, normalized)
        if not isinstance(stock_payload, dict):
            raise DataProviderError(
                f"TDX snapshot missing stock {normalized}: {self.snapshot_path}"
            )
        bars = [_bar_from_dict(item) for item in stock_payload.get("bars", [])]
        if not bars:
            raise DataProviderError(
                f"TDX snapshot stock {normalized} has no bars: {self.snapshot_path}"
            )
        return StockRawData(
            code=normalized,
            name=str(stock_payload.get("name") or normalized),
            bars=bars,
            fund_flow=_optional_float(stock_payload.get("fund_flow")),
            pe_ttm=_optional_float(stock_payload.get("pe_ttm")),
            valuation=_dict_from_payload(stock_payload.get("valuation")),
            fundamental_metrics=_dict_from_payload(stock_payload.get("fundamental_metrics")),
            fund_flow_detail=_dict_from_payload(stock_payload.get("fund_flow_detail")),
            news_items=[
                _news_from_dict(item) for item in _as_list(stock_payload.get("news_items"))
            ],
            announcements=[
                item
                for item in (
                    _dict_object_from_payload(row)
                    for row in _as_list(stock_payload.get("announcements"))
                )
                if item
            ],
            data_sources=[
                str(item) for item in _as_list(stock_payload.get("data_sources")) if item
            ],
        )

    def fetch_market(self) -> MarketRawData:
        payload = self._read_payload()
        market_payload = payload.get("market")
        if not isinstance(market_payload, dict):
            raise DataProviderError(f"TDX snapshot missing market data: {self.snapshot_path}")
        explicit_limit_down_payload = _limit_down_payload(market_payload)
        limit_down_details = [
            item
            for item in (_limit_down_from_dict(item) for item in explicit_limit_down_payload)
            if _is_valid_limit_down_detail(item)
        ]
        has_explicit_limit_down_payload = bool(explicit_limit_down_payload)
        if not has_explicit_limit_down_payload:
            limit_down_details = _computed_limit_down_details(payload)
        limit_down = (
            len(limit_down_details)
            if has_explicit_limit_down_payload or limit_down_details
            else int(market_payload.get("limit_down", 0))
        )
        advancing = int(market_payload.get("advancing", 0))
        declining = int(market_payload.get("declining", 0))
        unchanged = _market_unchanged_count(
            market_payload,
            payload=payload,
            advancing=advancing,
            declining=declining,
        )
        return MarketRawData(
            trade_date=str(market_payload.get("trade_date") or "latest"),
            indices=[_index_from_dict(item) for item in _as_list(market_payload.get("indices"))],
            advancing=advancing,
            declining=declining,
            limit_up=int(market_payload.get("limit_up", 0)),
            limit_down=limit_down,
            unchanged=unchanged,
            top_sectors=[
                (localize_theme_name(item[0]), float(item[1]))
                for item in _as_list(market_payload.get("top_sectors"))
                if isinstance(item, (list, tuple)) and len(item) >= 2
            ],
            northbound_net_inflow=_optional_float(market_payload.get("northbound_net_inflow")),
            limit_down_details=limit_down_details,
        )

    def fetch_sectors(self) -> list[SectorRawData]:
        payload = self._read_payload()
        sectors_payload = payload.get("sectors")
        if isinstance(sectors_payload, dict):
            sectors_payload = sectors_payload.get("sectors")
        sectors = [_sector_from_dict(item) for item in _as_list(sectors_payload)]
        if not sectors:
            raise DataProviderError(f"TDX snapshot missing sector data: {self.snapshot_path}")
        return sectors

    def fetch_candidate_universe(self) -> list[CandidateStockRawData]:
        payload = self._read_payload()
        universe_payload = payload.get("candidate_universe", payload.get("candidates"))
        if isinstance(universe_payload, dict):
            universe_payload = universe_payload.get("items")
        candidates = [_candidate_from_dict(item) for item in _as_list(universe_payload)]
        if not candidates:
            raise DataProviderError(
                f"TDX snapshot missing candidate universe: {self.snapshot_path}"
            )
        return candidates

    def fetch_market_news(self) -> list[NewsItem]:
        payload = self._read_payload()
        return [
            _news_from_dict(item)
            for item in _as_list(payload.get("market_news"))
            if isinstance(item, dict)
        ]

    def fetch_candidate_universe_metadata(self) -> dict[str, str]:
        payload = self._read_payload()
        universe_payload = payload.get("candidate_universe", payload.get("candidates"))
        if not isinstance(universe_payload, dict):
            universe_payload = {}
        keys = [
            "scope",
            "trade_date",
            "scanned_count",
            "prefiltered_count",
            "returned_count",
            "bar_source",
            "enriched_count",
            "enrichment_status",
            "enrichment_method",
            "enriched_at",
            "selection_method",
            "source",
            "generated_at",
        ]
        metadata = {
            key: str(universe_payload[key])
            for key in keys
            if universe_payload.get(key) not in {None, ""}
        }
        if payload.get("source") not in {None, ""}:
            metadata["snapshot_source"] = str(payload["source"])
        if payload.get("generated_at") not in {None, ""}:
            metadata["snapshot_generated_at"] = str(payload["generated_at"])
        for section_name, prefix in [
            ("kline_refresh", "kline_refresh"),
            ("holding_kline_refresh", "holding_kline_refresh"),
            ("external_enrichment", "external_enrichment"),
            ("manual_context_refresh", "manual_context_refresh"),
            ("mcp_market_news_refresh", "mcp_market_news_refresh"),
        ]:
            section = payload.get(section_name)
            if not isinstance(section, dict):
                continue
            if section.get("source") not in {None, ""}:
                metadata[f"{prefix}_source"] = str(section["source"])
            if section.get("generated_at") not in {None, ""}:
                metadata[f"{prefix}_generated_at"] = str(section["generated_at"])
            for count_key in [
                "updated_count",
                "failed_count",
                "requested_count",
                "enriched_stock_count",
                "error_count",
                "imported_count",
                "skipped_count",
                "total_market_news_count",
            ]:
                if section.get(count_key) not in {None, ""}:
                    metadata[f"{prefix}_{count_key}"] = str(section[count_key])
        return metadata

    def _read_payload(self) -> dict[str, Any]:
        if self._payload_cache is not None:
            return self._payload_cache
        if not self.snapshot_path.exists():
            raise DataProviderError(f"TDX snapshot file not found: {self.snapshot_path}")
        self._payload_cache = json.loads(self.snapshot_path.read_text(encoding="utf-8"))
        return self._payload_cache


def _bar_from_dict(item: object) -> DailyBar:
    if not isinstance(item, dict):
        raise DataProviderError("TDX snapshot bar must be an object")
    return DailyBar(
        date=str(item["date"]),
        open=float(item["open"]),
        high=float(item["high"]),
        low=float(item["low"]),
        close=float(item["close"]),
        volume=float(item.get("volume", item.get("vol", 0.0))),
    )


def _index_from_dict(item: object) -> IndexQuote:
    if not isinstance(item, dict):
        raise DataProviderError("TDX snapshot index must be an object")
    return IndexQuote(
        code=str(item.get("code") or ""),
        name=str(item.get("name") or item.get("code") or ""),
        close=float(item.get("close", 0.0)),
        pct_chg=float(item.get("pct_chg", 0.0)),
        amount=float(item.get("amount", 0.0)),
    )


def _limit_down_payload(market_payload: dict[str, Any]) -> list[Any]:
    for key in ("limit_down_details", "limit_down_stocks", "limit_downs"):
        items = _as_list(market_payload.get(key))
        if items:
            return items
    return []


def _market_unchanged_count(
    market_payload: dict[str, Any],
    *,
    payload: dict[str, Any],
    advancing: int,
    declining: int,
) -> int:
    explicit = market_payload.get("unchanged", market_payload.get("flat"))
    if explicit not in {None, ""}:
        return max(0, int(float(explicit)))
    universe_payload = payload.get("candidate_universe", payload.get("candidates"))
    if isinstance(universe_payload, dict):
        total = universe_payload.get("scanned_count") or universe_payload.get("total_count")
        if total not in {None, ""}:
            return max(0, int(float(total)) - advancing - declining)
    return 0


def _limit_down_from_dict(item: object) -> LimitDownStock:
    if not isinstance(item, dict):
        raise DataProviderError("TDX snapshot limit-down detail must be an object")
    return LimitDownStock(
        code=str(item.get("code") or item.get("symbol") or ""),
        name=str(item.get("name") or item.get("code") or ""),
        sector=localize_theme_name(item.get("sector") or item.get("theme") or item.get("board")),
        latest_close=float(
            item.get("latest_close", item.get("close", item.get("last_price", 0.0)))
        ),
        pct_chg=float(item.get("pct_chg", item.get("pct_change", item.get("change_pct", 0.0)))),
        reason=str(item.get("reason") or item.get("risk_reason") or item.get("tag") or ""),
    )


def _is_valid_limit_down_detail(item: LimitDownStock) -> bool:
    return item.latest_close > 0 and item.pct_chg <= -9.8


def _computed_limit_down_details(payload: dict[str, Any]) -> list[LimitDownStock]:
    rows: dict[str, LimitDownStock] = {}
    for item in _stock_like_payloads(payload):
        detail = _limit_down_from_bars(item)
        if detail is not None and detail.code:
            rows[detail.code] = detail
    return sorted(rows.values(), key=lambda item: item.pct_chg)


def _stock_like_payloads(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    stocks = payload.get("stocks")
    if isinstance(stocks, dict):
        rows.extend(dict(item) for item in stocks.values() if isinstance(item, dict))
    universe_payload = payload.get("candidate_universe", payload.get("candidates"))
    if isinstance(universe_payload, dict):
        universe_payload = universe_payload.get("items")
    rows.extend(dict(item) for item in _as_list(universe_payload) if isinstance(item, dict))
    return rows


def _limit_down_from_bars(item: dict[str, Any]) -> LimitDownStock | None:
    bars_payload = _as_list(item.get("bars"))
    if len(bars_payload) < 2:
        return None
    try:
        previous = _bar_from_dict(bars_payload[-2])
        latest = _bar_from_dict(bars_payload[-1])
    except (KeyError, TypeError, ValueError, DataProviderError):
        return None
    if previous.close <= 0 or latest.close <= 0:
        return None
    pct_chg = round((latest.close - previous.close) / previous.close * 100, 2)
    if pct_chg > -9.8:
        return None
    return LimitDownStock(
        code=str(item.get("code") or item.get("symbol") or ""),
        name=str(item.get("name") or item.get("code") or ""),
        sector=localize_theme_name(item.get("sector") or item.get("theme") or item.get("board")),
        latest_close=latest.close,
        pct_chg=pct_chg,
        reason=_computed_limit_down_reason(pct_chg),
    )


def _computed_limit_down_reason(pct_chg: float) -> str:
    if pct_chg <= -19.5:
        return "20cm 跌停或极端下跌"
    return "10cm 跌停或大幅下跌"


def _sector_from_dict(item: object) -> SectorRawData:
    if not isinstance(item, dict):
        raise DataProviderError("TDX snapshot sector must be an object")
    return SectorRawData(
        name=localize_theme_name(item.get("name")),
        pct_chg=float(item.get("pct_chg", 0.0)),
        advancing_ratio=float(item.get("advancing_ratio", 0.0)),
        amount_change=float(item.get("amount_change", 0.0)),
        fund_flow=_optional_float(item.get("fund_flow")),
        consecutive_days=int(item.get("consecutive_days", 1)),
        limit_up_count=int(item.get("limit_up_count", 0)),
        high_divergence=bool(item.get("high_divergence", False)),
    )


def _candidate_from_dict(item: object) -> CandidateStockRawData:
    if not isinstance(item, dict):
        raise DataProviderError("TDX snapshot candidate must be an object")
    bars = [_bar_from_dict(bar) for bar in _as_list(item.get("bars"))]
    if not bars:
        raise DataProviderError("TDX snapshot candidate has no bars")
    price_reliable = bool(item.get("price_reliable", _bars_have_explicit_dates(bars)))
    return CandidateStockRawData(
        code=str(item.get("code") or ""),
        name=str(item.get("name") or item.get("code") or ""),
        sector=localize_theme_name(item.get("sector")),
        bars=bars,
        fund_flow=_optional_float(item.get("fund_flow")),
        turnover_rate=float(item.get("turnover_rate", 0.0)),
        amount=float(item.get("amount", 0.0)),
        pe_ttm=_optional_float(item.get("pe_ttm")),
        price_reliable=price_reliable,
    )


def _candidate_stock_payload(payload: dict[str, Any], code: str) -> dict[str, Any] | None:
    universe_payload = payload.get("candidate_universe", payload.get("candidates"))
    if isinstance(universe_payload, dict):
        universe_payload = universe_payload.get("items")
    for item in _as_list(universe_payload):
        if isinstance(item, dict) and str(item.get("code") or "").strip() == code:
            return item
    return None


def _news_from_dict(item: object) -> NewsItem:
    if not isinstance(item, dict):
        return NewsItem(date="", source="", title="", summary="")
    return NewsItem(
        date=str(item.get("date") or item.get("发布时间") or ""),
        source=str(item.get("source") or item.get("文章来源") or ""),
        title=str(item.get("title") or item.get("新闻标题") or ""),
        summary=str(item.get("summary") or item.get("新闻内容") or ""),
        url=str(item.get("url") or item.get("新闻链接") or ""),
        sentiment=str(item.get("sentiment") or "neutral"),
    )


def _dict_from_payload(value: object) -> dict[str, float | str | None]:
    if not isinstance(value, dict):
        return {}
    return {
        str(key): item if isinstance(item, (int, float)) or item is None else str(item)
        for key, item in value.items()
    }


def _dict_object_from_payload(value: object) -> dict[str, object]:
    return dict(value) if isinstance(value, dict) else {}


def _as_list(value: object) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def _optional_float(value: object) -> float | None:
    if value in {None, ""}:
        return None
    return float(value)


def _bars_have_explicit_dates(bars: list[DailyBar]) -> bool:
    if len(bars) < 2:
        return False
    for bar in bars[-2:]:
        date = bar.date.strip()
        if date.startswith("latest") or len(date) < 10:
            return False
    return True
