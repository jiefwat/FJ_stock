from __future__ import annotations

from stock_ts.models import (
    CandidatePoolReport,
    CandidateStockAnalysis,
    CandidateStockRawData,
)

from .evidence import EvidenceStatus
from .market_regime import MarketRegimeAssessment
from .opportunity_dossier_models import (
    CandidateDecision,
    FunnelStage,
    OpportunityDossier,
    OpportunityGate,
    OpportunityRisk,
)

_STATE_PRIORITY = {"可验证": 0, "只观察": 1, "风险排除": 2, "待补数据": 3}
_EXCLUSION_MARKERS = (
    "退市",
    "立案调查",
    "重大诉讼",
    "重大处罚",
    "跌停",
    "流动性不足",
    "价格不可靠",
    "数据异常",
)


def build_opportunity_dossier(
    pool: CandidatePoolReport,
    *,
    market: MarketRegimeAssessment,
    quote_status: EvidenceStatus,
    candidate_universe: list[CandidateStockRawData],
    metadata: dict[str, str],
) -> OpportunityDossier:
    raw_by_code = {item.code: item for item in candidate_universe}
    blocked = quote_status in {EvidenceStatus.STALE, EvidenceStatus.BLOCKED}
    blocked = blocked or market.stage == "数据暂停" or market.risk_budget == "0%"
    pool_blocked = blocked or not pool.price_reliable
    decisions = [
        _candidate_decision(
            item,
            raw=raw_by_code.get(item.code),
            trade_date=pool.trade_date,
            blocked=pool_blocked,
            quote_status=quote_status,
        )
        for item in pool.candidates
    ]
    if not pool_blocked:
        decisions.sort(key=lambda item: (_STATE_PRIORITY[item.state], -_score(pool, item.code)))

    eligible_count = sum(item.state == "可验证" for item in decisions)
    evidence_ready_count = sum(
        item.data_status is EvidenceStatus.COMPLETE and bool(item.evidence)
        for item in decisions
    )
    scanned_count = _scanned_count(metadata)
    risks = _risk_register(decisions, market=market, blocked=pool_blocked)
    gate = _gate(
        market=market,
        blocked=pool_blocked,
        quote_status=quote_status,
        scanned_count=scanned_count,
        evidence_ready_count=evidence_ready_count,
        eligible_count=eligible_count,
    )
    funnel = _funnel(
        scanned_count=scanned_count,
        decisions=decisions,
        evidence_ready_count=evidence_ready_count,
    )
    source_notes = tuple(
        [*pool.method_notes, pool.disclaimer, *_metadata_notes(metadata)]
    )
    return OpportunityDossier(
        gate=gate,
        funnel=funnel,
        candidates=tuple(decisions),
        risks=risks,
        source_notes=source_notes,
    )


def _candidate_decision(
    item: CandidateStockAnalysis,
    *,
    raw: CandidateStockRawData | None,
    trade_date: str,
    blocked: bool,
    quote_status: EvidenceStatus,
) -> CandidateDecision:
    price_reliable = item.price_reliable and (raw is None or raw.price_reliable)
    explicit_exclusion = _explicit_exclusion(item)
    if blocked:
        state = "待补数据"
        data_status = (
            quote_status
            if quote_status in {EvidenceStatus.STALE, EvidenceStatus.BLOCKED}
            else EvidenceStatus.BLOCKED
        )
    elif not price_reliable:
        state = "待补数据"
        data_status = EvidenceStatus.MISSING
    elif explicit_exclusion:
        state = "风险排除"
        data_status = EvidenceStatus.COMPLETE
    elif item.score >= 70 and item.sector not in {"", "未识别主题"}:
        state = "可验证"
        data_status = EvidenceStatus.COMPLETE
    else:
        state = "只观察"
        data_status = EvidenceStatus.COMPLETE

    exclusion_reason = explicit_exclusion
    if state == "待补数据":
        exclusion_reason = "行情或候选价格证据未通过，不能参与当前排序"
    next_verification = {
        "可验证": "进入个股档案复核财务、估值、事件风险与价格触发",
        "只观察": "等待板块、量价或事件证据补强后再评估",
        "风险排除": "先解除明确风险，不进入当前研究前排",
        "待补数据": "刷新最近交易日行情与候选证据后重新分类",
    }[state]
    return CandidateDecision(
        code=item.code,
        name=item.name,
        sector=item.sector or "未识别主题",
        state=state,
        strategy=_strategy(item),
        evidence=tuple(item.reasons[:3]) or ("缺少可用支持证据",),
        counter_evidence=tuple(item.risks[:3]) or ("缺少独立反证，仍需复核公告与流动性",),
        data_date=trade_date,
        data_status=data_status,
        next_verification=next_verification,
        exclusion_reason=exclusion_reason,
    )


