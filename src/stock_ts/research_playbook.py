from __future__ import annotations

from dataclasses import dataclass

from .deep_models import DeepStockReport
from .models import (
    CandidatePoolReport,
    MarketSnapshot,
    PortfolioAnalysisReport,
    SectorAnalysisReport,
)


@dataclass(frozen=True)
class StrategyLens:
    name: str
    score: int
    stance: str
    evidence: str
    action: str


@dataclass(frozen=True)
class ResearchRoleCard:
    role: str
    conclusion: str
    evidence: str
    next_question: str


@dataclass(frozen=True)
class SourceBlock:
    name: str
    status: str
    detail: str


@dataclass(frozen=True)
class ObservationLevels:
    support: float
    resistance: float
    invalid_line: float
    position_note: str


@dataclass(frozen=True)
class DecisionDashboard:
    bias: str
    confidence_score: int
    risk_budget: str
    observation_levels: ObservationLevels
    catalysts: list[str]
    red_flags: list[str]
    checklist: list[str]
    strategy_lenses: list[StrategyLens]
    research_team: list[ResearchRoleCard]
    source_blocks: list[SourceBlock]


def build_decision_dashboard(
    *,
    stock: DeepStockReport,
    market: MarketSnapshot,
    sectors: SectorAnalysisReport,
    portfolio: PortfolioAnalysisReport | None,
    candidates: CandidatePoolReport,
    data_warnings: list[str] | None = None,
) -> DecisionDashboard:
    warnings = data_warnings or []
    quality_penalty = min(18, len(warnings) * 6)
    confidence = max(0, min(100, stock.upside.score - quality_penalty))
    bias = _bias(confidence, stock.risk_level)
    risk_budget = _risk_budget(confidence, market.heat_score, stock.risk_level)
    levels = _observation_levels(stock, risk_budget)
    lenses = _strategy_lenses(stock, market, sectors, portfolio)
    catalysts = _catalysts(stock, market, sectors, candidates)
    red_flags = list(dict.fromkeys([*stock.risks, *warnings, *stock.invalid_conditions[:2]]))
    return DecisionDashboard(
        bias=bias,
        confidence_score=confidence,
        risk_budget=risk_budget,
        observation_levels=levels,
        catalysts=catalysts,
        red_flags=red_flags,
        checklist=_checklist(stock, market, risk_budget, warnings),
        strategy_lenses=lenses,
        research_team=_research_team(stock, market, sectors, portfolio, lenses),
        source_blocks=_source_blocks(warnings, portfolio),
    )


def _bias(confidence: int, risk_level: str) -> str:
    if risk_level == "高" or confidence < 45:
        return "防守观察"
    if confidence >= 72:
        return "重点观察"
    if confidence >= 58:
        return "条件观察"
    return "谨慎观察"


def _risk_budget(confidence: int, market_heat: int, risk_level: str) -> str:
    if risk_level == "高" or market_heat < 45 or confidence < 50:
        return "低风险预算"
    if confidence >= 72 and market_heat >= 60:
        return "中高风险预算"
    return "中性风险预算"


def _observation_levels(stock: DeepStockReport, risk_budget: str) -> ObservationLevels:
    close = stock.latest_close
    support = close * 0.97
    resistance = close * 1.05
    invalid_line = close * (0.94 if risk_budget == "低风险预算" else 0.92)
    if risk_budget == "低风险预算":
        note = "只观察承接和止跌，不提高风险暴露。"
    elif risk_budget == "中高风险预算":
        note = "只有放量突破并满足大盘/板块验证后才提高观察优先级。"
    else:
        note = "维持小仓位/观察清单思路，等确认条件。"
    return ObservationLevels(
        support=round(support, 2),
        resistance=round(resistance, 2),
        invalid_line=round(invalid_line, 2),
        position_note=note,
    )


def _strategy_lenses(
    stock: DeepStockReport,
    market: MarketSnapshot,
    sectors: SectorAnalysisReport,
    portfolio: PortfolioAnalysisReport | None,
) -> list[StrategyLens]:
    angle_map = {angle.name: angle for angle in stock.angles}
    trend = angle_map.get("价格趋势")
    volume = angle_map.get("量能结构")
    risk = angle_map.get("风险约束")
    sector = angle_map.get("板块主线")
    market_score = angle_map.get("市场环境")
    portfolio_angle = angle_map.get("持仓影响")
    return [
        _lens(
            "均线趋势",
            trend.score if trend else 50,
            trend.evidence if trend else stock.trend,
        ),
        _lens(
            "量能承接",
            volume.score if volume else 50,
            volume.evidence if volume else "等待量能验证",
        ),
        _lens(
            "市场环境",
            market_score.score if market_score else market.heat_score,
            market.summary,
        ),
        _lens(
            "热点主线",
            sector.score if sector else 50,
            sector.evidence if sector else f"当前主线：{'、'.join(sectors.market_mainline)}",
        ),
        _lens(
            "风险回撤",
            risk.score if risk else 50,
            risk.evidence if risk else stock.risk_level,
        ),
        _lens(
            "持仓影响",
            portfolio_angle.score if portfolio_angle else (55 if portfolio is not None else 50),
            portfolio_angle.evidence if portfolio_angle else "当前未识别组合持仓影响",
        ),
    ]


