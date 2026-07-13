from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from stock_ts.models import FundamentalPeriod, Holding, StockRawData

from .evidence import (
    EvidenceItem,
    EvidenceStatus,
    ResearchInputQuality,
    fundamental_metric_coverage,
    has_comparable_valuation,
    has_usable_events,
)


@dataclass(frozen=True)
class ResearchSection:
    title: str
    conclusion: str
    facts: tuple[str, ...]
    limitations: str
    next_checks: tuple[str, ...] = ()


@dataclass(frozen=True)
class ResearchScenario:
    name: str
    premises: str
    signals: str
    action: str
    invalidation: str


@dataclass(frozen=True)
class ResearchVerdict:
    status: str
    confidence: int
    core_conflict: str
    strongest_evidence: str
    strongest_counter_evidence: str
    next_review: str


@dataclass(frozen=True)
class StockResearchMemo:
    code: str
    name: str
    trade_date: str
    latest_close: float
    verdict: ResearchVerdict
    business: ResearchSection
    quality: ResearchSection
    valuation: ResearchSection
    expectation_gap: ResearchSection
    technical: ResearchSection
    capital: ResearchSection
    events: ResearchSection
    portfolio: ResearchSection
    scenarios: tuple[ResearchScenario, ...]
    evidence: tuple[EvidenceItem, ...]


def build_stock_research_memo(
    raw: StockRawData,
    *,
    holding: Holding | None = None,
    technical: Any | None = None,
    event_radar: Any | None = None,
    input_quality: ResearchInputQuality | None = None,
) -> StockResearchMemo:
    latest = raw.bars[-1] if raw.bars else None
    trade_date = latest.date if latest else ""
    latest_close = latest.close if latest else 0.0
    fundamental_history = tuple(
        item
        for item in sorted(raw.fundamental_history, key=lambda item: item.date, reverse=True)
        if fundamental_metric_coverage(_period_metrics(item)) > 0
    )
    quality_metrics = _quality_metrics(raw, fundamental_history)
    fundamental_period_count = (
        len(fundamental_history)
        if fundamental_history
        else int(fundamental_metric_coverage(quality_metrics) > 0)
    )
    effective_valuation, valuation_observation_count = _effective_valuation(raw)
    quality_gate = input_quality or _derive_input_quality(
        raw,
        quality_metrics=quality_metrics,
        effective_valuation=effective_valuation,
    )
    quality = _quality_section(quality_metrics, fundamental_history)
    valuation = _valuation_section(
        raw,
        effective_valuation,
        valuation_observation_count,
    )
    events = _event_section(raw, event_radar)
    evidence = _evidence_items(
        raw,
        holding,
        trade_date,
        quality,
        valuation,
        events,
        quality_gate,
        fundamental_period_count,
    )
    verdict = _verdict(
        quality,
        valuation,
        events,
        quality_gate,
        fundamental_period_count=fundamental_period_count,
    )
    scenarios = (
        _paused_scenarios()
        if quality_gate.quote_status in {EvidenceStatus.STALE, EvidenceStatus.BLOCKED}
        else _scenarios(raw, quality, events)
    )
    return StockResearchMemo(
        code=raw.code,
        name=raw.name,
        trade_date=trade_date,
        latest_close=latest_close,
        verdict=verdict,
        business=_business_section(raw),
        quality=quality,
        valuation=valuation,
        expectation_gap=_expectation_section(raw, quality, events),
        technical=_technical_section(raw, technical),
        capital=_capital_section(raw),
        events=events,
        portfolio=_portfolio_section(holding, latest_close),
        scenarios=scenarios,
        evidence=evidence,
    )


def _derive_input_quality(
    raw: StockRawData,
    *,
    quality_metrics: dict[str, float | str | None],
    effective_valuation: dict[str, float | str | None],
) -> ResearchInputQuality:
    return ResearchInputQuality(
        quote_status=EvidenceStatus.COMPLETE if raw.bars else EvidenceStatus.BLOCKED,
        fundamental_coverage=fundamental_metric_coverage(quality_metrics),
        valuation_comparable=has_comparable_valuation(
            effective_valuation,
            pe_ttm=raw.pe_ttm,
        ),
        event_status=(
            EvidenceStatus.DEGRADED
            if has_usable_events(raw.announcements, raw.news_items)
            else EvidenceStatus.MISSING
        ),
        blockers=("缺少 K 线",) if not raw.bars else (),
    )


