from __future__ import annotations

from dataclasses import dataclass

from .models import DailyBar, StockAnalysisDimension, StockAnalysisReport, StockRawData


@dataclass(frozen=True)
class StockAnalysisContextPack:
    subject: str
    trade_date: str
    available_blocks: list[str]
    missing_blocks: list[str]
    data_sources: list[str]
    limitations: list[str]


@dataclass(frozen=True)
class SignalAttribution:
    technical_indicators: int
    news_sentiment: int
    fundamentals: int
    capital_volume: int
    strongest_bullish_signal: str
    strongest_bearish_signal: str

    @property
    def total(self) -> int:
        return (
            self.technical_indicators
            + self.news_sentiment
            + self.fundamentals
            + self.capital_volume
        )


@dataclass(frozen=True)
class AnalystFinding:
    role: str
    verdict: str
    evidence: list[str]
    missing: list[str]
    action: str


@dataclass(frozen=True)
class ResearchDebate:
    bull_thesis: str
    bear_thesis: str
    judge: str


@dataclass(frozen=True)
class TraderProposal:
    action: str
    entry_trigger: str
    invalidation: str
    position_rule: str
    no_trade_conditions: list[str]


@dataclass(frozen=True)
class RiskReview:
    aggressive: str
    neutral: str
    conservative: str
    portfolio_decision: str


@dataclass(frozen=True)
class StockAgentDecision:
    context_pack: StockAnalysisContextPack
    signal_attribution: SignalAttribution
    analyst_team: list[AnalystFinding]
    research_debate: ResearchDebate
    trader: TraderProposal
    risk_review: RiskReview


def build_stock_agent_decision(
    raw: StockRawData,
    report: StockAnalysisReport,
) -> StockAgentDecision:
    """Build a deterministic, auditable TradingAgents-style stock decision.

    The project does not call an LLM here. Instead it borrows the workflow shape
    from TradingAgents and the context-pack/signal-attribution guardrails from
    daily_stock_analysis, while only using facts already present in StockTS.
    """

    dimensions = {item.name: item for item in report.dimensions}
    context_pack = _build_context_pack(raw, report)
    attribution = _build_signal_attribution(raw, report, dimensions)
    analysts = _build_analyst_team(raw, report, dimensions)
    debate = _build_research_debate(raw, report, dimensions, analysts, attribution)
    trader = _build_trader_proposal(raw, report, dimensions)
    risk = _build_risk_review(raw, report, dimensions, trader, context_pack)
    return StockAgentDecision(
        context_pack=context_pack,
        signal_attribution=attribution,
        analyst_team=analysts,
        research_debate=debate,
        trader=trader,
        risk_review=risk,
    )


def build_stock_agent_decision_from_report(report: StockAnalysisReport) -> StockAgentDecision:
    previous_close = (
        report.latest_close / (1 + report.pct_change / 100)
        if report.pct_change != -100
        else report.latest_close
    )
    raw = StockRawData(
        code=report.code,
        name=report.name,
        bars=[
            DailyBar(
                date=report.latest_date,
                open=previous_close,
                high=max(previous_close, report.latest_close),
                low=min(previous_close, report.latest_close),
                close=previous_close,
                volume=0,
            ),
            DailyBar(
                date=report.latest_date,
                open=previous_close,
                high=max(previous_close, report.latest_close),
                low=min(previous_close, report.latest_close),
                close=report.latest_close,
                volume=0,
            ),
        ],
        fund_flow=report.fund_flow,
        pe_ttm=report.pe_ttm,
        data_sources=["analysis-report"],
    )
    return build_stock_agent_decision(raw, report)


