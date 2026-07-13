from __future__ import annotations

from stock_ts.models import PortfolioAnalysisReport, PositionAnalysis
from stock_ts.portfolio_advice import PortfolioAdvice, PositionAdvice

from .evidence import EvidenceStatus
from .market_regime import MarketRegimeAssessment
from .portfolio_dossier_models import (
    PortfolioBoundary,
    PortfolioDossier,
    PortfolioExposure,
    PortfolioMetric,
    PortfolioQueueItem,
    PortfolioVerdict,
)

_QUEUE_PRIORITY = {"必须处理": 0, "重点观察": 1, "可继续持有": 2, "待补数据": 3}


def build_portfolio_dossier(
    portfolio: PortfolioAnalysisReport,
    advice: PortfolioAdvice,
    *,
    market: MarketRegimeAssessment,
    quote_status: EvidenceStatus,
) -> PortfolioDossier:
    blocked = quote_status in {EvidenceStatus.STALE, EvidenceStatus.BLOCKED}
    blocked = blocked or market.stage == "数据暂停" or market.risk_budget == "0%"
    advice_by_code = {item.code: item for item in advice.position_advices}
    queue = [
        _queue_item(position, advice_by_code.get(position.holding.code), blocked=blocked)
        for position in portfolio.positions
    ]
    queue.sort(
        key=lambda item: (
            _QUEUE_PRIORITY[item.state],
            -item.current_weight,
        )
    )
    boundaries = tuple(
        _boundary(position, advice_by_code.get(position.holding.code), blocked=blocked)
        for position in portfolio.positions
    )
    return PortfolioDossier(
        verdict=_verdict(portfolio, advice, market=market, blocked=blocked),
        metrics=_metrics(portfolio),
        queue=tuple(queue),
        exposures=_exposures(portfolio),
        boundaries=boundaries,
    )


