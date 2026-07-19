from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any

from .ui_modules import (
    render_opportunity_deck,
    render_portfolio_deck,
    render_stock_deck,
)

ASSET_DIR = Path(__file__).with_name("assets")


def asset_text(name: str) -> str:
    if name not in {"app.css", "app.js", "modules.css", "portfolio.js"}:
        raise ValueError("unknown asset")
    return (ASSET_DIR / name).read_text(encoding="utf-8")


def _safe(value: Any) -> str:
    return escape(str(value), quote=True)


def _number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _dictionary_items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _generated_label(value: Any) -> str:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return str(value)
    return parsed.astimezone().strftime("%H:%M")


def _signed(value: Any, suffix: str = "%") -> str:
    if value is None:
        return "—"
    number = _number(value)
    return f"{number:+.2f}{suffix}"


def _tone(value: Any) -> str:
    if value is None:
        return "unavailable"
    return "positive" if _number(value) >= 0 else "negative"


def _render_indices(view: dict[str, Any]) -> str:
    indices = _dictionary_items(view.get("indices"))
    if not indices:
        return '<span class="telemetry-empty">指数数据未提供</span>'
    return "".join(
        f"""
        <div class="index-tick">
          <span class="index-name">{_safe(item.get("name", "指数"))}</span>
          <strong>{_number(item.get("value")):,.2f}</strong>
          <span class="delta {_tone(item.get("pct_change"))}">
            {_signed(item.get("pct_change"))}
          </span>
        </div>
        """
        for item in indices
    )


def _decision_brief(view: dict[str, Any]) -> dict[str, Any]:
    brief = view.get("decision_brief")
    return brief if isinstance(brief, dict) else {}


def _render_decision_chain(view: dict[str, Any]) -> str:
    brief = _decision_brief(view)
    mainline = brief.get("mainline", {})
    mainline = mainline if isinstance(mainline, dict) else {}
    chain = _dictionary_items(brief.get("chain"))
    status = _safe(mainline.get("status", "none"))
    steps = "".join(
        f"""
        <div class="decision-step" data-decision-step="{_safe(item.get('key', 'step'))}">
          <span>{index:02d}</span>
          <small>{_safe(item.get("label", "判断"))}</small>
          <strong>{_safe(item.get("value", "待判断"))}</strong>
        </div>
        """
        for index, item in enumerate(chain, start=1)
    )
    return f"""
    <section class="decision-chain" data-decision-chain
      data-decision-status="{status}" aria-label="今日研判链">
      {steps}
    </section>
    """


def _render_thesis_stage(view: dict[str, Any]) -> str:
    brief = _decision_brief(view)
    permission = brief.get("permission", {})
    permission = permission if isinstance(permission, dict) else {}
    mainline = brief.get("mainline", {})
    mainline = mainline if isinstance(mainline, dict) else {}
    analysis = view.get("market_analysis", {})
    analysis = analysis if isinstance(analysis, dict) else {}
    evidence = _dictionary_items(analysis.get("evidence"))[:4]
    evidence_html = "".join(
        f"""
        <article>
          <span>{_safe(item.get("label", "证据"))}</span>
          <strong>{_safe(item.get("value", "—"))}{_safe(item.get("unit", ""))}</strong>
          <em>{_safe(item.get("signal", "待判断"))}</em>
        </article>
        """
        for item in evidence
    )
    return f"""
    <section class="thesis-stage" id="market-overview" data-view-section="market">
      <div class="thesis-copy">
        <span class="thesis-eyebrow">今日结论</span>
        <span class="permission-flag"
          data-permission-tone="{_safe(permission.get('tone', 'selective'))}">
          参与许可 · {_safe(permission.get("label", "等待判断"))}
        </span>
        <h1>{_safe(brief.get("headline", "等待市场结论"))}</h1>
        <p class="thesis-summary">{_safe(brief.get("summary", "等待主线证据"))}</p>
        <div class="thesis-mainline">
          <span>{_safe(mainline.get("label", "未形成主线"))}</span>
          <strong>{_safe(mainline.get("theme") or "暂无验证方向")}</strong>
          <small>{_safe(mainline.get("reason", "等待证据"))}</small>
        </div>
        <div class="thesis-trigger">
          <span>升级条件</span>
          <strong>{_safe(brief.get("next_trigger", "等待下一份有效快照"))}</strong>
        </div>
      </div>
      <div class="thesis-evidence">
        <div class="thesis-evidence-grid">{evidence_html}</div>
        <div class="thesis-risk">
          <span>主要风险</span>
          <strong>{_safe(analysis.get("primary_risk", "等待市场证据"))}</strong>
        </div>
      </div>
    </section>
    """


