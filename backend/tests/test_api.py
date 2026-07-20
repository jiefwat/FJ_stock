from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from marketdesk.api import create_app
from marketdesk.models import (
    DatasetMeta,
    EquityQuote,
    Freshness,
    IndexQuote,
    MarketEventRaw,
    SectorSnapshot,
)
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
        assert sector_code == "BK1"
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


def client(tmp_path) -> TestClient:
    service = MarketService(provider=FixtureProvider(), store=Store(tmp_path / "test.db"))
    return TestClient(create_app(service))


def test_market_today_and_stock_routes(tmp_path) -> None:
    api = client(tmp_path)

    market = api.get("/api/v1/market")
    today = api.get("/api/v1/today")
    stock = api.get("/api/v1/stocks/SH.600519")

    assert market.status_code == 200
    assert market.json()["snapshot"]["meta"]["source"] == "fixture"
    assert today.json()["top_opportunities"][0]["quote"]["name"] == "贵州茅台"
    assert stock.json()["stance"] in {"strong_watch", "watch", "neutral", "avoid"}


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


def test_sector_route_returns_analysis_and_constituents(tmp_path) -> None:
    api = client(tmp_path)

    response = api.get("/api/v1/sectors/BK1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["sector"]["name"] == "白酒"
    assert payload["evidence_coverage"] == 1
    assert "主力净流入" in payload["summary"][0]
    assert payload["constituents"][0]["symbol"] == "SH.600519"


def test_data_status_lists_eastmoney_fund_flow_as_optional(tmp_path) -> None:
    status = client(tmp_path).get("/api/v1/data-status")
    assert status.status_code == 200
    provider = status.json()["providers"]["eastmoney_fund_flow"]
    assert provider["required"] is False
    assert provider["status"] in {"not_checked", "ready"}


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


def test_stock_route_backfills_sector_and_capital_when_snapshot_is_older(tmp_path) -> None:
    service = MarketService(
        provider=StockEnhancementProvider(), store=Store(tmp_path / "enhanced.db")
    )
    api = TestClient(create_app(service))

    payload = api.get("/api/v1/stocks/SH.600519").json()

    assert payload["quote"]["sector"] == "白酒Ⅱ"
    assert payload["quote"]["net_flow"] == -854_126_672.0
    assert "个股行业映射" not in payload["missing_evidence"]
    assert "资金流数据" not in payload["missing_evidence"]


def test_stock_route_uses_research_enrichment_without_branding(tmp_path) -> None:
    service = MarketService(
        provider=ResearchEnhancementProvider(), store=Store(tmp_path / "research.db")
    )
    api = TestClient(create_app(service))

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
