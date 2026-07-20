import re
from datetime import UTC, datetime

from marketdesk.models import (
    DatasetMeta,
    Freshness,
    MarketEvent,
    MarketEventCluster,
    MarketEventRaw,
    MarketEventResult,
)

CATEGORY_META = {
    "policy_support": ("政策与监管", "positive"),
    "capital_style": ("资金与风格", "neutral"),
    "corporate_action": ("公司动作", "positive"),
    "industry_catalyst": ("行业催化", "positive"),
    "risk_alert": ("风险扰动", "negative"),
    "macro_global": ("宏观与海外", "neutral"),
    "other": ("其他热点", "neutral"),
}

CATEGORY_IMPORTANCE_BOOST = {
    "policy_support": 8,
    "risk_alert": 6,
    "corporate_action": 4,
    "industry_catalyst": 3,
    "capital_style": 0,
    "macro_global": 0,
    "other": 0,
}

KEYWORDS = {
    "policy_support": ["政策", "监管", "央企", "国资", "再贷款", "增持", "维护市场", "改革"],
    "capital_style": ["风格", "资金", "低波", "绝对收益", "相对收益", "ETF", "主力"],
    "corporate_action": ["回购", "增持", "减持", "并购", "重组", "分红", "业绩预告"],
    "industry_catalyst": ["AI", "算力", "机器人", "半导体", "新能源", "银行", "白酒", "医药", "订单"],
    "risk_alert": ["下跌", "风险", "暂停", "调查", "亏损", "退市", "暴跌", "紧缺"],
    "macro_global": ["美联储", "关税", "汇率", "美元", "原油", "黄金", "海外", "通胀"],
}

SECTOR_KEYWORDS = {
    "银行": ["银行", "息差", "低波"],
    "央企改革": ["央企", "国资", "国新", "诚通", "维护市场"],
    "证券": ["券商", "证券", "财富管理"],
    "人工智能": ["AI", "Kimi", "大模型", "算力"],
    "算力": ["算力", "GPU", "服务器"],
    "机器人": ["机器人", "具身智能"],
    "半导体": ["半导体", "芯片", "晶圆"],
    "新能源": ["新能源", "光伏", "锂电"],
    "白酒": ["白酒", "高端酒"],
    "医药": ["医药", "创新药"],
    "军工": ["军工", "军贸"],
    "黄金": ["黄金", "贵金属"],
    "石油": ["原油", "石油"],
}


def analyse_market_events(raw_events: list[MarketEventRaw]) -> MarketEventResult:
    events = [_classify_event(item) for item in raw_events]
    events.sort(key=lambda item: (item.importance_score, item.published_at), reverse=True)
    clusters = _clusters(events)
    now = datetime.now(UTC)
    observed_at = max((item.published_at for item in events), default=now)
    return MarketEventResult(
        meta=DatasetMeta(
            source="eastmoney_fast_news",
            observed_at=observed_at,
            fetched_at=now,
            freshness=Freshness.FRESH if events else Freshness.UNAVAILABLE,
            coverage=1.0 if events else 0.0,
            errors=[] if events else ["market events unavailable"],
        ),
        summary=_summary(events, clusters),
        next_actions=_next_actions(events, clusters),
        clusters=clusters,
        events=events,
    )


def _classify_event(raw: MarketEventRaw) -> MarketEvent:
    display_sectors = _readable_sectors(raw.title, raw.summary, raw.related_sectors)
    text = f"{raw.title} {raw.summary} {' '.join(raw.related_sectors)} {' '.join(display_sectors)}"
    scores = {
        key: sum(1 for keyword in keywords if keyword.lower() in text.lower())
        for key, keywords in KEYWORDS.items()
    }
    category = max(scores, key=lambda key: scores[key])
    if scores[category] == 0:
        category = "other"
    label, default_signal = CATEGORY_META[category]
    tags = [label, *display_sectors[:3]]
    if category == "policy_support" and "政策支持" not in tags:
        tags.append("政策支持")
    if category == "capital_style" and "资金风格" not in tags:
        tags.append("资金风格")
    sentiment = _sentiment(category, text, default_signal)
    importance = min(
        100.0,
        45
        + scores.get(category, 0) * 10
        + min(len(raw.related_symbols), 3) * 5
        + min(len(raw.related_sectors), 3) * 4
        + (8 if "【" in raw.summary else 0)
        + CATEGORY_IMPORTANCE_BOOST.get(category, 0),
    )
    return MarketEvent(
        id=raw.id,
        title=raw.title,
        summary=raw.summary,
        source=raw.source,
        url=raw.url,
        published_at=raw.published_at,
        related_symbols=raw.related_symbols,
        related_sectors=raw.related_sectors,
        category=category,
        sentiment=sentiment,
        importance_score=round(importance, 1),
        tags=list(dict.fromkeys(tags))[:6],
        impact=_impact(category, raw),
        action=_action(category, raw),
    )


