from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from marketdesk.api import create_app
from marketdesk.models import (
    DatasetMeta,
    EquityQuote,
    EvidenceDocument,
    Freshness,
    IndexQuote,
    InstrumentTheme,
    MarketEventRaw,
    SectorSnapshot,
    SemanticScreenResult,
    SourceRef,
    TradingAnomaly,
)
from marketdesk.providers.base import ProviderUnavailable
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
        assert sector_code in {"BK1", "BK0896"}
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
            )
        ]

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


class SectorFailProvider(FixtureProvider):
    async def fetch_sectors(self):
        raise RuntimeError("sector provider unavailable")


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
    async def query_stock_screen(
        self, question: str, limit: int = 20
    ) -> SemanticScreenResult:
        assert question == "低估值白酒股"
        assert limit == 20
        return SemanticScreenResult(
            columns=["股票代码", "股票简称", "市盈率"],
            rows=[{"股票代码": "600519", "股票简称": "贵州茅台", "市盈率": 23.0}],
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
    assert payload["answer"].startswith("FINAL GATE：")
    assert payload["observed_at"]


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

    held_response = api_a.post(
        "/api/v1/ask-stock", json={"question": "我持有的贵州茅台要减仓吗"}
    )
    empty_response = api_b.post(
        "/api/v1/ask-stock", json={"question": "我持有的贵州茅台要减仓吗"}
    )

    assert held_response.status_code == 200
    held = held_response.json()
    assert held["holding_context"]["owned"] is True
    assert held["holding_context"]["quantity"] == 10
    assert "结合你的账户持仓" in held["answer"]
    assert "持仓盈亏" in [item["label"] for item in held["metrics"]]
    assert any(item["label"] == "价格与 MA20" for item in held["factors"])

    assert empty_response.status_code == 200
    empty = empty_response.json()
    assert empty["holding_context"] is None
    assert "结合你的账户持仓" not in empty["answer"]


def test_ask_stock_answers_portfolio_question_without_cross_account_leakage(tmp_path) -> None:
    service = MarketService(
        provider=FixtureProvider(), store=Store(tmp_path / "ask-portfolio.db")
    )
    api_a = authenticated_client(service, "portfolio-a@example.com")
    api_b = authenticated_client(service, "portfolio-b@example.com")
    assert api_a.post(
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
    ).status_code == 201

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
        "目标仓位",
        "偏离",
        "盈亏",
        "动作",
        "风险",
    ]
    assert any(item["label"] == "最大单票集中度" for item in payload_a["factors"])
    assert {row["股票代码"] for row in payload_a["rows"]} == {
        "SH.600519",
        "SZ.000001",
        "BJ.430047",
    }

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
    assert "建议股数" in payload_a["answer"]
    assert [item["label"] for item in payload_a["metrics"]] == [
        "持仓数量",
        "总市值",
        "需调仓",
        "净调整",
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
        "目标仓位",
        "偏离",
        "偏离金额",
        "建议股数",
        "优先级",
        "动作",
        "风险",
    ]
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
    assert api.post(
        "/api/v1/ask-stock", json={"question": "茅" * 161}
    ).status_code == 422


def test_ask_stock_rejects_multiple_local_stocks(tmp_path) -> None:
    service = MarketService(
        provider=EquityBrowserProvider(), store=Store(tmp_path / "ask-ambiguous.db")
    )
    api = authenticated_client(service)

    response = api.post(
        "/api/v1/ask-stock", json={"question": "贵州茅台和平安银行哪个更好"}
    )

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
    assert response.json()["detail"] == "条件选股增强暂不可用；你也可以在问题中包含一个 A 股股票名称或代码继续分析。"
    assert "问财" not in response.json()["detail"]
    assert api.get("/api/v1/today").status_code == 200


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
        "/api/v1/today",
        "/api/v1/opportunities",
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
    assert api.post(
        "/api/v1/auth/login",
        json={"email": "gate-user@example.com", "password": "GatePass-0725"},
    ).status_code == 200


def test_market_today_and_stock_routes(tmp_path) -> None:
    api = client(tmp_path)

    market = api.get("/api/v1/market")
    today = api.get("/api/v1/today")
    stock = api.get("/api/v1/stocks/SH.600519")

    assert market.status_code == 200
    market_payload = market.json()
    assert market_payload["snapshot"]["meta"]["source"] == "fixture"
    assert market_payload["snapshot"]["indices"][0]["symbol"] == "SH.000001"
    assert market_payload["snapshot"]["sectors"][0]["code"] == "BK1"
    assert "equities" not in market_payload["snapshot"]
    assert today.json()["top_opportunities"][0]["quote"]["name"] == "贵州茅台"
    stock_payload = stock.json()
    assert stock_payload["stance"] in {"strong_watch", "watch", "neutral", "avoid"}
    assert "signal_validation" in stock_payload
    assert stock_payload["technical"]["macd_histogram"] is not None
    assert stock_payload["technical"]["atr_pct"] is not None


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


