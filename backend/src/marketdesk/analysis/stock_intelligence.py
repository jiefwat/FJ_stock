import re
from datetime import UTC, datetime, timedelta

from marketdesk.models import (
    FinancialHealth,
    FinancialPeriod,
    StockNewsItem,
    StockNewsSentiment,
)

HARD_RISK_TERMS = (
    "立案调查",
    "立案告知",
    "监管处罚",
    "行政处罚",
    "退市风险",
    "终止上市",
    "预亏",
    "利润大幅下降",
    "业绩大幅下降",
    "债务违约",
    "债务逾期",
)
NEGATIVE_TERMS = (
    "承压",
    "下滑",
    "下降",
    "亏损",
    "风险",
    "处罚",
    "调查",
    "违约",
    "减持",
)
POSITIVE_TERMS = (
    "增长",
    "增持",
    "中标",
    "获批",
    "分红",
    "回购",
    "扭亏",
    "订单",
)


def _is_consistent_slowdown(values: list[float | None]) -> bool:
    available = [value for value in values[:3] if value is not None]
    return len(available) == 3 and all(
        newer <= older - 5 for newer, older in zip(available, available[1:], strict=False)
    )


def _news_event_key(item: StockNewsItem) -> str:
    return re.sub(r"[\W_]+", "", item.title, flags=re.UNICODE).casefold()


def analyse_financial_health(periods: list[FinancialPeriod]) -> FinancialHealth:
    if not periods:
        return FinancialHealth(available=False, conclusion="财报待补")

    ordered = sorted(periods, key=lambda item: item.report_date, reverse=True)
    latest = ordered[0]
    points: list[float] = []
    risks: list[str] = []

    if latest.revenue_yoy is not None:
        points.append(12 if latest.revenue_yoy >= 5 else 6 if latest.revenue_yoy >= 0 else -8)
        if latest.revenue_yoy < 0:
            risks.append("营业收入同比下降")

    if latest.net_profit_yoy is not None:
        if latest.net_profit_yoy >= 10:
            points.append(18)
        elif latest.net_profit_yoy >= 0:
            points.append(8)
        elif latest.net_profit_yoy <= -30:
            points.append(-25)
        else:
            points.append(-15)
        if latest.net_profit_yoy < 0:
            risks.append("盈利同比下滑")

    if latest.roe is not None:
        points.append(16 if latest.roe >= 15 else 8 if latest.roe >= 8 else -12 if latest.roe < 5 else 0)
        if latest.roe < 5:
            risks.append("净资产收益率偏低")

    if latest.operating_cash_flow_per_share is not None:
        points.append(8 if latest.operating_cash_flow_per_share > 0 else -15)
        if latest.operating_cash_flow_per_share < 0:
            risks.append("经营现金流为负")

    if latest.cash_receipts_to_revenue is not None:
        points.append(8 if latest.cash_receipts_to_revenue >= 90 else -15 if latest.cash_receipts_to_revenue < 70 else 0)
        if latest.cash_receipts_to_revenue < 70:
            risks.append("收入转化为现金偏弱")

    if latest.debt_to_assets is not None:
        points.append(8 if latest.debt_to_assets <= 50 else -18 if latest.debt_to_assets > 70 else -10 if latest.debt_to_assets > 60 else 0)
        if latest.debt_to_assets > 70:
            risks.append("资产负债率偏高")

    if _is_consistent_slowdown([item.revenue_yoy for item in ordered]):
        points.append(-6)
        risks.append("营业收入增速连续放缓")

    if _is_consistent_slowdown([item.net_profit_yoy for item in ordered]):
        points.append(-6)
        risks.append("盈利增速连续放缓")

    if not points:
        return FinancialHealth(
            available=True,
            conclusion="财务指标不足",
            report_date=latest.report_date,
            periods=ordered,
        )

    score = max(0.0, min(100.0, 50 + sum(points)))
    impact = 6 if score >= 75 else 3 if score >= 65 else 1 if score >= 55 else -10 if score < 30 else -7 if score < 40 else -3 if score < 50 else 0
    conclusion = (
        "盈利和现金质量较稳"
        if score >= 65
        else "财务表现中性"
        if score >= 50
        else "盈利或现金质量承压"
    )
    return FinancialHealth(
        available=True,
        score=round(score, 1),
        score_impact=impact,
        conclusion=conclusion,
        report_date=latest.report_date,
        risks=list(dict.fromkeys(risks)),
        periods=ordered,
    )


def analyse_stock_news(
    items: list[StockNewsItem],
    *,
    now: datetime | None = None,
    window_days: int = 30,
) -> StockNewsSentiment:
    current = now or datetime.now(UTC)
    cutoff = current - timedelta(days=window_days)
    recent: list[StockNewsItem] = []
    seen_events: set[str] = set()
    for item in sorted(items, key=lambda value: value.published_at, reverse=True):
        if not cutoff <= item.published_at <= current:
            continue
        event_key = _news_event_key(item)
        if event_key in seen_events:
            continue
        seen_events.add(event_key)
        recent.append(item)
    classified: list[StockNewsItem] = []
    hard_risk_count = 0
    positive_count = 0
    negative_count = 0
    neutral_count = 0
    penalty = 0
    risks: list[str] = []

    for item in recent:
        text = f"{item.title} {item.summary}"
        hard_terms = [term for term in HARD_RISK_TERMS if term in text]
        if hard_terms:
            sentiment = "negative"
            hard_risk_count += 1
            negative_count += 1
            age_days = max(0, (current - item.published_at).days)
            penalty -= 3 if age_days <= 7 else 2
            risks.append(f"{item.title}（{hard_terms[0]}）")
        elif any(term in text for term in NEGATIVE_TERMS):
            sentiment = "negative"
            negative_count += 1
        elif any(term in text for term in POSITIVE_TERMS):
            sentiment = "positive"
            positive_count += 1
        else:
            sentiment = "neutral"
            neutral_count += 1
        classified.append(
            item.model_copy(
                update={
                    "sentiment": sentiment,
                    "hard_risk": bool(hard_terms),
                    "hard_risk_terms": hard_terms,
                }
            )
        )

    if hard_risk_count:
        conclusion = f"近{window_days}天有{hard_risk_count}条明确风险"
    elif negative_count > positive_count:
        conclusion = f"近{window_days}天负面信息偏多，未触发硬风险"
    elif positive_count > negative_count:
        conclusion = f"近{window_days}天正面信息较多，不上调评分"
    elif classified:
        conclusion = f"近{window_days}天舆情整体中性"
    else:
        conclusion = f"近{window_days}天暂无相关新闻"

    return StockNewsSentiment(
        available=True,
        window_days=window_days,
        conclusion=conclusion,
        positive_count=positive_count,
        negative_count=negative_count,
        neutral_count=neutral_count,
        hard_risk_count=hard_risk_count,
        score_impact=max(-6, penalty),
        risks=risks,
        items=classified,
    )
