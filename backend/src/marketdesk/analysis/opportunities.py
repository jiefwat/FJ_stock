from math import sqrt

from marketdesk.analysis.decisions import candidate_decision
from marketdesk.analysis.indicators import maximum_drawdown
from marketdesk.models import (
    Bar,
    EquityQuote,
    ExcludedCandidate,
    OpportunityDimension,
    OpportunityHistoryCheck,
    OpportunityResult,
    RankedCandidate,
    ScoreComponent,
    StrategyValidation,
)

STRATEGY_LABELS = {
    "trend": "趋势延续",
    "volume_breakout": "放量突破",
    "value_rebound": "低估反弹",
    "oversold_repair": "超跌修复",
    "capital_confirmed": "资金确认",
    "sector_momentum": "板块共振",
    "pullback_support": "回踩企稳",
    "quality_value": "估值质量",
    "large_cap_stability": "蓝筹稳健",
}

STRATEGY_RULES = {
    "trend": ["涨幅 0.5% 至 7%", "成交额至少 3 亿元", "排除涨停追高"],
    "volume_breakout": ["涨幅 1% 至 8%", "成交额至少 5 亿元", "量比高于 1.3 或换手率高于 3%"],
    "value_rebound": ["涨跌幅 -1% 至 2%", "PE 介于 0 至 30", "PB 不高于 5 且成交额至少 1 亿元"],
    "oversold_repair": ["当日跌幅 -7% 至 -1%", "PE 介于 0 至 60", "成交额至少 1 亿元"],
    "capital_confirmed": ["涨跌幅 -1% 至 6%", "主力净流入至少 2000 万", "成交额至少 3 亿元"],
    "sector_momentum": ["已归属行业板块", "涨幅 0% 至 6%", "成交额至少 3 亿元且量能/换手不弱"],
    "pullback_support": ["涨跌幅 -3% 至 1.5%", "资金不净流出", "成交额至少 2 亿元"],
    "quality_value": ["PE 介于 0 至 25", "PB 介于 0 至 3.5", "市值至少 100 亿元"],
    "large_cap_stability": ["市值至少 500 亿元", "成交额至少 5 亿元", "涨跌幅 -1.5% 至 3.5%"],
}

PRESET_ALIASES = {
    "sector_improving": "sector_momentum",
    "oversold_rebound": "oversold_repair",
}

RECOMMENDATION_ALGORITHM_VERSION = "strategy-profiles-v3"


def _score(value: float | None, low: float, high: float) -> float:
    if value is None:
        return 50.0
    if high == low:
        return 50.0
    return max(0.0, min(100.0, (value - low) / (high - low) * 100))


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


def _clamp_score(value: float) -> float:
    return max(0.0, min(100.0, value))


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
    return f"{'+' if value > 0 else ''}{_money(value)}"


def rank_candidates(
    equities: list[EquityQuote],
    market_regime: str,
    preset: str = "trend",
    history_by_symbol: dict[str, list[Bar]] | None = None,
    sector_strength: dict[str, float] | None = None,
) -> OpportunityResult:
    preset = PRESET_ALIASES.get(preset, preset)
    if preset not in STRATEGY_RULES:
        raise ValueError("unknown preset")

    excluded: list[ExcludedCandidate] = []
    ranked: list[RankedCandidate] = []
    for quote in equities:
        reasons: list[str] = []
        if "ST" in quote.name.upper() or "退" in quote.name:
            reasons.append("special_treatment")
        if quote.price is None or quote.price <= 0:
            reasons.append("invalid_price")
        if quote.amount is None or quote.amount < 100_000_000:
            reasons.append("insufficient_liquidity")
        if quote.market_cap is not None and quote.market_cap < 2_000_000_000:
            reasons.append("insufficient_market_cap")
        validation = _strategy_validation(quote, preset, sector_strength)
        if not reasons and not validation.passed:
            reasons.extend(validation.failures or ["strategy_mismatch"])
        if reasons:
            excluded.append(ExcludedCandidate(quote=quote, reasons=reasons))
            continue
        component_values: list[tuple[str, str, float, float, float]] = []
        risk_flags: list[str] = []
        history_check: OpportunityHistoryCheck | None = None
        if history_by_symbol is not None and quote.symbol in history_by_symbol:
            history_check = analyse_opportunity_history(history_by_symbol[quote.symbol])
        if quote.change_pct is not None:
            component_values.append(
                ("trend", "价格趋势", _score(quote.change_pct, -3, 5), 0.25, quote.change_pct)
            )
        if quote.net_flow is not None:
            component_values.append(
                (
                    "capital",
                    "资金确认",
                    _score(quote.net_flow, -50_000_000, 100_000_000),
                    0.20,
                    quote.net_flow,
                )
            )
        else:
            risk_flags.append("资金数据暂缺")
        if quote.amount is not None:
            component_values.append(
                (
                    "liquidity",
                    "流动性",
                    _score(quote.amount, 100_000_000, 1_500_000_000),
                    0.15,
                    quote.amount,
                )
            )
        if quote.pe is not None:
            component_values.append(
                (
                    "valuation",
                    "估值约束",
                    75.0 if 0 < quote.pe < 50 else 35.0,
                    0.10,
                    quote.pe,
                )
            )
        if history_check is not None:
            if history_check.available and history_check.score is not None:
                component_values.append(
                    (
                        "history_confirmation",
                        "历史确认",
                        history_check.score,
                        0.20,
                        history_check.trend_20d_pct or 0.0,
                    )
                )
            else:
                risk_flags.append("历史K线不足")
            risk_flags.extend(history_check.risk_flags)
        if quote.sector is None:
            risk_flags.append("板块归属暂缺")
        elif sector_strength is None or quote.sector not in sector_strength:
            risk_flags.append("板块强度数据暂缺")
        risk_flags.append("催化证据暂缺")
        available_weight = sum(item[3] for item in component_values)
        components = [
            ScoreComponent(
                key=key,
                label=label,
                raw_value=raw,
                score=round(score, 2),
                weight=weight / available_weight,
                weighted_score=round(score * weight / available_weight, 2),
            )
            for key, label, score, weight, raw in component_values
        ]
        base_score = round(sum(item.weighted_score for item in components), 2)
        context_penalty = (
            15.0 if market_regime == "risk_off" else 8.0 if market_regime == "cautious" else 0.0
        )
        upside_score, upside_label, upside_summary, upside_drivers, upside_risks = (
            _candidate_upside(
                quote=quote,
                preset=preset,
                components=components,
                context_penalty=context_penalty,
                history_check=history_check,
                sector_strength=sector_strength,
            )
        )
        if market_regime in {"risk_off", "cautious"}:
            risk_flags.append("市场偏弱")
        risk_flags = list(dict.fromkeys(risk_flags))
        candidate = RankedCandidate(
                quote=quote,
                base_score=base_score,
                context_penalty=context_penalty,
                score=upside_score,
                upside_score=upside_score,
                upside_label=upside_label,
                upside_summary=upside_summary,
                upside_drivers=upside_drivers,
                upside_risks=upside_risks,
                evidence_coverage=round(min(1.0, available_weight), 2),
                components=components,
                dimensions=_candidate_dimensions(
                    quote,
                    preset,
                    components,
                    context_penalty,
                    history_check,
                    validation,
                    sector_strength,
                ),
                history_check=history_check,
                strategy_validation=validation,
                thesis=_candidate_thesis(quote, preset),
                invalidation=_candidate_invalidation(quote, preset),
                next_actions=_candidate_next_actions(quote, context_penalty),
                risk_flags=risk_flags,
        )
        ranked.append(candidate.model_copy(update={"decision": candidate_decision(candidate)}))
    ranked.sort(key=lambda item: item.upside_score, reverse=True)
    funnel = {"universe": len(equities), "excluded": len(excluded), "ranked": len(ranked)}
    diagnostics = _strategy_diagnostics(
        equities=equities,
        market_regime=market_regime,
        preset=preset,
        funnel=funnel,
        available=True,
        unavailable_reason=None,
    )
    return OpportunityResult(
        preset=preset,
        available=True,
        summary=_strategy_summary(preset, market_regime, funnel),
        rules=STRATEGY_RULES[preset],
        diagnostics=diagnostics,
        next_actions=_strategy_next_actions(preset, diagnostics, market_regime, available=True),
        funnel=funnel,
        candidates=ranked,
        excluded=excluded,
    )


