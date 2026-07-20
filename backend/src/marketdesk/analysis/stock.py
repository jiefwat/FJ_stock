from math import sqrt

from marketdesk.models import (
    Bar,
    EquityQuote,
    StockAnalysisDimension,
    StockComparisonItem,
    StockDossier,
    StockInvestmentAdvice,
    StockScoreFactor,
    TechnicalSummary,
)


def _average(values: list[float], size: int) -> float | None:
    return sum(values[-size:]) / size if len(values) >= size else None


def analyse_stock(
    quote: EquityQuote,
    bars: list[Bar],
    research_evidence: list[str] | None = None,
    peer_quotes: list[EquityQuote] | None = None,
) -> StockDossier:
    research = research_evidence or []
    if not bars:
        advice = StockInvestmentAdvice(
            action="暂不参与",
            position_hint="0 仓位，先补齐历史行情",
            entry_plan="等历史行情、成交额、估值和资金证据齐全后再评估",
            stop_loss="无有效价格锚，不能设置可复核止损",
            take_profit="无有效压力位，不能设置止盈计划",
            time_horizon="补数据后重新判断",
            confidence=0,
            rationale=["历史行情缺失，无法计算趋势、波动和支撑压力"],
            disclaimer="研究建议不是保证收益，不能替代你的风险承受能力判断。",
        )
        return StockDossier(
            quote=quote,
            stance="insufficient_data",
            stance_score=None,
            conclusion=f"总结论：{quote.name} 历史行情证据不足，暂不能形成可复核的个股判断；需先补齐历史行情。",
            evidence_coverage=0,
            score_factors=[],
            analysis_dimensions=[],
            investment_advice=advice,
            horizontal_comparison=[],
            vertical_comparison=[],
            next_actions=["补齐历史行情后再判断趋势、波动和支撑压力"],
            research_evidence=research,
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
    missing = [] if research else ["公告与研报增强数据"]
    if quote.sector is None:
        missing.append("个股行业映射")
    if quote.net_flow is None:
        missing.append("资金流数据")
    history_coverage = 0.55 if len(bars) >= 60 else 0.4 if len(bars) >= 20 else 0.2
    evidence_coverage = history_coverage
    evidence_coverage += 0.15 if quote.pe is not None else 0
    evidence_coverage += 0.10 if quote.sector is not None else 0
    evidence_coverage += 0.10 if quote.net_flow is not None else 0
    evidence_coverage += 0.10 if research else 0
    dimensions = _analysis_dimensions(quote, closes[-1], technical, factors, research)
    next_actions = _next_actions(quote, technical, missing, dimensions)
    horizontal = _horizontal_comparison(quote, peer_quotes or [quote])
    vertical = _vertical_comparison(closes, technical)
    advice = _investment_advice(
        quote=quote,
        stance=stance,
        score=score,
        coverage=round(min(evidence_coverage, 1), 2),
        technical=technical,
        dimensions=dimensions,
        horizontal=horizontal,
        vertical=vertical,
        next_actions=next_actions,
    )
    conclusion = _build_conclusion(
        quote=quote,
        stance=stance,
        score=score,
        bull=bull,
        bear=bear,
        invalidation=invalidation,
        missing=missing,
        dimensions=dimensions,
        advice=advice,
        horizontal=horizontal,
        vertical=vertical,
        next_actions=next_actions,
    )
    return StockDossier(
        quote=quote,
        stance=stance,
        stance_score=score,
        conclusion=conclusion,
        evidence_coverage=round(min(evidence_coverage, 1), 2),
        score_factors=factors,
        analysis_dimensions=dimensions,
        investment_advice=advice,
        horizontal_comparison=horizontal,
        vertical_comparison=vertical,
        next_actions=next_actions,
        research_evidence=research,
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


def _signal(score: float | None, available: bool = True) -> str:
    if not available:
        return "missing"
    if score is None:
        return "neutral"
    if score >= 65:
        return "positive"
    if score < 45:
        return "negative"
    return "neutral"


def _money(value: float | None) -> str:
    if value is None:
        return "—"
    if abs(value) >= 100_000_000:
        return f"{value / 100_000_000:.1f} 亿"
    if abs(value) >= 10_000:
        return f"{value / 10_000:.0f} 万"
    return f"{value:.0f}"


def _signed_money(value: float | None) -> str:
    if value is None:
        return "—"
    sign = "+" if value > 0 else ""
    return f"{sign}{_money(value)}"


def _distance_pct(anchor: float | None, close: float) -> float | None:
    if anchor is None or close == 0:
        return None
    return (anchor / close - 1) * 100


def _factor_by_key(factors: list[StockScoreFactor], key: str) -> StockScoreFactor | None:
    return next((item for item in factors if item.key == key), None)


def _percentile_rank(value: float | None, values: list[float], higher_is_better: bool = True) -> float | None:
    if value is None or not values:
        return None
    usable = sorted(item for item in values if item is not None)
    if not usable:
        return None
    count = sum(1 for item in usable if item <= value)
    percentile = count / len(usable) * 100
    return round(percentile if higher_is_better else 100 - percentile, 1)


def _median(values: list[float]) -> float | None:
    usable = sorted(values)
    if not usable:
        return None
    mid = len(usable) // 2
    if len(usable) % 2:
        return usable[mid]
    return (usable[mid - 1] + usable[mid]) / 2


def _comparison_signal(percentile: float | None, available: bool = True) -> str:
    if not available or percentile is None:
        return "missing"
    if percentile >= 65:
        return "positive"
    if percentile < 35:
        return "negative"
    return "neutral"


def _horizontal_comparison(
    quote: EquityQuote, peer_quotes: list[EquityQuote]
) -> list[StockComparisonItem]:
    same_sector = [item for item in peer_quotes if quote.sector and item.sector == quote.sector]
    peers = same_sector if len(same_sector) >= 2 else peer_quotes
    benchmark_name = f"{quote.sector}同业" if quote.sector and len(same_sector) >= 2 else "全市场样本"

    change_values = [item.change_pct for item in peers if item.change_pct is not None]
    pe_values = [item.pe for item in peers if item.pe is not None and item.pe > 0]
    amount_values = [item.amount for item in peers if item.amount is not None]
    flow_values = [item.net_flow for item in peers if item.net_flow is not None]

    change_pctile = _percentile_rank(quote.change_pct, change_values)
    pe_pctile = _percentile_rank(quote.pe, pe_values, higher_is_better=False)
    amount_pctile = _percentile_rank(quote.amount, amount_values)
    flow_pctile = _percentile_rank(quote.net_flow, flow_values)
    pe_median = _median(pe_values)

    return [
        StockComparisonItem(
            key="sector_change_rank",
            label="涨跌强弱",
            signal=_comparison_signal(change_pctile, quote.change_pct is not None and bool(change_values)),
            value=f"{quote.change_pct:.2f}%" if quote.change_pct is not None else "暂缺",
            benchmark=benchmark_name,
            percentile=change_pctile,
            summary=(
                f"相对{benchmark_name}涨跌强度处于约 {change_pctile:.0f} 分位"
                if change_pctile is not None
                else "缺少同业涨跌幅，无法横向比较强弱"
            ),
            available=change_pctile is not None,
        ),
        StockComparisonItem(
            key="sector_pe_position",
            label="估值位置",
            signal=_comparison_signal(pe_pctile, quote.pe is not None and bool(pe_values)),
            value=f"PE {quote.pe:.1f}" if quote.pe is not None else "PE 暂缺",
            benchmark=f"{benchmark_name} PE 中位 {pe_median:.1f}" if pe_median is not None else benchmark_name,
            percentile=pe_pctile,
            summary=(
                f"PE {quote.pe:.1f} 相对{benchmark_name}估值吸引力约 {pe_pctile:.0f} 分位"
                if quote.pe is not None and pe_pctile is not None
                else "PE 缺失，无法判断相对估值"
            ),
            available=pe_pctile is not None,
        ),
        StockComparisonItem(
            key="sector_liquidity_rank",
            label="流动性排名",
            signal=_comparison_signal(amount_pctile, quote.amount is not None and bool(amount_values)),
            value=_money(quote.amount),
            benchmark=benchmark_name,
            percentile=amount_pctile,
            summary=(
                f"成交额在{benchmark_name}中约处于 {amount_pctile:.0f} 分位，流动性越高越便于执行"
                if amount_pctile is not None
                else "成交额缺失，无法横向比较流动性"
            ),
            available=amount_pctile is not None,
        ),
        StockComparisonItem(
            key="sector_capital_rank",
            label="资金排名",
            signal=_comparison_signal(flow_pctile, quote.net_flow is not None and bool(flow_values)),
            value=_signed_money(quote.net_flow),
            benchmark=benchmark_name,
            percentile=flow_pctile,
            summary=(
                f"主力净流相对{benchmark_name}约处于 {flow_pctile:.0f} 分位"
                if flow_pctile is not None
                else "资金流缺失，无法横向比较主动资金"
            ),
            available=flow_pctile is not None,
        ),
    ]


def _period_return(closes: list[float], days: int) -> float | None:
    if len(closes) <= days or closes[-days - 1] == 0:
        return None
    return (closes[-1] / closes[-days - 1] - 1) * 100


def _vertical_comparison(
    closes: list[float], technical: TechnicalSummary
) -> list[StockComparisonItem]:
    return_20 = _period_return(closes, 20)
    return_60 = _period_return(closes, 60)
    high_60 = max(closes[-60:]) if len(closes) >= 60 else None
    low_60 = min(closes[-60:]) if len(closes) >= 60 else None
    drawdown_60 = (closes[-1] / high_60 - 1) * 100 if high_60 else None
    range_position = (
        (closes[-1] - low_60) / (high_60 - low_60) * 100
        if high_60 is not None and low_60 is not None and high_60 != low_60
        else None
    )
    ma20_distance = _distance_pct(technical.ma20, closes[-1])

    return [
        StockComparisonItem(
            key="return_20d",
            label="20日收益",
            signal=_comparison_signal(50 + (return_20 or 0), return_20 is not None),
            value=f"{return_20:.1f}%" if return_20 is not None else "暂缺",
            benchmark="自身过去 20 日",
            percentile=None,
            summary=(
                f"过去 20 日累计涨跌 {return_20:.1f}%"
                if return_20 is not None
                else "历史不足，无法计算 20 日收益"
            ),
            available=return_20 is not None,
        ),
        StockComparisonItem(
            key="return_60d",
            label="60日收益",
            signal=_comparison_signal(50 + (return_60 or 0), return_60 is not None),
            value=f"{return_60:.1f}%" if return_60 is not None else "暂缺",
            benchmark="自身过去 60 日",
            percentile=None,
            summary=(
                f"过去 60 日累计涨跌 {return_60:.1f}%"
                if return_60 is not None
                else "历史不足，无法计算 60 日收益"
            ),
            available=return_60 is not None,
        ),
        StockComparisonItem(
            key="drawdown_60d",
            label="60日回撤",
            signal="positive" if drawdown_60 is not None and drawdown_60 > -8 else "negative" if drawdown_60 is not None and drawdown_60 < -20 else "neutral" if drawdown_60 is not None else "missing",
            value=f"{drawdown_60:.1f}%" if drawdown_60 is not None else "暂缺",
            benchmark="自身 60 日高点",
            percentile=None,
            summary=(
                f"距离过去 60 日高点回撤 {drawdown_60:.1f}%"
                if drawdown_60 is not None
                else "历史不足，无法计算 60 日回撤"
            ),
            available=drawdown_60 is not None,
        ),
        StockComparisonItem(
            key="range_position_60d",
            label="60日区间位置",
            signal=_comparison_signal(range_position, range_position is not None),
            value=f"{range_position:.0f}%" if range_position is not None else "暂缺",
            benchmark="自身 60 日价格区间",
            percentile=round(range_position, 1) if range_position is not None else None,
            summary=(
                f"现价处于过去 60 日价格区间约 {range_position:.0f}% 位置"
                if range_position is not None
                else "历史不足，无法判断区间位置"
            ),
            available=range_position is not None,
        ),
        StockComparisonItem(
            key="ma20_distance",
            label="MA20距离",
            signal="negative" if ma20_distance is not None and ma20_distance < -8 else "positive" if ma20_distance is not None and -3 <= ma20_distance <= 2 else "neutral" if ma20_distance is not None else "missing",
            value=f"{abs(ma20_distance):.1f}%" if ma20_distance is not None else "暂缺",
            benchmark="20 日均线",
            percentile=None,
            summary=(
                f"MA20 距现价 {ma20_distance:.1f}%，{'价格明显高于 MA20，追高风险上升' if ma20_distance < -8 else '接近 MA20，便于观察回踩确认' if -3 <= ma20_distance <= 2 else '用于判断追高或回踩空间'}"
                if ma20_distance is not None
                else "MA20 不足，无法判断均线距离"
            ),
            available=ma20_distance is not None,
        ),
    ]


def _investment_advice(
    quote: EquityQuote,
    stance: str,
    score: float,
    coverage: float,
    technical: TechnicalSummary,
    dimensions: list[StockAnalysisDimension],
    horizontal: list[StockComparisonItem],
    vertical: list[StockComparisonItem],
    next_actions: list[str],
) -> StockInvestmentAdvice:
    risk_reward = next((item for item in dimensions if item.key == "risk_reward"), None)
    overheat = technical.rsi14 is not None and technical.rsi14 > 75
    weak_rr = risk_reward is not None and risk_reward.score is not None and risk_reward.score < 45
    if stance == "strong_watch" and coverage >= 0.7 and not overheat and not weak_rr:
        action = "可小仓试错"
        position = "建议 10%-20% 试探仓，只有放量突破或回踩确认后再加"
    elif stance in {"strong_watch", "watch"}:
        action = "持有观察"
        position = "已有仓位可继续持有观察；新仓控制在 10% 以内，避免一次性追高"
    elif weak_rr or overheat:
        action = "等待回踩"
        position = "暂不追高，等价格回到支撑/MA20 附近再评估"
    else:
        action = "暂不参与"
        position = "0-5% 观察仓即可，把资金留给证据更完整的机会"

    stop_loss = (
        f"跌破 {technical.support:.2f} 且无法快速收回，放弃本轮跟踪"
        if technical.support is not None
        else "支撑位暂缺，先不设置交易"
    )
    take_profit = (
        f"接近 {technical.resistance:.2f} 时至少复核量能、资金流和板块温度"
        if technical.resistance is not None
        else "压力位暂缺，先不做止盈判断"
    )
    entry = next_actions[0] if next_actions else "等待趋势、估值、资金和事件证据共振"
    confidence = round(max(0.0, min(1.0, coverage * (0.55 + score / 200))), 2)
    rationale = [
        next((item.summary for item in dimensions if item.key == "trend"), "趋势证据不足"),
        next((item.summary for item in horizontal if item.available), "横向对比证据不足"),
        next((item.summary for item in vertical if item.available), "纵向对比证据不足"),
    ]
    if quote.net_flow is not None:
        rationale.append(f"资金流 {_signed_money(quote.net_flow)}")

    return StockInvestmentAdvice(
        action=action,
        position_hint=position,
        entry_plan=entry,
        stop_loss=stop_loss,
        take_profit=take_profit,
        time_horizon="1-4 周滚动复盘，跌破放弃线或证据恶化立即重评",
        confidence=confidence,
        rationale=rationale[:4],
        disclaimer="研究建议不是保证收益，不能替代你的风险承受能力判断。",
    )


def _analysis_dimensions(
    quote: EquityQuote,
    close: float,
    technical: TechnicalSummary,
    factors: list[StockScoreFactor],
    research: list[str],
) -> list[StockAnalysisDimension]:
    trend_factors = [
        item
        for item in factors
        if item.key in {"price_ma20", "ma5_ma20", "ma20_ma60", "rsi"}
    ]
    trend_score = max(0.0, min(100.0, 50 + sum(item.impact for item in trend_factors)))
    trend_evidence = [item.evidence for item in trend_factors]
    trend_summary = "；".join(trend_evidence[:3]) if trend_evidence else "趋势证据不足"

    upside = _distance_pct(technical.resistance, close)
    downside = _distance_pct(technical.support, close)
    risk_reward = None
    if upside is not None and downside is not None and downside < 0:
        risk_reward = upside / abs(downside)
    rr_score = 50.0
    if risk_reward is not None:
        rr_score = 70.0 if risk_reward >= 1.5 else 55.0 if risk_reward >= 0.8 else 35.0
    risk_reward_summary = (
        "支撑压力不足，暂不能计算风险收益比"
        if upside is None or downside is None or risk_reward is None
        else f"距压力位 {upside:.1f}%，距支撑位 {downside:.1f}%，风险收益比 {risk_reward:.2f}"
    )

    valuation_factor = _factor_by_key(factors, "valuation")
    valuation_available = valuation_factor.available if valuation_factor else False
    valuation_score = None if not valuation_available else max(0.0, min(100.0, 50 + (valuation_factor.impact if valuation_factor else 0) * 4))
    valuation_bits = []
    if quote.pe is not None:
        valuation_bits.append(f"PE {quote.pe:.1f}")
    if quote.pb is not None:
        valuation_bits.append(f"PB {quote.pb:.1f}")
    valuation_bits.append(valuation_factor.evidence if valuation_factor else "估值数据不足")

    amount = quote.amount
    turnover = quote.turnover_rate
    volume_ratio = quote.volume_ratio
    liquidity_score = 50.0
    liquidity_evidence: list[str] = []
    if amount is None:
        liquidity_score -= 15
        liquidity_evidence.append("成交额暂缺")
    else:
        liquidity_evidence.append(f"成交额 {_money(amount)}")
        liquidity_score += 15 if amount >= 300_000_000 else -10 if amount < 80_000_000 else 5
    if turnover is None:
        liquidity_evidence.append("换手率暂缺")
    else:
        liquidity_evidence.append(f"换手率 {turnover:.2f}%")
        liquidity_score += 8 if 1 <= turnover <= 8 else -5 if turnover > 12 else 0
    if volume_ratio is None:
        liquidity_evidence.append("量比暂缺")
    else:
        liquidity_evidence.append(f"量比 {volume_ratio:.2f}")
        liquidity_score += 6 if 1.1 <= volume_ratio <= 2.5 else -5 if volume_ratio > 4 else 0
    liquidity_score = max(0.0, min(100.0, liquidity_score))
    liquidity_summary = "，".join(liquidity_evidence[:3])

    net_flow = quote.net_flow
    if net_flow is None:
        capital_available = False
        capital_score = None
        capital_summary = "资金流数据暂缺，不能确认主动资金态度"
    else:
        capital_available = True
        capital_score = 65.0 if net_flow > 0 else 40.0 if net_flow < 0 else 50.0
        flow_tone = "偏正向" if net_flow > 0 else "偏谨慎" if net_flow < 0 else "中性"
        capital_summary = f"主力净流入 {_signed_money(net_flow)}，资金态度{flow_tone}"

    sector_available = quote.sector is not None
    sector_summary = (
        f"已映射到 {quote.sector}，需要和板块温度联动复核"
        if quote.sector
        else "行业映射暂缺，无法判断是否站在强势板块里"
    )

    research_available = bool(research)
    research_summary = (
        "；".join(research[:2])
        if research
        else "公告与研报增强数据暂缺，暂不能验证基本面叙事"
    )
    market_cap_score = 60.0 if quote.market_cap is None else 72.0 if quote.market_cap >= 50_000_000_000 else 58.0
    fundamental_score = max(
        0.0,
        min(
            100.0,
            50
            + (12 if quote.pe is not None and 0 < quote.pe < 35 else -6 if quote.pe is not None else 0)
            + (8 if quote.pb is not None and 0 < quote.pb < 5 else -4 if quote.pb is not None else 0)
            + (8 if quote.market_cap is not None and quote.market_cap >= 20_000_000_000 else 0)
            + (6 if research else 0),
        ),
    )
    fundamental_evidence = [
        f"PE {quote.pe:.1f}" if quote.pe is not None else "PE 暂缺",
        f"PB {quote.pb:.1f}" if quote.pb is not None else "PB 暂缺",
        f"总市值 {_money(quote.market_cap)}" if quote.market_cap is not None else "总市值暂缺",
    ]
    if research:
        fundamental_evidence.append(f"研究证据 {len(research)} 条")
    fundamental_summary = (
        "基本面质量用估值、规模和公告研报交叉验证；"
        + "，".join(fundamental_evidence[:3])
    )
    catalyst_score = None if not research and quote.sector is None else 50.0 + (12 if research else 0) + (6 if quote.sector else 0)
    catalyst_evidence = research[:3] if research else ["公告、研报和事件催化暂缺"]
    if quote.sector:
        catalyst_evidence.append(f"板块线索 {quote.sector}")
    catalyst_summary = (
        "催化与事件已有可跟踪线索：" + "；".join(catalyst_evidence[:3])
        if research
        else "催化与事件待补齐，不能只用价格波动解释上涨"
    )
    risk_control_score = max(
        0.0,
        min(
            100.0,
            58
            + (6 if technical.support is not None else -8)
            + (6 if technical.resistance is not None else -8)
            + (
                -8
                if technical.volatility20 is not None and technical.volatility20 > 40
                else 4
                if technical.volatility20 is not None and technical.volatility20 < 25
                else 0
            ),
        ),
    )
    risk_control_evidence = [
        f"放弃线 {technical.support:.2f}" if technical.support is not None else "放弃线暂缺",
        f"压力位 {technical.resistance:.2f}" if technical.resistance is not None else "压力位暂缺",
        f"波动率 {technical.volatility20:.1f}%"
        if technical.volatility20 is not None
        else "波动率暂缺",
    ]
    risk_control_summary = (
        "交易计划先定义放弃线、压力位和复核节奏；" + "，".join(risk_control_evidence)
    )

    return [
        StockAnalysisDimension(
            key="trend",
            label="趋势结构",
            signal=_signal(trend_score),
            score=round(trend_score, 1),
            summary=trend_summary,
            evidence=trend_evidence,
        ),
        StockAnalysisDimension(
            key="risk_reward",
            label="风险收益",
            signal=_signal(rr_score, risk_reward is not None),
            score=round(rr_score, 1) if risk_reward is not None else None,
            summary=risk_reward_summary,
            evidence=[
                f"现价 {close:.2f}",
                f"支撑 {technical.support:.2f}" if technical.support is not None else "支撑暂缺",
                f"压力 {technical.resistance:.2f}" if technical.resistance is not None else "压力暂缺",
            ],
            available=risk_reward is not None,
        ),
        StockAnalysisDimension(
            key="valuation",
            label="估值约束",
            signal=_signal(valuation_score, valuation_available),
            score=round(valuation_score, 1) if valuation_score is not None else None,
            summary="，".join(valuation_bits),
            evidence=valuation_bits,
            available=valuation_available,
        ),
        StockAnalysisDimension(
            key="liquidity",
            label="流动性",
            signal=_signal(liquidity_score, amount is not None),
            score=round(liquidity_score, 1) if amount is not None else None,
            summary=liquidity_summary,
            evidence=liquidity_evidence,
            available=amount is not None,
        ),
        StockAnalysisDimension(
            key="capital_flow",
            label="资金流",
            signal=_signal(capital_score, capital_available),
            score=capital_score,
            summary=capital_summary,
            evidence=[capital_summary],
            available=capital_available,
        ),
        StockAnalysisDimension(
            key="sector",
            label="行业位置",
            signal=_signal(55.0, sector_available),
            score=55.0 if sector_available else None,
            summary=sector_summary,
            evidence=[sector_summary],
            available=sector_available,
        ),
        StockAnalysisDimension(
            key="research",
            label="公告研报",
            signal=_signal(60.0, research_available),
            score=60.0 if research_available else None,
            summary=research_summary,
            evidence=research[:3] if research else [research_summary],
            available=research_available,
        ),
        StockAnalysisDimension(
            key="fundamental_quality",
            label="基本面质量",
            signal=_signal(fundamental_score),
            score=round(fundamental_score, 1),
            summary=fundamental_summary,
            evidence=fundamental_evidence,
        ),
        StockAnalysisDimension(
            key="catalyst",
            label="催化与事件",
            signal=_signal(catalyst_score, catalyst_score is not None),
            score=round(catalyst_score, 1) if catalyst_score is not None else None,
            summary=catalyst_summary,
            evidence=catalyst_evidence,
            available=catalyst_score is not None,
        ),
        StockAnalysisDimension(
            key="risk_controls",
            label="交易计划",
            signal=_signal(risk_control_score),
            score=round(risk_control_score, 1),
            summary=risk_control_summary,
            evidence=risk_control_evidence,
        ),
        StockAnalysisDimension(
            key="size_style",
            label="市值风格",
            signal=_signal(market_cap_score, quote.market_cap is not None),
            score=round(market_cap_score, 1) if quote.market_cap is not None else None,
            summary=(
                f"总市值 {_money(quote.market_cap)}，用于判断波动承载和机构关注度"
                if quote.market_cap is not None
                else "总市值暂缺，风格暴露待确认"
            ),
            evidence=[f"market_cap={_money(quote.market_cap)}"],
            available=quote.market_cap is not None,
        ),
    ]


def _next_actions(
    quote: EquityQuote,
    technical: TechnicalSummary,
    missing: list[str],
    dimensions: list[StockAnalysisDimension],
) -> list[str]:
    actions: list[str] = []
    risk_reward = next((item for item in dimensions if item.key == "risk_reward"), None)
    if technical.support is not None:
        actions.append(f"把 {technical.support:.2f} 作为跟踪放弃线，跌破后重新评估")
    if technical.resistance is not None:
        actions.append(f"接近 {technical.resistance:.2f} 压力位时复核量能和资金流")
    if risk_reward and risk_reward.score is not None and risk_reward.score < 50:
        actions.append("风险收益比不足时不追高，等待回踩后的新证据")
    if quote.net_flow is None:
        actions.append("补齐资金流数据，确认上涨是否有资金配合")
    if missing:
        actions.append(f"优先补齐{missing[0]}，避免只用行情数据下结论")
    if quote.sector:
        actions.append(f"把 {quote.sector} 板块温度和个股强弱放在一起复核")
    actions.append("补读最新公告与研报，确认基本面叙事是否支持当前估值")
    actions.append("写清关注理由、放弃条件和下次复盘时间，避免临盘追涨")
    return actions[:7]


def _build_conclusion(
    quote: EquityQuote,
    stance: str,
    score: float,
    bull: list[str],
    bear: list[str],
    invalidation: list[str],
    missing: list[str],
    dimensions: list[StockAnalysisDimension],
    advice: StockInvestmentAdvice,
    horizontal: list[StockComparisonItem],
    vertical: list[StockComparisonItem],
    next_actions: list[str],
) -> str:
    stance_labels = {
        "strong_watch": "重点观察",
        "watch": "观察",
        "neutral": "中性",
        "avoid": "回避",
        "insufficient_data": "证据不足",
    }
    action_text = {
        "strong_watch": "可列为重点观察",
        "watch": "可继续观察",
        "neutral": "暂不形成明确倾向",
        "avoid": "暂先回避进攻性机会",
        "insufficient_data": "暂不形成结论",
    }
    support = "、".join(bull[:2]) if bull else "暂无明确正向证据"
    risk = "、".join(bear[:2]) if bear else "暂无强反方证据"
    invalid = invalidation[0] if invalidation else "核心证据链转弱"
    missing_text = "、".join(missing) if missing else "关键证据相对完整"
    label = stance_labels.get(stance, stance)
    action = action_text.get(stance, "继续跟踪证据变化")
    by_key = {item.key: item for item in dimensions}
    trend = by_key.get("trend")
    risk_reward = by_key.get("risk_reward")
    valuation = by_key.get("valuation")
    liquidity = by_key.get("liquidity")
    capital = by_key.get("capital_flow")
    sector = by_key.get("sector")
    fundamental = by_key.get("fundamental_quality")
    catalyst = by_key.get("catalyst")
    risk_controls = by_key.get("risk_controls")
    next_step = next_actions[0] if next_actions else "继续补证据后再调整判断"
    horizontal_text = "；".join(item.summary for item in horizontal[:2]) if horizontal else "横向样本不足"
    vertical_text = "；".join(item.summary for item in vertical[:2]) if vertical else "纵向历史不足"
    return (
        f"总结论：{quote.name} 当前为{label}（{score:.0f}/100），{action}，但不是买卖指令。"
        f"投资建议：{advice.action}；{advice.position_hint}；入场：{advice.entry_plan}；止损：{advice.stop_loss}；止盈：{advice.take_profit}。"
        f"技术面：{trend.summary if trend else support}。"
        f"风险收益：{risk_reward.summary if risk_reward else '支撑压力不足'}。"
        f"估值：{valuation.summary if valuation else '估值数据不足'}；"
        f"流动性：{liquidity.summary if liquidity else '成交数据不足'}。"
        f"基本面：{fundamental.summary if fundamental else '基本面证据待补'}。"
        f"催化：{catalyst.summary if catalyst else '公告研报催化待补'}。"
        f"资金/行业：{capital.summary if capital else '资金流暂缺'}；{sector.summary if sector else '行业映射暂缺'}。"
        f"横向对比：{horizontal_text}。"
        f"纵向对比：{vertical_text}。"
        f"交易计划：{risk_controls.summary if risk_controls else '先定义放弃线和复盘节奏'}。"
        f"主要风险：{risk}；若 {invalid} 则关注理由失效。"
        f"下一步：{next_step}。仍需补齐{missing_text}。"
    )
