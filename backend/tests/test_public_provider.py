from datetime import UTC, datetime
from types import SimpleNamespace

import httpx
import pytest

from marketdesk.providers.public_market import PublicMarketProvider, _market_observed_at


def test_public_provider_does_not_read_shell_proxy_environment(monkeypatch) -> None:
    created_clients: list[dict[str, object]] = []

    class FakeClient:
        def __init__(self, **kwargs: object) -> None:
            created_clients.append(kwargs)

    monkeypatch.setattr("marketdesk.providers.public_market.httpx.AsyncClient", FakeClient)

    PublicMarketProvider()

    assert created_clients[0]["trust_env"] is False


def test_sina_equities_normalize_market_cap_units() -> None:
    rows = [
        {
            "symbol": "sh600519",
            "code": "600519",
            "name": "贵州茅台",
            "trade": "1500.50",
            "changepercent": 1.25,
            "amount": 2_000_000_000,
            "turnoverratio": 0.63,
            "per": 22.4,
            "pb": 7.4,
            "mktcap": 1_900_000_00,
        }
    ]

    dataset = PublicMarketProvider().normalize_equities(rows)

    assert dataset.items[0].symbol == "SH.600519"
    assert dataset.items[0].market_cap == 1_900_000_000_000
    assert dataset.meta.coverage == 1


def test_sina_industry_payload_normalizes_sector_change() -> None:
    text = 'var S_Finance_bankuai_sinaindustry = {"new_dlhy":"new_dlhy,电力行业,62,8.266,0.1201,1.4751,5596,44585,sh600236,10.05,10.62,0.97,桂冠电力"};'

    sectors = PublicMarketProvider().normalize_sectors(text)

    assert sectors[0].name == "电力行业"
    assert sectors[0].change_pct == 1.4751


def test_eastmoney_board_constituents_normalize_to_quotes() -> None:
    payload = {
        "data": {
            "diff": [
                {
                    "f12": "600236",
                    "f14": "桂冠电力",
                    "f2": 10.62,
                    "f3": 10.05,
                    "f6": 387_794_582,
                    "f8": 0.47,
                    "f9": 24.36,
                    "f10": 2.38,
                    "f20": 83_710_852_257,
                    "f23": 4.87,
                    "f62": 87_265_482,
                    "f100": "电力",
                }
            ]
        }
    }

    quotes = PublicMarketProvider.normalize_eastmoney_board_constituents(payload)

    assert quotes[0].symbol == "SH.600236"
    assert quotes[0].net_flow == 87_265_482
    assert quotes[0].sector == "电力"


@pytest.mark.asyncio
async def test_eastmoney_json_falls_back_to_curl_when_httpx_disconnects(monkeypatch) -> None:
    class BrokenClient:
        async def get(self, *args, **kwargs):
            raise httpx.RemoteProtocolError("Server disconnected without sending a response.")

    def fake_run(*args, **kwargs):
        return SimpleNamespace(
            stdout='{"data":{"diff":[{"f12":"BK1380","f14":"水力发电","f3":3.28,"f62":161979008.0}]}}'
        )

    monkeypatch.setattr("marketdesk.providers.public_market.subprocess.run", fake_run)

    payload = await PublicMarketProvider(BrokenClient())._get_eastmoney_json({"pn": 1})

    assert payload["data"]["diff"][0]["f14"] == "水力发电"


def test_tencent_quotes_and_kline_normalize() -> None:
    quotes = 'v_sh000001="1~上证指数~000001~3764.15~3882.41~3865.32~650450984~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~~20260717161402~-118.26~-3.05~3869.21~3745.17~3764.15/650450984/1246445452836";'
    kline = {
        "data": {"sh600519": {"qfqday": [["2026-07-17", "1180", "1190", "1200", "1170", "50000"]]}}
    }

    provider = PublicMarketProvider()
    indices = provider.normalize_indices(quotes)
    bars = provider.normalize_kline(kline, "SH.600519")

    assert indices[0].symbol == "SH.000001"
    assert indices[0].change_pct == -3.05
    assert bars[0].close == 1190


def test_weekend_observation_uses_previous_market_close() -> None:
    sunday = datetime(2026, 7, 19, 8, tzinfo=UTC)

    observed = _market_observed_at(sunday)

    assert observed == datetime(2026, 7, 17, 7, tzinfo=UTC)
