from __future__ import annotations

import json
import re
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

OpenFunc = Callable[[str, float], bytes]


@dataclass(frozen=True)
class NewsClassification:
    sentiment: str
    risk_tags: list[str] = field(default_factory=list)
    catalyst_tags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class IntelligenceSource:
    id: str
    name: str
    url: str
    source_type: str = "json"
    market: str = "cn"
    scope_type: str = "market"
    enabled: bool = True


@dataclass(frozen=True)
class IntelligenceItem:
    title: str
    source: str
    summary: str = ""
    url: str = ""
    published_at: str = ""
    fetched_at: str = ""
    market: str = "cn"
    scope_type: str = "market"
    symbols: list[str] = field(default_factory=list)
    sentiment: str = "neutral"
    risk_tags: list[str] = field(default_factory=list)
    catalyst_tags: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return {
            "date": self.published_at[:10] if self.published_at else self.fetched_at[:10],
            "source": self.source,
            "title": self.title,
            "summary": self.summary,
            "url": self.url,
            "sentiment": self.sentiment,
            "risk_tags": list(self.risk_tags),
            "catalyst_tags": list(self.catalyst_tags),
            "market": self.market,
            "scope_type": self.scope_type,
            "symbols": list(self.symbols),
            "published_at": self.published_at,
            "fetched_at": self.fetched_at,
        }


@dataclass(frozen=True)
class IntelligenceFetchResult:
    items: list[IntelligenceItem]
    source_statuses: dict[str, str]
    warnings: list[str]


_RISK_PATTERNS = {
    "减持": ["减持", "拟减持"],
    "监管处罚": ["监管处罚", "处罚", "立案", "问询函", "警示函", "涉嫌", "信披违法"],
    "业绩下滑": ["亏损", "业绩下滑", "预亏", "净利润下降"],
    "诉讼纠纷": ["诉讼", "仲裁", "纠纷"],
    "股权质押": ["质押", "平仓风险"],
    "退市风险": ["退市", "ST", "终止上市"],
    "市场下跌": ["跌幅扩大", "熔断", "破位", "跳水", "重挫", "暴跌", "波动风险"],
}


_MARKET_RELEVANCE_KEYWORDS = [
    "A股",
    "港股",
    "美股",
    "沪指",
    "深成指",
    "创业板",
    "科创",
    "指数",
    "涨停",
    "跌停",
    "ETF",
    "板块",
    "主线",
    "概念",
    "半导体",
    "芯片",
    "算力",
    "机器人",
    "AI",
    "商业航天",
    "新能源",
    "汽车",
    "医药",
    "白酒",
    "券商",
    "银行",
    "订单",
    "回购",
    "并购",
    "重组",
    "业绩",
    "中标",
    "净利润",
    "公司",
]


_CHINA_MARKET_KEYWORDS = [
    "A股",
    "港股",
    "H股",
    "中概",
    "中国",
    "国内",
    "沪",
    "深",
    "创业板",
    "科创",
    "北向",
    "人民币",
    "恒生",
]

_FOREIGN_NOISE_KEYWORDS = ["美国", "特朗普", "韩国", "KOSPI", "日经", "欧洲", "美股"]
_FOREIGN_BROKER_NOISE_KEYWORDS = ["摩根大通", "高盛", "通用汽车", "美元", "目标价"]
_PUBLIC_WELFARE_NOISE_KEYWORDS = ["捐赠", "驰援", "救灾", "防汛保供"]
_MARKET_ACTION_KEYWORDS = ["股价", "A股", "港股", "订单", "业绩", "回购", "并购", "重组"]

_CATALYST_NEGATION_PATTERNS = [
    "不直接开展",
    "不涉及",
    "未涉及",
    "未开展",
    "暂无",
    "没有",
    "不生产",
    "不研发",
    "不属于",
]

_CATALYST_PATTERNS = {
    "AI算力": ["AI", "人工智能", "算力", "数据中心", "大模型"],
    "机器人": ["机器人", "人形机器人"],
    "商业航天": ["商业航天", "卫星", "火箭"],
    "并购重组": ["并购", "重组", "收购", "资产注入"],
    "订单": ["订单", "中标", "签订合同", "大单"],
    "回购": ["回购"],
    "业绩增长": ["业绩增长", "预增", "净利润增长", "扭亏"],
}


def classify_news_item(title: str, summary: str = "") -> NewsClassification:
    text = f"{title} {summary}"
    risk_tags = _matched_tags(text, _RISK_PATTERNS)
    catalyst_tags = _matched_tags(text, _CATALYST_PATTERNS)
    if _has_catalyst_negation(text):
        catalyst_tags = []
    if risk_tags and not catalyst_tags:
        sentiment = "negative"
    elif catalyst_tags and not risk_tags:
        sentiment = "positive"
    elif risk_tags and catalyst_tags:
        sentiment = "negative" if len(risk_tags) >= len(catalyst_tags) else "positive"
    else:
        sentiment = "neutral"
    return NewsClassification(sentiment=sentiment, risk_tags=risk_tags, catalyst_tags=catalyst_tags)


