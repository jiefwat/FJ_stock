#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from stock_ts.config import get_settings
from stock_ts.daily_decisions import read_decision_artifact
from stock_ts.notification import dispatch_report
from stock_ts.symbols import stock_name_for_code

DispatchFunc = Callable[..., object]


@dataclass(frozen=True)
class SendResult:
    ok: bool
    markdown: str


def build_morning_report(
    *,
    daily_dir: str | Path = "reports/daily",
    html_dir: str | Path = "reports/html",
    announcement_dir: str | Path = "reports/announcements",
    holdings_path: str | Path = "data/portfolio/holdings.csv",
    site_url: str = "https://stock.jiewat-kaka-fj.com",
) -> str:
    daily_path = Path(daily_dir) / "latest.md"
    decisions_path = Path(daily_dir) / "latest_decisions.json"
    pipeline_path = Path(daily_dir) / "pipeline.status"
    announcements_path = Path(announcement_dir) / "latest.md"
    daily = _read_text(daily_path)
    decisions = read_decision_artifact(decisions_path)
    pipeline = _read_text(pipeline_path)
    announcements = _read_text(announcements_path)
    trade_date = _decision_trade_date(decisions) or _report_trade_date(daily)
    name_map = _stock_name_map(daily, holdings_path=holdings_path)
    conclusion = _section(daily, "## 深度结论", max_lines=8)
    market = _first_section(
        daily,
        ["## 每日大盘情况", "## 每日大盘分析", "## A股大盘"],
        max_lines=10,
    )
    decision_market = _decision_market_summary(decisions)
    if decision_market:
        conclusion = f"- {decision_market}"
        market = f"- {decision_market}"
    sectors = _first_section(
        daily,
        ["## 板块情况", "## 每日板块情况", "## 板块主题"],
        max_lines=10,
    )
    portfolio = _first_section(
        daily,
        ["## 持仓分析", "## 每日持仓分析", "## 我的持仓"],
        max_lines=12,
    )
    opportunities = _section(daily, "## 候选股票池摘要", max_lines=16)
    if not opportunities:
        opportunities = _section(daily, "## 候选股票", max_lines=16)
    stock_decisions = _stock_decision_map(daily)
    portfolio_actions = _portfolio_stock_actions(
        daily,
        name_map=name_map,
        decision_map=stock_decisions,
    )
    opportunity_actions = _opportunity_actions(daily, limit=10)
    position_advice = _position_advice_lines(daily, pipeline)
    portfolio_layers = _portfolio_layer_lines(daily)
    opening_actions = _opening_action_checklist(daily, pipeline, limit=5)
    announcement_actions = _announcement_action_summary(announcements, name_map=name_map)
    traffic_light_actions = _decision_traffic_light_actions(decisions) or _traffic_light_trade_list(
        daily, limit=5
    )
    opportunity_actions = _decision_opportunity_actions(decisions, limit=10) or opportunity_actions
    action_limit_lines = _decision_action_limit_lines(decisions)
    automation_lines = _decision_automation_lines(decisions)
    generated_at = datetime.now().isoformat(timespec="seconds")
    first_conclusion = _first_content_line(conclusion) or "未读取到深度结论，请检查日报生成状态。"
    quick_reads = _quick_read_items(
        conclusion=conclusion,
        market=market,
        sectors=sectors,
        portfolio=portfolio,
        opportunities="\n".join(opportunity_actions) if opportunity_actions else opportunities,
    )
    commuter_brief = _commuter_decision_brief(
        conclusion=first_conclusion,
        market=market,
        portfolio_actions=portfolio_actions,
        opportunity_actions=opportunity_actions,
        pipeline=pipeline,
    )
    execution_guard = _execution_guard_lines(trade_date, generated_at[:10], pipeline)
    lines = [
        f"# StockTS 早间复盘与机会｜今日操作（{generated_at[:10]}，基于交易日：{trade_date}）",
        "",
        "## 一句话结论",
        _bullet(first_conclusion),
        "",
        "## 先确认能不能执行",
        *execution_guard,
        "",
        "## 手机决策版",
        *(_bullet(item) for item in commuter_brief),
        "",
        "## 红黄绿交易清单",
        "\n".join(traffic_light_actions),
        "",
        "## 今日交易限制",
        "\n".join(action_limit_lines),
        "",
        "## 自动任务提醒",
        "\n".join(automation_lines),
        "",
        "## 地铁上先看这 5 条",
        *(_bullet(item) for item in quick_reads),
        "",
        "## 今日仓位建议",
        "\n".join(position_advice),
        "",
        "## 持仓四象限",
        "\n".join(portfolio_layers),
        "",
        "## 开盘前操作清单",
        "\n".join(opening_actions),
        "",
        f"## 昨日大盘（{trade_date}）",
        _compact_block(market, fallback="未读取到大盘摘要，请检查最新日报。", max_items=4),
        "",
        "## 昨日板块",
        _compact_block(sectors, fallback="未读取到板块摘要，请检查最新日报。", max_items=4),
        "",
        "## 今天持仓怎么做",
        "\n".join(portfolio_actions)
        if portfolio_actions
        else _compact_block(
            portfolio, fallback="未读取到持仓摘要，请检查持仓文件和日报生成状态。", max_items=5
        ),
        "",
        "## 今日机会 10 条",
        "\n".join(opportunity_actions)
        if opportunity_actions
        else _compact_block(
            opportunities, fallback="未读取到候选摘要，请检查日报生成状态。", max_items=10
        ),
        "",
        "## 数据状态",
        _pipeline_summary(pipeline),
        "",
        "## 公告风险怎么处理",
        announcement_actions,
        "",
        "## 数据提示",
        "\n".join(_data_notice_lines(trade_date, generated_at[:10], pipeline)),
    ]
    return "\n".join(lines).strip() + "\n"