def _render_mainline_ladder(view: dict[str, Any]) -> str:
    opportunities = _dictionary_items(view.get("opportunities"))[:5]
    brief = _decision_brief(view)
    mainline = brief.get("mainline", {})
    mainline = mainline if isinstance(mainline, dict) else {}
    rows = []
    for index, item in enumerate(opportunities):
        candidates = _dictionary_items(item.get("candidates"))[:3]
        candidate_html = "".join(
            f"""
            <button type="button" class="mainline-stock"
              data-open-stock="{_safe(stock.get('code', ''))}">
              <strong>{_safe(stock.get("name", stock.get("code", "—")))}</strong>
              <span>{_safe(stock.get("code", "—"))} · {_signed(stock.get("pct_change"))}</span>
            </button>
            """
            for stock in candidates
        ) or '<span class="mainline-empty">暂无映射股票</span>'
        label = mainline.get("label", "观察方向") if index == 0 else "观察方向"
        rows.append(
            f"""
            <article class="mainline-row" data-mainline-rank="{index + 1}">
              <div class="mainline-rank"><span>{index + 1:02d}</span><em>{_safe(label)}</em></div>
              <div class="mainline-theme">
                <strong>{_safe(item.get("theme", "待分类"))}</strong>
                <span>{_safe(item.get("stage", "观察"))} ·
                  强度 {_safe(item.get("strength", "—"))}</span>
              </div>
              <div class="mainline-evidence">
                <strong>{_number(item.get("advancing_ratio")) * 100:.0f}% 参与</strong>
                <span>连续 {_safe(item.get("consecutive_days", 0))} 日 ·
                  成交 {_signed(item.get("amount_change"))}</span>
              </div>
              <div class="mainline-candidates">{candidate_html}</div>
              <div class="mainline-invalid">
                <span>失效条件</span>
                <p>{_safe(item.get("invalidation", "等待证据"))}</p>
              </div>
            </article>
            """
        )
    body = "".join(rows) or '<p class="empty-line">当前快照没有主题证据，未形成主线。</p>'
    return f"""
    <section class="mainline-section" aria-label="主线梯队">
      <div class="mainline-heading">
        <h2>主线梯队</h2>
      </div>
      <div class="mainline-columns" aria-hidden="true">
        <span>判断</span><span>方向 / 阶段</span><span>证据</span>
        <span>领涨映射</span><span>失效条件</span>
      </div>
      <div class="mainline-ladder">{body}</div>
    </section>
    """


def _render_unavailable(view: dict[str, Any]) -> str:
    message = _safe(view.get("message", "行情快照当前无法读取"))
    return f"""
    <main class="unavailable-stage" id="market-overview">
      <span class="status-kicker">DATA INTERRUPTED</span>
      <h1>数据暂不可用</h1>
      <p>{message}</p>
      <div class="unavailable-rule"><i></i></div>
      <strong>等待下一份有效行情快照</strong>
      <button type="button" data-refresh>重新读取</button>
    </main>
    """


def _render_ready(view: dict[str, Any]) -> str:
    return f"""
    <main>
      {_render_decision_chain(view)}
      <section class="analysis-deck is-active" data-module-deck="market">
      {_render_thesis_stage(view)}

      <section class="telemetry-ribbon" aria-label="主要指数与市场统计">
        <div class="index-ticks">{_render_indices(view)}</div>
        <div class="market-counts">
          <span><b>{_safe(view.get("advancing", 0))}</b> 上涨</span>
          <span><b>{_safe(view.get("declining", 0))}</b> 下跌</span>
          <span><b>{_safe(view.get("limit_up", 0))}</b> 涨停</span>
          <span class="risk-count"><b>{_safe(view.get("limit_down", 0))}</b> 跌停</span>
        </div>
      </section>

      {_render_mainline_ladder(view)}
      </section>
      {render_opportunity_deck(view)}
      {render_stock_deck()}
      {render_portfolio_deck()}
    </main>
    """


def render_app(view: dict[str, Any]) -> str:
    ready = view.get("status") == "ready"
    content = _render_ready(view) if ready else _render_unavailable(view)
    trade_date = _safe(view.get("trade_date", "等待数据"))
    generated_value = view.get("generated_at", "尚未生成")
    generated_at = _safe(generated_value)
    generated_label = _safe(_generated_label(generated_value))
    status = "已连接" if ready else "中断"
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="color-scheme" content="light">
  <title>Aster Market · A股今日研判</title>
  <link rel="stylesheet" href="/assets/app.css?v=decision-v1">
  <link rel="stylesheet" href="/assets/modules.css?v=decision-v1">
</head>
<body data-aster-app="decision-chain">
  <header class="command-band">
    <a class="aster-brand" href="#market-overview" aria-label="Aster Market 首页">
      <span class="brand-mark" aria-hidden="true"><i></i><i></i><i></i></span>
      <span><strong>ASTER</strong><small>MARKET FIELD</small></span>
    </a>
    <div class="data-pulse">
      <span class="pulse-dot" aria-hidden="true"></span>
      <strong>{_safe(status)}</strong>
      <span>交易日 {trade_date}</span>
      <time datetime="{generated_at}" title="完整更新时间：{generated_at}">
        更新 {generated_label}
      </time>
    </div>
    <nav class="view-switcher" aria-label="分析模块" data-keyboard-hint="1-4">
      <button class="is-active" type="button" data-module-switch="market"
        data-shortcut="1" aria-keyshortcuts="1" aria-label="今日研判，快捷键 1">今日研判</button>
      <button type="button" data-module-switch="opportunities"
        data-shortcut="2" aria-keyshortcuts="2" aria-label="主线扫描，快捷键 2">主线扫描</button>
      <button type="button" data-module-switch="stock"
        data-shortcut="3" aria-keyshortcuts="3" aria-label="个股验证，快捷键 3">个股验证</button>
      <button type="button" data-module-switch="portfolio"
        data-shortcut="4" aria-keyshortcuts="4" aria-label="持仓检查，快捷键 4">持仓检查</button>
    </nav>
    <div class="command-actions">
      <label class="candidate-search" for="candidate-search">
        <span>搜索股票 <kbd>/</kbd></span>
        <input id="candidate-search" type="search" autocomplete="off"
          placeholder="代码 / 名称 / 主题">
      </label>
      <button class="refresh-command" type="button" data-refresh>刷新</button>
    </div>
  </header>
  {content}
  <div class="aster-toast" role="status" aria-live="polite" data-toast hidden></div>
  <footer class="aster-footer">
    <p>Aster Market 只提供公开市场观察，不执行交易，也不构成投资建议。</p>
    <span>READ-ONLY / A-SHARE / DESKTOP</span>
  </footer>
  <script src="/assets/app.js?v=decision-v1" defer></script>
  <script src="/assets/portfolio.js?v=decision-v1" defer></script>
</body>
</html>
"""