def analyse_opportunity_history(bars: list[Bar]) -> OpportunityHistoryCheck:
    ordered = sorted(bars, key=lambda item: item.date)
    closes = [bar.close for bar in ordered if bar.close > 0]
    if len(closes) < 20:
        return OpportunityHistoryCheck(
            available=False,
            lookback_days=len(closes),
            summary=f"历史K线不足：仅 {len(closes)} 个交易日，不能确认趋势、波动和回撤。",
            evidence=["至少需要 20 个交易日K线"],
            risk_flags=["历史K线不足"],
        )

    latest = closes[-1]
    ma20 = sum(closes[-20:]) / 20
    trend_20d = (
        (latest / closes[-21] - 1) * 100 if len(closes) >= 21 else (latest / closes[0] - 1) * 100
    )
    trend_60d = (latest / closes[-61] - 1) * 100 if len(closes) >= 61 else None
    ma20_gap = (latest / ma20 - 1) * 100 if ma20 > 0 else None
    returns = [
        (closes[index] / closes[index - 1] - 1)
        for index in range(1, len(closes))
        if closes[index - 1] > 0
    ]
    recent_returns = returns[-20:]
    volatility = None
    if recent_returns:
        mean = sum(recent_returns) / len(recent_returns)
        variance = sum((value - mean) ** 2 for value in recent_returns) / len(recent_returns)
        volatility = sqrt(variance) * sqrt(252) * 100
    drawdown = maximum_drawdown(closes, min(60, len(closes)))
    volumes = [bar.volume for bar in ordered if bar.volume > 0]
    volume_ratio = None
    if len(volumes) >= 21:
        average_volume = sum(volumes[-21:-1]) / 20
        volume_ratio = volumes[-1] / average_volume if average_volume > 0 else None

    score = 50.0
    score += max(-18.0, min(20.0, trend_20d * 1.25))
    if trend_60d is not None:
        score += max(-12.0, min(15.0, trend_60d * 0.45))
    else:
        score -= 4.0
    if ma20_gap is not None:
        if -4 <= ma20_gap <= 10:
            score += 12.0
        elif 10 < ma20_gap <= 15:
            score += 4.0
        elif ma20_gap > 15:
            score -= min(18.0, (ma20_gap - 15) * 1.4)
        else:
            score -= min(12.0, abs(ma20_gap) * 1.2)
    if volatility is not None:
        if volatility <= 35:
            score += 8.0
        elif volatility > 60:
            score -= 14.0
        elif volatility > 45:
            score -= 6.0
    if drawdown is not None:
        if drawdown <= 12:
            score += 8.0
        elif drawdown > 30:
            score -= 14.0
        elif drawdown > 20:
            score -= 7.0
    if volume_ratio is not None:
        if 1.1 <= volume_ratio <= 2.5:
            score += 8.0
        elif volume_ratio > 4:
            score -= 7.0
        elif volume_ratio < 0.75:
            score -= 5.0

    risk_flags: list[str] = []
    if ma20_gap is not None and ma20_gap > 15:
        risk_flags.append("远离MA20，追高风险")
    if volatility is not None and volatility > 45:
        risk_flags.append("20日波动偏高")
    if drawdown is not None and drawdown > 20:
        risk_flags.append("60日回撤偏深")
    if volume_ratio is not None and volume_ratio > 4:
        risk_flags.append("放量过急，需等回踩确认")
    if trend_20d < -3:
        risk_flags.append("20日趋势转弱")

    evidence = [
        f"20日趋势 {trend_20d:+.1f}%",
        f"MA20偏离 {ma20_gap:+.1f}%" if ma20_gap is not None else "MA20偏离待确认",
    ]
    if trend_60d is not None:
        evidence.append(f"60日趋势 {trend_60d:+.1f}%")
    if volatility is not None:
        evidence.append(f"20日波动 {volatility:.1f}%")
    if drawdown is not None:
        evidence.append(f"60日最大回撤 {drawdown:.1f}%")
    if volume_ratio is not None:
        evidence.append(f"量能 {volume_ratio:.1f}x")

    status = "通过" if score >= 65 and not risk_flags else "需复核" if score >= 50 else "偏弱"
    summary = (
        f"历史确认{status}：20日趋势 {trend_20d:+.1f}%，"
        f"MA20偏离 {ma20_gap:+.1f}%，"
        f"{'未明显追高' if ma20_gap is not None and ma20_gap <= 15 else '注意追高'}。"
    )
    return OpportunityHistoryCheck(
        available=True,
        lookback_days=len(closes),
        score=round(max(0.0, min(100.0, score)), 2),
        trend_20d_pct=round(trend_20d, 2),
        trend_60d_pct=round(trend_60d, 2) if trend_60d is not None else None,
        ma20_gap_pct=round(ma20_gap, 2) if ma20_gap is not None else None,
        volatility_20d=round(volatility, 2) if volatility is not None else None,
        max_drawdown_60d=round(drawdown, 2) if drawdown is not None else None,
        volume_ratio_20d=round(volume_ratio, 2) if volume_ratio is not None else None,
        summary=summary,
        evidence=evidence,
        risk_flags=risk_flags,
    )


