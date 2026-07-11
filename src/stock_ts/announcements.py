from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from html import unescape
from typing import Any, Callable, Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .report import DISCLAIMER

CNINFO_QUERY_URL = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
CNINFO_STATIC_BASE = "http://static.cninfo.com.cn/"
HKEX_BASE_URL = "https://www1.hkexnews.hk"
HKEX_PARTIAL_URL = f"{HKEX_BASE_URL}/search/partial.do"
HKEX_TITLE_SEARCH_URL = f"{HKEX_BASE_URL}/search/titlesearch.xhtml?lang=en"

PostForm = Callable[[str, dict[str, str], dict[str, str]], dict[str, Any]]
OpenUrl = Callable[[str, Optional[bytes], dict[str, str]], bytes]


@dataclass(frozen=True)
class AnnouncementItem:
    code: str
    name: str
    title: str
    date: str
    url: str
    risk_flags: list[str]


@dataclass(frozen=True)
class AnnouncementReport:
    query: str
    total: int
    items: list[AnnouncementItem]
    risk_events: list[AnnouncementItem]
    source: str = "cninfo"
    disclaimer: str = DISCLAIMER


def fetch_cninfo_announcements(
    query: str,
    *,
    limit: int = 10,
    post_form: PostForm | None = None,
    hkex_open_url: OpenUrl | None = None,
) -> AnnouncementReport:
    if _is_hk_code(query):
        return fetch_hkex_announcements(query, limit=limit, open_url=hkex_open_url)
    column, plate = _cninfo_exchange_params(query)
    form = {
        "tabName": "fulltext",
        "pageSize": str(limit),
        "pageNum": "1",
        "column": column,
        "category": "",
        "plate": plate,
        "seDate": "",
        "searchkey": query.strip(),
        "secid": "",
        "sortName": "",
        "sortType": "",
        "isHLtitle": "true",
    }
    headers = {
        "User-Agent": "Mozilla/5.0 StockTS/0.1",
        "Referer": "http://www.cninfo.com.cn/",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    }
    payload = (post_form or _post_form)(CNINFO_QUERY_URL, form, headers)
    rows = payload.get("announcements") or []
    items = [_announcement_from_row(row) for row in rows[:limit] if isinstance(row, dict)]
    risk_events = [item for item in items if item.risk_flags]
    return AnnouncementReport(
        query=query.strip(),
        total=int(payload.get("totalAnnouncement") or len(items)),
        items=items,
        risk_events=risk_events,
    )


def fetch_hkex_announcements(
    query: str,
    *,
    limit: int = 10,
    open_url: OpenUrl | None = None,
) -> AnnouncementReport:
    code = _normalize_hk_code(query)
    opener = open_url or _open_url
    stock = _fetch_hkex_stock(code, opener)
    if not stock:
        return AnnouncementReport(query=code, total=0, items=[], risk_events=[], source="hkexnews")
    to_date = datetime.now().strftime("%Y%m%d")
    from_date = (datetime.now() - timedelta(days=366)).strftime("%Y%m%d")
    form = {
        "lang": "EN",
        "category": "0",
        "market": "SEHK",
        "searchType": "0",
        "stockId": str(stock["stockId"]),
        "from": from_date,
        "to": to_date,
    }
    headers = {
        "User-Agent": "Mozilla/5.0 StockTS/0.1",
        "Referer": HKEX_TITLE_SEARCH_URL,
        "Content-Type": "application/x-www-form-urlencoded",
    }
    html = opener(HKEX_TITLE_SEARCH_URL, urlencode(form).encode(), headers).decode(
        "utf-8", errors="replace"
    )
    items = _hkex_items_from_html(html, code=code, name=str(stock.get("name") or code), limit=limit)
    total = _hkex_total_from_html(html) or len(items)
    risk_events = [item for item in items if item.risk_flags]
    return AnnouncementReport(
        query=code,
        total=total,
        items=items,
        risk_events=risk_events,
        source="hkexnews",
    )


def _cninfo_exchange_params(query: str) -> tuple[str, str]:
    code = "".join(ch for ch in query.strip() if ch.isdigit())
    if code.startswith(("000", "001", "002", "003", "300", "301")):
        return "szse", "sz"
    return "sse", "sh"


def render_announcement_markdown(report: AnnouncementReport) -> str:
    lines = [
        f"# 公告/财报事件：{report.query}",
        "",
        report.disclaimer,
        "",
        "## 快速结论",
        f"- 数据源：{report.source}",
        f"- 命中公告总数：{report.total}",
        f"- 本次返回：{len(report.items)} 条",
        f"- 风险事件：{len(report.risk_events)} 条",
        "",
        "## 风险事件",
    ]
    if report.risk_events:
        for item in report.risk_events:
            lines.append(
                f"- {item.date} {item.name}（{item.code}）：{item.title} "
                f"[{','.join(item.risk_flags)}] {item.url}"
            )
    else:
        lines.append("- 未在本次返回公告标题中识别出减持、监管、诉讼等风险关键词。")
    lines.extend(["", "## 最新公告"])
    for item in report.items:
        flags = f" · 风险标签：{','.join(item.risk_flags)}" if item.risk_flags else ""
        lines.append(f"- {item.date} {item.title}{flags} {item.url}")
    lines.extend(
        [
            "",
            "## 使用说明",
            "- 公告标题只能作为事件入口，关键事项必须打开 PDF 原文复核。",
            "- 风险标签来自标题关键词规则，不代表完整法律或财务结论。",
            "- 后续可把年报/季报 PDF 接入基本面评分、管理层讨论和财务风险分析。",
            "",
            "---",
            report.disclaimer,
        ]
    )
    return "\n".join(lines).strip() + "\n"