def _sentiment(category: str, text: str, default_signal: str) -> str:
    if any(word in text for word in ["风险", "调查", "亏损", "减持", "退市", "暴跌"]):
        return "negative"
    if any(word in text for word in ["增持", "回购", "政策", "利好", "修复", "增长"]):
        return "positive"
    return default_signal


def _impact(category: str, raw: MarketEventRaw) -> str:
    sectors = "、".join(_readable_sectors(raw.title, raw.summary, raw.related_sectors)[:3]) or "相关板块"
    return {
        "policy_support": f"可能改善风险偏好，优先观察 {sectors} 的持续性和成交放大。",
        "capital_style": f"提示市场风格切换，关注 {sectors} 是否获得连续资金确认。",
        "corporate_action": "公司动作可能影响个股估值和情绪，需要回到个股证据账本核验。",
        "industry_catalyst": f"行业催化可能带动主题扩散，但需确认 {sectors} 的业绩或订单支撑。",
        "risk_alert": "风险事件可能压制情绪，先判断是否影响持仓和高位候选。",
        "macro_global": "宏观或海外事件会影响风险偏好，需和指数、汇率、大宗商品联动看。",
        "other": "事件热度需要结合板块温度、资金流和个股证据继续确认。",
    }[category]


def _action(category: str, raw: MarketEventRaw) -> str:
    sectors = "、".join(_readable_sectors(raw.title, raw.summary, raw.related_sectors)[:2])
    if category == "policy_support":
        return f"打开关联板块{f'（{sectors}）' if sectors else ''}，检查资金流和领涨股。"
    if category == "capital_style":
        return "对照涨跌家数和成交额，确认这是风格切换还是短线避险。"
    if category == "corporate_action":
        return "打开相关个股，补读公告原文、回购/增持规模和历史兑现情况。"
    if category == "industry_catalyst":
        return f"跟踪{sectors or '相关行业'}的板块温度、订单/政策催化和龙头表现。"
    if category == "risk_alert":
        return "检查持仓和机会池是否暴露在该风险事件下，必要时降低优先级。"
    return "把事件加入今日复盘，等待价格、资金和板块共振确认。"


def _clusters(events: list[MarketEvent]) -> list[MarketEventCluster]:
    grouped: dict[str, list[MarketEvent]] = {}
    for event in events:
        grouped.setdefault(event.category, []).append(event)
    clusters: list[MarketEventCluster] = []
    for key, items in grouped.items():
        label, default_signal = CATEGORY_META[key]
        top = max(items, key=lambda item: item.importance_score)
        clusters.append(
            MarketEventCluster(
                key=key,
                label=label,
                signal=top.sentiment if top.sentiment != "neutral" else default_signal,
                count=len(items),
                summary=f"{label}出现 {len(items)} 条热讯，代表事件：{top.title}",
                hot_score=round(max(item.importance_score for item in items), 1),
            )
        )
    return sorted(clusters, key=lambda item: item.hot_score, reverse=True)


def _summary(events: list[MarketEvent], clusters: list[MarketEventCluster]) -> list[str]:
    if not events:
        return ["暂未获取到市场异动新闻，先以指数、板块和资金数据为主。"]
    lines = []
    for cluster in clusters[:3]:
        sectors = []
        for event in events:
            if event.category == cluster.key:
                sectors.extend(
                    _readable_sectors(event.title, event.summary, event.related_sectors)
                )
        sector_text = "、".join(list(dict.fromkeys(sectors))[:3]) or "相关板块"
        lines.append(f"{sector_text}出现{cluster.label}信号：{cluster.summary}")
    return lines


def _readable_sectors(title: str, summary: str, related_sectors: list[str]) -> list[str]:
    text = f"{title} {summary}"
    inferred = [
        label
        for label, keywords in SECTOR_KEYWORDS.items()
        if any(keyword.lower() in text.lower() for keyword in keywords)
    ]
    named = [
        sector
        for sector in related_sectors
        if not re.match(r"^BK\d+$", sector, flags=re.IGNORECASE)
    ]
    return list(dict.fromkeys([*named, *inferred]))


def _next_actions(events: list[MarketEvent], clusters: list[MarketEventCluster]) -> list[str]:
    if not events:
        return ["刷新数据后重新读取市场异动", "先检查板块热度和机会候选是否出现异常集中"]
    actions = ["先打开关联板块检查资金持续性和领涨股扩散", "补读公告/政策原文再判断事件是否可持续"]
    if any(event.category == "risk_alert" for event in events):
        actions.append("风险扰动事件出现时，先检查持仓和高位候选的暴露")
    if clusters:
        actions.append(f"把今日最高热度的{clusters[0].label}加入收盘复盘")
    actions.append("不要只按新闻标题追热点，必须等价格、资金、板块三方确认")
    return actions[:5]
