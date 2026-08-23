import asyncio
import contextlib
import time
from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from marketdesk.api import _safe_auto_refresh, create_app
from marketdesk.cli.send_morning_emails import dispatch_morning_emails
from marketdesk.config import Settings
from marketdesk.models import (
    AskStockMetric,
    AskStockResponse,
    Bar,
    DatasetMeta,
    DecisionPresentation,
    DecisionSnapshot,
    EquityQuote,
    EvidenceDocument,
    FinancialPeriod,
    Freshness,
    IndexQuote,
    InstrumentTheme,
    MarketEventRaw,
    RecommendationObservation,
    SectorSnapshot,
    SemanticScreenResult,
    SourceRef,
    StockNewsItem,
    TradingAnomaly,
)
from marketdesk.providers.base import ProviderUnavailable
from marketdesk.providers.llm_web import LLMWebAskContext
from marketdesk.services import MarketService
from marketdesk.store import Store


class FixtureProvider:
    async def fetch_equities(self):
        now = datetime.now(UTC)
        from marketdesk.models import EquityDataset

        return EquityDataset(
            meta=DatasetMeta(
                source="fixture",
                observed_at=now,
                fetched_at=now,
                freshness=Freshness.FRESH,
                coverage=1,
            ),
            items=[
                EquityQuote(
                    symbol="SH.600519",
                    code="600519",
                    name="贵州茅台",
                    price=1500,
                    change_pct=1.2,
                    amount=2_000_000_000,
                    turnover_rate=0.8,
                    volume_ratio=1.1,
                    pe=23,
                    pb=7,
                    market_cap=1_900_000_000_000,
                    net_flow=80_000_000,
                    sector="白酒",
                    exchange="SH",
                    price_limit_pct=10,
                )
            ],
        )

    async def fetch_indices(self):
        return [
            IndexQuote(
                symbol="SH.000001",
                name="上证指数",
                price=3764.15,
                change_pct=-3.05,
                amount=1_246_445_452_836,
            )
        ]

    async def fetch_sectors(self):
        return [SectorSnapshot(code="BK1", name="白酒", change_pct=1.4, net_flow=100_000_000)]

    async def fetch_sector_constituents(self, sector_code: str):
        assert sector_code in {"BK1", "BK0896", "BK100", "BK200"}
        return [
            EquityQuote(
                symbol="SH.600519",
                code="600519",
                name="贵州茅台",
                price=1500,
                change_pct=1.2,
                amount=2_000_000_000,
                turnover_rate=0.8,
                volume_ratio=1.1,
                pe=23,
                pb=7,
                market_cap=1_900_000_000_000,
                net_flow=80_000_000,
                sector="白酒",
                exchange="SH",
                price_limit_pct=10,
            )
        ]

    async def fetch_market_groups(self, kind: str):
        if kind == "concept":
            return [SectorSnapshot(code="BK100", name="酿酒概念", change_pct=1.8, net_flow=80_000_000)]
        return [SectorSnapshot(code="BK200", name="食品饮料", change_pct=1.4, net_flow=100_000_000)]

    async def fetch_raw_kline(self, symbol: str, limit: int = 30):
        return [
            Bar(
                date=date(2026, 8, 20) + timedelta(days=i),
                open=100 * (1.1**i),
                high=100 * (1.1**i),
                low=100 * (1.1**i),
                close=100 * (1.1**i),
                volume=1000,
                amount=100_000,
            )
            for i in range(2)
        ][:limit]

    async def fetch_market_events(self, limit: int = 50):
        now = datetime.now(UTC)
        return [
            MarketEventRaw(
                id="e1",
                title="两家央企宣布增持",
                summary="中国国新、中国诚通继续增持央企和科技企业股票，维护资本市场平稳运行。",
                source="东方财富快讯",
                url="https://finance.eastmoney.com/a/e1.html",
                published_at=now,
                related_symbols=["SH.600519"],
                related_sectors=["央企改革", "科技"],
            ),
            MarketEventRaw(
                id="e2",
                title="中信证券：银行板块兼具绝对和相对收益",
                summary="近期市场风格剧烈波动，低波稳健型资金关注银行板块。",
                source="东方财富快讯",
                url="https://finance.eastmoney.com/a/e2.html",
                published_at=now,
                related_symbols=[],
                related_sectors=["银行"],
            ),
        ][:limit]

    async def fetch_kline(self, symbol: str, limit: int = 180):
        from datetime import date, timedelta

        from marketdesk.models import Bar

        start = date(2026, 1, 1)
        return [
            Bar(
                date=start + timedelta(days=i),
                open=100 + i,
                high=102 + i,
                low=99 + i,
                close=101 + i,
                volume=1000 + i,
                amount=10_000 + i,
            )
            for i in range(70)
        ]

    async def fetch_financial_periods(self, symbol: str, limit: int = 5):
        return [
            FinancialPeriod(
                report_date=date(2026, 6, 30),
                report_label="2026中报",
                report_type="中报",
                revenue_yoy=8.2,
                net_profit_yoy=10.5,
                roe=16.0,
                operating_cash_flow_per_share=1.2,
                cash_receipts_to_revenue=101.0,
                debt_to_assets=32.0,
            )
        ][:limit]

    async def fetch_stock_news(self, symbol: str, name: str, limit: int = 20):
        return [
            StockNewsItem(
                id="fixture-news-1",
                title=f"{name}发布半年报",
                summary="营业收入保持增长。",
                media="测试媒体",
                url="https://example.com/stock-news",
                published_at=datetime.now(UTC),
            )
        ][:limit]

    async def fetch_global_quote(self, symbol: str, name: str | None = None):
        normalized = symbol.strip().upper()
        if normalized in {"HK.700", "HK.00700", "00700"}:
            return EquityQuote(
                symbol="HK.00700",
                code="00700",
                name=name or "腾讯控股",
                price=485.8,
                change_pct=-0.94,
                amount=10_900_000_000,
                turnover_rate=0.25,
                pe=17.74,
                market_cap=4_417_144_410_000,
                sector="港股/HKD",
            )
        if normalized in {"US.AAPL", "AAPL"}:
            return EquityQuote(
                symbol="US.AAPL",
                code="AAPL",
                name=name or "苹果",
                price=303.42,
                change_pct=-1.78,
                amount=22_896_288_310,
                sector="美股/USD",
            )
        raise ProviderUnavailable("global quote unavailable")

    async def search_global_quotes(self, query: str, limit: int = 10):
        normalized = query.strip().lower()
        rows = []
        if normalized in {"腾讯", "00700", "hk.00700"}:
            rows.append(await self.fetch_global_quote("HK.00700"))
        if normalized in {"苹果", "aapl", "us.aapl"}:
            rows.append(await self.fetch_global_quote("US.AAPL"))
        return rows[:limit]


class SectorFailProvider(FixtureProvider):
    async def fetch_sectors(self):
        raise RuntimeError("sector provider unavailable")


class HangingEquityProvider(FixtureProvider):
    async def fetch_equities(self):
        await asyncio.sleep(5)
        return await super().fetch_equities()


class EquityBrowserProvider(FixtureProvider):
    async def fetch_equities(self):
        dataset = await super().fetch_equities()
        return dataset.model_copy(
            update={
                "items": [
                    *dataset.items,
                    EquityQuote(
                        symbol="SZ.000001",
                        code="000001",
                        name="平安银行",
                        price=12.5,
                        change_pct=-0.5,
                        amount=1_000_000_000,
                        turnover_rate=1.2,
                        market_cap=240_000_000_000,
                        sector="银行",
                    ),
                    EquityQuote(
                        symbol="SZ.000002",
                        code="000002",
                        name="万科A",
                        price=8.2,
                        change_pct=3.0,
                        amount=None,
                        turnover_rate=None,
                        market_cap=98_000_000_000,
                    ),
                    EquityQuote(
                        symbol="BJ.430047",
                        code="430047",
                        name="诺思兰德",
                        price=15.8,
                        change_pct=1.5,
                        amount=500_000_000,
                        turnover_rate=2.4,
                        market_cap=4_300_000_000,
                    ),
                ]
            }
        )


class QinglongAskProvider(EquityBrowserProvider):
    async def fetch_equities(self):
        dataset = await super().fetch_equities()
        return dataset.model_copy(
            update={
                "items": [
                    *dataset.items,
                    EquityQuote(
                        symbol="SZ.002457",
                        code="002457",
                        name="青龙管业",
                        price=11.2,
                        change_pct=1.8,
                        amount=520_000_000,
                        turnover_rate=7.2,
                        market_cap=3_700_000_000,
                        sector="水泥建材",
                    ),
                    EquityQuote(
                        symbol="SH.603158",
                        code="603158",
                        name="XD腾龙股",
                        price=8.9,
                        change_pct=-0.3,
                        amount=210_000_000,
                        turnover_rate=2.1,
                        market_cap=4_100_000_000,
                        sector="汽车零部件",
                    ),
                ]
            }
        )


class HoldingNameProvider(EquityBrowserProvider):
    async def fetch_equities(self):
        dataset = await super().fetch_equities()
        return dataset.model_copy(
            update={
                "items": [
                    *dataset.items,
                    EquityQuote(
                        symbol="SZ.002487",
                        code="002487",
                        name="大金重工",
                        price=72.1,
                        change_pct=1.1,
                        amount=850_000_000,
                        turnover_rate=2.8,
                        market_cap=28_000_000_000,
                        sector="风电设备",
                    ),
                ]
            }
        )


class FallingAskProvider(FixtureProvider):
    async def fetch_equities(self):
        dataset = await super().fetch_equities()
        return dataset.model_copy(
            update={
                "items": [
                    *dataset.items,
                    EquityQuote(
                        symbol="SH.603278",
                        code="603278",
                        name="大业股份",
                        price=8.08,
                        change_pct=-8.2,
                        amount=420_000_000,
                        turnover_rate=9.4,
                        volume_ratio=1.9,
                        pe=29,
                        pb=1.7,
                        market_cap=2_800_000_000,
                        net_flow=-36_000_000,
                        sector="金属制品",
                    ),
                ]
            }
        )

    async def fetch_kline(self, symbol: str, limit: int = 180):
        from datetime import date, timedelta

        from marketdesk.models import Bar

        if symbol != "SH.603278":
            return await super().fetch_kline(symbol, limit)
        start = date(2026, 1, 1)
        closes = [13.0 - index * 0.035 for index in range(64)] + [10.4, 10.1, 9.7, 9.2, 8.6, 8.08]
        return [
            Bar(
                date=start + timedelta(days=index),
                open=close + 0.12,
                high=close + 0.28,
                low=max(0.01, close - 0.26),
                close=close,
                volume=1000 + index * 8 + (800 if index >= 65 else 0),
                amount=10_000 + index * 100,
            )
            for index, close in enumerate(closes)
        ]


class StockEnhancementProvider(FixtureProvider):
    async def fetch_equities(self):
        dataset = await super().fetch_equities()
        return dataset.model_copy(
            update={
                "items": [
                    item.model_copy(update={"sector": None, "net_flow": None})
                    for item in dataset.items
                ]
            }
        )

    async def fetch_equity_enrichment(self, symbol: str):
        assert symbol == "SH.600519"
        return {"sector": "白酒Ⅱ", "net_flow": -854_126_672.0}


class ResearchEnhancementProvider(FixtureProvider):
    async def fetch_research_enrichment(self, symbol: str, name: str, sector: str | None):
        assert symbol == "SH.600519"
        assert name == "贵州茅台"
        return ["近三十日有分红相关公告", "研报关注现金流与渠道库存"]


