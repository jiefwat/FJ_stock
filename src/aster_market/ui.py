from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

ASSET_DIR = Path(__file__).with_name("assets")


def asset_text(name: str) -> str:
    if name not in {"app.css", "app.js"}:
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


def _signed(value: Any, suffix: str = "%") -> str:
    number = _number(value)
    return f"{number:+.2f}{suffix}"


def _tone(value: Any) -> str:
    return "positive" if _number(value) >= 0 else "negative"


def _horizon_path(points: Any) -> str:
    values = points if isinstance(points, list) else []
    normalized = [max(12, min(106, int(_number(value)))) for value in values[:6]]
    while len(normalized) < 6:
        normalized.append(58)
    x_positions = [20, 192, 364, 536, 708, 880]
    return " ".join(
        ("M" if index == 0 else "L") + f" {x} {normalized[index]}"
        for index, x in enumerate(x_positions)
    )


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


def _render_sectors(view: dict[str, Any]) -> str:
    sectors = _dictionary_items(view.get("sectors"))[:8]
    if not sectors:
        return '<p class="empty-line">当前快照没有可用主题强度数据。</p>'

    peak = max((_number(item.get("strength")) for item in sectors), default=1.0) or 1.0
    rows = []
    for index, item in enumerate(sectors):
        width = max(14.0, min(100.0, _number(item.get("strength")) / peak * 100))
        divergence = "分歧" if item.get("high_divergence") else "延续"
        rows.append(
            f"""
            <div class="theme-band">
              <div class="theme-rank">{index + 1:02d}</div>
              <div class="theme-identity">
                <strong>{_safe(item.get("name", "待分类"))}</strong>
                <span>{_safe(divergence)} · 连续 {_safe(item.get("consecutive_days", 0))} 日</span>
              </div>
              <div class="theme-track" aria-hidden="true">
                <i style="--theme-strength: {width:.2f}%"></i>
              </div>
              <span class="theme-breadth">
                {_number(item.get("advancing_ratio")) * 100:.0f}% 上涨
              </span>
              <strong class="delta {_tone(item.get("pct_change"))}">
                {_signed(item.get("pct_change"))}
              </strong>
            </div>
            """
        )
    return "".join(rows)


def _render_candidates(view: dict[str, Any]) -> str:
    candidates = _dictionary_items(view.get("candidates"))[:18]
    if not candidates:
        return '<p class="empty-line">当前快照没有候选股票。候选为空不会自动补入示例标的。</p>'

    rows = []
    for item in candidates:
        haystack = " ".join(
            str(item.get(key, "")) for key in ("code", "name", "sector", "reason", "risk")
        ).lower()
        rows.append(
            f"""
            <article class="candidate-row" data-candidate-row
              data-candidate-haystack="{_safe(haystack)}">
              <div class="candidate-symbol">
                <strong>{_safe(item.get("name", "未命名"))}</strong>
                <span>{_safe(item.get("code", "—"))}</span>
              </div>
              <div class="candidate-theme">{_safe(item.get("sector", "待分类"))}</div>
              <div class="candidate-price">
                <strong>{_number(item.get("latest_price")):,.2f}</strong>
                <span class="delta {_tone(item.get("pct_change"))}">
                  {_signed(item.get("pct_change"))}
                </span>
              </div>
              <p>{_safe(item.get("reason", "进入观察池"))}</p>
              <div class="candidate-risk">{_safe(item.get("risk", "观察，不是买点"))}</div>
            </article>
            """
        )
    return "".join(rows)


