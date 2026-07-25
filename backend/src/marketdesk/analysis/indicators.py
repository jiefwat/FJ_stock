from math import sqrt

from marketdesk.models import Bar


def ema_series(values: list[float], period: int) -> list[float | None]:
    result: list[float | None] = [None] * len(values)
    if period <= 0 or len(values) < period:
        return result

    current = sum(values[:period]) / period
    result[period - 1] = current
    alpha = 2 / (period + 1)
    for index in range(period, len(values)):
        current = (values[index] - current) * alpha + current
        result[index] = current
    return result


def macd_series(
    values: list[float],
    fast: int = 12,
    slow: int = 26,
    signal_period: int = 9,
) -> tuple[list[float | None], list[float | None], list[float | None]]:
    fast_line = ema_series(values, fast)
    slow_line = ema_series(values, slow)
    macd: list[float | None] = [
        fast_value - slow_value
        if fast_value is not None and slow_value is not None
        else None
        for fast_value, slow_value in zip(fast_line, slow_line, strict=True)
    ]

    indexes: list[int] = []
    compact: list[float] = []
    for index, value in enumerate(macd):
        if value is not None:
            indexes.append(index)
            compact.append(value)
    compact_signal = ema_series(compact, signal_period)
    signal: list[float | None] = [None] * len(values)
    for index, value in zip(indexes, compact_signal, strict=True):
        signal[index] = value
    histogram = [
        value - signal_value
        if value is not None and signal_value is not None
        else None
        for value, signal_value in zip(macd, signal, strict=True)
    ]
    return macd, signal, histogram


def average_true_range(bars: list[Bar], period: int = 14) -> float | None:
    if period <= 0 or len(bars) < period + 1:
        return None

    true_ranges = [
        max(
            bar.high - bar.low,
            abs(bar.high - bars[index - 1].close),
            abs(bar.low - bars[index - 1].close),
        )
        for index, bar in enumerate(bars[1:], start=1)
    ]
    current = sum(true_ranges[:period]) / period
    for value in true_ranges[period:]:
        current = (current * (period - 1) + value) / period
    return current


def bollinger_bands(
    values: list[float], period: int = 20, deviations: float = 2
) -> tuple[float | None, float | None, float | None]:
    if period <= 0 or len(values) < period:
        return None, None, None

    sample = values[-period:]
    mean = sum(sample) / period
    standard_deviation = sqrt(sum((value - mean) ** 2 for value in sample) / period)
    upper = mean + deviations * standard_deviation
    lower = mean - deviations * standard_deviation
    position = 0.5 if upper == lower else (sample[-1] - lower) / (upper - lower)
    return upper, lower, position


def maximum_drawdown(values: list[float], window: int = 60) -> float | None:
    if window <= 0 or len(values) < window:
        return None

    sample = values[-window:]
    if any(value <= 0 for value in sample):
        return None
    peak = sample[0]
    drawdown = 0.0
    for value in sample[1:]:
        peak = max(peak, value)
        drawdown = max(drawdown, (peak - value) / peak * 100)
    return drawdown