def _quality_metrics(
    raw: StockRawData,
    history: tuple[FundamentalPeriod, ...],
) -> dict[str, float | str | None]:
    if fundamental_metric_coverage(raw.fundamental_metrics) > 0:
        return dict(raw.fundamental_metrics)
    return _period_metrics(history[0]) if history else dict(raw.fundamental_metrics)


def _period_metrics(period: FundamentalPeriod) -> dict[str, float | str | None]:
    return {
        "date": period.date,
        "source": period.source,
        "revenue_yoy": period.revenue_yoy,
        "net_profit_yoy": period.net_profit_yoy,
        "roe": period.roe,
        "gross_margin": period.gross_margin,
        "debt_to_assets": period.debt_to_assets,
        "ocf_to_profit": period.ocf_to_profit,
    }


def _effective_valuation(
    raw: StockRawData,
) -> tuple[dict[str, float | str | None], int]:
    valuation = dict(raw.valuation)
    points_by_date = {item.date: item for item in raw.valuation_history if item.date}
    valid_points = [
        item.pe_ttm
        for item in points_by_date.values()
        if item.pe_ttm is not None and math.isfinite(item.pe_ttm) and item.pe_ttm > 0
    ]
    explicit = _number(valuation.get("pe_percentile"))
    explicit_valid = explicit is not None and 0 <= explicit <= 100
    current = raw.pe_ttm if raw.pe_ttm is not None else _number(valuation.get("pe_ttm"))
    if (
        not explicit_valid
        and current is not None
        and math.isfinite(current)
        and current > 0
        and len(valid_points) >= 20
    ):
        valuation["pe_percentile"] = (
            sum(point <= current for point in valid_points) / len(valid_points) * 100
        )
        valuation["pe_percentile_basis"] = len(valid_points)
    return valuation, len(valid_points)


def _business_section(raw: StockRawData) -> ResearchSection:
    sector = str(raw.fundamental_metrics.get("industry") or "行业定位待补")
    business = str(raw.fundamental_metrics.get("business_summary") or "主营业务结构待补")
    return ResearchSection(
        "公司与生意",
        f"{raw.name}：{business}；{sector}。",
        (f"证券代码 {raw.code}", f"已识别行业 {sector}"),
        "缺少业务分部与收入来源时，只能确认证券身份，不能推导竞争优势。",
        ("补充主营构成、客户集中度和行业位置",),
    )


def _quality_section(
    metrics: dict[str, float | str | None],
    history: tuple[FundamentalPeriod, ...],
) -> ResearchSection:
    period_count = len(history) if history else int(fundamental_metric_coverage(metrics) > 0)
    if fundamental_metric_coverage(metrics) == 0:
        return ResearchSection(
            "经营质量",
            "经营质量数据缺失，不能判断盈利能力和现金流质量。",
            (),
            f"财务 {period_count} 期；缺少营收、利润、ROE、负债与经营现金流字段。",
            ("补充最近财报和至少一个可比期间",),
        )
    revenue = _number(metrics.get("revenue_yoy"))
    profit = _number(metrics.get("net_profit_yoy"))
    roe = _number(metrics.get("roe"))
    margin = _number(metrics.get("gross_margin"))
    debt = _number(metrics.get("debt_to_assets"))
    cash_match = _number(metrics.get("ocf_to_profit"))
    facts = tuple(
        text
        for text in (
            _metric("营收同比", revenue, "%"),
            _metric("净利润同比", profit, "%"),
            _metric("ROE", roe, "%"),
            _metric("毛利率", margin, "%"),
            _metric("资产负债率", debt, "%"),
            _metric("经营现金流/利润", cash_match, ""),
        )
        if text
    )
    history_conclusion = _fundamental_history_conclusion(history)
    if history_conclusion:
        conclusion = history_conclusion
    elif revenue is not None and profit is not None and profit > revenue:
        conclusion = "盈利增速高于收入增速，但仍需拆解利润质量和基数影响。"
    elif revenue is not None and profit is not None and profit < revenue:
        conclusion = "利润增速落后于收入增速，盈利质量需要重点复核。"
    else:
        conclusion = "已有部分经营指标，但不足以形成完整盈利质量判断。"
    if period_count >= 3:
        limitation = f"财务 {period_count} 期；跨期方向仍需结合基数和报告口径复核。"
    elif period_count == 2:
        limitation = "财务 2 期；仅能描述较上一期变化，不能声称长期趋势。"
    else:
        limitation = "财务 1 期；单期数据只能描述当前截面，不能声称趋势改善或恶化。"
    return ResearchSection(
        "经营质量",
        conclusion,
        facts,
        limitation,
        ("对比最近四个报告期", "核对经营现金流与净利润匹配度"),
    )


