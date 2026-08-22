from marketdesk.analysis.decisions import holding_decision
from marketdesk.models import (
    Bar,
    EquityQuote,
    HoldingAnalysisDimension,
    HoldingDailyChange,
    HoldingDossier,
    HoldingItem,
)


def analyse_holding(
    item: HoldingItem,
    quote: EquityQuote,
    total_market_value: float | None,
    bars: list[Bar] | None = None,
) -> HoldingDossier:
    cost_value = item.quantity * item.cost_price
    market_value = item.quantity * quote.price if quote.price is not None else None
    pnl = market_value - cost_value if market_value is not None else None
    pnl_pct = pnl / cost_value * 100 if pnl is not None and cost_value else None
    portfolio_weight = (
        market_value / total_market_value
        if market_value is not None and total_market_value and total_market_value > 0
        else None
    )
    has_target = False
    drift = portfolio_weight - item.target_weight if has_target and portfolio_weight is not None else None
    target_market_value = (
        total_market_value * item.target_weight
        if has_target and total_market_value is not None and total_market_value > 0
        else None
    )
    rebalance_value = (
        target_market_value - market_value
        if target_market_value is not None and market_value is not None
        else None
    )
    rebalance_quantity = (
        rebalance_value / quote.price
        if rebalance_value is not None and quote.price is not None and quote.price > 0
        else None
    )
    price_gap_to_cost_pct = (
        (quote.price / item.cost_price - 1) * 100
        if quote.price is not None and item.cost_price > 0
        else None
    )
    day_pnl, day_pnl_pct = _period_pnl_from_change(item, quote, quote.change_pct)
    three_day_pnl, three_day_pnl_pct = _multi_day_pnl(item, quote, bars or [], 3)
    five_day_pnl, five_day_pnl_pct = _multi_day_pnl(item, quote, bars or [], 5)
    recent_daily_changes = _recent_daily_changes(bars or [], 10)
    risk_flags = _risk_flags(item, quote, pnl_pct, drift, portfolio_weight, recent_daily_changes)
    action = _action(pnl_pct, portfolio_weight, quote, recent_daily_changes)
    confidence = _holding_confidence(item, quote, total_market_value, bars or [])
    next_actions = _next_actions(action, item, quote)
    rounded_rebalance_quantity = (
        round(rebalance_quantity, 2) if rebalance_quantity is not None else None
    )
    return HoldingDossier(
        item=item,
        quote=quote,
        market_value=round(market_value, 2) if market_value is not None else None,
        cost_value=round(cost_value, 2),
        pnl=round(pnl, 2) if pnl is not None else None,
        pnl_pct=round(pnl_pct, 2) if pnl_pct is not None else None,
        day_pnl=round(day_pnl, 2) if day_pnl is not None else None,
        day_pnl_pct=round(day_pnl_pct, 2) if day_pnl_pct is not None else None,
        three_day_pnl=round(three_day_pnl, 2) if three_day_pnl is not None else None,
        three_day_pnl_pct=round(three_day_pnl_pct, 2) if three_day_pnl_pct is not None else None,
        five_day_pnl=round(five_day_pnl, 2) if five_day_pnl is not None else None,
        five_day_pnl_pct=round(five_day_pnl_pct, 2) if five_day_pnl_pct is not None else None,
        recent_daily_changes=recent_daily_changes,
        portfolio_weight=round(portfolio_weight, 4) if portfolio_weight is not None else None,
        drift=round(drift, 4) if drift is not None else None,
        target_market_value=round(target_market_value, 2)
        if target_market_value is not None
        else None,
        rebalance_value=round(rebalance_value, 2) if rebalance_value is not None else None,
        rebalance_quantity=rounded_rebalance_quantity,
        break_even_price=round(item.cost_price, 2),
        price_gap_to_cost_pct=round(price_gap_to_cost_pct, 2)
        if price_gap_to_cost_pct is not None
        else None,
        analysis_dimensions=_analysis_dimensions(
            item=item,
            quote=quote,
            market_value=market_value,
            cost_value=cost_value,
            pnl=pnl,
            pnl_pct=pnl_pct,
            portfolio_weight=portfolio_weight,
            drift=drift,
            target_market_value=target_market_value,
            rebalance_value=rebalance_value,
            rebalance_quantity=rebalance_quantity,
            price_gap_to_cost_pct=price_gap_to_cost_pct,
        ),
        action=action,
        decision=holding_decision(action, confidence=confidence),
        conclusion=_conclusion(
            item,
            quote,
            pnl_pct,
            drift,
            portfolio_weight,
            recent_daily_changes,
            action,
        ),
        risk_flags=risk_flags,
        next_actions=next_actions,
    )