def _explicit_exclusion(item: CandidateStockAnalysis) -> str:
    if item.name.upper().startswith("ST") or "退" in item.name[:2]:
        return "ST/退市风险标的，不进入当前研究前排"
    text = "；".join(item.risks)
    marker = next((value for value in _EXCLUSION_MARKERS if value in text), "")
    return f"命中明确排除项：{marker}" if marker else ""


def _strategy(item: CandidateStockAnalysis) -> str:
    reason_text = "；".join(item.reasons)
    if "放量" in reason_text or "突破" in reason_text:
        return "放量突破"
    if item.pct_change < -3:
        return "超跌修复"
    if item.score >= 75:
        return "主线强势与资金承接"
    return "主线观察"


def _gate(
    *,
    market: MarketRegimeAssessment,
    blocked: bool,
    quote_status: EvidenceStatus,
    scanned_count: int | None,
    evidence_ready_count: int,
    eligible_count: int,
) -> OpportunityGate:
    if blocked:
        state = "数据暂停"
        action = "停止排序，只保留证据审计"
        thesis = "行情或候选数据闸门未通过，当前名单不能用于形成研究优先级。"
        next_step = "刷新最近交易日行情、候选价格和风险证据后重新生成漏斗。"
    elif eligible_count:
        state = "开放验证"
        action = f"仅验证 {eligible_count} 只证据较完整候选"
        thesis = f"市场阶段为{market.stage}，候选只获得进入个股档案复核的资格。"
        next_step = "逐只进入个股档案，确认财务、估值、事件和价格失效条件。"
    else:
        state = "只观察"
        action = "不形成前排候选"
        thesis = f"市场阶段为{market.stage}，当前候选证据尚不足以开放验证。"
        next_step = "等待板块扩散、量价承接或风险解除。"
    return OpportunityGate(
        state=state,
        action=action,
        risk_budget=market.risk_budget,
        data_status=quote_status.value,
        scanned_count=scanned_count,
        evidence_ready_count=evidence_ready_count,
        eligible_count=eligible_count,
        thesis=thesis,
        next_step=next_step,
    )


def _funnel(
    *,
    scanned_count: int | None,
    decisions: list[CandidateDecision],
    evidence_ready_count: int,
) -> tuple[FunnelStage, ...]:
    counts = {state: sum(item.state == state for item in decisions) for state in _STATE_PRIORITY}
    return (
        FunnelStage("扫描范围", scanned_count or 0, "audit", "全市场或配置候选源"),
        FunnelStage("证据就绪", evidence_ready_count, "evidence", "价格与支持证据可审计"),
        FunnelStage("风险排除", counts["风险排除"], "excluded", "明确风险先剔除"),
        FunnelStage("只观察", counts["只观察"] + counts["待补数据"], "watch", "等待确认或补数据"),
        FunnelStage("可验证", counts["可验证"], "eligible", "仅允许进入个股档案"),
    )


def _risk_register(
    decisions: list[CandidateDecision],
    *,
    market: MarketRegimeAssessment,
    blocked: bool,
) -> tuple[OpportunityRisk, ...]:
    risks = [
        OpportunityRisk(
            "市场闸门",
            "critical" if blocked else "high",
            market.primary_risk,
            "限制候选验证范围",
        ),
    ]
    risks.extend(
        OpportunityRisk("候选排除", "high", item.exclusion_reason, f"{item.name}不进入当前前排")
        for item in decisions
        if item.state == "风险排除"
    )
    if blocked:
        risks.append(
            OpportunityRisk(
                "数据质量",
                "critical",
                "行情或候选价格证据未通过",
                "停止排序并刷新数据",
            )
        )
    return tuple(risks)


def _scanned_count(metadata: dict[str, str]) -> int | None:
    value = metadata.get("universe_size") or metadata.get("scanned")
    try:
        return int(value) if value not in {None, ""} else None
    except (TypeError, ValueError):
        return None


def _metadata_notes(metadata: dict[str, str]) -> list[str]:
    return [
        f"{key}={value}"
        for key, value in sorted(metadata.items())
        if value not in {None, ""}
    ][:8]


def _score(pool: CandidatePoolReport, code: str) -> int:
    return next((item.score for item in pool.candidates if item.code == code), 0)
