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
    ThesisFramework,
    WeightedEvidence,
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
    diagnostics = (
        financial,
        valuation,
        technical_block,
        capital,
        event_block,
    )
    thesis_framework = _thesis_framework(
        raw,
        financial=financial,
        valuation=valuation,
        technical=technical_block,
        capital=capital,
        risks=risks,
        sector_context=sector_context,
        paused=paused,
        resistance=technical.resistance,
        invalid_line=technical.invalid_line,
    )
    weighted_evidence = _weighted_evidence(
        raw=raw,
        financial=financial,
        valuation=valuation,
        event=event_block,
        capital=capital,
        technical=technical_block,
        risks=risks,
        sector_context=sector_context,
        paused=paused,
    )
    supporting_evidence = next(
        (item.fact for item in weighted_evidence if item.direction == "支持"),
        "尚无足以支撑提高风险预算的证据。",
    )
    counter_evidence = (
        blocker
        if paused
        else (
            risks[0].evidence
            if risks
            else next(
                (item.fact for item in weighted_evidence if item.direction == "反证"),
                "未识别高权重反证，但未知项仍需补齐。",
            )
        )
    )
    verdict = DossierVerdict(
        stance=stance,
        action=action,
        evidence_grade=grade,
        confidence=0 if paused else confidence,
        horizon=thesis_framework.catalyst_window,
        thesis=thesis_framework.headline,
        strongest_evidence=(
            "保留已有事实用于审计，不形成当前交易判断。"
            if paused
            else supporting_evidence
        ),
        strongest_counter_evidence=counter_evidence,
        next_review="刷新最近交易日行情后重新评估。"
        if paused
        else "下一交易日收盘或重大公告后复核。",
    )
    research_confirmation = _research_confirmation(
        financial=financial,
        risks=risks,
        financial_direction=weighted_evidence[0].direction,
    )
    position = _position_guidance(
        technical,
        holding=holding,
        paused=paused,
        grade=grade,
        stance=stance,
        latest_close=latest.close if latest else 0.0,
        thesis=thesis_framework,
        research_confirmation=research_confirmation,
        risks=risks,
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
        decision_steps=_decision_steps(
            technical,
            paused=paused,
            stance=stance,
            action=action,
            thesis=thesis_framework,
            research_confirmation=research_confirmation,
            risks=risks,
        ),
        diagnostics=diagnostics,
        risks=risks,
        position=position,
        scenarios=scenarios,
        evidence=evidence,
        thesis=thesis_framework,
        weighted_evidence=weighted_evidence,
    )