def send_morning_report(
    *,
    daily_dir: str | Path = "reports/daily",
    html_dir: str | Path = "reports/html",
    announcement_dir: str | Path = "reports/announcements",
    site_url: str = "https://stock.jiewat-kaka-fj.com",
    channels: list[str] | None = None,
    dry_run: bool = False,
    style: str = "digest",
    dispatcher: DispatchFunc = dispatch_report,
) -> SendResult:
    content = build_morning_report(
        daily_dir=daily_dir,
        html_dir=html_dir,
        announcement_dir=announcement_dir,
        site_url=site_url,
    )
    subject = f"StockTS 早间复盘与机会 {datetime.now().date().isoformat()}"
    result = dispatcher(
        content,
        channels=channels or ["email"],
        subject=subject,
        dry_run=dry_run,
        style=style,
    )
    return SendResult(
        ok=bool(getattr(result, "ok", False)), markdown=str(getattr(result, "markdown", ""))
    )


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def _decision_trade_date(decisions: dict[str, object]) -> str:
    value = decisions.get("trade_date") if isinstance(decisions, dict) else ""
    return str(value).strip() if value else ""


def _decision_market_summary(decisions: dict[str, object]) -> str:
    market = decisions.get("market") if isinstance(decisions, dict) else None
    if not isinstance(market, dict):
        return ""
    summary = market.get("summary")
    return _shorten_line(str(summary).strip(), limit=140) if summary else ""


def _decision_traffic_light_actions(decisions: dict[str, object]) -> list[str]:
    lights = decisions.get("traffic_lights") if isinstance(decisions, dict) else None
    if not isinstance(lights, dict):
        return []
    rows = [
        ("red", "红灯", "不加仓，反弹优先锁利润/降风险"),
        ("yellow", "黄灯", "只看修复确认，不补亏不追高"),
        ("green", "绿灯", "持有跟踪，跌破纪律线再减"),
    ]
    actions: list[str] = []
    for key, label, fallback_action in rows:
        items = lights.get(key)
        if not isinstance(items, list):
            continue
        names = [str(item.get("name", "")).strip() for item in items if isinstance(item, dict)]
        names = [name for name in names if name]
        first_action = _first_decision_item_value(items, "action") or fallback_action
        first_reason = _first_decision_item_value(items, "reason")
        line = f"{label}：{_join_names(names) if names else '暂无'}；动作：{first_action}"
        if first_reason:
            line += f"；原因：{first_reason}"
        actions.append(_bullet(line))
    opportunities = decisions.get("opportunities")
    if isinstance(opportunities, list):
        names = [
            str(item.get("name", "")).strip()
            for item in opportunities
            if isinstance(item, dict) and item.get("name")
        ]
        actions.append(
            _bullet(
                "机会："
                + (_join_names(names, limit=5) if names else "暂无")
                + "；动作：只等开盘承接，不因名单出现就买"
            )
        )
    return actions


def _decision_opportunity_actions(decisions: dict[str, object], *, limit: int) -> list[str]:
    items = decisions.get("opportunities") if isinstance(decisions, dict) else None
    if not isinstance(items, list):
        return []
    actions: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "未识别股票").strip()
        sector = str(item.get("sector") or "未识别板块").strip()
        reason = str(item.get("reason") or "入选理由待补充").strip()
        risk = str(item.get("risk") or "等待盘中确认").strip()
        action = str(item.get("action") or "只观察，不追高").strip()
        detail = (
            f"{name}｜{sector}｜机会：{reason}；"
            f"风险：{risk}；动作：{action}"
        )
        actions.append(
            f"{len(actions) + 1}. {_shorten_line(detail, limit=150)}"
        )
        if len(actions) >= limit:
            break
    return actions


def _decision_action_limit_lines(decisions: dict[str, object]) -> list[str]:
    limits = decisions.get("action_limits") if isinstance(decisions, dict) else None
    if not isinstance(limits, list):
        return [_bullet("未读取到结构化交易限制；按数据状态和价格触发执行。")]
    visible = [str(item).strip() for item in limits if str(item).strip()]
    if not visible:
        return [_bullet("未触发结构化交易限制；仍不追高、不补亏。")]
    return [_bullet(item) for item in visible[:6]]


def _decision_automation_lines(decisions: dict[str, object]) -> list[str]:
    automation = decisions.get("automation") if isinstance(decisions, dict) else None
    if not isinstance(automation, dict):
        return [_bullet("未读取到自动任务结构化状态；以 pipeline.status 为准。")]
    advice = str(automation.get("advice") or "").strip()
    failed = automation.get("failed_steps")
    failed_text = ""
    if isinstance(failed, list) and failed:
        failed_text = "异常步骤：" + "、".join(str(item) for item in failed if item)
    lines = []
    if advice:
        lines.append(_bullet(advice))
    if failed_text:
        lines.append(_bullet(failed_text))
    return lines or [_bullet("自动更新未发现硬失败。")]


def _first_decision_item_value(items: object, key: str) -> str:
    if not isinstance(items, list):
        return ""
    for item in items:
        if isinstance(item, dict) and item.get(key):
            return _shorten_line(str(item[key]).strip(), limit=80)
    return ""


def _section(markdown: str, heading: str, *, max_lines: int) -> str:
    lines = markdown.splitlines()
    capture = False
    captured: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped == heading:
            capture = True
            continue
        if capture and stripped.startswith("#"):
            break
        if capture and stripped:
            captured.append(_shorten_line(stripped))
        if len(captured) >= max_lines:
            break
    return "\n".join(captured)


def _first_section(markdown: str, headings: list[str], *, max_lines: int) -> str:
    for heading in headings:
        content = _section(markdown, heading, max_lines=max_lines)
        if content:
            return content
    return ""


def _report_trade_date(markdown: str) -> str:
    match = re.search(r"（(\d{4}-\d{2}-\d{2})）", markdown)
    if match:
        return match.group(1)
    return "最近交易日"


