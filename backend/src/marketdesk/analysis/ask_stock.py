from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import datetime
from typing import Literal, cast

from marketdesk.models import (
    AskStockFactor,
    AskStockHoldingContext,
    AskStockMetric,
    AskStockResponse,
    EquityQuote,
    HoldingDossier,
    JsonScalar,
    StockDossier,
)

AskStockIntent = Literal["risk", "trend", "valuation", "action", "overview"]
AskStockMetricTone = Literal["positive", "neutral", "negative", "missing"]


class StockQuestionNotFound(ValueError):
    """Raised when a question does not identify a local stock."""


class AmbiguousStockQuestion(ValueError):
    """Raised when a question identifies more than one local stock."""


def resolve_stock_question(question: str, quotes: list[EquityQuote]) -> EquityQuote:
    normalized = _compact(question).casefold()
    codes = set(re.findall(r"(?<!\d)\d{6}(?!\d)", normalized))
    matched: dict[str, EquityQuote] = {
        quote.symbol: quote for quote in quotes if quote.code in codes
    }
    for quote in quotes:
        name = _compact(quote.name).casefold()
        if len(name) >= 2 and name in normalized:
            matched[quote.symbol] = quote
    alias_counts = _alias_counts(quotes)
    for quote in quotes:
        name = _compact(quote.name).casefold()
        if any(alias_counts.get(alias) == 1 and alias in normalized for alias in _name_aliases(name)):
            matched[quote.symbol] = quote
    if not matched:
        raise StockQuestionNotFound("问题中没有可识别的股票名称或代码")
    if len(matched) > 1:
        raise AmbiguousStockQuestion("一次只问一只股票")
    return next(iter(matched.values()))


def is_portfolio_question(question: str) -> bool:
    normalized = _compact(question)
    keywords = (
        "我的持仓",
        "持仓里",
        "持仓中",
        "组合",
        "账户",
        "仓位里",
        "我持有",
        "我买的",
    )
    return any(keyword in normalized for keyword in keywords)


def classify_stock_question(question: str) -> AskStockIntent:
    normalized = _compact(question).casefold()
    keyword_groups: tuple[tuple[AskStockIntent, tuple[str, ...]], ...] = (
        ("risk", ("风险", "利空", "隐患", "下跌", "回撤")),
        ("trend", ("趋势", "技术", "走势", "均线", "动量", "macd", "rsi")),
        ("valuation", ("估值", "市盈率", "市净率", "贵不贵", "便宜", "对比")),
        ("action", ("买", "卖", "仓位", "减仓", "加仓", "止损", "止盈", "操作", "入场")),
    )
    for intent, keywords in keyword_groups:
        if any(keyword in normalized for keyword in keywords):
            return intent
    return "overview"


def build_stock_answer(
    *,
    question: str,
    intent: AskStockIntent,
    dossier: StockDossier,
    observed_at: datetime,
    holding: HoldingDossier | None = None,
) -> AskStockResponse:
    quote = dossier.quote
    risks = _unique([*dossier.bear_case, *dossier.invalidation])[:4]
    next_actions = _unique(dossier.next_actions)[:4]
    evidence: list[str]

    if intent == "risk":
        evidence = _unique([*dossier.bear_case, *dossier.invalidation, *dossier.missing_evidence])
        answer = _lead(quote.name, "当前主要风险", dossier.bear_case, "风险证据不足")
    elif intent == "trend":
        evidence = _unique(
            [dossier.trend_forecast.summary, *dossier.trend_forecast.drivers]
            + [factor.evidence for factor in dossier.score_factors if factor.available]
        )
        answer = (
            f"{quote.name}的{dossier.trend_forecast.horizon}趋势判断为"
            f"{dossier.trend_forecast.direction}：{dossier.trend_forecast.summary}"
        )
    elif intent == "valuation":
        valuation = next(
            (item for item in dossier.analysis_dimensions if item.key == "valuation"), None
        )
        comparisons = [
            item.summary
            for item in [*dossier.horizontal_comparison, *dossier.vertical_comparison]
            if item.available and item.key in {"valuation", "pe", "pb"}
        ]
        evidence = _unique(
            ([valuation.summary, *valuation.evidence] if valuation else []) + comparisons
        )
        answer = (
            f"{quote.name}的估值判断：{valuation.summary}"
            if valuation
            else f"{quote.name}当前缺少足够的估值比较证据。"
        )
    elif intent == "action":
        advice = dossier.investment_advice
        evidence = _unique(
            [*advice.rationale, advice.entry_plan, advice.stop_loss, advice.take_profit]
        )
        answer = (
            f"{quote.name}当前建议为{advice.action}。{advice.position_hint}；"
            f"入场纪律：{advice.entry_plan}；止损纪律：{advice.stop_loss}。"
        )
    else:
        evidence = _unique(
            [*dossier.bull_case, *dossier.bear_case]
            + [factor.evidence for factor in dossier.score_factors if factor.available]
        )
        answer = dossier.conclusion

    holding_context = _holding_context(holding)
    if holding is not None:
        answer = _with_holding_summary(answer, holding)
        risks = _unique([*holding.risk_flags, *risks])[:4]
        evidence = _unique([
            f"账户持仓：{holding.item.quantity:g} 股，成本 {holding.item.cost_price:.2f}",
            *evidence,
        ])
        next_actions = _unique([*holding.next_actions, *next_actions])[:4]

    if not evidence:
        evidence = ["当前证据覆盖不足，暂不形成更强结论。"]
    return AskStockResponse(
        kind="stock_analysis",
        question=" ".join(question.split()),
        intent=intent,
        symbol=quote.symbol,
        name=quote.name,
        answer=answer,
        evidence=evidence[:5],
        risks=risks,
        next_actions=next_actions,
        metrics=_stock_metrics(dossier, holding),
        factors=_stock_factors(dossier),
        holding_context=holding_context,
        observed_at=observed_at,
        source="本地行情快照 + 确定性分析",
        disclaimer="研究辅助信息，不构成投资建议。",
    )


