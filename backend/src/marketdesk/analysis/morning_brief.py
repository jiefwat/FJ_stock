from __future__ import annotations

from datetime import UTC, datetime
from html import escape
from urllib.parse import urlencode

from marketdesk.models import (
    HoldingDossier,
    MarketEventResult,
    MarketIntelligenceResult,
    MarketPayload,
    MorningEmailBrief,
    OpportunityResult,
    UserAccount,
    UserPreferences,
    WatchlistItem,
)

REGIME_LABELS = {
    "risk_off": "防守",
    "cautious": "谨慎",
    "balanced": "均衡",
    "risk_on": "进攻",
}

RISK_BUDGETS = {"risk_off": 25, "cautious": 40, "balanced": 60, "risk_on": 75}
REGIME_GUARDS = {
    "risk_off": "防守日：先保护本金，候选只做观察，不主动扩大风险。",
    "cautious": "谨慎日：只有板块、量能、价格三项同时确认，才允许小仓位试探。",
    "balanced": "均衡日：可以复核机会，但先看市场广度是否继续站在中性以上。",
    "risk_on": "进攻日：仍按触发线执行，禁止脱离止损线追涨。",
}


def _fmt(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "—"
    return f"{value:,.{digits}f}".rstrip("0").rstrip(".")


def _pct(value: float | None) -> str:
    if value is None:
        return "—"
    prefix = "+" if value > 0 else ""
    return f"{prefix}{value:.2f}%"


def _amount_yi(value: float | None) -> str:
    if value is None:
        return "—"
    amount = value / 100_000_000
    prefix = "+" if amount > 0 else ""
    return f"{prefix}{_fmt(amount)} 亿"


def _link(base_url: str, route: str, query: dict[str, str] | None = None) -> str:
    root = base_url.rstrip("/")
    search = f"?{urlencode(query)}" if query else ""
    return f"{root}/#/{route}{search}"


def _li(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "- 暂无可用项目"


def _html_list(items: list[str]) -> str:
    if not items:
        return "<li>暂无可用项目</li>"
    return "".join(f"<li>{escape(item)}</li>" for item in items)


def _button(url: str, label: str) -> str:
    return (
        f'<a href="{escape(url)}" style="display:inline-block;margin-top:10px;padding:9px 12px;'
        'border-radius:999px;background:#17332c;color:#fff;text-decoration:none;font-size:12px;'
        f'font-weight:700;">{escape(label)}</a>'
    )


def _mini_button(url: str, label: str) -> str:
    return (
        f'<a href="{escape(url)}" style="display:inline-block;margin:0 6px 6px 0;padding:7px 10px;'
        'border-radius:999px;background:#eef3ed;color:#17332c;text-decoration:none;font-size:12px;'
        f'font-weight:750;">{escape(label)}</a>'
    )


def _priority_label(score: float, coverage: float, risk_flags: list[str]) -> tuple[str, str, str]:
    if len(risk_flags) >= 2 or score < 50:
        return ("高风险线索", "#8a4a27", "先看风险，不追开盘强拉。")
    if score >= 70 and coverage >= 0.6 and not risk_flags:
        return ("优先复核", "#1f7a4c", "只在大盘和板块继续确认时复核。")
    return ("观察等待", "#b28a45", "等承接和相对强度，不急于动作。")


def _top_market_factors(market: MarketPayload) -> list[str]:
    available = [factor for factor in market.analysis.factors if factor.available]
    available.sort(key=lambda factor: factor.weight, reverse=True)
    return [
        f"{factor.label}: {factor.evidence}（权重 {_pct(factor.weight * 100)}）"
        for factor in available[:3]
    ]


def _sector_lines(intelligence: MarketIntelligenceResult) -> list[str]:
    return [
        f"{item.name} {_pct(item.change_pct)}，资金 {_amount_yi(item.net_flow)}"
        for item in intelligence.sector_flows[:5]
    ]


def _sector_cards_html(intelligence: MarketIntelligenceResult, base_url: str) -> str:
    if not intelligence.sector_flows:
        return '<p style="margin:0;color:#6f7c76;font-size:13px;">暂无资金主线。</p>'
    cells = []
    for item in intelligence.sector_flows[:4]:
        url = _link(base_url, "market", {"sector": item.code})
        cells.append(
            '<td style="width:50%;padding:5px;vertical-align:top;">'
            '<div style="background:#fff;border:1px solid #dfe4dc;border-radius:14px;'
            'padding:14px 15px;">'
            f'<div style="font-size:13px;font-weight:800;color:#17332c;">{escape(item.name)}</div>'
            f'<div style="margin-top:7px;font-size:22px;font-weight:800;color:#1f7a4c;">{escape(_pct(item.change_pct))}</div>'
            f'<div style="margin-top:4px;color:#6f7c76;font-size:12px;">资金 {_amount_yi(item.net_flow)}</div>'
            f'{_button(url, "查看板块")}'
            "</div></td>"
        )
    rows = ["<tr>" + "".join(cells[index : index + 2]) + "</tr>" for index in range(0, len(cells), 2)]
    return '<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;margin:0 -5px;">' + "".join(rows) + "</table>"


def _anomaly_lines(intelligence: MarketIntelligenceResult) -> list[str]:
    return [
        f"{item.name} {item.symbol}: {item.reason}，净买 {_amount_yi(item.net_buy)}"
        for item in intelligence.anomalies[:3]
    ]


def _event_lines(events: MarketEventResult) -> list[str]:
    if events.summary:
        return events.summary[:3]
    return [
        f"{event.tags[0] if event.tags else event.category}: {event.title}"
        for event in events.events[:3]
    ]


def _candidate_lines(opportunities: OpportunityResult, base_url: str) -> list[str]:
    if not opportunities.available:
        return [opportunities.unavailable_reason or "当前候选池不可用，先看市场证据。"]
    lines: list[str] = []
    for candidate in opportunities.candidates[:3]:
        reasons = "；".join(candidate.thesis.split("；")[:2]) if candidate.thesis else "打开个股页复核证据链"
        url = _link(base_url, "stocks", {"symbol": candidate.quote.symbol})
        lines.append(
            f"{candidate.quote.name} {candidate.quote.symbol}: 分数 {_fmt(candidate.score, 0)}，"
            f"涨跌 {_pct(candidate.quote.change_pct)}，确认项：强于大盘、板块延续、回踩不破；"
            f"先看 {reasons}。{url}"
        )
    return lines


def _candidate_cards_html(opportunities: OpportunityResult, base_url: str) -> str:
    if not opportunities.available:
        reason = opportunities.unavailable_reason or "当前候选池不可用，先看市场证据。"
        return f'<p style="margin:0;color:#6f7c76;font-size:13px;">{escape(reason)}</p>'
    if not opportunities.candidates:
        return '<p style="margin:0;color:#6f7c76;font-size:13px;">暂无推荐股票；今天不为凑数降低标准。</p>'
    cards = []
    for index, candidate in enumerate(opportunities.candidates[:3], start=1):
        quote = candidate.quote
        url = _link(base_url, "stocks", {"symbol": quote.symbol})
        reasons = "；".join(candidate.thesis.split("；")[:2]) if candidate.thesis else "打开个股页复核证据链"
        risk = "；".join(candidate.risk_flags[:2]) if candidate.risk_flags else "等待开盘承接确认"
        priority, priority_color, priority_note = _priority_label(
            candidate.score,
            candidate.evidence_coverage,
            candidate.risk_flags,
        )
        cards.append(
            '<article style="background:#fffaf2;border:1px solid #ead7b5;border-radius:16px;'
            'padding:16px;margin:10px 0;">'
            f'<div style="color:#b5522d;font-size:11px;font-weight:800;letter-spacing:.08em;">推荐股票 #{index}</div>'
            f'<h3 style="margin:6px 0 4px;font-size:20px;line-height:1.25;color:#17332c;">{escape(quote.name)} '
            f'<span style="font-size:12px;color:#6f7c76;">{escape(quote.symbol)}</span></h3>'
            '<div style="display:flex;gap:8px;flex-wrap:wrap;margin:10px 0;">'
            f'<span style="padding:5px 8px;border-radius:999px;background:{priority_color};color:#fff;font-size:12px;">{escape(priority)}</span>'
            f'<span style="padding:5px 8px;border-radius:999px;background:#17332c;color:#fff;font-size:12px;">评分 {_fmt(candidate.score, 0)}</span>'
            f'<span style="padding:5px 8px;border-radius:999px;background:#edf5ee;color:#1f7a4c;font-size:12px;">涨跌 {_pct(quote.change_pct)}</span>'
            f'<span style="padding:5px 8px;border-radius:999px;background:#f2f4ef;color:#51605a;font-size:12px;">成交 {_amount_yi(quote.amount)}</span>'
            "</div>"
            f'<p style="margin:0 0 6px;color:{priority_color};font-size:13px;line-height:1.7;"><b>复核级别：</b>{escape(priority_note)}</p>'
            f'<p style="margin:0;color:#33443e;font-size:13px;line-height:1.7;"><b>推荐理由：</b>{escape(reasons)}</p>'
            f'<p style="margin:6px 0 0;color:#8a4a27;font-size:13px;line-height:1.7;"><b>先看风险：</b>{escape(risk)}</p>'
            '<p style="margin:6px 0 0;color:#6f7c76;font-size:12px;line-height:1.7;">确认项：强于大盘、板块延续、回踩不破。</p>'
            f'{_button(url, "打开个股页复核")}'
            "</article>"
        )
    return "".join(cards)


def _holding_lines(holdings: list[HoldingDossier], base_url: str) -> list[str]:
    if not holdings:
        return ["暂无持仓记录；如有实盘持仓，建议先补齐成本、仓位与失效条件。"]
    lines: list[str] = []
    for item in _rank_holdings(holdings)[:3]:
        risks = "；".join(item.risk_flags[:2]) if item.risk_flags else item.conclusion
        url = _link(base_url, "holdings")
        lines.append(
            f"{item.item.name} {item.item.symbol}: 持仓占比 {_pct((item.portfolio_weight or 0) * 100)}，"
            f"盈亏 {_pct(item.pnl_pct)}，动作 {item.action}，关注 {risks}。{url}"
        )
    return lines


def _rank_holdings(holdings: list[HoldingDossier]) -> list[HoldingDossier]:
    return sorted(
        holdings,
        key=lambda item: (
            len(item.risk_flags),
            abs(item.drift or 0),
            abs(item.pnl_pct or 0),
        ),
        reverse=True,
    )


def _holding_cards_html(holdings: list[HoldingDossier], base_url: str) -> str:
    if not holdings:
        return (
            '<p style="margin:0;color:#6f7c76;font-size:13px;">暂无持仓风险雷达；'
            '如果有实盘仓位，先补齐持仓再看机会。</p>'
        )
    url = _link(base_url, "holdings")
    cells = []
    for item in _rank_holdings(holdings)[:2]:
        risk_text = "；".join(item.risk_flags[:2]) if item.risk_flags else item.conclusion
        tone = "#b5522d" if item.risk_flags else "#1f7a4c"
        cells.append(
            '<td style="width:50%;padding:5px;vertical-align:top;">'
            '<div style="background:#fff;border:1px solid #dfe4dc;border-radius:14px;padding:14px 15px;">'
            f'<div style="font-size:13px;font-weight:850;color:#17332c;">{escape(item.item.name)} '
            f'<span style="font-size:11px;color:#6f7c76;">{escape(item.item.symbol)}</span></div>'
            f'<div style="margin-top:8px;color:{tone};font-size:18px;font-weight:850;">{escape(item.action)}</div>'
            f'<div style="margin-top:5px;color:#6f7c76;font-size:12px;">仓位 {_pct((item.portfolio_weight or 0) * 100)} · 盈亏 {_pct(item.pnl_pct)}</div>'
            f'<p style="margin:8px 0 0;color:#33443e;font-size:12px;line-height:1.65;">{escape(risk_text)}</p>'
            f'{_button(url, "处理持仓")}'
            "</div></td>"
        )
    return (
        '<table role="presentation" width="100%" cellspacing="0" cellpadding="0" '
        'style="border-collapse:collapse;margin:0 -5px;"><tr>'
        + "".join(cells)
        + "</tr></table>"
    )


def _market_score_color(score: float) -> str:
    if score >= 70:
        return "#1f7a4c"
    if score >= 50:
        return "#b28a45"
    return "#b5522d"


def _metric_cards_html(
    *,
    market: MarketPayload,
    regime_label: str,
    risk_budget: int,
) -> str:
    score_color = _market_score_color(market.analysis.score)
    cards = [
        ("大盘温度", f"{_fmt(market.analysis.score, 0)}/100", regime_label, score_color),
        ("上涨 / 下跌", f"{market.analysis.advancing}/{market.analysis.declining}", "市场广度", "#17332c"),
        ("风险预算", f"{risk_budget}%", "今日上限", "#b5522d"),
        ("数据覆盖", _pct(market.snapshot.meta.coverage * 100), market.snapshot.meta.freshness.value, "#17332c"),
    ]
    cells = []
    for label, value, note, color in cards:
        cells.append(
            '<td style="width:25%;padding:5px;vertical-align:top;">'
            '<div style="background:#fff;border:1px solid #dfe4dc;border-radius:14px;'
            'padding:15px 16px;">'
            f'<div style="font-size:11px;color:#6f7c76;font-weight:700;">{escape(label)}</div>'
            f'<div style="margin-top:6px;color:{color};font-size:25px;font-weight:850;line-height:1;">{escape(value)}</div>'
            f'<div style="margin-top:6px;color:#87918c;font-size:11px;">{escape(note)}</div>'
            "</div></td>"
        )
    return (
        '<table role="presentation" width="100%" cellspacing="0" cellpadding="0" '
        'style="border-collapse:collapse;margin:14px -5px;"><tr>'
        + "".join(cells)
        + "</tr></table>"
    )


def _market_breadth_html(market: MarketPayload) -> str:
    advancing = market.analysis.advancing
    declining = market.analysis.declining
    unchanged = market.analysis.unchanged
    total = max(1, advancing + declining + unchanged)
    adv_pct = advancing / total * 100
    flat_pct = unchanged / total * 100
    dec_pct = max(0.0, 100 - adv_pct - flat_pct)
    return (
        '<section style="background:#fff;border:1px solid #dfe4dc;border-radius:18px;padding:16px 18px;margin:14px 0;">'
        '<div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-end;">'
        '<h2 style="margin:0;font-size:16px;color:#17332c;">市场广度仪表</h2>'
        f'<span style="color:#6f7c76;font-size:12px;">上涨占比 {_pct(adv_pct)}</span>'
        "</div>"
        '<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;margin-top:12px;"><tr>'
        f'<td style="width:{adv_pct:.2f}%;height:12px;background:#1f7a4c;border-radius:999px 0 0 999px;"></td>'
        f'<td style="width:{flat_pct:.2f}%;height:12px;background:#d7dbd2;"></td>'
        f'<td style="width:{dec_pct:.2f}%;height:12px;background:#b5522d;border-radius:0 999px 999px 0;"></td>'
        "</tr></table>"
        '<div style="margin-top:8px;color:#6f7c76;font-size:12px;line-height:1.7;">'
        f'上涨 {advancing} · 平盘 {unchanged} · 下跌 {declining}。'
        '上涨占比不过半时，候选自动降一级复核。</div>'
        "</section>"
    )


def _opening_route_html(base_url: str, risk_budget: int) -> str:
    return (
        '<section style="background:#17332c;color:#fff;border-radius:18px;padding:16px 18px;margin:14px 0;">'
        '<div style="font-size:12px;letter-spacing:.1em;color:#f0a77f;font-weight:850;">OPENING ROUTE</div>'
        '<h2 style="margin:6px 0 10px;font-size:18px;color:#fff;">今日开盘路线</h2>'
        '<p style="margin:0 0 12px;color:#d4ddd6;font-size:13px;line-height:1.7;">'
        f'先锁定 {risk_budget}% 风险预算，再处理旧仓，最后只复核 1-3 只推荐股票。</p>'
        f'{_mini_button(_link(base_url, "today"), "看今日")}'
        f'{_mini_button(_link(base_url, "holdings"), "处理持仓")}'
        f'{_mini_button(_link(base_url, "opportunities"), "复核机会")}'
        "</section>"
    )


def _watchlist_lines(watchlist: list[WatchlistItem], base_url: str) -> list[str]:
    if not watchlist:
        return ["跟踪池为空；今天可以从机会页挑 1-3 个候选加入观察。"]
    url = _link(base_url, "watchlist")
    return [
        f"{item.name} {item.symbol}: {item.status}，失效条件：{item.invalidation}。{url}"
        for item in watchlist[:3]
    ]


def _opening_checklist_lines(
    *,
    market: MarketPayload,
    intelligence: MarketIntelligenceResult,
    opportunities: OpportunityResult,
) -> list[str]:
    top_sector = intelligence.sector_flows[0].name if intelligence.sector_flows else "资金主线"
    top_candidate = (
        opportunities.candidates[0].quote.name
        if opportunities.available and opportunities.candidates
        else "首个候选"
    )
    return [
        f"09:25 集合竞价：确认 {top_sector} 是否仍在资金榜前列，若转弱则候选全部降级观察。",
        f"09:45 第一轮检查：上涨家数需不弱于开盘前判断，{top_candidate} 不能弱于所属板块。",
        "10:30 第二轮检查：只保留放量承接且未跌破开盘价/关键均线的标的。",
    ]


def _forbidden_action_lines(regime: str, holdings: list[HoldingDossier]) -> list[str]:
    lines = [
        REGIME_GUARDS.get(regime, "先确认市场和个股证据，再考虑动作。"),
        "不因邮件出现某只股票就直接交易，必须回到个股页复核证据链。",
        "不在公告、数据或资金状态标记为缺口时加仓。",
    ]
    if holdings:
        lines.insert(1, "持仓有风险提示时，先处理旧仓，不用新机会掩盖旧风险。")
    else:
        lines.insert(1, "没有持仓记录时，先补齐真实持仓/观察池，再谈仓位。")
    return lines


def build_morning_email_brief(
    *,
    user: UserAccount,
    preferences: UserPreferences,
    market: MarketPayload,
    intelligence: MarketIntelligenceResult,
    events: MarketEventResult,
    opportunities: OpportunityResult,
    holdings: list[HoldingDossier],
    watchlist: list[WatchlistItem],
    base_url: str,
    generated_at: datetime | None = None,
) -> MorningEmailBrief:
    generated = generated_at or datetime.now(UTC)
    regime = market.analysis.regime
    regime_label = REGIME_LABELS.get(regime, regime)
    risk_budget = RISK_BUDGETS.get(regime, 50)
    observation = market.snapshot.meta.observed_at.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")
    top_sector = intelligence.sector_flows[0].name if intelligence.sector_flows else "暂无资金主线"
    top_candidate = (
        opportunities.candidates[0].quote.name
        if opportunities.available and opportunities.candidates
        else "暂无候选"
    )
    subject = (
        f"Market Desk 晨报 · {regime_label} {market.analysis.score:.0f}/100 · "
        f"{market.snapshot.meta.observed_at:%m-%d}"
    )
    preheader = (
        f"上涨 {market.analysis.advancing} / 下跌 {market.analysis.declining}；"
        f"资金主线 {top_sector}；优先复核 {top_candidate}。"
    )
    summary_lines = [
        f"市场状态：{regime_label}，综合温度 {_fmt(market.analysis.score, 0)}/100，建议风险预算 {risk_budget}%。",
        f"市场广度：上涨 {market.analysis.advancing}，下跌 {market.analysis.declining}，平盘 {market.analysis.unchanged}。",
        f"数据时间：{observation}；覆盖率 {_pct(market.snapshot.meta.coverage * 100)}。",
    ]
    factor_lines = _top_market_factors(market)
    sector_lines = _sector_lines(intelligence)
    anomaly_lines = _anomaly_lines(intelligence)
    event_lines = _event_lines(events)
    candidate_lines = _candidate_lines(opportunities, base_url)
    holding_lines = _holding_lines(holdings, base_url)
    watchlist_lines = _watchlist_lines(watchlist, base_url)
    checklist_lines = _opening_checklist_lines(
        market=market,
        intelligence=intelligence,
        opportunities=opportunities,
    )
    forbidden_lines = _forbidden_action_lines(regime, holdings)
    action_lines = [
        f"先打开今日页确认市场温度：{_link(base_url, 'today')}",
        f"再打开大盘页钻取资金主线：{_link(base_url, 'market')}",
        f"最后只复核 1-3 个候选，不因邮件内容直接交易：{_link(base_url, 'opportunities')}",
    ]
    text = "\n\n".join(
        [
            f"{subject}\n{preheader}",
            "一、开盘前结论\n" + _li(summary_lines),
            "二、关键证据\n" + _li(factor_lines),
            "三、资金主线\n" + _li(sector_lines),
            "四、事件与异动\n" + _li([*event_lines, *anomaly_lines[:2]]),
            "五、推荐股票（需复核）\n" + _li(candidate_lines),
            "六、持仓和跟踪池\n" + _li([*holding_lines, *watchlist_lines]),
            "七、开盘检查清单\n" + _li(checklist_lines),
            "八、今日禁止动作\n" + _li(forbidden_lines),
            "九、下一步\n" + _li(action_lines),
            "提示：本邮件为研究辅助信息，不构成投资建议；外部情报只作展示，不改变确定性评分。",
        ]
    )
    html = f"""<!doctype html>
<html lang="zh-CN"><body style="margin:0;background:#efe9dd;color:#17332c;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <div style="display:none;max-height:0;overflow:hidden;">{escape(preheader)}</div>
  <main style="max-width:760px;margin:0 auto;padding:24px;">
    <section style="background:linear-gradient(135deg,#17332c,#274c41);color:#fff;padding:28px;border-radius:22px;box-shadow:0 18px 45px rgba(23,51,44,.18);">
      <p style="margin:0 0 8px;color:#f0a77f;font-size:12px;letter-spacing:.12em;">MARKET DESK MORNING BRIEF</p>
      <h1 style="margin:0;font-size:30px;line-height:1.25;">今日大盘：{escape(regime_label)} · {_fmt(market.analysis.score, 0)}/100</h1>
      <p style="margin:12px 0 0;color:#d4ddd6;line-height:1.7;">{escape(preheader)}</p>
    </section>
    { _metric_cards_html(market=market, regime_label=regime_label, risk_budget=risk_budget) }
    { _opening_route_html(base_url, risk_budget) }
    { _market_breadth_html(market) }
    { _section_html("大盘情况", summary_lines) }
    <section style="background:#fff;border:1px solid #dfe4dc;border-radius:18px;padding:18px 20px;margin:14px 0;">
      <h2 style="margin:0 0 12px;font-size:17px;color:#17332c;">推荐股票（需复核）</h2>
      {_candidate_cards_html(opportunities, base_url)}
    </section>
    <section style="background:#f8faf5;border:1px solid #dfe4dc;border-radius:18px;padding:18px 20px;margin:14px 0;">
      <h2 style="margin:0 0 12px;font-size:17px;color:#17332c;">板块资金主线</h2>
      {_sector_cards_html(intelligence, base_url)}
    </section>
    { _section_html("关键证据", factor_lines) }
    { _section_html("事件与异动", [*event_lines, *anomaly_lines[:2]]) }
    <section style="background:#fff;border:1px solid #dfe4dc;border-radius:18px;padding:18px 20px;margin:14px 0;">
      <h2 style="margin:0 0 12px;font-size:17px;color:#17332c;">持仓风险雷达</h2>
      {_holding_cards_html(holdings, base_url)}
    </section>
    { _section_html("持仓和跟踪池", [*holding_lines, *watchlist_lines]) }
    { _section_html("开盘检查清单", checklist_lines) }
    { _section_html("今日禁止动作", forbidden_lines) }
    <section style="background:#fff8ee;border-left:4px solid #e65f32;padding:16px 18px;margin:14px 0;">
      <h2 style="margin:0 0 10px;font-size:16px;">下一步</h2>
      <ol style="margin:0;padding-left:20px;line-height:1.8;">{_html_list(action_lines)}</ol>
    </section>
    <p style="color:#73807a;font-size:12px;line-height:1.7;">本邮件为研究辅助信息，不构成投资建议；外部情报只作展示，不改变确定性评分。生成时间：{escape(generated.strftime('%Y-%m-%d %H:%M UTC'))}</p>
  </main>
</body></html>"""
    return MorningEmailBrief(
        recipient=user.email,
        enabled=preferences.morning_email_enabled,
        generated_at=generated,
        subject=subject,
        preheader=preheader,
        text=text,
        html=html,
    )


def _section_html(title: str, items: list[str]) -> str:
    return (
        '<section style="background:#fff;border:1px solid #dfe4dc;padding:18px 20px;margin:14px 0;">'
        f'<h2 style="margin:0 0 10px;font-size:16px;">{escape(title)}</h2>'
        f'<ul style="margin:0;padding-left:20px;line-height:1.8;">{_html_list(items)}</ul>'
        "</section>"
    )
