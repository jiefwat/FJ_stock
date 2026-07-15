from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from .models import (
    CandidateStockRawData,
    MarketSnapshot,
    SectorAnalysisReport,
    StockAnalysisReport,
    StockRawData,
)


@dataclass(frozen=True)
class MarketPulseMetric:
    key: str
    label: str
    value: str
    interpretation: str
    tone: str = "neutral"


@dataclass(frozen=True)
class MarketPulse:
    advance_ratio: float
    breadth_ratio: float
    limit_balance: int
    extreme_up_count: int
    extreme_down_count: int
    confirmed_theme_count: int
    sector_participation: float
    coverage: int
    regime: str
    risk_budget: str
    metrics: tuple[MarketPulseMetric, ...]
    hard_gate_reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class StockEvidenceDimension:
    name: str
    score: int
    coverage: str
    confidence: str
    supporting_evidence: tuple[str, ...]
    counter_evidence: tuple[str, ...]
    strengthen_condition: str
    invalidation_condition: str


@dataclass(frozen=True)
class StockEvidenceMatrix:
    code: str
    name: str
    as_of: str
    decision_label: str
    action: str
    primary_risk: str
    confidence: str
    strengthen_condition: str
    invalidation_condition: str
    dimensions: tuple[StockEvidenceDimension, ...]
    hard_gate_reasons: tuple[str, ...] = ()


def build_market_pulse(
    market: MarketSnapshot,
    sectors: SectorAnalysisReport,
    candidates: Sequence[CandidateStockRawData],
) -> MarketPulse:
    total = market.advancing_count + market.declining_count + market.unchanged_count
    advance_ratio = market.advancing_count / total if total else 0.0
    breadth_ratio = (
        market.advancing_count / max(market.declining_count, 1) if total else 0.0
    )
    limit_balance = market.limit_up_count - market.limit_down_count * 2

    candidate_moves = [
        (candidate.sector.strip(), _candidate_pct_change(candidate))
        for candidate in candidates
        if candidate.price_reliable and len(candidate.bars) >= 2
    ]
    extreme_up_count = sum(1 for _sector, value in candidate_moves if value >= 3)
    extreme_down_count = sum(1 for _sector, value in candidate_moves if value <= -3)
    extreme_spread = extreme_up_count - extreme_down_count
    strong_theme_counts = Counter(
        sector
        for sector, value in candidate_moves
        if sector and sector != "未识别主题" and value >= 3
    )
    observed_themes = {
        sector for sector, _value in candidate_moves if sector and sector != "未识别主题"
    }
    confirmed_theme_count = sum(1 for count in strong_theme_counts.values() if count >= 2)
    sector_participation = (
        confirmed_theme_count / len(observed_themes) if observed_themes else 0.0
    )

    ready_blocks = sum((total > 0, bool(candidate_moves), bool(sectors.sectors)))
    coverage = round(ready_blocks / 3 * 100) if ready_blocks else 0
    hard_gate_reasons = _market_hard_gates(
        total=total,
        limit_up=market.limit_up_count,
        limit_down=market.limit_down_count,
        extreme_spread=extreme_spread,
        sample_size=len(candidate_moves),
    )
    regime = _market_regime(
        hard_gate_reasons=hard_gate_reasons,
        coverage=coverage,
        breadth_ratio=breadth_ratio,
        extreme_spread=extreme_spread,
        confirmed_theme_count=confirmed_theme_count,
    )
    risk_budget = {
        "risk_off": "0%",
        "defensive": "10%-30%",
        "balanced": "30%-50%",
        "constructive": "50%-70%",
        "risk_on": "70%-80%",
    }[regime]
    metrics = (
        MarketPulseMetric(
            key="participation",
            label="上涨参与率",
            value=f"{advance_ratio:.1%}" if total else "待补",
            interpretation=(
                f"上涨 {market.advancing_count} / 全市场 {total} 家"
                if total
                else "全市场涨跌家数未返回"
            ),
            tone=_ratio_tone(advance_ratio, high=0.56, low=0.44),
        ),
        MarketPulseMetric(
            key="breadth",
            label="涨跌宽度比",
            value=f"{breadth_ratio:.2f}" if total else "待补",
            interpretation="高于 1.30 才视为广度扩散",
            tone=_ratio_tone(breadth_ratio, high=1.3, low=0.8),
        ),
        MarketPulseMetric(
            key="limit_balance",
            label="涨跌停平衡",
            value=f"{limit_balance:+d}" if total else "待补",
            interpretation=(
                f"涨停 {market.limit_up_count} / 跌停 {market.limit_down_count}"
                if total
                else "涨跌停统计未返回"
            ),
            tone=_ratio_tone(limit_balance, high=20, low=0),
        ),
        MarketPulseMetric(
            key="extreme_spread",
            label="扫描样本强弱差",
            value=f"{extreme_spread:+d}" if candidate_moves else "待补",
            interpretation=(
                f">3% {extreme_up_count} / <-3% {extreme_down_count}，样本 {len(candidate_moves)}"
                if candidate_moves
                else "候选扫描样本未返回"
            ),
            tone=_ratio_tone(extreme_spread, high=2, low=0),
        ),
        MarketPulseMetric(
            key="theme_participation",
            label="主题扩散",
            value=f"{confirmed_theme_count} 个",
            interpretation="至少两只样本同步涨逾 3% 才确认一个主题",
            tone="positive" if confirmed_theme_count else "caution",
        ),
        MarketPulseMetric(
            key="coverage",
            label="证据覆盖",
            value=f"{coverage}%",
            interpretation="涨跌统计、扫描样本、主题数据三块覆盖",
            tone=_ratio_tone(coverage, high=100, low=60),
        ),
    )
    return MarketPulse(
        advance_ratio=round(advance_ratio, 2),
        breadth_ratio=round(breadth_ratio, 2),
        limit_balance=limit_balance,
        extreme_up_count=extreme_up_count,
        extreme_down_count=extreme_down_count,
        confirmed_theme_count=confirmed_theme_count,
        sector_participation=round(sector_participation, 2),
        coverage=coverage,
        regime=regime,
        risk_budget=risk_budget,
        metrics=metrics,
        hard_gate_reasons=hard_gate_reasons,
    )


