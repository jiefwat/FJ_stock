from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from .analysis import analyze_stock
from .models import StockRawData
from .professional_analytics import (
    MarketPulse,
    StockEvidenceDimension,
    build_market_pulse,
    build_stock_evidence_matrix,
)
from .providers.base import StockDataProvider
from .research_engine import (
    ResearchContext,
    ResearchFact,
    ResearchFinding,
    ResearchModuleItem,
    ResearchModuleSection,
    ResearchWorkspaceResult,
)
from .workflows import (
    build_candidate_report,
    build_market_report,
    build_portfolio_report,
    build_sector_report,
)

FALLBACK_REASON = "实时研究暂不可用，已使用本地证据。"


def build_local_research(
    module: str,
    context: ResearchContext,
    *,
    provider: StockDataProvider,
    holdings_path: str | Path | None = None,
    opportunity_snapshot: dict[str, object] | None = None,
) -> ResearchWorkspaceResult:
    if module == "stock":
        try:
            return _build_stock_research(context, provider)
        except Exception:
            if opportunity_snapshot is not None:
                return _build_snapshot_stock_research(context, opportunity_snapshot)
            raise
    market = build_market_report(provider)
    sectors = build_sector_report(provider, market=market)
    if module == "market":
        return _build_market_research(provider, market, sectors)
    if module == "portfolio":
        portfolio = build_portfolio_report(
            provider,
            holdings_path=holdings_path,
            market=market,
            allow_empty=True,
        )
        return _build_portfolio_research(portfolio)
    if module == "opportunity":
        candidates = build_candidate_report(
            provider,
            market=market,
            sectors=sectors,
            limit=10,
        )
        return _build_opportunity_research(market, sectors, candidates)
    raise ValueError(f"unsupported local research module: {module}")


def _build_stock_research(
    context: ResearchContext,
    provider: StockDataProvider,
) -> ResearchWorkspaceResult:
    raw = _fetch_stock_raw(provider, context)
    report = analyze_stock(raw)
    evidence_matrix = build_stock_evidence_matrix(raw, report)
    industry = str(raw.fundamental_metrics.get("industry") or "").strip()
    items = (
        _stock_item(
            "财务质量",
            _fundamental_summary(raw.fundamental_metrics),
            bool(raw.fundamental_metrics),
        ),
        _stock_item("经营结构", "经营结构需要实时研究恢复后补充。", False),
        _stock_item("机构预期", "机构预期需要实时研究恢复后补充。", False),
        _stock_item("事件风险", _event_summary(raw), bool(raw.news_items or raw.announcements)),
        _stock_item("行情资金", _market_summary(report), True),
        _stock_item(
            "行业位置",
            f"当前行业归属：{industry}。行业相对位置待实时研究恢复后复核。"
            if industry
            else "行业归属与相对位置需要实时研究恢复后补充。",
            bool(industry),
        ),
        _stock_item("公告事项", _announcement_summary(raw.announcements), bool(raw.announcements)),
        _stock_item("研报观点", "研报观点需要实时研究恢复后补充。", False),
    )
    available_items = tuple(item for item in items if item.status == "ready")
    missing = tuple(item.label for item in items if item.status != "ready")
    findings = (
        ResearchFinding(
            title="价格与资金",
            summary=_market_summary(report),
            target=report.name,
            facts=(
                ResearchFact(label="最新收盘", value=f"{report.latest_close:.2f}"),
                ResearchFact(label="短期趋势", value=report.trend),
            ),
        ),
        ResearchFinding(
            title="主要限制",
            summary=_primary_constraint(raw, report),
            target=report.name,
        ),
        ResearchFinding(
            title="下一步验证",
            summary=report.decision.strengthen_condition,
            target=report.name,
        ),
    )
    evidence_items = tuple(
        _stock_evidence_item(item) for item in evidence_matrix.dimensions
    )
    sections = (
        ResearchModuleSection(
            key="stock-evidence",
            title="八维证据矩阵",
            conclusion=(
                "支持证据、反对证据和失效条件分开呈现；"
                f"当前整体可信度为{_confidence_label(evidence_matrix.confidence)}。"
            ),
            tone="negative" if evidence_matrix.hard_gate_reasons else "neutral",
            items=evidence_items,
        ),
    )
    generated_at = datetime.now().astimezone().isoformat(timespec="seconds")
    return ResearchWorkspaceResult(
        ok=True,
        status="partial",
        module="stock",
        generated_at=generated_at,
        verdict=(
            f"{report.name}当前为{evidence_matrix.decision_label}：{report.trend}，"
            f"先按{report.risk_level}风险级别处理，等待下一项确认。"
        ),
        action=evidence_matrix.action,
        primary_risk=evidence_matrix.primary_risk,
        findings=findings,
        missing_sections=missing,
        subject_count=1,
        coverage_ready=len(available_items),
        coverage_total=len(items),
        delivery="local_fallback",
        data_label="本地证据",
        fallback_reason=FALLBACK_REASON,
        as_of=report.latest_date,
        module_items=items,
        decision_label=evidence_matrix.decision_label,
        module_sections=sections,
    )


