from stock_ts.realtime_quotes import QuoteFetchError, RealtimeQuote, fetch_realtime_quote


def test_fetch_realtime_quote_falls_back_and_records_quality() -> None:
    def broken(code: str) -> RealtimeQuote:
        raise QuoteFetchError("timeout")

    def working(code: str) -> RealtimeQuote:
        return RealtimeQuote(
            code=code, name="测试股票", source="tencent", price=12.3, change_pct=1.2
        )

    quote = fetch_realtime_quote("600519", [("tdx", broken), ("tencent", working)])

    assert quote.source == "tencent"
    assert quote.fallback_from == ["tdx"]
    assert quote.data_quality == "partial"
    assert quote.price == 12.3


def test_fetch_realtime_quote_marks_missing_price_as_poor() -> None:
    def no_price(code: str) -> RealtimeQuote:
        return RealtimeQuote(
            code=code, name="测试股票", source="empty", price=None, change_pct=None
        )

    quote = fetch_realtime_quote("600519", [("empty", no_price)])

    assert quote.data_quality == "poor"
    assert quote.missing_fields == ["price", "change_pct"]