def _gate(checks: list[str], failures: list[str], passed: bool, ok: str, fail: str) -> None:
    if passed:
        checks.append(ok)
    else:
        failures.append(fail)


def _strategy_validation(
    quote: EquityQuote,
    preset: str,
    sector_strength: dict[str, float] | None = None,
) -> StrategyValidation:
    checks: list[str] = []
    failures: list[str] = []
    change = quote.change_pct
    amount = quote.amount or 0.0
    net_flow = quote.net_flow
    volume_active = (quote.volume_ratio or 0) >= 1.3 or (quote.turnover_rate or 0) >= 3
    mild_activity = (quote.volume_ratio or 0) >= 1.0 or (quote.turnover_rate or 0) >= 1.5

    if preset == "trend":
        _gate(
            checks,
            failures,
            change is not None and 0.5 <= change <= 7,
            "涨幅在趋势区间",
            "strategy_mismatch",
        )
        _gate(checks, failures, amount >= 300_000_000, "成交额 >= 3 亿", "insufficient_liquidity")
        _gate(
            checks,
            failures,
            change is not None and change < 9.5,
            "未触及涨停追高",
            "limit_up_chasing",
        )
    elif preset == "volume_breakout":
        _gate(
            checks,
            failures,
            change is not None and 1 <= change <= 8,
            "涨幅在突破区间",
            "strategy_mismatch",
        )
        _gate(checks, failures, amount >= 500_000_000, "成交额 >= 5 亿", "insufficient_liquidity")
        _gate(checks, failures, volume_active, "量比或换手确认", "volume_not_confirmed")
    elif preset == "value_rebound":
        _gate(
            checks,
            failures,
            change is not None and -1 <= change <= 2,
            "价格未明显追高",
            "strategy_mismatch",
        )
        _gate(
            checks,
            failures,
            quote.pe is not None and 0 < quote.pe <= 30,
            "PE 在低估区间",
            "valuation_not_qualified",
        )
        _gate(
            checks,
            failures,
            quote.pb is None or quote.pb <= 5,
            "PB 未拥挤",
            "valuation_not_qualified",
        )
        _gate(checks, failures, amount >= 100_000_000, "成交额 >= 1 亿", "insufficient_liquidity")
    elif preset == "oversold_repair":
        _gate(
            checks,
            failures,
            change is not None and -7 <= change <= -1,
            "跌幅进入修复观察区",
            "strategy_mismatch",
        )
        _gate(
            checks,
            failures,
            quote.pe is not None and 0 < quote.pe <= 60,
            "PE 未失真",
            "valuation_not_qualified",
        )
        _gate(checks, failures, amount >= 100_000_000, "成交额 >= 1 亿", "insufficient_liquidity")
    elif preset == "capital_confirmed":
        _gate(
            checks,
            failures,
            change is not None and -1 <= change <= 6,
            "价格未过热",
            "strategy_mismatch",
        )
        _gate(
            checks,
            failures,
            net_flow is not None and net_flow >= 20_000_000,
            "资金净流入 >= 2000 万",
            "capital_not_confirmed",
        )
        _gate(checks, failures, amount >= 300_000_000, "成交额 >= 3 亿", "insufficient_liquidity")
        _gate(
            checks,
            failures,
            quote.turnover_rate is None or quote.turnover_rate <= 12,
            "换手未异常过热",
            "overheated_turnover",
        )
    elif preset == "sector_momentum":
        _gate(checks, failures, quote.sector is not None, "板块归属明确", "sector_missing")
        if sector_strength is not None:
            _gate(
                checks,
                failures,
                quote.sector is not None and quote.sector in sector_strength,
                "板块强度已覆盖",
                "sector_strength_missing",
            )
        _gate(
            checks,
            failures,
            change is not None and 0 <= change <= 6,
            "个股涨幅跟随板块",
            "strategy_mismatch",
        )
        _gate(checks, failures, amount >= 300_000_000, "成交额 >= 3 亿", "insufficient_liquidity")
        _gate(checks, failures, mild_activity, "量能或换手不弱", "volume_not_confirmed")
    elif preset == "pullback_support":
        _gate(
            checks,
            failures,
            change is not None and -3 <= change <= 1.5,
            "回踩幅度可控",
            "strategy_mismatch",
        )
        _gate(
            checks,
            failures,
            net_flow is not None and net_flow >= 0,
            "资金没有净流出",
            "capital_not_confirmed",
        )
        _gate(checks, failures, amount >= 200_000_000, "成交额 >= 2 亿", "insufficient_liquidity")
        _gate(
            checks,
            failures,
            quote.pe is None or 0 < quote.pe <= 50,
            "估值未明显失真",
            "valuation_not_qualified",
        )
    elif preset == "quality_value":
        _gate(
            checks,
            failures,
            change is not None and -2 <= change <= 3,
            "价格仍在低位观察区",
            "strategy_mismatch",
        )
        _gate(
            checks,
            failures,
            quote.pe is not None and 0 < quote.pe <= 25,
            "PE <= 25",
            "valuation_not_qualified",
        )
        _gate(
            checks,
            failures,
            quote.pb is not None and 0 < quote.pb <= 3.5,
            "PB <= 3.5",
            "valuation_not_qualified",
        )
        _gate(
            checks,
            failures,
            quote.market_cap is not None and quote.market_cap >= 10_000_000_000,
            "市值 >= 100 亿",
            "insufficient_market_cap",
        )
        _gate(checks, failures, amount >= 150_000_000, "成交额 >= 1.5 亿", "insufficient_liquidity")
    elif preset == "large_cap_stability":
        _gate(
            checks,
            failures,
            quote.market_cap is not None and quote.market_cap >= 50_000_000_000,
            "市值 >= 500 亿",
            "insufficient_market_cap",
        )
        _gate(checks, failures, amount >= 500_000_000, "成交额 >= 5 亿", "insufficient_liquidity")
        _gate(
            checks,
            failures,
            change is not None and -1.5 <= change <= 3.5,
            "波动在稳健区间",
            "strategy_mismatch",
        )
        _gate(
            checks,
            failures,
            quote.turnover_rate is None or quote.turnover_rate <= 8,
            "换手不过热",
            "overheated_turnover",
        )
        _gate(
            checks,
            failures,
            quote.pe is None or 0 < quote.pe <= 40,
            "估值未明显失真",
            "valuation_not_qualified",
        )
    else:
        failures.append("strategy_mismatch")

    return StrategyValidation(
        passed=not failures, checks=checks, failures=list(dict.fromkeys(failures))
    )