def _fetch_stock_raw(
    provider: StockDataProvider,
    context: ResearchContext,
) -> StockRawData:
    try:
        return provider.fetch_stock(context.code)
    except Exception as stock_error:
        target = _code_key(context.code)
        try:
            candidates = provider.fetch_candidate_universe()
        except Exception as candidate_error:
            raise stock_error from candidate_error
        candidate = next(
            (item for item in candidates if _code_key(item.code) == target),
            None,
        )
        if candidate is None:
            raise stock_error from None
        return StockRawData(
            code=candidate.code,
            name=candidate.name or context.name or candidate.code,
            bars=candidate.bars,
            fund_flow=candidate.fund_flow,
            pe_ttm=candidate.pe_ttm,
            fund_flow_detail={"source": "candidate_snapshot"},
            news_items=candidate.news_items,
            announcements=candidate.announcements,
            data_sources=["candidate_snapshot"],
        )


def _code_key(value: str) -> str:
    digits = "".join(character for character in value if character.isdigit())
    return digits[:6] or value.strip().upper()


def _build_snapshot_stock_research(
    context: ResearchContext,
    snapshot: dict[str, object],
) -> ResearchWorkspaceResult:
    raw_items = snapshot.get("module_items")
    items = raw_items if isinstance(raw_items, list) else []
    primary_candidate = next(
        (
            item
            for item in items
            if isinstance(item, dict)
            and _code_key(str(item.get("code") or "")) == _code_key(context.code)
        ),
        None,
    )
    nested_candidate = next(
        (
            item
            for item in _snapshot_section_items(snapshot)
            if _code_key(str(item.get("code") or "")) == _code_key(context.code)
        ),
        None,
    )
    candidate = primary_candidate or nested_candidate
    if candidate is None:
        raise ValueError(f"opportunity snapshot missing stock {context.code}")
    name = str(candidate.get("name") or context.name or context.code)
    theme = str(
        (nested_candidate or {}).get("label")
        or candidate.get("label")
        or "主题待确认"
    )
    summary = str(candidate.get("summary") or "候选入选依据待补。")
    risk = str(candidate.get("risk") or "候选失效条件待补。")
    module_items = (
        _stock_item("财务质量", "独立财务快照待补。", False),
        _stock_item("经营结构", "经营结构需要实时研究恢复后补充。", False),
        _stock_item("机构预期", "机构预期需要实时研究恢复后补充。", False),
        _stock_item("事件风险", "事件风险需要实时研究恢复后补充。", False),
        _stock_item("行情资金", summary, True),
        _stock_item("行业位置", f"当前候选主题：{theme}。", True),
        _stock_item("公告事项", "公告事项需要实时研究恢复后补充。", False),
        _stock_item("研报观点", "研报观点需要实时研究恢复后补充。", False),
    )
    findings = (
        ResearchFinding(
            title="候选依据",
            summary=summary,
            target=name,
        ),
        ResearchFinding(
            title="主题位置",
            summary=f"当前归入{theme}，主题持续性仍需复核。",
            target=name,
        ),
        ResearchFinding(
            title="下一步验证",
            summary="补齐独立行情、财务和事件证据后，再判断是否继续跟踪。",
            target=name,
        ),
    )
    generated_at = datetime.now().astimezone().isoformat(timespec="seconds")
    return ResearchWorkspaceResult(
        ok=True,
        status="partial",
        module="stock",
        generated_at=generated_at,
        verdict=f"{name}当前仅有候选快照；独立行情与财务补齐前保持等待确认。",
        action="先核对候选入选依据，等待独立行情、财务和事件至少两项确认。",
        primary_risk=risk,
        findings=findings,
        missing_sections=tuple(
            item.label for item in module_items if item.status != "ready"
        ),
        subject_count=1,
        coverage_ready=2,
        coverage_total=8,
        delivery="local_fallback",
        data_label="本地证据",
        fallback_reason=FALLBACK_REASON,
        as_of=str(snapshot.get("as_of") or snapshot.get("generated_at") or generated_at),
        module_items=module_items,
        decision_label="等待确认",
    )


