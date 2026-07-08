from stock_ts.models import DailyBar
from stock_ts.providers.tencent_provider import (
    _MARKET_CACHE,
    _STOCK_CACHE,
    TencentProvider,
    _TencentQuote,
)


def test_tencent_provider_caches_stock_results(monkeypatch) -> None:
    _MARKET_CACHE.clear()
    _STOCK_CACHE.clear()
    calls = {"quote": 0, "kline": 0}

    def fake_quote(symbol: str, *, timeout: float) -> _TencentQuote:
        calls["quote"] += 1
        fields = [""] * 40
        fields[1] = "贵州茅台"
        return _TencentQuote(symbol, fields)

    def fake_kline(symbol: str, *, count: int, timeout: float) -> list[DailyBar]:
        calls["kline"] += 1
        return [
            DailyBar(
                date="2026-06-13",
                open=1580.0,
                close=1600.0,
                high=1610.0,
                low=1572.0,
                volume=100000.0,
            )
        ]

    monkeypatch.setattr("stock_ts.providers.tencent_provider._fetch_quote", fake_quote)
    monkeypatch.setattr("stock_ts.providers.tencent_provider._fetch_kline", fake_kline)

    provider = TencentProvider(request_timeout=1.5)
    first = provider.fetch_stock("600519")
    second = provider.fetch_stock("600519")

    assert first == second
    assert calls == {"quote": 1, "kline": 1}
