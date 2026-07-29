from __future__ import annotations

import asyncio
import re
import time
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
    resolve_stock_question,
)
from marketdesk.analysis.events import analyse_market_events
from marketdesk.analysis.holding import analyse_holding
from marketdesk.analysis.market import analyse_market
from marketdesk.analysis.morning_brief import build_morning_email_brief
from marketdesk.analysis.opportunities import rank_candidates
from marketdesk.analysis.sector import analyse_sector
from marketdesk.analysis.stock import analyse_stock
from marketdesk.config import Settings
from marketdesk.models import (
    AskStockMetric,
    AskStockResponse,
    Bar,
    CapabilityState,
    CapabilityStatus,
    EquityDataset,
    EquityPage,
    EquityQuote,
    EvidenceDocument,
    Freshness,
    HoldingDossier,
    HoldingItem,
    InstrumentEvidenceResult,
    InstrumentTheme,
    MarketEventRaw,
    MarketEventResult,
    MarketIntelligenceResult,
    MarketPayload,
    MarketSnapshot,
    MarketSummarySnapshot,
    MorningEmailBrief,
    OpportunityResult,
    SectorDossier,
    SectorSnapshot,
    StockDossier,
    TradingAnomaly,
)
from marketdesk.providers.base import ProviderUnavailable
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
    async def fetch_filings(
        self, symbol: str, limit: int = 20
    ) -> list[EvidenceDocument]: ...
    async def fetch_research_documents(
        self, symbol: str, limit: int = 20
    ) -> list[EvidenceDocument]: ...
    async def fetch_themes(
        self, symbol: str, limit: int = 30
    ) -> list[InstrumentTheme]: ...
    async def fetch_dragon_tiger(self, limit: int = 20) -> list[TradingAnomaly]: ...


class MarketService:
    def __init__(self, provider: MarketProvider | None = None, store: Store | None = None) -> None:
        settings = Settings()
        self.provider = provider or PublicMarketProvider()
        self.store = store or Store(settings.database_path)
        self._snapshot: MarketSnapshot | None = None
        self._provider_errors: dict[str, str] = {}
        self._capability_cache: dict[str, tuple[float, Any]] = {}
        self._capability_cache_lock = asyncio.Lock()

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

    async def _cached_capability(
        self, key: str, ttl_seconds: float, loader: Any
    ) -> Any:
        cached = self._capability_cache.get(key)
        now = time.monotonic()
        if cached is not None and now - cached[0] < ttl_seconds:
            return cached[1]
        async with self._capability_cache_lock:
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

    async def instrument_evidence(
        self, symbol: str, limit: int = 20
    ) -> InstrumentEvidenceResult:
        normalized = self._require_a_share_symbol(symbol)

        async def load() -> InstrumentEvidenceResult:
            fetched_at = datetime.now(UTC)

            async def fetch(name: str, provider: str, method_name: str) -> tuple[str, list[Any], CapabilityState]:
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
            flow_state = self._capability_state(
                "eastmoney_sector_flow", fetched_at, list(flows)
            )
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
                state.error
                for state in (flow_state, anomaly_state)
                if state.error is not None
            ]
            available_count = int(bool(flows)) + int(bool(anomalies))
            freshness = (
                snapshot.meta.freshness if available_count else Freshness.UNAVAILABLE
            )
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
            await self._cached_capability(
                f"cn-market-intelligence:{limit}", 10 * 60, load
            ),
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

        pairs = await asyncio.gather(*(fetch(symbol) for symbol in unique_symbols))
        return dict(pairs)

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
        initial = rank_candidates(snapshot.equities, regime, preset)
        symbols = [item.quote.symbol for item in initial.candidates[: max(50, limit)]]
        history_by_symbol = await self._opportunity_kline_history(symbols)
        result = rank_candidates(snapshot.equities, regime, preset, history_by_symbol)
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

    async def ask_stock(
        self,
        question: str,
        user_id: int | None = None,
        *,
        context_symbol: str | None = None,
        context_name: str | None = None,
    ) -> AskStockResponse:
        snapshot = await self.market()
        holdings = self.store.list_holdings(user_id) if user_id is not None else []
        context_quote = self._resolve_ask_context_stock(
            snapshot.equities, context_symbol, context_name
        )
        try:
            quote = resolve_stock_question(question, snapshot.equities)
        except StockQuestionNotFound as error:
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
                semantic_screener = getattr(self.provider, "query_stock_screen", None)
                if not callable(semantic_screener):
                    raise ProviderUnavailable(
                        "semantic stock screening is not configured"
                    ) from error
                result = await semantic_screener(question, 20)
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
                    source="条件选股增强（可选）",
                    disclaimer="研究辅助信息，不构成投资建议。",
                    columns=result.columns,
                    rows=result.rows,
                )
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

    def _resolve_ask_context_stock(
        self,
        quotes: list[EquityQuote],
        symbol: str | None,
        name: str | None,
    ) -> EquityQuote | None:
        if symbol:
            try:
                normalized_symbol = self._normalize_a_share_symbol(symbol)
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

    async def holdings(self, user_id: int | None = None) -> list[HoldingDossier]:
        snapshot = await self.market()
        items = self.store.list_holdings(user_id)
        return await self._analyse_holdings(items, snapshot)

    async def create_holding(
        self, payload: dict[str, Any], user_id: int | None = None
    ) -> HoldingDossier:
        normalized_symbol = self._normalize_a_share_symbol(str(payload.get("symbol", "")))
        existing_items = self.store.list_holdings(user_id)
        existing = next(
            (
                item
                for item in existing_items
                if self._normalize_holding_item(item).symbol == normalized_symbol
            ),
            None,
        )
        snapshot = await self.market()
        if existing is not None:
            return await self._analyse_selected_holding(existing_items, snapshot, existing.id)
        normalized_payload = {
            **payload,
            "symbol": normalized_symbol,
        }
        item = self.store.create_holding(**normalized_payload, user_id=user_id)
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
        items = [self._normalize_holding_item(item) for item in items]
        quote_by_symbol = {quote.symbol: quote for quote in snapshot.equities}
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
            normalized = self._normalize_a_share_symbol(item.symbol)
        except ValueError:
            return item
        return item.model_copy(update={"symbol": normalized})

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