def build_stock_evidence_matrix(
    raw: StockRawData,
    report: StockAnalysisReport,
) -> StockEvidenceMatrix:
    negative_events = _material_negative_events(raw)
    hard_gate_reasons = (
        ("重大负面事件待核查：" + "；".join(negative_events[:2]),)
        if negative_events
        else ()
    )
    dimensions = tuple(
        _stock_evidence_dimension(raw, report, dimension.name, dimension.score, dimension.evidence)
        for dimension in report.dimensions
    )
    if negative_events:
        dimensions = tuple(
            _block_event_dimension(item, negative_events) if item.name == "消息事件" else item
            for item in dimensions
        )
    confidence = "blocked" if hard_gate_reasons else _matrix_confidence(report)
    decision_label = "先处理风险" if hard_gate_reasons else report.decision.verdict
    action = (
        "暂停加仓并核查负面事件原文；确认影响前只做风险处理。"
        if hard_gate_reasons
        else report.decision.today_action
    )
    primary_risk = (
        hard_gate_reasons[0]
        if hard_gate_reasons
        else (report.decision.core_conflicts[0] if report.decision.core_conflicts else "风险待复核")
    )
    return StockEvidenceMatrix(
        code=report.code,
        name=report.name,
        as_of=report.latest_date,
        decision_label=decision_label,
        action=action,
        primary_risk=primary_risk,
        confidence=confidence,
        strengthen_condition=report.decision.strengthen_condition,
        invalidation_condition=report.decision.exit_condition,
        dimensions=dimensions,
        hard_gate_reasons=hard_gate_reasons,
    )


def _candidate_pct_change(candidate: CandidateStockRawData) -> float:
    previous = candidate.bars[-2].close
    if previous == 0:
        return 0.0
    return (candidate.bars[-1].close - previous) / previous * 100