def _snapshot_section_items(snapshot: dict[str, object]) -> list[dict[str, object]]:
    raw_sections = snapshot.get("module_sections")
    sections = raw_sections if isinstance(raw_sections, list) else []
    result: list[dict[str, object]] = []
    for section in sections:
        if not isinstance(section, dict):
            continue
        raw_items = section.get("items")
        if not isinstance(raw_items, list):
            continue
        result.extend(item for item in raw_items if isinstance(item, dict))
    return result


def _stock_item(label: str, summary: str, available: bool) -> ResearchModuleItem:
    return ResearchModuleItem(
        kind="stock_dimension",
        label=label,
        summary=summary,
        risk="证据待补，结论强度已降低。" if not available else "按条件验证，不作单点判断。",
        status="ready" if available else "missing",
    )


def _fundamental_summary(metrics: dict[str, Any]) -> str:
    if not metrics:
        return "财务质量需要实时研究恢复后补充。"
    labels = {
        "roe": "ROE",
        "revenue_yoy": "营收同比",
        "net_profit_yoy": "净利润同比",
        "gross_margin": "毛利率",
        "debt_to_assets": "资产负债率",
    }
    facts = []
    for key, label in labels.items():
        value = metrics.get(key)
        if value not in {None, ""}:
            suffix = "%" if isinstance(value, (int, float)) else ""
            facts.append(f"{label} {value}{suffix}")
    return "；".join(facts[:4]) or "已有财务快照，但关键指标仍需补充。"


def _market_summary(report: Any) -> str:
    fund = "资金数据待补"
    if report.fund_flow is not None:
        direction = "净流入" if report.fund_flow >= 0 else "净流出"
        fund = f"主力资金{direction} {abs(report.fund_flow):.2f} 亿元"
    return (
        f"最新收盘 {report.latest_close:.2f}，单日 {report.pct_change:+.2f}%，"
        f"短期为{report.trend}，{fund}。"
    )


def _event_summary(raw: Any) -> str:
    if raw.announcements:
        title = str(raw.announcements[0].get("title") or "最新公告")
        return f"最新事项：{title}。需核对其对盈利与预期的实际影响。"
    if raw.news_items:
        return f"最新公开信息：{raw.news_items[0].title}。需继续核对事实与影响。"
    return "近期事件证据不足，实时研究恢复后补充。"


def _announcement_summary(announcements: list[dict[str, object]]) -> str:
    if not announcements:
        return "公告事项需要实时研究恢复后补充。"
    latest = announcements[0]
    date = str(latest.get("date") or "日期待核对")
    title = str(latest.get("title") or "公告标题待核对")
    return f"{date}：{title}。"


def _primary_constraint(raw: Any, report: Any) -> str:
    if not raw.fundamental_metrics:
        return "财务与经营证据不完整，不能只按价格趋势行动。"
    if report.risk_level == "高":
        return "价格波动风险较高，确认信号出现前先控制风险暴露。"
    if raw.fundamental_metrics.get("net_profit_yoy") not in {None, ""}:
        value = raw.fundamental_metrics["net_profit_yoy"]
        if isinstance(value, (int, float)) and value < 0:
            return f"净利润同比 {value:.1f}%，盈利修复尚未确认。"
    return "机构预期与研报观点缺失，当前结论只用于条件复核。"


