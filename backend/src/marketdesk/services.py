from __future__ import annotations

import asyncio
from typing import Any, Literal, Protocol, cast

from marketdesk.analysis.events import analyse_market_events
from marketdesk.analysis.holding import analyse_holding
from marketdesk.analysis.market import analyse_market
from marketdesk.analysis.opportunities import rank_candidates
from marketdesk.analysis.sector import analyse_sector
from marketdesk.analysis.stock import analyse_stock
from marketdesk.config import Settings
from marketdesk.models import (
    EquityDataset,
    EquityPage,
    EquityQuote,
    HoldingDossier,
    HoldingItem,
    MarketEventRaw,
    MarketEventResult,
    MarketPayload,
    MarketSnapshot,
    MarketSummarySnapshot,
    OpportunityResult,
    SectorDossier,
    StockDossier,
)
from marketdesk.providers.public_market import PublicMarketProvider
from marketdesk.store import Store


class MarketProvider(Protocol):
    async def fetch_equities(self) -> EquityDataset: ...
    async def fetch_indices(self) -> list[Any]: ...
    async def fetch_sectors(self) -> list[Any]: ...
    async def fetch_sector_constituents(self, sector_code: str) -> list[Any]: ...
    async def fetch_research_enrichment(
        self, symbol: str, name: str, sector: str | None
    ) -> list[str]: ...
    async def fetch_market_events(self, limit: int = 50) -> list[MarketEventRaw]: ...
    async def fetch_kline(self, symbol: str, limit: int = 180) -> list[Any]: ...