def _matches_preset(quote: EquityQuote, preset: str) -> bool:
    return _strategy_validation(quote, preset).passed


def _strategy_summary(preset: str, market_regime: str, funnel: dict[str, int]) -> str:
    label = STRATEGY_LABELS.get(preset, preset)
    ranked = funnel.get("ranked", 0)
    universe = funnel.get("universe", 0)
    rate = ranked / universe * 100 if universe else 0
    regime_text = {
        "risk_off": "防守市况下只适合把线索放进证据复核，不适合扩大进攻",
        "cautious": "谨慎市况下需要提高确认标准",
        "balanced": "均衡市况下可按复核优先级推进线索短名单",
        "risk_on": "积极市况下可放宽观察范围，但仍需控制追高",
    }.get(market_regime, "市场环境待确认")
    return (
        f"{label}线索策略当前可运行，筛出线索 {ranked}/{universe}（{rate:.1f}%）；{regime_text}。"
    )


def _strategy_diagnostics(
    equities: list[EquityQuote],
    market_regime: str,
    preset: str,
    funnel: dict[str, int],
    available: bool,
    unavailable_reason: str | None,
) -> list[OpportunityDimension]:
    universe = max(funnel.get("universe", len(equities)), 1)
    ranked = funnel.get("ranked", 0)
    selection_rate = ranked / universe * 100
    flow_coverage = sum(1 for quote in equities if quote.net_flow is not None) / universe
    sector_coverage = sum(1 for quote in equities if quote.sector is not None) / universe
    amount_coverage = sum(1 for quote in equities if quote.amount is not None) / universe
    evidence_coverage = (flow_coverage + sector_coverage + amount_coverage) / 3
    penalty = 15 if market_regime == "risk_off" else 8 if market_regime == "cautious" else 0
    market_score = 70 - penalty * 2
    selection_score = 75 if 1 <= selection_rate <= 8 else 50 if selection_rate <= 15 else 35
    data_score = evidence_coverage * 100
    risk_score = 45 if market_regime == "risk_off" else 55 if market_regime == "cautious" else 70
    return [
        OpportunityDimension(
            key="market_fit",
            label="市场适配",
            signal=_signal(market_score, available),
            score=round(market_score, 1) if available else None,
            summary=(
                f"当前市场状态 {market_regime}，策略环境扣分 {penalty}"
                if available
                else f"策略暂不可运行：{unavailable_reason}"
            ),
            evidence=[f"market_regime={market_regime}", f"context_penalty={penalty}"],
            available=available,
        ),
        OpportunityDimension(
            key="selection_pressure",
            label="筛选压力",
            signal=_signal(selection_score, available),
            score=round(selection_score, 1) if available else None,
            summary=(
                f"线索率 {selection_rate:.1f}%，{'短名单足够收敛' if selection_rate <= 8 else '线索偏多，需要二次确认'}"
                if available
                else "当前没有可排序线索，先修复策略所需数据"
            ),
            evidence=[f"ranked={ranked}", f"universe={universe}"],
            available=available,
        ),
        OpportunityDimension(
            key="data_quality",
            label="数据完整度",
            signal=_signal(data_score),
            score=round(data_score, 1),
            summary=f"资金覆盖 {flow_coverage:.0%}，行业覆盖 {sector_coverage:.0%}，成交额覆盖 {amount_coverage:.0%}",
            evidence=["资金流", "行业映射", "成交额"],
        ),
        OpportunityDimension(
            key="risk_control",
            label="风险控制",
            signal=_signal(risk_score),
            score=round(risk_score, 1),
            summary=(
                "防守或谨慎市况下，线索必须先看失效条件和流动性"
                if market_regime in {"risk_off", "cautious"}
                else "市场环境允许线索扩散，但仍需排除追高和低流动性"
            ),
            evidence=["硬排除 ST/退市/低流动性", "市场环境扣分直接体现在最终分"],
        ),
    ]


def _strategy_next_actions(
    preset: str,
    diagnostics: list[OpportunityDimension],
    market_regime: str,
    available: bool,
) -> list[str]:
    if not available:
        return [
            "先切换到可运行的趋势延续策略，避免使用伪线索",
            "补齐策略依赖的数据后再回到当前策略复核",
        ]
    actions = ["先核对前 10 名的资金、行业和流动性证据"]
    data_quality = next((item for item in diagnostics if item.key == "data_quality"), None)
    if data_quality and data_quality.score is not None and data_quality.score < 70:
        actions.append("数据完整度不足的线索只保留候选，不直接通过为参与判断")
    if market_regime in {"risk_off", "cautious"}:
        actions.append("市场偏弱时优先保留有资金确认和成交额支撑的线索")
    if preset == "oversold_repair":
        actions.append("超跌修复线索必须等待止跌确认，不能只因便宜而参与")
    elif preset == "value_rebound":
        actions.append("低估反弹线索必须复核基本面和估值陷阱，不因低 PE 直接通过复核")
    elif preset == "volume_breakout":
        actions.append("放量突破线索必须复核是否有真实催化，避免单日放量骗线")
    elif preset == "capital_confirmed":
        actions.append("资金确认线索必须复核净流入是否连续，单日流入不直接通过")
    elif preset == "sector_momentum":
        actions.append("板块共振线索必须回到大盘页确认板块资金和扩散")
    elif preset == "pullback_support":
        actions.append("回踩企稳线索必须等止跌和重新放量，不接下跌惯性")
    elif preset == "quality_value":
        actions.append("估值质量线索必须排除价值陷阱，先看业绩和现金流证据")
    elif preset == "large_cap_stability":
        actions.append("蓝筹稳健线索重在低波和流动性，不按短线涨幅追高")
    else:
        actions.append("风险收益不足的线索不追高，等待回踩后的新证据")
    return actions[:4]


def _component_score(components: list[ScoreComponent], key: str) -> float | None:
    item = next((component for component in components if component.key == key), None)
    return item.score if item else None


