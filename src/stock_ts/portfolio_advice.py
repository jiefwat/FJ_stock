from __future__ import annotations

from dataclasses import dataclass

from .models import MarketSnapshot, PortfolioAnalysisReport, PositionAnalysis


@dataclass(frozen=True)
class PositionAdvice:
    code: str
    name: str
    action: str
    current_weight: float
    target_weight: str
    adjust_amount: float
    stop_loss: float
    take_profit: float
    reason: str
    next_check: str


@dataclass(frozen=True)
class PortfolioAdvice:
    holdings_path: str
    transactions_path: str
    holdings_template: str
    overall_action: str
    target_cash: str
    position_overview: list[str]
    portfolio_actions: list[str]
    position_advices: list[PositionAdvice]
    add_holding_steps: list[str]


def build_portfolio_advice(
    portfolio: PortfolioAnalysisReport,
    *,
    market: MarketSnapshot,
    holdings_path: str,
    transactions_path: str | None = None,
) -> PortfolioAdvice:
    advices = [_position_advice(position, portfolio, market) for position in portfolio.positions]
    return PortfolioAdvice(
        holdings_path=holdings_path,
        transactions_path=transactions_path or "data/portfolio/transactions.csv",
        holdings_template="code,name,shares,cost_price,sector,note",
        overall_action=_overall_action(portfolio, market),
        target_cash=_target_cash(portfolio, market),
        position_overview=_position_overview(portfolio, market),
        portfolio_actions=_portfolio_actions(portfolio, market, advices),
        position_advices=advices,
        add_holding_steps=[
            f"编辑 {holdings_path}，按表头 code,name,shares,cost_price,sector,note 增加一行。",
            "code 用 6 位股票代码；shares 填当前股数；cost_price 填你的持仓成本。",
            "如果你更习惯记录交易流水，编辑 transactions CSV，然后用 --transactions 生成持仓。",
            "Web URL 可加 holdings=你的文件路径，用不同持仓文件做多账户分析。",
        ],
    )


def render_portfolio_advice_markdown(advice: PortfolioAdvice) -> str:
    lines = [
        "## 我的持仓在哪添加",
        f"- 持仓文件：`{advice.holdings_path}`",
        f"- 交易流水：`{advice.transactions_path}`",
        f"- CSV 表头：`{advice.holdings_template}`",
        "",
        "## 组合整体建议",
        f"- 总体动作：{advice.overall_action}",
        f"- 目标现金/低风险仓位：{advice.target_cash}",
    ]
    lines.extend(["", "## 整体仓位情况"])
    lines.extend(f"- {item}" for item in advice.position_overview)
    lines.extend(["", "## 组合处理动作"])
    lines.extend(f"- {item}" for item in advice.portfolio_actions)
    lines.extend(["", "## 具体持仓处理"])
    for item in advice.position_advices:
        lines.append(
            f"- {item.name}（{item.code}）：{item.action}，当前仓位 {item.current_weight:.1%}，"
            f"目标仓位 {item.target_weight}，调整金额 {item.adjust_amount:.2f}，"
            f"止损 {item.stop_loss:.2f}，止盈观察 {item.take_profit:.2f}。{item.reason}"
        )
    return "\n".join(lines).strip() + "\n"


def _position_advice(
    position: PositionAnalysis,
    portfolio: PortfolioAnalysisReport,
    market: MarketSnapshot,
) -> PositionAdvice:
    action = _position_action(position, portfolio, market)
    target_low, target_high = _target_weight_range(action, position)
    target_mid = (target_low + target_high) / 2
    target_value = portfolio.total_market_value * target_mid
    adjust_amount = target_value - position.market_value
    stop_loss = _stop_loss(position)
    take_profit = _take_profit(position)
    return PositionAdvice(
        code=position.holding.code,
        name=position.holding.name,
        action=action,
        current_weight=position.weight,
        target_weight=f"{target_low:.0%}-{target_high:.0%}",
        adjust_amount=round(adjust_amount, 2),
        stop_loss=round(stop_loss, 2),
        take_profit=round(take_profit, 2),
        reason=_position_reason(position, action, market),
        next_check=_next_check(position, stop_loss),
    )


def _position_action(
    position: PositionAnalysis,
    portfolio: PortfolioAnalysisReport,
    market: MarketSnapshot,
) -> str:
    if position.risk_level == "高" or position.trend == "下降趋势":
        return "降仓"
    if position.weight >= 0.5:
        return "降仓"
    if market.heat_score < 45 and position.weight >= 0.25:
        return "降仓"
    if position.pnl_ratio >= 15 and position.weight >= 0.30:
        return "锁定利润"
    if position.trend == "上升趋势" and market.heat_score >= 60 and position.weight <= 0.20:
        return "持有观察"
    if portfolio.health_score >= 70:
        return "持有"
    return "持有观察"


