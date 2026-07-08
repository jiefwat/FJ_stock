from __future__ import annotations

import csv
from pathlib import Path

from .models import DailyBar, NewsItem


def load_price_bars_csv(path: str | Path) -> list[DailyBar]:
    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Price CSV not found: {csv_path}")

    bars: list[DailyBar] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            date = (row.get("date") or row.get("日期") or "").strip()
            if not date:
                continue
            bars.append(
                DailyBar(
                    date=date,
                    open=float(row.get("open") or row.get("开盘") or 0),
                    high=float(row.get("high") or row.get("最高") or 0),
                    low=float(row.get("low") or row.get("最低") or 0),
                    close=float(row.get("close") or row.get("收盘") or 0),
                    volume=float(row.get("volume") or row.get("成交量") or 0),
                )
            )
    if not bars:
        raise ValueError(f"No price bars found in {csv_path}")
    return bars


def load_news_csv(path: str | Path) -> list[NewsItem]:
    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"News CSV not found: {csv_path}")

    items: list[NewsItem] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            title = (row.get("title") or row.get("标题") or "").strip()
            if not title:
                continue
            summary = (row.get("summary") or row.get("摘要") or row.get("content") or "").strip()
            items.append(
                NewsItem(
                    date=(row.get("date") or row.get("日期") or "").strip(),
                    source=(row.get("source") or row.get("来源") or "本地导入").strip(),
                    title=title,
                    summary=summary,
                    url=(row.get("url") or row.get("链接") or "").strip(),
                    sentiment=_normalize_sentiment(row.get("sentiment") or row.get("情绪") or ""),
                )
            )
    if not items:
        raise ValueError(f"No news items found in {csv_path}")
    return items


def _normalize_sentiment(value: str) -> str:
    text = value.strip().lower()
    if text in {"positive", "pos", "利好", "正面"}:
        return "positive"
    if text in {"negative", "neg", "利空", "负面"}:
        return "negative"
    if text in {"neutral", "neu", "中性"}:
        return "neutral"
    return "neutral"