def _risk_reward_score(
    quote: EquityQuote, history_check: OpportunityHistoryCheck | None
) -> tuple[float, list[str], list[str]]:
    score = 58.0
    drivers: list[str] = []
    risks: list[str] = []

    if quote.change_pct is not None:
        if 1 <= quote.change_pct <= 5.5:
            score += 10
            drivers.append(f"当日涨幅 {quote.change_pct:.1f}% 未明显过热")
        elif quote.change_pct > 6.5:
            score -= min(16.0, (quote.change_pct - 6.5) * 4)
            risks.append("当日涨幅偏高，追高性价比下降")
        elif quote.change_pct < 0:
            score -= 8
            risks.append("价格仍在下跌，先等止跌确认")

    if history_check and history_check.available:
        if history_check.ma20_gap_pct is not None:
            if -3 <= history_check.ma20_gap_pct <= 8:
                score += 12
                drivers.append(f"距 MA20 {history_check.ma20_gap_pct:+.1f}%，买点不拥挤")
            elif history_check.ma20_gap_pct > 12:
                score -= min(20.0, (history_check.ma20_gap_pct - 12) * 1.6)
                risks.append(f"距 MA20 {history_check.ma20_gap_pct:+.1f}%，容易回踩")
            elif history_check.ma20_gap_pct < -5:
                score -= 8
                risks.append("跌破均线区间，趋势需要修复")
        if history_check.max_drawdown_60d is not None:
            if history_check.max_drawdown_60d <= 12:
                score += 8
                drivers.append(f"60日回撤 {history_check.max_drawdown_60d:.1f}%，结构较稳")
            elif history_check.max_drawdown_60d > 22:
                score -= 10
                risks.append("60日回撤偏深，反弹持续性要复核")
        if history_check.volatility_20d is not None:
            if history_check.volatility_20d <= 35:
                score += 5
            elif history_check.volatility_20d > 50:
                score -= 8
                risks.append("20日波动偏高，胜率会被拉低")
    else:
        score -= 6
        risks.append("历史K线不足，上涨持续性不能确认")

    return _clamp_score(score), drivers, risks


def _valuation_room_score(quote: EquityQuote) -> tuple[float, str]:
    if quote.pe is None and quote.pb is None:
        return 50.0, "估值数据缺失，上涨空间只能先按量价线索判断"

    score = 58.0
    parts: list[str] = []
    if quote.pe is not None:
        if 0 < quote.pe <= 25:
            score += 16
            parts.append(f"PE {quote.pe:.1f} 仍有估值余地")
        elif quote.pe <= 45:
            score += 4
            parts.append(f"PE {quote.pe:.1f} 中性")
        elif quote.pe <= 70:
            score -= 8
            parts.append(f"PE {quote.pe:.1f} 偏高")
        else:
            score -= 18
            parts.append(f"PE {quote.pe:.1f} 过高")
    if quote.pb is not None:
        if quote.pb <= 3:
            score += 8
            parts.append(f"PB {quote.pb:.1f} 不拥挤")
        elif quote.pb > 6:
            score -= 10
            parts.append(f"PB {quote.pb:.1f} 偏贵")
        else:
            parts.append(f"PB {quote.pb:.1f} 中性")
    return _clamp_score(score), "，".join(parts)


def _weighted_available_score(inputs: list[tuple[float | None, float]]) -> float:
    available = [(score, weight) for score, weight in inputs if score is not None]
    available_weight = sum(weight for _, weight in available)
    if not available_weight:
        return 50.0
    return _clamp_score(sum(score * weight for score, weight in available) / available_weight)


def _strategy_fit_score(
    quote: EquityQuote,
    preset: str,
    history_check: OpportunityHistoryCheck | None,
    sector_strength: dict[str, float] | None,
) -> tuple[float, str]:
    change = quote.change_pct
    history_score = (
        history_check.score if history_check is not None and history_check.available else None
    )
    capital_intensity = (
        quote.net_flow / quote.amount
        if quote.net_flow is not None and quote.amount is not None and quote.amount > 0
        else None
    )
    sector_change = (
        sector_strength.get(quote.sector)
        if sector_strength is not None and quote.sector is not None
        else None
    )

    if preset == "trend":
        score = _weighted_available_score(
            [
                (_score(change, 0.5, 5.5) if change is not None else None, 0.45),
                (history_score, 0.55),
            ]
        )
        return score, f"趋势专属分 {score:.0f}/100，侧重价格延续和历史确认"
    if preset == "volume_breakout":
        score = _weighted_available_score(
            [
                (_score(change, 1, 7) if change is not None else None, 0.20),
                (
                    _score(quote.volume_ratio, 1.3, 3.5)
                    if quote.volume_ratio is not None
                    else None,
                    0.35,
                ),
                (
                    _score(quote.turnover_rate, 3, 8) if quote.turnover_rate is not None else None,
                    0.20,
                ),
                (
                    _score(quote.amount, 500_000_000, 2_000_000_000)
                    if quote.amount is not None
                    else None,
                    0.25,
                ),
            ]
        )
        return score, f"突破专属分 {score:.0f}/100，侧重放量、换手和成交承接"
    if preset == "capital_confirmed":
        score = _weighted_available_score(
            [
                (
                    _score(capital_intensity, 0.03, 0.25)
                    if capital_intensity is not None
                    else None,
                    0.70,
                ),
                (
                    _score(quote.net_flow, 20_000_000, 150_000_000)
                    if quote.net_flow is not None
                    else None,
                    0.30,
                ),
            ]
        )
        intensity_text = (
            f"净流入占成交额 {capital_intensity:.1%}"
            if capital_intensity is not None
            else "资金强度待补"
        )
        return score, f"资金专属分 {score:.0f}/100，{intensity_text}"
    if preset == "sector_momentum":
        score = _weighted_available_score(
            [
                (
                    _score(sector_change, -2, 5) if sector_change is not None else None,
                    0.75,
                ),
                (_score(change, 0, 5) if change is not None else None, 0.25),
            ]
        )
        sector_text = (
            f"{quote.sector} 板块涨跌 {sector_change:+.1f}%"
            if sector_change is not None
            else "板块强度待补，仅按个股跟随度"
        )
        return score, f"板块专属分 {score:.0f}/100，{sector_text}"
    if preset == "pullback_support":
        pullback_score = _clamp_score(100 - abs(change + 0.8) * 35) if change is not None else None
        score = _weighted_available_score(
            [
                (pullback_score, 0.50),
                (
                    _score(capital_intensity, 0, 0.12) if capital_intensity is not None else None,
                    0.30,
                ),
                (history_score, 0.20),
            ]
        )
        return score, f"回踩专属分 {score:.0f}/100，侧重回踩幅度、承接和趋势结构"
    if preset in {"value_rebound", "quality_value"}:
        pe_score = (
            _clamp_score(100 - max(0.0, quote.pe - 8) * 3.5)
            if quote.pe is not None and quote.pe > 0
            else None
        )
        pb_score = (
            _clamp_score(100 - max(0.0, quote.pb - 1) * 16)
            if quote.pb is not None and quote.pb > 0
            else None
        )
        score = _weighted_available_score([(pe_score, 0.60), (pb_score, 0.40)])
        return score, f"估值专属分 {score:.0f}/100，侧重 PE/PB 安全边际"
    if preset == "oversold_repair":
        repair_score = _clamp_score(100 - abs(change + 3.5) * 22) if change is not None else None
        score = _weighted_available_score(
            [
                (repair_score, 0.60),
                (history_score, 0.20),
                (
                    _score(capital_intensity, -0.05, 0.08)
                    if capital_intensity is not None
                    else None,
                    0.20,
                ),
            ]
        )
        return score, f"修复专属分 {score:.0f}/100，侧重超跌幅度和止跌承接"
    if preset == "large_cap_stability":
        stability = _clamp_score(100 - abs(change) * 20) if change is not None else None
        score = _weighted_available_score(
            [
                (
                    _score(quote.market_cap, 50_000_000_000, 500_000_000_000)
                    if quote.market_cap is not None
                    else None,
                    0.45,
                ),
                (
                    _score(quote.amount, 500_000_000, 3_000_000_000)
                    if quote.amount is not None
                    else None,
                    0.30,
                ),
                (stability, 0.25),
            ]
        )
        return score, f"稳健专属分 {score:.0f}/100，侧重大市值、流动性和低波动"
    return 50.0, "策略专属证据待补"