class MarketService:
    def __init__(self, provider: MarketProvider | None = None, store: Store | None = None) -> None:
        settings = Settings()
        self.provider = provider or PublicMarketProvider()
        self.store = store or Store(settings.database_path)
        self._snapshot: MarketSnapshot | None = None
        self._provider_errors: dict[str, str] = {}

    async def refresh(self) -> MarketSnapshot:
        equities = await self.provider.fetch_equities()
        errors: list[str] = []
        self._provider_errors = {}
        indices: list[Any]
        try:
            indices = await self.provider.fetch_indices()
        except Exception as error:
            indices = []
            message = str(error)
            errors.append(f"indices: {message}")
            self._provider_errors["tencent"] = message
        sectors: list[Any]
        try:
            sectors = await self.provider.fetch_sectors()
        except Exception as error:
            sectors = []
            message = str(error)
            errors.append(f"sectors: {message}")
            self._provider_errors["sina"] = message
        meta = equities.meta.model_copy(update={"errors": errors})
        self._snapshot = MarketSnapshot(
            meta=meta, indices=indices, equities=equities.items, sectors=sectors
        )
        self.store.save_snapshot(
            "market", self._snapshot.meta.observed_at, self._snapshot.model_dump(mode="json")
        )
        return self._snapshot

    async def market(self, force: bool = False) -> MarketSnapshot:
        if self._snapshot is None or force:
            try:
                return await self.refresh()
            except Exception:
                cached = self.store.latest_snapshot("market")
                if cached is None:
                    raise
                payload = dict(cached.payload)
                payload["meta"]["freshness"] = "stale"  # type: ignore[index]
                self._snapshot = MarketSnapshot.model_validate(payload)
        return self._snapshot

    async def market_payload(self) -> MarketPayload:
        snapshot = await self.market()
        return MarketPayload(
            snapshot=MarketSummarySnapshot(
                meta=snapshot.meta,
                indices=snapshot.indices,
                sectors=snapshot.sectors,
            ),
            analysis=analyse_market(snapshot),
        )

    async def equities_page(
        self,
        *,
        query: str | None,
        sort_by: Literal["amount", "change_pct", "turnover_rate", "market_cap"],
        direction: Literal["asc", "desc"],
        page: int,
        page_size: int,
    ) -> EquityPage:
        snapshot = await self.market()
        normalized = (query or "").strip().lower()
        filtered = [
            item
            for item in snapshot.equities
            if not normalized
            or normalized in item.symbol.lower()
            or normalized in item.code.lower()
            or normalized in item.name.lower()
        ]
        present = [item for item in filtered if getattr(item, sort_by) is not None]
        missing = [item for item in filtered if getattr(item, sort_by) is None]
        present.sort(key=lambda item: item.symbol)
        present.sort(
            key=lambda item: cast(float, getattr(item, sort_by)),
            reverse=direction == "desc",
        )
        missing.sort(key=lambda item: item.symbol)
        ordered = [*present, *missing]
        start = (page - 1) * page_size
        return EquityPage(
            meta=snapshot.meta,
            total=len(ordered),
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            direction=direction,
            items=ordered[start : start + page_size],
        )

    async def market_events(self, limit: int = 30) -> MarketEventResult:
        fetcher = getattr(self.provider, "fetch_market_events", None)
        if not callable(fetcher):
            return analyse_market_events([])
        try:
            raw_events = await fetcher(limit)
        except Exception as error:
            self._provider_errors["eastmoney_fast_news"] = str(error)
            raw_events = []
        return analyse_market_events(raw_events[:limit])

    async def sector(self, code: str) -> SectorDossier:
        snapshot = await self.market()
        sector = next(
            (
                item
                for item in snapshot.sectors
                if item.code.lower() == code.lower() or item.name == code
            ),
            None,
        )
        if sector is None:
            raise KeyError(code)
        constituents = [item for item in snapshot.equities if item.sector == sector.name]
        fetcher = getattr(self.provider, "fetch_sector_constituents", None)
        if callable(fetcher):
            try:
                provider_rows = await fetcher(sector.code)
                constituents = [
                    quote.model_copy(update={"sector": sector.name})
                    if isinstance(quote, EquityQuote)
                    else quote
                    for quote in provider_rows
                ]
            except Exception as error:
                self._provider_errors["sector_constituents"] = str(error)
        return analyse_sector(sector, constituents)

    async def opportunities(self, preset: str = "trend", limit: int = 50) -> OpportunityResult:
        if preset not in {
            "trend",
            "volume_breakout",
            "value_rebound",
            "oversold_repair",
            "sector_improving",
            "capital_confirmed",
            "oversold_rebound",
        }:
            raise ValueError("unknown preset")
        snapshot = await self.market()
        regime = analyse_market(snapshot).regime
        result = rank_candidates(snapshot.equities, regime, preset)
        return result.model_copy(update={"candidates": result.candidates[:limit]})

    async def today(self) -> dict[str, Any]:
        snapshot = await self.market()
        analysis = analyse_market(snapshot)
        opportunities = rank_candidates(snapshot.equities, analysis.regime)
        risk_budget = {"risk_off": 25, "cautious": 40, "balanced": 60, "risk_on": 75}[
            analysis.regime
        ]
        return {
            "meta": snapshot.meta,
            "analysis": analysis,
            "indices": snapshot.indices,
            "sectors": snapshot.sectors[:8],
            "top_opportunities": opportunities.candidates[:3],
            "risk_budget": risk_budget,
            "next_actions": ["核对市场广度与指数趋势", "查看强势板块的持续性", "打开候选股证据链"],
        }

    async def search(self, query: str) -> list[EquityQuote]:
        snapshot = await self.market()
        normalized = query.strip().lower()
        if not normalized:
            return []
        return [
            item
            for item in snapshot.equities
            if normalized in item.code.lower() or normalized in item.name.lower()
        ][:20]

    async def stock(self, symbol: str) -> StockDossier:
        snapshot = await self.market()
        quote = next((item for item in snapshot.equities if item.symbol == symbol), None)
        if quote is None:
            raise KeyError(symbol)
        if quote.sector is None or quote.net_flow is None:
            enricher = getattr(self.provider, "fetch_equity_enrichment", None)
            if callable(enricher):
                try:
                    quote = quote.model_copy(update=await enricher(symbol))
                except Exception as error:
                    self._provider_errors["eastmoney_fund_flow"] = str(error)
        research_evidence: list[str] = []
        research_fetcher = getattr(self.provider, "fetch_research_enrichment", None)
        if callable(research_fetcher):
            try:
                research_evidence = await research_fetcher(symbol, quote.name, quote.sector)
            except Exception as error:
                self._provider_errors["semantic_research"] = str(error)
        bars = await self.provider.fetch_kline(symbol)
        return analyse_stock(quote, bars, research_evidence, peer_quotes=snapshot.equities)

    async def holdings(self, user_id: int | None = None) -> list[HoldingDossier]:
        snapshot = await self.market()
        items = self.store.list_holdings(user_id)
        return await self._analyse_holdings(items, snapshot)

    async def create_holding(
        self, payload: dict[str, Any], user_id: int | None = None
    ) -> HoldingDossier:
        item = self.store.create_holding(**payload, user_id=user_id)
        snapshot = await self.market()
        return await self._analyse_selected_holding(
            self.store.list_holdings(user_id), snapshot, item.id
        )

    async def update_holding(
        self, item_id: int, changes: dict[str, Any], user_id: int | None = None
    ) -> HoldingDossier:
        item = self.store.update_holding(item_id, user_id=user_id, **changes)
        snapshot = await self.market()
        return await self._analyse_selected_holding(
            self.store.list_holdings(user_id), snapshot, item.id
        )

    def delete_holding(self, item_id: int, user_id: int | None = None) -> None:
        self.store.delete_holding(item_id, user_id)

    async def _analyse_holdings(
        self, items: list[HoldingItem], snapshot: MarketSnapshot
    ) -> list[HoldingDossier]:
        quote_by_symbol = {quote.symbol: quote for quote in snapshot.equities}
        total_market_value = 0.0
        for item in items:
            quote = quote_by_symbol.get(item.symbol)
            if quote is not None and quote.price is not None:
                total_market_value += item.quantity * quote.price
        bars_by_symbol = await self._holding_bars(items)
        return [
            analyse_holding(
                item,
                quote_by_symbol.get(
                    item.symbol,
                    EquityQuote(
                        symbol=item.symbol,
                        code=item.symbol.split(".")[-1],
                        name=item.name,
                    ),
                ),
                total_market_value or None,
                bars_by_symbol.get(item.symbol),
            )
            for item in items
        ]

    async def _holding_bars(self, items: list[HoldingItem]) -> dict[str, list[Any]]:
        symbols = list(dict.fromkeys(item.symbol for item in items))
        results = await asyncio.gather(
            *(self.provider.fetch_kline(symbol, limit=8) for symbol in symbols),
            return_exceptions=True,
        )
        bars_by_symbol: dict[str, list[Any]] = {}
        for symbol, result in zip(symbols, results, strict=False):
            if isinstance(result, BaseException):
                continue
            bars_by_symbol[symbol] = result
        return bars_by_symbol

    async def _analyse_selected_holding(
        self, items: list[HoldingItem], snapshot: MarketSnapshot, selected_id: int
    ) -> HoldingDossier:
        selected = next(
            (dossier for dossier in await self._analyse_holdings(items, snapshot) if dossier.item.id == selected_id),
            None,
        )
        if selected is None:
            raise KeyError(selected_id)
        return selected

    def data_status(self) -> dict[str, Any]:
        provider_status = {}
        status_getter = getattr(self.provider, "provider_status", None)
        if callable(status_getter):
            provider_status = status_getter()
        return {
            "providers": {
                "eastmoney_fund_flow": {
                    "status": "not_checked",
                    "required": False,
                    "description": "东方财富资金流增强源",
                },
                "sina": {
                    "status": "partial"
                    if "sina" in self._provider_errors
                    else "ready"
                    if self._snapshot
                    else "not_checked",
                    "required": True,
                },
                "tencent": {
                    "status": "partial"
                    if "tencent" in self._provider_errors
                    else "ready"
                    if self._snapshot
                    else "not_checked",
                    "required": True,
                },
                "semantic_research": {
                    "status": "configured"
                    if Settings().iwencai_api_key and Settings().iwencai_endpoint
                    else "not_configured",
                    "required": False,
                    "description": "语义研究增强",
                },
                **provider_status,
            },
            "snapshot": self._snapshot.meta if self._snapshot else None,
        }