def _fundamental_history_conclusion(
    history: tuple[FundamentalPeriod, ...],
) -> str:
    recent = history[:3]
    if len(recent) < 2:
        return ""
    chronological = tuple(reversed(recent))
    revenues = [item.revenue_yoy for item in chronological]
    profits = [item.net_profit_yoy for item in chronological]
    if any(value is None for value in (*revenues, *profits)):
        return ""
    revenue_values = [float(value) for value in revenues if value is not None]
    profit_values = [float(value) for value in profits if value is not None]
    if len(recent) == 2:
        return (
            f"较上一期变化：营收同比 {revenue_values[0]:.2f}% -> "
            f"{revenue_values[-1]:.2f}%，净利润同比 {profit_values[0]:.2f}% -> "
            f"{profit_values[-1]:.2f}%。"
        )
    revenue_direction = _strict_direction(revenue_values)
    profit_direction = _strict_direction(profit_values)
    if revenue_direction == profit_direction == "improving":
        return "最近三期营收与净利润增速连续改善，但仍需复核基数和现金流质量。"
    if revenue_direction == profit_direction == "weakening":
        return "最近三期营收与净利润增速连续走弱，经营压力需要优先复核。"
    if revenue_direction != profit_direction:
        return "最近三期收入与利润增速分化，不能把单一利润改善视为整体经营改善。"
    return "最近三期经营增速波动，尚未形成一致方向。"


def _strict_direction(values: list[float]) -> str:
    if len(values) < 3:
        return "insufficient"
    pairs = zip(values, values[1:])
    if all(current > previous for previous, current in pairs):
        return "improving"
    pairs = zip(values, values[1:])
    if all(current < previous for previous, current in pairs):
        return "weakening"
    return "mixed"


def _valuation_section(
    raw: StockRawData,
    valuation: dict[str, float | str | None],
    observation_count: int,
) -> ResearchSection:
    pe = raw.pe_ttm if raw.pe_ttm is not None else _number(valuation.get("pe_ttm"))
    pb = _number(valuation.get("pb"))
    ps = _number(valuation.get("ps"))
    percentile = _number(valuation.get("pe_percentile"))
    percentile_basis = int(_number(valuation.get("pe_percentile_basis")) or 0)
    industry_median = _number(valuation.get("industry_pe_median"))
    facts = tuple(
        text
        for text in (_metric("PE(TTM)", pe, "x"), _metric("PB", pb, "x"), _metric("PS", ps, "x"))
        if text
    )
    if percentile is not None and 0 <= percentile <= 100:
        if percentile_basis >= 20:
            conclusion = (
                f"基于 {percentile_basis} 个观察点的 PE 历史分位 {percentile:.0f}%，"
                "估值判断具备内部历史参照。"
            )
            limitation = "内部历史分位仍需结合盈利周期、样本跨度和口径变化。"
        else:
            conclusion = f"PE 历史分位 {percentile:.0f}%，估值判断具备历史参照。"
            limitation = "提供方历史分位仍需结合盈利周期和口径变化。"
    elif industry_median is not None and industry_median > 0 and pe is not None and pe > 0:
        conclusion = f"PE {pe:.2f}x，对比行业中位数 {industry_median:.2f}x。"
        limitation = "行业对比不能替代公司盈利质量和增长持续性判断。"
    else:
        conclusion = "；".join(facts) if facts else "估值字段缺失。"
        limitation = (
            "缺少历史分位或行业对比，只描述绝对估值水平；"
            f"估值历史积累中 {observation_count}/20。"
        )
    return ResearchSection(
        "估值与预期",
        conclusion,
        facts,
        limitation,
        ("补充历史估值分位", "补充同行可比公司中位数"),
    )


def _expectation_section(
    raw: StockRawData, quality: ResearchSection, events: ResearchSection
) -> ResearchSection:
    catalysts = [item.title for item in raw.news_items[:2]]
    facts = tuple(catalysts) or (quality.conclusion, events.conclusion)
    return ResearchSection(
        "预期差",
        "当前只能从经营、事件与价格证据反推市场预期，尚无一致预期数据。",
        facts,
        "未接入盈利一致预期，不能量化预期上修或下修幅度。",
        ("跟踪业绩预告和机构盈利预测变化",),
    )