def _post_form(url: str, data: dict[str, str], headers: dict[str, str]) -> dict[str, Any]:
    request = Request(url, data=urlencode(data).encode(), headers=headers)
    with urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def _open_url(url: str, data: bytes | None, headers: dict[str, str]) -> bytes:
    request = Request(url, data=data, headers=headers)
    with urlopen(request, timeout=15) as response:
        return response.read()


def _announcement_from_row(row: dict[str, Any]) -> AnnouncementItem:
    title = _clean_html(str(row.get("announcementTitle") or row.get("shortTitle") or ""))
    name = _clean_html(str(row.get("secName") or row.get("tileSecName") or ""))
    code = str(row.get("secCode") or "")
    adjunct_url = str(row.get("adjunctUrl") or "")
    return AnnouncementItem(
        code=code,
        name=name,
        title=title,
        date=_date_from_millis(row.get("announcementTime")),
        url=CNINFO_STATIC_BASE + adjunct_url if adjunct_url else "",
        risk_flags=_risk_flags(title),
    )


def _fetch_hkex_stock(code: str, open_url: OpenUrl) -> dict[str, Any]:
    query = urlencode(
        {
            "lang": "EN",
            "type": "A",
            "name": code,
            "market": "SEHK",
            "callback": "callback",
        }
    )
    headers = {
        "User-Agent": "Mozilla/5.0 StockTS/0.1",
        "Referer": HKEX_TITLE_SEARCH_URL,
    }
    raw = open_url(f"{HKEX_PARTIAL_URL}?{query}", None, headers).decode(
        "utf-8", errors="replace"
    )
    match = re.search(r"callback\((.*)\)\s*;?\s*$", raw.strip(), flags=re.DOTALL)
    if not match:
        return {}
    payload = json.loads(match.group(1))
    for item in payload.get("stockInfo") or []:
        if isinstance(item, dict) and str(item.get("code") or "").zfill(5) == code:
            return item
    return {}


def _hkex_items_from_html(
    html: str, *, code: str, name: str, limit: int
) -> list[AnnouncementItem]:
    items: list[AnnouncementItem] = []
    pattern = re.compile(
        r'<a[^>]+href="(?P<href>/listedco/listconews/sehk/[^"]+?\.pdf)"[^>]*>'
        r"(?P<title>.*?)</a>",
        flags=re.IGNORECASE | re.DOTALL,
    )
    for match in pattern.finditer(html):
        title = _clean_html(match.group("title"))
        href = unescape(match.group("href"))
        if not title:
            continue
        items.append(
            AnnouncementItem(
                code=code,
                name=name,
                title=title,
                date=_date_from_hkex_url(href),
                url=f"{HKEX_BASE_URL}{href}",
                risk_flags=_risk_flags(title),
            )
        )
        if len(items) >= limit:
            break
    return items


def _hkex_total_from_html(html: str) -> int:
    match = re.search(r"Total records found:\s*([0-9,]+)", _clean_html(html), flags=re.I)
    if not match:
        return 0
    return int(match.group(1).replace(",", ""))


def _date_from_hkex_url(href: str) -> str:
    match = re.search(r"/sehk/([0-9]{4})/([0-9]{4})/", href)
    if not match:
        return "unknown"
    year, month_day = match.groups()
    return f"{year}-{month_day[:2]}-{month_day[2:]}"


def _clean_html(value: str) -> str:
    return re.sub(r"<[^>]+>", "", unescape(value)).strip()


def _date_from_millis(value: object) -> str:
    try:
        timestamp = int(value) / 1000
    except (TypeError, ValueError):
        return "unknown"
    return datetime.fromtimestamp(timestamp).date().isoformat()


def _risk_flags(title: str) -> list[str]:
    rules = [
        ("减持", ["减持"]),
        ("监管", ["监管", "问询", "警示", "处罚", "处分"]),
        ("诉讼", ["诉讼", "仲裁", "纠纷"]),
        ("担保", ["担保", "质押"]),
        ("亏损", ["亏损", "预亏", "业绩下降", "LOSS", "PROFIT WARNING"]),
        ("财报/业绩", ["FINANCIAL INFORMATION", "ANNUAL RESULTS", "INTERIM RESULTS"]),
        ("退市/ST", ["退市", "ST", "风险警示"]),
        ("重大事项", ["重大", "停牌", "重组", "控制权", "INSIDE INFORMATION"]),
    ]
    title_upper = title.upper()
    flags = [
        label
        for label, keywords in rules
        if any(keyword in title or keyword in title_upper for keyword in keywords)
    ]
    return list(dict.fromkeys(flags))


def _normalize_hk_code(query: str) -> str:
    digits = "".join(ch for ch in query.strip() if ch.isdigit())
    return digits.zfill(5) if 1 <= len(digits) <= 5 else digits


def _is_hk_code(query: str) -> bool:
    digits = "".join(ch for ch in query.strip() if ch.isdigit())
    return 1 <= len(digits) <= 5
