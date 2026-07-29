from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import datetime
from typing import Literal, TypedDict, cast

from marketdesk.models import (
    AskStockFactor,
    AskStockHoldingContext,
    AskStockMetric,
    AskStockResponse,
    Bar,
    EquityQuote,
    HoldingDossier,
    JsonScalar,
    StockAnalysisDimension,
    StockDossier,
)

AskStockIntent = Literal[
    "risk",
    "trend",
    "valuation",
    "fundamental",
    "catalyst",
    "action",
    "movement",
    "overview",
]
AskStockMetricTone = Literal["positive", "neutral", "negative", "missing"]


class PortfolioConcentration(TypedDict):
    max_holding_text: str
    max_weight: float
    max_weight_text: str
    top_sector: str
    top_sector_weight: float
    top_sector_weight_text: str
    top_sector_text: str


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
        name = _stock_name_key(quote.name)
        if len(name) >= 2 and name in normalized:
            matched[quote.symbol] = quote
    alias_counts = _alias_counts(quotes)
    for quote in quotes:
        name = _stock_name_key(quote.name)
        if any(alias_counts.get(alias) == 1 and alias in normalized for alias in _name_aliases(name)):
            matched[quote.symbol] = quote
    if not matched:
        raise StockQuestionNotFound("问题中没有可识别的股票名称或代码")
    if len(matched) > 1:
        raise AmbiguousStockQuestion("一次只问一只股票")
    return next(iter(matched.values()))


def is_contextual_stock_followup(question: str) -> bool:
    normalized = _compact(question).casefold()
    if not normalized:
        return False
    broad_screening_keywords = (
        "低估值",
        "高股息",
        "龙头",
        "筛选",
        "选股",
        "有哪些",
        "哪些",
        "推荐",
        "找",
        "寻找",
        "排名",
        "排行",
    )
    contextual_keywords = ("它", "这只", "该股", "这个标的", "这条线索", "这家公司", "这笔")
    if any(keyword in normalized for keyword in broad_screening_keywords) and not any(
        keyword in normalized for keyword in contextual_keywords
    ):
        return False
    followup_prefixes = ("那", "它", "这个", "这只", "该股", "刚才", "上面", "继续", "再", "顺便")
    followup_topics = (
        "风险",
        "趋势",
        "估值",
        "基本面",
        "财报",
        "业绩",
        "利润",
        "营收",
        "现金流",
        "负债",
        "公告",
        "研报",
        "消息",
        "催化",
        "题材",
        "龙虎榜",
        "仓位",
        "止损",
        "止盈",
        "支撑",
        "压力",
        "目标价",
        "价格",
        "股价",
        "合理",
        "多少",
        "为什么",
        "为啥",
        "怎么跌",
        "怎么涨",
        "大跌",
        "大涨",
        "异动",
        "发生了什么",
        "能买吗",
        "能不能",
        "要不要",
        "可以买",
        "可以卖",
        "怎么样",
        "怎么看",
    )
    if any(keyword in normalized for keyword in contextual_keywords):
        return True
    if normalized.startswith(followup_prefixes):
        return True
    return len(normalized) <= 20 and any(keyword in normalized for keyword in followup_topics)

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
        "调仓",
        "再平衡",
        "仓位调整",
    )
    return any(keyword in normalized for keyword in keywords)


def is_portfolio_diagnostic_question(question: str) -> bool:
    normalized = _compact(question)
    if not is_portfolio_question(normalized):
        return False
    if ("我持有" in normalized or "我买的" in normalized) and not any(
        keyword in normalized
        for keyword in (
            "我的持仓",
            "持仓里",
            "持仓中",
            "组合",
            "账户",
            "排序",
            "排名",
            "占比",
            "调仓",
            "再平衡",
            "仓位调整",
        )
    ):
        return False
    keywords = (
        "风险最大",
        "哪个",
        "哪些",
        "排序",
        "排名",
        "组合",
        "集中",
        "行业",
        "板块",
        "占比",
        "仓位太",
        "仓位过",
        "太重",
        "过重",
        "分散",
        "配置",
        "调仓",
        "怎么处理",
        "如何处理",
        "要不要减仓",
        "要不要卖",
        "减仓",
        "补仓",
    )
    return any(keyword in normalized for keyword in keywords)


