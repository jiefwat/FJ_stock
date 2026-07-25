from datetime import date, timedelta

import pytest

from marketdesk.analysis.indicators import (
    average_true_range,
    bollinger_bands,
    ema_series,
    macd_series,
    maximum_drawdown,
)
from marketdesk.models import Bar


def test_ema_series_seeds_with_sma_and_then_recurses() -> None:
    assert ema_series([1, 2, 3, 4], 3) == [None, None, 2.0, 3.0]


def test_macd_requires_a_warmed_signal_line() -> None:
    line, signal, histogram = macd_series([float(value) for value in range(1, 41)])

    assert line[-1] is not None
    assert signal[-1] is not None
    assert histogram[-1] == pytest.approx(line[-1] - signal[-1])
    assert all(value is None for value in signal[:33])


def test_atr_uses_true_range_and_requires_previous_close() -> None:
    start = date(2026, 1, 1)
    bars = [
        Bar(
            date=start + timedelta(days=index),
            open=10,
            high=12,
            low=9,
            close=11,
            volume=1,
            amount=1,
        )
        for index in range(15)
    ]

    assert average_true_range(bars, 14) == pytest.approx(3.0)
    assert average_true_range(bars[:14], 14) is None


def test_bollinger_and_drawdown_handle_flat_and_zero_values() -> None:
    assert bollinger_bands([10.0] * 20) == (10.0, 10.0, 0.5)
    assert maximum_drawdown([100, 120, 90], 3) == pytest.approx(25.0)
    assert maximum_drawdown([0, 1, 2], 3) is None


def test_short_series_return_unavailable_indicator_values() -> None:
    line, signal, histogram = macd_series([1.0] * 20)

    assert line == [None] * 20
    assert signal == [None] * 20
    assert histogram == [None] * 20
    assert bollinger_bands([1.0] * 19) == (None, None, None)
    assert maximum_drawdown([1.0] * 59, 60) is None