def _thesis_framework(
    raw: StockRawData,
    *,
    financial: DiagnosticBlock,
    valuation: DiagnosticBlock,
    technical: DiagnosticBlock,
    capital: DiagnosticBlock,
    risks: tuple[RiskItem, ...],
    sector_context: str,
    paused: bool,
    resistance: float,
    invalid_line: float,
) -> ThesisFramework:
    del capital, sector_context
    loss_making = _is_loss_making(raw)
    top_risk = risks[0].evidence if risks else "未识别高等级事件反证"
    risk_category = risks[0].category if risks else "事件风险"
    if paused:
        return ThesisFramework(
            headline="数据未通过，研究假设暂停",
            core_conflict="价格与研究证据不在同一有效时点。",
            causal_chain=(
                "保留已有经营与事件事实，仅用于审计",
                "行情时效恢复前不推断风险收益变化",
                "刷新后重算估值、触发线与失效线",
            ),
            expectation_gap="一致预期与当前价格时点不一致，预期差不可量化。",
            valuation_fit="旧价格下的估值不参与当前判断。",
            catalyst_window="最近交易日行情恢复后",
            key_unknown="最近交易日价格、成交量与流水线状态",
            falsifier="行情仍过期或刷新后证据方向发生变化。",
        )
    if financial.status == "missing":
        headline = "经营证据待验证：价格信号不能替代公司质量"
        core_conflict = "当前价格强度是否有真实经营事实支撑。"
    elif loss_making and risks:
        headline = f"投资假设尚未成立：盈利修复与{risk_category}解除必须同时发生"
        core_conflict = f"盈利修复能否覆盖{risk_category}造成的风险折价。"
    elif loss_making:
        headline = "修复假设待验证：盈利转正后估值与价格才有解释力"
        core_conflict = "盈利何时修复，以及修复后估值能否恢复可比性。"
    elif risks:
        headline = f"风险解除假设待验证：先核对{risk_category}，再谈价格机会"
        core_conflict = f"经营证据能否抵消{risk_category}对风险预算的约束。"
    elif valuation.status != "complete":
        headline = "条件研究：经营证据需先证明当前估值合理"
        core_conflict = "经营质量能否支撑当前估值，且估值口径能否被核对。"
    else:
        headline = "条件研究：经营延续后，估值与价格共振才形成机会"
        core_conflict = "经营质量能否持续，并被当前估值与价格正确反映。"

    if financial.status == "missing":
        impact = "先补经营与现金流证据，暂不推断盈利变化"
    elif loss_making:
        impact = "只有亏损收窄或转盈，且关键事件风险解除，估值锚才可能恢复"
    else:
        impact = "盈利与现金流质量需要延续，才能支撑估值和风险预算"
    price_validation = (
        f"{valuation.conclusion} 价格需站稳 {resistance:.2f} 且量能确认；"
        f"跌破 {invalid_line:.2f} 终止当前价格论点"
    )
    if financial.status == "missing":
        key_unknown = "最近财报、盈利与经营现金流质量"
    elif valuation.status != "complete":
        key_unknown = "一致预期、历史估值分位与同行可比口径"
    elif not risks:
        key_unknown = "一致预期变化与下一财报的盈利持续性"
    else:
        key_unknown = f"{risk_category}原文、影响范围与解除条件"
    falsifier_parts = ["盈利或现金流方向性恶化", f"收盘跌破 {invalid_line:.2f}"]
    if loss_making:
        falsifier_parts.insert(0, "亏损继续扩大或现金流转弱")
    if risks:
        falsifier_parts.insert(0, f"{top_risk}未解除或继续升级")
    return ThesisFramework(
        headline=headline,
        core_conflict=core_conflict,
        causal_chain=(
            f"事实：{financial.conclusion}；事件：{top_risk}",
            f"推断：{impact}",
            f"验证：{price_validation}",
        ),
        expectation_gap=(
            "未接入盈利一致预期，预期差不可量化；"
            "下一步核对业绩预告、机构预测变化与实际财报。"
        ),
        valuation_fit=(
            f"{valuation.conclusion} "
            + (
                "亏损阶段 PE 失去解释力；盈利修复前不得据此判断低估。"
                if loss_making
                else "估值必须与盈利增长、现金流和行业位置一起验证。"
            )
        ),
        catalyst_window="未来 5-20 个交易日，并在下一份财报或重大公告时重评。",
        key_unknown=key_unknown,
        falsifier="；".join(falsifier_parts) + "。",
    )