def is_rebalance_plan_question(question: str) -> bool:
    normalized = _compact(question)
    if not is_portfolio_question(normalized):
        return False
    keywords = (
        "调仓计划",
        "生成调仓",
        "怎么调仓",
        "如何调仓",
        "调仓",
        "再平衡",
        "仓位调整",
        "调整仓位",
        "目标仓位",
        "减到",
        "加到",
        "补到",
    )
    return any(keyword in normalized for keyword in keywords)


def classify_stock_question(question: str) -> AskStockIntent:
    normalized = _compact(question).casefold()
    if _is_movement_question(normalized):
        return "movement"
    keyword_groups: tuple[tuple[AskStockIntent, tuple[str, ...]], ...] = (
        ("risk", ("风险", "利空", "隐患", "下跌风险", "回撤风险")),
        ("trend", ("趋势", "技术", "走势", "均线", "动量", "macd", "rsi")),
        ("valuation", ("估值", "市盈率", "市净率", "贵不贵", "便宜", "对比")),
        ("catalyst", ("催化", "消息", "消息面", "公告", "研报", "题材", "概念", "龙虎榜", "事件")),
        ("fundamental", ("基本面", "财报", "业绩", "利润", "营收", "收入", "现金流", "负债", "roe", "毛利率")),
        (
            "action",
            (
                "买",
                "卖",
                "仓位",
                "减仓",
                "加仓",
                "止损",
                "止盈",
                "操作",
                "入场",
                "目标价",
                "涨到",
                "空间",
                "压力位",
                "未来",
            ),
        ),
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
        risk = dossier.bear_case[0] if dossier.bear_case else "风险证据不足"
        stop = dossier.invalidation[0] if dossier.invalidation else dossier.investment_advice.stop_loss
        answer = (
            f"结论：{quote.name}现在先按“{dossier.investment_advice.action}”处理，"
            f"不要因为单一指标直接加仓。主要风险是{risk}；如果{stop}，就降级观察。"
        )
    elif intent == "trend":
        evidence = _unique(
            [dossier.trend_forecast.summary, *dossier.trend_forecast.drivers]
            + [factor.evidence for factor in dossier.score_factors if factor.available]
        )
        answer = (
            f"结论：{quote.name}的{dossier.trend_forecast.horizon}趋势是"
            f"{dossier.trend_forecast.direction}，但操作上先按“{dossier.investment_advice.action}”。"
            f"{dossier.trend_forecast.summary}"
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
        verdict = _valuation_verdict(quote)
        answer = (
            f"结论：{quote.name}估值{verdict}。{valuation.summary}"
            if valuation
            else f"结论：{quote.name}当前缺少足够的估值比较证据，不能只凭 PE/PB 判断贵不贵。"
        )
    elif intent == "fundamental":
        quality = _dimension(dossier, "fundamental_quality")
        research = _dimension(dossier, "research")
        valuation = _dimension(dossier, "valuation")
        quality_summary = quality.summary if quality else "基本面质量维度暂缺"
        research_summary = (
            research.summary if research and research.available else "公告研报增强数据暂缺，不能只用行情替代财报验证"
        )
        valuation_summary = valuation.summary if valuation and valuation.available else "估值约束暂缺"
        evidence = _unique(
            [
                quality_summary,
                *(_dimension_evidence(quality)),
                f"公告研报：{research_summary}",
                *(_dimension_evidence(research) if research and research.available else []),
                f"估值约束：{valuation_summary}",
            ]
        )
        verdict = "有可用线索，但仍要补财报细节" if research and research.available else "只能做轮廓判断，财报/公告研报证据还不够"
        answer = (
            f"结论：{quote.name}基本面{verdict}。{quality_summary}；"
            f"公告研报：{research_summary}；估值约束：{valuation_summary}。"
        )
        next_actions = _unique(
            [
                f"优先补读{quote.name}最近年报、季报和业绩预告",
                "核对营收、利润、现金流和负债变化，别只看价格走势",
                *next_actions,
            ]
        )[:4]
    elif intent == "catalyst":
        catalyst = _dimension(dossier, "catalyst")
        research = _dimension(dossier, "research")
        sector = _dimension(dossier, "sector")
        catalyst_summary = (
            catalyst.summary if catalyst and catalyst.available else "未拿到可验证的催化证据"
        )
        research_summary = (
            research.summary if research and research.available else "公告研报暂缺，不能确认消息面原因"
        )
        sector_summary = sector.summary if sector and sector.available else f"{quote.sector or '所属板块'}联动待确认"
        evidence = _unique(
            [
                f"催化与事件：{catalyst_summary}",
                *(_dimension_evidence(catalyst)),
                f"公告研报：{research_summary}",
                *(_dimension_evidence(research) if research and research.available else []),
                f"板块联动：{sector_summary}",
            ]
        )
        verdict = "已有待核验线索" if catalyst and catalyst.available else "还没有被本地证据确认"
        answer = (
            f"结论：{quote.name}催化证据{verdict}。{catalyst_summary}；"
            f"公告研报：{research_summary}；板块/题材：{sector_summary}。"
            "没有源链接或最新公告确认前，不把消息当成交易理由。"
        )
        next_actions = _unique(
            [
                f"打开{quote.name}公告与研报，确认是否有业绩、订单、政策或题材催化",
                f"回到大盘页看{quote.sector or '所属板块'}是否同步扩散",
                *next_actions,
            ]
        )[:4]
    elif intent == "movement":
        direction = _movement_direction(question, dossier)
        evidence = _movement_evidence(dossier, direction)
        drivers = _movement_drivers(dossier, direction)
        movement_text = "，".join(evidence[:3]) if evidence else "近端涨跌幅证据不足"
        driver_text = "；".join(drivers[:3]) if drivers else "近期价格异动证据不足"
        answer = (
            f"结论：{quote.name}近期{direction}不能直接归因到单一消息，"
            f"先按行情结构解释。{movement_text}；"
            f"本地证据显示：{driver_text}。"
            f"若要确认真正诱因，下一步核对公告、研报和{quote.sector or '所属板块'}新闻。"
        )
        next_actions = _unique(
            [
                f"核对{quote.name}最近公告、业绩预告和交易异动公告",
                f"回到大盘页检查{quote.sector or '所属板块'}是否同步走弱",
                "看后续 1-3 个交易日是否放量止跌或继续破位",
                *next_actions,
            ]
        )[:4]
    elif intent == "action":
        advice = dossier.investment_advice
        evidence = _unique(
            [*advice.rationale, advice.entry_plan, advice.stop_loss, advice.take_profit]
        )
        if _is_price_target_question(question):
            price_text = f"当前价约 {_price(quote.price)}，" if quote.price is not None else ""
            answer = (
                f"结论：不能精确预测会涨到多少；{quote.name}{price_text}"
                f"上方先按止盈/压力纪律看：{_short_text(advice.take_profit, 72)}。"
                f"若没有放量和趋势继续确认，就不要把目标价当承诺。"
            )
        else:
            answer = (
                f"结论：{quote.name}当前建议为“{advice.action}”。"
                f"{_short_text(advice.position_hint, 70)}；"
                f"入场：{_short_text(advice.entry_plan, 72)}；"
                f"止损：{_short_text(advice.stop_loss, 72)}。"
            )
    else:
        evidence = _unique(
            [*dossier.bull_case, *dossier.bear_case]
            + [factor.evidence for factor in dossier.score_factors if factor.available]
        )
        final_gate, _ = _final_gate(dossier)
        bull = dossier.bull_case[0] if dossier.bull_case else "正向证据不足"
        bear = dossier.bear_case[0] if dossier.bear_case else "反方证据不足"
        next_action = dossier.next_actions[0] if dossier.next_actions else "继续补齐证据后再复核"
        answer = (
            f"结论：{final_gate}。{quote.name}当前动作是“{dossier.investment_advice.action}”，"
            f"综合分 {dossier.stance_score or 0:.0f}/100，证据覆盖 {_percent(dossier.evidence_coverage)}。"
            f"核心理由：{_short_text(bull, 56)}；主要风险：{_short_text(bear, 56)}；"
            f"下一步：{_short_text(next_action, 56)}。"
        )

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
    focus_symbol: str | None = None,
) -> AskStockResponse:
    rebalance_mode = is_rebalance_plan_question(question)
    if not holdings:
        empty_answer = (
            "当前账户没有持仓记录，无法生成调仓计划。先在持仓页录入股票、成本、目标仓位后再问调仓。"
            if rebalance_mode
            else "当前账户没有持仓记录，无法生成组合风险排序。先在持仓页录入股票、成本、目标仓位后再问组合问题。"
        )
        return AskStockResponse(
            kind="portfolio_analysis",
            question=" ".join(question.split()),
            intent="portfolio",
            answer=empty_answer,
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
    plan_rows = sorted(holdings, key=_rebalance_priority, reverse=True)
    total_value = sum(item.market_value or 0 for item in holdings)
    concentration = _portfolio_concentration(holdings)
    risky = sum(1 for item in holdings if item.risk_flags)
    top = ranked[0]
    overweight = sum(1 for item in holdings if item.drift is not None and item.drift > 0.1)
    missing_invalidation = sum(1 for item in holdings if not item.item.invalidation.strip())
    focused = next((item for item in holdings if item.item.symbol == focus_symbol), None)
    actionable = sum(1 for item in holdings if _rebalance_abs_value(item) >= 1_000)
    net_rebalance = sum(item.rebalance_value or 0 for item in holdings)
    if rebalance_mode:
        priority = plan_rows[0]
        answer = (
            f"调仓计划先处理 {priority.item.name}（{priority.item.symbol}）："
            f"当前占比 {_percent(priority.portfolio_weight)}，目标 {_percent(priority.item.target_weight)}，"
            f"偏离金额 {_money(priority.rebalance_value)}，建议股数 {_signed_shares(priority.rebalance_quantity)}。"
            f"全组合共有 {actionable} 个持仓偏离金额超过 1,000 元。"
        )
    elif focus_symbol and focused is None:
        answer = (
            f"当前账户没有 {focus_symbol} 的持仓记录；组合诊断仍按你的账户现有持仓生成，"
            f"最需要先复核的是 {top.item.name}（{top.item.symbol}）。"
        )
    elif focused is not None:
        rank = ranked.index(focused) + 1
        answer = (
            f"{focused.item.name}（{focused.item.symbol}）在当前组合风险排序第 {rank}，"
            f"组合占比 {_percent(focused.portfolio_weight)}，目标仓位 {_percent(focused.item.target_weight)}，"
            f"偏离 {_signed_percent(focused.drift)}，动作建议 {focused.action}。"
        )
    else:
        answer = (
            f"当前组合最需要先复核的是 {top.item.name}（{top.item.symbol}）。"
            f"持仓动作建议为 {top.action}，"
            f"当前盈亏 {_pct(top.pnl_pct)}，组合占比 {_percent(top.portfolio_weight)}。"
        )
    answer = (
        f"{answer} 最大单票占比 {concentration['max_weight_text']}，"
        f"最高行业集中在 {concentration['top_sector_text']}。"
    )
    next_actions = (
        _rebalance_next_actions(plan_rows)
        if rebalance_mode
        else _unique(action for item in ranked[:3] for action in item.next_actions)[:5]
    )
    return AskStockResponse(
        kind="portfolio_analysis",
        question=" ".join(question.split()),
        intent="portfolio",
        answer=answer,
        evidence=[
            f"最大单票：{concentration['max_holding_text']}",
            f"行业集中：{concentration['top_sector_text']}",
            f"超目标持仓 {overweight} 个，缺少失效条件 {missing_invalidation} 个。",
            *[item.conclusion for item in ranked[:3]],
        ][:5],
        risks=_unique(flag for item in ranked for flag in item.risk_flags)[:5],
        next_actions=next_actions,
        metrics=[
            AskStockMetric(label="持仓数量", value=str(len(holdings)), tone="neutral"),
            AskStockMetric(label="总市值", value=_money(total_value or None), tone="neutral"),
            *(
                [
                    AskStockMetric(
                        label="需调仓",
                        value=str(actionable),
                        tone="negative" if actionable else "positive",
                    ),
                    AskStockMetric(
                        label="净调整",
                        value=_money(net_rebalance),
                        tone=_rebalance_tone(net_rebalance),
                    ),
                ]
                if rebalance_mode
                else []
            ),
            AskStockMetric(
                label="最大单票",
                value=concentration["max_weight_text"],
                tone="negative" if concentration["max_weight"] > 0.35 else "neutral",
            ),
            AskStockMetric(
                label="行业集中",
                value=concentration["top_sector_weight_text"],
                tone="negative" if concentration["top_sector_weight"] > 0.5 else "neutral",
            ),
            AskStockMetric(
                label="风险持仓",
                value=str(risky),
                tone="negative" if risky else "positive",
            ),
            AskStockMetric(label="最需复核", value=top.item.name, tone="negative" if top.risk_flags else "neutral"),
        ],
        factors=_portfolio_factors(
            concentration=concentration,
            risky=risky,
            overweight=overweight,
            missing_invalidation=missing_invalidation,
            actionable=actionable,
            rebalance_mode=rebalance_mode,
        ),
        rows=[
            _rebalance_row(item) if rebalance_mode else _holding_row(item)
            for item in (plan_rows if rebalance_mode else ranked)[:8]
        ],
        columns=(
            [
                "股票代码",
                "股票简称",
                "行业",
                "组合占比",
                "目标仓位",
                "偏离",
                "偏离金额",
                "建议股数",
                "优先级",
                "动作",
                "风险",
            ]
            if rebalance_mode
            else [
                "股票代码",
                "股票简称",
                "行业",
                "组合占比",
                "目标仓位",
                "偏离",
                "盈亏",
                "动作",
                "风险",
            ]
        ),
        observed_at=observed_at,
        source="账户持仓 + 本地行情快照 + 确定性分析",
        disclaimer="研究辅助信息，不构成投资建议。",
    )


def _compact(value: str) -> str:
    return "".join(value.split())


def _stock_name_key(name: str) -> str:
    normalized = _compact(name).casefold()
    return re.sub(r"^(\*?st|xd|xr|dr|n|c)", "", normalized)


def _name_aliases(name: str) -> list[str]:
    if len(name) <= 2:
        return []
    aliases = {name[:2]}
    suffix = name[-2:]
    if not _is_generic_name_suffix(suffix):
        aliases.add(suffix)
    return [alias for alias in aliases if len(alias) >= 2]


def _is_generic_name_suffix(value: str) -> bool:
    weak_suffixes = {"股份", "控股", "集团", "证券", "银行", "科技", "管业"}
    return "股" in value or value in weak_suffixes


def _alias_counts(quotes: list[EquityQuote]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for quote in quotes:
        for alias in _name_aliases(_stock_name_key(quote.name)):
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


def _signed_percent(value: float | None) -> str:
    if value is None:
        return "—"
    sign = "+" if value > 0 else ""
    return f"{sign}{value * 100:.1f}%"


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


def _risk_count(dossier: StockDossier) -> int:
    return sum(1 for factor in dossier.score_factors if factor.available and factor.signal == "negative") + len(dossier.bear_case)


def _support_count(dossier: StockDossier) -> int:
    return sum(1 for factor in dossier.score_factors if factor.available and factor.signal == "positive") + len(dossier.bull_case)


def _gap_count(dossier: StockDossier) -> int:
    return len(dossier.missing_evidence)


def _final_gate(dossier: StockDossier) -> tuple[str, AskStockMetricTone]:
    action = dossier.investment_advice.action
    score = dossier.stance_score
    risk_count = _risk_count(dossier)
    support_count = _support_count(dossier)
    if score is None or dossier.evidence_coverage < 0.45:
        return "证据不足", "missing"
    if action in {"可小仓试错", "持有观察"} and support_count >= risk_count:
        return "进入交易计划", "positive"
    if action in {"等待回踩", "继续观察"}:
        return "观察等确认", "neutral"
    if risk_count > support_count:
        return "先守失效线", "negative"
    return action, _metric_tone(score, good=60, bad=45)


def _ledger_gate(dossier: StockDossier) -> tuple[str, AskStockMetricTone]:
    risk_count = _risk_count(dossier)
    support_count = _support_count(dossier)
    gap_count = _gap_count(dossier)
    if dossier.evidence_coverage < 0.6 or gap_count >= 2:
        return "先补证据", "missing"
    if risk_count > support_count:
        return "反方占优", "negative"
    return "证据够用", "positive"


def _gate_detail(dossier: StockDossier) -> str:
    final_gate, _ = _final_gate(dossier)
    ledger_gate, _ = _ledger_gate(dossier)
    return (
        f"FINAL GATE：{final_gate}；LEDGER GATE：{ledger_gate}"
        f"（覆盖 {_percent(dossier.evidence_coverage)}，支持 {_support_count(dossier)}，"
        f"反方 {_risk_count(dossier)}，缺口 {_gap_count(dossier)}）。"
    )


def _with_gate_summary(answer: str, dossier: StockDossier) -> str:
    return f"{_gate_detail(dossier)}{answer}"


def _valuation_verdict(quote: EquityQuote) -> str:
    pe = quote.pe
    pb = quote.pb
    if pe is None and pb is None:
        return "证据不足"
    if (pe is not None and pe <= 15) or (pb is not None and pb <= 1.5):
        return "不贵，但还要看盈利质量和行业风险"
    if (pe is not None and pe > 50) or (pb is not None and pb > 8):
        return "偏贵，除非增长或资产质量能继续兑现"
    if (pe is not None and pe <= 30) and (pb is None or pb <= 5):
        return "不算贵，但不是单凭便宜就能参与"
    return "偏中性，贵不贵要放到同行和自身历史区间里看"


def _dimension(dossier: StockDossier, key: str) -> StockAnalysisDimension | None:
    return next((item for item in dossier.analysis_dimensions if item.key == key), None)


def _dimension_evidence(dimension: StockAnalysisDimension | None) -> list[str]:
    if dimension is None:
        return []
    return [dimension.summary, *dimension.evidence]


def _is_price_target_question(question: str) -> bool:
    normalized = _compact(question)
    return any(
        keyword in normalized
        for keyword in ("涨到多少", "能涨多少", "目标价", "未来涨", "上涨空间", "压力位")
    )


def _is_movement_question(normalized_question: str) -> bool:
    movement_patterns = (
        "为什么跌",
        "为啥跌",
        "怎么跌",
        "大跌",
        "暴跌",
        "跌这么多",
        "跌停",
        "最近跌",
        "近期跌",
        "为什么涨",
        "为啥涨",
        "怎么涨",
        "大涨",
        "暴涨",
        "涨这么多",
        "涨停",
        "最近涨",
        "近期涨",
        "异动",
        "发生了什么",
        "怎么回事",
    )
    return any(pattern in normalized_question for pattern in movement_patterns)


def _movement_direction(question: str, dossier: StockDossier) -> str:
    normalized = _compact(question)
    if any(keyword in normalized for keyword in ("跌", "回落", "杀跌", "跳水")):
        return "下跌"
    if any(keyword in normalized for keyword in ("涨", "拉升", "走强", "反弹")):
        return "上涨"
    recent = _period_return(dossier.bars, 5)
    if recent is None:
        recent = dossier.quote.change_pct
    if recent is not None and recent < 0:
        return "下跌"
    if recent is not None and recent > 0:
        return "上涨"
    return "异动"


def _period_return(bars: list[Bar], days: int) -> float | None:
    if len(bars) <= days:
        return None
    base = bars[-days - 1].close
    latest = bars[-1].close
    if base <= 0:
        return None
    return (latest / base - 1) * 100


def _movement_evidence(dossier: StockDossier, direction: str) -> list[str]:
    quote = dossier.quote
    rows: list[str] = []
    if quote.change_pct is not None:
        rows.append(f"当日涨跌幅 {_pct(quote.change_pct)}")
    for days in (5, 20):
        value = _period_return(dossier.bars, days)
        if value is not None:
            rows.append(f"近{days}日涨跌幅 {_pct(value)}")
    if quote.volume_ratio is not None:
        rows.append(f"量比 {quote.volume_ratio:.1f}，{'放量波动' if quote.volume_ratio >= 1.5 else '量能未明显放大'}")
    if quote.net_flow is not None:
        rows.append(f"资金流 {_signed_money(quote.net_flow)}")
    if not rows:
        rows.append(f"本地行情暂不足以量化近期{direction}幅度")
    return rows


def _movement_drivers(dossier: StockDossier, direction: str) -> list[str]:
    quote = dossier.quote
    technical = dossier.technical
    drivers: list[str] = []
    if technical is not None and quote.price is not None:
        if direction == "下跌":
            if technical.ma20 is not None and quote.price < technical.ma20:
                drivers.append(f"价格低于 MA20（{technical.ma20:.2f}），短线结构偏弱")
            if technical.support is not None and quote.price <= technical.support * 1.01:
                drivers.append(f"价格贴近近 20 日支撑 {technical.support:.2f}，破位压力上升")
            if technical.max_drawdown60 is not None and technical.max_drawdown60 > 15:
                drivers.append(f"60 日最大回撤 {technical.max_drawdown60:.1f}%，修复压力偏大")
        elif direction == "上涨":
            if technical.ma20 is not None and quote.price > technical.ma20:
                drivers.append(f"价格站上 MA20（{technical.ma20:.2f}），短线结构转强")
            if technical.resistance is not None and quote.price >= technical.resistance * 0.98:
                drivers.append(f"价格接近近 20 日压力 {technical.resistance:.2f}，需要量能继续确认")
        if technical.atr_pct is not None and technical.atr_pct > 3:
            drivers.append(f"ATR 占现价 {technical.atr_pct:.1f}%，波动已经偏高")
    if quote.net_flow is not None:
        if quote.net_flow < 0:
            drivers.append(f"净流出 {_money(abs(quote.net_flow))}，资金没有给价格提供支撑")
        elif quote.net_flow > 0:
            drivers.append(f"净流入 {_money(quote.net_flow)}，资金对价格有托举")
    if quote.volume_ratio is not None and quote.volume_ratio >= 1.5:
        drivers.append(f"量比 {quote.volume_ratio:.1f}，说明这不是安静波动，需要继续看承接")
    factor_drivers = [
        factor.evidence
        for factor in dossier.score_factors
        if factor.available and factor.signal == ("negative" if direction == "下跌" else "positive")
    ]
    return _unique([*drivers, *factor_drivers])[:5]


def _short_text(value: str, limit: int = 72) -> str:
    compacted = " ".join(value.split())
    return compacted if len(compacted) <= limit else f"{compacted[:limit].rstrip()}..."


def _money(value: float | None) -> str:
    if value is None:
        return "—"
    if abs(value) >= 100_000_000:
        return f"{value / 100_000_000:.1f} 亿"
    if abs(value) >= 10_000:
        return f"{value / 10_000:.0f} 万"
    return f"{value:.0f}"


def _signed_money(value: float | None) -> str:
    if value is None:
        return "—"
    sign = "+" if value > 0 else ""
    return f"{sign}{_money(value)}"


def _signed_shares(value: float | None) -> str:
    if value is None:
        return "—"
    shares = round(value)
    if shares == 0:
        return "0 股"
    sign = "+" if shares > 0 else ""
    return f"{sign}{shares:g} 股"


def _stock_metrics(dossier: StockDossier, holding: HoldingDossier | None) -> list[AskStockMetric]:
    quote = dossier.quote
    score = dossier.stance_score
    confidence = dossier.investment_advice.confidence
    final_gate, final_gate_tone = _final_gate(dossier)
    ledger_gate, ledger_gate_tone = _ledger_gate(dossier)
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
        AskStockMetric(label="FINAL GATE", value=final_gate, tone=final_gate_tone),
        AskStockMetric(label="LEDGER GATE", value=ledger_gate, tone=ledger_gate_tone),
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
            *metrics[4:6],
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
        "行业": holding.quote.sector or "待补",
        "组合占比": _percent(holding.portfolio_weight),
        "目标仓位": _percent(holding.item.target_weight),
        "偏离": _signed_percent(holding.drift),
        "盈亏": _pct(holding.pnl_pct),
        "动作": holding.action,
        "风险": "；".join(holding.risk_flags) if holding.risk_flags else "未触发",
    }


def _rebalance_row(holding: HoldingDossier) -> dict[str, JsonScalar]:
    return {
        "股票代码": holding.item.symbol,
        "股票简称": holding.item.name,
        "行业": holding.quote.sector or "待补",
        "组合占比": _percent(holding.portfolio_weight),
        "目标仓位": _percent(holding.item.target_weight),
        "偏离": _signed_percent(holding.drift),
        "偏离金额": _signed_money(holding.rebalance_value),
        "建议股数": _signed_shares(holding.rebalance_quantity),
        "优先级": _rebalance_priority_label(holding),
        "动作": holding.action,
        "风险": "；".join(holding.risk_flags) if holding.risk_flags else "未触发",
    }


def _portfolio_concentration(holdings: list[HoldingDossier]) -> PortfolioConcentration:
    weighted = [item for item in holdings if item.portfolio_weight is not None]
    max_holding = max(weighted, key=lambda item: item.portfolio_weight or 0, default=None)
    sector_weights: dict[str, float] = {}
    for item in weighted:
        sector = item.quote.sector or "行业待补"
        sector_weights[sector] = sector_weights.get(sector, 0.0) + (item.portfolio_weight or 0.0)
    top_sector, top_sector_weight = max(
        sector_weights.items(), key=lambda item: item[1], default=("—", 0.0)
    )
    max_weight = max_holding.portfolio_weight if max_holding and max_holding.portfolio_weight is not None else 0.0
    return {
        "max_holding_text": (
            f"{max_holding.item.name} {_percent(max_holding.portfolio_weight)}"
            if max_holding is not None
            else "—"
        ),
        "max_weight": max_weight,
        "max_weight_text": _percent(max_weight) if max_holding is not None else "—",
        "top_sector": top_sector,
        "top_sector_weight": top_sector_weight,
        "top_sector_weight_text": _percent(top_sector_weight) if top_sector != "—" else "—",
        "top_sector_text": (
            f"{top_sector} {_percent(top_sector_weight)}" if top_sector != "—" else "—"
        ),
    }


def _portfolio_factors(
    *,
    concentration: PortfolioConcentration,
    risky: int,
    overweight: int,
    missing_invalidation: int,
    actionable: int,
    rebalance_mode: bool,
) -> list[AskStockFactor]:
    max_weight = concentration["max_weight"]
    top_sector_weight = concentration["top_sector_weight"]
    factors = [
        AskStockFactor(
            label="最大单票集中度",
            impact=-10 if max_weight > 0.35 else 3,
            signal="negative" if max_weight > 0.35 else "neutral",
            evidence=f"最大单票占比 {concentration['max_weight_text']}，超过 35% 需要复核分散度。",
        ),
        AskStockFactor(
            label="行业集中度",
            impact=-8 if top_sector_weight > 0.5 else 2,
            signal="negative" if top_sector_weight > 0.5 else "neutral",
            evidence=f"最高行业为 {concentration['top_sector_text']}，超过 50% 需要检查同向风险。",
        ),
        AskStockFactor(
            label="目标仓位偏离",
            impact=-6 if overweight else 2,
            signal="negative" if overweight else "neutral",
            evidence=f"{overweight} 个持仓高于目标仓位 10 个百分点以上。",
        ),
        AskStockFactor(
            label="风控记录完整度",
            impact=-6 if missing_invalidation else 3,
            signal="negative" if missing_invalidation else "positive",
            evidence=f"{missing_invalidation} 个持仓缺少失效条件。",
        ),
        AskStockFactor(
            label="风险旗标数量",
            impact=-5 if risky else 2,
            signal="negative" if risky else "positive",
            evidence=f"{risky} 个持仓触发风险旗标。",
        ),
    ]
    if rebalance_mode:
        factors.insert(
            0,
            AskStockFactor(
                label="调仓执行量",
                impact=-6 if actionable else 3,
                signal="negative" if actionable else "positive",
                evidence=f"{actionable} 个持仓偏离金额超过 1,000 元，建议先处理高优先级项。",
            ),
        )
    return factors[:12]


def _rebalance_abs_value(holding: HoldingDossier) -> float:
    return abs(holding.rebalance_value or 0.0)


def _rebalance_priority(holding: HoldingDossier) -> float:
    return _rebalance_abs_value(holding) + _holding_risk_score(holding) * 500


def _rebalance_priority_label(holding: HoldingDossier) -> str:
    value = _rebalance_abs_value(holding)
    if value >= 20_000 or holding.risk_flags:
        return "高"
    if value >= 5_000:
        return "中"
    return "低"


def _rebalance_tone(value: float | None) -> AskStockMetricTone:
    if value is None:
        return "missing"
    if abs(value) < 1_000:
        return "positive"
    return "negative"


def _rebalance_next_actions(holdings: list[HoldingDossier]) -> list[str]:
    actions = []
    for item in holdings[:3]:
        shares = _signed_shares(item.rebalance_quantity)
        if item.rebalance_value is None or abs(item.rebalance_value) < 1_000:
            actions.append(f"{item.item.name} 接近目标仓位，暂不因微小偏离交易")
        elif item.rebalance_value < 0:
            actions.append(f"{item.item.name} 优先减仓 {shares}，先把单票/目标偏离降下来")
        else:
            actions.append(f"{item.item.name} 可补仓 {shares}，但需先确认个股证据未恶化")
    actions.append("调仓前核对流动性、失效条件和是否触发止损，不按表格机械交易")
    return _unique(actions)[:5]


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