def _holding_confidence(
    item: HoldingItem,
    quote: EquityQuote,
    total_market_value: float | None,
    bars: list[Bar],
) -> float:
    checks = (
        quote.price is not None,
        quote.change_pct is not None,
        len(bars) >= 6,
        item.quantity > 0 and item.cost_price > 0,
        total_market_value is not None and total_market_value > 0,
    )
    return round(sum(checks) / len(checks), 2)


def _period_pnl_from_change(
    item: HoldingItem, quote: EquityQuote, change_pct: float | None
) -> tuple[float | None, float | None]:
    if quote.price is None or change_pct is None:
        return None, None
    base_price = quote.price / (1 + change_pct / 100) if change_pct != -100 else None
    if base_price is None:
        return None, None
    pnl = (quote.price - base_price) * item.quantity
    return pnl, change_pct


def _multi_day_pnl(
    item: HoldingItem, quote: EquityQuote, bars: list[Bar], days: int
) -> tuple[float | None, float | None]:
    if quote.price is None or len(bars) < days + 1:
        return None, None
    base_price = bars[-(days + 1)].close
    if base_price == 0:
        return None, None
    pnl = (quote.price - base_price) * item.quantity
    pct = (quote.price / base_price - 1) * 100
    return pnl, pct


def _recent_daily_changes(bars: list[Bar], days: int) -> list[HoldingDailyChange]:
    if len(bars) < 2:
        return []
    window = bars[-(days + 1) :]
    changes: list[HoldingDailyChange] = []
    for previous, current in zip(window, window[1:], strict=False):
        change_pct = None
        if previous.close != 0:
            change_pct = round((current.close / previous.close - 1) * 100, 2)
        changes.append(HoldingDailyChange(date=current.date, change_pct=change_pct))
    return changes[-days:]


def _change_values(changes: list[HoldingDailyChange]) -> list[float]:
    return [item.change_pct for item in changes if item.change_pct is not None]


def _change_sum(changes: list[HoldingDailyChange]) -> float | None:
    values = _change_values(changes)
    if not values:
        return None
    return round(sum(values), 2)


def _positive_days(changes: list[HoldingDailyChange]) -> int:
    return sum(1 for value in _change_values(changes) if value > 0)


def _negative_streak(changes: list[HoldingDailyChange]) -> int:
    streak = 0
    for item in reversed(changes):
        if item.change_pct is None or item.change_pct >= 0:
            break
        streak += 1
    return streak


def _worst_day(changes: list[HoldingDailyChange]) -> float | None:
    values = _change_values(changes)
    return min(values) if values else None


def _risk_flags(
    item: HoldingItem,
    quote: EquityQuote,
    pnl_pct: float | None,
    drift: float | None,
    portfolio_weight: float | None,
    recent_daily_changes: list[HoldingDailyChange],
) -> list[str]:
    flags: list[str] = []
    ten_day_change = _change_sum(recent_daily_changes)
    negative_streak = _negative_streak(recent_daily_changes)
    worst_day = _worst_day(recent_daily_changes)
    if pnl_pct is None:
        flags.append("行情价格暂缺")
    elif pnl_pct <= -10:
        flags.append("亏损超过 10%")
    elif pnl_pct >= 20:
        flags.append("盈利较高，注意回撤")
    if portfolio_weight is not None and portfolio_weight >= 0.35:
        flags.append("单票占比偏高")
    if drift is not None:
        if drift > 0.1:
            flags.append("组合占比高于目标")
        elif drift < -0.1:
            flags.append("组合占比低于目标")
    if ten_day_change is not None and ten_day_change <= -8:
        flags.append("近10日连续走弱")
    elif ten_day_change is not None and ten_day_change >= 18:
        flags.append("近10日涨幅过热")
    if negative_streak >= 4:
        flags.append("连续下跌，先做风控")
    if worst_day is not None and worst_day <= -6:
        flags.append("单日波动过大")
    if quote.net_flow is not None and quote.net_flow < 0:
        flags.append("资金净流出")
    if not item.invalidation.strip():
        flags.append("缺少失效条件")
    return flags