def _weighted_evidence(
    *,
    raw: StockRawData,
    financial: DiagnosticBlock,
    valuation: DiagnosticBlock,
    event: DiagnosticBlock,
    capital: DiagnosticBlock,
    technical: DiagnosticBlock,
    risks: tuple[RiskItem, ...],
    sector_context: str,
    paused: bool,
) -> tuple[WeightedEvidence, ...]:
    history_direction, history_fact = _fundamental_history_signal(raw)
    if financial.status == "missing":
        financial_direction = "未知"
        financial_inference = "没有经营事实时，技术强度不能升级为投资逻辑。"
    elif financial.risks:
        financial_direction = "反证"
        financial_inference = "盈利或现金流压力直接压低风险预算。"
    elif history_direction == "improving":
        financial_direction = "支持"
        financial_inference = "多期收入与利润增速改善可支持继续验证，但仍需现金流和估值匹配。"
    elif history_direction == "weakening":
        financial_direction = "反证"
        financial_inference = "多期收入与利润增速走弱，经营趋势压低风险预算。"
    else:
        financial_direction = "中性"
        financial_inference = "单期财务只能描述现状，不能证明趋势。"

    if valuation.status == "missing" or "PE 失去解释力" in valuation.conclusion:
        valuation_direction = "未知"
        valuation_inference = "缺少有效估值锚，不能形成低估或高估判断。"
    elif valuation.risks:
        valuation_direction = "反证"
        valuation_inference = "估值口径冲突会降低结论可信度。"
    else:
        valuation_direction = "中性"
        valuation_inference = "相对估值只提供参照，仍需盈利质量支撑。"

    if event.status == "missing":
        event_direction = "未知"
        event_inference = "没有事件数据不等于没有风险。"
    elif risks:
        event_direction = "反证"
        event_inference = "高等级事件在原文证伪前优先约束新风险。"
    else:
        event_direction = "中性"
        event_inference = "未见标题级风险只能通过初筛，不能当成催化。"

    if paused:
        market_direction = "未知"
    elif technical.status == "missing" and capital.status == "missing":
        market_direction = "未知"
    elif any(
        marker in technical.conclusion
        for marker in ("破位风险", "趋势走弱", "反弹尝试")
    ):
        market_direction = "反证"
    elif "趋势延续" in technical.conclusion:
        market_direction = "支持"
    else:
        market_direction = "中性"

    return (
        WeightedEvidence(
            dimension="盈利质量",
            importance="高",
            direction=financial_direction,
            fact=f"{financial.conclusion} {history_fact}".strip(),
            inference=financial_inference,
            unknown=(
                "补充至少一个财务截面与三个可比期间。"
                if financial.status == "missing"
                else financial.limitation
            ),
        ),
        WeightedEvidence(
            dimension="估值与预期差",
            importance="高",
            direction=valuation_direction,
            fact=valuation.conclusion,
            inference=valuation_inference,
            unknown="补充一致预期、历史分位与同行可比口径。",
        ),
        WeightedEvidence(
            dimension="事件与治理",
            importance="高",
            direction=event_direction,
            fact=event.conclusion,
            inference=event_inference,
            unknown=event.limitation,
        ),
        WeightedEvidence(
            dimension="行业位置",
            importance="中",
            direction="中性" if sector_context.strip() else "未知",
            fact=sector_context.strip() or "缺少结构化行业强弱与公司相对排名。",
            inference=(
                "现有行业描述只用于比较，未形成结构化排名，不自动加分。"
                if sector_context.strip()
                else "没有行业位置时，无法判断公司变化是否优于同业。"
            ),
            unknown="补充行业景气、同业盈利和相对强弱排名。",
        ),
        (
            WeightedEvidence(
                dimension="资金与价格",
                importance="中",
                direction="未知",
                fact="行情时效未通过；旧价格与资金事实仅供审计。",
                inference="刷新前不确认执行时点、承接或失效线。",
                unknown="补齐最近交易日价格、成交量与资金证据。",
            )
            if paused
            else WeightedEvidence(
                dimension="资金与价格",
                importance="中",
                direction=market_direction,
                fact=f"{technical.conclusion}；{capital.conclusion}",
                inference="只确认执行时点、承接和失效，不证明公司质量。",
                unknown=f"{technical.limitation} {capital.limitation}",
            )
        ),
    )


def _fundamental_history_signal(raw: StockRawData) -> tuple[str, str]:
    recent = sorted(raw.fundamental_history, key=lambda item: item.date)[-3:]
    if len(recent) < 3:
        return "insufficient", "财务历史不足三期，不能确认趋势。"
    revenues = [item.revenue_yoy for item in recent]
    profits = [item.net_profit_yoy for item in recent]
    if any(value is None for value in (*revenues, *profits)):
        return "incomplete", "最近三期收入或利润增速字段不完整。"
    revenue_values = [float(value) for value in revenues if value is not None]
    profit_values = [float(value) for value in profits if value is not None]
    fact = (
        "最近三期营收同比 "
        + " -> ".join(f"{value:.1f}%" for value in revenue_values)
        + "；净利润同比 "
        + " -> ".join(f"{value:.1f}%" for value in profit_values)
        + "。"
    )
    revenue_improving = all(
        current > previous for previous, current in zip(revenue_values, revenue_values[1:])
    )
    profit_improving = all(
        current > previous for previous, current in zip(profit_values, profit_values[1:])
    )
    revenue_weakening = all(
        current < previous for previous, current in zip(revenue_values, revenue_values[1:])
    )
    profit_weakening = all(
        current < previous for previous, current in zip(profit_values, profit_values[1:])
    )
    if revenue_improving and profit_improving:
        return "improving", f"{fact} 收入与利润增速连续改善。"
    if revenue_weakening and profit_weakening:
        return "weakening", f"{fact} 收入与利润增速连续走弱。"
    return "mixed", f"{fact} 收入与利润方向分化或波动。"


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
    thesis: ThesisFramework,
    research_confirmation: str,
    risks: tuple[RiskItem, ...],
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
    if stance == "风险规避":
        entry_trigger = f"风险未解除前暂停；先确认{research_confirmation}"
        add_trigger = "暂停；研究反证未解除前不增加风险"
    else:
        entry_trigger = (
            f"经营与事件确认：{research_confirmation}；"
            f"价格站稳 {technical.resistance:.2f} 且量能确认"
        )
        add_trigger = (
            "首次触发后回踩不破，且盈利、现金流与事件证据没有降级"
        )
    risk_reduce = (
        f"{risks[0].category}升级"
        if risks
        else "盈利、现金流或事件证据转弱"
    )
    return PositionGuidance(
        audience=audience,
        current_action=current,
        position_cap=position_cap,
        risk_budget=(
            "不分配新增风险"
            if stance == "风险规避" or position_cap == "0%"
            else "单次账户风险不超过 0.5%"
        ),
        entry_trigger=entry_trigger,
        add_trigger=add_trigger,
        reduce_trigger=f"{risk_reduce}，或收盘跌破 {technical.support:.2f}",
        invalidation=thesis.falsifier,
        prohibited_action="禁止追反弹、未修复失效前摊低成本、不能把低 PB 单独当买点",
    )


