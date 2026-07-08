import sys
import types

import pytest

from stock_ts.providers.base import DataProviderError
from stock_ts.providers.factory import create_provider
from stock_ts.providers.tushare_provider import TushareProvider, to_tushare_code


class FakeFrame:
    def __init__(self, rows):
        self._rows = rows
        self.empty = not rows

    def to_dict(self, orient):
        assert orient == "records"
        return list(self._rows)


class FakeTusharePro:
    def __init__(self):
        self.daily_calls = []
        self.index_calls = []

    def daily(self, **kwargs):
        self.daily_calls.append(kwargs)
        return FakeFrame(
            [
                {
                    "trade_date": "20260619",
                    "open": 1690,
                    "high": 1708,
                    "low": 1680,
                    "close": 1700,
                    "vol": 321.5,
                },
                {
                    "trade_date": "20260618",
                    "open": 1680,
                    "high": 1695,
                    "low": 1675,
                    "close": 1690,
                    "vol": 300.0,
                },
            ]
        )

    def stock_basic(self, **kwargs):
        return FakeFrame([{"ts_code": "600519.SH", "name": "贵州茅台"}])

    def index_daily(self, **kwargs):
        self.index_calls.append(kwargs)
        return FakeFrame(
            [
                {"trade_date": "20260619", "close": 3200.0, "pct_chg": 0.5, "amount": 502000000.0},
                {"trade_date": "20260618", "close": 3184.0, "pct_chg": -0.2, "amount": 480000000.0},
            ]
        )


def test_to_tushare_code_normalizes_a_share_suffix() -> None:
    assert to_tushare_code("600519") == "600519.SH"
    assert to_tushare_code("002487") == "002487.SZ"
    assert to_tushare_code("300750") == "300750.SZ"
    assert to_tushare_code("920363") == "920363.BJ"
    assert to_tushare_code("600519.SH") == "600519.SH"


def test_tushare_provider_reads_stock_daily_bars_in_chronological_order() -> None:
    client = FakeTusharePro()
    provider = TushareProvider(token="fake-token", pro_client=client)

    stock = provider.fetch_stock("600519")

    assert client.daily_calls[0]["ts_code"] == "600519.SH"
    assert stock.code == "600519"
    assert stock.name == "贵州茅台"
    assert [bar.date for bar in stock.bars] == ["2026-06-18", "2026-06-19"]
    assert stock.bars[-1].close == 1700.0
    assert stock.bars[-1].volume == 32150.0


def test_tushare_provider_reads_index_market_quotes() -> None:
    provider = TushareProvider(token="fake-token", pro_client=FakeTusharePro())

    market = provider.fetch_market()

    assert market.trade_date == "2026-06-19"
    assert [item.code for item in market.indices] == ["000001", "399001", "399006"]
    assert market.indices[0].name == "上证指数"
    assert market.indices[0].pct_chg == 0.5


def test_tushare_provider_requires_token_without_injected_client(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("TUSHARE_TOKEN", raising=False)

    with pytest.raises(DataProviderError, match="Tushare token"):
        TushareProvider()


def test_provider_factory_can_create_tushare_provider(monkeypatch) -> None:
    monkeypatch.setenv("TUSHARE_TOKEN", "fake-token")
    fake_module = types.SimpleNamespace(pro_api=lambda token: FakeTusharePro())
    monkeypatch.setitem(sys.modules, "tushare", fake_module)

    provider = create_provider("tushare")

    assert isinstance(provider, TushareProvider)
