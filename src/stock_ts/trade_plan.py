from __future__ import annotations

from dataclasses import dataclass

from .professional_research import EventRadar, TechnicalProfile


@dataclass(frozen=True)
class TradePlan:
    verdict: str
    conviction: int
    target_position: str
    entry_trigger: str
    add_trigger: str
    stop_loss: str
    take_profit: str
    reduce_trigger: str
    forbidden_actions: list[str]
    intraday_checklist: list[str]
    reason: str


def build_trade_plan(
    *,
    stock_name: str,
    latest_close: float,
    upside_score: int,
    risk_level: str,
    trend: str,
    technical: TechnicalProfile,
    event_radar: EventRadar,
    data_quality_warnings: list[str],
) -> TradePlan:
    conviction = _conviction(upside_score, risk_level, trend, event_radar, data_quality_warnings)
    verdict = _verdict(conviction, trend, event_radar, data_quality_warnings)
    target_position = _target_position(verdict, conviction)
    resistance_break = technical.resistance * 1.01
    reclaim_price = max(latest_close * 1.03, (technical.ma5 or latest_close) * 1.005)
    pullback_zone_low = technical.support * 1.01
    pullback_zone_high = max(technical.support * 1.03, technical.invalid_line * 1.04)
    stop_price = technical.invalid_line
    reduce_price = max(technical.invalid_line, latest_close * 0.97)
    take_profit_1 = latest_close * 1.06
    take_profit_2 = (
        technical.resistance if technical.resistance > latest_close else latest_close * 1.10
    )

    if verdict in {"观望", "减仓"}:
        entry_trigger = (
            f"不直接买入；只有放量站回 {reclaim_price:.2f} 且 30 分钟不跌回该价位，"
            "才允许从观察转为小仓试错。"
        )
        add_trigger = "本轮不设置主动加仓；先等趋势从下降/震荡修复为上升。"
    elif verdict == "小仓试错":
        entry_trigger = (
            f"允许小仓试错：回踩 {pullback_zone_low:.2f}-{pullback_zone_high:.2f} 不破，"
            "或放量突破压力位后回踩确认。"
        )
        add_trigger = f"只有收盘站上 {resistance_break:.2f} 且公告无新增风险，再把仓位上调一档。"
    else:
        entry_trigger = (
            f"已有仓位可持有；新仓只在回踩 "
            f"{pullback_zone_low:.2f}-{pullback_zone_high:.2f} 承接有效时执行。"
        )
        add_trigger = f"放量突破 {resistance_break:.2f} 后，第二天不破突破位再考虑加仓。"

    forbidden = [
        f"跌破 {stop_price:.2f} 后禁止补仓摊低。",
        "公告事件未复核前禁止重仓。",
        "大盘热度转弱或板块退潮时禁止追高。",
    ]
    if data_quality_warnings:
        forbidden.insert(0, "数据质量仍有告警时禁止把页面结论当作实盘指令。")

    return TradePlan(
        verdict=verdict,
        conviction=conviction,
        target_position=target_position,
        entry_trigger=entry_trigger,
        add_trigger=add_trigger,
        stop_loss=f"跌破 {stop_price:.2f} 立即按失效处理；若盘中放量跌破，先减仓，不等收盘。",
        take_profit=(
            f"第一止盈观察 {take_profit_1:.2f}；若到 {take_profit_2:.2f} 附近放量滞涨，"
            "至少锁定一部分利润。"
        ),
        reduce_trigger=(
            f"跌破 {reduce_price:.2f}、跌破 5 日线且量能放大、或公告新增减持/质押/监管风险，"
            "触发降风险。"
        ),
        forbidden_actions=forbidden,
        intraday_checklist=[
            f"09:30-10:00 看是否站稳 {latest_close:.2f} 上方，弱于昨日收盘则不追。",
            f"10:30 前若无法收回 {reduce_price:.2f}，持仓优先降风险。",
            f"突破 {resistance_break:.2f} 必须同时满足放量和板块不退潮。",
            "收盘后复核公告、板块排名和成交量，再决定是否保留到下一交易日。",
        ],
        reason=_reason(stock_name, verdict, conviction, trend, event_radar, data_quality_warnings),
    )


def render_trade_plan_markdown(plan: TradePlan) -> str:
    lines = [
        "## 明确操作建议",
        f"- 当前动作：{plan.verdict}",
        f"- 执行置信度：{plan.conviction}/100",
        f"- 目标仓位：{plan.target_position}",
        f"- 主要理由：{plan.reason}",
        f"- 买入/加仓触发条件：{plan.entry_trigger}",
        f"- 加仓规则：{plan.add_trigger}",
        f"- 止损/减仓触发：{plan.stop_loss}",
        f"- 止盈计划：{plan.take_profit}",
        f"- 降风险规则：{plan.reduce_trigger}",
        "",
        "### 禁止动作",
    ]
    lines.extend(f"- {item}" for item in plan.forbidden_actions)
    lines.extend(["", "### 盘中执行清单"])
    lines.extend(f"- {item}" for item in plan.intraday_checklist)
    return "\n".join(lines).strip() + "\n"


def _conviction(
    upside_score: int,
    risk_level: str,
    trend: str,
    event_radar: EventRadar,
    data_quality_warnings: list[str],
) -> int:
    score = upside_score
    if trend == "下降趋势":
        score -= 18
    elif trend == "上升趋势":
        score += 8
    if risk_level == "高":
        score -= 18
    elif risk_level == "中":
        score -= 8
    if event_radar.gate == "事件需复核":
        score -= 15
    if data_quality_warnings:
        score -= 20
    return max(0, min(100, score))


def _verdict(
    conviction: int,
    trend: str,
    event_radar: EventRadar,
    data_quality_warnings: list[str],
) -> str:
    if data_quality_warnings:
        return "观望"
    if trend == "下降趋势" and conviction < 55:
        return "减仓"
    if event_radar.gate == "事件需复核" and conviction < 60:
        return "观望"
    if conviction >= 72:
        return "持有"
    if conviction >= 55:
        return "小仓试错"
    return "观望"


def _target_position(verdict: str, conviction: int) -> str:
    if verdict == "减仓":
        return "已有仓位降到 0%-10%；无仓不新开。"
    if verdict == "观望":
        return "0%；只保留观察，不开新仓。"
    if verdict == "小仓试错":
        return "10%-20%；单票风险不超过组合可承受回撤。"
    return "20%-35%；只有趋势和事件均确认后才允许接近上限。"


def _reason(
    stock_name: str,
    verdict: str,
    conviction: int,
    trend: str,
    event_radar: EventRadar,
    data_quality_warnings: list[str],
) -> str:
    blockers = []
    if trend == "下降趋势":
        blockers.append("趋势未修复")
    if event_radar.gate == "事件需复核":
        blockers.append("公告事件需要复核")
    if data_quality_warnings:
        blockers.append("数据质量有告警")
    if blockers:
        joined = "、".join(blockers)
        return (
            f"{stock_name} 当前执行结论为 {verdict}，置信度 {conviction}/100，约束来自：{joined}。"
        )
    return f"{stock_name} 当前执行结论为 {verdict}，置信度 {conviction}/100，允许按触发条件执行。"