def _lens(name: str, score: int, evidence: str) -> StrategyLens:
    if score >= 70:
        stance = "通过"
        action = "可进入下一层验证"
    elif score <= 45:
        stance = "不通过"
        action = "降低优先级或等待修复"
    else:
        stance = "待确认"
        action = "保留观察，等待盘中证据"
    return StrategyLens(name=name, score=score, stance=stance, evidence=evidence, action=action)


def _catalysts(
    stock: DeepStockReport,
    market: MarketSnapshot,
    sectors: SectorAnalysisReport,
    candidates: CandidatePoolReport,
) -> list[str]:
    items = list(stock.upside.drivers[:3])
    if sectors.market_mainline:
        items.append(f"市场主线关注 {'、'.join(sectors.market_mainline[:3])}")
    if market.heat_score >= 55:
        items.append(f"大盘热度 {market.heat_score}/100，对风险偏好有支撑")
    if candidates.candidates:
        top = candidates.candidates[0]
        items.append(f"候选池龙头观察：{top.name}（{top.score}/100）")
    return list(dict.fromkeys(items))[:6]


def _checklist(
    stock: DeepStockReport,
    market: MarketSnapshot,
    risk_budget: str,
    warnings: list[str],
) -> list[str]:
    items = [
        "开盘前先确认数据质量：日期、Provider、是否样例/降级。",
        f"确认市场热度不低于 {max(45, market.heat_score - 10)}/100。",
        "确认所属板块仍在主线或至少没有明显跑输。",
        "盘中 30 分钟看承接，不用隔夜结论直接行动。",
        f"风险预算：{risk_budget}；任何动作都必须先定义失效线。",
        f"若触发失效条件：{stock.invalid_conditions[0]}，降低观察优先级。",
    ]
    if warnings:
        items.insert(1, "存在数据告警，本轮结论只能作为研究草稿。")
    return items


def _research_team(
    stock: DeepStockReport,
    market: MarketSnapshot,
    sectors: SectorAnalysisReport,
    portfolio: PortfolioAnalysisReport | None,
    lenses: list[StrategyLens],
) -> list[ResearchRoleCard]:
    failed = [lens.name for lens in lenses if lens.stance == "不通过"]
    top_mainline = (
        "、".join(sectors.market_mainline[:3]) if sectors.market_mainline else "暂无明确主线"
    )
    portfolio_note = (
        "未接入组合" if portfolio is None else f"组合健康度 {portfolio.health_score}/100"
    )
    return [
        ResearchRoleCard(
            "技术分析师",
            stock.trend,
            _lens_evidence(lenses, "均线趋势"),
            "量能是否支持趋势延续？",
        ),
        ResearchRoleCard(
            "情绪/主线分析师",
            top_mainline,
            f"市场状态 {market.regime}，热度 {market.heat_score}/100",
            "主线是否有梯队扩散？",
        ),
        ResearchRoleCard(
            "风险经理",
            "、".join(failed) or "暂无硬性否决",
            stock.invalid_conditions[0],
            "失效线是否清晰且能执行？",
        ),
        ResearchRoleCard(
            "组合经理",
            portfolio_note,
            _lens_evidence(lenses, "持仓影响"),
            "是否会放大组合集中度？",
        ),
        ResearchRoleCard(
            "裁判/研究经理",
            stock.final_conclusion,
            f"观察分 {stock.upside.score}/100",
            "证据是否足够从观察进入行动？",
        ),
    ]


def _lens_evidence(lenses: list[StrategyLens], name: str) -> str:
    return next((lens.evidence for lens in lenses if lens.name == name), "待补充")


def _source_blocks(
    warnings: list[str],
    portfolio: PortfolioAnalysisReport | None,
) -> list[SourceBlock]:
    quality_status = "warn" if warnings else "ok"
    return [
        SourceBlock("行情/K线", quality_status, "已检查 Provider 与日期；有告警时只作研究草稿。"),
        SourceBlock("技术指标", "ok", "趋势、量能、MACD、RSI、BOLL 已进入规则分析。"),
        SourceBlock("板块/主线", "partial", "已有结构化主线矩阵；真实行业映射仍需继续增强。"),
        SourceBlock("新闻/公告", "partial", "支持本地新闻和 AKShare 新闻，公告/研报全文待接入。"),
        SourceBlock("基本面/估值", "partial", "已有 PE 入口，财务质量、盈利预测和估值分位待接入。"),
        SourceBlock(
            "组合持仓",
            "ok" if portfolio is not None else "missing",
            "支持持仓 CSV/交易流水，暂不直连券商账户。",
        ),
    ]