def _action(
    pnl_pct: float | None,
    portfolio_weight: float | None,
    quote: EquityQuote,
    recent_daily_changes: list[HoldingDailyChange],
) -> str:
    if pnl_pct is None:
        return "review"
    ten_day_change = _change_sum(recent_daily_changes)
    positive_days = _positive_days(recent_daily_changes)
    negative_streak = _negative_streak(recent_daily_changes)
    worst_day = _worst_day(recent_daily_changes)
    is_heavy = portfolio_weight is not None and portfolio_weight >= 0.35
    net_outflow = quote.net_flow is not None and quote.net_flow < 0
    if (
        pnl_pct <= -10
        or (quote.change_pct is not None and quote.change_pct < -7)
        or (ten_day_change is not None and ten_day_change <= -12)
        or negative_streak >= 4
    ):
        return "exit_watch"
    if (
        (
            pnl_pct >= 20
            and (
                quote.change_pct is not None
                and quote.change_pct < 0
                or ten_day_change is not None
                and ten_day_change < 0
            )
        )
        or (ten_day_change is not None and ten_day_change >= 18)
        or (
            is_heavy
            and (
                pnl_pct >= 12
                or net_outflow
                or ten_day_change is not None
                and ten_day_change < 0
            )
        )
    ):
        return "trim"
    if (
        pnl_pct >= -3
        and ten_day_change is not None
        and 1 <= ten_day_change <= 15
        and positive_days >= 6
        and (worst_day is None or worst_day > -5)
        and (quote.change_pct is None or quote.change_pct > -3)
        and (quote.net_flow is None or quote.net_flow >= 0)
        and (portfolio_weight is None or portfolio_weight < 0.35)
        and (quote.pe is None or quote.pe <= 80)
    ):
        return "add_watch"
    return "hold"


def _next_actions(action: str, item: HoldingItem, quote: EquityQuote) -> list[str]:
    actions = {
        "trim": ["系统持续检查分批减仓条件", "更新保留仓位的退出条件"],
        "exit_watch": ["系统持续检查退出条件", "提醒优先减仓或止损"],
        "add_watch": ["系统持续检查小幅加仓条件", "加仓前设定退出条件"],
        "review": ["补齐行情价格或成本数据", "重读个股证据账本"],
        "hold": ["继续跟踪持仓逻辑", "收盘后复核资金与趋势证据"],
    }[action]
    if quote.sector:
        actions.append(f"同步检查 {quote.sector} 板块温度")
    if quote.net_flow is not None and quote.net_flow < 0:
        actions.append("资金流为净流出，复核是否只是估值修复而缺少主动资金")
    elif quote.net_flow is not None:
        actions.append("资金流为净流入，观察是否连续三日确认")
    actions.append("复核估值和行业位置，避免只按持仓盈亏决定加减仓")
    actions.append("把持仓逻辑、失效条件和下次复盘时间写清楚")
    return actions[:7]


def _conclusion(
    item: HoldingItem,
    quote: EquityQuote,
    pnl_pct: float | None,
    drift: float | None,
    portfolio_weight: float | None,
    recent_daily_changes: list[HoldingDailyChange],
    action: str,
) -> str:
    action_text = _action_text(action)
    reasons = _priority_reasons(
        item,
        quote,
        pnl_pct,
        drift,
        portfolio_weight,
        recent_daily_changes,
        action,
    )
    execution = _execution_text(action)
    return f"建议动作：{action_text}。{'，'.join(reasons)}。{execution}"