def _build_context_pack(raw: StockRawData, report: StockAnalysisReport) -> StockAnalysisContextPack:
    available: list[str] = []
    missing: list[str] = []
    limitations: list[str] = []
    if raw.bars:
        available.append("K线")
    else:
        missing.append("K线")
        limitations.append("缺少日线，不能判断趋势和波动")
    if raw.fund_flow is not None or raw.fund_flow_detail:
        available.append("资金")
    elif len(raw.bars) >= 5:
        available.append("成交侧资金代理")
        limitations.append("资金流缺失，成交侧只能作为替代观察，不等同主力净流")
    else:
        missing.append("资金")
    if raw.pe_ttm is not None or raw.valuation:
        available.append("估值")
    else:
        missing.append("估值/基本面")
        limitations.append("估值和财务质量缺失，基本面结论降级")
    if raw.news_items:
        available.append("新闻")
    else:
        missing.append("新闻/公告")
        limitations.append("缺少新闻公告，不能确认事件催化或风险")
    sources = list(raw.data_sources) or ["stock-ts-local"]
    return StockAnalysisContextPack(
        subject=f"{raw.name}({raw.code})",
        trade_date=report.latest_date,
        available_blocks=available,
        missing_blocks=missing,
        data_sources=sources,
        limitations=limitations,
    )


def _build_signal_attribution(
    raw: StockRawData,
    report: StockAnalysisReport,
    dimensions: dict[str, StockAnalysisDimension],
) -> SignalAttribution:
    technical_score = _avg_score(dimensions, ["技术趋势", "量价结构", "统计位置"])
    news_score = _score(dimensions, "消息事件")
    fundamental_score = _score(dimensions, "估值基本面")
    capital_score = _score(dimensions, "资金行为")
    values = _normalize_to_100(
        [
            max(1, technical_score),
            max(1, news_score if raw.news_items else 15),
            max(1, fundamental_score if raw.pe_ttm is not None or raw.valuation else 15),
            max(1, capital_score),
        ]
    )
    bullish = _strongest_bullish_signal(dimensions)
    bearish = _strongest_bearish_signal(raw, dimensions, report)
    if bullish == bearish:
        risk_dimension = dimensions.get("风险约束")
        risk_text = risk_dimension.evidence if risk_dimension else report.risk_level
        bearish = f"风险约束：{risk_text}"
    return SignalAttribution(
        technical_indicators=values[0],
        news_sentiment=values[1],
        fundamentals=values[2],
        capital_volume=values[3],
        strongest_bullish_signal=bullish,
        strongest_bearish_signal=bearish,
    )


def _build_analyst_team(
    raw: StockRawData,
    report: StockAnalysisReport,
    dimensions: dict[str, StockAnalysisDimension],
) -> list[AnalystFinding]:
    technical_items = [
        dimensions.get("技术趋势"),
        dimensions.get("量价结构"),
        dimensions.get("统计位置"),
    ]
    fundamental = dimensions.get("估值基本面")
    news = dimensions.get("消息事件")
    capital = dimensions.get("资金行为")
    return [
        AnalystFinding(
            role="技术分析师",
            verdict=_verdict_from_scores(_existing_scores(technical_items)),
            evidence=_dimension_evidence(technical_items),
            missing=[] if raw.bars else ["K线"],
            action=_combine_actions(technical_items),
        ),
        AnalystFinding(
            role="基本面分析师",
            verdict=_verdict_from_scores([fundamental.score if fundamental else 40]),
            evidence=_dimension_evidence([fundamental]),
            missing=[] if raw.pe_ttm is not None or raw.valuation else ["估值", "财务质量"],
            action=fundamental.action if fundamental else "基本面缺失，不作为买入理由",
        ),
        AnalystFinding(
            role="新闻/情绪分析师",
            verdict=_verdict_from_scores([news.score if news else 45]),
            evidence=_news_evidence(raw, news),
            missing=[] if raw.news_items else ["新闻", "公告"],
            action=news.action if news else "没有事件证据，回到技术和资金确认",
        ),
        AnalystFinding(
            role="资金/成交分析师",
            verdict=_verdict_from_scores([capital.score if capital else 45]),
            evidence=_dimension_evidence([capital]),
            missing=[] if raw.fund_flow is not None or raw.fund_flow_detail else ["真实主力资金"],
            action=capital.action if capital else "资金面缺失，不作为买入理由",
        ),
    ]


