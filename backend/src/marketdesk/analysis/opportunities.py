from marketdesk.models import (
    EquityQuote,
    ExcludedCandidate,
    OpportunityDimension,
    OpportunityResult,
    RankedCandidate,
    ScoreComponent,
)

STRATEGY_LABELS = {
    "trend": "趋势延续",
    "volume_breakout": "放量突破",
    "value_rebound": "低估反弹",
    "oversold_repair": "超跌修复",
}

PRESET_ALIASES = {
    "sector_improving": "volume_breakout",
    "capital_confirmed": "volume_breakout",
    "oversold_rebound": "oversold_repair",
}


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
    equities: list[EquityQuote], market_regime: str, preset: str = "trend"
) -> OpportunityResult:
    preset = PRESET_ALIASES.get(preset, preset)
    strategy_rules = {
        "trend": ["涨幅 0.5% 至 7%", "成交额至少 3 亿元", "排除涨停追高"],
        "volume_breakout": ["涨幅 1% 至 8%", "成交额至少 5 亿元", "量比高于 1.3 或换手率高于 3%"],
        "value_rebound": ["涨跌幅 -1% 至 2%", "PE 介于 0 至 30", "PB 不高于 5 且成交额至少 1 亿元"],
        "oversold_repair": ["当日跌幅 -7% 至 -1%", "PE 介于 0 至 60", "成交额至少 1 亿元"],
    }
    if preset not in strategy_rules:
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
                dimensions=_candidate_dimensions(quote, preset, components, context_penalty),
                thesis=_candidate_thesis(quote, preset),
                invalidation=_candidate_invalidation(quote, preset),
                next_actions=_candidate_next_actions(quote, context_penalty),
                risk_flags=risk_flags,
            )
        )
    ranked.sort(key=lambda item: item.score, reverse=True)
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
        rules=strategy_rules[preset],
        diagnostics=diagnostics,
        next_actions=_strategy_next_actions(preset, diagnostics, market_regime, available=True),
        funnel=funnel,
        candidates=ranked,
        excluded=excluded,
    )


def _matches_preset(quote: EquityQuote, preset: str) -> bool:
    change = quote.change_pct
    if change is None:
        return False
    if preset == "trend":
        return 0.5 <= change <= 7 and (quote.amount or 0) >= 300_000_000
    if preset == "volume_breakout":
        active_volume = (quote.volume_ratio or 0) >= 1.3 or (quote.turnover_rate or 0) >= 3
        return 1 <= change <= 8 and (quote.amount or 0) >= 500_000_000 and active_volume
    if preset == "value_rebound":
        pb_ok = quote.pb is None or quote.pb <= 5
        return (
            -1 <= change <= 2
            and quote.pe is not None
            and 0 < quote.pe <= 30
            and pb_ok
            and (quote.amount or 0) >= 100_000_000
        )
    return (
        -7 <= change <= -1
        and quote.pe is not None
        and 0 < quote.pe <= 60
        and (quote.amount or 0) >= 100_000_000
    )


def _strategy_summary(preset: str, market_regime: str, funnel: dict[str, int]) -> str:
    label = STRATEGY_LABELS.get(preset, preset)
    ranked = funnel.get("ranked", 0)
    universe = funnel.get("universe", 0)
    rate = ranked / universe * 100 if universe else 0
    regime_text = {
        "risk_off": "防守市况下只适合做证据复核，不适合扩大进攻",
        "cautious": "谨慎市况下需要提高确认标准",
        "balanced": "均衡市况下可按研究优先级推进短名单",
        "risk_on": "积极市况下可放宽观察范围，但仍需控制追高",
    }.get(market_regime, "市场环境待确认")
    return f"{label}策略当前可运行，入选 {ranked}/{universe}（{rate:.1f}%）；{regime_text}。"


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
                f"入选率 {selection_rate:.1f}%，{'短名单足够收敛' if selection_rate <= 8 else '候选偏多，需要二次确认'}"
                if available
                else "当前没有可排序候选，先修复策略所需数据"
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
                "防守或谨慎市况下，候选必须先看失效条件和流动性"
                if market_regime in {"risk_off", "cautious"}
                else "市场环境允许研究扩散，但仍需排除追高和低流动性"
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
            "先切换到可运行的趋势延续策略，避免使用伪候选",
            "补齐策略依赖的数据后再回到当前策略复核",
        ]
    actions = ["先核对前 10 名的资金、行业和流动性证据"]
    data_quality = next((item for item in diagnostics if item.key == "data_quality"), None)
    if data_quality and data_quality.score is not None and data_quality.score < 70:
        actions.append("数据完整度不足的候选只进入跟踪，不直接升级为重点研究")
    if market_regime in {"risk_off", "cautious"}:
        actions.append("市场偏弱时优先保留有资金确认和成交额支撑的候选")
    if preset == "oversold_repair":
        actions.append("超跌修复候选必须等待止跌确认，不能只因便宜而加入")
    elif preset == "value_rebound":
        actions.append("低估反弹候选必须复核基本面和估值陷阱，不因低 PE 直接升级")
    elif preset == "volume_breakout":
        actions.append("放量突破候选必须复核是否有真实催化，避免单日放量骗线")
    else:
        actions.append("风险收益不足的候选不追高，等待回踩后的新证据")
    return actions[:4]