def _candidate_upside(
    quote: EquityQuote,
    preset: str,
    components: list[ScoreComponent],
    context_penalty: float,
    history_check: OpportunityHistoryCheck | None,
    sector_strength: dict[str, float] | None = None,
) -> tuple[float, str, str, list[str], list[str]]:
    trend_score = _component_score(components, "trend")
    capital_score = _component_score(components, "capital")
    liquidity_score = _component_score(components, "liquidity")
    valuation_component = _component_score(components, "valuation")
    history_score = history_check.score if history_check and history_check.available else None
    persistence_score = history_score if history_score is not None else trend_score
    risk_reward, risk_reward_drivers, risk_reward_risks = _risk_reward_score(quote, history_check)
    valuation_room, valuation_summary = _valuation_room_score(quote)
    strategy_fit, strategy_driver = _strategy_fit_score(
        quote, preset, history_check, sector_strength
    )
    valuation_score = valuation_component if valuation_component is not None else valuation_room
    profiles: dict[str, list[tuple[float | None, float]]] = {
        "trend": [
            (strategy_fit, 0.46),
            (persistence_score, 0.25),
            (capital_score, 0.10),
            (risk_reward, 0.12),
            (liquidity_score, 0.07),
        ],
        "volume_breakout": [
            (strategy_fit, 0.50),
            (persistence_score, 0.12),
            (capital_score, 0.10),
            (risk_reward, 0.12),
            (liquidity_score, 0.16),
        ],
        "capital_confirmed": [
            (strategy_fit, 0.52),
            (capital_score, 0.18),
            (persistence_score, 0.08),
            (risk_reward, 0.12),
            (liquidity_score, 0.10),
        ],
        "sector_momentum": [
            (strategy_fit, 0.52),
            (persistence_score, 0.13),
            (capital_score, 0.10),
            (risk_reward, 0.13),
            (liquidity_score, 0.12),
        ],
        "pullback_support": [
            (strategy_fit, 0.48),
            (risk_reward, 0.22),
            (capital_score, 0.12),
            (valuation_score, 0.12),
            (persistence_score, 0.06),
        ],
        "value_rebound": [
            (strategy_fit, 0.48),
            (valuation_score, 0.22),
            (risk_reward, 0.15),
            (capital_score, 0.08),
            (liquidity_score, 0.07),
        ],
        "oversold_repair": [
            (strategy_fit, 0.48),
            (risk_reward, 0.22),
            (valuation_score, 0.12),
            (capital_score, 0.10),
            (liquidity_score, 0.08),
        ],
        "quality_value": [
            (strategy_fit, 0.50),
            (valuation_score, 0.25),
            (risk_reward, 0.15),
            (liquidity_score, 0.10),
        ],
        "large_cap_stability": [
            (strategy_fit, 0.50),
            (liquidity_score, 0.18),
            (risk_reward, 0.16),
            (valuation_score, 0.10),
            (persistence_score, 0.06),
        ],
    }
    score_inputs = profiles[preset]
    available = [(score, weight) for score, weight in score_inputs if score is not None]
    available_weight = sum(weight for _, weight in available) or 1.0
    raw_score = sum(score * weight for score, weight in available) / available_weight
    score = round(_clamp_score(raw_score - context_penalty), 2)

    if score >= 82:
        label = "高概率延续"
    elif score >= 72:
        label = "优先复核"
    elif score >= 62:
        label = "有弹性待确认"
    elif score >= 52:
        label = "反弹观察"
    else:
        label = "上涨证据偏弱"

    drivers: list[str] = [strategy_driver]
    if persistence_score is not None and persistence_score >= 65:
        if history_score is not None:
            drivers.append(f"趋势持续性 {persistence_score:.0f}/100，未来上涨线索更强")
        else:
            drivers.append(f"当前价格动量 {persistence_score:.0f}/100，需补历史确认")
    drivers.extend(risk_reward_drivers)
    if quote.net_flow is not None and quote.net_flow > 0:
        drivers.append(f"主动资金净流入 {_signed_money(quote.net_flow)}")
    if quote.amount is not None and quote.amount >= 500_000_000:
        drivers.append(f"成交额 {_money(quote.amount)}，承接较好")
    if valuation_room >= 66:
        drivers.append(valuation_summary)

    risks: list[str] = []
    if context_penalty > 0:
        risks.append(f"市场环境扣 {context_penalty:.0f} 分")
    if quote.net_flow is not None and quote.net_flow < 0:
        risks.append(f"资金净流出 {_signed_money(quote.net_flow)}")
    if capital_score is None:
        risks.append("资金数据缺失")
    risks.extend(risk_reward_risks)
    if history_check and history_check.risk_flags:
        risks.extend(history_check.risk_flags)
    if valuation_room < 45:
        risks.append(valuation_summary)
    risks.append("催化仍需公告、业绩或研报确认")

    drivers = list(dict.fromkeys(drivers))[:4]
    risks = list(dict.fromkeys(risks))[:4]
    driver_text = "；".join(drivers) if drivers else "候选线索主要来自策略触发，仍需补确认"
    risk_text = "；".join(risks[:2]) if risks else "暂无突出硬伤"
    summary = f"{label}：复核分 {score:.0f}/100，{driver_text}。风险：{risk_text}。"
    return score, label, summary, drivers, risks