def is_market_relevant_news(title: str, summary: str = "") -> bool:
    text = f"{title} {summary}".upper()
    if _has_any(text, _FOREIGN_NOISE_KEYWORDS) and not _has_any(text, _CHINA_MARKET_KEYWORDS):
        return False
    if _has_any(text, _FOREIGN_BROKER_NOISE_KEYWORDS) and not _has_any(
        text, _CHINA_MARKET_KEYWORDS
    ):
        return False
    if _has_any(text, _PUBLIC_WELFARE_NOISE_KEYWORDS) and not _has_any(
        text, _MARKET_ACTION_KEYWORDS
    ):
        return False
    return _has_any(text, _MARKET_RELEVANCE_KEYWORDS)


def _has_any(upper_text: str, keywords: list[str]) -> bool:
    return any(keyword.upper() in upper_text for keyword in keywords)


def _has_catalyst_negation(text: str) -> bool:
    return any(pattern in text for pattern in _CATALYST_NEGATION_PATTERNS)


def dedupe_items_by_url(items: list[IntelligenceItem]) -> list[IntelligenceItem]:
    seen: set[str] = set()
    deduped: list[IntelligenceItem] = []
    for item in items:
        key = item.url.strip() or _normalize_text(item.title)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def fetch_json_intelligence_sources(
    sources: list[IntelligenceSource],
    *,
    opener: OpenFunc | None = None,
    timeout: float = 8.0,
    limit_per_source: int = 20,
) -> IntelligenceFetchResult:
    open_func = opener or _default_open
    statuses: dict[str, str] = {}
    warnings: list[str] = []
    items: list[IntelligenceItem] = []
    for source in sources:
        if not source.enabled:
            statuses[source.id] = "skipped"
            continue
        try:
            payload = json.loads(open_func(source.url, timeout).decode("utf-8", "replace"))
            parsed = _parse_json_items(payload, source, limit=limit_per_source)
            statuses[source.id] = f"ok:{len(parsed)}"
            items.extend(parsed)
        except Exception as exc:
            statuses[source.id] = f"failed:{type(exc).__name__}:{str(exc)[:120]}"
            warnings.append(f"{source.name} 抓取失败：{type(exc).__name__}")
    return IntelligenceFetchResult(
        items=dedupe_items_by_url(items),
        source_statuses=statuses,
        warnings=warnings,
    )


def default_intelligence_sources_from_env(raw: str | None) -> list[IntelligenceSource]:
    if not raw:
        return []
    sources: list[IntelligenceSource] = []
    for index, chunk in enumerate(raw.split(","), start=1):
        url = chunk.strip()
        if not url or not _safe_http_url(url):
            continue
        sources.append(IntelligenceSource(id=f"env-{index}", name=f"外部情报源{index}", url=url))
    return sources


def _parse_json_items(
    payload: Any, source: IntelligenceSource, *, limit: int
) -> list[IntelligenceItem]:
    rows = (
        payload.get("items", payload.get("data", payload.get("news", [])))
        if isinstance(payload, dict)
        else payload
    )
    if not isinstance(rows, list):
        return []
    fetched_at = datetime.now(timezone.utc).isoformat()
    items: list[IntelligenceItem] = []
    for row in rows[:limit]:
        if not isinstance(row, dict):
            continue
        title = str(row.get("title") or row.get("新闻标题") or row.get("content") or "").strip()
        if not title:
            continue
        summary = str(row.get("summary") or row.get("摘要") or row.get("desc") or "").strip()
        classification = classify_news_item(title, summary)
        items.append(
            IntelligenceItem(
                title=title,
                source=str(row.get("source") or row.get("文章来源") or source.name),
                summary=summary,
                url=str(row.get("url") or row.get("link") or ""),
                published_at=str(
                    row.get("published_at") or row.get("date") or row.get("发布时间") or ""
                ),
                fetched_at=fetched_at,
                market=source.market,
                scope_type=source.scope_type,
                symbols=_symbols_from_row(row),
                sentiment=classification.sentiment,
                risk_tags=classification.risk_tags,
                catalyst_tags=classification.catalyst_tags,
            )
        )
    return items


def _symbols_from_row(row: dict[str, Any]) -> list[str]:
    raw = row.get("symbols") or row.get("codes") or []
    if isinstance(raw, str):
        return re.findall(r"\d{5,6}", raw)
    if isinstance(raw, list):
        return [str(item) for item in raw if str(item).strip()]
    return []


def _matched_tags(text: str, patterns: dict[str, list[str]]) -> list[str]:
    upper_text = text.upper()
    tags: list[str] = []
    for tag, keywords in patterns.items():
        if any(keyword.upper() in upper_text for keyword in keywords):
            tags.append(tag)
    return tags


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", "", text.strip().lower())


def _safe_http_url(url: str) -> bool:
    return url.startswith("https://") or url.startswith("http://")


def _default_open(url: str, timeout: float) -> bytes:
    if not _safe_http_url(url):
        raise ValueError("only http/https intelligence urls are allowed")
    request = urllib.request.Request(url, headers={"User-Agent": "StockTS/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - URL is explicit/env validated.
        return response.read()