def _normalize_code(code: str) -> str:
    return code.strip().lower().removeprefix("sh").removeprefix("sz").split("，", 1)[0].strip()


def _clean_stock_name(raw: str) -> str:
    cleaned = re.sub(r"^\s*(?:[-*]\s*)?\d+[.、]\s*", "", raw.strip())
    return cleaned.strip()


def _stock_name_map(markdown: str, *, holdings_path: str | Path) -> dict[str, str]:
    names: dict[str, str] = {}
    for match in re.finditer(
        r"([A-Za-z0-9\u4e00-\u9fff Ｈ·&.\-]+?)（([0-9A-Za-z]{5,6})(?:，[^）]*)?）", markdown
    ):
        name = _clean_stock_name(match.group(1))
        code = _normalize_code(match.group(2))
        if code and name:
            names[code] = name
    path = Path(holdings_path)
    if path.exists():
        with path.open(encoding="utf-8", errors="ignore") as file:
            for row in csv.DictReader(file):
                code = _normalize_code(row.get("code", ""))
                name = (row.get("name") or "").strip()
                if code and name:
                    names.setdefault(code, name)
    return names


def _display_stock(code: str, name_map: dict[str, str]) -> str:
    normalized = _normalize_code(code)
    return name_map.get(normalized) or stock_name_for_code(normalized) or f"未识别名称（{code}）"


def _portfolio_stock_actions(
    markdown: str,
    *,
    name_map: dict[str, str],
    decision_map: dict[str, dict[str, str]] | None = None,
) -> list[str]:
    detail = _section(markdown, "## 持仓明细", max_lines=80)
    if not detail:
        detail = _first_section(markdown, ["## 每日持仓分析", "## 持仓分析"], max_lines=80)
    actions: list[str] = []
    for item in _content_items(detail):
        parsed = _parse_stock_line(item)
        if not parsed:
            continue
        name, code, detail_text = parsed
        display = _display_stock(code, name_map) if name == code else name
        decision = (decision_map or {}).get(_normalize_code(code))
        if decision:
            actions.append(_format_stock_decision_action(display, decision))
            continue
        trend = _extract_field(detail_text, "趋势") or "未识别"
        risk = _extract_field(detail_text, "风险") or "未识别"
        actions.append(
            _format_stock_decision_action(
                display,
                _position_detail_decision(detail_text, trend=trend, risk=risk),
            )
        )
    if not actions and decision_map:
        for code, decision in decision_map.items():
            actions.append(_format_stock_decision_action(_display_stock(code, name_map), decision))
    return actions[:12]


def _format_stock_decision_action(display: str, decision: dict[str, str]) -> str:
    parts = [
        f"{display}：判断：{_clause(decision.get('verdict', '观察'))}",
        f"动作：{_clause(decision.get('action', '只观察'), limit=42)}",
        f"风险：{_clause(decision.get('conflict', '证据不足'), limit=46)}",
        f"禁忌：{_clause(decision.get('forbidden', '不临时交易'), limit=28)}",
        f"离场：{_clause(decision.get('exit', '跌破关键线降风险'), limit=34)}",
    ]
    return _bullet("；".join(parts))


def _clause(value: str, *, limit: int = 80) -> str:
    return _shorten_line(str(value).strip().rstrip("。；;，, "), limit=limit)


def _stock_decision_map(markdown: str) -> dict[str, dict[str, str]]:
    decisions: dict[str, dict[str, str]] = {}
    stock_heading = re.compile(r"^#\s+个股分析：(?P<name>.+?)（(?P<code>[0-9A-Za-z]{5,6})")
    current_code = ""
    in_decision = False
    current: dict[str, str] = {}
    for raw_line in [*markdown.splitlines(), "# END"]:
        line = raw_line.strip()
        heading = stock_heading.match(line)
        if heading:
            if current_code and current:
                decisions[current_code] = current
            current_code = _normalize_code(heading.group("code"))
            current = {}
            in_decision = False
            continue
        if line.startswith("# ") and current_code:
            if current:
                decisions[current_code] = current
            current_code = ""
            current = {}
            in_decision = False
            continue
        if not current_code:
            continue
        if line == "## 决策摘要":
            in_decision = True
            continue
        if in_decision and line.startswith("## "):
            in_decision = False
            continue
        if not in_decision or not line.startswith(("- ", "* ")):
            continue
        text = _strip_bullet(line)
        label, sep, value = text.partition("：")
        if not sep:
            continue
        key = {
            "最终判断": "verdict",
            "核心矛盾": "conflict",
            "今日动作": "action",
            "不能做什么": "forbidden",
            "转强条件": "strengthen",
            "离场条件": "exit",
            "数据可信度": "reliability",
        }.get(label.strip())
        if key:
            current[key] = _shorten_line(value.strip(), limit=92)
    for code, fallback in _deep_stock_observation_decision_map(markdown).items():
        decisions.setdefault(code, fallback)
    return decisions


