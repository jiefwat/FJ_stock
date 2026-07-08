from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ResearchRunTask:
    name: str
    priority: str
    question: str
    evidence: list[str]
    action: str
    guardrail: str


@dataclass(frozen=True)
class ResearchRunCard:
    title: str
    trade_date: str
    mission: str
    risk_budget: str
    data_contract: str
    tasks: list[ResearchRunTask]
    shadow_account_policy: str


SHADOW_ACCOUNT_POLICY = "只读研究和纸面推演；不接真实下单、不保存券商交易凭证。"


def build_research_run_card(markdown: str, *, pipeline_status: str = "") -> ResearchRunCard:
    trade_date = _report_trade_date(markdown)
    mission = (
        _first_item(_section(markdown, "## 深度结论", max_lines=5))
        or _first_item(_section(markdown, "## 今日一句话", max_lines=3))
        or "先确认数据质量，再做市场、持仓和机会判断。"
    )
    health = _portfolio_health_score(markdown)
    risk_budget = _risk_budget(health)
    data_contract = _data_contract(pipeline_status)
    tasks = [
        _market_task(markdown),
        _portfolio_task(markdown),
        _opportunity_task(markdown),
        _data_quality_task(pipeline_status, data_contract),
    ]
    return ResearchRunCard(
        title="盘前研究运行卡",
        trade_date=trade_date,
        mission=_shorten(_strip_bullet(mission), 96),
        risk_budget=risk_budget,
        data_contract=data_contract,
        tasks=tasks,
        shadow_account_policy=SHADOW_ACCOUNT_POLICY,
    )


def render_research_run_card_markdown(card: ResearchRunCard) -> str:
    lines = [
        "## 研究运行卡",
        f"- 日期：{card.trade_date}；目标：{_shorten(card.mission, 78)}",
        f"- 仓位：{card.risk_budget}；数据：{card.data_contract}",
        f"- Shadow Account：{card.shadow_account_policy}",
        "",
    ]
    for task in card.tasks:
        evidence = "；".join(task.evidence[:2]) or "证据不足"
        line = (
            f"- {task.priority}｜{task.name}：问：{task.question}；"
            f"证据：{evidence}；动作：{task.action}；边界：{task.guardrail}"
        )
        lines.append(_shorten(line, 170))
    return "\n".join(lines).strip() + "\n"


def _market_task(markdown: str) -> ResearchRunTask:
    market = _section(markdown, "## 每日大盘情况", max_lines=8) or _section(
        markdown, "## 每日大盘分析", max_lines=8
    )
    evidence = _content_items(market)[:2] or ["未读取到大盘摘要"]
    priority = (
        "P0"
        if any(word in "；".join(evidence) for word in ["跌停", "防守", "退潮", "下跌"])
        else "P1"
    )
    return ResearchRunTask(
        name="市场状态确认",
        priority=priority,
        question="今天能不能提高风险暴露？",
        evidence=evidence,
        action="先确认涨跌家数、涨跌停和主线承接，再决定仓位",
        guardrail="市场退潮或跌停扩散时不追高",
    )


def _portfolio_task(markdown: str) -> ResearchRunTask:
    detail = _section(markdown, "## 持仓明细", max_lines=80)
    positions = [_strip_bullet(item) for item in _content_items(detail) if _parse_stock_line(item)]
    risky = [item for item in positions if "风险 高" in item or "下降趋势" in item]
    evidence = [_shorten(item, 70) for item in (risky or positions)[:3]] or ["未读取到持仓明细"]
    priority = "P0" if risky else "P1"
    return ResearchRunTask(
        name="持仓风险处置",
        priority=priority,
        question="哪些持仓今天必须先处理？",
        evidence=evidence,
        action="先处理高风险/下降趋势持仓，盈利弱势先锁利润，亏损弱势不补仓",
        guardrail="不补仓摊低；不把反弹当反转",
    )


def _opportunity_task(markdown: str) -> ResearchRunTask:
    candidates = _candidate_entries(markdown, limit=3)
    evidence = [f"{item['name']}｜{item['sector']}｜{item['summary']}" for item in candidates]
    return ResearchRunTask(
        name="机会池验证",
        priority="P1" if candidates else "P2",
        question="今天有哪些票只值得观察，不值得追？",
        evidence=[_shorten(item, 76) for item in evidence] or ["未读取到候选池"],
        action="只看竞价和开盘 30 分钟承接，满足条件再加入观察",
        guardrail="高开过多不追高；没有板块延续不新增风险",
    )


