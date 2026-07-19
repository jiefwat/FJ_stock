from __future__ import annotations

from typing import Any, Protocol

from marketdesk.analysis.market import analyse_market
from marketdesk.analysis.opportunities import rank_candidates
from marketdesk.analysis.stock import analyse_stock
from marketdesk.config import Settings
from marketdesk.models import (
    EquityDataset,
    EquityQuote,
    MarketSnapshot,
    OpportunityResult,
    StockDossier,
)
from marketdesk.providers.public_market import PublicMarketProvider
from marketdesk.store import Store


class MarketProvider(Protocol):
    async def fetch_equities(self) -> EquityDataset: ...
    async def fetch_indices(self) -> list[Any]: ...
    async def fetch_sectors(self) -> list[Any]: ...
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

    async def market_payload(self) -> dict[str, Any]:
        snapshot = await self.market()
        return {"snapshot": snapshot, "analysis": analyse_market(snapshot)}

    async def opportunities(self, preset: str = "trend", limit: int = 50) -> OpportunityResult:
        if preset not in {"trend", "sector_improving", "capital_confirmed", "oversold_rebound"}:
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
        bars = await self.provider.fetch_kline(symbol)
        return analyse_stock(quote, bars)

    def data_status(self) -> dict[str, Any]:
        return {
            "providers": {
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
                "iwencai": {
                    "status": "configured"
                    if Settings().iwencai_api_key
                    else "not_configured",
                    "required": False,
                },
            },
            "snapshot": self._snapshot.meta if self._snapshot else None,
        }