def _action_text(action: str) -> str:
    return {
        "hold": "继续持有",
        "trim": "建议分批减仓",
        "add_watch": "仅小幅加仓",
        "review": "暂不操作",
        "exit_watch": "优先减仓或止损",
    }[action]


def _priority_reasons(
    item: HoldingItem,
    quote: EquityQuote,
    pnl_pct: float | None,
    drift: float | None,
    portfolio_weight: float | None,
    recent_daily_changes: list[HoldingDailyChange],
    action: str,
) -> list[str]:
    reasons: list[str] = []
    ten_day_change = _change_sum(recent_daily_changes)
    positive_days = _positive_days(recent_daily_changes)
    negative_streak = _negative_streak(recent_daily_changes)

    if action == "exit_watch":
        if pnl_pct is not None and pnl_pct <= -10:
            reasons.append(f"亏损 {_pct(pnl_pct)} 已触发风控")
        elif quote.change_pct is not None and quote.change_pct < -7:
            reasons.append(f"当日跌幅 {_pct(quote.change_pct)} 偏大")
        elif ten_day_change is not None and ten_day_change <= -12:
            reasons.append(f"近10日跌幅 {_pct(ten_day_change)} 偏大")
        elif negative_streak >= 4:
            reasons.append("近10日连续走弱")
        if drift is not None and drift > 0.1:
            reasons.append(f"仓位高于目标 {_weight(drift)}")
        elif drift is not None and drift < -0.1:
            reasons.append(f"虽低于目标 {_weight(drift)}，但风控优先")
        elif portfolio_weight is not None and portfolio_weight >= 0.35:
            reasons.append(f"单票占比 {_weight(portfolio_weight)} 偏高")
        _append_flow_reason(reasons, quote)
        _append_valuation_reason(reasons, quote)
        if not item.invalidation.strip():
            reasons.append("失效条件不完整")
        return reasons[:3] or ["先核对失效条件"]

    if drift is None:
        reasons.append("不使用目标比例，按盈亏、近10日走势和资金复核")
    elif drift > 0.1:
        reasons.append(f"仓位高于目标 {_weight(drift)}")
    elif drift < -0.1:
        reasons.append(f"仓位低于目标 {_weight(drift)}")
    else:
        reasons.append("仓位接近目标")

    if portfolio_weight is not None and portfolio_weight >= 0.35:
        reasons.append(f"单票占比 {_weight(portfolio_weight)} 偏高")
    if ten_day_change is not None:
        if ten_day_change >= 18:
            reasons.append(f"近10日涨幅 {_pct(ten_day_change)}，注意过热")
        elif ten_day_change > 0:
            reasons.append(f"近10日上涨 {_pct(ten_day_change)}，{positive_days} 天收涨")
        elif ten_day_change < 0:
            reasons.append(f"近10日下跌 {_pct(ten_day_change)}，先看是否转弱")

    if pnl_pct is None:
        reasons.append("成本风控缺少现价证据")
    elif pnl_pct <= -10:
        reasons.append(f"亏损 {_pct(pnl_pct)} 已触发风控")
    elif pnl_pct >= 20:
        reasons.append(f"浮盈 {_pct(pnl_pct)}，注意回撤")
    else:
        reasons.append(f"盈亏 {_pct(pnl_pct)} 未触发止损")

    _append_valuation_reason(reasons, quote)
    _append_flow_reason(reasons, quote)

    if quote.amount is not None and quote.amount < 80_000_000:
        reasons.append("成交额偏低，调仓要分批")
    if not item.thesis.strip() or not item.invalidation.strip():
        reasons.append("持仓逻辑或失效条件不完整")
    return reasons[:4]


def _append_valuation_reason(reasons: list[str], quote: EquityQuote) -> None:
    if quote.pe is None and quote.pb is None:
        return
    if quote.pe is not None and quote.pe > 60:
        reasons.append(f"估值压力偏高，PE {_price(quote.pe)}")
    elif quote.pe is not None and 0 < quote.pe < 20:
        reasons.append(f"估值相对温和，PE {_price(quote.pe)}")
    elif quote.pb is not None and 0 < quote.pb < 1:
        reasons.append(f"估值相对温和，PB {_price(quote.pb)}")