class EvidenceCapabilityProvider(FixtureProvider):
    def __init__(self) -> None:
        self.filing_calls = 0
        self.research_calls = 0
        self.theme_calls = 0
        self.anomaly_calls = 0

    @staticmethod
    def source(provider: str, capability: str) -> SourceRef:
        now = datetime.now(UTC)
        return SourceRef(
            provider=provider,
            label=provider,
            capability=capability,
            source_url="https://example.com/source",
            observed_at=now,
            fetched_at=now,
            freshness=Freshness.FRESH,
        )

    async def fetch_filings(self, symbol: str, limit: int = 20):
        self.filing_calls += 1
        now = datetime.now(UTC)
        return [
            EvidenceDocument(
                id="cninfo:1",
                kind="filing",
                symbol=symbol,
                title="年度权益分派实施公告",
                category="权益分派",
                publisher="巨潮资讯",
                published_at=now,
                url="https://example.com/filing",
                source=self.source("cninfo", "filings"),
            )
        ][:limit]

    async def fetch_research_documents(self, symbol: str, limit: int = 20):
        self.research_calls += 1
        raise ProviderUnavailable("research endpoint unavailable")

    async def fetch_themes(self, symbol: str, limit: int = 30):
        self.theme_calls += 1
        return [
            InstrumentTheme(
                code="BK0896",
                name="酿酒概念",
                change_pct=1.8,
                lead_stock="贵州茅台",
                source=self.source("eastmoney_theme", "themes"),
            )
        ][:limit]

    async def fetch_dragon_tiger(self, limit: int = 20):
        self.anomaly_calls += 1
        return [
            TradingAnomaly(
                symbol="SZ.002475",
                name="立讯精密",
                trade_date=datetime.now(UTC).date(),
                reason="日涨幅偏离值达 7%",
                net_buy=120_000_000,
                source=self.source("eastmoney_datacenter", "dragon_tiger"),
            )
        ][:limit]

    def provider_status(self):
        return {
            "cninfo_filings": {
                "status": "ready",
                "required": False,
                "description": "巨潮公告元数据",
            },
            "eastmoney_research": {
                "status": "unavailable",
                "required": False,
                "description": "东方财富研报元数据",
                "error": "research endpoint unavailable",
            },
        }


class SemanticScreenProvider(FixtureProvider):
    async def query_stock_screen(self, question: str, limit: int = 20) -> SemanticScreenResult:
        assert question == "低估值白酒股"
        assert limit == 20
        return SemanticScreenResult(
            columns=["股票代码", "股票简称", "市盈率"],
            rows=[{"股票代码": "600519", "股票简称": "贵州茅台", "市盈率": 23.0}],
        )


class LLMAskProvider(EquityBrowserProvider):
    def __init__(self) -> None:
        self.received_context: LLMWebAskContext | None = None

    @property
    def llm_web_configured(self) -> bool:
        return True

    async def ask_stock_with_llm(self, context: LLMWebAskContext) -> AskStockResponse:
        self.received_context = context
        return AskStockResponse(
            kind="llm_answer",
            question=context.question,
            intent="overview",
            symbol=context.stock["symbol"] if context.stock else None,
            name=context.stock["name"] if context.stock else None,
            answer="结论：先看最新公告、行业消息和资金变化。",
            evidence=["资料核对已核对最新公开信息。"],
            risks=["公开信息可能滞后。"],
            next_actions=["回到个股研究页复核本地指标。"],
            metrics=[AskStockMetric(label="回答模式", value="智能分析", tone="neutral")],
            observed_at=context.observed_at,
            source="智能分析",
            disclaimer="研究辅助信息，不构成投资建议。",
        )

    async def stream_ask_stock_with_llm(self, context: LLMWebAskContext):
        self.received_context = context
        yield "结论：先看最新公告。\n"
        yield "依据：资料核对已核对最新公开信息。"

    def build_streamed_llm_answer(self, context: LLMWebAskContext, text: str) -> AskStockResponse:
        return AskStockResponse(
            kind="llm_answer",
            question=context.question,
            intent="overview",
            symbol=context.stock["symbol"] if context.stock else None,
            name=context.stock["name"] if context.stock else None,
            answer=text,
            evidence=["资料核对已核对最新公开信息。"],
            risks=["公开信息可能滞后。"],
            next_actions=["回到个股研究页复核本地指标。"],
            metrics=[AskStockMetric(label="回答模式", value="智能分析", tone="neutral")],
            observed_at=context.observed_at,
            source="智能分析",
            disclaimer="研究辅助信息，不构成投资建议。",
        )


class FailingLLMAskProvider(EquityBrowserProvider):
    def __init__(self) -> None:
        self.llm_calls = 0

    @property
    def llm_web_configured(self) -> bool:
        return True

    async def ask_stock_with_llm(self, context: LLMWebAskContext) -> AskStockResponse:
        self.llm_calls += 1
        raise ProviderUnavailable("financial model unavailable")

    async def stream_ask_stock_with_llm(self, context: LLMWebAskContext):
        self.llm_calls += 1
        if False:
            yield ""
        raise ProviderUnavailable("financial model unavailable")


class LLMAndSemanticScreenProvider(LLMAskProvider):
    def __init__(self) -> None:
        super().__init__()
        self.screen_limit: int | None = None

    async def query_stock_screen(self, question: str, limit: int = 20) -> SemanticScreenResult:
        assert question == "A股近十个交易日，综合上涨效果最好的100支股票"
        self.screen_limit = limit
        return SemanticScreenResult(
            columns=["股票代码", "股票简称", "近10日涨跌幅"],
            rows=[
                {
                    "股票代码": f"{index:06d}",
                    "股票简称": f"测试股票{index}",
                    "近10日涨跌幅": 100 - index,
                }
                for index in range(1, 101)
            ],
        )


class LLMAndPeriodRankingProvider(LLMAskProvider):
    def __init__(self) -> None:
        super().__init__()
        self.ranking_request: tuple[int, int] | None = None

    async def fetch_equity_period_ranking(self, days: int, limit: int) -> SemanticScreenResult:
        self.ranking_request = (days, limit)
        return SemanticScreenResult(
            columns=["股票代码", "股票简称", "近10日涨跌幅"],
            rows=[
                {
                    "股票代码": f"{index:06d}",
                    "股票简称": f"测试股票{index}",
                    "近10日涨跌幅": 100 - index,
                }
                for index in range(1, 101)
            ],
        )


def authenticated_client(
    service: MarketService, email: str = "fixture-user@example.com"
) -> TestClient:
    api = TestClient(create_app(service))
    result = api.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "FixturePass-0724",
            "display_name": "Fixture User",
        },
    )
    api.headers["Authorization"] = f"Bearer {result.json()['access_token']}"
    return api


def client(tmp_path) -> TestClient:
    service = MarketService(provider=FixtureProvider(), store=Store(tmp_path / "test.db"))
    return authenticated_client(service)


def test_ask_stock_requires_authentication(tmp_path) -> None:
    service = MarketService(provider=FixtureProvider(), store=Store(tmp_path / "ask-auth.db"))
    response = TestClient(create_app(service)).post(
        "/api/v1/ask-stock", json={"question": "贵州茅台怎么样"}
    )
    assert response.status_code == 401