def _build_market_research(
    provider: StockDataProvider,
    market: Any,
    sectors: Any,
) -> ResearchWorkspaceResult:
    try:
        candidate_universe = provider.fetch_candidate_universe()
    except Exception:
        candidate_universe = []
    candidates = build_candidate_report(
        provider,
        market=market,
        sectors=sectors,
        limit=5,
    )
    pulse = build_market_pulse(market, sectors, candidate_universe)
    breadth = _breadth_item(market)
    index_items = tuple(
        ResearchModuleItem(
            kind="index",
            code=index.code,
            name=index.name,
            label="指数趋势",
            summary=f"收于 {index.close:.2f}，当日 {index.pct_chg:+.2f}%。",
            risk="指数上涨不代表所有主题同步走强。",
        )
        for index in market.indices
    )
    theme_items = tuple(_theme_item(item) for item in sectors.sectors[:5])
    hot_items = tuple(_candidate_item(item, kind="hot_stock") for item in candidates.candidates[:5])
    findings = (
        ResearchFinding(title="市场宽度", summary=breadth.summary),
        ResearchFinding(
            title="当前主线",
            summary=_join_or_default(sectors.market_mainline[:3], "主线尚未形成一致确认。"),
        ),
        ResearchFinding(
            title="退潮条件",
            summary=_join_or_default(market.risks[:2], "若上涨家数与成交同步回落，降低风险暴露。"),
        ),
    )
    sections = (
        ResearchModuleSection(
            key="market-pulse",
            title="市场脉搏",
            conclusion=_market_pulse_conclusion(pulse),
            tone=_pulse_tone(pulse),
            items=tuple(_market_pulse_item(item) for item in pulse.metrics),
        ),
        ResearchModuleSection(
            key="market-breadth",
            title="市场涨跌分布",
            conclusion=breadth.summary,
            tone=_market_tone(market),
            items=_breadth_items(market),
        ),
        ResearchModuleSection(
            key="market-themes",
            title="当前主题",
            conclusion=_join_or_default(sectors.market_mainline[:3], "当前主题仍在轮动。"),
            tone="positive" if theme_items else "neutral",
            items=theme_items,
        ),
        ResearchModuleSection(
            key="market-hot-stocks",
            title="热门股票",
            conclusion="只保留具备主题、价格与风险条件的代表股。",
            items=hot_items,
        ),
    )
    return _result(
        module="market",
        as_of=market.trade_date,
        verdict=_market_pulse_conclusion(pulse),
        action=(
            f"研究风险预算上限 {pulse.risk_budget}；"
            "先看前三主题能否扩散，再按市场宽度调整风险暴露。"
        ),
        risk=(
            "；".join(pulse.hard_gate_reasons)
            if pulse.hard_gate_reasons
            else _join_or_default(market.risks[:2], "主题快速轮动，避免只按单一热点行动。")
        ),
        findings=findings,
        items=index_items + hot_items,
        sections=sections,
        decision_label=_market_pulse_label(pulse.regime),
        subject_count=len(index_items) + len(hot_items),
    )