def build_portfolio_answer(
    *,
    question: str,
    holdings: list[HoldingDossier],
    observed_at: datetime,
) -> AskStockResponse:
    if not holdings:
        return AskStockResponse(
            kind="portfolio_analysis",
            question=" ".join(question.split()),
            intent="portfolio",
            answer="当前账户没有持仓记录，无法生成组合风险排序。先在持仓页录入股票、成本、目标仓位后再问组合问题。",
            evidence=["账户持仓为空，未使用默认账户或其他用户数据。"],
            risks=["缺少个人持仓上下文"],
            next_actions=["在持仓页新增至少一条持仓", "录入成本价、目标仓位、持仓逻辑和失效条件"],
            metrics=[
                AskStockMetric(label="持仓数量", value="0", tone="missing"),
                AskStockMetric(label="总市值", value="—", tone="missing"),
                AskStockMetric(label="风险持仓", value="0", tone="neutral"),
            ],
            observed_at=observed_at,
            source="账户持仓 + 本地行情快照 + 确定性分析",
            disclaimer="研究辅助信息，不构成投资建议。",
        )

    ranked = sorted(holdings, key=_holding_risk_score, reverse=True)
    total_value = sum(item.market_value or 0 for item in holdings)
    risky = sum(1 for item in holdings if item.risk_flags)
    top = ranked[0]
    answer = (
        f"当前组合最需要先复核的是 {top.item.name}（{top.item.symbol}）。"
        f"持仓动作建议为 {top.action}，"
        f"当前盈亏 { _pct(top.pnl_pct) }，组合占比 { _percent(top.portfolio_weight) }。"
    )
    return AskStockResponse(
        kind="portfolio_analysis",
        question=" ".join(question.split()),
        intent="portfolio",
        answer=answer,
        evidence=[item.conclusion for item in ranked[:5]],
        risks=_unique(flag for item in ranked for flag in item.risk_flags)[:5],
        next_actions=_unique(action for item in ranked[:3] for action in item.next_actions)[:5],
        metrics=[
            AskStockMetric(label="持仓数量", value=str(len(holdings)), tone="neutral"),
            AskStockMetric(label="总市值", value=_money(total_value or None), tone="neutral"),
            AskStockMetric(
                label="风险持仓",
                value=str(risky),
                tone="negative" if risky else "positive",
            ),
            AskStockMetric(label="最需复核", value=top.item.name, tone="negative" if top.risk_flags else "neutral"),
        ],
        rows=[_holding_row(item) for item in ranked[:8]],
        columns=["股票代码", "股票简称", "组合占比", "盈亏", "动作", "风险"],
        observed_at=observed_at,
        source="账户持仓 + 本地行情快照 + 确定性分析",
        disclaimer="研究辅助信息，不构成投资建议。",
    )


def _compact(value: str) -> str:
    return "".join(value.split())


def _name_aliases(name: str) -> list[str]:
    if len(name) <= 2:
        return []
    aliases = {name[:2], name[-2:]}
    return [alias for alias in aliases if len(alias) >= 2]


def _alias_counts(quotes: list[EquityQuote]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for quote in quotes:
        for alias in _name_aliases(_compact(quote.name).casefold()):
            counts[alias] = counts.get(alias, 0) + 1
    return counts


def _metric_tone(value: float | None, *, good: float, bad: float) -> AskStockMetricTone:
    if value is None:
        return "missing"
    if value >= good:
        return "positive"
    if value < bad:
        return "negative"
    return "neutral"


def _percent(value: float | None) -> str:
    return "—" if value is None else f"{value * 100:.0f}%"


def _pct(value: float | None) -> str:
    if value is None:
        return "—"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.2f}%"