def _deep_stock_observation_decision_map(markdown: str) -> dict[str, dict[str, str]]:
    section = _section(markdown, "## 个股深度观察", max_lines=80)
    if not section:
        return {}
    decisions: dict[str, dict[str, str]] = {}
    pattern = re.compile(
        r"(?P<name>.+?)（(?P<code>[0-9A-Za-z]{5,6})(?:，[^）]*)?）："
        r"(?P<score>\d{1,3})/100，(?P<summary>.+)"
    )
    current_code = ""
    current_action = ""
    current_event = ""

    def flush_observation() -> None:
        nonlocal current_action, current_code, current_event
        if not current_code or current_code not in decisions:
            return
        decision = decisions[current_code]
        if current_action:
            decision["action"] = _shorten_line(current_action, limit=92)
        if current_event:
            event = _shorten_line(current_event, limit=92)
            conflict = decision.get("conflict", "")
            decision["conflict"] = _shorten_line(
                f"{conflict}；{event}" if conflict else event, limit=92
            )
        current_action = ""
        current_event = ""

    for item in _content_items(section):
        match = pattern.match(item)
        if match:
            flush_observation()
            current_code = _normalize_code(match.group("code"))
            score = max(0, min(100, int(match.group("score"))))
            summary = _clean_deep_observation_summary(
                match.group("summary"),
                _clean_stock_name(match.group("name")),
            )
            decisions[current_code] = _deep_observation_decision(score, summary)
            continue
        if not current_code:
            continue
        if item.startswith("今日动作："):
            current_action = item.removeprefix("今日动作：").strip()
        elif item.startswith(("消息事件/新闻舆情：", "新闻舆情：", "消息事件：")):
            current_event = item.split("：", 1)[1].strip()
    flush_observation()
    return decisions


def _clean_deep_observation_summary(summary: str, stock_name: str) -> str:
    clean = _shorten_line(summary.strip(), limit=84)
    if stock_name:
        clean = clean.removeprefix(stock_name).strip(" ，。")
    generic_patterns = (
        "当前信号不足或风险约束较多",
        "优先观察而非进攻",
        "信号不足",
    )
    if any(pattern in clean for pattern in generic_patterns):
        return ""
    return clean or "信号不足，先按风控纪律处理"


def _deep_observation_decision(score: int, summary: str) -> dict[str, str]:
    if score <= 40:
        verdict = "降风险"
        action = "不加仓；反弹先降风险，等趋势和资金修复后再看。"
        reliability = "低可信"
        score_reason = "弱势分低，按风险股处理"
    elif score <= 55:
        verdict = "防守观察"
        action = "不加仓；先等重新站回短期均线并出现承接。"
        reliability = "部分可信"
        score_reason = "未到进攻区，等待趋势修复"
    elif score <= 70:
        verdict = "观察"
        action = "只观察；满足承接和板块延续再看。"
        reliability = "部分可信"
        score_reason = "中性观察，先看承接"
    else:
        verdict = "谨慎进攻"
        action = "小仓位观察；只在回踩不破且放量承接时考虑。"
        reliability = "部分可信"
        score_reason = "相对强势，仍需等买点"
    reason = summary or score_reason
    return {
        "verdict": verdict,
        "conflict": _shorten_line(f"深度分 {score}/100，{reason}", limit=92),
        "action": action,
        "forbidden": "不补仓摊低；不因跌多了临时买入。",
        "strengthen": "站回短期均线且放量不跌回开盘价",
        "exit": "跌破关键支撑或继续放量下跌时降低仓位",
        "reliability": reliability,
    }


def _position_detail_decision(detail: str, *, trend: str, risk: str) -> dict[str, str]:
    is_profit = "盈亏 -" not in detail and re.search(r"盈亏 [0-9]", detail) is not None
    action = _today_action_from_position(detail, trend=trend, risk=risk)
    if risk == "高" or trend == "下降趋势":
        verdict = "锁利润" if is_profit else "降风险"
        forbidden = "不补仓摊低；不因跌多了临时买入。"
        strengthen = "站回短期均线且放量承接"
        exit_rule = "跌破止损线或继续放量下跌时减仓"
    elif risk == "中":
        verdict = "防守观察"
        forbidden = "不追高；不在缩量时加仓。"
        strengthen = "放量站稳短期均线"
        exit_rule = "跌破短期均线且不能收回时降低仓位"
    elif trend == "上升趋势" and risk == "低":
        verdict = "持有观察"
        forbidden = "不追高；不脱离止损线加仓。"
        strengthen = "继续稳在 5 日线之上且量能不萎缩"
        exit_rule = "跌破 5 日线或利润回撤扩大时减仓"
    else:
        verdict = "观察"
        forbidden = "不临时交易；不把不确定当机会。"
        strengthen = "趋势、量能和板块同时转强"
        exit_rule = "跌破关键支撑时降低仓位"
    pnl = _extract_position_pnl(detail)
    conflict = f"趋势 {trend}，风险 {risk}" + (f"，盈亏 {pnl}" if pnl else "")
    return {
        "verdict": verdict,
        "conflict": _shorten_line(conflict, limit=92),
        "action": action,
        "forbidden": forbidden,
        "strengthen": strengthen,
        "exit": exit_rule,
        "reliability": "基础可信",
    }


def _extract_position_pnl(detail: str) -> str:
    match = re.search(r"盈亏\s*([^，]+(?:（[^）]+）)?)", detail)
    return match.group(1).strip() if match else ""


def _parse_stock_line(text: str) -> tuple[str, str, str] | None:
    match = re.match(
        r"(?:\d+[.、]\s*)?(?P<name>.+?)（(?P<code>[0-9A-Za-z]{5,6})(?:，[^）]*)?）：(?P<detail>.+)",
        _strip_bullet(text),
    )
    if not match:
        return None
    return (
        _clean_stock_name(match.group("name")),
        _normalize_code(match.group("code")),
        match.group("detail").strip(),
    )


def _extract_field(text: str, label: str) -> str:
    match = re.search(rf"{label}\s*([^，。；\s]+)", text)
    return match.group(1).strip() if match else ""


def _today_action_from_position(detail: str, *, trend: str, risk: str) -> str:
    is_profit = "盈亏 -" not in detail and re.search(r"盈亏 [0-9]", detail) is not None
    is_loss = "盈亏 -" in detail
    if risk == "高" or trend == "下降趋势":
        if is_profit:
            return "不加仓；反弹先降仓/锁利润，等趋势修复再看"
        if is_loss:
            return "不加仓；跌破止损线就减仓，先保护本金"
        return "不加仓；先降风险，等趋势重新转强"
    if risk == "中":
        return "轻仓观察；只在放量转强时保留，不追高"
    if trend == "上升趋势" and risk == "低":
        return "持有观察；不追高，跌破 5 日线再减"
    return "持有观察；按价格触发执行，不临时加仓"