def _build_portfolio_research(portfolio: Any) -> ResearchWorkspaceResult:
    position_items = tuple(_position_item(position) for position in portfolio.positions)
    theme_items = tuple(
        ResearchModuleItem(
            kind="portfolio_theme",
            name=sector or "主题待确认",
            label="主题暴露",
            summary=f"该主题包含 {_sector_position_count(portfolio.positions, sector)} 只持仓。",
            risk="主题集中度需结合账户风险预算复核。",
        )
        for sector, _weight in portfolio.sector_weights[:8]
    )
    divergence_items = tuple(
        _divergence_item(portfolio.positions, sector)
        for sector in _divergent_sectors(portfolio.positions)
    )
    priority = sorted(
        portfolio.positions,
        key=lambda item: (_risk_rank(item.risk_level), -abs(item.daily_pnl_ratio)),
        reverse=True,
    )[:3]
    findings = tuple(
        ResearchFinding(
            title=f"优先处理：{item.holding.name}",
            summary=_position_summary(item),
            target=item.holding.name,
        )
        for item in priority
    )
    if not findings:
        findings = (
            ResearchFinding(
                title="持仓待录入",
                summary="当前账户没有可分析持仓，录入后将显示主题、分化与优先处理顺序。",
            ),
        )
    sections = (
        ResearchModuleSection(
            key="portfolio-themes",
            title="主题暴露",
            conclusion=_portfolio_theme_conclusion(portfolio),
            items=theme_items,
        ),
        ResearchModuleSection(
            key="portfolio-divergence",
            title="主题内分化",
            conclusion=(
                "同主题持仓表现已出现分化，先处理弱势与高风险标的。"
                if divergence_items
                else "当前没有足够的同主题持仓用于分化比较。"
            ),
            items=divergence_items,
        ),
    )
    return _result(
        module="portfolio",
        as_of=portfolio.trade_date,
        verdict=_portfolio_verdict(portfolio),
        action=_join_or_default(
            portfolio.action_checklist[:2],
            "先处理高风险持仓，再观察主题确认。",
        ),
        risk=_join_or_default(portfolio.risk_alerts[:2], "持仓数据不完整时只作风险排序。"),
        findings=findings,
        items=position_items,
        sections=sections,
        decision_label=_portfolio_decision_label(portfolio),
        subject_count=len(position_items),
    )


def _build_opportunity_research(
    market: Any,
    sectors: Any,
    candidates: Any,
) -> ResearchWorkspaceResult:
    theme_items = tuple(_theme_item(item) for item in sectors.sectors[:5])
    candidate_items = tuple(_candidate_item(item) for item in candidates.candidates[:10])
    findings = tuple(
        ResearchFinding(
            title=f"候选：{item.name}",
            summary=(item.reasons[0] if item.reasons else "候选证据待核对。"),
            target=item.name,
        )
        for item in candidates.candidates[:3]
    )
    sections = (
        ResearchModuleSection(
            key="opportunity-themes",
            title="主线主题",
            conclusion=_join_or_default(sectors.market_mainline[:3], "当前没有确认度足够的主线。"),
            items=theme_items,
        ),
        ResearchModuleSection(
            key="opportunity-candidates",
            title="候选与验证",
            conclusion="候选必须同时通过主题持续、价格确认和风险排除。",
            items=candidate_items,
        ),
    )
    return _result(
        module="opportunity",
        as_of=candidates.trade_date,
        verdict=(
            f"当前保留 {len(candidate_items)} 只条件候选，"
            f"优先围绕{_first_theme(sectors)}做验证。"
        ),
        action="先确认主题持续性，再逐只等待价格与成交条件，不追逐临时脉冲。",
        risk=_join_or_default(sectors.risk_notes[:2], "热点强度可能快速衰减，候选不等于交易信号。"),
        findings=findings,
        items=candidate_items,
        sections=sections,
        decision_label="条件观察" if candidate_items else "暂停筛选",
        subject_count=len(candidate_items),
    )


def _result(
    *,
    module: str,
    as_of: str,
    verdict: str,
    action: str,
    risk: str,
    findings: tuple[ResearchFinding, ...],
    items: tuple[ResearchModuleItem, ...],
    sections: tuple[ResearchModuleSection, ...],
    decision_label: str,
    subject_count: int,
) -> ResearchWorkspaceResult:
    generated_at = datetime.now().astimezone().isoformat(timespec="seconds")
    return ResearchWorkspaceResult(
        ok=True,
        status="partial",
        module=module,
        generated_at=generated_at,
        verdict=verdict,
        action=action,
        primary_risk=risk,
        findings=findings,
        subject_count=subject_count,
        coverage_ready=len(items),
        coverage_total=len(items),
        delivery="local_fallback",
        data_label="本地证据",
        fallback_reason=FALLBACK_REASON,
        as_of=as_of,
        module_items=items,
        decision_label=decision_label,
        module_sections=sections,
    )


