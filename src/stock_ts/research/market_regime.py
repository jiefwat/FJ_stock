from __future__ import annotations

from dataclasses import dataclass

from stock_ts.models import MarketSnapshot

from .evidence import EvidenceStatus


@dataclass(frozen=True)
class MarketRegimeDimension:
    name: str
    status: EvidenceStatus
    conclusion: str
    evidence: str
    confidence: int
    missing_fields: tuple[str, ...] = ()


@dataclass(frozen=True)
class MarketScenario:
    name: str
    trigger: str
    action: str
    invalidation: str


@dataclass(frozen=True)
class MarketRegimeAssessment:
    trade_date: str
    stage: str
    risk_budget: str
    confidence: int
    thesis: str
    primary_risk: str
    supporting_evidence: tuple[str, ...]
    counter_evidence: tuple[str, ...]
    invalidate_condition: str
    dimensions: tuple[MarketRegimeDimension, ...]
    scenarios: tuple[MarketScenario, ...]


def assess_market_regime(
    market: MarketSnapshot,
    *,
    quote_status: EvidenceStatus = EvidenceStatus.COMPLETE,
) -> MarketRegimeAssessment:
    if quote_status in {EvidenceStatus.STALE, EvidenceStatus.BLOCKED}:
        return MarketRegimeAssessment(
            trade_date=market.trade_date,
            stage="数据暂停",
            risk_budget="0%",
            confidence=0,
            thesis="行情时效未通过，暂停按当前盘面形成市场判断。",
            primary_risk="行情已过期，任何进攻性结论都可能基于错误时点。",
            supporting_evidence=("数据质量闸门已阻断",),
            counter_evidence=("等待最近交易日行情后重新评估",),
            invalidate_condition="最近交易日行情、宽度和指数数据刷新并通过校验。",
            dimensions=_dimensions(market, blocked=True),
            scenarios=_scenarios("数据暂停"),
        )

    stage, risk_budget = _classify(market)
    dimensions = _dimensions(market, blocked=False)
    degraded_count = sum(item.status != EvidenceStatus.COMPLETE for item in dimensions)
    confidence = max(35, 82 - degraded_count * 4)
    support = _supporting_evidence(market, stage)
    counter = _counter_evidence(market, stage)
    return MarketRegimeAssessment(
        trade_date=market.trade_date,
        stage=stage,
        risk_budget=risk_budget,
        confidence=confidence,
        thesis=_thesis(stage, market),
        primary_risk=counter[0],
        supporting_evidence=support,
        counter_evidence=counter,
        invalidate_condition=_invalidation(stage),
        dimensions=dimensions,
        scenarios=_scenarios(stage),
    )


def _classify(market: MarketSnapshot) -> tuple[str, str]:
    if market.heat_score >= 70 and market.breadth_ratio >= 1.5 and market.limit_down_count < 10:
        return "进攻", "70%-85%"
    if market.heat_score >= 55 and market.breadth_ratio >= 0.9:
        return "轮动", "50%-70%"
    if market.limit_down_count >= 30 or market.breadth_ratio < 0.55:
        return "风险释放", "10%-30%"
    if market.heat_score < 45:
        return "防守", "20%-40%"
    return "震荡", "40%-60%"


