from __future__ import annotations

import asyncio
import re
import time
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any, Literal, Protocol, cast

from marketdesk.analysis.ask_stock import (
    StockQuestionNotFound,
    build_portfolio_answer,
    build_stock_answer,
    classify_stock_question,
    is_contextual_stock_followup,
    is_portfolio_diagnostic_question,
    is_portfolio_question,
    is_stock_screening_question,
    resolve_stock_question,
    stock_screening_limit,
    stock_screening_period_days,
)
from marketdesk.analysis.decisions import candidate_decision, holding_decision
from marketdesk.analysis.events import analyse_market_events
from marketdesk.analysis.holding import analyse_holding
from marketdesk.analysis.market import analyse_market
from marketdesk.analysis.market_structure import (
    analyse_market_dashboard,
    analyse_market_groups,
    build_limit_ladder,
    build_strategy_board,
)
from marketdesk.analysis.morning_brief import build_morning_email_brief
from marketdesk.analysis.opportunities import (
    RECOMMENDATION_ALGORITHM_VERSION,
    rank_candidates,
)
from marketdesk.analysis.recommendation_history import analyse_recommendation_history
from marketdesk.analysis.sector import analyse_sector
from marketdesk.analysis.stock import analyse_stock
from marketdesk.analysis.stock_intelligence import analyse_financial_health, analyse_stock_news
from marketdesk.config import Settings
from marketdesk.models import (
    AskStockConversationMessage,
    AskStockMetric,
    AskStockResponse,
    AskStockSourceContext,
    Bar,
    CapabilityState,
    CapabilityStatus,
    DecisionEventFeed,
    DecisionSnapshot,
    EquityDataset,
    EquityPage,
    EquityQuote,
    EvidenceDocument,
    FinancialHealth,
    FinancialPeriod,
    Freshness,
    HoldingDossier,
    HoldingItem,
    InstrumentEvidenceResult,
    InstrumentTheme,
    LimitLadderResult,
    MarketDashboard,
    MarketEventRaw,
    MarketEventResult,
    MarketGroupAnalysis,
    MarketIntelligenceResult,
    MarketPayload,
    MarketSnapshot,
    MarketSummarySnapshot,
    MorningEmailBrief,
    OpportunityResult,
    RecommendationHistoryResult,
    RecommendationObservation,
    RecommendationSnapshot,
    RecommendationSnapshotPick,
    SectorDossier,
    SectorSnapshot,
    StockDossier,
    StockNewsItem,
    StockNewsSentiment,
    StrategyBoard,
    TradingAnomaly,
)
from marketdesk.providers.base import ProviderUnavailable
from marketdesk.providers.global_market import GlobalMarketProvider
from marketdesk.providers.llm_web import LLMWebAskContext
from marketdesk.providers.public_market import PublicMarketProvider
from marketdesk.store import Store

OPPORTUNITY_PRESETS = {
    "trend",
    "volume_breakout",
    "value_rebound",
    "oversold_repair",
    "sector_improving",
    "capital_confirmed",
    "sector_momentum",
    "pullback_support",
    "quality_value",
    "large_cap_stability",
    "oversold_rebound",
}

RECOMMENDATION_REVIEW_PRESETS = (
    "trend",
    "volume_breakout",
    "capital_confirmed",
    "sector_momentum",
    "pullback_support",
)

MONITORED_OPPORTUNITY_PRESETS = (
    "trend",
    "volume_breakout",
    "capital_confirmed",
    "sector_momentum",
    "pullback_support",
    "value_rebound",
    "quality_value",
    "large_cap_stability",
    "oversold_repair",
)


class MarketProvider(Protocol):
    async def fetch_equities(self) -> EquityDataset: ...
    async def fetch_indices(self) -> list[Any]: ...
    async def fetch_sectors(self) -> list[Any]: ...
    async def fetch_market_groups(self, kind: Literal["concept", "industry"]) -> list[Any]: ...
    async def fetch_sector_constituents(self, sector_code: str) -> list[Any]: ...
    async def fetch_research_enrichment(
        self, symbol: str, name: str, sector: str | None
    ) -> list[str]: ...
    async def fetch_market_events(self, limit: int = 50) -> list[MarketEventRaw]: ...
    async def fetch_kline(self, symbol: str, limit: int = 180) -> list[Any]: ...
    async def fetch_raw_kline(self, symbol: str, limit: int = 30) -> list[Any]: ...
    async def fetch_global_quote(self, symbol: str, name: str | None = None) -> EquityQuote: ...
    async def search_global_quotes(self, query: str, limit: int = 10) -> list[EquityQuote]: ...
    async def fetch_filings(self, symbol: str, limit: int = 20) -> list[EvidenceDocument]: ...
    async def fetch_research_documents(
        self, symbol: str, limit: int = 20
    ) -> list[EvidenceDocument]: ...
    async def fetch_themes(self, symbol: str, limit: int = 30) -> list[InstrumentTheme]: ...
    async def fetch_dragon_tiger(self, limit: int = 20) -> list[TradingAnomaly]: ...
    async def fetch_financial_periods(
        self, symbol: str, limit: int = 5
    ) -> list[FinancialPeriod]: ...
    async def fetch_stock_news(
        self, symbol: str, name: str, limit: int = 20
    ) -> list[StockNewsItem]: ...