def _render_news(view: dict[str, Any]) -> str:
    news = _dictionary_items(view.get("news"))[:8]
    if not news:
        return '<p class="empty-line">当前快照没有市场事件。</p>'
    return "".join(
        f"""
        <article class="event-row">
          <time>{_safe(item.get("published_at", "时间未标注"))}</time>
          <div>
            <span>{_safe(item.get("source", "来源未标注"))}</span>
            <h3>{_safe(item.get("title", "未命名事件"))}</h3>
            <p>{_safe(item.get("summary", ""))}</p>
          </div>
        </article>
        """
        for item in news
    )


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
    path = _horizon_path(view.get("horizon_points"))
    horizon_values = view.get("horizon_points")
    risk_point = _number(horizon_values[3] if isinstance(horizon_values, list) else 58)
    regime = _safe(view.get("regime", "待判断"))
    risk_level = _safe(view.get("risk_level", "待判断"))
    breadth = _number(view.get("breadth_ratio")) * 100
    return f"""
    <main>
      <section class="horizon-stage" id="market-overview" data-view-section="market">
        <div class="market-statement">
          <span class="status-kicker">MARKET CONDITION</span>
          <h1>{regime}<small>市场状态</small></h1>
          <p>上涨家数占比 {breadth:.1f}%，风险状态为“{risk_level}”。
            先观察强度是否扩散，再决定是否继续跟踪候选。</p>
          <div class="statement-status">
            <span>风险</span><strong>{risk_level}</strong>
          </div>
        </div>
        <div class="horizon-visual" data-market-horizon>
          <div class="horizon-heading">
            <div>
              <span class="status-kicker">SIGNAL TOPOGRAPHY</span>
              <h2>市场地平线</h2>
            </div>
            <p>广度 / 强度 / 风险的连续轨迹</p>
          </div>
          <svg viewBox="0 0 900 120" role="img" aria-label="市场广度、强度与风险轨迹">
            <defs>
              <linearGradient id="horizon-fill" x1="0" x2="1">
                <stop offset="0" stop-color="#1346D8" stop-opacity="0.28"></stop>
                <stop offset="0.7" stop-color="#16856B" stop-opacity="0.13"></stop>
                <stop offset="1" stop-color="#FF5A36" stop-opacity="0.18"></stop>
              </linearGradient>
            </defs>
            <path class="horizon-grid" d="M 20 88 H 880 M 20 58 H 880 M 20 28 H 880"></path>
            <path class="horizon-area" d="{path} L 880 112 L 20 112 Z"></path>
            <path class="horizon-line" d="{path}"></path>
            <circle class="horizon-risk" cx="536" cy="{risk_point:.0f}" r="5"></circle>
          </svg>
          <div class="horizon-legend">
            <span>广度</span><span>主题强度</span><span>风险扰动</span><span>收盘确认</span>
          </div>
        </div>
      </section>

      <section class="telemetry-ribbon" aria-label="主要指数与市场统计">
        <div class="index-ticks">{_render_indices(view)}</div>
        <div class="market-counts">
          <span><b>{_safe(view.get("advancing", 0))}</b> 上涨</span>
          <span><b>{_safe(view.get("declining", 0))}</b> 下跌</span>
          <span><b>{_safe(view.get("limit_up", 0))}</b> 涨停</span>
          <span class="risk-count"><b>{_safe(view.get("limit_down", 0))}</b> 跌停</span>
        </div>
      </section>

      <section class="terrain-layout" id="theme-field" data-view-section="themes">
        <div class="section-heading">
          <span class="status-kicker">STRENGTH FIELD</span>
          <h2>强度落在哪里</h2>
          <p>长度由涨幅、上涨占比、成交变化与连续性共同决定。</p>
        </div>
        <div class="theme-field">{_render_sectors(view)}</div>
        <aside class="next-timeline" aria-label="下一步观察顺序">
          <span class="status-kicker">NEXT READ</span>
          <h2>下一步</h2>
          <ol>
            <li><time>开盘前</time><span>确认快照时间与来源</span></li>
            <li><time>开盘后</time><span>观察广度是否继续扩散</span></li>
            <li><time>盘中</time><span>核对第一主题是否保持强度</span></li>
            <li><time>收盘前</time><span>复查跌停数与高分歧方向</span></li>
          </ol>
        </aside>
      </section>

      <section class="candidate-stream" id="candidate-stream" data-view-section="candidates">
        <div class="section-heading stream-heading">
          <div>
            <span class="status-kicker">OBSERVATION STREAM</span>
            <h2>值得继续看的股票</h2>
          </div>
          <p>候选来自只读快照；进入列表不代表买入建议。</p>
        </div>
        <div class="candidate-columns" aria-hidden="true">
          <span>股票</span><span>主题</span><span>价格 / 变化</span>
          <span>进入原因</span><span>风险</span>
        </div>
        <div data-candidate-list>{_render_candidates(view)}</div>
        <p class="search-empty" data-search-empty hidden>没有匹配的候选股票。</p>
      </section>

      <section class="event-stream" id="event-stream" data-view-section="events">
        <div class="section-heading">
          <span class="status-kicker">EVENT TRACE</span>
          <h2>今天发生了什么</h2>
          <p>事件只保留时间、来源与摘要，用来解释市场，不代替行情信号。</p>
        </div>
        <div class="event-list">{_render_news(view)}</div>
      </section>
    </main>
    """


def render_app(view: dict[str, Any]) -> str:
    ready = view.get("status") == "ready"
    content = _render_ready(view) if ready else _render_unavailable(view)
    trade_date = _safe(view.get("trade_date", "等待数据"))
    generated_at = _safe(view.get("generated_at", "尚未生成"))
    status = "已连接" if ready else "中断"
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="color-scheme" content="light">
  <title>Aster Market · A股市场地形</title>
  <link rel="stylesheet" href="/assets/app.css">
</head>
<body data-aster-app="market-horizon">
  <header class="command-band">
    <a class="aster-brand" href="#market-overview" aria-label="Aster Market 首页">
      <span class="brand-mark" aria-hidden="true"><i></i><i></i><i></i></span>
      <span><strong>ASTER</strong><small>MARKET FIELD</small></span>
    </a>
    <div class="data-pulse">
      <span class="pulse-dot" aria-hidden="true"></span>
      <strong>{_safe(status)}</strong>
      <span>{trade_date}</span>
      <time>{generated_at}</time>
    </div>
    <nav class="view-switcher" aria-label="工作区视图">
      <button class="is-active" type="button" data-view-filter="market">市场</button>
      <button type="button" data-view-filter="themes">强度</button>
      <button type="button" data-view-filter="candidates">候选</button>
      <button type="button" data-view-filter="events">事件</button>
    </nav>
    <div class="command-actions">
      <label class="candidate-search" for="candidate-search">
        <span>搜索候选</span>
        <input id="candidate-search" type="search" autocomplete="off"
          placeholder="代码 / 名称 / 主题">
      </label>
      <button class="refresh-command" type="button" data-refresh>刷新快照</button>
    </div>
  </header>
  {content}
  <footer class="aster-footer">
    <p>Aster Market 只提供公开市场观察，不执行交易，也不构成投资建议。</p>
    <span>READ-ONLY / A-SHARE / DESKTOP</span>
  </footer>
  <script src="/assets/app.js" defer></script>
</body>
</html>
"""
