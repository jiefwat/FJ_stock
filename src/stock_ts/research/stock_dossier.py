from __future__ import annotations

from stock_ts.models import Holding, StockRawData
from stock_ts.professional_research import EventRadar, TechnicalProfile

from .evidence import (
    EvidenceStatus,
    ResearchInputQuality,
    has_comparable_valuation,
    has_usable_events,
)
from .stock_dossier_models import (
    DecisionStep,
    DossierVerdict,
    PositionGuidance,
    ProfessionalStockDossier,
)

_FINANCIAL_SNAPSHOT_FIELDS = {
    "eps",
    "operating_revenue",
    "operating_profit",
    "net_profit",
    "operating_cash_flow",
    "net_asset_per_share",
    "total_assets",
    "shareholder_count",
}


def build_professional_stock_dossier(
    raw: StockRawData,
    *,
    technical: TechnicalProfile,
    event_radar: EventRadar,
    holding: Holding | None = None,
    input_quality: ResearchInputQuality | None = None,
    sector_context: str = "",
    market_context: str = "",
) -> ProfessionalStockDossier:
    del market_context
    latest = raw.bars[-1] if raw.bars else None
    quality = input_quality or ResearchInputQuality(
        quote_status=EvidenceStatus.COMPLETE if latest else EvidenceStatus.BLOCKED,
        blockers=() if latest else ("缺少行情",),
    )
    paused = quality.quote_status in {EvidenceStatus.STALE, EvidenceStatus.BLOCKED}
    financial_snapshot = _has_financial_snapshot(raw)
    usable_events = has_usable_events(raw.announcements, raw.news_items)
    valuation_comparable = has_comparable_valuation(raw.valuation, pe_ttm=raw.pe_ttm)
    confidence = _completeness_score(
        raw,
        quality=quality,
        financial_snapshot=financial_snapshot,
        usable_events=usable_events,
        valuation_comparable=valuation_comparable,
        sector_context=sector_context,
    )
    grade = _evidence_grade(
        raw,
        paused=paused,
        financial_snapshot=financial_snapshot,
        usable_events=usable_events,
        valuation_comparable=valuation_comparable,
    )
    blocker = quality.blockers[0] if quality.blockers else "行情时效未通过"
    stance = "数据暂停" if paused else ("条件观察" if grade in {"A", "B"} else "等待修复")
    action = (
        "刷新数据后重评"
        if paused
        else ("等待触发后小仓验证" if grade in {"A", "B"} else "只观察，不建仓")
    )
    verdict = DossierVerdict(
        stance=stance,
        action=action,
        evidence_grade=grade,
        confidence=0 if paused else confidence,
        horizon="5-20 个交易日，并在下一份财报或重大公告后重评",
        thesis=(
            "行情时效未通过，当前证据只用于审计。"
            if paused
            else "以经营事实、价格结构和事件风险共同验证，不用单一分数代替结论。"
        ),
        strongest_evidence=technical.structure,
        strongest_counter_evidence=blocker if paused else event_radar.gate,
        next_review="刷新最近交易日行情后重新评估。"
        if paused
        else "下一交易日收盘或重大公告后复核。",
    )
    position = _position_guidance(
        technical,
        holding=holding,
        paused=paused,
        grade=grade,
    )
    return ProfessionalStockDossier(
        code=raw.code,
        name=raw.name,
        trade_date=latest.date if latest else "",
        latest_close=latest.close if latest else 0.0,
        verdict=verdict,
        decision_steps=_decision_steps(technical, paused=paused),
        diagnostics=(),
        risks=(),
        position=position,
        scenarios=(),
        evidence=(),
    )


def _has_financial_snapshot(raw: StockRawData) -> bool:
    return any(
        raw.fundamental_metrics.get(field) not in {None, ""} for field in _FINANCIAL_SNAPSHOT_FIELDS
    )


def _completeness_score(
    raw: StockRawData,
    *,
    quality: ResearchInputQuality,
    financial_snapshot: bool,
    usable_events: bool,
    valuation_comparable: bool,
    sector_context: str,
) -> int:
    if quality.quote_status in {EvidenceStatus.STALE, EvidenceStatus.BLOCKED}:
        return 0
    score = 25
    score += 15 if len(raw.bars) >= 60 else 0
    score += 15 if financial_snapshot else 0
    score += 10 if len(raw.fundamental_history) >= 3 else 0
    score += 10 if valuation_comparable else 0
    score += 10 if usable_events else 0
    score += 5 if raw.fund_flow_detail.get("source") or raw.fund_flow is not None else 0
    score += 5 if sector_context.strip() else 0
    score += 5
    return min(100, score)


def _evidence_grade(
    raw: StockRawData,
    *,
    paused: bool,
    financial_snapshot: bool,
    usable_events: bool,
    valuation_comparable: bool,
) -> str:
    if paused or not raw.bars:
        return "D"
    if (
        len(raw.bars) >= 60
        and len(raw.fundamental_history) >= 3
        and valuation_comparable
        and usable_events
    ):
        return "A"
    if len(raw.bars) >= 60 and financial_snapshot and usable_events:
        return "B"
    return "C"


def _position_guidance(
    technical: TechnicalProfile,
    *,
    holding: Holding | None,
    paused: bool,
    grade: str,
) -> PositionGuidance:
    if paused:
        return PositionGuidance(
            audience="已持仓" if holding else "未持仓",
            current_action="暂停执行，先刷新行情",
            position_cap="0%",
            risk_budget="0%",
            entry_trigger="行情时效恢复后重新计算",
            add_trigger="暂停",
            reduce_trigger="暂停新增风险，持仓回到人工风控",
            invalidation="行情时效未通过",
            prohibited_action="禁止使用旧价格追涨、抄底或补仓",
        )
    position_cap = "5%" if grade in {"A", "B"} else "0%"
    audience = "已持仓" if holding else "未持仓"
    current = (
        f"持仓 {holding.shares:g} 股，成本 {holding.cost_price:.2f}，按失效线管理"
        if holding
        else "未持仓，等待价格与证据双重触发"
    )
    return PositionGuidance(
        audience=audience,
        current_action=current,
        position_cap=position_cap,
        risk_budget="单次账户风险不超过 0.5%" if position_cap != "0%" else "不分配新增风险",
        entry_trigger=f"站稳 {technical.resistance:.2f} 且量能确认",
        add_trigger="首次触发后回踩不破，再确认经营与事件风险",
        reduce_trigger=f"跌破 {technical.support:.2f} 或事件风险升级",
        invalidation=f"跌破 {technical.invalid_line:.2f}",
        prohibited_action="禁止追单日反弹、未修复失效前摊低成本",
    )


def _decision_steps(
    technical: TechnicalProfile,
    *,
    paused: bool,
) -> tuple[DecisionStep, ...]:
    return (
        DecisionStep(
            "当前状态", "paused" if paused else "current", technical.structure, "决定当前动作"
        ),
        DecisionStep("转强触发", "upgrade", f"站稳 {technical.resistance:.2f}", "允许重新评估"),
        DecisionStep("加仓确认", "confirm", "回踩不破且事件风险未升级", "才允许增加风险"),
        DecisionStep(
            "降级触发", "downgrade", f"跌破 {technical.support:.2f}", "降低观察或持仓等级"
        ),
        DecisionStep("失效退出", "invalid", f"跌破 {technical.invalid_line:.2f}", "终止当前论点"),
    )
