from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from marketdesk.models import AskStockMetric, AskStockResponse, EquityQuote, StockDossier

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


def classify_stock_question(question: str) -> AskStockIntent:
    normalized = _compact(question).casefold()
    keyword_groups: tuple[tuple[AskStockIntent, tuple[str, ...]], ...] = (
        ("risk", ("风险", "利空", "隐患", "下跌", "回撤")),
        ("trend", ("趋势", "技术", "走势", "均线", "动量", "macd", "rsi")),
        ("valuation", ("估值", "市盈率", "市净率", "贵不贵", "便宜", "对比")),
        ("action", ("买", "卖", "仓位", "止损", "止盈", "操作", "入场")),
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
        metrics=_stock_metrics(dossier),
        observed_at=observed_at,
        source="本地行情快照 + 确定性分析",
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


def _stock_metrics(dossier: StockDossier) -> list[AskStockMetric]:
    quote = dossier.quote
    score = dossier.stance_score
    confidence = dossier.investment_advice.confidence
    return [
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


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        normalized = " ".join(value.split())
        if normalized and normalized not in result:
            result.append(normalized)
    return result


def _lead(name: str, label: str, values: list[str], fallback: str) -> str:
    selected = _unique(values)[:2]
    return f"{name}{label}：{'；'.join(selected) if selected else fallback}。"