def _opening_action_checklist(markdown: str, pipeline_status: str, *, limit: int) -> list[str]:
    positions = _portfolio_action_records(markdown)
    candidates = _candidate_entries(markdown, limit=3)
    protect = [
        item["name"]
        for item in positions
        if item["is_profit"] and (item["risk"] == "高" or item["trend"] == "下降趋势")
    ]
    problem = [
        item["name"]
        for item in positions
        if item["is_loss"] and (item["risk"] in {"高", "中"} or item["trend"] == "下降趋势")
    ]
    keep = [
        item["name"]
        for item in positions
        if not item["is_loss"] and item["trend"] == "上升趋势" and item["risk"] in {"低", "中"}
    ]
    action_lines: list[str] = []
    if protect:
        action_lines.append(
            _bullet(
                f"保护利润：{'、'.join(protect[:3])}；不加仓；反弹先降仓/锁利润，等趋势修复再看"
            )
        )
    if problem:
        action_lines.append(
            _bullet(f"问题仓：{'、'.join(problem[:4])}；不开新仓补亏，先等放量站回短期均线")
        )
    if keep:
        action_lines.append(_bullet(f"可继续观察：{'、'.join(keep[:3])}；只做持有跟踪，不追高"))
    if candidates:
        action_lines.append(
            _bullet(
                "今日只观察不追高："
                + "、".join(entry["name"] for entry in candidates[:3])
                + "；高开超过 3% 先等回落承接"
            )
        )
    gap = _data_gap_sentence(pipeline_status)
    if gap:
        action_lines.append(_bullet(gap))
    if not action_lines:
        action_lines.append(_bullet("没有提取到可执行动作；先检查最新日报和持仓文件是否生成完整。"))
    return action_lines[:limit]


def _portfolio_action_records(markdown: str) -> list[dict[str, object]]:
    detail = _section(markdown, "## 持仓明细", max_lines=80)
    if not detail:
        detail = _first_section(markdown, ["## 每日持仓分析", "## 持仓分析"], max_lines=80)
    records: list[dict[str, object]] = []
    for item in _content_items(detail):
        parsed = _parse_stock_line(item)
        if not parsed:
            continue
        name, _code, detail_text = parsed
        trend = _extract_field(detail_text, "趋势") or "未识别"
        risk = _extract_field(detail_text, "风险") or "未识别"
        records.append(
            {
                "name": name,
                "trend": trend,
                "risk": risk,
                "is_profit": "盈亏 -" not in detail_text
                and re.search(r"盈亏 [0-9]", detail_text) is not None,
                "is_loss": "盈亏 -" in detail_text,
            }
        )
    return records


def _data_gap_sentence(status_text: str) -> str:
    status = _parse_status(status_text)
    gaps: list[str] = []
    if str(status.get("external_enrich", "")).startswith(("failed", "partial")):
        gaps.append("新闻/资金仍需补强")
    if str(status.get("a_share_kline", "")).startswith("failed"):
        gaps.append("部分K线失败")
    if not gaps:
        return ""
    return "数据缺口：" + "、".join(gaps) + "；涉及个股只做观察，不把缺口当利好。"


def _position_advice_lines(markdown: str, pipeline_status: str) -> list[str]:
    health = _portfolio_health_score(markdown)
    if health is None:
        first = "组合健康度未读取；建议仓位：半仓以下；先确认日报和持仓数据完整"
    else:
        if health < 40:
            cap = "3成以内"
            stance = "防守为主"
        elif health < 60:
            cap = "5成以内"
            stance = "控仓修复"
        elif health < 70:
            cap = "6成以内"
            stance = "谨慎进攻"
        else:
            cap = "7成以内"
            stance = "可进攻但不追高"
        first = f"组合健康度 {health}/100；建议仓位：{cap}；状态：{stance}"
    lines = [_bullet(first)]
    reliability = _data_reliability_line(pipeline_status)
    if reliability:
        lines.append(_bullet(reliability))
    return lines


def _portfolio_health_score(markdown: str) -> int | None:
    match = re.search(r"健康度：\s*(\d{1,3})/100", markdown)
    if not match:
        match = re.search(r"组合健康度\s*(\d{1,3})/100", markdown)
    if not match:
        return None
    return max(0, min(100, int(match.group(1))))


def _data_reliability_line(status_text: str) -> str:
    status = _parse_status(status_text)
    if not status:
        return ""
    notes: list[str] = []
    external = str(status.get("external_enrich", ""))
    kline = str(status.get("a_share_kline", ""))
    if external.startswith(("failed", "partial")):
        notes.extend(["资金面判断：不可信", "消息催化判断：不可信"])
    if kline.startswith("failed"):
        notes.append("部分K线：不完整")
    if not notes:
        return ""
    return "；".join(notes) + "；今天以价格、趋势和仓位纪律为主。"


def _portfolio_layer_lines(markdown: str) -> list[str]:
    records = _portfolio_action_records(markdown)
    if not records:
        return [_bullet("未读取到持仓明细；先确认持仓文件和日报是否生成完整。")]
    protect: list[str] = []
    problem: list[str] = []
    repair: list[str] = []
    trend: list[str] = []
    for item in records:
        name = str(item["name"])
        item_trend = str(item["trend"])
        risk = str(item["risk"])
        is_profit = bool(item["is_profit"])
        is_loss = bool(item["is_loss"])
        if is_profit and (risk == "高" or item_trend == "下降趋势"):
            protect.append(name)
        elif is_loss and item_trend == "上升趋势" and risk in {"低", "中"}:
            repair.append(name)
        elif is_loss:
            problem.append(name)
        elif is_profit and item_trend == "上升趋势" and risk in {"低", "中"}:
            trend.append(name)
    return [
        _bullet(
            "保护利润仓："
            + (_join_names(protect) if protect else "暂无")
            + "；动作：不加仓，反弹先锁利润"
        ),
        _bullet(
            "问题仓："
            + (_join_names(problem) if problem else "暂无")
            + "；动作：不补亏，跌破纪律线先降风险"
        ),
        _bullet(
            "修复观察仓："
            + (_join_names(repair) if repair else "暂无")
            + "；动作：只看放量修复，不提前加仓"
        ),
        _bullet(
            "趋势持有仓："
            + (_join_names(trend) if trend else "暂无")
            + "；动作：持有跟踪，跌破 5 日线再减"
        ),
    ]


