from stock_ts.indicators import bollinger_bands, ema, macd, rsi, volume_ma


def test_ema_uses_standard_smoothing() -> None:
    values = [10, 11, 12, 13]

    assert round(ema(values, 3)[-1], 4) == 12.125


def test_macd_returns_dif_dea_and_histogram_series() -> None:
    values = [10, 10.5, 11, 11.8, 12.4, 12.1, 12.9, 13.5, 13.2, 14.0]

    result = macd(values, fast=3, slow=6, signal=3)

    assert set(result) == {"dif", "dea", "macd"}
    assert len(result["dif"]) == len(values)
    assert len(result["dea"]) == len(values)
    assert len(result["macd"]) == len(values)
    assert result["dif"][-1] > 0


def test_rsi_and_bollinger_handle_short_and_full_windows() -> None:
    closes = [10, 10.5, 10.2, 11, 11.8, 11.5, 12.2]

    assert rsi(closes[:2], 6)[-1] is None
    assert rsi(closes, 6)[-1] is not None

    bands = bollinger_bands(closes, window=5, num_std=2)
    assert bands["middle"][-1] is not None
    assert bands["upper"][-1] > bands["middle"][-1] > bands["lower"][-1]


def test_volume_ma_returns_none_until_window_is_available() -> None:
    result = volume_ma([100, 120, 140, 160], 3)

    assert result == [None, None, 120, 140]