def _build_research_debate(
    raw: StockRawData,
    report: StockAnalysisReport,
    dimensions: dict[str, StockAnalysisDimension],
    analysts: list[AnalystFinding],
    attribution: SignalAttribution,
) -> ResearchDebate:
    strong = sorted(report.dimensions, key=lambda item: item.score, reverse=True)[:2]
    weak = sorted(report.dimensions, key=lambda item: item.score)[:2]
    bull_evidence = "；".join(f"{item.name}{item.score}分：{item.evidence}" for item in strong)
    bear_evidence = "；".join(f"{item.name}{item.score}分：{item.evidence}" for item in weak)
    news_line = _first_news_title(raw) or "无明确新闻催化"
    bull = (
        f"多头观点：{raw.name}({raw.code}) 的机会只来自已验证证据：{bull_evidence}；"
        f"最强正向信号是 {attribution.strongest_bullish_signal}；消息侧参考 {news_line}。"
    )
    bear = (
        f"空头观点：{raw.name}({raw.code}) 的主要反证是 {bear_evidence}；"
        f"最强风险信号是 {attribution.strongest_bearish_signal}。"
    )
    judge = _judge_text(raw, report, dimensions, analysts)
    return ResearchDebate(bull_thesis=bull, bear_thesis=bear, judge=judge)


def _build_trader_proposal(
    raw: StockRawData,
    report: StockAnalysisReport,
    dimensions: dict[str, StockAnalysisDimension],
) -> TraderProposal:
    fund_score = _score(dimensions, "资金行为")
    risk_score = _score(dimensions, "风险约束")
    if report.decision.verdict in {"降风险", "防守观察"} or risk_score <= 45:
        action = "HOLD/REDUCE"
        position_rule = "不新增仓位；已有仓位先按止损和反弹减压执行"
    elif report.decision.verdict == "谨慎进攻" and fund_score >= 50:
        action = "WATCH/ADD_ON_TRIGGER"
        position_rule = "单次试错仓不超过计划仓位的1/3，确认后再考虑加仓"
    else:
        action = "WATCH"
        position_rule = "只放入观察，不主动开仓"
    no_trade = [report.decision.forbidden_action]
    if report.decision.data_reliability != "较可信":
        no_trade.append(f"数据可信度为{report.decision.data_reliability}时不能放大仓位")
    if raw.pe_ttm is not None and raw.pe_ttm > 80:
        no_trade.append(f"PE(TTM) {raw.pe_ttm:.2f} 偏高，不能用估值安全垫解释买入")
    return TraderProposal(
        action=action,
        entry_trigger=report.decision.strengthen_condition,
        invalidation=report.decision.exit_condition,
        position_rule=position_rule,
        no_trade_conditions=no_trade,
    )


def _build_risk_review(
    raw: StockRawData,
    report: StockAnalysisReport,
    dimensions: dict[str, StockAnalysisDimension],
    trader: TraderProposal,
    context_pack: StockAnalysisContextPack,
) -> RiskReview:
    strong = _strongest_bullish_signal(dimensions)
    weak = _strongest_bearish_signal(raw, dimensions, report)
    limitation = "；".join(context_pack.limitations[:2]) or "核心数据块可用"
    aggressive = (
        f"激进风控：只有 {strong} 继续验证且触发 {trader.entry_trigger} 时，才允许小仓试错。"
    )
    neutral = (
        f"中性风控：当前动作 {trader.action}，先跟踪 {report.latest_close:.2f} "
        "附近承接，不预设上涨。"
    )
    conservative = f"保守风控：{weak}；{limitation}，若触发 {trader.invalidation} 立即降级。"
    portfolio = (
        f"组合经理最终意见：{raw.name}({raw.code}) 维持 {report.decision.verdict}；"
        f"理由是 {weak}，数据可信度 {report.decision.data_reliability}。"
    )
    if raw.pe_ttm is not None and raw.pe_ttm > 80:
        portfolio += f" PE(TTM) {raw.pe_ttm:.2f} 属高估值约束，不能重仓追高。"
    return RiskReview(
        aggressive=aggressive,
        neutral=neutral,
        conservative=conservative,
        portfolio_decision=portfolio,
    )