def _decision_steps(
    technical: TechnicalProfile,
    *,
    paused: bool,
    stance: str,
    action: str,
    thesis: ThesisFramework,
    research_confirmation: str,
    risks: tuple[RiskItem, ...],
) -> tuple[DecisionStep, ...]:
    if paused:
        return (
            DecisionStep("当前判断", "paused", "暂停执行", "行情时效未通过"),
            DecisionStep("研究转强", "paused", "刷新行情后重算", "旧证据不升级结论"),
            DecisionStep("价格确认", "paused", "暂停使用旧价格", "刷新后重建触发线"),
            DecisionStep("降级条件", "paused", "行情仍过期，继续暂停", "持仓转人工风控"),
            DecisionStep("论点失效", "paused", "刷新后证据方向变化", "重新建立研究假设"),
        )
    downgrade = (
        f"{risks[0].category}继续升级，或收盘跌破 {technical.support:.2f}"
        if risks
        else f"经营或事件证据转弱，或收盘跌破 {technical.support:.2f}"
    )
    price_confirmation = (
        "风险解除后才重启价格确认"
        if stance == "风险规避"
        else f"站稳 {technical.resistance:.2f} 且量能确认"
    )
    return (
        DecisionStep("当前判断", "current", stance, action),
        DecisionStep("研究转强", "upgrade", research_confirmation, "允许进入价格确认"),
        DecisionStep("价格确认", "confirm", price_confirmation, "才允许增加风险"),
        DecisionStep("降级条件", "downgrade", downgrade, "降低观察或持仓等级"),
        DecisionStep("论点失效", "invalid", thesis.falsifier, "终止当前研究假设"),
    )


def _research_confirmation(
    *,
    financial: DiagnosticBlock,
    risks: tuple[RiskItem, ...],
    financial_direction: str,
) -> str:
    if financial.status == "missing":
        financial_condition = "补齐财务并确认盈利与现金流没有恶化"
    elif any(marker in financial.risks for marker in ("盈利为负", "主营盈利承压")):
        financial_condition = "亏损收窄或转盈，且经营现金流不恶化"
    elif financial_direction == "支持":
        financial_condition = "多期收入与利润改善延续，且现金流质量不恶化"
    elif financial_direction == "反证":
        financial_condition = "收入与利润增速停止走弱，并由下一期财报确认"
    else:
        financial_condition = "下一期财报确认盈利与经营现金流没有恶化"
    if risks:
        return f"{financial_condition}，并由公告原文确认{risks[0].category}解除"
    return f"{financial_condition}，且事件风险不升级"


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
    if paused:
        return _paused_dossier_scenarios()
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


def _paused_dossier_scenarios() -> tuple[DossierScenario, ...]:
    return (
        DossierScenario(
            name="改善",
            premise="最近交易日行情、成交量与流水线状态恢复有效。",
            confirmation="刷新后经营、事件与价格证据仍支持原研究方向。",
            action="暂停执行；数据恢复后重新生成改善情景。",
            invalidation="行情继续过期或刷新后证据方向变化。",
            evidence_source="数据时效闸门",
        ),
        DossierScenario(
            name="基准",
            premise="已有事实保留，但当前价格证据仍不可执行。",
            confirmation="等待最近交易日数据与研究证据重新对齐。",
            action="暂停执行；只保留事实核对。",
            invalidation="任何旧价格触发线均不再有效。",
            evidence_source="数据时效闸门",
        ),
        DossierScenario(
            name="恶化",
            premise="行情继续过期，或刷新后经营与事件证据进一步转弱。",
            confirmation="数据质量告警持续，不能确认当前风险边界。",
            action="暂停执行；持仓回到人工风控。",
            invalidation="数据恢复并完成全量重评。",
            evidence_source="数据时效闸门",
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
