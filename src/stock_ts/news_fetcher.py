from __future__ import annotations

from .models import NewsItem
from .news_intelligence import classify_news_item


def fetch_akshare_stock_news(ak: object, *, symbol: str, limit: int = 20) -> list[NewsItem]:
    try:
        frame = ak.stock_news_em(symbol=symbol)
    except Exception as exc:
        return [
            NewsItem(
                date="latest",
                source="AKShare",
                title="AKShare新闻接口不可用",
                summary=f"{symbol} 新闻抓取失败：{exc}",
                sentiment="neutral",
            )
        ]
    if getattr(frame, "empty", False):
        return [
            NewsItem(
                date="latest",
                source="AKShare",
                title="未获取到相关新闻",
                summary=f"{symbol} 暂无可用新闻结果",
                sentiment="neutral",
            )
        ]

    items: list[NewsItem] = []
    for _index, row in frame.iterrows():
        title = _first_text(row, "新闻标题", "title", "标题")
        if not title:
            continue
        published_at = _first_text(row, "发布时间", "date", "日期")
        summary = _first_text(row, "新闻内容", "summary", "摘要") or title
        classification = classify_news_item(title, summary)
        items.append(
            NewsItem(
                date=published_at[:10] if published_at else "",
                source=_first_text(row, "文章来源", "source", "来源") or "AKShare",
                title=title,
                summary=summary,
                url=_first_text(row, "新闻链接", "url", "链接"),
                sentiment=classification.sentiment,
            )
        )
        if len(items) >= limit:
            break
    return items


def _first_text(row: object, *keys: str) -> str:
    for key in keys:
        value = row.get(key, "")  # type: ignore[attr-defined]
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""
