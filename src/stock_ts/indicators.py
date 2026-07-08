from __future__ import annotations

import math


def sma(values: list[float], window: int) -> float | None:
    if window <= 0:
        raise ValueError("window must be positive")
    if len(values) < window:
        return None
    return sum(values[-window:]) / window


def pct_change(previous: float, current: float) -> float:
    if previous == 0:
        return 0.0
    return (current - previous) / previous * 100


def volatility(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    avg = sum(values) / len(values)
    if avg == 0:
        return 0.0
    variance = sum((item - avg) ** 2 for item in values) / len(values)
    return variance**0.5 / avg * 100


def ema(values: list[float], period: int) -> list[float]:
    if period <= 0:
        raise ValueError("period must be positive")
    if not values:
        return []
    alpha = 2 / (period + 1)
    result = [float(values[0])]
    for value in values[1:]:
        result.append(float(value) * alpha + result[-1] * (1 - alpha))
    return result


def macd(
    values: list[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> dict[str, list[float]]:
    if fast <= 0 or slow <= 0 or signal <= 0:
        raise ValueError("macd periods must be positive")
    fast_ema = ema(values, fast)
    slow_ema = ema(values, slow)
    dif = [fast_value - slow_value for fast_value, slow_value in zip(fast_ema, slow_ema)]
    dea = ema(dif, signal)
    histogram = [(dif_value - dea_value) * 2 for dif_value, dea_value in zip(dif, dea)]
    return {"dif": dif, "dea": dea, "macd": histogram}


def rsi(values: list[float], period: int = 14) -> list[float | None]:
    if period <= 0:
        raise ValueError("period must be positive")
    result: list[float | None] = [None] * len(values)
    if len(values) <= period:
        return result
    for index in range(period, len(values)):
        window = values[index - period : index + 1]
        gains = 0.0
        losses = 0.0
        for previous, current in zip(window, window[1:]):
            change = current - previous
            if change >= 0:
                gains += change
            else:
                losses += abs(change)
        if losses == 0:
            result[index] = 100.0
        else:
            rs = gains / losses
            result[index] = 100 - 100 / (1 + rs)
    return result


def bollinger_bands(
    values: list[float],
    window: int = 20,
    num_std: float = 2.0,
) -> dict[str, list[float | None]]:
    if window <= 0:
        raise ValueError("window must be positive")
    upper: list[float | None] = []
    middle: list[float | None] = []
    lower: list[float | None] = []
    for index in range(len(values)):
        if index + 1 < window:
            upper.append(None)
            middle.append(None)
            lower.append(None)
            continue
        current = values[index + 1 - window : index + 1]
        avg = sum(current) / window
        variance = sum((item - avg) ** 2 for item in current) / window
        band_width = math.sqrt(variance) * num_std
        upper.append(avg + band_width)
        middle.append(avg)
        lower.append(avg - band_width)
    return {"upper": upper, "middle": middle, "lower": lower}


def volume_ma(values: list[float], window: int) -> list[float | None]:
    if window <= 0:
        raise ValueError("window must be positive")
    result: list[float | None] = []
    for index in range(len(values)):
        if index + 1 < window:
            result.append(None)
            continue
        result.append(sum(values[index + 1 - window : index + 1]) / window)
    return result
