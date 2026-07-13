from __future__ import annotations

from stock_ts.models import Holding, StockRawData
from stock_ts.professional_research import EventRadar, TechnicalProfile

from .evidence import (
    EvidenceItem,
    EvidenceStatus,
    ResearchInputQuality,
    has_comparable_valuation,
    has_usable_events,
)
from .stock_diagnostics import (
    build_capital_diagnostic,
    build_event_diagnostic,
    build_financial_diagnostic,
    build_technical_diagnostic,
    build_valuation_diagnostic,
)
from .stock_dossier_models import (
    DecisionStep,
    DiagnosticBlock,
    DossierScenario,
    DossierVerdict,
    PositionGuidance,
    ProfessionalStockDossier,
    RiskItem,
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
    financial = build_financial_diagnostic(raw)
    valuation = build_valuation_diagnostic(raw)
    technical_block = build_technical_diagnostic(raw, technical)
    capital = build_capital_diagnostic(raw)
    event_block, risks = build_event_diagnostic(raw, event_radar)
    loss_making = _is_loss_making(raw)
    weak_technical = any(
        marker in technical_block.conclusion
        for marker in ("破位风险", "趋势走弱", "反弹尝试")
    )
    critical_risk = any(item.severity == "critical" for item in risks)
    high_risk = any(item.severity == "high" for item in risks)
    combined_high_risk = critical_risk or high_risk and (loss_making or weak_technical)
    blocker = quality.blockers[0] if quality.blockers else "行情时效未通过"
    stance = _stance(
        paused=paused,
        combined_high_risk=combined_high_risk,
        holding=holding,
        grade=grade,
        weak_technical=weak_technical,
    )
    action = _action(stance)
    counter = risks[0].evidence if risks else event_radar.gate
    thesis = _thesis(
        stance,
        financial=financial,
        technical=technical_block,
        counter=counter,
    )
    verdict = DossierVerdict(
        stance=stance,
        action=action,
        evidence_grade=grade,
        confidence=0 if paused else confidence,
        horizon="5-20 个交易日，并在下一份财报或重大公告后重评",
        thesis=thesis,
        strongest_evidence=technical_block.conclusion,
        strongest_counter_evidence=blocker if paused else counter,
        next_review="刷新最近交易日行情后重新评估。"
        if paused
        else "下一交易日收盘或重大公告后复核。",
    )
    position = _position_guidance(
        technical,
        holding=holding,
        paused=paused,
        grade=grade,
        stance=stance,
        latest_close=latest.close if latest else 0.0,
    )
    diagnostics = (
        financial,
        valuation,
        technical_block,
        capital,
        event_block,
    )
    scenarios = _scenarios(
        raw,
        financial=financial,
        technical=technical_block,
        risks=risks,
        paused=paused,
        resistance=technical.resistance,
        invalid_line=technical.invalid_line,
    )
    evidence = _evidence_ledger(
        raw,
        diagnostics,
        quote_status=quality.quote_status,
    )
    return ProfessionalStockDossier(
        code=raw.code,
        name=raw.name,
        trade_date=latest.date if latest else "",
        latest_close=latest.close if latest else 0.0,
        verdict=verdict,
        decision_steps=_decision_steps(technical, paused=paused),
        diagnostics=diagnostics,
        risks=risks,
        position=position,
        scenarios=scenarios,
        evidence=evidence,
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
    stance: str,
    latest_close: float,
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
    if stance == "风险规避":
        position_cap = "0% 新增" if holding else "0%"
    elif holding:
        position_cap = "不高于当前仓位"
    else:
        position_cap = "5%" if grade in {"A", "B"} else "0%"
    audience = "已持仓" if holding else "未持仓"
    if holding and holding.cost_price > 0:
        pnl = (latest_close / holding.cost_price - 1) * 100
        current = (
            f"持仓 {holding.shares:g} 股，成本 {holding.cost_price:.2f}，"
            f"当前相对成本 {pnl:+.1f}%，按失效线管理"
        )
    elif holding:
        current = f"持仓 {holding.shares:g} 股，成本待补录；先按失效线管理"
    else:
        current = "未持仓，等待价格与证据双重触发"
    return PositionGuidance(
        audience=audience,
        current_action=current,
        position_cap=position_cap,
        risk_budget=(
            "不分配新增风险"
            if stance == "风险规避" or position_cap == "0%"
            else "单次账户风险不超过 0.5%"
        ),
        entry_trigger=f"站稳 {technical.resistance:.2f} 且量能确认",
        add_trigger="首次触发后回踩不破，再确认经营与事件风险",
        reduce_trigger=f"跌破 {technical.support:.2f} 或事件风险升级",
        invalidation=f"跌破 {technical.invalid_line:.2f}",
        prohibited_action="禁止追反弹、未修复失效前摊低成本、不能把低 PB 单独当买点",
    )


def _decision_steps(
    technical: TechnicalProfile,
    *,
    paused: bool,
) -> tuple[DecisionStep, ...]:
    if paused:
        return (
            DecisionStep("当前状态", "paused", "暂停执行", "行情时效未通过"),
            DecisionStep("转强触发", "paused", "刷新行情后重算", "旧压力位不作为触发"),
            DecisionStep("加仓确认", "paused", "暂停加仓", "不增加风险"),
            DecisionStep("降级触发", "paused", "刷新行情后重算", "持仓转人工风控"),
            DecisionStep("失效退出", "paused", "暂停使用旧价格", "刷新后重建失效线"),
        )
    return (
        DecisionStep(
            "当前状态", "current", technical.structure, "决定当前动作"
        ),
        DecisionStep("转强触发", "upgrade", f"站稳 {technical.resistance:.2f}", "允许重新评估"),
        DecisionStep("加仓确认", "confirm", "回踩不破且事件风险未升级", "才允许增加风险"),
        DecisionStep(
            "降级触发", "downgrade", f"跌破 {technical.support:.2f}", "降低观察或持仓等级"
        ),
        DecisionStep("失效退出", "invalid", f"跌破 {technical.invalid_line:.2f}", "终止当前论点"),
    )


def _is_loss_making(raw: StockRawData) -> bool:
    value = raw.fundamental_metrics.get("net_profit")
    try:
        net_profit = float(value) if value not in {None, ""} else None
    except (TypeError, ValueError):
        net_profit = None
    return (net_profit is not None and net_profit < 0) or (
        raw.pe_ttm is not None and raw.pe_ttm <= 0
    )


def _stance(
    *,
    paused: bool,
    combined_high_risk: bool,
    holding: Holding | None,
    grade: str,
    weak_technical: bool,
) -> str:
    if paused:
        return "数据暂停"
    if combined_high_risk:
        return "风险规避"
    if holding is not None:
        return "持仓管理"
    if grade == "C" or weak_technical:
        return "等待修复"
    return "条件观察"


def _action(stance: str) -> str:
    return {
        "数据暂停": "刷新数据后重评",
        "风险规避": "不新开仓；已有仓位优先降低风险",
        "持仓管理": "按成本、支撑和事件风险管理，不盲目加仓",
        "等待修复": "只观察，不建仓",
        "条件观察": "等待价格与证据触发后小仓验证",
    }[stance]


def _thesis(
    stance: str,
    *,
    financial,
    technical,
    counter: str,
) -> str:
    if stance == "数据暂停":
        return "行情时效未通过，当前证据只用于审计。"
    if stance == "风险规避":
        return f"{financial.conclusion}；{technical.conclusion}；{counter}，当前风险收益不匹配。"
    return f"{financial.conclusion}；{technical.conclusion}；最大反证为 {counter}。"


def _scenarios(
    raw: StockRawData,
    *,
    financial: DiagnosticBlock,
    technical: DiagnosticBlock,
    risks: tuple[RiskItem, ...],
    paused: bool,
    resistance: float,
    invalid_line: float,
) -> tuple[DossierScenario, ...]:
    risk_text = risks[0].evidence if risks else "当前未识别高等级标题风险"
    risk_repair = (
        f"{risks[0].category}得到原文证伪或风险解除"
        if risks
        else "没有新增高等级事件风险"
    )
    technical_20 = next(
        (fact for fact in technical.facts if fact.startswith("20日 ")),
        technical.conclusion,
    )
    if paused:
        action = "暂停执行，刷新行情后重新生成情景"
    else:
        action = "仅在经营、事件和价格同时确认后小仓验证"
    return (
        DossierScenario(
            name="改善",
            premise=f"当前财务状态为：{financial.conclusion}；事件反证为：{risk_text}。",
            confirmation=(
                f"亏损收窄或转盈，{risk_repair}，"
                f"且收盘站稳 {resistance:.2f}；当前 {technical_20}。"
            ),
            action=action,
            invalidation="净利润继续为负、事件风险未解除或突破后快速跌回压力位下方。",
            evidence_source="财务截面、公告新闻、20日价格结构",
        ),
        DossierScenario(
            name="基准",
            premise=f"维持当前财务与价格状态：{financial.conclusion}；{technical.conclusion}",
            confirmation=f"价格未跌破 {invalid_line:.2f}，但经营与事件证据没有方向性改善。",
            action="保持当前研究或持仓管理等级，不因单日反弹提高仓位。",
            invalidation="财务、事件或20日价格结构任一项发生方向性恶化。",
            evidence_source="当前财务、技术与风险登记表",
        ),
        DossierScenario(
            name="恶化",
            premise=f"亏损或现金流压力扩大，同时 {risk_text} 继续发酵。",
            confirmation=f"收盘跌破 {invalid_line:.2f}，20日价格损伤扩大或新增高等级公告。",
            action="未持仓继续规避；已持仓优先降低风险，不用补仓摊低成本。",
            invalidation="风险事件证伪、盈利修复且价格重新站稳压力位。",
            evidence_source="财务风险、事件原文与失效价格",
        ),
    )


def _evidence_ledger(
    raw: StockRawData,
    diagnostics: tuple[DiagnosticBlock, ...],
    *,
    quote_status: EvidenceStatus,
) -> tuple[EvidenceItem, ...]:
    sources = ", ".join(raw.data_sources) or "unknown"
    trade_date = raw.bars[-1].date if raw.bars else ""
    items: list[EvidenceItem] = []
    for diagnostic in diagnostics:
        source, as_of = _diagnostic_source(raw, diagnostic.name, sources, trade_date)
        status = _diagnostic_status(diagnostic.status)
        if quote_status in {EvidenceStatus.STALE, EvidenceStatus.BLOCKED} and diagnostic.name in {
            "估值",
            "技术结构",
            "资金与交易",
        }:
            status = quote_status
        risk_detail = (
            f" 风险：{'；'.join(diagnostic.risks)}。" if diagnostic.risks else ""
        )
        items.append(
            EvidenceItem(
                block=diagnostic.name,
                source=source,
                as_of=as_of,
                status=status,
                detail=f"{diagnostic.conclusion}{risk_detail} {diagnostic.limitation}".strip(),
            )
        )
    return tuple(items)


def _diagnostic_source(
    raw: StockRawData,
    block: str,
    fallback: str,
    trade_date: str,
) -> tuple[str, str]:
    if block == "财务质量":
        return (
            str(raw.fundamental_metrics.get("source") or fallback),
            str(raw.fundamental_metrics.get("date") or ""),
        )
    if block == "估值":
        return (
            str(raw.valuation.get("source") or fallback),
            str(raw.valuation.get("date") or trade_date),
        )
    if block == "资金与交易":
        return (
            str(raw.fund_flow_detail.get("source") or fallback),
            str(raw.fund_flow_detail.get("date") or trade_date),
        )
    if block == "事件风险":
        dates = [str(item.get("date") or "") for item in raw.announcements]
        dates.extend(item.date for item in raw.news_items)
        return fallback, max((date for date in dates if date), default=trade_date)
    return fallback, trade_date


def _diagnostic_status(status: str) -> EvidenceStatus:
    return {
        "complete": EvidenceStatus.COMPLETE,
        "missing": EvidenceStatus.MISSING,
        "blocked": EvidenceStatus.BLOCKED,
    }.get(status, EvidenceStatus.DEGRADED)