def _technical_section(raw: StockRawData, technical: Any | None) -> ResearchSection:
    if not raw.bars:
        return ResearchSection("技术结构", "K 线缺失。", (), "不能判断趋势和关键位置。")
    latest = raw.bars[-1]
    if technical is not None:
        conclusion = str(getattr(technical, "structure", "技术结构待确认"))
        facts = (
            f"支撑 {getattr(technical, 'support', latest.low):.2f}",
            f"压力 {getattr(technical, 'resistance', latest.high):.2f}",
        )
    else:
        conclusion = "价格结构可用，专业支撑压力由技术模块补充。"
        facts = (f"收盘 {latest.close:.2f}", f"成交量 {latest.volume:.0f}")
    return ResearchSection(
        "技术结构",
        conclusion,
        facts,
        "技术结构只定义触发与失效，不能证明公司质量。",
    )


def _capital_section(raw: StockRawData) -> ResearchSection:
    if raw.fund_flow is None and not raw.fund_flow_detail:
        return ResearchSection(
            "资金行为",
            "真实资金流字段缺失。",
            (),
            "成交量代理不等同于主力净流入。",
            ("补充分级资金流和换手率",),
        )
    facts = []
    if raw.fund_flow is not None:
        facts.append(f"资金净流 {raw.fund_flow:+.2f}")
    facts.extend(f"{key}={value}" for key, value in list(raw.fund_flow_detail.items())[:3])
    return ResearchSection(
        "资金行为",
        "资金字段可用，需与价格和板块承接共同验证。",
        tuple(facts),
        "单日资金流不能证明持续性。",
    )


def _event_section(raw: StockRawData, event_radar: Any | None) -> ResearchSection:
    titles = [str(item.get("title", "")) for item in raw.announcements if item.get("title")]
    titles.extend(item.title for item in raw.news_items[:3])
    if not titles:
        return ResearchSection(
            "事件与公告",
            "新闻公告缺失，不能确认催化或排除事件风险。",
            (),
            "缺少事件数据。",
            ("补充巨潮公告并打开原文复核",),
        )
    risk = "；".join(
        title
        for title in titles
        if any(word in title for word in ("减持", "诉讼", "监管", "质押"))
    )
    conclusion = f"发现需优先复核的事件：{risk}" if risk else "未见标题级高风险词。"
    if event_radar is not None and getattr(event_radar, "gate", ""):
        conclusion = f"{conclusion} 事件闸门：{event_radar.gate}。"
    return ResearchSection(
        "事件与公告",
        conclusion,
        tuple(titles[:5]),
        "当前为标题级风险扫描，未代替原文复核。",
        ("打开公告原文核对金额、期限和适用条件",),
    )


def _portfolio_section(holding: Holding | None, latest_close: float) -> ResearchSection:
    if holding is None:
        return ResearchSection(
            "组合上下文",
            "当前未持仓，只评估研究价值，不生成持仓处置动作。",
            (),
            "无持仓成本与组合集中度上下文。",
        )
    pnl = (latest_close / holding.cost_price - 1) * 100 if holding.cost_price else 0.0
    return ResearchSection(
        "组合上下文",
        f"已持仓 {holding.shares:g} 股，成本 {holding.cost_price:.2f}，当前相对成本 {pnl:+.1f}%。",
        (f"行业 {holding.sector or '未分类'}",),
        "尚未获得账户总资产，不能计算真实组合风险占用。",
        ("结合组合集中度决定风险预算",),
    )


def _verdict(
    quality: ResearchSection,
    valuation: ResearchSection,
    events: ResearchSection,
    quality_gate: ResearchInputQuality,
    *,
    fundamental_period_count: int,
) -> ResearchVerdict:
    if quality_gate.quote_status in {EvidenceStatus.STALE, EvidenceStatus.BLOCKED}:
        blocker = quality_gate.blockers[0] if quality_gate.blockers else "行情时效未通过"
        return ResearchVerdict(
            status="数据暂停",
            confidence=0,
            core_conflict="行情时效未通过，当前价格与研究证据不在同一有效时点。",
            strongest_evidence="保留已有事实用于审计，不形成当前交易判断。",
            strongest_counter_evidence=blocker,
            next_review="刷新最近交易日行情后重新评估。",
        )

    has_fundamentals = quality_gate.fundamental_coverage > 0
    has_comparison = quality_gate.valuation_comparable
    has_events = quality_gate.event_status in {
        EvidenceStatus.COMPLETE,
        EvidenceStatus.DEGRADED,
    }
    missing_count = sum(not value for value in (has_fundamentals, has_comparison, has_events))
    status = "技术性观察" if missing_count >= 2 else "条件研究"
    depth_bonus = min(6, max(0, fundamental_period_count - 2) * 2)
    confidence = max(25, min(100, 78 - missing_count * 18 + depth_bonus))
    positive = quality.conclusion if has_fundamentals else "价格与技术数据可用于观察"
    counter = events.conclusion if has_events else valuation.limitations
    return ResearchVerdict(
        status=status,
        confidence=confidence,
        core_conflict="经营与事件证据能否支撑当前绝对估值和价格强度。",
        strongest_evidence=positive,
        strongest_counter_evidence=counter,
        next_review="补齐缺失证据，并在下一份财报或重大公告后重新评估。",
    )