def test_ask_stock_uses_configured_llm_web_answer_with_context(tmp_path) -> None:
    provider = LLMAskProvider()
    service = MarketService(provider=provider, store=Store(tmp_path / "ask-llm.db"))
    api = authenticated_client(service)

    response = api.post(
        "/api/v1/ask-stock",
        json={
            "question": "它最新有什么需要注意",
            "context_symbol": "SH.600519",
            "context_name": "贵州茅台",
            "conversation": [
                {"role": "user", "content": "贵州茅台主要风险是什么"},
                {"role": "assistant", "content": "先看需求节奏和估值压力。"},
            ],
            "source_context": {
                "origin": "BOARD BRIDGE",
                "label": "从白酒板块复核继续问",
                "detail": "默认围绕 贵州茅台 SH.600519 追问。",
                "stock": {"symbol": "SH.600519", "name": "贵州茅台"},
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["kind"] == "llm_answer"
    assert payload["source"] == "智能分析"
    assert payload["symbol"] == "SH.600519"
    assert payload["name"] == "贵州茅台"
    assert payload["metrics"] == [{"label": "回答模式", "value": "智能分析", "tone": "neutral"}]
    assert provider.received_context is not None
    assert provider.received_context.conversation[-1].content == "先看需求节奏和估值压力。"
    assert provider.received_context.source_context is not None
    assert provider.received_context.source_context.origin == "BOARD BRIDGE"
    assert provider.received_context.stock is not None
    assert provider.received_context.stock["sector"] == "白酒"
    assert any("确定性结论" in note for note in provider.received_context.analysis_notes)
    assert any("技术指标" in note for note in provider.received_context.analysis_notes)


def test_ask_stock_streams_llm_answer_before_final_payload(tmp_path) -> None:
    provider = LLMAskProvider()
    service = MarketService(provider=provider, store=Store(tmp_path / "ask-llm-stream.db"))
    api = authenticated_client(service)

    with api.stream(
        "POST",
        "/api/v1/ask-stock/stream",
        json={"question": "贵州茅台现在主要风险是什么", "context_symbol": "SH.600519"},
    ) as response:
        body = response.read().decode()

    assert response.status_code == 200
    assert "event: status" in body
    assert "event: delta" in body
    assert "结论：先看最新公告" in body
    assert "联网" not in body
    assert "event: final" in body
    assert '"kind": "llm_answer"' in body
    assert provider.received_context is not None
    assert provider.received_context.stock is not None
    assert provider.received_context.stock["symbol"] == "SH.600519"


def test_ask_stock_configured_llm_handles_multi_stock_questions(tmp_path) -> None:
    service = MarketService(provider=LLMAskProvider(), store=Store(tmp_path / "ask-llm-multi.db"))
    api = authenticated_client(service)

    response = api.post("/api/v1/ask-stock", json={"question": "贵州茅台和平安银行哪个更值得关注"})

    assert response.status_code == 200
    assert response.json()["kind"] == "llm_answer"


def test_ask_stock_falls_back_to_deterministic_answer_when_financial_llm_fails(
    tmp_path,
) -> None:
    provider = FailingLLMAskProvider()
    service = MarketService(provider=provider, store=Store(tmp_path / "ask-llm-fallback.db"))
    api = authenticated_client(service)

    response = api.post(
        "/api/v1/ask-stock",
        json={"question": "贵州茅台主要风险是什么"},
    )

    assert response.status_code == 200
    assert response.json()["kind"] == "stock_analysis"
    assert response.json()["source"] == "本地行情快照 + 确定性分析"
    assert provider.llm_calls == 1


def test_ask_stock_stream_falls_back_when_financial_llm_fails(tmp_path) -> None:
    provider = FailingLLMAskProvider()
    service = MarketService(provider=provider, store=Store(tmp_path / "ask-llm-stream-fallback.db"))
    api = authenticated_client(service)

    with api.stream(
        "POST",
        "/api/v1/ask-stock/stream",
        json={"question": "贵州茅台主要风险是什么"},
    ) as response:
        body = response.read().decode()

    assert response.status_code == 200
    assert '"kind": "stock_analysis"' in body
    assert '"source": "本地行情快照 + 确定性分析"' in body
    assert '"kind": "llm_answer"' not in body
    assert provider.llm_calls == 1


def test_ask_stock_routes_top_100_market_ranking_to_semantic_screen(tmp_path) -> None:
    provider = LLMAndSemanticScreenProvider()
    service = MarketService(provider=provider, store=Store(tmp_path / "ask-top-100.db"))
    api = authenticated_client(service)

    response = api.post(
        "/api/v1/ask-stock",
        json={"question": "A股近十个交易日，综合上涨效果最好的100支股票"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["kind"] == "semantic_screen"
    assert payload["intent"] == "screening"
    assert provider.screen_limit == 100
    assert len(payload["rows"]) == 100
    assert payload["rows"][0]["股票简称"] == "测试股票1"


def test_ask_stock_stream_routes_top_100_market_ranking_to_semantic_screen(tmp_path) -> None:
    provider = LLMAndSemanticScreenProvider()
    service = MarketService(provider=provider, store=Store(tmp_path / "ask-top-100-stream.db"))
    api = authenticated_client(service)

    with api.stream(
        "POST",
        "/api/v1/ask-stock/stream",
        json={"question": "A股近十个交易日，综合上涨效果最好的100支股票"},
    ) as response:
        body = response.read().decode()

    assert response.status_code == 200
    assert "event: final" in body
    assert '"kind": "semantic_screen"' in body
    assert '"股票简称": "测试股票100"' in body
    assert "event: delta" not in body
    assert provider.screen_limit == 100
    assert provider.received_context is None


def test_ask_stock_top_100_uses_public_period_ranking_without_semantic_credentials(
    tmp_path,
) -> None:
    provider = LLMAndPeriodRankingProvider()
    service = MarketService(provider=provider, store=Store(tmp_path / "ask-public-ranking.db"))
    api = authenticated_client(service)

    with api.stream(
        "POST",
        "/api/v1/ask-stock/stream",
        json={"question": "A股近十个交易日，综合上涨效果最好的100支股票"},
    ) as response:
        body = response.read().decode()

    assert response.status_code == 200
    assert '"kind": "semantic_screen"' in body
    assert '"股票简称": "测试股票100"' in body
    assert provider.ranking_request == (10, 100)
    assert provider.received_context is None


def test_ask_stock_answers_named_stock_from_deterministic_dossier(tmp_path) -> None:
    api = client(tmp_path)

    response = api.post("/api/v1/ask-stock", json={"question": "贵州茅台主要风险是什么"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["kind"] == "stock_analysis"
    assert payload["intent"] == "risk"
    assert payload["symbol"] == "SH.600519"
    assert payload["name"] == "贵州茅台"
    assert payload["evidence"]
    assert [item["label"] for item in payload["metrics"]] == [
        "综合分",
        "建议动作",
        "证据覆盖",
        "置信度",
        "FINAL GATE",
        "LEDGER GATE",
        "最新价",
        "涨跌幅",
    ]
    assert payload["answer"].startswith("结论：")
    assert not payload["answer"].startswith("FINAL GATE：")
    assert payload["observed_at"]


def test_ask_stock_answers_recent_drop_questions_with_movement_cause(tmp_path) -> None:
    service = MarketService(
        provider=FallingAskProvider(), store=Store(tmp_path / "ask-movement.db")
    )
    api = authenticated_client(service)

    response = api.post("/api/v1/ask-stock", json={"question": "最近大业股份怎么大跌"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["kind"] == "stock_analysis"
    assert payload["intent"] == "movement"
    assert payload["symbol"] == "SH.603278"
    assert payload["name"] == "大业股份"
    assert "近期" in payload["answer"]
    assert "不能直接归因" in payload["answer"]
    assert "近5日" in payload["answer"]
    assert "暂不参与" not in payload["answer"]
    assert any("近5日" in item for item in payload["evidence"])


def test_ask_stock_uses_explicit_context_for_short_followups(tmp_path) -> None:
    api = client(tmp_path)

    response = api.post(
        "/api/v1/ask-stock",
        json={
            "question": "为什么最近大跌",
            "context_symbol": "SH.600519",
            "context_name": "贵州茅台",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["kind"] == "stock_analysis"
    assert payload["intent"] == "movement"
    assert payload["symbol"] == "SH.600519"
    assert payload["name"] == "贵州茅台"
    assert payload["source"] == "本地行情快照 + 确定性分析"


def test_ask_stock_answers_fundamental_and_catalyst_questions(tmp_path) -> None:
    api = client(tmp_path)

    fundamental = api.post("/api/v1/ask-stock", json={"question": "贵州茅台基本面怎么样"})
    catalyst = api.post("/api/v1/ask-stock", json={"question": "贵州茅台有什么公告催化"})

    assert fundamental.status_code == 200
    fundamental_payload = fundamental.json()
    assert fundamental_payload["intent"] == "fundamental"
    assert "基本面" in fundamental_payload["answer"]
    assert "公告研报" in fundamental_payload["answer"]
    assert "当前动作" not in fundamental_payload["answer"]

    assert catalyst.status_code == 200
    catalyst_payload = catalyst.json()
    assert catalyst_payload["intent"] == "catalyst"
    assert "催化" in catalyst_payload["answer"]
    assert "公告研报" in catalyst_payload["answer"]
    assert "当前动作" not in catalyst_payload["answer"]


def test_ask_stock_includes_only_current_user_holding_context(tmp_path) -> None:
    service = MarketService(
        provider=FixtureProvider(), store=Store(tmp_path / "ask-holding-context.db")
    )
    api_a = authenticated_client(service, "holder-a@example.com")
    api_b = authenticated_client(service, "holder-b@example.com")
    holding_payload = {
        "symbol": "SH.600519",
        "name": "贵州茅台",
        "quantity": 10,
        "cost_price": 1400,
        "target_weight": 0.5,
        "thesis": "白酒龙头现金流稳定",
        "invalidation": "跌破长期均线",
    }
    assert api_a.post("/api/v1/holdings", json=holding_payload).status_code == 201

    held_response = api_a.post("/api/v1/ask-stock", json={"question": "我持有的贵州茅台要减仓吗"})
    empty_response = api_b.post("/api/v1/ask-stock", json={"question": "我持有的贵州茅台要减仓吗"})

    assert held_response.status_code == 200
    held = held_response.json()
    assert held["holding_context"]["owned"] is True
    assert held["holding_context"]["quantity"] == 10
    assert "ten_day_change_pct" in held["holding_context"]
    assert "ten_day_contribution" in held["holding_context"]
    assert "结合你的账户持仓" in held["answer"]
    assert "近10日走势" in held["answer"]
    assert "10日贡献" in held["answer"]
    assert "持仓盈亏" in [item["label"] for item in held["metrics"]]
    assert any(item["label"] == "价格与 MA20" for item in held["factors"])

    assert empty_response.status_code == 200
    empty = empty_response.json()
    assert empty["holding_context"] is None
    assert "结合你的账户持仓" not in empty["answer"]


def test_ask_stock_answers_portfolio_question_without_cross_account_leakage(tmp_path) -> None:
    service = MarketService(provider=FixtureProvider(), store=Store(tmp_path / "ask-portfolio.db"))
    api_a = authenticated_client(service, "portfolio-a@example.com")
    api_b = authenticated_client(service, "portfolio-b@example.com")
    assert (
        api_a.post(
            "/api/v1/holdings",
            json={
                "symbol": "SH.600519",
                "name": "贵州茅台",
                "quantity": 10,
                "cost_price": 1700,
                "target_weight": 0.3,
                "thesis": "白酒龙头",
                "invalidation": "跌破支撑",
            },
        ).status_code
        == 201
    )

    response_a = api_a.post("/api/v1/ask-stock", json={"question": "我的持仓里风险最大的是哪个"})
    response_b = api_b.post("/api/v1/ask-stock", json={"question": "我的持仓里风险最大的是哪个"})

    assert response_a.status_code == 200
    payload_a = response_a.json()
    assert payload_a["kind"] == "portfolio_analysis"
    assert payload_a["intent"] == "portfolio"
    assert payload_a["rows"][0]["股票代码"] == "SH.600519"
    assert payload_a["metrics"][0] == {"label": "持仓数量", "value": "1", "tone": "neutral"}

    assert response_b.status_code == 200
    payload_b = response_b.json()
    assert payload_b["kind"] == "portfolio_analysis"
    assert payload_b["metrics"][0] == {"label": "持仓数量", "value": "0", "tone": "missing"}
    assert payload_b["rows"] == []


def test_ask_stock_named_portfolio_diagnostic_uses_current_account_holdings(tmp_path) -> None:
    service = MarketService(
        provider=EquityBrowserProvider(), store=Store(tmp_path / "ask-portfolio-focus.db")
    )
    api_a = authenticated_client(service, "portfolio-focus-a@example.com")
    api_b = authenticated_client(service, "portfolio-focus-b@example.com")
    for payload in (
        {
            "symbol": "SH.600519",
            "name": "贵州茅台",
            "quantity": 10,
            "cost_price": 1700,
            "target_weight": 0.2,
            "thesis": "白酒龙头",
            "invalidation": "跌破支撑",
        },
        {
            "symbol": "SZ.000001",
            "name": "平安银行",
            "quantity": 1000,
            "cost_price": 12,
            "target_weight": 0.2,
            "thesis": "低估值银行",
            "invalidation": "净息差继续下行",
        },
        {
            "symbol": "BJ.430047",
            "name": "诺思兰德",
            "quantity": 1000,
            "cost_price": 13,
            "target_weight": 0.2,
            "thesis": "北交所成长观察",
            "invalidation": "成交萎缩",
        },
    ):
        assert api_a.post("/api/v1/holdings", json=payload).status_code == 201

    response_a = api_a.post(
        "/api/v1/ask-stock", json={"question": "我的持仓里贵州茅台占比是不是太高"}
    )
    treatment_a = api_a.post(
        "/api/v1/ask-stock",
        json={"question": "我的持仓里贵州茅台风险怎么处理"},
    )
    response_b = api_b.post(
        "/api/v1/ask-stock", json={"question": "我的持仓里贵州茅台占比是不是太高"}
    )

    assert response_a.status_code == 200
    payload_a = response_a.json()
    assert payload_a["kind"] == "portfolio_analysis"
    assert "贵州茅台（SH.600519）在当前组合风险排序第" in payload_a["answer"]
    assert "最大单票占比" in payload_a["answer"]
    assert [item["label"] for item in payload_a["metrics"]] == [
        "持仓数量",
        "总市值",
        "最大单票",
        "行业集中",
        "风险持仓",
        "最需复核",
    ]
    assert payload_a["columns"] == [
        "股票代码",
        "股票简称",
        "行业",
        "组合占比",
        "盈亏",
        "10日走势",
        "10日贡献",
        "动作",
        "风险",
    ]
    assert "10日走势" in payload_a["rows"][0]
    assert "10日贡献" in payload_a["rows"][0]
    assert any(item["label"] == "最大单票集中度" for item in payload_a["factors"])
    assert {row["股票代码"] for row in payload_a["rows"]} == {
        "SH.600519",
        "SZ.000001",
        "BJ.430047",
    }

    assert treatment_a.status_code == 200
    treatment_payload = treatment_a.json()
    assert treatment_payload["kind"] == "portfolio_analysis"
    assert treatment_payload["intent"] == "portfolio"
    assert "贵州茅台（SH.600519）在当前组合风险排序第" in treatment_payload["answer"]
    assert any(row["股票代码"] == "SH.600519" for row in treatment_payload["rows"])

    assert response_b.status_code == 200
    payload_b = response_b.json()
    assert payload_b["kind"] == "portfolio_analysis"
    assert payload_b["metrics"][0] == {"label": "持仓数量", "value": "0", "tone": "missing"}
    assert payload_b["rows"] == []


def test_ask_stock_generates_account_scoped_rebalance_plan(tmp_path) -> None:
    service = MarketService(
        provider=EquityBrowserProvider(), store=Store(tmp_path / "ask-rebalance-plan.db")
    )
    api_a = authenticated_client(service, "rebalance-a@example.com")
    api_b = authenticated_client(service, "rebalance-b@example.com")
    for payload in (
        {
            "symbol": "SH.600519",
            "name": "贵州茅台",
            "quantity": 10,
            "cost_price": 1700,
            "target_weight": 0.2,
            "thesis": "白酒龙头",
            "invalidation": "跌破支撑",
        },
        {
            "symbol": "SZ.000001",
            "name": "平安银行",
            "quantity": 1000,
            "cost_price": 12,
            "target_weight": 0.5,
            "thesis": "低估值银行",
            "invalidation": "净息差继续下行",
        },
        {
            "symbol": "BJ.430047",
            "name": "诺思兰德",
            "quantity": 1000,
            "cost_price": 13,
            "target_weight": 0.3,
            "thesis": "北交所成长观察",
            "invalidation": "成交萎缩",
        },
    ):
        assert api_a.post("/api/v1/holdings", json=payload).status_code == 201

    response_a = api_a.post("/api/v1/ask-stock", json={"question": "帮我生成调仓计划"})
    response_b = api_b.post("/api/v1/ask-stock", json={"question": "帮我生成调仓计划"})

    assert response_a.status_code == 200
    payload_a = response_a.json()
    assert payload_a["kind"] == "portfolio_analysis"
    assert "调仓计划先处理" in payload_a["answer"]
    assert "持仓盈亏" in payload_a["answer"]
    assert [item["label"] for item in payload_a["metrics"]] == [
        "持仓数量",
        "总市值",
        "待复核",
        "最大单票",
        "行业集中",
        "风险持仓",
        "最需复核",
    ]
    assert payload_a["columns"] == [
        "股票代码",
        "股票简称",
        "行业",
        "组合占比",
        "盈亏",
        "10日走势",
        "10日贡献",
        "优先级",
        "动作",
        "风险",
    ]
    assert "近10日" in payload_a["answer"]
    assert "10日贡献" in payload_a["rows"][0]
    assert payload_a["rows"][0]["优先级"] == "高"
    assert any(item["label"] == "调仓执行量" for item in payload_a["factors"])
    assert any("不按表格机械交易" in item for item in payload_a["next_actions"])

    assert response_b.status_code == 200
    payload_b = response_b.json()
    assert payload_b["kind"] == "portfolio_analysis"
    assert payload_b["metrics"][0] == {"label": "持仓数量", "value": "0", "tone": "missing"}
    assert payload_b["rows"] == []


def test_ask_stock_validates_question_length(tmp_path) -> None:
    api = client(tmp_path)
    assert api.post("/api/v1/ask-stock", json={"question": " "}).status_code == 422
    assert api.post("/api/v1/ask-stock", json={"question": "茅" * 161}).status_code == 422


def test_ask_stock_rejects_multiple_local_stocks(tmp_path) -> None:
    service = MarketService(
        provider=EquityBrowserProvider(), store=Store(tmp_path / "ask-ambiguous.db")
    )
    api = authenticated_client(service)

    response = api.post("/api/v1/ask-stock", json={"question": "贵州茅台和平安银行哪个更好"})

    assert response.status_code == 422
    assert response.json()["detail"] == "一次只问一只股票"


def test_ask_stock_accepts_colloquial_qinglong_share_name(tmp_path) -> None:
    service = MarketService(
        provider=QinglongAskProvider(), store=Store(tmp_path / "ask-qinglong.db")
    )
    api = authenticated_client(service)

    response = api.post("/api/v1/ask-stock", json={"question": "为什么是青龙股份"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["kind"] == "stock_analysis"
    assert payload["symbol"] == "SZ.002457"
    assert payload["name"] == "青龙管业"


def test_ask_stock_uses_optional_semantic_screen(tmp_path) -> None:
    service = MarketService(
        provider=SemanticScreenProvider(), store=Store(tmp_path / "ask-semantic.db")
    )
    api = authenticated_client(service)

    response = api.post("/api/v1/ask-stock", json={"question": "低估值白酒股"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["kind"] == "semantic_screen"
    assert payload["intent"] == "screening"
    assert payload["answer"] == "条件选股增强返回 1 个候选结果。"
    assert payload["source"] == "条件选股增强（可选）"
    assert payload["metrics"] == [
        {"label": "候选数量", "value": "1", "tone": "neutral"},
        {"label": "增强来源", "value": "条件选股", "tone": "neutral"},
    ]
    assert payload["columns"] == ["股票代码", "股票简称", "市盈率"]
    assert payload["rows"][0]["股票代码"] == "600519"
    assert "问财" not in str(payload)


def test_ask_stock_semantic_unavailable_does_not_break_market(tmp_path) -> None:
    api = client(tmp_path)

    response = api.post("/api/v1/ask-stock", json={"question": "低估值白酒股"})

    assert response.status_code == 503
    assert (
        response.json()["detail"]
        == "条件选股增强暂不可用；你也可以在问题中包含一个 A 股股票名称或代码继续分析。"
    )
    assert "问财" not in response.json()["detail"]
    assert api.get("/api/v1/market").status_code == 200


def test_application_routes_require_authentication(tmp_path) -> None:
    service = MarketService(provider=FixtureProvider(), store=Store(tmp_path / "auth-boundary.db"))
    api = TestClient(create_app(service))

    for path in (
        "/api/v1/auth/me",
        "/api/v1/preferences",
        "/api/v1/market",
        "/api/v1/equities",
        "/api/v1/market-events",
        "/api/v1/instruments/SH.600519/evidence",
        "/api/v1/markets/CN/intelligence",
        "/api/v1/sectors/BK1",
        "/api/v1/opportunities",
        "/api/v1/recommendation-history",
        "/api/v1/search?q=SH.600519",
        "/api/v1/stocks/SH.600519",
        "/api/v1/data-status",
        "/api/v1/holdings",
        "/api/v1/watchlist",
        "/api/v1/equity-views",
    ):
        assert api.get(path).status_code == 401

    assert api.post("/api/v1/refresh").status_code == 401
    registration = api.post(
        "/api/v1/auth/register",
        json={
            "email": "gate-user@example.com",
            "password": "GatePass-0725",
            "display_name": "Gate User",
        },
    )
    assert registration.status_code == 201
    assert (
        api.post(
            "/api/v1/auth/login",
            json={"email": "gate-user@example.com", "password": "GatePass-0725"},
        ).status_code
        == 200
    )


def test_market_and_stock_routes(tmp_path) -> None:
    api = client(tmp_path)

    market = api.get("/api/v1/market")
    stock = api.get("/api/v1/stocks/SH.600519")

    assert market.status_code == 200
    market_payload = market.json()
    assert market_payload["snapshot"]["meta"]["source"] == "fixture"
    assert market_payload["snapshot"]["indices"][0]["symbol"] == "SH.000001"
    assert market_payload["snapshot"]["sectors"][0]["code"] == "BK1"
    assert "equities" not in market_payload["snapshot"]
    stock_payload = stock.json()
    assert stock_payload["stance"] in {"strong_watch", "watch", "neutral", "avoid"}
    assert "signal_validation" in stock_payload
    assert stock_payload["technical"]["macd_histogram"] is not None
    assert stock_payload["technical"]["atr_pct"] is not None
    assert stock_payload["financial_health"]["available"] is True
    assert stock_payload["financial_health"]["periods"][0]["report_label"] == "2026中报"
    assert stock_payload["news_sentiment"]["available"] is True
    assert stock_payload["news_sentiment"]["items"][0]["media"] == "测试媒体"


def test_market_structure_routes_share_snapshot_and_return_drilldown_models(tmp_path) -> None:
    api = client(tmp_path)

    dashboard = api.get("/api/v1/market-structure/dashboard")
    strategies = api.get("/api/v1/market-structure/strategies")
    ladder = api.get("/api/v1/market-structure/limit-ladder", params={"mode": "up"})
    concepts = api.get("/api/v1/market-structure/groups", params={"kind": "concept"})
    industries = api.get("/api/v1/market-structure/groups", params={"kind": "industry"})

    assert dashboard.status_code == 200
    assert strategies.status_code == 200
    assert ladder.status_code == 200
    assert concepts.status_code == 200
    assert industries.status_code == 200
    assert dashboard.json()["meta"]["observed_at"] == strategies.json()["meta"]["observed_at"]
    assert strategies.json()["cards"][0]["id"] == "trend"
    assert concepts.json()["groups"][0]["kind"] == "concept"
    assert industries.json()["groups"][0]["kind"] == "industry"


def test_market_group_detail_hydrates_a_group_outside_catalog_prefetch(tmp_path) -> None:
    class ManyGroupProvider(FixtureProvider):
        async def fetch_market_groups(self, kind: str):
            return [
                SectorSnapshot(
                    code=f"BK{index:03d}",
                    name=f"测试{kind}{index}",
                    change_pct=index / 10,
                    net_flow=index * 1_000_000,
                )
                for index in range(1, 26)
            ]

        async def fetch_sector_constituents(self, sector_code: str):
            return await FixtureProvider.fetch_sector_constituents(self, "BK100")

    service = MarketService(
        provider=ManyGroupProvider(),
        store=Store(tmp_path / "group-detail.db"),
    )
    api = authenticated_client(service)

    catalog = api.get("/api/v1/market-structure/groups", params={"kind": "concept"})
    catalog_group = next(
        item for item in catalog.json()["groups"] if item["code"] == "BK025"
    )
    detail = api.get("/api/v1/market-structure/groups/concept/BK025")

    assert catalog.status_code == 200
    assert catalog_group["constituent_count"] == 0
    assert detail.status_code == 200
    detail_payload = detail.json()
    assert detail_payload["degraded"] is False
    assert detail_payload["groups"][0]["code"] == "BK025"
    assert detail_payload["groups"][0]["constituent_count"] == 1
    assert detail_payload["groups"][0]["leader"]["quote"]["name"] == "贵州茅台"
    assert detail_payload["groups"][0]["advancing"] == 1
    assert detail_payload["groups"][0]["missing_evidence"] == []
    assert api.get("/api/v1/market-structure/groups/concept/BK999").status_code == 404


def test_market_group_detail_retries_empty_constituent_responses(tmp_path) -> None:
    class RetryGroupProvider(FixtureProvider):
        target_attempts = 0

        async def fetch_market_groups(self, kind: str):
            return [
                SectorSnapshot(code=f"BK{index:03d}", name=f"测试{index}")
                for index in range(1, 26)
            ]

        async def fetch_sector_constituents(self, sector_code: str):
            if sector_code == "BK025":
                self.target_attempts += 1
                if self.target_attempts == 1:
                    return []
            return await FixtureProvider.fetch_sector_constituents(self, "BK100")

    provider = RetryGroupProvider()
    service = MarketService(
        provider=provider,
        store=Store(tmp_path / "group-detail-retry.db"),
    )
    api = authenticated_client(service)

    first = api.get("/api/v1/market-structure/groups/concept/BK025")
    second = api.get("/api/v1/market-structure/groups/concept/BK025")

    assert first.status_code == 200
    assert first.json()["degraded"] is True
    assert first.json()["groups"][0]["constituent_count"] == 0
    assert second.status_code == 200
    assert second.json()["degraded"] is False
    assert second.json()["groups"][0]["constituent_count"] == 1
    assert provider.target_attempts == 2


@pytest.mark.asyncio
async def test_market_group_monitor_prewarms_top_missing_groups(tmp_path) -> None:
    class WarmGroupProvider(FixtureProvider):
        target_calls = 0

        async def fetch_market_groups(self, kind: str):
            prefix = "BK" if kind == "concept" else "BI"
            return [
                SectorSnapshot(
                    code=f"{prefix}{index:03d}",
                    name=f"测试{kind}{index}",
                    change_pct=10 if index == 25 else 0,
                    net_flow=3_000_000_000 if index == 25 else 0,
                )
                for index in range(1, 26)
            ]

        async def fetch_sector_constituents(self, sector_code: str):
            if sector_code.endswith("025"):
                self.target_calls += 1
            return await FixtureProvider.fetch_sector_constituents(self, "BK100")

    provider = WarmGroupProvider()
    service = MarketService(
        provider=provider,
        store=Store(tmp_path / "group-monitor.db"),
    )

    result = await service.refresh_market_group_monitor(limit=1)
    calls_after_warm = provider.target_calls
    concept = await service.market_group_detail("concept", "BK025")
    industry = await service.market_group_detail("industry", "BI025")

    assert result == {"groups": 2, "ready": 2}
    assert concept is not None and concept.groups[0].constituent_count == 1
    assert industry is not None and industry.groups[0].constituent_count == 1
    assert calls_after_warm == 2
    assert provider.target_calls == calls_after_warm


@pytest.mark.asyncio
async def test_market_groups_keep_last_good_result_when_catalog_refresh_fails(tmp_path) -> None:
    class FlakyGroupProvider(FixtureProvider):
        fail_groups = False

        async def fetch_market_groups(self, kind: str):
            if self.fail_groups:
                raise ProviderUnavailable("catalog timeout")
            return await super().fetch_market_groups(kind)

    provider = FlakyGroupProvider()
    service = MarketService(provider=provider, store=Store(tmp_path / "groups-last-good.db"))

    first = await service.market_groups("concept")
    provider.fail_groups = True
    service._market_structure_cache.clear()
    degraded = await service.market_groups("concept")

    assert first.available is True
    assert degraded.available is True
    assert degraded.degraded is True
    assert degraded.meta.freshness == Freshness.STALE
    assert degraded.groups == first.groups
    assert degraded.unavailable_reason is not None
    assert "catalog timeout" in degraded.unavailable_reason


def test_stock_financial_and_news_failures_degrade_independently(tmp_path) -> None:
    class FinancialFailureProvider(FixtureProvider):
        async def fetch_financial_periods(self, symbol: str, limit: int = 5):
            raise ProviderUnavailable("financial timeout")

    class NewsFailureProvider(FixtureProvider):
        async def fetch_stock_news(self, symbol: str, name: str, limit: int = 20):
            raise ProviderUnavailable("news timeout")

    finance_api = authenticated_client(
        MarketService(
            provider=FinancialFailureProvider(),
            store=Store(tmp_path / "finance-failure.db"),
        )
    )
    news_api = authenticated_client(
        MarketService(
            provider=NewsFailureProvider(),
            store=Store(tmp_path / "news-failure.db"),
        )
    )

    finance_response = finance_api.get("/api/v1/stocks/SH.600519")
    news_response = news_api.get("/api/v1/stocks/SH.600519")

    assert finance_response.status_code == 200
    assert finance_response.json()["financial_health"]["available"] is False
    assert finance_response.json()["news_sentiment"]["available"] is True
    assert news_response.status_code == 200
    assert news_response.json()["financial_health"]["available"] is True
    assert news_response.json()["news_sentiment"]["available"] is False


def test_stock_financial_and_news_are_cached_between_page_opens(tmp_path) -> None:
    class CountingProvider(FixtureProvider):
        def __init__(self) -> None:
            self.financial_calls = 0
            self.news_calls = 0

        async def fetch_financial_periods(self, symbol: str, limit: int = 5):
            self.financial_calls += 1
            return await super().fetch_financial_periods(symbol, limit)

        async def fetch_stock_news(self, symbol: str, name: str, limit: int = 20):
            self.news_calls += 1
            return await super().fetch_stock_news(symbol, name, limit)

    provider = CountingProvider()
    api = authenticated_client(
        MarketService(provider=provider, store=Store(tmp_path / "stock-cache.db"))
    )

    assert api.get("/api/v1/stocks/SH.600519").status_code == 200
    assert api.get("/api/v1/stocks/SH.600519").status_code == 200

    assert provider.financial_calls == 1
    assert provider.news_calls == 1


@pytest.mark.asyncio
async def test_stock_reuses_monitored_history_when_live_kline_fails(tmp_path) -> None:
    class IntermittentKlineProvider(FixtureProvider):
        fail_kline = False

        async def fetch_kline(self, symbol: str, limit: int = 180):
            if self.fail_kline:
                raise ProviderUnavailable("temporary K-line failure")
            return await super().fetch_kline(symbol, limit)

    provider = IntermittentKlineProvider()
    service = MarketService(provider=provider, store=Store(tmp_path / "stock-history.db"))
    await service.refresh_opportunity_monitor("trend", limit=1)

    provider.fail_kline = True
    dossier = await service.stock("SH.600519")

    assert len(dossier.bars) == 70
    assert dossier.technical is not None
    assert dossier.stance != "insufficient_data"


@pytest.mark.asyncio
async def test_stock_returns_safe_decision_when_kline_is_unavailable(tmp_path) -> None:
    class UnavailableKlineProvider(FixtureProvider):
        async def fetch_kline(self, symbol: str, limit: int = 180):
            raise ProviderUnavailable("temporary K-line failure")

    service = MarketService(
        provider=UnavailableKlineProvider(), store=Store(tmp_path / "stock-degraded.db")
    )

    dossier = await service.stock("SH.600519")

    assert dossier.stance == "insufficient_data"
    assert dossier.investment_advice.action == "暂不参与"
    assert dossier.bars == []


def test_opportunities_route_enriches_top_candidates_with_history(tmp_path) -> None:
    api = client(tmp_path)

    response = api.get("/api/v1/opportunities", params={"preset": "trend", "limit": 1})

    assert response.status_code == 200
    candidate = response.json()["candidates"][0]
    assert candidate["history_check"]["available"] is True
    assert candidate["history_check"]["lookback_days"] == 70
    assert candidate["history_check"]["trend_20d_pct"] is not None
    assert "历史确认" in {item["label"] for item in candidate["dimensions"]}
    assert "历史确认" in {item["label"] for item in candidate["components"]}


def test_recommendation_history_freezes_one_daily_run_and_tracks_current_price(
    tmp_path,
) -> None:
    api = client(tmp_path)

    first = api.get("/api/v1/recommendation-history")
    second = api.get("/api/v1/recommendation-history")

    assert first.status_code == 200
    assert second.status_code == 200
    payload = second.json()
    assert payload["preset"] == "trend"
    assert payload["summary"]["run_count"] == 1
    assert payload["summary"]["pick_count"] == 1
    assert payload["summary"]["evaluated_count"] == 0
    assert payload["days"][0]["picks"][0]["symbol"] == "SH.600519"
    assert payload["days"][0]["picks"][0]["entry_price"] == 1500
    assert payload["days"][0]["picks"][0]["current_return"] == 0
    assert payload["days"][0]["picks"][0]["status"] == "tracking"
    assert "自动刷新归档" in payload["methodology"][1]
    assert "首次启用" in payload["methodology"][4]


def test_opportunities_route_accepts_strict_new_strategy_preset(tmp_path) -> None:
    api = client(tmp_path)

    response = api.get("/api/v1/opportunities", params={"preset": "capital_confirmed", "limit": 1})

    assert response.status_code == 200
    payload = response.json()
    assert payload["preset"] == "capital_confirmed"
    candidate = payload["candidates"][0]
    assert candidate["strategy_validation"]["passed"] is True
    assert "资金净流入 >= 2000 万" in candidate["strategy_validation"]["checks"]
    assert "策略校验" in {item["label"] for item in candidate["dimensions"]}


def test_sector_strategy_uses_snapshot_sector_strength(tmp_path) -> None:
    api = client(tmp_path)

    response = api.get("/api/v1/opportunities", params={"preset": "sector_momentum", "limit": 1})

    assert response.status_code == 200
    candidate = response.json()["candidates"][0]
    strategy_fit = next(item for item in candidate["dimensions"] if item["key"] == "strategy_fit")
    assert "白酒 板块涨跌 +1.4%" in strategy_fit["summary"]
    assert "板块强度数据暂缺" not in candidate["risk_flags"]


class ManyExcludedOpportunityProvider(FixtureProvider):
    async def fetch_equities(self):
        dataset = await super().fetch_equities()
        extras = [
            EquityQuote(
                symbol=f"SZ.{i:06d}",
                code=f"{i:06d}",
                name=f"ST样本{i}",
                price=8.0,
                change_pct=-1.0,
                amount=1_000_000,
                turnover_rate=0.2,
                volume_ratio=0.6,
                pe=30,
                pb=2,
                market_cap=5_000_000_000,
                net_flow=-1_000_000,
                sector="测试",
            )
            for i in range(300000, 300500)
        ]
        return dataset.model_copy(update={"items": [*dataset.items, *extras]})


def test_opportunities_route_does_not_send_full_excluded_universe(tmp_path) -> None:
    service = MarketService(
        provider=ManyExcludedOpportunityProvider(),
        store=Store(tmp_path / "opportunity-payload.db"),
    )
    api = authenticated_client(service)

    response = api.get("/api/v1/opportunities", params={"preset": "trend", "limit": 1})

    assert response.status_code == 200
    payload = response.json()
    assert payload["funnel"]["excluded"] >= 500
    assert payload["excluded"] == []
    assert len(response.content) < 80_000


class HangingKlineProvider(FixtureProvider):
    async def fetch_kline(self, symbol: str, limit: int = 180):
        await asyncio.sleep(60)
        return []


def test_opportunities_route_degrades_when_history_provider_hangs(tmp_path) -> None:
    service = MarketService(
        provider=HangingKlineProvider(), store=Store(tmp_path / "opportunity-timeout.db")
    )
    service._opportunity_kline_timeout_seconds = 0.01
    api = authenticated_client(service)

    started = time.monotonic()
    response = api.get("/api/v1/opportunities", params={"preset": "trend", "limit": 1})
    elapsed = time.monotonic() - started

    assert response.status_code == 200
    assert elapsed < 1
    payload = response.json()
    assert payload["candidates"][0]["quote"]["symbol"] == "SH.600519"
    assert payload["candidates"][0]["history_check"]["available"] is False
    assert payload["candidates"][0]["history_check"]["lookback_days"] == 0


def test_equity_browser_searches_sorts_and_paginates(tmp_path) -> None:
    service = MarketService(provider=EquityBrowserProvider(), store=Store(tmp_path / "equities.db"))
    api = authenticated_client(service)

    response = api.get(
        "/api/v1/equities",
        params={"sort_by": "amount", "direction": "desc", "page": 1, "page_size": 2},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    payload = response.json()
    assert payload["total"] == 4
    assert payload["page"] == 1
    assert payload["page_size"] == 2
    assert payload["exchange"] == "all"
    assert [item["symbol"] for item in payload["items"]] == ["SH.600519", "SZ.000001"]
    assert "equities" not in payload

    second_page = api.get(
        "/api/v1/equities",
        params={"sort_by": "amount", "direction": "desc", "page": 2, "page_size": 2},
    ).json()
    assert [item["symbol"] for item in second_page["items"]] == ["BJ.430047", "SZ.000002"]

    missing_last = api.get(
        "/api/v1/equities",
        params={"sort_by": "amount", "direction": "asc", "page": 1, "page_size": 4},
    ).json()
    assert missing_last["items"][-1]["amount"] is None

    search = api.get("/api/v1/equities", params={"q": "茅台"}).json()
    assert search["total"] == 1
    assert search["items"][0]["symbol"] == "SH.600519"

    code_search = api.get("/api/v1/equities", params={"q": "000001"}).json()
    assert code_search["items"][0]["name"] == "平安银行"

    beijing = api.get("/api/v1/equities", params={"exchange": "bj"}).json()
    assert beijing["exchange"] == "bj"
    assert beijing["total"] == 1
    assert beijing["items"][0]["symbol"] == "BJ.430047"

    shenzhen_search = api.get("/api/v1/equities", params={"exchange": "sz", "q": "000001"}).json()
    assert shenzhen_search["total"] == 1
    assert shenzhen_search["items"][0]["name"] == "平安银行"


def test_advanced_equity_filters_combine_and_report_real_sectors(tmp_path) -> None:
    service = MarketService(
        provider=EquityBrowserProvider(), store=Store(tmp_path / "advanced-equities.db")
    )
    api = authenticated_client(service)

    response = api.get(
        "/api/v1/equities",
        params={
            "sector": "白酒",
            "min_change_pct": 1,
            "max_change_pct": 2,
            "min_amount": 1_500_000_000,
            "min_turnover_rate": 0.5,
            "max_turnover_rate": 1,
            "min_market_cap": 1_000_000_000_000,
            "complete_only": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert [item["symbol"] for item in payload["items"]] == ["SH.600519"]
    assert payload["available_sectors"] == ["白酒", "银行"]


@pytest.mark.parametrize(
    ("minimum", "maximum"),
    [
        ("min_change_pct", "max_change_pct"),
        ("min_amount", "max_amount"),
        ("min_turnover_rate", "max_turnover_rate"),
        ("min_market_cap", "max_market_cap"),
    ],
)
def test_advanced_equity_filters_reject_inverted_ranges(
    tmp_path, minimum: str, maximum: str
) -> None:
    api = authenticated_client(
        MarketService(provider=EquityBrowserProvider(), store=Store(tmp_path / f"{minimum}.db"))
    )

    response = api.get("/api/v1/equities", params={minimum: 2, maximum: 1})

    assert response.status_code == 422


def test_market_events_route_returns_classified_hot_events(tmp_path) -> None:
    api = client(tmp_path)

    response = api.get("/api/v1/market-events")

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["source"] == "eastmoney_fast_news"
    assert payload["events"][0]["category"] == "policy_support"
    assert payload["events"][0]["impact"] != ""
    assert payload["clusters"][0]["label"] in {"政策与监管", "资金与风格"}
    assert any("央企改革" in item for item in payload["summary"])
    assert any("公告/政策原文" in item for item in payload["next_actions"])


def test_instrument_evidence_returns_partial_sources_and_uses_ttl_cache(tmp_path) -> None:
    provider = EvidenceCapabilityProvider()
    service = MarketService(provider=provider, store=Store(tmp_path / "evidence.db"))
    api = authenticated_client(service)

    first = api.get("/api/v1/instruments/SH.600519/evidence", params={"limit": 10})
    second = api.get("/api/v1/instruments/SH.600519/evidence", params={"limit": 10})

    assert first.status_code == 200
    payload = first.json()
    assert payload["symbol"] == "SH.600519"
    assert payload["filings"][0]["source"]["provider"] == "cninfo"
    assert payload["research"] == []
    assert payload["themes"][0]["name"] == "酿酒概念"
    assert payload["capabilities"]["filings"]["status"] == "ready"
    assert payload["capabilities"]["research"]["status"] == "unavailable"
    assert "research endpoint unavailable" in payload["capabilities"]["research"]["error"]
    assert second.json() == payload
    assert (provider.filing_calls, provider.research_calls, provider.theme_calls) == (1, 1, 1)


def test_cn_market_intelligence_returns_flow_and_latest_anomalies(tmp_path) -> None:
    provider = EvidenceCapabilityProvider()
    service = MarketService(provider=provider, store=Store(tmp_path / "intelligence.db"))
    api = authenticated_client(service)

    first = api.get("/api/v1/markets/CN/intelligence", params={"limit": 10})
    second = api.get("/api/v1/markets/CN/intelligence", params={"limit": 10})

    assert first.status_code == 200
    payload = first.json()
    assert payload["meta"]["source"] == "eastmoney_sector_flow+eastmoney_dragon_tiger"
    assert payload["sector_flows"][0]["name"] == "白酒"
    assert payload["anomalies"][0]["symbol"] == "SZ.002475"
    assert payload["capabilities"]["sector_flows"]["status"] == "ready"
    assert payload["capabilities"]["dragon_tiger"]["status"] == "ready"
    assert second.json() == payload
    assert provider.anomaly_calls == 1


def test_instrument_evidence_returns_empty_capabilities_for_global_symbols(tmp_path) -> None:
    api = client(tmp_path)

    response = api.get("/api/v1/instruments/US.AAPL/evidence")

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "US.AAPL"
    assert payload["filings"] == []
    assert payload["capabilities"]["filings"]["status"] == "empty"
    assert payload["capabilities"]["filings"]["provider"] == "not_supported"


def test_sector_route_returns_analysis_and_constituents(tmp_path) -> None:
    api = client(tmp_path)

    response = api.get("/api/v1/sectors/BK1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["sector"]["name"] == "白酒"
    assert payload["evidence_coverage"] == 1
    assert "主力净流入" in payload["summary"][0]
    assert payload["constituents"][0]["symbol"] == "SH.600519"


def test_theme_route_returns_board_constituents_for_clickthrough(tmp_path) -> None:
    api = client(tmp_path)

    response = api.get(
        "/api/v1/themes/BK0896",
        params={"name": "酿酒概念", "change_pct": 1.8},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["sector"]["code"] == "BK0896"
    assert payload["sector"]["name"] == "酿酒概念"
    assert payload["sector"]["change_pct"] == 1.8
    assert payload["sector"]["net_flow"] == 80_000_000
    assert payload["evidence_coverage"] == 1
    assert "主力净流入" in payload["summary"][0]
    assert payload["constituents"][0]["symbol"] == "SH.600519"
    assert payload["constituents"][0]["sector"] == "酿酒概念"


def test_theme_route_rejects_non_board_codes(tmp_path) -> None:
    api = client(tmp_path)

    response = api.get("/api/v1/themes/BAD123")

    assert response.status_code == 422
    assert response.json()["detail"] == "Eastmoney board code required"


def test_data_status_lists_eastmoney_fund_flow_as_optional(tmp_path) -> None:
    status = client(tmp_path).get("/api/v1/data-status")
    assert status.status_code == 200
    provider = status.json()["providers"]["eastmoney_fund_flow"]
    assert provider["required"] is False
    assert provider["status"] in {"not_checked", "ready"}


def test_data_status_lists_company_evidence_capabilities_separately(tmp_path) -> None:
    provider = EvidenceCapabilityProvider()
    service = MarketService(provider=provider, store=Store(tmp_path / "capabilities.db"))
    status = authenticated_client(service).get("/api/v1/data-status")

    assert status.status_code == 200
    providers = status.json()["providers"]
    assert providers["cninfo_filings"]["description"] == "巨潮公告元数据"
    assert providers["eastmoney_research"]["status"] == "unavailable"
    assert providers["eastmoney_research"]["required"] is False


def test_search_and_watchlist_crud(tmp_path) -> None:
    api = client(tmp_path)
    api.get("/api/v1/market")
    assert api.get("/api/v1/search", params={"q": "茅台"}).json()[0]["symbol"] == "SH.600519"

    created = api.post(
        "/api/v1/watchlist",
        json={
            "symbol": "SH.600519",
            "name": "贵州茅台",
            "thesis": "现金流稳定",
            "invalidation": "趋势破位",
        },
    )
    assert created.status_code == 201
    item_id = created.json()["id"]
    assert (
        api.patch(
            f"/api/v1/watchlist/{item_id}", json={"status": "researching", "thesis": "等待估值"}
        ).json()["status"]
        == "researching"
    )
    assert len(api.get("/api/v1/watchlist").json()) == 1
    assert api.delete(f"/api/v1/watchlist/{item_id}").status_code == 204


def test_holdings_are_editable_and_return_position_analysis(tmp_path) -> None:
    api = client(tmp_path)
    api.get("/api/v1/market")

    created = api.post(
        "/api/v1/holdings",
        json={
            "symbol": "SH.600519",
            "name": "贵州茅台",
            "quantity": 100,
            "cost_price": 1400,
            "target_weight": 0.4,
            "thesis": "现金流稳定，等待趋势延续",
            "invalidation": "跌破成本且基本面证据转弱",
        },
    )

    assert created.status_code == 201
    payload = created.json()
    assert payload["item"]["symbol"] == "SH.600519"
    assert payload["market_value"] == 150_000
    assert payload["pnl"] == 10_000
    assert round(payload["pnl_pct"], 2) == 7.14
    assert payload["action"] in {"hold", "trim", "add_watch", "review", "exit_watch"}
    assert payload["conclusion"].startswith("建议动作：")
    assert "分析维度：" not in payload["conclusion"]
    assert "原因：" not in payload["conclusion"]
    assert any(token in payload["conclusion"] for token in ("仓位", "盈亏", "风控"))

    item_id = payload["item"]["id"]
    updated = api.patch(
        f"/api/v1/holdings/{item_id}",
        json={"target_weight": 0.25, "thesis": "降仓后继续观察现金流"},
    )

    assert updated.status_code == 200
    assert updated.json()["item"]["target_weight"] == 0.25
    assert updated.json()["item"]["thesis"] == "降仓后继续观察现金流"
    assert updated.json()["conclusion"].startswith("建议动作：")
    assert len(api.get("/api/v1/holdings").json()) == 1


def test_holding_update_can_correct_symbol_and_refresh_price(tmp_path) -> None:
    service = MarketService(provider=QinglongAskProvider(), store=Store(tmp_path / "rename.db"))
    api = authenticated_client(service)

    created = api.post(
        "/api/v1/holdings",
        json={
            "symbol": "SH.600519",
            "name": "贵州茅台",
            "quantity": 1000,
            "cost_price": 10,
            "target_weight": 0.3,
            "thesis": "先录错的持仓",
            "invalidation": "跌破支撑",
        },
    )
    item_id = created.json()["item"]["id"]

    updated = api.patch(
        f"/api/v1/holdings/{item_id}",
        json={"symbol": "SZ.002457", "name": "青龙管业"},
    )

    assert updated.status_code == 200
    payload = updated.json()
    assert payload["item"]["symbol"] == "SZ.002457"
    assert payload["item"]["name"] == "青龙管业"
    assert payload["quote"]["price"] == 11.2
    assert payload["market_value"] == 11_200


def test_holdings_repair_legacy_symbol_name_mismatch_for_analysis(tmp_path) -> None:
    service = MarketService(
        provider=QinglongAskProvider(), store=Store(tmp_path / "legacy-mismatch.db")
    )
    api = authenticated_client(service)
    account = service.store.get_user_by_email("fixture-user@example.com")
    assert account is not None
    service.store.create_holding(
        symbol="SH.600519",
        name="青龙管业",
        quantity=1000,
        cost_price=10,
        target_weight=0.3,
        thesis="旧版本录入时名称和代码错配",
        invalidation="跌破支撑",
        user_id=account.account.id,
    )

    payload = api.get("/api/v1/holdings").json()[0]

    assert payload["item"]["symbol"] == "SZ.002457"
    assert payload["item"]["name"] == "青龙管业"
    assert payload["quote"]["price"] == 11.2
    assert payload["market_value"] == 11_200


def test_holding_create_normalizes_six_digit_symbol_for_price_lookup(tmp_path) -> None:
    api = client(tmp_path)

    created = api.post(
        "/api/v1/holdings",
        json={
            "symbol": "600519",
            "name": "贵州茅台",
            "quantity": 100,
            "cost_price": 1400,
            "target_weight": 0.4,
            "thesis": "现金流稳定，等待趋势延续",
            "invalidation": "跌破成本且基本面证据转弱",
        },
    )

    assert created.status_code == 201
    payload = created.json()
    assert payload["item"]["symbol"] == "SH.600519"
    assert payload["quote"]["price"] == 1500
    assert payload["market_value"] == 150_000
    assert payload["pnl"] == 10_000


def test_holding_create_accepts_empty_research_notes(tmp_path) -> None:
    service = MarketService(
        provider=HoldingNameProvider(), store=Store(tmp_path / "empty-notes.db")
    )
    api = authenticated_client(service)

    created = api.post(
        "/api/v1/holdings",
        json={
            "symbol": "",
            "name": "大金重工",
            "quantity": 800,
            "cost_price": 76.574,
            "target_weight": 0,
            "thesis": "",
            "invalidation": "",
        },
    )

    assert created.status_code == 201
    payload = created.json()
    assert payload["item"]["symbol"] == "SZ.002487"
    assert payload["item"]["name"] == "大金重工"
    assert "持仓逻辑待补充" in payload["item"]["thesis"]
    assert "复核降仓或退出" in payload["item"]["invalidation"]


def test_holding_create_resolves_name_only_and_rejects_symbol_name_mismatch(
    tmp_path,
) -> None:
    service = MarketService(provider=QinglongAskProvider(), store=Store(tmp_path / "name.db"))
    api = authenticated_client(service)

    qinglong = api.post(
        "/api/v1/holdings",
        json={
            "symbol": "",
            "name": "青龙管业",
            "quantity": 1000,
            "cost_price": 10,
            "target_weight": 0.3,
            "thesis": "水泥建材修复观察",
            "invalidation": "跌破支撑",
        },
    )
    pingan = api.post(
        "/api/v1/holdings",
        json={
            "symbol": "",
            "name": "平安银行",
            "quantity": 2000,
            "cost_price": 11,
            "target_weight": 0.2,
            "thesis": "低波红利观察",
            "invalidation": "银行板块走弱",
        },
    )

    assert qinglong.status_code == 201
    assert qinglong.json()["item"]["symbol"] == "SZ.002457"
    assert qinglong.json()["quote"]["price"] == 11.2
    assert qinglong.json()["market_value"] == 11_200
    assert pingan.status_code == 201
    assert pingan.json()["item"]["symbol"] == "SZ.000001"
    assert len(api.get("/api/v1/holdings").json()) == 2

    mismatch = api.post(
        "/api/v1/holdings",
        json={
            "symbol": "SH.600519",
            "name": "青龙管业",
            "quantity": 100,
            "cost_price": 10,
            "target_weight": 0.1,
            "thesis": "代码和名称不一致",
            "invalidation": "拒绝错误价格",
        },
    )

    assert mismatch.status_code == 400
    assert "代码和名称不一致" in mismatch.json()["detail"]


def test_holding_create_reuses_existing_unprefixed_symbol(tmp_path) -> None:
    service = MarketService(provider=FixtureProvider(), store=Store(tmp_path / "legacy.db"))
    api = authenticated_client(service)
    account = service.store.get_user_by_email("fixture-user@example.com")
    assert account is not None
    legacy = service.store.create_holding(
        symbol="600519",
        name="贵州茅台",
        quantity=100,
        cost_price=1400,
        target_weight=0.4,
        thesis="现金流稳定，等待趋势延续",
        invalidation="跌破成本且基本面证据转弱",
        user_id=account.account.id,
    )

    created = api.post(
        "/api/v1/holdings",
        json={
            "symbol": "SH.600519",
            "name": "贵州茅台",
            "quantity": 200,
            "cost_price": 1300,
            "target_weight": 0.2,
            "thesis": "重复添加",
            "invalidation": "重复添加",
        },
    )

    assert created.status_code == 201
    payload = created.json()
    assert payload["item"]["id"] == legacy.id
    assert payload["item"]["symbol"] == "SH.600519"
    assert payload["item"]["quantity"] == 100
    assert len(api.get("/api/v1/holdings").json()) == 1


def test_stock_route_backfills_sector_and_capital_when_snapshot_is_older(tmp_path) -> None:
    service = MarketService(
        provider=StockEnhancementProvider(), store=Store(tmp_path / "enhanced.db")
    )
    api = authenticated_client(service)

    payload = api.get("/api/v1/stocks/SH.600519").json()

    assert payload["quote"]["sector"] == "白酒Ⅱ"
    assert payload["quote"]["net_flow"] == -854_126_672.0
    assert "个股行业映射" not in payload["missing_evidence"]
    assert "资金流数据" not in payload["missing_evidence"]


def test_stock_route_uses_research_enrichment_without_branding(tmp_path) -> None:
    service = MarketService(
        provider=ResearchEnhancementProvider(), store=Store(tmp_path / "research.db")
    )
    api = authenticated_client(service)

    payload = api.get("/api/v1/stocks/SH.600519").json()

    assert payload["research_evidence"] == ["近三十日有分红相关公告", "研报关注现金流与渠道库存"]
    assert "公告与研报增强数据" not in payload["missing_evidence"]
    assert "iwencai" not in str(payload).lower()


def test_adding_existing_symbol_is_idempotent(tmp_path) -> None:
    api = client(tmp_path)
    original = {
        "symbol": "SH.600519",
        "name": "贵州茅台",
        "thesis": "现金流稳定",
        "invalidation": "趋势破位",
    }
    first = api.post("/api/v1/watchlist", json=original)

    duplicate = api.post(
        "/api/v1/watchlist",
        json={**original, "thesis": "页面默认研究理由"},
    )

    assert first.status_code == 201
    assert duplicate.status_code == 201
    assert duplicate.json()["id"] == first.json()["id"]
    assert duplicate.json()["thesis"] == "现金流稳定"
    assert len(api.get("/api/v1/watchlist").json()) == 1


def test_registered_users_have_isolated_holdings(tmp_path) -> None:
    api = client(tmp_path)

    alpha = api.post(
        "/api/v1/auth/register",
        json={
            "email": "alpha@example.com",
            "password": "Passw0rd-alpha",
            "display_name": "Alpha",
        },
    )
    beta = api.post(
        "/api/v1/auth/register",
        json={
            "email": "beta@example.com",
            "password": "Passw0rd-beta",
            "display_name": "Beta",
        },
    )

    assert alpha.status_code == 201
    assert beta.status_code == 201
    alpha_auth = {"Authorization": f"Bearer {alpha.json()['access_token']}"}
    beta_auth = {"Authorization": f"Bearer {beta.json()['access_token']}"}

    created = api.post(
        "/api/v1/holdings",
        headers=alpha_auth,
        json={
            "symbol": "SH.600519",
            "name": "贵州茅台",
            "quantity": 100,
            "cost_price": 1400,
            "target_weight": 0.4,
            "thesis": "Alpha 的现金流逻辑",
            "invalidation": "Alpha 的失效条件",
        },
    )

    assert created.status_code == 201
    assert len(api.get("/api/v1/holdings", headers=alpha_auth).json()) == 1
    assert api.get("/api/v1/holdings", headers=beta_auth).json() == []

    beta_created = api.post(
        "/api/v1/holdings",
        headers=beta_auth,
        json={
            "symbol": "SH.600519",
            "name": "贵州茅台",
            "quantity": 8,
            "cost_price": 1490,
            "target_weight": 0.1,
            "thesis": "Beta 的低仓位观察",
            "invalidation": "Beta 的失效条件",
        },
    )

    assert beta_created.status_code == 201
    assert api.get("/api/v1/holdings", headers=alpha_auth).json()[0]["item"]["quantity"] == 100
    assert api.get("/api/v1/holdings", headers=beta_auth).json()[0]["item"]["quantity"] == 8


def test_user_preferences_are_personal(tmp_path) -> None:
    api = client(tmp_path)
    alpha = api.post(
        "/api/v1/auth/register",
        json={
            "email": "prefs-alpha@example.com",
            "password": "Passw0rd-alpha",
            "display_name": "Alpha",
        },
    ).json()
    beta = api.post(
        "/api/v1/auth/register",
        json={
            "email": "prefs-beta@example.com",
            "password": "Passw0rd-beta",
            "display_name": "Beta",
        },
    ).json()
    alpha_auth = {"Authorization": f"Bearer {alpha['access_token']}"}
    beta_auth = {"Authorization": f"Bearer {beta['access_token']}"}

    updated = api.patch(
        "/api/v1/preferences",
        headers=alpha_auth,
        json={
            "default_symbol": "SH.600519",
            "start_page": "holdings",
            "risk_profile": "defensive",
            "morning_email_enabled": False,
        },
    )

    assert updated.status_code == 200
    assert updated.json()["start_page"] == "holdings"
    assert updated.json()["risk_profile"] == "defensive"
    assert updated.json()["morning_email_enabled"] is False
    assert api.get("/api/v1/preferences", headers=beta_auth).json()["start_page"] == "market"
    assert (
        api.get("/api/v1/auth/me", headers=alpha_auth).json()["email"] == "prefs-alpha@example.com"
    )


def test_morning_email_preview_summarizes_actionable_research(tmp_path) -> None:
    api = client(tmp_path)
    assert (
        api.post(
            "/api/v1/holdings",
            json={
                "symbol": "SH.600519",
                "name": "贵州茅台",
                "quantity": 10,
                "cost_price": 1700,
                "target_weight": 0.5,
                "thesis": "白酒龙头现金流稳定",
                "invalidation": "跌破长期均线",
            },
        ).status_code
        == 201
    )
    assert (
        api.post(
            "/api/v1/watchlist",
            json={
                "symbol": "SH.600519",
                "name": "贵州茅台",
                "thesis": "等待资金确认",
                "invalidation": "跌破长期均线",
            },
        ).status_code
        == 201
    )

    response = api.get(
        "/api/v1/morning-email/preview",
        params={"base_url": "https://stock.example.com"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["recipient"] == "fixture-user@example.com"
    assert payload["enabled"] is True
    assert payload["subject"].startswith("StockTS 晨报")
    assert "风险预算" in payload["preheader"]
    assert "一、今日行动台" in payload["text"]
    assert "二、市场闸门" in payload["text"]
    assert "三、持仓优先" in payload["text"]
    assert "四、候选复核（必须过闸）" in payload["text"]
    assert "五、严格校验清单" in payload["text"]
    assert "六、资金与事件证据" in payload["text"]
    assert "八、开盘检查清单" in payload["text"]
    assert "九、今日禁止动作" in payload["text"]
    assert "09:25 集合竞价" in payload["text"]
    assert "不因邮件出现某只股票就直接交易" in payload["text"]
    assert "必须强于大盘和所属板块" in payload["text"]
    assert "贵州茅台 SH.600519" in payload["text"]
    assert "https://stock.example.com/#/stocks?symbol=SH.600519" in payload["text"]
    assert "不构成投资建议" in payload["text"]
    assert "<html" in payload["html"]
    assert "STOCKTS OPENING ACTION DESK" in payload["html"]
    assert "今日行动台" in payload["html"]
    assert "市场广度仪表" in payload["html"]
    assert "上涨占比" in payload["html"]
    assert "市场闸门" in payload["html"]
    assert "候选复核（必须过闸）" in payload["html"]
    assert "候选线索 #1" in payload["html"]
    assert "先给结论" in payload["html"]
    assert "资金与事件证据" in payload["html"]
    assert "持仓优先" in payload["html"]
    assert "开盘检查清单" in payload["html"]


def test_morning_email_dispatch_sends_enabled_platform_users(tmp_path) -> None:
    service = MarketService(provider=FixtureProvider(), store=Store(tmp_path / "dispatch.db"))
    service.store.create_user("dispatch@stock.test", "Dispatch User", "disabled")
    settings = Settings(
        data_dir=tmp_path,
        email_sender="sender@qq.com",
        email_password="secret",
        email_receivers="ops@example.com",
    )

    summary = asyncio.run(
        dispatch_morning_emails(
            settings=settings,
            service=service,
            base_url="https://stock.example.com",
            dry_run=True,
            force=True,
        )
    )

    assert summary.sent == 1
    assert summary.failed == 0
    assert summary.attempts[0].recipient == "ops@example.com"
    assert "dry-run" in summary.attempts[0].detail


def test_equity_views_are_validated_and_isolated_by_account(tmp_path) -> None:
    api = client(tmp_path)
    alpha = api.post(
        "/api/v1/auth/register",
        json={
            "email": "views-alpha@example.com",
            "password": "Passw0rd-alpha",
            "display_name": "Alpha",
        },
    ).json()
    beta = api.post(
        "/api/v1/auth/register",
        json={
            "email": "views-beta@example.com",
            "password": "Passw0rd-beta",
            "display_name": "Beta",
        },
    ).json()
    alpha_auth = {"Authorization": f"Bearer {alpha['access_token']}"}
    beta_auth = {"Authorization": f"Bearer {beta['access_token']}"}
    payload = {
        "name": "白酒放量",
        "filters": {
            "query": "茅台",
            "exchange": "sh",
            "sector": "白酒",
            "min_change_pct": 1,
            "max_change_pct": 5,
            "min_amount": 1_000_000_000,
            "max_amount": None,
            "min_turnover_rate": 0.5,
            "max_turnover_rate": 3,
            "min_market_cap": 100_000_000_000,
            "max_market_cap": None,
            "complete_only": True,
            "sort_by": "amount",
            "direction": "desc",
            "page_size": 50,
        },
    }

    alpha_created = api.post("/api/v1/equity-views", headers=alpha_auth, json=payload)
    beta_created = api.post("/api/v1/equity-views", headers=beta_auth, json=payload)

    assert alpha_created.status_code == 201
    assert beta_created.status_code == 201
    assert len(api.get("/api/v1/equity-views", headers=alpha_auth).json()) == 1
    assert len(api.get("/api/v1/equity-views", headers=beta_auth).json()) == 1
    assert api.post("/api/v1/equity-views", headers=alpha_auth, json=payload).status_code == 409
    alpha_id = alpha_created.json()["id"]
    assert api.delete(f"/api/v1/equity-views/{alpha_id}", headers=beta_auth).status_code == 404
    assert api.delete(f"/api/v1/equity-views/{alpha_id}", headers=alpha_auth).status_code == 204
    assert api.get("/api/v1/equity-views", headers=alpha_auth).json() == []

    blank_name = api.post(
        "/api/v1/equity-views",
        headers=alpha_auth,
        json={**payload, "name": "   "},
    )
    assert blank_name.status_code == 422

    invalid = api.post(
        "/api/v1/equity-views",
        headers=alpha_auth,
        json={
            **payload,
            "name": "反向区间",
            "filters": {**payload["filters"], "min_change_pct": 5, "max_change_pct": 1},
        },
    )
    assert invalid.status_code == 422


def test_data_status_marks_semantic_research_optional(tmp_path) -> None:
    status = client(tmp_path).get("/api/v1/data-status")
    assert status.status_code == 200
    provider = status.json()["providers"]["semantic_research"]
    assert provider["status"] == "not_configured"
    assert provider["description"] == "语义研究增强"


def test_decision_feed_groups_events_and_enforces_read_ownership(tmp_path) -> None:
    service = MarketService(
        provider=FixtureProvider(), store=Store(tmp_path / "decision-feed.db")
    )
    first_api = authenticated_client(service, "first-feed@example.com")
    second_api = authenticated_client(service, "second-feed@example.com")
    first = service.store.get_user_by_email("first-feed@example.com")
    assert first is not None
    observed = datetime.now(UTC)
    holding = service.store.create_holding(
        symbol="SH.600519",
        name="贵州茅台",
        quantity=10,
        cost_price=1500,
        target_weight=0.2,
        thesis="测试",
        invalidation="跌破失效线",
        user_id=first.account.id,
    )

    def record(previous: str, current: str, *, required: bool, severity: str, key: str):
        def value(action: str, when: datetime) -> DecisionSnapshot:
            return DecisionSnapshot.model_validate(
                {
                    "source": "holding" if required else "opportunity",
                    "subject_key": key,
                    "symbol": "SH.600519",
                    "name": "贵州茅台",
                    "decision": DecisionPresentation(
                        action=action,
                        summary=f"决定变为{action}",
                        severity=severity if action == current else "info",
                        user_required=required if action == current else False,
                        reason_code=f"reason_{key}",
                    ),
                    "href": "/holdings",
                    "observed_at": when,
                }
            )

        service.store.record_decision_snapshot(first.account.id, value(previous, observed))
        return service.store.record_decision_snapshot(
            first.account.id, value(current, observed + timedelta(minutes=10))
        )

    actionable = record(
        "继续持有", "建议分批减仓", required=True, severity="high", key=str(holding.id)
    )
    record("仅观察", "暂不买入", required=False, severity="info", key="trend")
    assert actionable is not None

    response = first_api.get("/api/v1/decision-events")

    assert response.status_code == 200
    assert response.json()["unread_count"] == 2
    assert response.json()["requires_action"][0]["action"] == "建议分批减仓"
    assert response.json()["monitoring"][0]["action"] == "暂不买入"
    assert (
        second_api.post(f"/api/v1/decision-events/{actionable.id}/read").status_code
        == 404
    )
    assert first_api.post(f"/api/v1/decision-events/{actionable.id}/read").status_code == 200
    assert first_api.post("/api/v1/decision-events/read-all").json() == {"read": 1}
    assert first_api.get("/api/v1/decision-events").json()["unread_count"] == 0


def test_decision_feed_hides_events_after_the_holding_is_deleted(tmp_path) -> None:
    service = MarketService(
        provider=FixtureProvider(), store=Store(tmp_path / "deleted-holding-feed.db")
    )
    api = authenticated_client(service, "deleted-holding@example.com")
    account = service.store.get_user_by_email("deleted-holding@example.com")
    assert account is not None
    holding = service.store.create_holding(
        symbol="SH.600519",
        name="贵州茅台",
        quantity=10,
        cost_price=1500,
        target_weight=0.2,
        thesis="测试",
        invalidation="跌破失效线",
        user_id=account.account.id,
    )
    observed = datetime.now(UTC)

    def value(action: str, severity: str, when: datetime) -> DecisionSnapshot:
        return DecisionSnapshot(
            source="holding",
            subject_key=str(holding.id),
            symbol=holding.symbol,
            name=holding.name,
            decision=DecisionPresentation(
                action=action,
                summary=f"决定变为{action}",
                severity=severity,
                user_required=severity in {"high", "critical"},
                reason_code=f"holding_{severity}",
                confidence=0.8,
            ),
            href=f"/holdings?symbol={holding.symbol}",
            observed_at=when,
        )

    service.store.record_decision_snapshot(
        account.account.id, value("继续持有", "info", observed)
    )
    service.store.record_decision_snapshot(
        account.account.id,
        value("建议分批减仓", "high", observed + timedelta(minutes=10)),
    )
    assert api.get("/api/v1/decision-events").json()["unread_count"] == 1

    service.store.delete_holding(holding.id, account.account.id)

    feed = api.get("/api/v1/decision-events").json()
    assert feed["unread_count"] == 0
    assert feed["requires_action"] == []


@pytest.mark.asyncio
async def test_market_service_keeps_core_data_when_sector_source_fails(tmp_path) -> None:
    service = MarketService(provider=SectorFailProvider(), store=Store(tmp_path / "partial.db"))

    snapshot = await service.market()

    assert len(snapshot.equities) == 1
    assert snapshot.sectors == []
    assert snapshot.meta.errors == ["sectors: sector provider unavailable"]


@pytest.mark.asyncio
async def test_market_service_returns_cached_snapshot_before_slow_cold_refresh(tmp_path) -> None:
    store = Store(tmp_path / "cached-cold-start.db")
    await MarketService(provider=FixtureProvider(), store=store).refresh()
    service = MarketService(provider=HangingEquityProvider(), store=store)

    snapshot = await asyncio.wait_for(service.market(), timeout=0.2)

    assert len(snapshot.equities) == 1
    assert snapshot.meta.freshness == Freshness.STALE
    task = service._refresh_task
    if task is not None:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


def test_app_can_refresh_market_data_and_all_review_strategies_on_a_schedule(
    tmp_path,
) -> None:
    class CountingProvider(FixtureProvider):
        def __init__(self) -> None:
            self.calls = 0

        async def fetch_equities(self):
            self.calls += 1
            return await super().fetch_equities()

    provider = CountingProvider()
    store = Store(tmp_path / "scheduled.db")
    service = MarketService(provider=provider, store=store)
    app = create_app(
        service,
        auto_refresh_interval_seconds=0.01,
        auto_refresh_run_immediately=True,
    )

    import time

    with TestClient(app):
        deadline = time.time() + 2
        while time.time() < deadline:
            ready = all(
                store.list_recommendation_runs(preset, algorithm_version="strategy-profiles-v3")
                for preset in (
                    "trend",
                    "volume_breakout",
                    "capital_confirmed",
                    "sector_momentum",
                    "pullback_support",
                )
            )
            monitored = set(service.opportunity_monitor_status()["presets"])
            if provider.calls >= 2 and ready and monitored == {
                "trend",
                "volume_breakout",
                "capital_confirmed",
                "sector_momentum",
                "pullback_support",
                "value_rebound",
                "quality_value",
                "large_cap_stability",
                "oversold_repair",
            }:
                break
            time.sleep(0.02)

    assert provider.calls >= 2
    assert ready is True
    assert monitored == {
        "trend",
        "volume_breakout",
        "capital_confirmed",
        "sector_momentum",
        "pullback_support",
        "value_rebound",
        "quality_value",
        "large_cap_stability",
        "oversold_repair",
    }
    assert app.state.auto_refresh_interval_seconds == 0.01


@pytest.mark.asyncio
async def test_scheduled_refresh_warms_user_stocks_before_strategy_work() -> None:
    class RecordingService:
        def __init__(self) -> None:
            self.calls: list[str] = []

        async def market(self, force: bool = False):
            self.calls.append("market")

        async def refresh_stock_monitor(self):
            self.calls.append("stocks")
            return {"symbols": 1, "ready": 1}

        async def refresh_market_group_monitor(self):
            self.calls.append("groups")
            return {"groups": 2, "ready": 2}

        async def refresh_opportunity_monitor(self, preset: str):
            self.calls.append(f"opportunity:{preset}")

        async def capture_daily_recommendations(self, preset: str):
            self.calls.append(f"history:{preset}")

        async def refresh_decision_monitor(self):
            self.calls.append("decisions")
            return {"events": 0}

    service = RecordingService()

    await _safe_auto_refresh(service)  # type: ignore[arg-type]

    assert service.calls[:3] == ["market", "groups", "stocks"]
    assert service.calls.index("stocks") < next(
        index for index, call in enumerate(service.calls) if call.startswith("opportunity:")
    )


@pytest.mark.asyncio
async def test_stock_monitor_prewarms_default_stock_intelligence(tmp_path) -> None:
    class CountingProvider(FixtureProvider):
        def __init__(self) -> None:
            self.financial_calls = 0
            self.news_calls = 0

        async def fetch_financial_periods(self, symbol: str, limit: int = 5):
            self.financial_calls += 1
            return await super().fetch_financial_periods(symbol, limit)

        async def fetch_stock_news(self, symbol: str, name: str, limit: int = 20):
            self.news_calls += 1
            return await super().fetch_stock_news(symbol, name, limit)

    provider = CountingProvider()
    service = MarketService(provider=provider, store=Store(tmp_path / "stock-monitor.db"))

    result = await service.refresh_stock_monitor()
    await service.stock("SH.600519")

    assert result["symbols"] == 1
    assert result["ready"] == 1
    assert provider.financial_calls == 1
    assert provider.news_calls == 1


@pytest.mark.asyncio
async def test_opportunity_monitor_warms_results_for_page_requests(tmp_path) -> None:
    class CountingKlineProvider(FixtureProvider):
        def __init__(self) -> None:
            self.kline_calls = 0

        async def fetch_kline(self, symbol: str, limit: int = 180):
            self.kline_calls += 1
            return await super().fetch_kline(symbol, limit)

    provider = CountingKlineProvider()
    service = MarketService(provider=provider, store=Store(tmp_path / "monitor-cache.db"))

    warmed = await service.refresh_opportunity_monitor("trend", limit=10)
    calls_after_warm = provider.kline_calls
    served = await service.opportunities("trend", limit=1)

    assert warmed.monitoring_active is True
    assert warmed.monitored_at is not None
    assert served.monitoring_active is True
    assert served.monitored_at == warmed.monitored_at
    assert provider.kline_calls == calls_after_warm

    api = authenticated_client(service)
    monitor = api.get("/api/v1/data-status").json()["opportunity_monitor"]
    assert monitor["active"] is True
    assert monitor["presets"] == ["trend"]
    assert monitor["checked_at"] == warmed.monitored_at.isoformat().replace("+00:00", "Z")


@pytest.mark.asyncio
async def test_decision_monitor_establishes_baseline_then_records_one_change(tmp_path) -> None:
    class MutableHoldingProvider(FixtureProvider):
        price = 1_500.0
        change_pct = 1.2

        async def fetch_equities(self):
            dataset = await super().fetch_equities()
            return dataset.model_copy(
                update={
                    "items": [
                        dataset.items[0].model_copy(
                            update={"price": self.price, "change_pct": self.change_pct}
                        )
                    ]
                }
            )

    provider = MutableHoldingProvider()
    store = Store(tmp_path / "decision-monitor.db")
    user = store.create_user("decision-monitor@example.test", "Decision Monitor", "hash")
    store.create_holding(
        symbol="SH.600519",
        name="贵州茅台",
        quantity=100,
        cost_price=1_500,
        target_weight=0.2,
        thesis="现金流稳定",
        invalidation="亏损超过 10%",
        user_id=user.id,
    )
    service = MarketService(provider=provider, store=store)
    await service.refresh()

    first = await service.refresh_decision_monitor()
    provider.price = 1_200
    provider.change_pct = -8
    await service.refresh()
    second = await service.refresh_decision_monitor()
    repeated = await service.refresh_decision_monitor()

    events = store.list_decision_events(user.id)
    assert first["events"] == 0
    assert second["events"] == 1
    assert repeated["events"] == 0
    assert len(events) == 1
    assert events[0].action == "优先减仓或止损"


@pytest.mark.asyncio
async def test_cached_recommendation_history_does_not_rewrite_observations(
    tmp_path,
) -> None:
    class CountingStore(Store):
        observation_writes = 0

        def save_recommendation_observation(
            self, run_id: int, observation: RecommendationObservation
        ) -> None:
            self.observation_writes += 1
            super().save_recommendation_observation(run_id, observation)

    store = CountingStore(tmp_path / "cached-history.db")
    service = MarketService(provider=FixtureProvider(), store=store)
    await service.recommendation_history("trend")
    store.observation_writes = 0

    await service.recommendation_history("trend")

    assert store.observation_writes == 0


def test_global_stock_search_stock_and_holding_flow(tmp_path) -> None:
    api = client(tmp_path)

    search = api.get("/api/v1/search", params={"q": "AAPL"}).json()
    assert search[0]["symbol"] == "US.AAPL"
    assert search[0]["sector"] == "美股/USD"

    stock = api.get("/api/v1/stocks/US.AAPL")
    assert stock.status_code == 200
    payload = stock.json()
    assert payload["quote"]["symbol"] == "US.AAPL"
    assert payload["quote"]["name"] == "苹果"
    assert payload["bars"]

    created = api.post(
        "/api/v1/holdings",
        json={
            "symbol": "HK.700",
            "name": "腾讯控股",
            "quantity": 100,
            "cost_price": 470,
            "thesis": "港股核心互联网持仓",
            "invalidation": "跌破成本且趋势转弱",
        },
    )
    assert created.status_code == 201
    holding = created.json()
    assert holding["item"]["symbol"] == "HK.00700"
    assert holding["quote"]["sector"] == "港股/HKD"
    assert holding["market_value"] == 48_580

    rows = api.get("/api/v1/holdings").json()
    assert rows[0]["item"]["symbol"] == "HK.00700"
    assert rows[0]["day_pnl"] is not None
    assert len(rows[0]["recent_daily_changes"]) == 10
    assert rows[0]["target_market_value"] is None
    assert rows[0]["rebalance_value"] is None


def test_ask_stock_accepts_explicit_global_symbol(tmp_path) -> None:
    api = client(tmp_path)

    response = api.post("/api/v1/ask-stock", json={"question": "US.AAPL 现在怎么样"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["kind"] == "stock_analysis"
    assert payload["symbol"] == "US.AAPL"
    assert payload["name"] == "苹果"
    assert payload["holding_context"] is None