def _target_weight_range(action: str, position: PositionAnalysis) -> tuple[float, float]:
    if action == "降仓":
        if position.weight >= 0.5:
            return 0.35, 0.45
        return 0.0, 0.10
    if action == "锁定利润":
        return 0.20, 0.30
    if action == "持有":
        return max(0.05, position.weight - 0.05), min(0.35, position.weight + 0.05)
    return max(0.03, position.weight - 0.03), min(0.25, position.weight + 0.03)


def _stop_loss(position: PositionAnalysis) -> float:
    if position.pnl_ratio > 10:
        return max(position.holding.cost_price, position.latest_price * 0.93)
    return position.latest_price * 0.92


def _take_profit(position: PositionAnalysis) -> float:
    if position.pnl_ratio > 15:
        return position.latest_price * 1.05
    return position.latest_price * 1.10


def _position_reason(position: PositionAnalysis, action: str, market: MarketSnapshot) -> str:
    reasons = [
        f"趋势 {position.trend}",
        f"风险 {position.risk_level}",
        f"盈亏 {position.pnl_ratio:.2f}%",
    ]
    if position.weight >= 0.5:
        reasons.append("单票集中度过高")
    if market.heat_score < 45:
        reasons.append("市场偏弱")
    return f"{action}原因：{'、'.join(reasons)}。"


def _next_check(position: PositionAnalysis, stop_loss: float) -> str:
    return f"盘中若跌破 {stop_loss:.2f} 或连续弱于指数，按计划执行，不临盘改规则。"


def _overall_action(portfolio: PortfolioAnalysisReport, market: MarketSnapshot) -> str:
    if portfolio.top_position_weight >= 0.5:
        return "先降集中度，再谈进攻"
    if market.heat_score < 45:
        return "防守优先，降低权益暴露"
    if portfolio.health_score >= 75:
        return "结构健康，按持仓纪律滚动优化"
    return "中性调整，先处理弱势和过度集中持仓"


def _target_cash(portfolio: PortfolioAnalysisReport, market: MarketSnapshot) -> str:
    if market.heat_score < 45:
        return "30%-50%"
    if portfolio.top_position_weight >= 0.5:
        return "20%-35%"
    if portfolio.health_score >= 75:
        return "10%-20%"
    return "15%-30%"


def _portfolio_actions(
    portfolio: PortfolioAnalysisReport,
    market: MarketSnapshot,
    advices: list[PositionAdvice],
) -> list[str]:
    actions: list[str] = []
    if portfolio.top_position_weight >= 0.5:
        top = portfolio.positions[0]
        actions.append(
            f"第一大持仓 {top.holding.name} 占比 {top.weight:.1%}，"
            "先降到 35%-45% 区间，避免组合被单票主导。"
        )
    weak = [item for item in advices if item.action == "降仓"]
    if weak:
        names = "、".join(item.name for item in weak[:3])
        actions.append(f"优先处理需降仓标的：{names}。")
    if portfolio.sector_weights:
        sector, weight = portfolio.sector_weights[0]
        if weight >= 0.5:
            actions.append(f"行业暴露最高为 {sector} {weight:.1%}，新仓不要继续加同方向。")
    mainline = "、".join(name for name, pct in market.top_sectors[:3] if pct > 0)
    if mainline:
        actions.append(f"若要新增持仓，只允许在市场主线 {mainline} 中等回踩确认，不追涨。")
    actions.append("所有调整按价格触发执行，不因为主观感觉临时加仓。")
    return actions


def _position_overview(
    portfolio: PortfolioAnalysisReport,
    market: MarketSnapshot,
) -> list[str]:
    if not portfolio.positions:
        return [
            "记录内股票仓位：0%，当前没有录入持仓。",
            "现金未录入：系统暂不能判断账户总仓位，只能分析已录入股票篮子。",
        ]
    top_positions = sorted(portfolio.positions, key=lambda item: item.weight, reverse=True)
    top = top_positions[0]
    top3_weight = sum(item.weight for item in top_positions[:3])
    top_sector = portfolio.sector_weights[0] if portfolio.sector_weights else ("未分类", 0.0)
    weak_weight = sum(
        item.weight
        for item in portfolio.positions
        if item.trend == "下降趋势" or item.risk_level == "高"
    )
    cash_target = _target_cash(portfolio, market)
    return [
        "记录内股票仓位：100%（仅按已录入股票市值计算，现金未录入，不能代表账户总仓位）。",
        f"目标现金/低风险：{cash_target}；如果这份持仓就是全部账户，先按这个区间预留机动仓。",
        f"第一大+前三大：{top.holding.name} {top.weight:.1%}，前三大合计 {top3_weight:.1%}。",
        f"行业暴露：{top_sector[0]} {top_sector[1]:.1%}，新仓避免继续堆到同一方向。",
        f"风险仓位：弱势/高风险持仓合计 {weak_weight:.1%}，先处理这部分再考虑扩仓。",
    ]
