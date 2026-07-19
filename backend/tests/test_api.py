from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from marketdesk.api import create_app
from marketdesk.models import (
    DatasetMeta,
    EquityQuote,
    Freshness,
    IndexQuote,
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


def test_data_status_marks_iwencai_optional(tmp_path) -> None:
    status = client(tmp_path).get("/api/v1/data-status")
    assert status.status_code == 200
    assert status.json()["providers"]["iwencai"]["status"] == "not_configured"


@pytest.mark.asyncio
async def test_market_service_keeps_core_data_when_sector_source_fails(tmp_path) -> None:
    service = MarketService(provider=SectorFailProvider(), store=Store(tmp_path / "partial.db"))

    snapshot = await service.market()

    assert len(snapshot.equities) == 1
    assert snapshot.sectors == []
    assert snapshot.meta.errors == ["sectors: sector provider unavailable"]
