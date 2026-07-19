from datetime import UTC

import httpx
import pytest

from marketdesk.providers.eastmoney import EastmoneyProvider


def test_normalize_equities_maps_symbols_and_missing_values() -> None:
    payload = {
        "data": {
            "diff": [
                {
                    "f12": "600519",
                    "f14": "贵州茅台",
                    "f2": 1500.5,
                    "f3": 1.25,
                    "f6": 2_000_000_000,
                    "f8": 0.63,
                    "f9": 22.4,
                    "f10": 1.2,
                    "f20": 1_900_000_000_000,
                    "f23": 7.4,
                    "f62": 80_000_000,
                },
                {"f12": "000001", "f14": "平安银行", "f2": "-", "f3": None},
            ]
        }
    }

    dataset = EastmoneyProvider().normalize_equities(payload)

    assert dataset.items[0].symbol == "SH.600519"
    assert dataset.items[0].change_pct == 1.25
    assert dataset.items[1].symbol == "SZ.000001"
    assert dataset.items[1].price is None
    assert dataset.meta.observed_at.tzinfo == UTC
    assert 0 < dataset.meta.coverage < 1


def test_normalize_kline_returns_ordered_bars() -> None:
    payload = {
        "data": {
            "klines": [
                "2026-07-17,10,11,12,9,1000,20000,3,10,1,2",
                "2026-07-18,11,12,13,10,1100,22000,3,9,1,2",
            ]
        }
    }

    bars = EastmoneyProvider().normalize_kline(payload)

    assert [bar.close for bar in bars] == [11.0, 12.0]
    assert bars[0].date.isoformat() == "2026-07-17"


def test_normalize_indices_uses_index_market_mapping() -> None:
    payload = {
        "data": {
            "diff": [
                {"f12": "000001", "f14": "上证指数", "f2": 3764.15, "f3": -3.05},
                {"f12": "399001", "f14": "深证成指", "f2": 13706.88, "f3": -5.4},
            ]
        }
    }

    indices = EastmoneyProvider().normalize_indices(payload)

    assert indices[0].symbol == "SH.000001"
    assert indices[1].symbol == "SZ.399001"


@pytest.mark.asyncio
async def test_fetch_equities_paginates_to_reported_total() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params["pn"])
        size = 100 if page < 3 else 50
        rows = [
            {
                "f12": f"{page}{index:05d}"[-6:],
                "f14": f"股票{page}-{index}",
                "f2": 10,
                "f3": 1,
                "f6": 200_000_000,
                "f8": 2,
                "f9": 20,
                "f10": 1,
                "f20": 5_000_000_000,
                "f23": 2,
                "f62": 10_000_000,
            }
            for index in range(size)
        ]
        return httpx.Response(200, json={"data": {"total": 250, "diff": rows}})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    dataset = await EastmoneyProvider(client).fetch_equities()

    assert len(dataset.items) == 250


@pytest.mark.asyncio
async def test_fetch_indices_retries_transient_connection_error() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise httpx.ConnectError("temporary disconnect", request=request)
        return httpx.Response(
            200,
            json={
                "data": {
                    "diff": [
                        {"f12": "000001", "f14": "上证指数", "f2": 3764.15, "f3": -3.05, "f6": 100}
                    ]
                }
            },
        )

    provider = EastmoneyProvider(httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    indices = await provider.fetch_indices()

    assert attempts == 2
    assert indices[0].symbol == "SH.000001"