def _traffic_light_trade_list(markdown: str, *, limit: int) -> list[str]:
    records = _portfolio_action_records(markdown)
    candidates = _candidate_entries(markdown, limit=limit)
    if not records and not candidates:
        return [_bullet("红灯/黄灯/绿灯暂缺：未读取到持仓或候选数据，今天先不主动扩大风险。")]

    red: list[str] = []
    yellow: list[str] = []
    green: list[str] = []
    seen_positions: set[str] = set()
    for item in records:
        name = str(item["name"])
        if not name or name in seen_positions:
            continue
        seen_positions.add(name)
        item_trend = str(item["trend"])
        risk = str(item["risk"])
        is_profit = bool(item["is_profit"])
        is_loss = bool(item["is_loss"])
        if risk == "高" or (is_profit and item_trend == "下降趋势"):
            red.append(name)
        elif is_profit and item_trend == "上升趋势":
            green.append(name)
        elif is_loss or item_trend == "下降趋势" or risk == "中":
            yellow.append(name)

    if not red and not yellow and not green:
        red.extend(_weak_holding_names_from_summary(markdown))

    candidate_names = [
        entry["name"]
        for entry in candidates
        if entry.get("name") and entry["name"] not in seen_positions
    ]
    return [
        _bullet(
            "红灯："
            + (_join_names(red) if red else "暂无")
            + "；动作：不加仓，反弹优先锁利润/降风险"
        ),
        _bullet(
            "黄灯："
            + (_join_names(yellow) if yellow else "暂无")
            + "；动作：只看修复确认，不补亏不追高"
        ),
        _bullet(
            "绿灯："
            + (_join_names(green) if green else "暂无")
            + "；动作：持有跟踪，跌破纪律线再减"
        ),
        _bullet(
            "机会："
            + (_join_names(candidate_names, limit=limit) if candidate_names else "暂无")
            + "；动作：只等开盘承接，不因名单出现就买"
        ),
    ]


def _weak_holding_names_from_summary(markdown: str) -> list[str]:
    names: list[str] = []
    for match in re.finditer(r"弱势或高风险持仓：([^\n。；]+)", markdown):
        for raw_name in re.split(r"[、,，]", match.group(1)):
            name = re.sub(r"^[\s：:。；;]+|[\s：:。；;]+$", "", raw_name)
            if not name or _looks_like_summary_phrase(name):
                continue
            names.append(name)
    return list(dict.fromkeys(names))


def _looks_like_summary_phrase(text: str) -> bool:
    summary_keywords = ("持仓", "大盘", "环境", "需要", "降低", "回撤", "先处理")
    return any(keyword in text for keyword in summary_keywords) or len(text) > 12


def _join_names(names: list[str], *, limit: int = 4) -> str:
    visible = names[:limit]
    suffix = f"等{len(names)}只" if len(names) > limit else ""
    return "、".join(visible) + suffix


def _opportunity_actions(markdown: str, *, limit: int) -> list[str]:
    entries = _candidate_entries(markdown, limit=limit)
    actions: list[str] = []
    for index, entry in enumerate(entries, start=1):
        actions.append(f"{index}. {_format_opportunity_entry(entry)}")
    return actions


def _format_opportunity_entry(entry: dict[str, str]) -> str:
    name = entry["name"]
    reason = _clean_candidate_text(entry["reason"], name)
    risk = _clean_candidate_text(entry["risk"], name)
    action = _clean_candidate_text(entry["action"], name)
    text = f"{name}｜{entry['sector']}｜机会：{reason}；风险：{risk}；动作：{action}"
    return _shorten_line(text, limit=150)


def _clean_candidate_text(text: str, stock_name: str) -> str:
    clean = _strip_bullet(text)
    if stock_name:
        clean = clean.replace(f"{stock_name}所在", "")
        clean = clean.replace(stock_name, "")
    clean = re.sub(r"观察分\s*\d+/100[，,；;]?", "", clean)
    clean = re.sub(r"最新价\s*[-0-9.]+[，,；;]?", "", clean)
    clean = re.sub(r"日涨跌\s*[-0-9.]+%[，,；;]?", "", clean)
    clean = clean.replace("；；", "；").replace("，，", "，")
    return clean.strip(" ，；;") or "等待盘中确认"


def _candidate_entries(markdown: str, *, limit: int) -> list[dict[str, str]]:
    section = _section(markdown, "## 候选观察票", max_lines=limit * 4 + 20)
    if not section:
        section = _section(markdown, "## 候选股票", max_lines=limit * 4 + 20)
    if not section:
        section = _section(markdown, "## 候选股票池摘要", max_lines=limit * 4 + 20)
    entries: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for raw_line in section.splitlines():
        line = raw_line.strip()
        match = re.match(
            r"(?P<rank>\d+)[.、]\s*(?P<name>.+?)（(?P<code>[0-9A-Za-z]{5,6})(?:，(?P<sector>[^）]+))?）：(?P<summary>.+)",
            line,
        )
        if match:
            if current:
                entries.append(_complete_candidate_entry(current))
            current = {
                "name": _clean_stock_name(match.group("name")),
                "code": _normalize_code(match.group("code")),
                "sector": (match.group("sector") or "未识别板块").strip(),
                "summary": match.group("summary").strip(),
                "reason": "",
                "risk": "",
                "action": "",
            }
            continue
        if current is None:
            continue
        stripped = _strip_bullet(line)
        if stripped.startswith("入选理由："):
            current["reason"] = stripped.removeprefix("入选理由：").strip()
        elif stripped.startswith("风险提示："):
            current["risk"] = stripped.removeprefix("风险提示：").strip()
        elif stripped.startswith("观察条件："):
            current["action"] = stripped.removeprefix("观察条件：").strip()
    if current and len(entries) < limit:
        entries.append(_complete_candidate_entry(current))
    return _deduplicate_candidate_entries(entries)[:limit]


