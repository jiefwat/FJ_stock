from marketdesk.models import EquityQuote, HoldingAnalysisDimension, HoldingDossier, HoldingItem


def analyse_holding(
    item: HoldingItem, quote: EquityQuote, total_market_value: float | None
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
    drift = portfolio_weight - item.target_weight if portfolio_weight is not None else None
    target_market_value = (
        total_market_value * item.target_weight
        if total_market_value is not None and total_market_value > 0
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
    risk_flags = _risk_flags(item, quote, pnl_pct, drift)
    action = _action(pnl_pct, drift, quote)
    next_actions = _next_actions(action, item, quote, rebalance_quantity)
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
        conclusion=_conclusion(item, quote, pnl_pct, drift, action, rebalance_quantity),
        risk_flags=risk_flags,
        next_actions=next_actions,
    )


def _risk_flags(
    item: HoldingItem, quote: EquityQuote, pnl_pct: float | None, drift: float | None
) -> list[str]:
    flags: list[str] = []
    if pnl_pct is None:
        flags.append("行情价格暂缺")
    elif pnl_pct <= -10:
        flags.append("亏损超过 10%")
    elif pnl_pct >= 20:
        flags.append("盈利较高，注意回撤")
    if drift is not None:
        if drift > 0.1:
            flags.append("组合占比高于目标")
        elif drift < -0.1:
            flags.append("组合占比低于目标")
    if quote.net_flow is not None and quote.net_flow < 0:
        flags.append("资金净流出")
    if not item.invalidation.strip():
        flags.append("缺少失效条件")
    return flags


def _action(pnl_pct: float | None, drift: float | None, quote: EquityQuote) -> str:
    if pnl_pct is None:
        return "review"
    if pnl_pct <= -10 or (quote.change_pct is not None and quote.change_pct < -7):
        return "exit_watch"
    if drift is not None and drift > 0.1:
        return "trim"
    if (
        drift is not None
        and drift < -0.1
        and pnl_pct >= 0
        and (quote.net_flow is None or quote.net_flow >= 0)
    ):
        return "add_watch"
    return "hold"


def _next_actions(
    action: str, item: HoldingItem, quote: EquityQuote, rebalance_quantity: float | None
) -> list[str]:
    actions = {
        "trim": ["复核是否需要降仓到目标仓位", "更新保留仓位的失效条件"],
        "exit_watch": ["检查是否触发失效条件", "决定减仓、止损或转入跟踪清单"],
        "add_watch": ["只在个股证据继续确认时补足目标仓位", "补仓前先设定失效条件"],
        "review": ["补齐行情价格或成本数据", "重读个股证据账本"],
        "hold": ["继续跟踪持仓逻辑", "收盘后复核资金与趋势证据"],
    }[action]
    if rebalance_quantity is not None:
        shares = abs(round(rebalance_quantity))
        if shares > 0 and rebalance_quantity < 0:
            actions.insert(0, f"若回到目标仓位，需减仓约 {shares:g} 股")
        elif shares > 0:
            actions.insert(0, f"若补足目标仓位，可加仓约 {shares:g} 股")
    if quote.sector:
        actions.append(f"同步检查 {quote.sector} 板块温度")
    if quote.net_flow is not None and quote.net_flow < 0:
        actions.append("资金流为净流出，复核是否只是估值修复而缺少主动资金")
    elif quote.net_flow is not None:
        actions.append("资金流为净流入，观察是否连续三日确认")
    actions.append("复核估值和行业位置，避免只按持仓盈亏决定加减仓")
    actions.append("把持仓逻辑、失效条件和下次复盘时间写清楚")
    if item.target_weight == 0:
        actions.append("目标仓位为 0，确认是否应退出持仓")
    return actions[:7]


def _conclusion(
    item: HoldingItem,
    quote: EquityQuote,
    pnl_pct: float | None,
    drift: float | None,
    action: str,
    rebalance_quantity: float | None,
) -> str:
    action_text = _action_text(action)
    dimensions = "仓位偏离、成本风控、估值、流动性、板块资金、持仓逻辑"
    reasons = _reason_fragments(item, quote, pnl_pct, drift)
    execution = _execution_text(action, rebalance_quantity)
    return (
        f"建议动作：{action_text}。"
        f"分析维度：{dimensions}。"
        f"原因：{'、'.join(reasons)}。"
        f"{execution}"
    )


def _action_text(action: str) -> str:
    return {
        "hold": "维持持有",
        "trim": "减仓",
        "add_watch": "可加仓",
        "review": "暂不加仓，先补齐数据",
        "exit_watch": "减仓/退出复核",
    }[action]


def _reason_fragments(
    item: HoldingItem,
    quote: EquityQuote,
    pnl_pct: float | None,
    drift: float | None,
) -> list[str]:
    reasons: list[str] = []
    if drift is None:
        reasons.append("仓位偏离需要先用有效行情确认")
    elif drift > 0.1:
        reasons.append("仓位明显高于目标")
    elif drift < -0.1:
        reasons.append("仓位低于目标")
    else:
        reasons.append("仓位接近目标")

    if pnl_pct is None:
        reasons.append("成本风控缺少现价证据")
    elif pnl_pct <= -10:
        reasons.append("成本风控已触发")
    elif pnl_pct >= 20:
        reasons.append("已有较高安全垫但需防回撤")
    else:
        reasons.append("成本风险未触发强制处理")

    if quote.pe is None and quote.pb is None:
        reasons.append("估值证据暂缺")
    elif quote.pe is not None and quote.pe > 60:
        reasons.append("估值压力偏高")
    elif quote.pe is not None and 0 < quote.pe < 20:
        reasons.append("估值相对温和")
    else:
        reasons.append("估值需要结合行业比较")

    if quote.amount is None:
        reasons.append("流动性待确认")
    elif quote.amount >= 300_000_000:
        reasons.append("流动性足够执行调仓")
    elif quote.amount < 80_000_000:
        reasons.append("流动性偏弱，调仓要分批")
    else:
        reasons.append("流动性中性")

    if quote.net_flow is None:
        reasons.append("板块资金持续性待确认")
    elif quote.net_flow < 0:
        reasons.append("资金净流出")
    else:
        reasons.append("资金净流入")

    if item.thesis.strip() and item.invalidation.strip():
        reasons.append("持仓逻辑已记录，可进入个股页复核证据")
    else:
        reasons.append("持仓逻辑或失效条件不完整")
    return reasons


def _execution_text(action: str, rebalance_quantity: float | None) -> str:
    shares = abs(round(rebalance_quantity)) if rebalance_quantity is not None else 0
    if action == "add_watch":
        return (
            f"可按目标仓位补仓约 {shares:g} 股，但必须等待个股页证据继续确认。"
            if shares > 0
            else "仓位已接近目标，暂不追高加仓。"
        )
    if action == "trim":
        return (
            f"建议先减仓约 {shares:g} 股，回到目标仓位后再复核保留理由。"
            if shares > 0
            else "仓位已接近目标，先观察而不是主动加仓。"
        )
    if action == "exit_watch":
        return (
            f"建议先减仓约 {shares:g} 股，剩余仓位进入个股页复核。"
            if shares > 0
            else "建议先做退出复核，确认是否减仓、止损或转入跟踪清单。"
        )
    if action == "review":
        return "先补齐行情、成本和持仓逻辑，再决定是否加减仓。"
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
    return [
        HoldingAnalysisDimension(
            key="position",
            label="持仓规模",
            signal="neutral" if drift is None or abs(drift) <= 0.05 else "warning",
            summary=(
                f"持仓数量 {item.quantity:g} 股，当前市值 {_money(market_value)}，"
                f"组合占比 {_weight(portfolio_weight)}。"
            ),
            evidence=[
                f"现价 {_price(quote.price)}",
                f"目标仓位 {item.target_weight * 100:.1f}%",
                f"仓位偏离 {_weight(drift)}",
            ],
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