def _candidate_dimensions(
    quote: EquityQuote,
    preset: str,
    components: list[ScoreComponent],
    context_penalty: float,
    history_check: OpportunityHistoryCheck | None = None,
    validation: StrategyValidation | None = None,
    sector_strength: dict[str, float] | None = None,
) -> list[OpportunityDimension]:
    trend_score = _component_score(components, "trend")
    capital_score = _component_score(components, "capital")
    liquidity_score = _component_score(components, "liquidity")
    valuation_score = _component_score(components, "valuation")
    persistence_score = (
        history_check.score
        if history_check is not None and history_check.available and history_check.score is not None
        else trend_score
    )
    risk_reward_score, _, _ = _risk_reward_score(quote, history_check)
    valuation_room_score, valuation_room_summary = _valuation_room_score(quote)
    strategy_fit, strategy_fit_summary = _strategy_fit_score(
        quote, preset, history_check, sector_strength
    )
    upside_score, upside_label, upside_summary, upside_drivers, upside_risks = _candidate_upside(
        quote, preset, components, context_penalty, history_check, sector_strength
    )
    trigger_summary = {
        "trend": f"涨幅 {quote.change_pct:.2f}% 处在温和趋势区间"
        if quote.change_pct is not None
        else "涨跌幅暂缺",
        "volume_breakout": f"涨幅 {quote.change_pct:.2f}%，成交额 {_money(quote.amount)}，量能具备突破观察价值"
        if quote.change_pct is not None
        else "涨跌幅暂缺",
        "value_rebound": f"PE {quote.pe:.1f} 处在低估观察区，价格未明显追高"
        if quote.pe is not None
        else "估值暂缺",
        "oversold_repair": f"跌幅 {quote.change_pct:.2f}%，先按超跌修复处理"
        if quote.change_pct is not None
        else "涨跌幅暂缺",
        "capital_confirmed": f"资金净流入 {_signed_money(quote.net_flow)}，价格未明显过热",
        "sector_momentum": f"{quote.sector or '板块待补'} 板块内个股放量跟随，涨幅 {quote.change_pct:.2f}%"
        if quote.change_pct is not None
        else "涨跌幅暂缺",
        "pullback_support": f"回踩 {quote.change_pct:.2f}%，资金没有明显撤退"
        if quote.change_pct is not None
        else "涨跌幅暂缺",
        "quality_value": f"PE {quote.pe:.1f}、PB {quote.pb:.1f} 通过估值质量门槛"
        if quote.pe is not None and quote.pb is not None
        else "估值暂缺",
        "large_cap_stability": f"市值 {_money(quote.market_cap)}，成交额 {_money(quote.amount)}，用于稳健观察",
    }.get(preset, "触发条件待确认")
    confirmation_bits = []
    if quote.amount is not None:
        confirmation_bits.append(f"成交额 {_money(quote.amount)}")
    if quote.net_flow is not None:
        confirmation_bits.append(f"资金 {_signed_money(quote.net_flow)}")
    if quote.sector:
        confirmation_bits.append(f"行业 {quote.sector}")
    capital_summary = (
        f"资金净流入 {_signed_money(quote.net_flow)}，可作为线索确认"
        if quote.net_flow is not None and quote.net_flow > 0
        else f"资金净流出 {_signed_money(quote.net_flow)}，只适合观察不通过"
        if quote.net_flow is not None
        else "资金流暂缺，不能确认主动资金态度"
    )
    sector_summary = (
        f"{quote.sector} 方向需要回到大盘页看板块温度和持续性"
        if quote.sector
        else "行业映射暂缺，无法判断板块共振"
    )
    liquidity_summary = (
        f"成交额 {_money(quote.amount)}，换手率 {quote.turnover_rate:.2f}%，量比 {quote.volume_ratio:.2f}"
        if quote.amount is not None
        and quote.turnover_rate is not None
        and quote.volume_ratio is not None
        else f"成交额 {_money(quote.amount)}，换手率或量比仍需补齐"
    )
    liquidity_score = liquidity_score if liquidity_score is not None else 45.0
    valuation_summary = (
        f"PE {quote.pe:.1f}、PB {quote.pb:.1f}，先做同行相对估值复核"
        if quote.pe is not None and quote.pb is not None
        else "PE/PB 不完整，不能只凭涨跌幅排序"
    )
    catalyst_summary = "公告、业绩预告、研报催化待核验；没有催化的线索只做候选复核"
    follow_up_summary = "系统继续检查个股条件、放弃条件和下次复盘触发点"
    dimensions = [
        OpportunityDimension(
            key="strategy_validation",
            label="策略校验",
            signal="positive" if validation is None or validation.passed else "negative",
            score=100.0 if validation is None or validation.passed else 0.0,
            summary=(
                f"通过 {len(validation.checks)} 项硬条件：{'；'.join(validation.checks[:4])}"
                if validation is not None and validation.passed
                else "策略硬条件未通过，本应被剔除"
            ),
            evidence=validation.checks
            if validation is not None
            else STRATEGY_RULES.get(preset, []),
            available=True,
        ),
        OpportunityDimension(
            key="strategy_fit",
            label="策略匹配",
            signal=_signal(strategy_fit),
            score=round(strategy_fit, 2),
            summary=strategy_fit_summary,
            evidence=[strategy_fit_summary],
            available=True,
        ),
        OpportunityDimension(
            key="future_probability",
            label="上涨概率",
            signal=_signal(upside_score),
            score=upside_score,
            summary=upside_summary,
            evidence=upside_drivers or ["策略触发后仍需补趋势、资金和催化确认"],
        ),
        OpportunityDimension(
            key="trend_persistence",
            label="趋势持续",
            signal=_signal(persistence_score, persistence_score is not None),
            score=persistence_score,
            summary=(
                f"历史趋势给出 {persistence_score:.0f}/100，越高越接近可延续上涨"
                if history_check is not None
                and history_check.available
                and persistence_score is not None
                else f"当前价格动量 {persistence_score:.0f}/100，仍需历史K线确认持续性"
                if persistence_score is not None
                else "缺少趋势确认，不能判断上涨持续性"
            ),
            evidence=(
                history_check.evidence
                if history_check is not None and history_check.evidence
                else [trigger_summary]
            ),
            available=persistence_score is not None,
        ),
        OpportunityDimension(
            key="upside_space",
            label="上涨空间",
            signal=_signal(valuation_room_score),
            score=valuation_room_score,
            summary=valuation_room_summary,
            evidence=[
                f"PE {quote.pe:.1f}" if quote.pe is not None else "PE 暂缺",
                f"PB {quote.pb:.1f}" if quote.pb is not None else "PB 暂缺",
            ],
        ),
        OpportunityDimension(
            key="timing_quality",
            label="买点质量",
            signal=_signal(risk_reward_score),
            score=risk_reward_score,
            summary=(
                "位置、波动和回撤共同评估是否还有风险收益"
                if not upside_risks
                else "；".join(upside_risks[:2])
            ),
            evidence=["当日涨跌幅", "MA20 偏离", "20日波动", "60日回撤"],
        ),
        OpportunityDimension(
            key="trigger",
            label="触发逻辑",
            signal=_signal(trend_score),
            score=trend_score,
            summary=trigger_summary,
            evidence=[trigger_summary],
        ),
        OpportunityDimension(
            key="confirmation",
            label="确认强度",
            signal=_signal(capital_score if capital_score is not None else liquidity_score),
            score=capital_score if capital_score is not None else liquidity_score,
            summary="，".join(confirmation_bits) if confirmation_bits else "确认数据不足",
            evidence=confirmation_bits or ["资金、行业或成交额仍需补齐"],
        ),
        OpportunityDimension(
            key="risk_control",
            label="风险控制",
            signal=_signal(55 - context_penalty),
            score=max(0.0, 55 - context_penalty),
            summary=f"最终分已扣除市场环境 {context_penalty:.0f} 分，避免弱市高分误判",
            evidence=[f"context_penalty={context_penalty:.0f}", "系统继续复查个股判断"],
        ),
        OpportunityDimension(
            key="execution",
            label="执行质量",
            signal=_signal(valuation_score if valuation_score is not None else liquidity_score),
            score=valuation_score if valuation_score is not None else liquidity_score,
            summary=(
                f"PE {quote.pe:.1f}，流动性 {_money(quote.amount)}，适合先做复核优先级排序"
                if quote.pe is not None
                else f"估值暂缺，先按流动性 {_money(quote.amount)} 控制观察仓位"
            ),
            evidence=["估值约束", "流动性约束", "不是买卖指令"],
        ),
        OpportunityDimension(
            key="capital_flow",
            label="资金态度",
            signal=_signal(capital_score, quote.net_flow is not None),
            score=capital_score,
            summary=capital_summary,
            evidence=[capital_summary],
            available=quote.net_flow is not None,
        ),
        OpportunityDimension(
            key="sector_context",
            label="板块位置",
            signal=_signal(58.0, quote.sector is not None),
            score=58.0 if quote.sector is not None else None,
            summary=sector_summary,
            evidence=[sector_summary],
            available=quote.sector is not None,
        ),
        OpportunityDimension(
            key="liquidity_depth",
            label="流动性承载",
            signal=_signal(liquidity_score, quote.amount is not None),
            score=liquidity_score if quote.amount is not None else None,
            summary=liquidity_summary,
            evidence=[
                f"成交额 {_money(quote.amount)}",
                f"换手率 {quote.turnover_rate:.2f}%"
                if quote.turnover_rate is not None
                else "换手率暂缺",
                f"量比 {quote.volume_ratio:.2f}" if quote.volume_ratio is not None else "量比暂缺",
            ],
            available=quote.amount is not None,
        ),
        OpportunityDimension(
            key="valuation_fit",
            label="估值匹配",
            signal=_signal(valuation_score, valuation_score is not None),
            score=valuation_score,
            summary=valuation_summary,
            evidence=[
                f"PE {quote.pe:.1f}" if quote.pe is not None else "PE 暂缺",
                f"PB {quote.pb:.1f}" if quote.pb is not None else "PB 暂缺",
            ],
            available=valuation_score is not None,
        ),
        OpportunityDimension(
            key="catalyst_check",
            label="催化核验",
            signal="missing",
            score=None,
            summary=catalyst_summary,
            evidence=["公告待核验", "研报待核验", "业绩/政策催化待核验"],
            available=False,
        ),
        OpportunityDimension(
            key="follow_up_plan",
            label="后续动作",
            signal="neutral",
            score=55.0,
            summary=follow_up_summary,
            evidence=["个股判断", "检查条件", "失效条件", "复盘触发点"],
        ),
    ]
    if history_check is not None:
        dimensions.insert(
            2,
            OpportunityDimension(
                key="history_confirmation",
                label="历史确认",
                signal=_signal(history_check.score, history_check.available),
                score=history_check.score,
                summary=history_check.summary,
                evidence=history_check.evidence,
                available=history_check.available,
            ),
        )
    return dimensions


