from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from stock_ts.models import Holding, StockRawData

from .evidence import EvidenceItem, EvidenceStatus


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
) -> StockResearchMemo:
    latest = raw.bars[-1] if raw.bars else None
    trade_date = latest.date if latest else ""
    latest_close = latest.close if latest else 0.0
    quality = _quality_section(raw.fundamental_metrics)
    valuation = _valuation_section(raw)
    events = _event_section(raw, event_radar)
    evidence = _evidence_items(raw, holding, trade_date, quality, valuation, events)
    verdict = _verdict(raw, quality, valuation, events)
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
        scenarios=_scenarios(raw, quality, events),
        evidence=evidence,
    )


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


def _quality_section(metrics: dict[str, float | str | None]) -> ResearchSection:
    if not metrics:
        return ResearchSection(
            "经营质量",
            "经营质量数据缺失，不能判断盈利能力和现金流质量。",
            (),
            "缺少营收、利润、ROE、负债与经营现金流字段。",
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
    if revenue is not None and profit is not None and profit > revenue:
        conclusion = "盈利增速高于收入增速，但仍需拆解利润质量和基数影响。"
    elif revenue is not None and profit is not None and profit < revenue:
        conclusion = "利润增速落后于收入增速，盈利质量需要重点复核。"
    else:
        conclusion = "已有部分经营指标，但不足以形成完整盈利质量判断。"
    return ResearchSection(
        "经营质量",
        conclusion,
        facts,
        "单期数据只能描述当前截面，不能声称趋势改善或恶化。",
        ("对比最近四个报告期", "核对经营现金流与净利润匹配度"),
    )


def _valuation_section(raw: StockRawData) -> ResearchSection:
    pe = raw.pe_ttm if raw.pe_ttm is not None else _number(raw.valuation.get("pe_ttm"))
    pb = _number(raw.valuation.get("pb"))
    ps = _number(raw.valuation.get("ps"))
    percentile = _number(raw.valuation.get("pe_percentile"))
    industry_median = _number(raw.valuation.get("industry_pe_median"))
    facts = tuple(
        text
        for text in (_metric("PE(TTM)", pe, "x"), _metric("PB", pb, "x"), _metric("PS", ps, "x"))
        if text
    )
    if percentile is not None:
        conclusion = f"PE 历史分位 {percentile:.0f}%，估值判断具备历史参照。"
        limitation = "历史分位仍需结合盈利周期和口径变化。"
    elif industry_median is not None and pe is not None:
        conclusion = f"PE {pe:.2f}x，对比行业中位数 {industry_median:.2f}x。"
        limitation = "行业对比不能替代公司盈利质量和增长持续性判断。"
    else:
        conclusion = "；".join(facts) if facts else "估值字段缺失。"
        limitation = "缺少历史分位或行业对比，只描述绝对估值水平。"
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
    raw: StockRawData,
    quality: ResearchSection,
    valuation: ResearchSection,
    events: ResearchSection,
) -> ResearchVerdict:
    has_fundamentals = bool(raw.fundamental_metrics)
    has_comparison = any(
        raw.valuation.get(key) is not None for key in ("pe_percentile", "industry_pe_median")
    )
    has_events = bool(raw.announcements or raw.news_items)
    missing_count = sum(not value for value in (has_fundamentals, has_comparison, has_events))
    status = "技术性观察" if missing_count >= 2 else "条件研究"
    confidence = max(25, 78 - missing_count * 18)
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


def _evidence_items(
    raw: StockRawData,
    holding: Holding | None,
    trade_date: str,
    quality: ResearchSection,
    valuation: ResearchSection,
    events: ResearchSection,
) -> tuple[EvidenceItem, ...]:
    source = ", ".join(raw.data_sources)
    valuation_comparable = any(
        raw.valuation.get(key) is not None for key in ("pe_percentile", "industry_pe_median")
    )
    return (
        EvidenceItem(
            "行情",
            source,
            trade_date,
            EvidenceStatus.COMPLETE if raw.bars else EvidenceStatus.BLOCKED,
            "日线价格与成交量" if raw.bars else "缺少 K 线",
        ),
        EvidenceItem(
            "经营质量",
            str(raw.fundamental_metrics.get("source") or ""),
            str(raw.fundamental_metrics.get("date") or ""),
            EvidenceStatus.DEGRADED if raw.fundamental_metrics else EvidenceStatus.MISSING,
            quality.limitations,
        ),
        EvidenceItem(
            "估值",
            str(raw.valuation.get("source") or ""),
            str(raw.valuation.get("date") or trade_date),
            EvidenceStatus.COMPLETE if valuation_comparable else EvidenceStatus.DEGRADED,
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
            EvidenceStatus.DEGRADED
            if raw.announcements or raw.news_items
            else EvidenceStatus.MISSING,
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
        return float(value)
    except (TypeError, ValueError):
        return None


def _metric(label: str, value: float | None, suffix: str) -> str:
    return "" if value is None else f"{label} {value:.2f}{suffix}"