def _append_flow_reason(reasons: list[str], quote: EquityQuote) -> None:
    if quote.net_flow is None and quote.sector:
        reasons.append(f"{quote.sector}板块资金待确认")
    elif quote.net_flow is not None and quote.net_flow < 0:
        prefix = f"{quote.sector}板块" if quote.sector else ""
        reasons.append(f"{prefix}资金净流出")
    elif quote.net_flow is not None and quote.net_flow > 0 and quote.sector:
        reasons.append(f"{quote.sector}板块资金净流入")


def _execution_text(action: str) -> str:
    if action == "add_watch":
        return "可以小幅加仓，但必须分批执行；跌破退出条件立即停止。"
    if action == "trim":
        return "建议先分批减仓，降低单票波动对整仓的影响，再复核保留理由。"
    if action == "exit_watch":
        return "建议优先减仓或止损，不再补仓或等待反弹证明判断。"
    if action == "review":
        return "暂不操作；补齐行情、成本和持仓原因后，系统再给调仓决定。"
    return "维持当前仓位，继续跟踪趋势、资金和失效条件。"


def _analysis_dimensions(
    *,
    item: HoldingItem,
    quote: EquityQuote,
    market_value: float | None,
    cost_value: float,
    pnl: float | None,
    pnl_pct: float | None,
    portfolio_weight: float | None,
    drift: float | None,
    target_market_value: float | None,
    rebalance_value: float | None,
    rebalance_quantity: float | None,
    price_gap_to_cost_pct: float | None,
) -> list[HoldingAnalysisDimension]:
    position_evidence = [f"现价 {_price(quote.price)}"]
    if target_market_value is not None:
        position_evidence.extend(
            [
                f"目标仓位 {item.target_weight * 100:.1f}%",
                f"仓位偏离 {_weight(drift)}",
            ]
        )
    else:
        position_evidence.append("不使用目标比例，按成本、趋势、资金和风控条件判断")

    dimensions = [
        HoldingAnalysisDimension(
            key="position",
            label="持仓规模",
            signal="neutral" if drift is None or abs(drift) <= 0.05 else "warning",
            summary=(
                f"持仓数量 {item.quantity:g} 股，当前市值 {_money(market_value)}，"
                f"组合占比 {_weight(portfolio_weight)}。"
            ),
            evidence=position_evidence,
        ),
        HoldingAnalysisDimension(
            key="cost",
            label="成本盈亏",
            signal="positive" if (pnl or 0) >= 0 else "negative",
            summary=(
                f"成本价 {item.cost_price:.2f}，持仓成本 {_money(cost_value)}，"
                f"浮动盈亏 {_money(pnl)} / {_pct(pnl_pct)}。"
            ),
            evidence=[
                f"盈亏平衡价 {item.cost_price:.2f}",
                f"现价较成本 {_pct(price_gap_to_cost_pct)}",
            ],
        ),
        HoldingAnalysisDimension(
            key="risk",
            label="风险检查",
            signal="negative" if pnl_pct is not None and pnl_pct <= -10 else "neutral",
            summary=(
                f"失效条件：{item.invalidation or '未填写'}；"
                f"资金流 {_money(quote.net_flow)}，当日涨跌 {_pct(quote.change_pct)}。"
            ),
            evidence=[
                f"持仓逻辑：{item.thesis or '未填写'}",
                f"行业：{quote.sector or '行业待补'}",
            ],
        ),
        HoldingAnalysisDimension(
            key="liquidity",
            label="流动性承载",
            signal=_liquidity_signal(quote.amount),
            summary=(
                f"成交额 {_money(quote.amount)}，换手率 {_pct(quote.turnover_rate)}；"
                "用于判断调仓是否会受流动性约束。"
            ),
            evidence=[
                f"成交额 {_money(quote.amount)}",
                f"换手率 {_pct(quote.turnover_rate)}",
                f"量比 {_price(quote.volume_ratio)}",
            ],
        ),
        HoldingAnalysisDimension(
            key="valuation",
            label="估值安全垫",
            signal=_valuation_signal(quote.pe, quote.pb),
            summary=(
                f"PE {_price(quote.pe)}、PB {_price(quote.pb)}，"
                "需要和行业估值、盈利稳定性一起判断安全垫。"
            ),
            evidence=[
                f"PE {_price(quote.pe)}",
                f"PB {_price(quote.pb)}",
                f"总市值 {_money(quote.market_cap)}",
            ],
        ),
        HoldingAnalysisDimension(
            key="sector_context",
            label="板块联动",
            signal="neutral" if quote.sector else "missing",
            summary=(
                f"所属板块 {quote.sector}，需要同步查看板块温度和资金持续性。"
                if quote.sector
                else "个股行业映射暂缺，无法判断板块共振。"
            ),
            evidence=[
                f"行业：{quote.sector or '行业待补'}",
                f"资金流 {_money(quote.net_flow)}",
            ],
        ),
        HoldingAnalysisDimension(
            key="thesis_quality",
            label="持仓逻辑质量",
            signal="positive" if item.thesis.strip() and item.invalidation.strip() else "negative",
            summary=(
                "持仓逻辑与失效条件已经记录，后续应按证据复盘而不是按情绪处理。"
                if item.thesis.strip() and item.invalidation.strip()
                else "持仓逻辑或失效条件不完整，容易变成被动扛单。"
            ),
            evidence=[
                f"逻辑：{item.thesis or '未填写'}",
                f"失效：{item.invalidation or '未填写'}",
            ],
        ),
    ]
    if target_market_value is not None:
        dimensions.insert(
            2,
            HoldingAnalysisDimension(
                key="rebalance",
                label="调仓建议",
                signal=_rebalance_signal(rebalance_quantity),
                summary=(
                    f"目标市值 {_money(target_market_value)}，"
                    f"偏离金额 {_money(rebalance_value)}，{_rebalance_text(rebalance_quantity)}。"
                ),
                evidence=[
                    f"目标仓位 {item.target_weight * 100:.1f}%",
                    f"当前仓位 {_weight(portfolio_weight)}",
                    f"建议股数 {_shares(rebalance_quantity)}",
                ],
            ),
        )
    return dimensions