def _market_hard_gates(
    *,
    total: int,
    limit_up: int,
    limit_down: int,
    extreme_spread: int,
    sample_size: int,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if total <= 0:
        reasons.append("全市场涨跌家数缺失")
    if limit_down >= 20 and limit_down * 2 >= max(limit_up, 1):
        reasons.append("跌停压力进入高风险区")
    if sample_size >= 10 and extreme_spread <= -3:
        reasons.append("扫描样本负向极端扩散")
    return tuple(reasons)


def _market_regime(
    *,
    hard_gate_reasons: tuple[str, ...],
    coverage: int,
    breadth_ratio: float,
    extreme_spread: int,
    confirmed_theme_count: int,
) -> str:
    if hard_gate_reasons:
        return "risk_off"
    if coverage < 60 or breadth_ratio < 0.8:
        return "defensive"
    if (
        coverage == 100
        and breadth_ratio >= 1.8
        and extreme_spread >= 4
        and confirmed_theme_count >= 2
    ):
        return "risk_on"
    if breadth_ratio >= 1.3 and extreme_spread > 0 and confirmed_theme_count >= 1:
        return "constructive"
    return "balanced"


def _ratio_tone(value: float, *, high: float, low: float) -> str:
    if value >= high:
        return "positive"
    if value < low:
        return "negative"
    return "caution"


def _stock_evidence_dimension(
    raw: StockRawData,
    report: StockAnalysisReport,
    name: str,
    score: int,
    evidence: str,
) -> StockEvidenceDimension:
    coverage = _dimension_coverage(raw, name)
    confidence = _dimension_confidence(coverage, score)
    counter = _dimension_counter_evidence(raw, report, name, score)
    return StockEvidenceDimension(
        name=name,
        score=score,
        coverage=coverage,
        confidence=confidence,
        supporting_evidence=(evidence,),
        counter_evidence=counter,
        strengthen_condition=report.decision.strengthen_condition,
        invalidation_condition=report.decision.exit_condition,
    )


def _dimension_coverage(raw: StockRawData, name: str) -> str:
    if name in {"技术趋势", "量价结构", "统计位置", "风险约束", "交易计划"}:
        return "ready" if len(raw.bars) >= 5 else "partial"
    if name == "资金行为":
        return "ready" if raw.fund_flow is not None or raw.fund_flow_detail else "missing"
    if name == "估值基本面":
        if raw.fundamental_metrics and (raw.pe_ttm is not None or raw.valuation):
            return "ready"
        return "partial" if raw.fundamental_metrics or raw.valuation else "missing"
    if name == "消息事件":
        return "ready" if raw.news_items or raw.announcements else "missing"
    return "partial"


def _dimension_confidence(coverage: str, score: int) -> str:
    if coverage == "missing":
        return "low"
    if coverage in {"partial", "stale"}:
        return "medium"
    return "high" if score >= 45 else "medium"


def _dimension_counter_evidence(
    raw: StockRawData,
    report: StockAnalysisReport,
    name: str,
    score: int,
) -> tuple[str, ...]:
    if name == "技术趋势":
        return (report.decision.exit_condition,)
    if name == "量价结构":
        return ("若价格上涨但成交持续收缩，趋势确认失效。",)
    if name == "资金行为":
        if raw.fund_flow is None and not raw.fund_flow_detail:
            return ("真实资金流缺失，当前成交代理不能替代主力资金证据。",)
        if raw.fund_flow is not None and raw.fund_flow < 0:
            return (f"主力资金净流出 {abs(raw.fund_flow):.2f} 亿元。",)
        return ("资金流入若不能带动价格站稳，需防止短期脉冲。",)
    if name == "估值基本面":
        if not raw.fundamental_metrics:
            return ("财务指标缺失，不能形成高可信基本面结论。",)
        if raw.pe_ttm is not None and raw.pe_ttm > 80:
            return (f"PE(TTM) {raw.pe_ttm:.2f}，高估值压缩安全边际。",)
        return ("当前估值仍需与行业分位和盈利兑现交叉验证。",)
    if name == "消息事件":
        negatives = _material_negative_events(raw)
        if negatives:
            return tuple(negatives[:3])
        if not raw.news_items and not raw.announcements:
            return ("新闻和公告缺失，事件风险无法排除。",)
        return ("公开信息可能滞后，重要事项仍需复核公告原文。",)
    if name == "统计位置":
        return ("统计强势不等于基本面改善，极端位置可能快速均值回归。",)
    if name == "风险约束":
        return (f"当前风险等级为{report.risk_level}，任何结论都受失效线约束。",)
    if name == "交易计划":
        return (report.decision.forbidden_action,)
    return ("该维度仍需独立证据交叉验证。",) if score >= 0 else ()


def _material_negative_events(raw: StockRawData) -> tuple[str, ...]:
    terms = ("立案", "处罚", "监管函", "退市", "重大亏损", "减持", "质押违约")
    texts = [
        f"{item.title} {item.summary}" for item in raw.news_items
    ] + [
        f"{item.get('title', '')} {item.get('summary', '')}" for item in raw.announcements
    ]
    return tuple(text.strip() for text in texts if any(term in text for term in terms))


def _block_event_dimension(
    item: StockEvidenceDimension,
    negative_events: tuple[str, ...],
) -> StockEvidenceDimension:
    return StockEvidenceDimension(
        name=item.name,
        score=min(item.score, 20),
        coverage=item.coverage,
        confidence="blocked",
        supporting_evidence=item.supporting_evidence,
        counter_evidence=negative_events[:3],
        strengthen_condition="核查负面事件原文并确认影响已被充分定价。",
        invalidation_condition="负面事件继续升级或对盈利、治理造成实质影响。",
    )


def _matrix_confidence(report: StockAnalysisReport) -> str:
    return {
        "较可信": "high",
        "部分可信": "medium",
        "低可信": "low",
    }.get(report.decision.data_reliability, "low")