def test_instrument_evidence_rejects_non_a_share_symbols(tmp_path) -> None:
    api = client(tmp_path)

    response = api.get("/api/v1/instruments/US.AAPL/evidence")

    assert response.status_code == 422
    assert response.json()["detail"] == "A-share symbol required"


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
    assert "分析维度：" in payload["conclusion"]
    assert "原因：" in payload["conclusion"]

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
    assert api.get("/api/v1/preferences", headers=beta_auth).json()["start_page"] == "today"
    assert (
        api.get("/api/v1/auth/me", headers=alpha_auth).json()["email"] == "prefs-alpha@example.com"
    )


def test_morning_email_preview_summarizes_actionable_research(tmp_path) -> None:
    api = client(tmp_path)
    assert api.post(
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
    ).status_code == 201
    assert api.post(
        "/api/v1/watchlist",
        json={
            "symbol": "SH.600519",
            "name": "贵州茅台",
            "thesis": "等待资金确认",
            "invalidation": "跌破长期均线",
        },
    ).status_code == 201

    response = api.get(
        "/api/v1/morning-email/preview",
        params={"base_url": "https://stock.example.com"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["recipient"] == "fixture-user@example.com"
    assert payload["enabled"] is True
    assert payload["subject"].startswith("Market Desk 晨报")
    assert "上涨" in payload["preheader"]
    assert "一、开盘前结论" in payload["text"]
    assert "三、资金主线" in payload["text"]
    assert "四、事件与异动" in payload["text"]
    assert "五、推荐股票（需复核）" in payload["text"]
    assert "六、持仓和跟踪池" in payload["text"]
    assert "七、开盘检查清单" in payload["text"]
    assert "八、今日禁止动作" in payload["text"]
    assert "09:25 集合竞价" in payload["text"]
    assert "不因邮件出现某只股票就直接交易" in payload["text"]
    assert "确认项：强于大盘、板块延续、回踩不破" in payload["text"]
    assert "贵州茅台 SH.600519" in payload["text"]
    assert "https://stock.example.com/#/stocks?symbol=SH.600519" in payload["text"]
    assert "不构成投资建议" in payload["text"]
    assert "<html" in payload["html"]
    assert "MARKET DESK MORNING BRIEF" in payload["html"]
    assert "今日大盘" in payload["html"]
    assert "今日开盘路线" in payload["html"]
    assert "市场广度仪表" in payload["html"]
    assert "上涨占比" in payload["html"]
    assert "大盘温度" in payload["html"]
    assert "推荐股票（需复核）" in payload["html"]
    assert "推荐股票 #1" in payload["html"]
    assert "复核级别" in payload["html"]
    assert "板块资金主线" in payload["html"]
    assert "持仓风险雷达" in payload["html"]
    assert "开盘检查清单" in payload["html"]


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


@pytest.mark.asyncio
async def test_market_service_keeps_core_data_when_sector_source_fails(tmp_path) -> None:
    service = MarketService(provider=SectorFailProvider(), store=Store(tmp_path / "partial.db"))

    snapshot = await service.market()

    assert len(snapshot.equities) == 1
    assert snapshot.sectors == []
    assert snapshot.meta.errors == ["sectors: sector provider unavailable"]


def test_app_can_refresh_market_data_on_a_two_hour_schedule(tmp_path) -> None:
    class CountingProvider(FixtureProvider):
        def __init__(self) -> None:
            self.calls = 0

        async def fetch_equities(self):
            self.calls += 1
            return await super().fetch_equities()

    provider = CountingProvider()
    service = MarketService(provider=provider, store=Store(tmp_path / "scheduled.db"))
    app = create_app(
        service,
        auto_refresh_interval_seconds=0.01,
        auto_refresh_run_immediately=True,
    )

    import time

    with TestClient(app):
        deadline = time.time() + 1
        while provider.calls < 2 and time.time() < deadline:
            time.sleep(0.02)

    assert provider.calls >= 2
    assert app.state.auto_refresh_interval_seconds == 0.01