def _dimensions(
    market: MarketSnapshot, *, blocked: bool
) -> tuple[MarketRegimeDimension, ...]:
    if blocked:
        blocked_dimension = MarketRegimeDimension(
            name="行情",
            status=EvidenceStatus.BLOCKED,
            conclusion="暂停判断",
            evidence="行情日期未通过时效校验。",
            confidence=0,
            missing_fields=("最近交易日行情",),
        )
        return (
            blocked_dimension,
            *(
                MarketRegimeDimension(
                    name=name,
                    status=EvidenceStatus.BLOCKED,
                    conclusion="暂停判断",
                    evidence="等待行情刷新。",
                    confidence=0,
                    missing_fields=("最近交易日行情",),
                )
                for name in ("趋势", "宽度", "流动性", "风格", "情绪")
            ),
        )

    index_text = "、".join(
        f"{item.name}{item.pct_chg:+.2f}%" for item in market.indices[:3]
    ) or "缺少主要指数"
    amount = sum(item.amount for item in market.indices if item.amount)
    top_style = "、".join(name for name, _ in market.top_sectors[:3]) or "主线缺失"
    return (
        MarketRegimeDimension(
            "趋势",
            EvidenceStatus.DEGRADED,
            "指数当日方向可见，跨期趋势待验证",
            f"{index_text}；仅有当日截面，不能确认趋势持续性。",
            62,
            ("指数历史序列",),
        ),
        MarketRegimeDimension(
            "宽度",
            EvidenceStatus.COMPLETE,
            "参与度偏强" if market.breadth_ratio >= 1 else "参与度偏弱",
            (
                f"上涨 {market.advancing_count} / 下跌 {market.declining_count}，"
                f"宽度比 {market.breadth_ratio:.2f}。"
            ),
            88,
        ),
        MarketRegimeDimension(
            "流动性",
            EvidenceStatus.DEGRADED,
            "成交截面可见，放缩量待验证",
            f"主要指数成交额合计 {amount:.2f}；仅有当日截面，不能判断放量或缩量。",
            55,
            ("前一交易日成交额",),
        ),
        MarketRegimeDimension(
            "风格",
            EvidenceStatus.DEGRADED,
            f"当日领先方向：{top_style}",
            f"领先方向 {top_style}；仅有当日截面，不能确认风格切换完成。",
            58,
            ("风格指数历史", "板块持续性",),
        ),
        MarketRegimeDimension(
            "情绪",
            EvidenceStatus.COMPLETE,
            "情绪活跃" if market.limit_up_count > market.limit_down_count * 2 else "情绪承压",
            f"涨停 {market.limit_up_count} / 跌停 {market.limit_down_count}。",
            86,
        ),
    )


def _supporting_evidence(market: MarketSnapshot, stage: str) -> tuple[str, ...]:
    if stage in {"进攻", "轮动"}:
        return (
            f"市场热度 {market.heat_score}/100",
            f"上涨/下跌宽度比 {market.breadth_ratio:.2f}",
            f"涨停 {market.limit_up_count} 家，跌停 {market.limit_down_count} 家",
        )
    return (
        f"市场热度 {market.heat_score}/100",
        f"下跌家数 {market.declining_count}，宽度比 {market.breadth_ratio:.2f}",
    )


def _counter_evidence(market: MarketSnapshot, stage: str) -> tuple[str, ...]:
    if stage in {"进攻", "轮动"}:
        return (
            "缺少跨期成交和风格序列，当前强度仍可能只是单日脉冲。",
            f"仍有 {market.limit_down_count} 家跌停，需防止风险扩散。",
        )
    return (
        "若上涨家数快速修复且跌停收敛，防守判断需要上调。",
        "单日截面不能证明弱势已经形成中期趋势。",
    )


def _thesis(stage: str, market: MarketSnapshot) -> str:
    mainline = "、".join(name for name, _ in market.top_sectors[:2]) or "主线待确认"
    return f"市场处于{stage}阶段，当前风险预算围绕{mainline}，但需用跨期量能确认持续性。"


def _invalidation(stage: str) -> str:
    if stage in {"进攻", "轮动"}:
        return "宽度比跌破 0.9、跌停扩散到 20 家以上或主线前排集体破位。"
    if stage == "风险释放":
        return "宽度比回到 0.9 以上、跌停收敛到 10 家以内且主线恢复扩散。"
    return "市场热度升破 60 且宽度、量能和主线同时改善。"


def _scenarios(stage: str) -> tuple[MarketScenario, ...]:
    return (
        MarketScenario(
            "偏强",
            "宽度继续改善、跌停收敛且主线前排放量不破位。",
            "风险预算上调一档，只验证主线前排。",
            "宽度回落或主线扩散失败。",
        ),
        MarketScenario(
            "基准",
            f"市场维持{stage}，强弱方向继续分化。",
            "维持当前风险预算，等待跨期量能确认。",
            "极端涨跌和指数方向同时恶化。",
        ),
        MarketScenario(
            "偏弱",
            "跌停扩散、宽度恶化或主要指数关键位置失守。",
            "降低风险暴露，暂停新增观察仓。",
            "跌停快速收敛且宽度重新站上 0.9。",
        ),
    )