class MarketService:
    def __init__(self, provider: MarketProvider | None = None, store: Store | None = None) -> None:
        settings = Settings()
        self.provider = provider or PublicMarketProvider()
        self.store = store or Store(settings.database_path)
        self._snapshot: MarketSnapshot | None = None
        self._provider_errors: dict[str, str] = {}
        self._capability_cache: dict[str, tuple[float, Any]] = {}
        self._capability_cache_locks: dict[str, asyncio.Lock] = {}
        self._opportunity_cache: dict[str, tuple[datetime, OpportunityResult]] = {}
        self._opportunity_cache_locks = {
            preset: asyncio.Lock() for preset in OPPORTUNITY_PRESETS
        }
        self._opportunity_monitored_at: dict[str, datetime] = {}
        self._opportunity_history_cache: dict[str, tuple[float, list[Bar]]] = {}
        self._opportunity_history_cache_ttl_seconds = 9 * 60
        self._opportunity_kline_timeout_seconds = 4.0
        self._refresh_lock = asyncio.Lock()
        self._refresh_task: asyncio.Task[MarketSnapshot] | None = None
        self._market_structure_cache: dict[str, tuple[float, Any]] = {}
        self._market_structure_last_good: dict[str, MarketGroupAnalysis] = {}
        self._limit_history_cache: dict[str, tuple[float, list[Bar]]] = {}

    async def refresh(self) -> MarketSnapshot:
        async with self._refresh_lock:
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
            self._record_recommendation_observations(self._snapshot)
            return self._snapshot

    async def market(self, force: bool = False) -> MarketSnapshot:
        if force:
            return await self.refresh()
        if self._snapshot is None:
            cached = self._cached_market_snapshot()
            if cached is not None:
                self._snapshot = cached
                self._schedule_background_refresh()
                return self._snapshot
            try:
                return await self.refresh()
            except Exception:
                cached = self._cached_market_snapshot()
                if cached is None:
                    raise
                self._snapshot = cached
        return self._snapshot

    def _cached_market_snapshot(self) -> MarketSnapshot | None:
        cached = self.store.latest_snapshot("market")
        if cached is None:
            return None
        payload = dict(cached.payload)
        payload["meta"]["freshness"] = "stale"  # type: ignore[index]
        return MarketSnapshot.model_validate(payload)

    def _schedule_background_refresh(self) -> None:
        if self._refresh_task is not None and not self._refresh_task.done():
            return
        self._refresh_task = asyncio.create_task(self._refresh_cache_safely())

    async def _refresh_cache_safely(self) -> MarketSnapshot:
        try:
            return await self.refresh()
        except Exception:
            if self._snapshot is None:
                raise
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

    async def market_dashboard(self) -> MarketDashboard:
        return analyse_market_dashboard(await self.market())

    async def strategy_board(self) -> StrategyBoard:
        return build_strategy_board(await self.market())

    async def limit_ladder(self, mode: Literal["up", "down"] = "up") -> LimitLadderResult:
        snapshot = await self.market()
        candidates = sorted(
            [
                item
                for item in snapshot.equities
                if item.change_pct is not None
                and item.price_limit_pct is not None
                and (
                    item.change_pct >= item.price_limit_pct - 0.2
                    if mode == "up"
                    else item.change_pct <= -item.price_limit_pct + 0.2
                )
            ],
            key=lambda item: (abs(item.change_pct or 0), item.amount or 0),
            reverse=True,
        )[:80]
        history = await self._raw_limit_history([item.symbol for item in candidates], limit=12)
        return build_limit_ladder(snapshot, history, mode)

    async def _raw_limit_history(
        self, symbols: list[str], limit: int
    ) -> dict[str, list[Bar]]:
        fetcher = getattr(self.provider, "fetch_raw_kline", None)
        if not callable(fetcher):
            return {}
        now = time.monotonic()
        cached = {
            symbol: entry[1]
            for symbol in symbols
            if (entry := self._limit_history_cache.get(symbol)) is not None
            and now - entry[0] < self._opportunity_history_cache_ttl_seconds
        }
        pending = [symbol for symbol in symbols if symbol not in cached]
        semaphore = asyncio.Semaphore(6)

        async def fetch(symbol: str) -> tuple[str, list[Bar]]:
            async with semaphore:
                try:
                    payload = await asyncio.wait_for(fetcher(symbol, limit=limit), timeout=4.0)
                    return symbol, [
                        item if isinstance(item, Bar) else Bar.model_validate(item)
                        for item in payload
                    ]
                except Exception as error:
                    self._provider_errors["raw_limit_kline"] = str(error)
                    return symbol, []

        pairs = await asyncio.gather(*(fetch(symbol) for symbol in pending))
        for symbol, bars in pairs:
            if bars:
                self._limit_history_cache[symbol] = (now, bars)
        return {**cached, **dict(pairs)}

    async def market_groups(
        self, kind: Literal["concept", "industry"]
    ) -> MarketGroupAnalysis:
        snapshot = await self.market()
        cache_key = f"groups:{kind}:{snapshot.meta.fetched_at.isoformat()}"
        cached = self._market_structure_cache.get(cache_key)
        now = time.monotonic()
        if cached is not None and now - cached[0] < 10 * 60:
            return cast(MarketGroupAnalysis, cached[1])

        fetcher = getattr(self.provider, "fetch_market_groups", None)
        unavailable_reason: str | None = None
        if callable(fetcher):
            try:
                groups = [
                    item if isinstance(item, SectorSnapshot) else SectorSnapshot.model_validate(item)
                    for item in await fetcher(kind)
                ]
                if not groups:
                    unavailable_reason = f"{kind} catalog returned no groups"
            except Exception as error:
                groups = []
                unavailable_reason = f"{kind} catalog unavailable: {error}"
        elif kind == "industry":
            groups = snapshot.sectors
        else:
            groups = []
            unavailable_reason = "concept catalog unavailable"

        if not groups and unavailable_reason:
            previous = self._market_structure_last_good.get(kind)
            if previous is not None:
                stale_meta = previous.meta.model_copy(
                    update={
                        "freshness": Freshness.STALE,
                        "errors": [*previous.meta.errors, unavailable_reason],
                    }
                )
                result = previous.model_copy(
                    update={
                        "meta": stale_meta,
                        "available": True,
                        "degraded": True,
                        "unavailable_reason": unavailable_reason,
                        "summary": f"当前显示上次有效的{kind}横截面；目录刷新失败，请按过期证据使用。",
                    }
                )
                self._market_structure_cache[cache_key] = (now, result)
                return result

        constituents_by_code: dict[str, list[EquityQuote]] = {}
        constituent_failures = 0
        constituent_fetcher = getattr(self.provider, "fetch_sector_constituents", None)
        if callable(constituent_fetcher) and groups:
            semaphore = asyncio.Semaphore(6)

            async def fetch_group(group: SectorSnapshot) -> tuple[str, list[EquityQuote]]:
                nonlocal constituent_failures
                async with semaphore:
                    try:
                        rows = await asyncio.wait_for(
                            constituent_fetcher(group.code), timeout=5.0
                        )
                        return group.code, [
                            item
                            if isinstance(item, EquityQuote)
                            else EquityQuote.model_validate(item)
                            for item in rows
                        ]
                    except Exception as error:
                        constituent_failures += 1
                        self._provider_errors[f"{kind}_constituents"] = str(error)
                        return group.code, []

            selected_groups = groups[:24]
            pairs = await asyncio.gather(*(fetch_group(group) for group in selected_groups))
            constituents_by_code = dict(pairs)
            if constituent_failures:
                unavailable_reason = (
                    f"{constituent_failures} {kind} constituent requests unavailable; "
                    "missing constituent evidence remains N/A"
                )

        result = analyse_market_groups(
            snapshot.meta,
            groups,
            constituents_by_code,
            kind,
            unavailable_reason=unavailable_reason,
            degraded=constituent_failures > 0,
        )
        self._market_structure_cache[cache_key] = (now, result)
        if result.available:
            self._market_structure_last_good[kind] = result
        return result

    async def market_group_detail(
        self, kind: Literal["concept", "industry"], group_code: str
    ) -> MarketGroupAnalysis | None:
        catalog = await self.market_groups(kind)
        catalog_group = next(
            (item for item in catalog.groups if item.code == group_code), None
        )
        if catalog_group is None:
            return None

        cache_key = (
            f"group-detail:{kind}:{group_code}:{catalog.meta.fetched_at.isoformat()}"
        )
        now = time.monotonic()
        cached = self._market_structure_cache.get(cache_key)
        if cached is not None and now - cached[0] < 10 * 60:
            return cast(MarketGroupAnalysis, cached[1])

        group = SectorSnapshot(
            code=catalog_group.code,
            name=catalog_group.name,
            change_pct=catalog_group.change_pct,
            net_flow=catalog_group.net_flow,
        )
        constituents = catalog_group.constituents
        unavailable_reason: str | None = None
        if not constituents:
            constituent_fetcher = getattr(
                self.provider, "fetch_sector_constituents", None
            )
            if callable(constituent_fetcher):
                try:
                    rows = await asyncio.wait_for(
                        constituent_fetcher(group_code), timeout=5.0
                    )
                    constituents = [
                        item
                        if isinstance(item, EquityQuote)
                        else EquityQuote.model_validate(item)
                        for item in rows
                    ]
                    if not constituents:
                        unavailable_reason = (
                            f"{kind} constituent request returned no constituents"
                        )
                except Exception as error:
                    self._provider_errors[f"{kind}_group_detail"] = str(error)
                    unavailable_reason = f"{kind} constituents unavailable: {error}"
            else:
                unavailable_reason = f"{kind} constituent provider unavailable"

        stale_catalog = catalog.meta.freshness == Freshness.STALE
        if stale_catalog and unavailable_reason is None:
            unavailable_reason = catalog.unavailable_reason or f"{kind} catalog is stale"
        result = analyse_market_groups(
            catalog.meta,
            [group],
            {group_code: constituents},
            kind,
            unavailable_reason=unavailable_reason,
            degraded=unavailable_reason is not None,
        )
        label = "概念" if kind == "concept" else "行业"
        result = result.model_copy(
            update={
                "summary": (
                    f"已补齐{catalog_group.name}的成分股、扩散、换手与龙头证据。"
                    if constituents
                    else f"{catalog_group.name}的板块行情可用，{label}成分证据暂未取得。"
                )
            }
        )
        if constituents:
            self._market_structure_cache[cache_key] = (now, result)
        return result

    async def refresh_market_group_monitor(self, limit: int = 12) -> dict[str, int]:
        catalogs = await asyncio.gather(
            self.market_groups("concept"),
            self.market_groups("industry"),
        )
        selected = [
            (catalog.kind, group.code)
            for catalog in catalogs
            for group in catalog.groups[: max(0, limit)]
        ]
        semaphore = asyncio.Semaphore(6)

        async def warm_detail(
            kind: Literal["concept", "industry"], group_code: str
        ) -> bool:
            async with semaphore:
                try:
                    detail = await self.market_group_detail(kind, group_code)
                except Exception as error:
                    self._provider_errors[f"{kind}_group_monitor"] = str(error)
                    return False
                return bool(detail and detail.groups and detail.groups[0].constituents)

        ready = await asyncio.gather(
            *(warm_detail(kind, group_code) for kind, group_code in selected)
        )
        return {"groups": len(selected), "ready": sum(ready)}

    async def equities_page(
        self,
        *,
        query: str | None,
        exchange: Literal["all", "sh", "sz", "bj"],
        sort_by: Literal["amount", "change_pct", "turnover_rate", "market_cap"],
        direction: Literal["asc", "desc"],
        page: int,
        page_size: int,
        sector: str | None = None,
        min_change_pct: float | None = None,
        max_change_pct: float | None = None,
        min_amount: float | None = None,
        max_amount: float | None = None,
        min_turnover_rate: float | None = None,
        max_turnover_rate: float | None = None,
        min_market_cap: float | None = None,
        max_market_cap: float | None = None,
        complete_only: bool = False,
    ) -> EquityPage:
        snapshot = await self.market()
        normalized = (query or "").strip().lower()
        available_sectors = sorted(
            {item.sector for item in snapshot.equities if item.sector},
            key=str.casefold,
        )
        ranges = (
            ("change_pct", min_change_pct, max_change_pct),
            ("amount", min_amount, max_amount),
            ("turnover_rate", min_turnover_rate, max_turnover_rate),
            ("market_cap", min_market_cap, max_market_cap),
        )

        def matches_ranges(item: EquityQuote) -> bool:
            for field, minimum, maximum in ranges:
                if minimum is None and maximum is None:
                    continue
                value = getattr(item, field)
                if value is None:
                    return False
                if minimum is not None and value < minimum:
                    return False
                if maximum is not None and value > maximum:
                    return False
            return True

        filtered = [
            item
            for item in snapshot.equities
            if (exchange == "all" or item.symbol.startswith(f"{exchange.upper()}."))
            and (sector is None or item.sector == sector)
            and (
                not normalized
                or normalized in item.symbol.lower()
                or normalized in item.code.lower()
                or normalized in item.name.lower()
            )
            and matches_ranges(item)
            and (
                not complete_only
                or all(
                    getattr(item, field) is not None
                    for field in ("price", "change_pct", "amount", "turnover_rate", "market_cap")
                )
            )
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
            exchange=exchange,
            sort_by=sort_by,
            direction=direction,
            available_sectors=available_sectors,
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

    @staticmethod
    def _require_a_share_symbol(symbol: str) -> str:
        return MarketService._normalize_a_share_symbol(symbol)

    @staticmethod
    def _normalize_supported_symbol(symbol: str) -> str:
        try:
            return MarketService._normalize_a_share_symbol(symbol)
        except ValueError:
            try:
                return GlobalMarketProvider.normalize_symbol(symbol)
            except ValueError as global_error:
                raise ValueError("supported stock symbol required") from global_error

    @staticmethod
    def _is_a_share_symbol(symbol: str) -> bool:
        return symbol.startswith(("SH.", "SZ.", "BJ."))

    @staticmethod
    def _normalize_a_share_symbol(symbol: str) -> str:
        normalized = symbol.strip().upper()
        match = re.fullmatch(r"(SH|SZ|BJ)\.(\d{6})", normalized)
        if match is None:
            bare = re.fullmatch(r"\d{6}", normalized)
            if bare is None:
                raise ValueError("A-share symbol required")
            code = bare.group(0)
            market = (
                "BJ"
                if code.startswith(("4", "8"))
                else "SH"
                if code.startswith(("5", "6", "9"))
                else "SZ"
            )
            return f"{market}.{code}"
        market, code = match.groups()
        expected = (
            "BJ"
            if code.startswith(("4", "8"))
            else "SH"
            if code.startswith(("5", "6", "9"))
            else "SZ"
        )
        if market != expected:
            raise ValueError("A-share symbol required")
        return normalized

    async def _cached_capability(self, key: str, ttl_seconds: float, loader: Any) -> Any:
        cached = self._capability_cache.get(key)
        now = time.monotonic()
        if cached is not None and now - cached[0] < ttl_seconds:
            return cached[1]
        lock = self._capability_cache_locks.setdefault(key, asyncio.Lock())
        async with lock:
            cached = self._capability_cache.get(key)
            now = time.monotonic()
            if cached is not None and now - cached[0] < ttl_seconds:
                return cached[1]
            value = await loader()
            self._capability_cache[key] = (time.monotonic(), value)
            return value

    @staticmethod
    def _capability_state(
        provider: str,
        fetched_at: datetime,
        items: list[Any] | None = None,
        error: Exception | None = None,
    ) -> CapabilityState:
        if error is not None:
            return CapabilityState(
                status=CapabilityStatus.UNAVAILABLE,
                provider=provider,
                error=str(error),
                fetched_at=fetched_at,
            )
        return CapabilityState(
            status=CapabilityStatus.READY if items else CapabilityStatus.EMPTY,
            provider=provider,
            fetched_at=fetched_at,
        )

    async def instrument_evidence(self, symbol: str, limit: int = 20) -> InstrumentEvidenceResult:
        normalized = self._normalize_supported_symbol(symbol)
        if not self._is_a_share_symbol(normalized):
            return InstrumentEvidenceResult(
                symbol=normalized,
                filings=[],
                research=[],
                themes=[],
                capabilities={
                    "filings": CapabilityState(
                        status=CapabilityStatus.EMPTY, provider="not_supported"
                    ),
                    "research": CapabilityState(
                        status=CapabilityStatus.EMPTY, provider="not_supported"
                    ),
                    "themes": CapabilityState(
                        status=CapabilityStatus.EMPTY, provider="not_supported"
                    ),
                },
            )

        async def load() -> InstrumentEvidenceResult:
            fetched_at = datetime.now(UTC)

            async def fetch(
                name: str, provider: str, method_name: str
            ) -> tuple[str, list[Any], CapabilityState]:
                fetcher = getattr(self.provider, method_name, None)
                if not callable(fetcher):
                    error = ProviderUnavailable(f"{name} capability is not supported")
                    return name, [], self._capability_state(provider, fetched_at, error=error)
                try:
                    items = await fetcher(normalized, limit)
                except Exception as error:
                    self._provider_errors[name] = str(error)
                    return name, [], self._capability_state(provider, fetched_at, error=error)
                return name, list(items), self._capability_state(provider, fetched_at, list(items))

            rows = await asyncio.gather(
                fetch("filings", "cninfo", "fetch_filings"),
                fetch("research", "eastmoney_report", "fetch_research_documents"),
                fetch("themes", "eastmoney_theme", "fetch_themes"),
            )
            by_name = {name: items for name, items, _state in rows}
            states = {name: state for name, _items, state in rows}
            return InstrumentEvidenceResult(
                symbol=normalized,
                filings=cast(list[EvidenceDocument], by_name["filings"]),
                research=cast(list[EvidenceDocument], by_name["research"]),
                themes=cast(list[InstrumentTheme], by_name["themes"]),
                capabilities=states,
            )

        return cast(
            InstrumentEvidenceResult,
            await self._cached_capability(
                f"instrument-evidence:{normalized}:{limit}", 15 * 60, load
            ),
        )

    async def cn_market_intelligence(self, limit: int = 20) -> MarketIntelligenceResult:
        async def load() -> MarketIntelligenceResult:
            snapshot = await self.market()
            fetched_at = datetime.now(UTC)
            flows = sorted(
                (item for item in snapshot.sectors if item.net_flow is not None),
                key=lambda item: item.net_flow or 0,
                reverse=True,
            )[:limit]
            flow_state = self._capability_state("eastmoney_sector_flow", fetched_at, list(flows))
            anomalies: list[TradingAnomaly] = []
            anomaly_error: Exception | None = None
            fetcher = getattr(self.provider, "fetch_dragon_tiger", None)
            if callable(fetcher):
                try:
                    anomalies = list(await fetcher(limit))
                except Exception as error:
                    anomaly_error = error
                    self._provider_errors["dragon_tiger"] = str(error)
            else:
                anomaly_error = ProviderUnavailable("dragon_tiger capability is not supported")
            anomaly_state = self._capability_state(
                "eastmoney_datacenter", fetched_at, anomalies, anomaly_error
            )
            errors = [
                state.error for state in (flow_state, anomaly_state) if state.error is not None
            ]
            available_count = int(bool(flows)) + int(bool(anomalies))
            freshness = snapshot.meta.freshness if available_count else Freshness.UNAVAILABLE
            return MarketIntelligenceResult(
                meta=snapshot.meta.model_copy(
                    update={
                        "source": "eastmoney_sector_flow+eastmoney_dragon_tiger",
                        "fetched_at": fetched_at,
                        "freshness": freshness,
                        "coverage": available_count / 2,
                        "errors": errors,
                    }
                ),
                sector_flows=flows,
                anomalies=anomalies,
                capabilities={
                    "sector_flows": flow_state,
                    "dragon_tiger": anomaly_state,
                },
            )

        return cast(
            MarketIntelligenceResult,
            await self._cached_capability(f"cn-market-intelligence:{limit}", 10 * 60, load),
        )

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

    @staticmethod
    def _require_board_code(code: str) -> str:
        normalized = code.strip().upper()
        if not re.fullmatch(r"BK\d{1,8}", normalized):
            raise ValueError("Eastmoney board code required")
        return normalized

    async def theme(
        self,
        code: str,
        name: str | None = None,
        change_pct: float | None = None,
    ) -> SectorDossier:
        normalized = self._require_board_code(code)
        theme_name = (name or normalized).strip() or normalized
        constituents: list[EquityQuote] = []
        fetcher = getattr(self.provider, "fetch_sector_constituents", None)
        if callable(fetcher):
            try:
                constituents = [
                    quote.model_copy(update={"sector": theme_name})
                    if isinstance(quote, EquityQuote)
                    else quote
                    for quote in await fetcher(normalized)
                ]
            except Exception as error:
                self._provider_errors["theme_constituents"] = str(error)
        net_flows = [quote.net_flow for quote in constituents if quote.net_flow is not None]
        snapshot = SectorSnapshot(
            code=normalized,
            name=theme_name,
            change_pct=change_pct,
            net_flow=sum(net_flows) if net_flows else None,
        )
        return analyse_sector(snapshot, constituents)

    async def _opportunity_kline_history(
        self, symbols: list[str], limit: int = 120
    ) -> dict[str, list[Bar]]:
        unique_symbols = list(dict.fromkeys(symbols))[:80]
        if not unique_symbols:
            return {}
        now = time.monotonic()
        cached = {
            symbol: entry[1]
            for symbol in unique_symbols
            if (entry := self._opportunity_history_cache.get(symbol)) is not None
            and now - entry[0] < self._opportunity_history_cache_ttl_seconds
        }
        pending_symbols = [symbol for symbol in unique_symbols if symbol not in cached]
        if not pending_symbols:
            return cached
        semaphore = asyncio.Semaphore(6)

        async def fetch(symbol: str) -> tuple[str, list[Bar]]:
            async with semaphore:
                try:
                    payload = await self.provider.fetch_kline(symbol, limit=limit)
                    bars = [
                        item if isinstance(item, Bar) else Bar.model_validate(item)
                        for item in payload
                    ]
                    return symbol, bars
                except Exception as error:
                    self._provider_errors["opportunity_kline"] = str(error)
                    return symbol, []

        tasks = [asyncio.create_task(fetch(symbol)) for symbol in pending_symbols]
        done, pending = await asyncio.wait(tasks, timeout=self._opportunity_kline_timeout_seconds)
        if pending:
            self._provider_errors["opportunity_kline"] = "history fetch timeout"
            for task in pending:
                task.cancel()
        pairs = [
            task.result() for task in done if not task.cancelled() and task.exception() is None
        ]
        fetched = dict(pairs)
        cached_at = time.monotonic()
        for symbol, bars in fetched.items():
            if bars:
                self._opportunity_history_cache[symbol] = (cached_at, bars)
        return {**cached, **fetched}

    async def _stock_kline_history(self, symbol: str, limit: int = 180) -> list[Bar]:
        cached = self._opportunity_history_cache.get(symbol)
        now = time.monotonic()
        if cached is not None and now - cached[0] < self._opportunity_history_cache_ttl_seconds:
            return cached[1]
        try:
            payload = await asyncio.wait_for(
                self.provider.fetch_kline(symbol, limit=limit),
                timeout=self._opportunity_kline_timeout_seconds,
            )
            bars = [
                item if isinstance(item, Bar) else Bar.model_validate(item) for item in payload
            ]
            if bars:
                self._opportunity_history_cache[symbol] = (now, bars)
            return bars
        except Exception as error:
            self._provider_errors["stock_kline"] = str(error)
            return cached[1] if cached is not None else []

    async def opportunities(self, preset: str = "trend", limit: int = 50) -> OpportunityResult:
        if preset not in OPPORTUNITY_PRESETS:
            raise ValueError("unknown preset")
        snapshot = await self.market()
        cached = self._opportunity_cache.get(preset)
        if cached is not None and cached[0] == snapshot.meta.fetched_at:
            return self._visible_opportunity_result(cached[1], limit)
        async with self._opportunity_cache_locks[preset]:
            cached = self._opportunity_cache.get(preset)
            if cached is not None and cached[0] == snapshot.meta.fetched_at:
                return self._visible_opportunity_result(cached[1], limit)
            result = await self._analyse_opportunities(snapshot, preset, limit)
            return self._visible_opportunity_result(result, limit)

    async def refresh_opportunity_monitor(
        self, preset: str = "trend", limit: int = 10
    ) -> OpportunityResult:
        if preset not in OPPORTUNITY_PRESETS:
            raise ValueError("unknown preset")
        snapshot = await self.market()
        async with self._opportunity_cache_locks[preset]:
            result = await self._analyse_opportunities(snapshot, preset, limit)
            return self._visible_opportunity_result(result, limit)

    def opportunity_monitor_status(self) -> dict[str, object]:
        return {
            "active": bool(self._opportunity_monitored_at),
            "presets": [
                preset
                for preset in MONITORED_OPPORTUNITY_PRESETS
                if preset in self._opportunity_monitored_at
            ],
            "checked_at": max(self._opportunity_monitored_at.values(), default=None),
        }

    @staticmethod
    def _visible_opportunity_result(result: OpportunityResult, limit: int) -> OpportunityResult:
        return result.model_copy(update={"candidates": result.candidates[:limit], "excluded": []})

    async def _analyse_opportunities(
        self, snapshot: MarketSnapshot, preset: str, limit: int
    ) -> OpportunityResult:
        regime = analyse_market(snapshot).regime
        sector_strength = {
            item.name: item.change_pct for item in snapshot.sectors if item.change_pct is not None
        }
        initial = rank_candidates(
            snapshot.equities,
            regime,
            preset,
            sector_strength=sector_strength,
        )
        symbols = [item.quote.symbol for item in initial.candidates[: max(80, limit * 8)]]
        history_by_symbol: dict[str, list[Bar]] = {}

        async def fetch_and_record(batch: list[str]) -> None:
            fetched = await self._opportunity_kline_history(batch)
            for symbol in batch:
                history_by_symbol[symbol] = fetched.get(symbol, [])

        await fetch_and_record(symbols)
        result = rank_candidates(
            snapshot.equities,
            regime,
            preset,
            history_by_symbol,
            sector_strength,
        )
        attempted_symbols = set(history_by_symbol)
        # Re-ranking with history can promote candidates that were outside the
        # first prefetch window. Fill the final visible page before returning it.
        for _ in range(8):
            visible_missing = [
                item.quote.symbol
                for item in result.candidates[:limit]
                if item.quote.symbol not in history_by_symbol
                and item.quote.symbol not in attempted_symbols
            ]
            if not visible_missing:
                break
            missing_symbols = [
                item.quote.symbol
                for item in result.candidates
                if item.quote.symbol not in history_by_symbol
                and item.quote.symbol not in attempted_symbols
            ][: max(80, limit * 8)]
            attempted_symbols.update(missing_symbols)
            await fetch_and_record(missing_symbols)
            result = rank_candidates(
                snapshot.equities,
                regime,
                preset,
                history_by_symbol,
                sector_strength,
            )
        monitored_result = result.model_copy(
            update={
                "monitoring_active": True,
                "monitored_at": snapshot.meta.fetched_at,
            }
        )
        self._opportunity_cache[preset] = (snapshot.meta.fetched_at, monitored_result)
        self._opportunity_monitored_at[preset] = snapshot.meta.fetched_at
        self._capture_recommendation_result(snapshot, monitored_result)
        return monitored_result

    @staticmethod
    def _recommendation_benchmark(snapshot: MarketSnapshot) -> tuple[str, str, float] | None:
        benchmark = next(
            (
                item
                for item in snapshot.indices
                if item.symbol == "SH.000001" and item.price is not None and item.price > 0
            ),
            None,
        )
        if benchmark is None or benchmark.price is None:
            return None
        return benchmark.symbol, benchmark.name, benchmark.price

    def _capture_recommendation_result(
        self, snapshot: MarketSnapshot, result: OpportunityResult
    ) -> None:
        benchmark = self._recommendation_benchmark(snapshot)
        run = RecommendationSnapshot(
            preset=result.preset,
            algorithm_version=RECOMMENDATION_ALGORITHM_VERSION,
            trading_date=snapshot.meta.observed_at.date(),
            observed_at=snapshot.meta.observed_at,
            available=result.available,
            unavailable_reason=result.unavailable_reason,
            summary=result.summary,
            benchmark_symbol=benchmark[0] if benchmark else None,
            benchmark_name=benchmark[1] if benchmark else None,
            benchmark_price=benchmark[2] if benchmark else None,
            picks=[
                RecommendationSnapshotPick(
                    rank=index,
                    symbol=item.quote.symbol,
                    name=item.quote.name,
                    sector=item.quote.sector,
                    entry_price=item.quote.price,
                    score=item.upside_score,
                    evidence_coverage=item.evidence_coverage,
                    thesis=item.thesis,
                    risk_flags=item.risk_flags,
                )
                for index, item in enumerate(result.candidates[:3], start=1)
            ],
        )
        self.store.save_recommendation_run(run)
        self._record_recommendation_observations(snapshot, presets={result.preset})

    def _record_recommendation_observations(
        self, snapshot: MarketSnapshot, presets: set[str] | None = None
    ) -> None:
        quote_prices = {
            item.symbol: item.price
            for item in snapshot.equities
            if item.price is not None and item.price > 0
        }
        index_prices = {
            item.symbol: item.price
            for item in snapshot.indices
            if item.price is not None and item.price > 0
        }
        observation_date = snapshot.meta.observed_at.date()
        for preset in presets or OPPORTUNITY_PRESETS:
            for record in self.store.list_recommendation_runs(
                preset, limit=180, algorithm_version=None
            ):
                if record.snapshot.trading_date > observation_date:
                    continue
                self.store.save_recommendation_observation(
                    record.id,
                    RecommendationObservation(
                        trading_date=observation_date,
                        observed_at=snapshot.meta.observed_at,
                        benchmark_price=index_prices.get(record.snapshot.benchmark_symbol or ""),
                        prices={
                            pick.symbol: quote_prices[pick.symbol]
                            for pick in record.snapshot.picks
                            if pick.symbol in quote_prices
                        },
                    ),
                )

    async def capture_daily_recommendations(self, preset: str = "trend") -> None:
        if preset not in OPPORTUNITY_PRESETS:
            raise ValueError("unknown preset")
        snapshot = await self.market()
        if self.store.recommendation_run_exists(
            preset,
            snapshot.meta.observed_at.date(),
            RECOMMENDATION_ALGORITHM_VERSION,
        ):
            return
        await self.opportunities(preset, 3)

    async def recommendation_history(
        self, preset: str = "trend", limit: int = 60
    ) -> RecommendationHistoryResult:
        await self.capture_daily_recommendations(preset)
        records = self.store.list_recommendation_runs(
            preset,
            limit=limit,
            algorithm_version=RECOMMENDATION_ALGORITHM_VERSION,
        )
        observations = self.store.list_recommendation_observations(
            [record.id for record in records]
        )
        return analyse_recommendation_history(
            preset,
            [(record.snapshot, observations.get(record.id, [])) for record in records],
            datetime.now(UTC),
        )

    async def morning_email_preview(self, user_id: int, base_url: str) -> MorningEmailBrief:
        user = self.store.get_user(user_id)
        preferences = self.store.get_preferences(user_id)
        market_payload = await self.market_payload()
        events, intelligence, opportunities, holdings = await asyncio.gather(
            self.market_events(12),
            self.cn_market_intelligence(12),
            self.opportunities("trend", 5),
            self.holdings(user_id),
        )
        watchlist = self.store.list_watchlist(user_id)
        return build_morning_email_brief(
            user=user,
            preferences=preferences,
            market=market_payload,
            intelligence=intelligence,
            events=events,
            opportunities=opportunities,
            holdings=holdings,
            watchlist=watchlist,
            base_url=base_url,
        )

    async def search(self, query: str) -> list[EquityQuote]:
        snapshot = await self.market()
        normalized = query.strip().lower()
        if not normalized:
            return []
        local_matches = [
            item
            for item in snapshot.equities
            if normalized in item.code.lower()
            or normalized in item.name.lower()
            or normalized in item.symbol.lower()
        ]
        global_matches: list[EquityQuote] = []
        searcher = getattr(self.provider, "search_global_quotes", None)
        if callable(searcher):
            try:
                global_matches = list(await searcher(query, 10))
            except Exception as error:
                self._provider_errors["global_market_search"] = str(error)
        by_symbol = {item.symbol: item for item in [*local_matches, *global_matches]}
        return list(by_symbol.values())[:20]

    async def stock(self, symbol: str) -> StockDossier:
        snapshot = await self.market()
        normalized_symbol = self._normalize_supported_symbol(symbol)
        quote = next((item for item in snapshot.equities if item.symbol == normalized_symbol), None)
        if quote is None:
            quote = await self._global_quote(normalized_symbol)
        symbol = quote.symbol
        if self._is_a_share_symbol(quote.symbol) and (
            quote.sector is None or quote.net_flow is None
        ):
            enricher = getattr(self.provider, "fetch_equity_enrichment", None)
            if callable(enricher):
                try:
                    quote = quote.model_copy(update=await enricher(symbol))
                except Exception as error:
                    self._provider_errors["eastmoney_fund_flow"] = str(error)
        async def load_research() -> list[str]:
            fetcher = getattr(self.provider, "fetch_research_enrichment", None)
            if not callable(fetcher):
                return []
            try:
                return list(await fetcher(symbol, quote.name, quote.sector))
            except Exception as error:
                self._provider_errors["semantic_research"] = str(error)
                return []

        async def load_financials() -> FinancialHealth:
            if not self._is_a_share_symbol(symbol):
                return FinancialHealth(available=False, conclusion="暂仅支持A股财报")
            fetcher = getattr(self.provider, "fetch_financial_periods", None)
            if not callable(fetcher):
                return FinancialHealth(available=False, conclusion="财报待补")
            try:
                periods = await self._cached_capability(
                    f"stock_financials:{symbol}",
                    600,
                    lambda: fetcher(symbol, 5),
                )
                return analyse_financial_health(list(periods))
            except Exception as error:
                self._provider_errors["stock_financials"] = str(error)
                return FinancialHealth(
                    available=False,
                    conclusion="财报暂不可用",
                    error=str(error),
                )

        async def load_news() -> StockNewsSentiment:
            if not self._is_a_share_symbol(symbol):
                return StockNewsSentiment(available=False, conclusion="暂仅支持A股新闻")
            fetcher = getattr(self.provider, "fetch_stock_news", None)
            if not callable(fetcher):
                return StockNewsSentiment(available=False, conclusion="新闻待补")
            try:
                items = await self._cached_capability(
                    f"stock_news:{symbol}",
                    600,
                    lambda: fetcher(symbol, quote.name, 20),
                )
                return analyse_stock_news(list(items))
            except Exception as error:
                self._provider_errors["stock_news"] = str(error)
                return StockNewsSentiment(
                    available=False,
                    conclusion="新闻暂不可用",
                    error=str(error),
                )

        bars, research_evidence, financial_health, news_sentiment = await asyncio.gather(
            self._stock_kline_history(symbol),
            load_research(),
            load_financials(),
            load_news(),
        )
        return analyse_stock(
            quote,
            bars,
            research_evidence,
            peer_quotes=snapshot.equities,
            financial_health=financial_health,
            news_sentiment=news_sentiment,
        )

    async def refresh_stock_monitor(self, limit: int = 12) -> dict[str, int]:
        snapshot = await self.market()
        available = {item.symbol for item in snapshot.equities}
        symbols: dict[str, None] = {}
        for user in self.store.list_users():
            preferred = self.store.get_preferences(user.id).default_symbol
            if preferred in available:
                symbols[preferred] = None
            tracked_symbols = [
                item.symbol for item in self.store.list_holdings(user.id)
            ] + [item.symbol for item in self.store.list_watchlist(user.id)]
            for tracked_symbol in tracked_symbols:
                if tracked_symbol in available:
                    symbols[tracked_symbol] = None
        for _preset, (_observed_at, result) in self._opportunity_cache.items():
            for candidate in result.candidates[:1]:
                if candidate.quote.symbol in available:
                    symbols[candidate.quote.symbol] = None

        selected = list(symbols)[: max(1, min(limit, 30))]
        semaphore = asyncio.Semaphore(3)

        async def warm(symbol: str) -> bool:
            async with semaphore:
                try:
                    await self.stock(symbol)
                except Exception as error:
                    self._provider_errors[f"stock_monitor_{symbol}"] = str(error)
                    return False
                return True

        ready = sum(await asyncio.gather(*(warm(symbol) for symbol in selected)))
        return {"symbols": len(selected), "ready": ready}

    async def ask_stock(
        self,
        question: str,
        user_id: int | None = None,
        *,
        context_symbol: str | None = None,
        context_name: str | None = None,
        conversation: list[AskStockConversationMessage] | None = None,
        source_context: AskStockSourceContext | None = None,
        _use_llm: bool = True,
    ) -> AskStockResponse:
        snapshot = await self.market()
        holdings = self.store.list_holdings(user_id) if user_id is not None else []
        source_stock = source_context.stock if source_context is not None else None
        context_symbol = context_symbol or (source_stock.symbol if source_stock else None)
        context_name = context_name or (source_stock.name if source_stock else None)
        context_quote = self._resolve_ask_context_stock(
            snapshot.equities, context_symbol, context_name
        )
        if context_quote is None and context_symbol:
            try:
                context_quote = await self._global_quote(
                    self._normalize_supported_symbol(context_symbol), context_name
                )
            except (KeyError, ValueError):
                context_quote = None
        if is_stock_screening_question(question):
            return await self._semantic_screen_answer(question, snapshot)
        llm_asker = getattr(self.provider, "ask_stock_with_llm", None)
        if (
            _use_llm
            and callable(llm_asker)
            and bool(getattr(self.provider, "llm_web_configured", False))
        ):
            llm_context = await self._build_llm_ask_context(
                question=question,
                snapshot=snapshot,
                holdings=holdings,
                context_quote=context_quote,
                context_symbol=context_symbol,
                context_name=context_name,
                conversation=conversation or [],
                source_context=source_context,
            )
            try:
                result = await llm_asker(llm_context)
                return cast(AskStockResponse, result)
            except ProviderUnavailable as error:
                self._provider_errors["financial_llm"] = str(error)
        try:
            quote = resolve_stock_question(question, snapshot.equities)
        except StockQuestionNotFound:
            if user_id is not None and is_portfolio_question(question):
                focus_symbol = (
                    context_quote.symbol
                    if context_quote is not None and is_contextual_stock_followup(question)
                    else None
                )
                return build_portfolio_answer(
                    question=question,
                    holdings=await self._analyse_holdings(holdings, snapshot),
                    observed_at=snapshot.meta.observed_at,
                    focus_symbol=focus_symbol,
                )
            if context_quote is not None and is_contextual_stock_followup(question):
                quote = context_quote
            else:
                global_symbol = self._global_symbol_from_text(question)
                if global_symbol is not None:
                    quote = await self._global_quote(global_symbol)
                else:
                    return await self._semantic_screen_answer(question, snapshot)
        if user_id is not None and is_portfolio_diagnostic_question(question):
            return build_portfolio_answer(
                question=question,
                holdings=await self._analyse_holdings(holdings, snapshot),
                observed_at=snapshot.meta.observed_at,
                focus_symbol=quote.symbol,
            )
        dossier = await self.stock(quote.symbol)
        holding_context = None
        if holdings:
            analysed_holdings = await self._analyse_holdings(holdings, snapshot)
            holding_context = next(
                (item for item in analysed_holdings if item.item.symbol == quote.symbol), None
            )
        return build_stock_answer(
            question=question,
            intent=classify_stock_question(question),
            dossier=dossier,
            holding=holding_context,
            observed_at=snapshot.meta.observed_at,
        )

    async def stream_ask_stock(
        self,
        question: str,
        user_id: int | None = None,
        *,
        context_symbol: str | None = None,
        context_name: str | None = None,
        conversation: list[AskStockConversationMessage] | None = None,
        source_context: AskStockSourceContext | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        yield {"event": "status", "message": "读取行情"}
        snapshot = await self.market()
        holdings = self.store.list_holdings(user_id) if user_id is not None else []
        source_stock = source_context.stock if source_context is not None else None
        context_symbol = context_symbol or (source_stock.symbol if source_stock else None)
        context_name = context_name or (source_stock.name if source_stock else None)
        context_quote = self._resolve_ask_context_stock(
            snapshot.equities, context_symbol, context_name
        )
        if is_stock_screening_question(question):
            yield {"event": "status", "message": "条件筛选"}
            result = await self._semantic_screen_answer(question, snapshot)
            yield {"event": "final", "result": result}
            return
        streamer = getattr(self.provider, "stream_ask_stock_with_llm", None)
        if callable(streamer) and bool(getattr(self.provider, "llm_web_configured", False)):
            llm_context = await self._build_llm_ask_context(
                question=question,
                snapshot=snapshot,
                holdings=holdings,
                context_quote=context_quote,
                context_symbol=context_symbol,
                context_name=context_name,
                conversation=conversation or [],
                source_context=source_context,
            )
            yield {"event": "status", "message": "资料核对"}
            parts: list[str] = []
            try:
                async for chunk in streamer(llm_context):
                    parts.append(chunk)
                    yield {"event": "delta", "text": chunk}
                builder = getattr(self.provider, "build_streamed_llm_answer", None)
                if callable(builder):
                    result = cast(AskStockResponse, builder(llm_context, "".join(parts)))
                else:
                    result = self._llm_unavailable_answer(
                        question, snapshot, context_quote, "流式结果缺少解析器"
                    )
                yield {"event": "final", "result": result}
                return
            except ProviderUnavailable as error:
                self._provider_errors["financial_llm"] = str(error)
                result = await self.ask_stock(
                    question,
                    user_id,
                    context_symbol=context_symbol,
                    context_name=context_name,
                    conversation=conversation,
                    source_context=source_context,
                    _use_llm=False,
                )
                yield {"event": "final", "result": result}
                return

        result = await self.ask_stock(
            question,
            user_id,
            context_symbol=context_symbol,
            context_name=context_name,
            conversation=conversation,
            source_context=source_context,
        )
        yield {"event": "final", "result": result}

    async def _semantic_screen_answer(
        self, question: str, snapshot: MarketSnapshot
    ) -> AskStockResponse:
        ranking_days = stock_screening_period_days(question)
        period_ranker = getattr(self.provider, "fetch_equity_period_ranking", None)
        if ranking_days is not None and callable(period_ranker):
            result = await period_ranker(ranking_days, stock_screening_limit(question))
            return AskStockResponse(
                kind="semantic_screen",
                question=question,
                intent="screening",
                answer=f"近 {ranking_days} 个交易日涨幅排行返回 {len(result.rows)} 只股票。",
                evidence=[f"按全市场近 {ranking_days} 日涨跌幅字段降序排列。"],
                risks=["新股或交易历史不足的股票可能按可用区间计算，需结合上市时间复核。"],
                next_actions=["点击股票代码进入个股研究，复核趋势、波动和追高风险。"],
                metrics=[
                    AskStockMetric(label="候选数量", value=str(len(result.rows)), tone="neutral"),
                    AskStockMetric(
                        label="排行口径",
                        value=f"近{ranking_days}日涨跌幅",
                        tone="neutral",
                    ),
                ],
                observed_at=snapshot.meta.observed_at,
                confidence=snapshot.meta.coverage,
                source="东方财富全市场行情",
                disclaimer="历史涨幅仅用于研究排序，不代表未来收益或买入建议。",
                columns=result.columns,
                rows=result.rows,
            )
        semantic_screener = getattr(self.provider, "query_stock_screen", None)
        if not callable(semantic_screener):
            raise ProviderUnavailable("semantic stock screening is not configured")
        result = await semantic_screener(question, stock_screening_limit(question))
        return AskStockResponse(
            kind="semantic_screen",
            question=question,
            intent="screening",
            answer=f"条件选股增强返回 {len(result.rows)} 个候选结果。",
            evidence=["候选字段与排序由当前自然语言问题和外部语义数据共同决定。"],
            risks=["筛选结果可能延迟或缺少字段，请回到个股研究页核对证据。"],
            next_actions=["选择候选股票后，在问股中输入股票名称或代码继续分析。"],
            metrics=[
                AskStockMetric(label="候选数量", value=str(len(result.rows)), tone="neutral"),
                AskStockMetric(label="增强来源", value="条件选股", tone="neutral"),
            ],
            observed_at=snapshot.meta.observed_at,
            confidence=round(snapshot.meta.coverage * 0.8, 2),
            source="条件选股增强（可选）",
            disclaimer="研究辅助信息，不构成投资建议。",
            columns=result.columns,
            rows=result.rows,
        )

    async def _build_llm_ask_context(
        self,
        *,
        question: str,
        snapshot: MarketSnapshot,
        holdings: list[HoldingItem],
        context_quote: EquityQuote | None,
        context_symbol: str | None,
        context_name: str | None,
        conversation: list[AskStockConversationMessage],
        source_context: AskStockSourceContext | None,
    ) -> LLMWebAskContext:
        quote = context_quote
        if quote is None:
            try:
                quote = resolve_stock_question(question, snapshot.equities)
            except ValueError:
                quote = None
        stock = self._llm_stock_payload(quote, context_symbol, context_name)
        analysis_notes: list[str] = []
        if quote is not None:
            try:
                dossier = await self.stock(quote.symbol)
                analysis_notes = self._llm_analysis_notes(dossier)
            except Exception as error:
                self._provider_errors["llm_context_analysis"] = str(error)
        return LLMWebAskContext(
            question=question,
            conversation=tuple(conversation[-8:]),
            source_context=source_context,
            stock=stock,
            holdings=tuple(self._llm_holding_notes(holdings)),
            observed_at=snapshot.meta.observed_at,
            market_notes=tuple(self._llm_market_notes(snapshot)),
            analysis_notes=tuple(analysis_notes),
        )

    def _llm_analysis_notes(self, dossier: StockDossier) -> list[str]:
        technical = dossier.technical
        score = f"{dossier.stance_score:.0f}" if dossier.stance_score is not None else "缺失"
        notes = [
            f"确定性结论：{dossier.conclusion}",
            (f"研究立场：{dossier.stance}；评分 {score}；证据覆盖 {dossier.evidence_coverage:.0%}"),
            (
                f"处理参考：{dossier.investment_advice.action}；"
                f"仓位 {dossier.investment_advice.position_hint}；"
                f"止损 {dossier.investment_advice.stop_loss}"
            ),
            (
                f"趋势预测：{dossier.trend_forecast.horizon} "
                f"{dossier.trend_forecast.direction}；{dossier.trend_forecast.summary}"
            ),
        ]
        if technical is not None:
            values = (
                f"MA5 {technical.ma5:.2f}" if technical.ma5 is not None else "MA5 缺失",
                f"MA20 {technical.ma20:.2f}" if technical.ma20 is not None else "MA20 缺失",
                f"MA60 {technical.ma60:.2f}" if technical.ma60 is not None else "MA60 缺失",
                f"RSI14 {technical.rsi14:.1f}" if technical.rsi14 is not None else "RSI14 缺失",
                f"支撑 {technical.support:.2f}" if technical.support is not None else "支撑缺失",
                f"压力 {technical.resistance:.2f}"
                if technical.resistance is not None
                else "压力缺失",
            )
            notes.append("技术指标：" + "；".join(values))
        if dossier.bull_case:
            notes.append("正向证据：" + "；".join(dossier.bull_case[:3]))
        if dossier.bear_case:
            notes.append("风险证据：" + "；".join(dossier.bear_case[:3]))
        if dossier.missing_evidence:
            notes.append("证据缺口：" + "；".join(dossier.missing_evidence[:3]))
        if dossier.research_evidence:
            notes.append("研究资料：" + "；".join(dossier.research_evidence[:3]))
        return notes[:10]

    def _llm_stock_payload(
        self,
        quote: EquityQuote | None,
        context_symbol: str | None,
        context_name: str | None,
    ) -> dict[str, str | int | float | None] | None:
        if quote is not None:
            return {
                "symbol": quote.symbol,
                "code": quote.code,
                "name": quote.name,
                "price": quote.price,
                "change_pct": quote.change_pct,
                "amount": quote.amount,
                "turnover_rate": quote.turnover_rate,
                "pe": quote.pe,
                "pb": quote.pb,
                "market_cap": quote.market_cap,
                "net_flow": quote.net_flow,
                "sector": quote.sector,
            }
        if context_symbol or context_name:
            return {"symbol": context_symbol, "name": context_name}
        return None

    def _llm_holding_notes(self, holdings: list[HoldingItem]) -> list[str]:
        notes: list[str] = []
        for item in holdings[:8]:
            holding = self._normalize_holding_item(item)
            notes.append(
                f"{holding.name}({holding.symbol}) 数量{holding.quantity:g} "
                f"成本{holding.cost_price:g} 状态{holding.status}"
            )
        return notes

    def _llm_market_notes(self, snapshot: MarketSnapshot) -> list[str]:
        notes: list[str] = []
        for index in snapshot.indices[:3]:
            change = f"{index.change_pct:+.2f}%" if index.change_pct is not None else "涨跌幅缺失"
            notes.append(f"{index.name} {change}")
        for sector in snapshot.sectors[:3]:
            change = f"{sector.change_pct:+.2f}%" if sector.change_pct is not None else "涨跌幅缺失"
            notes.append(f"{sector.name} {change}")
        return notes

    def _llm_unavailable_answer(
        self,
        question: str,
        snapshot: MarketSnapshot,
        context_quote: EquityQuote | None,
        error: str,
    ) -> AskStockResponse:
        return AskStockResponse(
            kind="llm_answer",
            question=question,
            intent="overview",
            symbol=context_quote.symbol if context_quote is not None else None,
            name=context_quote.name if context_quote is not None else None,
            answer="智能分析暂不可用，当前没有生成可交易结论。请稍后重试，或先打开个股研究页核对本地行情证据。",
            evidence=["智能分析请求未完成，未把旧版规则答案伪装成可用结论。"],
            risks=[error[:180]],
            next_actions=[
                "检查 MARKETDESK_FINANCIAL_LLM_API_KEY / MARKETDESK_FINANCIAL_LLM_MODEL 配置。"
            ],
            observed_at=snapshot.meta.observed_at,
            confidence=0,
            source="金融分析 Skill + 本地证据",
            disclaimer="研究辅助信息，不构成投资建议；交易前请复核公告、行情和账户风险。",
        )

    def _resolve_ask_context_stock(
        self,
        quotes: list[EquityQuote],
        symbol: str | None,
        name: str | None,
    ) -> EquityQuote | None:
        if symbol:
            try:
                normalized_symbol = self._normalize_supported_symbol(symbol)
            except ValueError:
                normalized_symbol = symbol.strip().upper()
            match = next((quote for quote in quotes if quote.symbol == normalized_symbol), None)
            if match is not None:
                return match
        if name:
            try:
                return resolve_stock_question(name, quotes)
            except (StockQuestionNotFound, ValueError):
                return None
        return None

    async def _global_quote(self, symbol: str, name: str | None = None) -> EquityQuote:
        fetcher = getattr(self.provider, "fetch_global_quote", None)
        if not callable(fetcher):
            raise KeyError(symbol)
        try:
            return cast(EquityQuote, await fetcher(symbol, name))
        except Exception as error:
            self._provider_errors["global_market_quote"] = str(error)
            raise KeyError(symbol) from error

    def _global_symbol_from_text(self, text: str) -> str | None:
        for pattern in (r"\bUS\.?\s*([A-Z][A-Z0-9.-]{0,14})\b", r"\bHK\.?\s*(\d{1,5})\b"):
            match = re.search(pattern, text.upper())
            if match is None:
                continue
            prefix = "US" if pattern.startswith(r"\bUS") else "HK"
            try:
                return self._normalize_supported_symbol(f"{prefix}.{match.group(1)}")
            except ValueError:
                continue
        return None

    async def holdings(self, user_id: int | None = None) -> list[HoldingDossier]:
        snapshot = await self.market()
        items = self.store.list_holdings(user_id)
        return await self._analyse_holdings(items, snapshot)

    async def refresh_decision_monitor(self) -> dict[str, int]:
        snapshot = await self.market()
        if snapshot.meta.freshness in {Freshness.STALE, Freshness.UNAVAILABLE}:
            return {"users": 0, "snapshots": 0, "events": 0}

        opportunity_results: dict[str, OpportunityResult] = {}
        for preset in MONITORED_OPPORTUNITY_PRESETS:
            cached = self._opportunity_cache.get(preset)
            try:
                opportunity_results[preset] = (
                    cached[1]
                    if cached is not None and cached[0] == snapshot.meta.fetched_at
                    else await self.opportunities(preset, 1)
                )
            except Exception as error:
                self._provider_errors[f"decision_opportunity_{preset}"] = str(error)

        users = [
            user for user in self.store.list_users() if user.email != "owner@marketdesk.local"
        ]
        snapshot_count = 0
        event_count = 0
        for user in users:
            try:
                holding_items = self.store.list_holdings(user.id)
                holding_dossiers = await self._analyse_holdings(holding_items, snapshot)
                self.store.delete_missing_holding_decision_snapshots(
                    user.id, {str(item.id) for item in holding_items}
                )
                for dossier in holding_dossiers:
                    decision = dossier.decision or holding_decision(dossier.action)
                    event = self.store.record_decision_snapshot(
                        user.id,
                        DecisionSnapshot(
                            source="holding",
                            subject_key=str(dossier.item.id),
                            symbol=dossier.item.symbol,
                            name=dossier.item.name,
                            decision=decision,
                            href=f"/holdings?symbol={dossier.item.symbol}",
                            observed_at=snapshot.meta.fetched_at,
                        ),
                    )
                    snapshot_count += 1
                    event_count += int(event is not None)
                for preset, result in opportunity_results.items():
                    if not result.available or not result.candidates:
                        continue
                    candidate = result.candidates[0]
                    decision = candidate.decision or candidate_decision(candidate)
                    event = self.store.record_decision_snapshot(
                        user.id,
                        DecisionSnapshot(
                            source="opportunity",
                            subject_key=preset,
                            symbol=candidate.quote.symbol,
                            name=candidate.quote.name,
                            strategy=preset,
                            decision=decision,
                            href=(
                                f"/stocks?symbol={candidate.quote.symbol}"
                                f"&from=opportunities&preset={preset}"
                            ),
                            observed_at=snapshot.meta.fetched_at,
                        ),
                    )
                    snapshot_count += 1
                    event_count += int(event is not None)
            except Exception as error:
                self._provider_errors[f"decision_monitor_user_{user.id}"] = str(error)
        return {"users": len(users), "snapshots": snapshot_count, "events": event_count}

    def decision_events(self, user_id: int, limit: int = 100) -> DecisionEventFeed:
        events = self.store.list_decision_events(user_id, limit)
        active_holding_keys = {str(item.id) for item in self.store.list_holdings(user_id)}
        events = [
            event
            for event in events
            if event.source != "holding" or event.subject_key in active_holding_keys
        ]
        return DecisionEventFeed(
            unread_count=sum(event.read_at is None for event in events),
            requires_action=[event for event in events if event.user_required][:50],
            monitoring=[event for event in events if not event.user_required][:50],
            monitored_at=self.store.latest_decision_monitored_at(user_id),
        )

    async def create_holding(
        self, payload: dict[str, Any], user_id: int | None = None
    ) -> HoldingDossier:
        snapshot = await self.market()
        normalized_symbol, canonical_name = await self._resolve_holding_identity(payload, snapshot)
        existing_items = self.store.list_holdings(user_id)
        existing = next(
            (
                item
                for item in existing_items
                if self._normalize_holding_item(item).symbol == normalized_symbol
            ),
            None,
        )
        if existing is not None:
            return await self._analyse_selected_holding(existing_items, snapshot, existing.id)
        normalized_payload = {
            **payload,
            "symbol": normalized_symbol,
            "name": canonical_name,
            "thesis": str(payload.get("thesis") or "").strip()
            or f"{canonical_name} 持仓逻辑待补充，先按价格、资金和板块证据复核。",
            "invalidation": str(payload.get("invalidation") or "").strip()
            or "跌破成本、趋势破位或基本面证据转弱时复核降仓或退出。",
        }
        item = self.store.create_holding(**normalized_payload, user_id=user_id)
        return await self._analyse_selected_holding(
            self.store.list_holdings(user_id), snapshot, item.id
        )

    async def update_holding(
        self, item_id: int, changes: dict[str, Any], user_id: int | None = None
    ) -> HoldingDossier:
        snapshot = await self.market()
        if "symbol" in changes or "name" in changes:
            current = self.store.get_holding(item_id, user_id)
            normalized_symbol, canonical_name = await self._resolve_holding_identity(
                {
                    "symbol": changes.get("symbol", current.symbol),
                    "name": changes.get("name", current.name),
                },
                snapshot,
            )
            for existing in self.store.list_holdings(user_id):
                if (
                    existing.id != item_id
                    and self._normalize_holding_item(existing).symbol == normalized_symbol
                ):
                    raise RuntimeError("holding already exists")
            changes = {**changes, "symbol": normalized_symbol, "name": canonical_name}
        item = self.store.update_holding(item_id, user_id=user_id, **changes)
        return await self._analyse_selected_holding(
            self.store.list_holdings(user_id), snapshot, item.id
        )

    def delete_holding(self, item_id: int, user_id: int | None = None) -> None:
        self.store.delete_holding(item_id, user_id)

    async def _analyse_holdings(
        self, items: list[HoldingItem], snapshot: MarketSnapshot
    ) -> list[HoldingDossier]:
        quote_by_symbol = {quote.symbol: quote for quote in snapshot.equities}
        items = [
            self._repair_holding_item_identity(item, snapshot.equities, quote_by_symbol)
            for item in items
        ]
        for item in items:
            if item.symbol in quote_by_symbol or not item.symbol.startswith(("HK.", "US.")):
                continue
            try:
                quote_by_symbol[item.symbol] = await self._global_quote(item.symbol, item.name)
            except KeyError:
                continue
        bars_by_symbol = await self._holding_bars(items)
        total_market_value = 0.0
        for item in items:
            quote = self._quote_for_holding(item, quote_by_symbol, bars_by_symbol)
            if quote is not None and quote.price is not None:
                total_market_value += item.quantity * quote.price
        return [
            analyse_holding(
                item,
                self._quote_for_holding(item, quote_by_symbol, bars_by_symbol),
                total_market_value or None,
                bars_by_symbol.get(item.symbol),
            )
            for item in items
        ]

    def _normalize_holding_item(self, item: HoldingItem) -> HoldingItem:
        try:
            normalized = self._normalize_supported_symbol(item.symbol)
        except ValueError:
            return item
        return item.model_copy(update={"symbol": normalized})

    def _repair_holding_item_identity(
        self,
        item: HoldingItem,
        quotes: list[EquityQuote],
        quote_by_symbol: dict[str, EquityQuote],
    ) -> HoldingItem:
        normalized = self._normalize_holding_item(item)
        symbol_quote = quote_by_symbol.get(normalized.symbol)
        try:
            name_quote = resolve_stock_question(normalized.name, quotes)
        except (StockQuestionNotFound, ValueError):
            return normalized
        if name_quote.symbol == normalized.symbol:
            return normalized.model_copy(update={"name": name_quote.name})
        if symbol_quote is not None and symbol_quote.name == normalized.name:
            return normalized
        return normalized.model_copy(update={"symbol": name_quote.symbol, "name": name_quote.name})

    async def _resolve_holding_identity(
        self, payload: dict[str, Any], snapshot: MarketSnapshot
    ) -> tuple[str, str]:
        raw_symbol = str(payload.get("symbol") or "").strip()
        raw_name = str(payload.get("name") or "").strip()
        quote_by_symbol = {quote.symbol: quote for quote in snapshot.equities}
        symbol_quote: EquityQuote | None = None
        normalized_symbol: str | None = None

        if raw_symbol:
            try:
                normalized_symbol = self._normalize_supported_symbol(raw_symbol)
            except ValueError as error:
                if raw_name:
                    raise ValueError(
                        "持仓代码必须是 A 股 6 位代码、SH/SZ/BJ.XXXXXX、HK.00700 或 US.AAPL"
                    ) from error
                try:
                    lookup_quote = resolve_stock_question(raw_symbol, snapshot.equities)
                except (StockQuestionNotFound, ValueError) as error:
                    raise ValueError("未找到这只股票，请填写准确代码或名称") from error
                return lookup_quote.symbol, lookup_quote.name
            symbol_quote = quote_by_symbol.get(normalized_symbol)
            if symbol_quote is None and normalized_symbol.startswith(("HK.", "US.")):
                try:
                    symbol_quote = await self._global_quote(normalized_symbol, raw_name or None)
                except Exception as error:
                    raise ValueError("港股/美股代码暂时无法取得行情，请稍后重试") from error

        name_quote: EquityQuote | None = None
        if raw_name:
            try:
                name_quote = resolve_stock_question(raw_name, snapshot.equities)
            except (StockQuestionNotFound, ValueError):
                name_quote = None

        if normalized_symbol and name_quote and name_quote.symbol != normalized_symbol:
            raise ValueError("持仓代码和名称不一致，请核对后再保存")
        if name_quote is not None:
            return name_quote.symbol, name_quote.name
        if normalized_symbol is not None:
            return (
                normalized_symbol,
                symbol_quote.name if symbol_quote is not None else raw_name or normalized_symbol,
            )
        raise ValueError("请填写持仓代码或股票名称")

    @staticmethod
    def _quote_for_holding(
        item: HoldingItem,
        quote_by_symbol: dict[str, EquityQuote],
        bars_by_symbol: dict[str, list[Any]],
    ) -> EquityQuote:
        quote = quote_by_symbol.get(
            item.symbol,
            EquityQuote(
                symbol=item.symbol,
                code=item.symbol.split(".")[-1],
                name=item.name,
            ),
        )
        bars = bars_by_symbol.get(item.symbol) or []
        if quote.price is None and bars:
            return quote.model_copy(update={"price": bars[-1].close})
        return quote

    async def _holding_bars(self, items: list[HoldingItem]) -> dict[str, list[Any]]:
        symbols = list(dict.fromkeys(item.symbol for item in items))
        results = await asyncio.gather(
            *(self.provider.fetch_kline(symbol, limit=12) for symbol in symbols),
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
            (
                dossier
                for dossier in await self._analyse_holdings(items, snapshot)
                if dossier.item.id == selected_id
            ),
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
