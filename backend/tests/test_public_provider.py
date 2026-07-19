from datetime import UTC, datetime

from marketdesk.providers.public_market import PublicMarketProvider, _market_observed_at


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
