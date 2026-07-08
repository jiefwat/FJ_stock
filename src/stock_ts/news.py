from __future__ import annotations

from dataclasses import replace

from .models import NewsItem, NewsSentimentReport
from .news_intelligence import classify_news_item


def analyze_news(items: list[NewsItem], trade_date: str | None = None) -> NewsSentimentReport:
    if not items:
        raise ValueError("news items cannot be empty")

    items = _normalize_news_items(items)

    positive_count = sum(1 for item in items if item.sentiment == "positive")
    negative_count = sum(1 for item in items if item.sentiment == "negative")
    neutral_count = len(items) - positive_count - negative_count
    if negative_count > positive_count:
        summary = "消息面偏谨慎，需优先排查利空影响"
    elif positive_count > negative_count:
        summary = "消息面偏积极，但仍需用价格和成交额确认"
    else:
        summary = "消息面中性，等待更多催化或风险信号"

    risks = []
    for item in items:
        if item.sentiment == "negative":
            risks.append(f"{item.title} 可能压制相关板块或持仓情绪")
    if not risks:
        risks.append("未导入明显负面消息，但新闻舆情只作为辅助输入")

    resolved_trade_date = trade_date or next((item.date for item in items if item.date), "latest")
    return NewsSentimentReport(
        trade_date=resolved_trade_date,
        items=items,
        positive_count=positive_count,
        negative_count=negative_count,
        neutral_count=neutral_count,
        summary=summary,
        risks=risks[:5],
    )


def _normalize_news_items(items: list[NewsItem]) -> list[NewsItem]:
    normalized: list[NewsItem] = []
    for item in items:
        if item.sentiment and item.sentiment != "neutral":
            normalized.append(item)
            continue
        classification = classify_news_item(item.title, item.summary)
        normalized.append(replace(item, sentiment=classification.sentiment))
    return normalized
