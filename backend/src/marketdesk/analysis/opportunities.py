from marketdesk.models import (
    EquityQuote,
    ExcludedCandidate,
    OpportunityResult,
    RankedCandidate,
    ScoreComponent,
)


def _score(value: float | None, low: float, high: float) -> float:
    if value is None:
        return 50.0
    if high == low:
        return 50.0
    return max(0.0, min(100.0, (value - low) / (high - low) * 100))


def rank_candidates(
    equities: list[EquityQuote], market_regime: str, preset: str = "trend"
) -> OpportunityResult:
    strategy_rules = {
        "trend": ["涨幅 0.5% 至 7%", "成交额至少 3 亿元", "排除涨停追高"],
        "sector_improving": ["具备个股行业映射", "行业方向为正", "个股价格同步走强"],
        "capital_confirmed": ["主力资金净流入", "价格方向非负", "成交额至少 1 亿元"],
        "oversold_rebound": ["当日跌幅 -7% 至 -1%", "PE 介于 0 至 50", "仅作日内超跌观察"],
    }
    if preset not in strategy_rules:
        raise ValueError("unknown preset")
    if preset == "capital_confirmed" and not any(
        quote.net_flow is not None for quote in equities
    ):
        return OpportunityResult(
            preset=preset,
            available=False,
            unavailable_reason="当前股票池没有资金流数据，不能运行资金确认策略。",
            rules=strategy_rules[preset],
            funnel={"universe": len(equities), "excluded": 0, "ranked": 0},
            candidates=[],
            excluded=[],
        )
    if preset == "sector_improving":
        return OpportunityResult(
            preset=preset,
            available=False,
            unavailable_reason="当前股票池没有可验证的个股行业映射与板块强度关联，不能运行板块改善策略。",
            rules=strategy_rules[preset],
            funnel={"universe": len(equities), "excluded": 0, "ranked": 0},
            candidates=[],
            excluded=[],
        )

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
        if not reasons and not _matches_preset(quote, preset):
            reasons.append("strategy_mismatch")
        if reasons:
            excluded.append(ExcludedCandidate(quote=quote, reasons=reasons))
            continue
        component_values: list[tuple[str, str, float, float, float]] = []
        risk_flags: list[str] = []
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
        risk_flags.append("板块归属暂缺" if quote.sector is None else "板块强度数据暂缺")
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
        context_penalty = 15.0 if market_regime == "risk_off" else 8.0 if market_regime == "cautious" else 0.0
        total = round(max(0.0, base_score - context_penalty), 2)
        if market_regime in {"risk_off", "cautious"}:
            risk_flags.append("市场偏弱")
        ranked.append(
            RankedCandidate(
                quote=quote,
                base_score=base_score,
                context_penalty=context_penalty,
                score=total,
                evidence_coverage=round(available_weight, 2),
                components=components,
                risk_flags=risk_flags,
            )
        )
    ranked.sort(key=lambda item: item.score, reverse=True)
    return OpportunityResult(
        preset=preset,
        available=True,
        rules=strategy_rules[preset],
        funnel={"universe": len(equities), "excluded": len(excluded), "ranked": len(ranked)},
        candidates=ranked,
        excluded=excluded,
    )


def _matches_preset(quote: EquityQuote, preset: str) -> bool:
    change = quote.change_pct
    if change is None:
        return False
    if preset == "trend":
        return 0.5 <= change <= 7 and (quote.amount or 0) >= 300_000_000
    if preset == "sector_improving":
        return quote.sector is not None and change > 0
    if preset == "capital_confirmed":
        return quote.net_flow is not None and quote.net_flow > 0 and change >= 0
    return (
        -7 <= change <= -1
        and quote.pe is not None
        and 0 < quote.pe < 50
        and (quote.amount or 0) >= 100_000_000
    )