def _complete_candidate_entry(entry: dict[str, str]) -> dict[str, str]:
    summary = entry.get("summary", "")
    return {
        "name": entry.get("name") or "未识别股票",
        "code": entry.get("code") or "",
        "sector": entry.get("sector") or "未识别板块",
        "reason": entry.get("reason") or summary or "入选理由待补充",
        "risk": entry.get("risk") or "等待盘中确认",
        "action": entry.get("action") or "只观察，不追高；开盘承接确认后再看",
    }


def _deduplicate_candidate_entries(entries: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    unique: list[dict[str, str]] = []
    for entry in entries:
        key = entry.get("code") or entry.get("name") or ""
        normalized = _normalize_code(key) if entry.get("code") else key.strip().lower()
        if normalized and normalized in seen:
            continue
        if normalized:
            seen.add(normalized)
        unique.append(entry)
    return unique


def _announcement_action_summary(markdown: str, *, name_map: dict[str, str]) -> str:
    items: list[str] = []
    current_code = ""
    risk_count = 0
    for line in [*markdown.splitlines(), "## END"]:
        stripped = line.strip()
        heading = re.match(r"##\s+([0-9A-Za-z]{5,6})$", stripped)
        if heading:
            if current_code and risk_count > 0:
                items.append(_announcement_action_line(current_code, risk_count, name_map))
            current_code = _normalize_code(heading.group(1))
            risk_count = 0
            continue
        if stripped == "## END":
            if current_code and risk_count > 0:
                items.append(_announcement_action_line(current_code, risk_count, name_map))
            break
        risk_match = re.match(r"-\s*风险事件：(\d+)", stripped)
        if risk_match:
            risk_count = int(risk_match.group(1))
    if not items:
        return "- 暂无需要优先处理的公告风险；持仓和机会仍按价格触发执行。"
    return "\n".join(items[:8])


def _announcement_action_line(code: str, risk_count: int, name_map: dict[str, str]) -> str:
    name = _display_stock(code, name_map)
    return _bullet(
        f"{name}：风险：公告风险 {risk_count} 条；今天建议：先复核公告标题/PDF，未确认前不加仓"
    )


def _status_lines(status_text: str) -> str:
    if not status_text.strip():
        return "- 未生成 pipeline.status。"
    return "\n".join(f"- {line}" for line in status_text.splitlines() if line.strip())


def _pipeline_summary(status_text: str) -> str:
    status = _parse_status(status_text)
    if not status:
        return "- 数据状态未知：未生成 pipeline.status。"
    parts = []
    if status.get("status") == "ok":
        parts.append("主流程已完成")
    elif status.get("status"):
        parts.append(f"主流程 {status['status']}")
    if status.get("refresh") == "ok":
        parts.append("全市场刷新完成")
    if status.get("report") == "ok":
        parts.append("报告已生成")
    warnings = []
    if str(status.get("a_share_kline", "")).startswith("failed"):
        warnings.append("K线部分更新失败")
    if str(status.get("external_enrich", "")).startswith("failed"):
        warnings.append("新闻/资金补强超时")
    if str(status.get("announcements", "")) == "ok":
        parts.append("公告已更新")
    if warnings:
        parts.append("；".join(warnings))
    generated_at = status.get("generated_at")
    suffix = f"（{generated_at}）" if generated_at else ""
    return _bullet("；".join(parts) + suffix if parts else "数据状态已记录。")


def _parse_status(status_text: str) -> dict[str, str]:
    status: dict[str, str] = {}
    for line in status_text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key == "codes":
            continue
        status[key] = value.strip()
    return status


def _pipeline_step_status_label(value: object) -> str:
    text = str(value or "").strip()
    lower = text.lower()
    if lower.startswith("failed"):
        if "timeout" in lower or "timed out" in lower:
            return "失败：超时"
        return "失败：待复核"
    if lower.startswith("partial"):
        if "news" in lower or "moneyflow" in lower:
            return "部分完成：新闻/资金缺口"
        return "部分完成"
    return text or "未知"


def _execution_guard_lines(trade_date: str, report_date: str, pipeline_status: str) -> list[str]:
    status = _parse_status(pipeline_status)
    generated_date = str(status.get("generated_at", ""))[:10]
    if trade_date != report_date or (generated_date and generated_date != report_date):
        known_date = generated_date or trade_date
        return [
            _bullet(
                f"先别按今天盘面执行：数据基于 {trade_date}，流水线生成 {known_date}，"
                f"今天 {report_date}。先等自动任务刷新或手动复核行情。"
            ),
            _bullet("可以参考方向和风险清单，但不要把涨跌幅、买点、卖点当成今日实时信号。"),
        ]
    failed = [
        _pipeline_step_status_label(value)
        for key, value in status.items()
        if key not in {"status", "generated_at", "codes", "error"}
        and str(value).lower().startswith(("failed", "partial"))
    ]
    if failed:
        return [
            _bullet(
                "先降级使用："
                + "；".join(dict.fromkeys(item for item in failed if item))
                + "。缺口项只观察，不作为买入理由。"
            )
        ]
    return [_bullet("可以执行条件化复盘：数据未发现硬滞后；仍按触发线和止损线，不做无条件交易。")]


def _data_notice_lines(trade_date: str, report_date: str, pipeline_status: str) -> list[str]:
    lines = [
        _bullet(f"基于交易日：{trade_date}；内容仅用于研究复盘。"),
    ]
    status = _parse_status(pipeline_status)
    generated_date = str(status.get("generated_at", ""))[:10]
    known_date = generated_date or trade_date
    if trade_date != report_date or (generated_date and generated_date != report_date):
        lines.append(
            _bullet(
                "数据可能滞后："
                f"最新交易日 {trade_date}，流水线生成 {known_date}，今天 {report_date}。"
            )
        )
    lines.append(_bullet("数据缺口会在上方状态里标明；缺口项只做观察，不作为买入理由。"))
    return lines


def _compact_block(content: str, *, fallback: str, max_items: int) -> str:
    items = _content_items(content)[:max_items]
    if not items:
        items = [fallback]
    return "\n".join(_bullet(item) for item in items)


def _quick_read_items(
    *,
    conclusion: str,
    market: str,
    sectors: str,
    portfolio: str,
    opportunities: str,
) -> list[str]:
    return [
        f"结论：{_strip_bullet(_first_content_line(conclusion)) or '等待日报结论'}",
        f"大盘：{_strip_bullet(_first_content_line(market)) or '大盘摘要缺失'}",
        f"板块：{_strip_bullet(_first_content_line(sectors)) or '板块摘要缺失'}",
        f"持仓：{_strip_bullet(_first_content_line(portfolio)) or '持仓摘要缺失'}",
        f"机会：{_strip_bullet(_first_content_line(opportunities)) or '候选机会缺失'}",
    ]


def _commuter_decision_brief(
    *,
    conclusion: str,
    market: str,
    portfolio_actions: list[str],
    opportunity_actions: list[str],
    pipeline: str,
) -> list[str]:
    risk = _data_gap_sentence(pipeline) or _risk_sentence_from_text(conclusion + "\n" + market)
    first_holding = (
        _strip_bullet(portfolio_actions[0])
        if portfolio_actions
        else "暂无持仓动作；先确认日报和持仓数据。"
    )
    first_opportunity = (
        _strip_number_prefix(opportunity_actions[0])
        if opportunity_actions
        else "暂无可读机会；今天不为了交易而交易。"
    )
    return [
        f"大盘：{_strip_bullet(_first_content_line(market)) or _strip_bullet(conclusion)}",
        f"风险：{risk}",
        f"持仓：{first_holding}",
        f"机会：{first_opportunity}",
        "今天不要做：不追高、不补亏、不用数据缺口当买入理由；不是买点不交易。",
    ]


def _risk_sentence_from_text(text: str) -> str:
    clean = _strip_bullet(_first_content_line(text))
    for keyword in ["跌停", "风险", "分歧", "偏弱", "震荡", "回撤"]:
        if keyword in clean:
            return _shorten_line(clean, limit=120)
    return "未看到硬风险扩散；仍按仓位纪律和价格触发执行。"


def _strip_number_prefix(text: str) -> str:
    return re.sub(r"^\s*\d+[.、]\s*", "", _strip_bullet(text)).strip()


def _content_items(content: str) -> list[str]:
    items = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        items.append(_strip_bullet(stripped))
    return items


def _first_content_line(content: str) -> str:
    for item in _content_items(content):
        if item:
            return item
    return ""


def _strip_bullet(text: str) -> str:
    stripped = text.strip()
    for prefix in ("- ", "* "):
        if stripped.startswith(prefix):
            return stripped[len(prefix) :].strip()
    if len(stripped) > 3 and stripped[0].isdigit() and stripped[1] in {".", "、"}:
        return stripped[2:].strip()
    return stripped


def _bullet(text: str) -> str:
    return f"- {_shorten_line(_strip_bullet(text))}"


def _shorten_line(text: str, *, limit: int = 190) -> str:
    clean = " ".join(str(text).strip().split())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 1].rstrip() + "…"