def _breadth_item(market: Any) -> ResearchModuleItem:
    total = market.advancing_count + market.declining_count + market.unchanged_count
    summary = (
        f"上涨 {market.advancing_count} 家，下跌 {market.declining_count} 家，"
        f"平盘 {market.unchanged_count} 家；涨停 {market.limit_up_count} 家，"
        f"跌停 {market.limit_down_count} 家。"
    )
    return ResearchModuleItem(
        kind="breadth",
        label="涨跌分布",
        summary=summary if total else "全市场涨跌分布待补。",
        risk="若上涨家数与涨停数同步回落，视为扩散减弱。",
        status="ready" if total else "missing",
    )


def _breadth_items(market: Any) -> tuple[ResearchModuleItem, ...]:
    total = market.advancing_count + market.declining_count + market.unchanged_count
    values = (
        ("上涨家数", market.advancing_count),
        ("下跌家数", market.declining_count),
        ("平盘家数", market.unchanged_count),
        ("涨停家数", market.limit_up_count),
        ("跌停家数", market.limit_down_count),
    )
    return tuple(
        ResearchModuleItem(
            kind="breadth_metric",
            name=label,
            label="全市场统计",
            summary=str(value),
            risk="全市场家数口径" if total else "全市场涨跌家数待补。",
            status="ready" if total else "missing",
        )
        for label, value in values
    )


def _market_pulse_item(metric: Any) -> ResearchModuleItem:
    return ResearchModuleItem(
        kind="market_metric",
        name=metric.label,
        label=metric.label,
        summary=metric.value,
        risk=metric.interpretation,
        status="missing" if metric.value == "待补" else "ready",
        facts=(ResearchFact(label="状态", value=_tone_label(metric.tone)),),
    )


def _market_pulse_conclusion(pulse: MarketPulse) -> str:
    label = _market_pulse_label(pulse.regime)
    return (
        f"当前市场为{label}，研究风险预算上限 {pulse.risk_budget}；"
        f"涨跌宽度比 {pulse.breadth_ratio:.2f}，确认主题 {pulse.confirmed_theme_count} 个。"
    )


def _market_pulse_label(regime: str) -> str:
    return {
        "risk_off": "风险关闭",
        "defensive": "防守",
        "balanced": "均衡",
        "constructive": "结构进攻",
        "risk_on": "风险开启",
    }.get(regime, "待确认")


def _pulse_tone(pulse: MarketPulse) -> str:
    if pulse.regime in {"risk_on", "constructive"}:
        return "positive"
    if pulse.regime in {"risk_off", "defensive"}:
        return "negative"
    return "neutral"


def _tone_label(tone: str) -> str:
    return {
        "positive": "偏强",
        "negative": "偏弱",
        "caution": "待确认",
    }.get(tone, "中性")


def _stock_evidence_item(item: StockEvidenceDimension) -> ResearchModuleItem:
    return ResearchModuleItem(
        kind="stock_evidence",
        name=item.name,
        label=item.name,
        summary="；".join(item.supporting_evidence),
        risk="反对证据：" + "；".join(item.counter_evidence),
        status="ready" if item.coverage == "ready" else item.coverage,
        facts=(
            ResearchFact(label="评分", value=f"{item.score}/100"),
            ResearchFact(label="可信度", value=_confidence_label(item.confidence)),
            ResearchFact(label="转强条件", value=item.strengthen_condition),
            ResearchFact(label="失效条件", value=item.invalidation_condition),
        ),
    )


def _confidence_label(confidence: str) -> str:
    return {
        "high": "高",
        "medium": "中",
        "low": "低",
        "blocked": "阻断",
    }.get(confidence, "低")


def _theme_item(sector: Any) -> ResearchModuleItem:
    return ResearchModuleItem(
        kind="theme",
        name=sector.name,
        label="主线主题",
        summary=(
            f"涨幅 {sector.pct_chg:+.2f}%，热度 {sector.heat_score}，"
            f"上涨占比 {sector.advancing_ratio:.0%}，{sector.continuity}。"
        ),
        risk=sector.risk,
        status="ready",
    )