def _score(dimensions: dict[str, StockAnalysisDimension], name: str) -> int:
    item = dimensions.get(name)
    return item.score if item else 45


def _avg_score(dimensions: dict[str, StockAnalysisDimension], names: list[str]) -> int:
    scores = [_score(dimensions, name) for name in names]
    return int(round(sum(scores) / max(len(scores), 1)))


def _normalize_to_100(values: list[int]) -> list[int]:
    total = sum(values) or 1
    normalized = [int(round(value / total * 100)) for value in values]
    diff = 100 - sum(normalized)
    if normalized:
        normalized[0] += diff
    return [max(0, value) for value in normalized]


def _existing_scores(items: list[StockAnalysisDimension | None]) -> list[int]:
    return [item.score for item in items if item]


def _verdict_from_scores(scores: list[int]) -> str:
    if not scores:
        return "证据缺失"
    avg = sum(scores) / len(scores)
    if avg >= 65:
        return "支持"
    if avg <= 45:
        return "约束"
    return "待验证"


def _dimension_evidence(items: list[StockAnalysisDimension | None]) -> list[str]:
    return [f"{item.name}：{item.evidence}" for item in items if item]


def _combine_actions(items: list[StockAnalysisDimension | None]) -> str:
    actions = [item.action for item in items if item]
    return "；".join(dict.fromkeys(actions)) or "等待证据补齐"


def _news_evidence(raw: StockRawData, news_dimension: StockAnalysisDimension | None) -> list[str]:
    evidence = _dimension_evidence([news_dimension])
    for item in raw.news_items[:3]:
        title = str(getattr(item, "title", "") or "").strip()
        source = str(getattr(item, "source", "") or "").strip()
        sentiment = str(getattr(item, "sentiment", "neutral") or "neutral")
        if title:
            evidence.append(f"{sentiment}：{title}{'（' + source + '）' if source else ''}")
    return evidence or ["新闻/公告事件未接入或为空"]


def _first_news_title(raw: StockRawData) -> str:
    for item in raw.news_items:
        title = str(getattr(item, "title", "") or "").strip()
        if title:
            return title
    return ""


def _strongest_bullish_signal(dimensions: dict[str, StockAnalysisDimension]) -> str:
    candidates = [item for item in dimensions.values() if item.score >= 55]
    if not candidates:
        candidates = list(dimensions.values())
    if not candidates:
        return "暂无正向信号"
    best = max(candidates, key=lambda item: item.score)
    return f"{best.name}：{best.evidence}"


def _strongest_bearish_signal(
    raw: StockRawData,
    dimensions: dict[str, StockAnalysisDimension],
    report: StockAnalysisReport,
) -> str:
    high_pe = raw.pe_ttm is not None and raw.pe_ttm > 80
    if high_pe:
        return f"基本面承压：PE(TTM) {raw.pe_ttm:.2f}，高估值需要趋势和资金持续确认"
    candidates = list(dimensions.values())
    if not candidates:
        return f"风险等级 {report.risk_level}"
    worst = min(candidates, key=lambda item: item.score)
    return f"{worst.name}：{worst.evidence}"


def _judge_text(
    raw: StockRawData,
    report: StockAnalysisReport,
    dimensions: dict[str, StockAnalysisDimension],
    analysts: list[AnalystFinding],
) -> str:
    blockers = [finding.role for finding in analysts if finding.verdict == "约束"]
    if blockers:
        return (
            f"研究经理裁决：{raw.name} 先按{report.decision.verdict}处理；"
            f"约束来自{'、'.join(blockers)}，必须等 "
            f"{report.decision.strengthen_condition} 后再上调。"
        )
    if report.decision.verdict == "谨慎进攻":
        return f"研究经理裁决：{raw.name} 允许进入条件化观察，但只执行触发式小仓，禁止追高。"
    return f"研究经理裁决：{raw.name} 证据未形成压倒性共振，维持观察。"