def _candidate_thesis(quote: EquityQuote, preset: str) -> str:
    label = STRATEGY_LABELS.get(preset, preset)
    pieces: list[str] = []
    if quote.change_pct is not None:
        pieces.append(f"价格变化 {quote.change_pct:.2f}%")
    if quote.amount is not None:
        pieces.append(f"成交额 {_money(quote.amount)}")
    if quote.net_flow is not None:
        pieces.append(f"资金 {_signed_money(quote.net_flow)}")
    evidence = "，".join(pieces) if pieces else "核心行情证据待补齐"
    return f"{label}线索：{evidence}；系统会继续复查完整个股判断。"


def _candidate_invalidation(quote: EquityQuote, preset: str) -> list[str]:
    rules = ["系统判断转为回避或信息不足"]
    if preset == "trend":
        rules.extend(["跌回策略涨幅区间外", "成交额低于 3 亿元"])
    elif preset == "volume_breakout":
        rules.extend(["成交额低于 5 亿元", "量比或换手率回落到策略门槛以下"])
    elif preset == "value_rebound":
        rules.extend(["PE/PB 优势消失", "低估原因被公告或业绩证伪"])
    elif preset == "oversold_repair":
        rules.extend(["继续放量下跌未见止跌", "PE 数据失真或转负"])
    elif preset == "capital_confirmed":
        rules.extend(["资金净流入低于 2000 万", "价格涨幅超过策略上限"])
    elif preset == "sector_momentum":
        rules.extend(["板块归属或板块资金无法确认", "量能/换手跌回策略门槛以下"])
    elif preset == "pullback_support":
        rules.extend(["资金重新净流出", "回踩跌幅扩大且未止跌"])
    elif preset == "quality_value":
        rules.extend(["PE/PB 不再满足质量门槛", "业绩或公告证伪估值优势"])
    elif preset == "large_cap_stability":
        rules.extend(["市值或成交额跌出稳健门槛", "换手异常过热"])
    if quote.amount is not None and quote.amount < 300_000_000:
        rules.append("流动性不足以支撑继续跟踪")
    return rules[:4]


def _candidate_next_actions(quote: EquityQuote, context_penalty: float) -> list[str]:
    actions = ["系统持续复查个股趋势、资金、收益空间和风险"]
    if context_penalty > 0:
        actions.insert(0, "系统持续检查市场环境，环境偏弱时自动降级")
    if quote.sector:
        actions.append(f"系统持续比较 {quote.sector} 板块温度和个股表现")
    if quote.net_flow is None:
        actions.append("资金流数据补齐后自动重算资金判断")
    else:
        actions.append("系统持续检查资金流是否连续，而不是只看单日净流入")
    actions.append("系统持续扫描公告、业绩预告和研报摘要")
    actions.append("系统持续比较同行估值和市值风格，避免只按涨幅排序")
    actions.append("系统按参与条件和放弃条件检查，不满足时自动降级")
    return actions[:6]