def _announcement_summary(markdown: str) -> str:
    if not markdown.strip():
        return "- 未生成公告摘要。"
    lines = []
    for line in markdown.splitlines():
        stripped = line.strip()
        if (
            stripped.startswith("## ")
            or stripped.startswith("- 返回公告")
            or stripped.startswith("- 风险事件")
        ):
            lines.append(stripped)
        if len(lines) >= 18:
            break
    return "\n".join(lines) if lines else "- 公告摘要为空。"


def _email_delivery_configured() -> bool:
    settings = get_settings()
    return bool(settings.email_sender.strip() and settings.email_password.strip())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Send StockTS morning recap email from latest artifacts."
    )
    parser.add_argument("--daily-dir", default="reports/daily")
    parser.add_argument("--html-dir", default="reports/html")
    parser.add_argument("--announcement-dir", default="reports/announcements")
    parser.add_argument("--site-url", default="https://stock.jiewat-kaka-fj.com")
    parser.add_argument("--channels", default="email")
    parser.add_argument("--style", default="digest")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-if-email-missing", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    channels = [item.strip() for item in args.channels.split(",") if item.strip()]
    if args.skip_if_email_missing and "email" in channels and not _email_delivery_configured():
        print(
            "# StockTS 晨报跳过\n"
            "- 邮箱未配置：缺少 EMAIL_SENDER 或 EMAIL_PASSWORD，已跳过本次发送。"
        )
        return 0
    result = send_morning_report(
        daily_dir=args.daily_dir,
        html_dir=args.html_dir,
        announcement_dir=args.announcement_dir,
        site_url=args.site_url,
        channels=channels,
        dry_run=args.dry_run,
        style=args.style,
    )
    print(result.markdown, end="")
    return 0 if result.ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