def _candidate_item(candidate: Any, *, kind: str = "candidate") -> ResearchModuleItem:
    confirm = (
        candidate.watch_conditions[0]
        if candidate.watch_conditions
        else "等待价格与成交确认。"
    )
    invalidate = candidate.risks[0] if candidate.risks else "主题强度回落则移出观察。"
    reason = candidate.reasons[0] if candidate.reasons else "候选证据待复核。"
    return ResearchModuleItem(
        kind=kind,
        code=candidate.code,
        name=candidate.name,
        label=candidate.sector or "主题待确认",
        summary=f"观察分 {candidate.score}；入选：{reason}；确认：{confirm}",
        risk=f"淘汰条件：{invalidate}",
        status="ready",
    )


def _position_item(position: Any) -> ResearchModuleItem:
    return ResearchModuleItem(
        kind="holding",
        code=position.holding.code,
        name=position.holding.name,
        label=position.holding.sector or "主题待确认",
        summary=_position_summary(position),
        risk=f"风险级别：{position.risk_level}；弱于主题时优先复核。",
        status="ready",
    )


def _position_summary(position: Any) -> str:
    if position.daily_pnl_ratio > 0:
        direction = "走强"
    elif position.daily_pnl_ratio < 0:
        direction = "走弱"
    else:
        direction = "持平"
    return f"当前{position.trend}，日内{direction}，风险级别{position.risk_level}。"


def _divergence_item(positions: list[Any], sector: str) -> ResearchModuleItem:
    members = [item for item in positions if (item.holding.sector or "主题待确认") == sector]
    strongest = max(members, key=lambda item: item.daily_pnl_ratio)
    weakest = min(members, key=lambda item: item.daily_pnl_ratio)
    return ResearchModuleItem(
        kind="theme_divergence",
        name=sector,
        label="主题内分化",
        summary=f"{strongest.holding.name}相对偏强，{weakest.holding.name}相对偏弱。",
        risk="若弱势成员持续落后主题，优先降低其处理优先级。",
    )


def _divergent_sectors(positions: list[Any]) -> tuple[str, ...]:
    counts: dict[str, int] = {}
    for item in positions:
        sector = item.holding.sector or "主题待确认"
        counts[sector] = counts.get(sector, 0) + 1
    return tuple(sector for sector, count in counts.items() if count >= 2)


def _sector_position_count(positions: list[Any], sector: str) -> int:
    return sum(1 for item in positions if item.holding.sector == sector)


def _portfolio_verdict(portfolio: Any) -> str:
    if not portfolio.positions:
        return "当前没有可分析持仓，先完成持仓录入。"
    high_risk = sum(1 for item in portfolio.positions if item.risk_level == "高")
    if high_risk:
        return f"组合先处理风险：{high_risk} 只持仓处于高风险状态。"
    return f"组合健康度 {portfolio.health_score}，先检查主题集中与弱势持仓。"


def _portfolio_theme_conclusion(portfolio: Any) -> str:
    if not portfolio.sector_weights:
        return "主题数据待补，当前只做逐只风险复核。"
    names = [name or "主题待确认" for name, _weight in portfolio.sector_weights[:3]]
    return f"主要暴露在{'、'.join(names)}，优先检查主题是否同向。"


def _portfolio_decision_label(portfolio: Any) -> str:
    if not portfolio.positions:
        return "待录入"
    if any(item.risk_level == "高" for item in portfolio.positions):
        return "先降风险"
    return "逐只复核"


def _market_tone(market: Any) -> str:
    if market.advancing_count > market.declining_count:
        return "positive"
    if market.declining_count > market.advancing_count:
        return "warning"
    return "neutral"


def _first_theme(sectors: Any) -> str:
    if sectors.sectors:
        return sectors.sectors[0].name
    return "待确认主题"


def _risk_rank(level: str) -> int:
    return {"高": 3, "中": 2, "低": 1}.get(level, 0)


def _join_or_default(items: list[str], default: str) -> str:
    cleaned = [str(item).strip() for item in items if str(item).strip()]
    return "；".join(cleaned) if cleaned else default
