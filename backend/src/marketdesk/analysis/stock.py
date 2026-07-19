from math import sqrt

from marketdesk.models import (
    Bar,
    EquityQuote,
    StockDossier,
    StockScoreFactor,
    TechnicalSummary,
)


def _average(values: list[float], size: int) -> float | None:
    return sum(values[-size:]) / size if len(values) >= size else None


def analyse_stock(quote: EquityQuote, bars: list[Bar]) -> StockDossier:
    if not bars:
        return StockDossier(
            quote=quote,
            stance="insufficient_data",
            stance_score=None,
            evidence_coverage=0,
            score_factors=[],
            technical=None,
            bull_case=[],
            bear_case=[],
            invalidation=[],
            missing_evidence=["历史行情"],
            bars=[],
        )
    closes = [bar.close for bar in bars]
    returns = [
        (closes[index] / closes[index - 1] - 1)
        for index in range(1, len(closes))
        if closes[index - 1]
    ]
    recent_returns = returns[-20:]
    volatility = None
    if len(recent_returns) >= 2:
        mean = sum(recent_returns) / len(recent_returns)
        volatility = (
            sqrt(sum((value - mean) ** 2 for value in recent_returns) / (len(recent_returns) - 1))
            * sqrt(252)
            * 100
        )
    gains = [max(value, 0) for value in returns[-14:]]
    losses = [abs(min(value, 0)) for value in returns[-14:]]
    rsi = None
    if len(returns) >= 14:
        avg_gain = sum(gains) / 14
        avg_loss = sum(losses) / 14
        rsi = 100 if avg_loss == 0 else 100 - 100 / (1 + avg_gain / avg_loss)
    technical = TechnicalSummary(
        ma5=_average(closes, 5),
        ma20=_average(closes, 20),
        ma60=_average(closes, 60),
        rsi14=rsi,
        volatility20=volatility,
        support=min(closes[-20:]),
        resistance=max(closes[-20:]),
    )
    factors = _score_factors(quote, closes[-1], technical)
    score = round(max(0.0, min(100.0, 50 + sum(item.impact for item in factors))), 2)
    stance = (
        "strong_watch"
        if score >= 75
        else "watch"
        if score >= 60
        else "neutral"
        if score >= 45
        else "avoid"
    )
    bull = [item.evidence for item in factors if item.impact > 0]
    bear = [item.evidence for item in factors if item.impact < 0]
    invalidation = (
        [f"跌破近 20 日支撑 {technical.support:.2f}"] if technical.support is not None else []
    )
    missing = ["公告与研报增强数据"]
    if quote.sector is None:
        missing.append("个股行业映射")
    if quote.net_flow is None:
        missing.append("资金流数据")
    history_coverage = 0.55 if len(bars) >= 60 else 0.4 if len(bars) >= 20 else 0.2
    evidence_coverage = history_coverage
    evidence_coverage += 0.15 if quote.pe is not None else 0
    evidence_coverage += 0.10 if quote.sector is not None else 0
    evidence_coverage += 0.10 if quote.net_flow is not None else 0
    return StockDossier(
        quote=quote,
        stance=stance,
        stance_score=score,
        evidence_coverage=round(evidence_coverage, 2),
        score_factors=factors,
        technical=technical,
        bull_case=bull,
        bear_case=bear,
        invalidation=invalidation,
        missing_evidence=missing,
        bars=bars,
    )


def _factor(
    key: str,
    label: str,
    impact: float,
    evidence: str,
    available: bool = True,
) -> StockScoreFactor:
    signal = "missing" if not available else "positive" if impact > 0 else "negative" if impact < 0 else "neutral"
    return StockScoreFactor(
        key=key,
        label=label,
        impact=impact,
        signal=signal,
        evidence=evidence,
        available=available,
    )


def _score_factors(
    quote: EquityQuote, close: float, technical: TechnicalSummary
) -> list[StockScoreFactor]:
    factors: list[StockScoreFactor] = []
    if technical.ma20 is None:
        factors.append(_factor("price_ma20", "价格与 MA20", 0, "MA20 数据不足", False))
    elif close >= technical.ma20:
        factors.append(_factor("price_ma20", "价格与 MA20", 10, "收盘价位于 20 日均线之上"))
    else:
        factors.append(_factor("price_ma20", "价格与 MA20", -10, "收盘价低于 20 日均线"))

    if technical.ma5 is None or technical.ma20 is None:
        factors.append(_factor("ma5_ma20", "短期均线", 0, "短期均线数据不足", False))
    elif technical.ma5 >= technical.ma20:
        factors.append(_factor("ma5_ma20", "短期均线", 8, "MA5 位于 MA20 之上"))
    else:
        factors.append(_factor("ma5_ma20", "短期均线", -6, "MA5 低于 MA20"))

    if technical.ma20 is None or technical.ma60 is None:
        factors.append(_factor("ma20_ma60", "中期均线", 0, "中期均线数据不足", False))
    elif technical.ma20 >= technical.ma60:
        factors.append(_factor("ma20_ma60", "中期均线", 8, "MA20 位于 MA60 之上"))
    else:
        factors.append(_factor("ma20_ma60", "中期均线", -8, "MA20 低于 MA60"))

    rsi = technical.rsi14
    if rsi is None:
        factors.append(_factor("rsi", "RSI 动量", 0, "RSI 数据不足", False))
    elif 45 <= rsi <= 70:
        factors.append(_factor("rsi", "RSI 动量", 5, f"RSI {rsi:.1f} 处于健康区间"))
    elif rsi > 75:
        factors.append(_factor("rsi", "RSI 动量", -8, f"RSI {rsi:.1f} 显示短线过热"))
    elif rsi < 30:
        factors.append(_factor("rsi", "RSI 动量", -5, f"RSI {rsi:.1f} 显示弱势超卖"))
    else:
        factors.append(_factor("rsi", "RSI 动量", 0, f"RSI {rsi:.1f} 信号中性"))

    volatility = technical.volatility20
    if volatility is None:
        factors.append(_factor("volatility", "波动风险", 0, "波动率数据不足", False))
    elif volatility < 25:
        factors.append(_factor("volatility", "波动风险", 5, f"年化波动率 {volatility:.1f}% 较低"))
    elif volatility > 40:
        factors.append(_factor("volatility", "波动风险", -8, f"年化波动率 {volatility:.1f}% 偏高"))
    else:
        factors.append(_factor("volatility", "波动风险", 0, f"年化波动率 {volatility:.1f}% 中性"))

    if quote.pe is None:
        factors.append(_factor("valuation", "估值约束", 0, "PE 数据不足", False))
    elif 0 < quote.pe < 50:
        factors.append(_factor("valuation", "估值约束", 5, f"PE {quote.pe:.1f} 位于约束区间"))
    else:
        factors.append(_factor("valuation", "估值约束", -5, f"PE {quote.pe:.1f} 超出约束区间"))

    if quote.change_pct is None:
        factors.append(_factor("chase_risk", "追涨风险", 0, "当日涨跌数据不足", False))
    elif quote.change_pct > 7:
        factors.append(_factor("chase_risk", "追涨风险", -8, f"当日涨幅 {quote.change_pct:.1f}% 偏高"))
    elif quote.change_pct < -7:
        factors.append(_factor("chase_risk", "极端波动", -5, f"当日跌幅 {quote.change_pct:.1f}% 偏大"))
    else:
        factors.append(_factor("chase_risk", "追涨风险", 0, "当日涨跌未触发极端波动约束"))
    return factors