def _verdict(
    portfolio: PortfolioAnalysisReport,
    advice: PortfolioAdvice,
    *,
    market: MarketRegimeAssessment,
    blocked: bool,
) -> PortfolioVerdict:
    primary_risk = (
        portfolio.risk_alerts[0]
        if portfolio.risk_alerts
        else _concentration_risk(portfolio)
    )
    if blocked:
        return PortfolioVerdict(
            state="数据暂停",
            action="保留账本审计，价格动作待刷新",
            risk_budget="0%",
            confidence=0,
            thesis="行情时效未通过；成本、股数和历史暴露可审计，但不能生成当前价格动作。",
            primary_risk="旧价格可能扭曲盈亏、止损和目标仓位判断",
            next_review="刷新最近交易日行情后重新生成处置队列。",
        )
    if portfolio.health_score < 45 or portfolio.top_position_weight >= 0.45:
        state = "风险收缩"
    elif portfolio.health_score >= 75 and not portfolio.risk_alerts:
        state = "结构稳态"
    else:
        state = "结构观察"
    confidence = min(95, max(0, (market.confidence + portfolio.health_score) // 2))
    return PortfolioVerdict(
        state=state,
        action=advice.overall_action,
        risk_budget=market.risk_budget,
        confidence=confidence,
        thesis=(
            f"市场阶段为{market.stage}，组合健康度 {portfolio.health_score}/100；"
            f"先处理集中度与弱势仓位，再使用 {advice.target_cash} 的现金/低风险目标。"
        ),
        primary_risk=primary_risk,
        next_review="下一交易日收盘或任一持仓触发失效条件后复核。",
    )


def _metrics(portfolio: PortfolioAnalysisReport) -> tuple[PortfolioMetric, ...]:
    top_sector = portfolio.sector_weights[0] if portfolio.sector_weights else ("未分类", 0.0)
    weak_count = sum(
        item.trend == "下降趋势" or item.risk_level == "高"
        for item in portfolio.positions
    )
    return (
        PortfolioMetric(
            "组合市值",
            f"{portfolio.total_market_value:,.2f}",
            "audit",
            "仅统计已录入股票，不代表总账户资产",
        ),
        PortfolioMetric(
            "累计盈亏",
            f"{portfolio.total_pnl_ratio:+.2f}%",
            "risk" if portfolio.total_pnl_ratio < 0 else "steady",
            f"金额 {portfolio.total_pnl:+,.2f}",
        ),
        PortfolioMetric(
            "第一大仓位",
            f"{portfolio.top_position_weight:.1%}",
            "critical" if portfolio.top_position_weight >= 0.45 else "watch",
            "超过 45% 视为高集中风险",
        ),
        PortfolioMetric(
            "最高行业暴露",
            f"{top_sector[0]} {top_sector[1]:.1%}",
            "critical" if top_sector[1] >= 0.60 else "watch",
            "同主题风险需要合并管理",
        ),
        PortfolioMetric(
            "弱势/高风险",
            f"{weak_count} 只",
            "risk" if weak_count else "steady",
            "下降趋势或高风险持仓",
        ),
    )


def _queue_item(
    position: PositionAnalysis,
    advice: PositionAdvice | None,
    *,
    blocked: bool,
) -> PortfolioQueueItem:
    if blocked or position.latest_price <= 0:
        state = "待补数据"
    elif advice is not None and advice.action in {"降仓", "锁定利润"}:
        state = "必须处理"
    elif position.risk_level == "高":
        state = "必须处理"
    elif advice is not None and advice.action == "持有观察":
        state = "重点观察"
    elif position.weight >= 0.25:
        state = "重点观察"
    else:
        state = "可继续持有"
    reason = advice.reason if advice is not None else _position_reason(position)
    trigger = "待刷新" if blocked else (advice.next_check if advice else "复核趋势与风险")
    invalidation = "待刷新" if blocked else _invalidation(position, advice)
    return PortfolioQueueItem(
        priority=_QUEUE_PRIORITY[state] + 1,
        state=state,
        code=position.holding.code,
        name=position.holding.name,
        current_weight=position.weight,
        cost_context=_cost_context(position),
        reason=reason,
        trigger=trigger,
        invalidation=invalidation,
    )


def _boundary(
    position: PositionAnalysis,
    advice: PositionAdvice | None,
    *,
    blocked: bool,
) -> PortfolioBoundary:
    if blocked:
        return PortfolioBoundary(
            code=position.holding.code,
            name=position.holding.name,
            current_action="价格动作待刷新",
            target_range="待刷新",
            reduce_trigger="待刷新",
            invalidation="待刷新",
            prohibited_action="禁止使用旧价格加仓、补仓或机械止损",
        )
    action = advice.action if advice is not None else "重点观察"
    target = advice.target_weight if advice is not None else "不高于当前仓位"
    reduce_trigger = advice.next_check if advice is not None else "趋势或风险等级恶化"
    invalidation = (
        f"跌破 {advice.stop_loss:.2f}" if advice is not None else "价格证据失效"
    )
    return PortfolioBoundary(
        code=position.holding.code,
        name=position.holding.name,
        current_action=action,
        target_range=target,
        reduce_trigger=reduce_trigger,
        invalidation=invalidation,
        prohibited_action="禁止因成本锚定摊低问题仓；未触发前不扩大风险",
    )


def _exposures(portfolio: PortfolioAnalysisReport) -> tuple[PortfolioExposure, ...]:
    exposures: list[PortfolioExposure] = []
    for sector, weight in portfolio.sector_weights:
        severity = "critical" if weight >= 0.60 else "high" if weight >= 0.45 else "watch"
        consequence = (
            "停止新增同主题仓位并优先降低相关性"
            if weight >= 0.60
            else "新增同主题仓位前复核组合相关性"
        )
        exposures.append(PortfolioExposure(f"行业：{sector}", weight, severity, consequence))
    for position in portfolio.positions:
        if position.weight < 0.30:
            continue
        severity = "critical" if position.weight >= 0.45 else "high"
        exposures.append(
            PortfolioExposure(
                f"单股：{position.holding.name}",
                position.weight,
                severity,
                "降低单票集中度后再考虑新增风险",
            )
        )
    return tuple(sorted(exposures, key=lambda item: item.weight, reverse=True))


def _cost_context(position: PositionAnalysis) -> str:
    if position.holding.cost_price <= 0:
        return "成本待补录"
    return (
        f"成本 {position.holding.cost_price:.2f} / 现价 {position.latest_price:.2f} / "
        f"盈亏 {position.pnl_ratio:+.1f}%"
    )


def _invalidation(position: PositionAnalysis, advice: PositionAdvice | None) -> str:
    if advice is not None:
        return f"跌破 {advice.stop_loss:.2f}"
    return "趋势转弱或风险等级升级"


def _position_reason(position: PositionAnalysis) -> str:
    return (
        f"趋势 {position.trend}；风险 {position.risk_level}；"
        f"当前仓位 {position.weight:.1%}"
    )


def _concentration_risk(portfolio: PortfolioAnalysisReport) -> str:
    if portfolio.top_position_weight >= 0.35:
        return f"第一大持仓占比 {portfolio.top_position_weight:.1%}"
    if portfolio.sector_weights:
        sector, weight = portfolio.sector_weights[0]
        return f"最高行业暴露为 {sector} {weight:.1%}"
    return "暂无突出集中度风险，仍需按持仓边界复核"