def _data_quality_task(status_text: str, data_contract: str) -> ResearchRunTask:
    status = _parse_status(status_text)
    gaps: list[str] = []
    for key, label in [
        ("a_share_kline", "K线"),
        ("external_enrich", "新闻/资金"),
        ("announcements", "公告"),
        ("refresh", "全市场刷新"),
    ]:
        value = status.get(key, "")
        if value.startswith(("failed", "partial")):
            gaps.append(f"{label}：{_safe_status(value)}")
    return ResearchRunTask(
        name="数据质量闸门",
        priority="P0" if data_contract != "可信" else "P2",
        question="哪些结论不能当作强证据？",
        evidence=gaps or ["主流程未暴露关键失败项"],
        action="缺口相关股票只做观察，不把缺失数据当利好",
        guardrail="数据不完整时不输出确定性判断",
    )


def _candidate_entries(markdown: str, *, limit: int) -> list[dict[str, str]]:
    section = _section(markdown, "## 候选股票", max_lines=limit * 4 + 20) or _section(
        markdown, "## 候选股票池摘要", max_lines=limit * 4 + 20
    )
    entries: list[dict[str, str]] = []
    for line in section.splitlines():
        match = re.match(
            r"(?P<rank>\d+)[.、]\s*(?P<name>.+?)（(?P<code>[0-9A-Za-z]{5,6})(?:，(?P<sector>[^）]+))?）：(?P<summary>.+)",
            line.strip(),
        )
        if not match:
            continue
        entries.append(
            {
                "name": _clean_stock_name(match.group("name")),
                "sector": (match.group("sector") or "未识别板块").strip(),
                "summary": _clean_candidate_summary(match.group("summary")),
            }
        )
        if len(entries) >= limit:
            break
    return entries


def _clean_candidate_summary(text: str) -> str:
    clean = re.sub(r"观察分\s*\d+/100[，,；;]?", "", text)
    clean = re.sub(r"最新价\s*[-0-9.]+[，,；;]?", "", clean)
    clean = re.sub(r"日涨跌\s*[-0-9.]+%[，,；;]?", "", clean)
    return clean.strip().strip("，").strip("；").strip(";").strip() or "等待盘中确认"


def _section(markdown: str, heading: str, *, max_lines: int) -> str:
    lines = markdown.splitlines()
    captured: list[str] = []
    capture = False
    for line in lines:
        stripped = line.strip()
        if stripped == heading:
            capture = True
            continue
        if capture and stripped.startswith("#"):
            break
        if capture and stripped:
            captured.append(stripped)
        if len(captured) >= max_lines:
            break
    return "\n".join(captured)


def _content_items(content: str) -> list[str]:
    return [_strip_bullet(line) for line in content.splitlines() if line.strip()]


def _first_item(content: str) -> str:
    items = _content_items(content)
    return items[0] if items else ""


def _strip_bullet(text: str) -> str:
    stripped = text.strip()
    for prefix in ("- ", "* "):
        if stripped.startswith(prefix):
            return stripped[len(prefix) :].strip()
    if len(stripped) > 3 and stripped[0].isdigit() and stripped[1] in {".", "、"}:
        return stripped[2:].strip()
    return stripped


def _parse_stock_line(text: str) -> tuple[str, str] | None:
    pattern = r"(?:\d+[.、]\s*)?(?P<name>.+?)（(?P<code>[0-9A-Za-z]{5,6})(?:，[^）]*)?）："
    match = re.match(pattern, _strip_bullet(text))
    if not match:
        return None
    return _clean_stock_name(match.group("name")), match.group("code")


def _clean_stock_name(raw: str) -> str:
    return re.sub(r"^\s*(?:[-*]\s*)?\d+[.、]\s*", "", raw.strip()).strip()


def _portfolio_health_score(markdown: str) -> int | None:
    match = re.search(r"健康度：\s*(\d{1,3})/100", markdown) or re.search(
        r"组合健康度\s*(\d{1,3})/100", markdown
    )
    return max(0, min(100, int(match.group(1)))) if match else None


def _risk_budget(health: int | None) -> str:
    if health is None:
        return "半仓以下"
    if health < 40:
        return "3成以内"
    if health < 60:
        return "5成以内"
    if health < 70:
        return "6成以内"
    return "7成以内"


def _data_contract(status_text: str) -> str:
    status = _parse_status(status_text)
    if not status:
        return "未知"
    values = "\n".join(status.values())
    if "failed" in values:
        return "低可信"
    if "partial" in values:
        return "部分可信"
    return "可信"


def _parse_status(status_text: str) -> dict[str, str]:
    status: dict[str, str] = {}
    for line in status_text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() != "codes":
            status[key.strip()] = value.strip()
    return status


def _safe_status(value: str) -> str:
    value = re.sub(r"subprocess\.[A-Za-z]+", "执行失败", value)
    value = re.sub(r"Command '\[[^\n]+", "命令失败", value)
    return _shorten(value, 36)


def _report_trade_date(markdown: str) -> str:
    match = re.search(r"（(\d{4}-\d{2}-\d{2})）", markdown)
    return match.group(1) if match else "最近交易日"


def _shorten(text: str, limit: int) -> str:
    clean = " ".join(str(text).strip().split())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 1].rstrip() + "…"