def _liquidity_signal(amount: float | None) -> str:
    if amount is None:
        return "missing"
    if amount >= 300_000_000:
        return "positive"
    if amount < 80_000_000:
        return "negative"
    return "neutral"


def _valuation_signal(pe: float | None, pb: float | None) -> str:
    if pe is None and pb is None:
        return "missing"
    if pe is not None and 0 < pe < 20:
        return "positive"
    if pb is not None and 0 < pb < 1:
        return "positive"
    if pe is not None and pe > 60:
        return "negative"
    return "neutral"


def _rebalance_signal(rebalance_quantity: float | None) -> str:
    if rebalance_quantity is None:
        return "neutral"
    if rebalance_quantity < -1:
        return "negative"
    if rebalance_quantity > 1:
        return "positive"
    return "neutral"


def _rebalance_text(rebalance_quantity: float | None) -> str:
    if rebalance_quantity is None:
        return "调仓股数待行情确认"
    shares = abs(round(rebalance_quantity))
    if shares == 0:
        return "接近目标仓位"
    if rebalance_quantity < 0:
        return f"建议减仓约 {shares:g} 股"
    return f"可补仓约 {shares:g} 股"


def _money(value: float | None) -> str:
    if value is None:
        return "暂缺"
    return f"{value:,.0f}"


def _price(value: float | None) -> str:
    if value is None:
        return "暂缺"
    return f"{value:.2f}"


def _pct(value: float | None) -> str:
    if value is None:
        return "暂缺"
    prefix = "+" if value > 0 else ""
    return f"{prefix}{value:.2f}%"


def _weight(value: float | None) -> str:
    if value is None:
        return "暂缺"
    return f"{value * 100:+.1f}%" if value < 0 else f"{value * 100:.1f}%"


def _shares(value: float | None) -> str:
    if value is None:
        return "暂缺"
    return f"{round(value):+g} 股"
