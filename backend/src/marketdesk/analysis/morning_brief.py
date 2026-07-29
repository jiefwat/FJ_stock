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
            f"涨跌 {_pct(candidate.quote.change_pct)}，{reasons}。{url}"
        )
    return lines


def _holding_lines(holdings: list[HoldingDossier], base_url: str) -> list[str]:
    if not holdings:
        return ["暂无持仓记录；如有实盘持仓，建议先补齐成本、仓位与失效条件。"]
    ordered = sorted(
        holdings,
        key=lambda item: (
            len(item.risk_flags),
            abs(item.drift or 0),
            abs(item.pnl_pct or 0),
        ),
        reverse=True,
    )
    lines: list[str] = []
    for item in ordered[:3]:
        risks = "；".join(item.risk_flags[:2]) if item.risk_flags else item.conclusion
        url = _link(base_url, "holdings")
        lines.append(
            f"{item.item.name} {item.item.symbol}: 持仓占比 {_pct((item.portfolio_weight or 0) * 100)}，"
            f"盈亏 {_pct(item.pnl_pct)}，动作 {item.action}，关注 {risks}。{url}"
        )
    return lines


def _watchlist_lines(watchlist: list[WatchlistItem], base_url: str) -> list[str]:
    if not watchlist:
        return ["跟踪池为空；今天可以从机会页挑 1-3 个候选加入观察。"]
    url = _link(base_url, "watchlist")
    return [
        f"{item.name} {item.symbol}: {item.status}，失效条件：{item.invalidation}。{url}"
        for item in watchlist[:3]
    ]


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
            "五、今日候选复核\n" + _li(candidate_lines),
            "六、持仓和跟踪池\n" + _li([*holding_lines, *watchlist_lines]),
            "七、下一步\n" + _li(action_lines),
            "提示：本邮件为研究辅助信息，不构成投资建议；外部情报只作展示，不改变确定性评分。",
        ]
    )
    html = f"""<!doctype html>
<html lang="zh-CN"><body style="margin:0;background:#f2f4ef;color:#17332c;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <div style="display:none;max-height:0;overflow:hidden;">{escape(preheader)}</div>
  <main style="max-width:760px;margin:0 auto;padding:24px;">
    <section style="background:#17332c;color:#fff;padding:26px 28px;border-radius:18px;">
      <p style="margin:0 0 8px;color:#f0a77f;font-size:12px;letter-spacing:.12em;">MARKET DESK MORNING BRIEF</p>
      <h1 style="margin:0;font-size:28px;line-height:1.25;">{escape(regime_label)} · {_fmt(market.analysis.score, 0)}/100</h1>
      <p style="margin:12px 0 0;color:#d4ddd6;line-height:1.7;">{escape(preheader)}</p>
    </section>
    <section style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:14px 0;">
      <article style="background:#fff;padding:16px;border:1px solid #dfe4dc;"><small>风险预算</small><strong style="display:block;font-size:24px;">{risk_budget}%</strong></article>
      <article style="background:#fff;padding:16px;border:1px solid #dfe4dc;"><small>上涨 / 下跌</small><strong style="display:block;font-size:24px;">{market.analysis.advancing}/{market.analysis.declining}</strong></article>
      <article style="background:#fff;padding:16px;border:1px solid #dfe4dc;"><small>数据覆盖</small><strong style="display:block;font-size:24px;">{_pct(market.snapshot.meta.coverage * 100)}</strong></article>
    </section>
    { _section_html("开盘前结论", summary_lines) }
    { _section_html("关键证据", factor_lines) }
    { _section_html("资金主线", sector_lines) }
    { _section_html("事件与异动", [*event_lines, *anomaly_lines[:2]]) }
    { _section_html("今日候选复核", candidate_lines) }
    { _section_html("持仓和跟踪池", [*holding_lines, *watchlist_lines]) }
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