def _price(value: float | None) -> str:
    return "—" if value is None else f"{value:.2f}"


def _change_pct(value: float | None) -> str:
    if value is None:
        return "—"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.2f}%"


def _change_tone(value: float | None) -> AskStockMetricTone:
    if value is None:
        return "missing"
    if value > 0:
        return "positive"
    if value < 0:
        return "negative"
    return "neutral"


def _money(value: float | None) -> str:
    if value is None:
        return "—"
    if abs(value) >= 100_000_000:
        return f"{value / 100_000_000:.1f} 亿"
    if abs(value) >= 10_000:
        return f"{value / 10_000:.0f} 万"
    return f"{value:.0f}"


def _stock_metrics(dossier: StockDossier, holding: HoldingDossier | None) -> list[AskStockMetric]:
    quote = dossier.quote
    score = dossier.stance_score
    confidence = dossier.investment_advice.confidence
    metrics = [
        AskStockMetric(
            label="综合分",
            value="—" if score is None else f"{score:.0f}",
            tone=_metric_tone(score, good=60, bad=45),
        ),
        AskStockMetric(
            label="建议动作",
            value=dossier.investment_advice.action,
            tone=_metric_tone(score, good=60, bad=45),
        ),
        AskStockMetric(
            label="证据覆盖",
            value=_percent(dossier.evidence_coverage),
            tone=_metric_tone(dossier.evidence_coverage, good=0.7, bad=0.45),
        ),
        AskStockMetric(
            label="置信度",
            value=_percent(confidence),
            tone=_metric_tone(confidence, good=0.65, bad=0.45),
        ),
        AskStockMetric(label="最新价", value=_price(quote.price), tone="neutral"),
        AskStockMetric(
            label="涨跌幅",
            value=_change_pct(quote.change_pct),
            tone=_change_tone(quote.change_pct),
        ),
    ]
    if holding is not None:
        metrics = [
            *metrics[:4],
            AskStockMetric(label="持仓盈亏", value=_pct(holding.pnl_pct), tone=_change_tone(holding.pnl_pct)),
            AskStockMetric(label="组合占比", value=_percent(holding.portfolio_weight), tone="neutral"),
        ]
    return metrics


def _stock_factors(dossier: StockDossier) -> list[AskStockFactor]:
    return [
        AskStockFactor(
            label=factor.label,
            impact=factor.impact,
            signal=cast(AskStockMetricTone, factor.signal),
            evidence=factor.evidence,
        )
        for factor in dossier.score_factors[:12]
    ]


def _holding_context(holding: HoldingDossier | None) -> AskStockHoldingContext | None:
    if holding is None:
        return None
    return AskStockHoldingContext(
        owned=True,
        quantity=holding.item.quantity,
        cost_price=holding.item.cost_price,
        market_value=holding.market_value,
        pnl_pct=holding.pnl_pct,
        portfolio_weight=holding.portfolio_weight,
        drift=holding.drift,
        action=holding.action,
        risk_flags=holding.risk_flags,
    )


def _with_holding_summary(answer: str, holding: HoldingDossier) -> str:
    return (
        f"{answer} 结合你的账户持仓：当前持有 {holding.item.quantity:g} 股，"
        f"成本 {holding.item.cost_price:.2f}，持仓盈亏 {_pct(holding.pnl_pct)}，"
        f"组合占比 {_percent(holding.portfolio_weight)}，持仓动作建议 {holding.action}。"
    )


def _holding_risk_score(holding: HoldingDossier) -> float:
    score = len(holding.risk_flags) * 25.0
    if holding.pnl_pct is not None and holding.pnl_pct < 0:
        score += min(abs(holding.pnl_pct), 30)
    if holding.drift is not None and holding.drift > 0:
        score += min(holding.drift * 100, 25)
    if holding.quote.change_pct is not None and holding.quote.change_pct < 0:
        score += min(abs(holding.quote.change_pct), 10)
    return score


def _holding_row(holding: HoldingDossier) -> dict[str, JsonScalar]:
    return {
        "股票代码": holding.item.symbol,
        "股票简称": holding.item.name,
        "组合占比": _percent(holding.portfolio_weight),
        "盈亏": _pct(holding.pnl_pct),
        "动作": holding.action,
        "风险": "；".join(holding.risk_flags) if holding.risk_flags else "未触发",
    }


def _unique(values: Iterable[object]) -> list[str]:
    result: list[str] = []
    for value in values:
        normalized = " ".join(str(value).split())
        if normalized and normalized not in result:
            result.append(normalized)
    return result


def _lead(name: str, label: str, values: list[str], fallback: str) -> str:
    selected = _unique(values)[:2]
    return f"{name}{label}：{'；'.join(selected) if selected else fallback}。"