def _component_score(components: list[ScoreComponent], key: str) -> float | None:
    item = next((component for component in components if component.key == key), None)
    return item.score if item else None


def _candidate_dimensions(
    quote: EquityQuote, preset: str, components: list[ScoreComponent], context_penalty: float
) -> list[OpportunityDimension]:
    trend_score = _component_score(components, "trend")
    capital_score = _component_score(components, "capital")
    liquidity_score = _component_score(components, "liquidity")
    valuation_score = _component_score(components, "valuation")
    trigger_summary = {
        "trend": f"涨幅 {quote.change_pct:.2f}% 处在温和趋势区间" if quote.change_pct is not None else "涨跌幅暂缺",
        "volume_breakout": f"涨幅 {quote.change_pct:.2f}%，成交额 {_money(quote.amount)}，量能具备突破观察价值" if quote.change_pct is not None else "涨跌幅暂缺",
        "value_rebound": f"PE {quote.pe:.1f} 处在低估观察区，价格未明显追高" if quote.pe is not None else "估值暂缺",
        "oversold_repair": f"跌幅 {quote.change_pct:.2f}%，先按超跌修复处理" if quote.change_pct is not None else "涨跌幅暂缺",
    }.get(preset, "触发条件待确认")
    confirmation_bits = []
    if quote.amount is not None:
        confirmation_bits.append(f"成交额 {_money(quote.amount)}")
    if quote.net_flow is not None:
        confirmation_bits.append(f"资金 {_signed_money(quote.net_flow)}")
    if quote.sector:
        confirmation_bits.append(f"行业 {quote.sector}")
    capital_summary = (
        f"资金净流入 {_signed_money(quote.net_flow)}，可作为入选确认"
        if quote.net_flow is not None and quote.net_flow > 0
        else f"资金净流出 {_signed_money(quote.net_flow)}，只适合观察不升级"
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
        if quote.amount is not None and quote.turnover_rate is not None and quote.volume_ratio is not None
        else f"成交额 {_money(quote.amount)}，换手率或量比仍需补齐"
    )
    liquidity_score = liquidity_score if liquidity_score is not None else 45.0
    valuation_summary = (
        f"PE {quote.pe:.1f}、PB {quote.pb:.1f}，先做同行相对估值复核"
        if quote.pe is not None and quote.pb is not None
        else "PE/PB 不完整，不能只凭涨跌幅排序"
    )
    catalyst_summary = "公告、业绩预告、研报催化待核验；没有催化的候选只进入观察池"
    follow_up_summary = "先打开个股证据账本，再写关注理由、失效条件和下次复盘触发点"
    return [
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
            evidence=[f"context_penalty={context_penalty:.0f}", "仍需打开个股证据账本复核"],
        ),
        OpportunityDimension(
            key="execution",
            label="执行质量",
            signal=_signal(valuation_score if valuation_score is not None else liquidity_score),
            score=valuation_score if valuation_score is not None else liquidity_score,
            summary=(
                f"PE {quote.pe:.1f}，流动性 {_money(quote.amount)}，适合先做研究优先级排序"
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
                f"换手率 {quote.turnover_rate:.2f}%" if quote.turnover_rate is not None else "换手率暂缺",
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
            evidence=["个股证据账本", "关注理由", "失效条件", "复盘触发点"],
        ),
    ]


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
    return f"{label}候选：{evidence}，先进入证据复核。"


def _candidate_invalidation(quote: EquityQuote, preset: str) -> list[str]:
    rules = ["个股证据账本转为回避或证据不足"]
    if preset == "trend":
        rules.extend(["跌回策略涨幅区间外", "成交额低于 3 亿元"])
    elif preset == "volume_breakout":
        rules.extend(["成交额低于 5 亿元", "量比或换手率回落到策略门槛以下"])
    elif preset == "value_rebound":
        rules.extend(["PE/PB 优势消失", "低估原因被公告或业绩证伪"])
    elif preset == "oversold_repair":
        rules.extend(["继续放量下跌未见止跌", "PE 数据失真或转负"])
    if quote.amount is not None and quote.amount < 300_000_000:
        rules.append("流动性不足以支撑继续跟踪")
    return rules[:4]


def _candidate_next_actions(quote: EquityQuote, context_penalty: float) -> list[str]:
    actions = ["打开个股证据账本复核趋势、资金和风险收益"]
    if context_penalty > 0:
        actions.insert(0, "市场环境有扣分，先做复核不急于升级")
    if quote.sector:
        actions.append(f"回到大盘页检查 {quote.sector} 板块温度")
    if quote.net_flow is None:
        actions.append("补齐资金流后再判断是否资金确认")
    else:
        actions.append("复核资金流是否连续，而不是只看单日净流入")
    actions.append("补读公告、业绩预告和研报摘要，确认是否存在真实催化")
    actions.append("比较同行估值和市值风格，避免只按涨幅排序")
    actions.append("加入跟踪前写清关注理由和放弃条件")
    return actions[:6]