def _scenarios(
    raw: StockRawData, quality: ResearchSection, events: ResearchSection
) -> tuple[ResearchScenario, ...]:
    return (
        ResearchScenario(
            "乐观",
            "盈利质量改善，事件无新增风险，价格与板块形成共振。",
            quality.conclusion,
            "进入条件观察，等待技术触发后再分配风险预算。",
            "利润增速转弱、现金流背离或关键位置失守。",
        ),
        ResearchScenario(
            "基准",
            "当前经营和价格证据延续，但缺失数据仍未补齐。",
            f"{raw.name}维持现有证据强度。",
            "保留研究跟踪，不因单一指标提高仓位。",
            "核心经营指标或事件判断发生方向性变化。",
        ),
        ResearchScenario(
            "悲观",
            "盈利质量恶化、资金转弱或出现重大风险事件。",
            events.conclusion,
            "降低研究优先级；已持仓时回到组合页评估风险。",
            "风险事件证伪且经营、价格证据同步修复。",
        ),
    )


def _paused_scenarios() -> tuple[ResearchScenario, ...]:
    return tuple(
        ResearchScenario(
            name,
            "行情时效恢复并与研究证据对齐。",
            "等待最近交易日价格、成交量和数据流水线通过校验。",
            "暂停形成交易判断，仅保留事实核对。",
            "行情仍过期或刷新后证据发生变化。",
        )
        for name in ("乐观", "基准", "悲观")
    )


def _evidence_items(
    raw: StockRawData,
    holding: Holding | None,
    trade_date: str,
    quality: ResearchSection,
    valuation: ResearchSection,
    events: ResearchSection,
    quality_gate: ResearchInputQuality,
    fundamental_period_count: int,
) -> tuple[EvidenceItem, ...]:
    source = ", ".join(raw.data_sources)
    if not raw.bars:
        quote_status = EvidenceStatus.BLOCKED
    else:
        quote_status = quality_gate.quote_status
    if quality_gate.fundamental_coverage <= 0:
        fundamental_status = EvidenceStatus.MISSING
    elif quality_gate.fundamental_coverage >= 1 and fundamental_period_count >= 3:
        fundamental_status = EvidenceStatus.COMPLETE
    else:
        fundamental_status = EvidenceStatus.DEGRADED
    latest_fundamental = (
        max(raw.fundamental_history, key=lambda item: item.date)
        if raw.fundamental_history
        else None
    )
    fundamental_source = str(raw.fundamental_metrics.get("source") or "") or (
        latest_fundamental.source if latest_fundamental else ""
    )
    fundamental_date = str(raw.fundamental_metrics.get("date") or "") or (
        latest_fundamental.date if latest_fundamental else ""
    )
    return (
        EvidenceItem(
            "行情",
            source,
            trade_date,
            quote_status,
            "日线价格与成交量" if raw.bars else "缺少 K 线",
        ),
        EvidenceItem(
            "经营质量",
            fundamental_source,
            fundamental_date,
            fundamental_status,
            quality.limitations,
        ),
        EvidenceItem(
            "估值",
            str(raw.valuation.get("source") or ""),
            str(raw.valuation.get("date") or trade_date),
            EvidenceStatus.COMPLETE
            if quality_gate.valuation_comparable
            else EvidenceStatus.DEGRADED,
            valuation.limitations,
        ),
        EvidenceItem(
            "资金",
            source,
            trade_date,
            EvidenceStatus.COMPLETE
            if raw.fund_flow is not None or raw.fund_flow_detail
            else EvidenceStatus.MISSING,
            "资金字段可用" if raw.fund_flow is not None or raw.fund_flow_detail else "资金字段缺失",
        ),
        EvidenceItem(
            "新闻公告",
            source,
            trade_date,
            quality_gate.event_status,
            events.limitations,
        ),
        EvidenceItem(
            "组合上下文",
            "local-holdings",
            trade_date,
            EvidenceStatus.COMPLETE if holding is not None else EvidenceStatus.MISSING,
            "已匹配持仓" if holding is not None else "未持仓",
        ),
    )


def _number(value: float | str | None) -> float | None:
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _metric(label: str, value: float | None, suffix: str) -> str:
    return "" if value is None else f"{label} {value:.2f}{suffix}"
