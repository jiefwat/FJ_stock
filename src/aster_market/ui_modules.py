from __future__ import annotations

from html import escape
from typing import Any


def _safe(value: Any) -> str:
    return escape(str(value), quote=True)


def _number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _signed(value: Any, suffix: str = "%") -> str:
    if value is None:
        return "—"
    return f"{_number(value):+.2f}{suffix}"


def _display(value: Any, suffix: str = "") -> str:
    if value is None:
        return "—"
    return f"{_number(value):,.2f}{suffix}"


def render_market_evidence(view: dict[str, Any]) -> str:
    analysis = view.get("market_analysis", {})
    analysis = analysis if isinstance(analysis, dict) else {}
    evidence = _items(analysis.get("evidence"))
    rows = "".join(
        f"""
        <article class="evidence-cell">
          <span>{_safe(item.get("label", "证据"))}</span>
          <strong>{_display(item.get("value"), _safe(item.get("unit", "")))}</strong>
          <em>{_safe(item.get("signal", "待判断"))}</em>
        </article>
        """
        for item in evidence
    )
    return f"""
    <section class="market-evidence" aria-label="大盘四维证据">
      <div class="evidence-intro">
        <span class="status-kicker">FOUR SIGNALS</span>
        <h2>大盘分析</h2>
        <p>{_safe(analysis.get("conclusion", "等待市场证据"))}</p>
      </div>
      <div class="evidence-cells">{rows}</div>
      <div class="evidence-check">
        <span>主要风险</span>
        <strong>{_safe(analysis.get("primary_risk", "待判断"))}</strong>
        <p>{_safe(analysis.get("next_check", "等待下一份快照"))}</p>
      </div>
    </section>
    """


def render_opportunity_deck(view: dict[str, Any]) -> str:
    opportunities = _items(view.get("opportunities"))
    rows = []
    for index, item in enumerate(opportunities):
        candidates = _items(item.get("candidates"))
        candidate_html = "".join(
            f"""
            <button type="button" class="corridor-stock"
              data-open-stock="{_safe(stock.get('code', ''))}">
              <strong>{_safe(stock.get("name", stock.get("code", "—")))}</strong>
              <span>{_signed(stock.get("pct_change"))}</span>
            </button>
            """
            for stock in candidates
        ) or '<span class="corridor-empty">当前没有匹配候选</span>'
        evidence = " · ".join(_safe(value) for value in item.get("evidence", []))
        width = max(12.0, min(100.0, _number(item.get("strength")) * 10))
        rows.append(
            f"""
            <article class="opportunity-lane"
              data-opportunity-stage="{_safe(item.get('stage', '观察'))}">
              <span class="lane-index">{index + 1:02d}</span>
              <div class="lane-theme">
                <span class="stage-flag">{_safe(item.get("stage", "观察"))}</span>
                <h3>{_safe(item.get("theme", "待分类"))}</h3>
                <p>{evidence}</p>
              </div>
              <div class="lane-strength" aria-label="主题强度">
                <i style="--lane-strength: {width:.2f}%"></i>
                <span>{_signed(item.get("pct_change"))}</span>
              </div>
              <div class="lane-candidates">{candidate_html}</div>
              <div class="lane-invalidation">
                <span>失效条件</span>
                <p>{_safe(item.get("invalidation", "证据不足"))}</p>
              </div>
            </article>
            """
        )
    lanes = "".join(rows) or '<p class="deck-empty">当前快照没有可用市场机会。</p>'
    return f"""
    <section class="analysis-deck opportunity-deck" data-module-deck="opportunities" hidden>
      <header class="deck-heading" tabindex="-1" data-deck-heading>
        <div>
          <span class="status-kicker">OPPORTUNITY CORRIDOR</span>
          <h1>市场机会</h1>
        </div>
        <p>按主题强度、参与度、成交变化和连续性排列。阶段是观察标签，不是买点。</p>
      </header>
      <div class="corridor-head" aria-hidden="true">
        <span>主题 / 阶段</span><span>强度</span><span>候选</span><span>失效条件</span>
      </div>
      <div class="opportunity-corridor">{lanes}</div>
    </section>
    """


def render_stock_deck() -> str:
    return """
    <section class="analysis-deck stock-deck" data-module-deck="stock" hidden>
      <header class="deck-heading" tabindex="-1" data-deck-heading>
        <div>
          <span class="status-kicker">STOCK EVIDENCE</span>
          <h1>股票分析</h1>
        </div>
        <p>搜索代码、名称或主题；所有结论来自当前快照，不生成目标价和买卖建议。</p>
      </header>
      <div class="stock-workspace">
        <aside class="stock-result-rail">
          <label for="stock-analysis-search">查找股票</label>
          <input id="stock-analysis-search" type="search" maxlength="40"
            placeholder="代码 / 名称 / 主题" autocomplete="off" data-stock-search>
          <p class="rail-hint">最多显示 20 个结果</p>
          <div class="stock-results" data-stock-results>
            <p class="deck-empty">输入代码、名称或主题开始分析。</p>
          </div>
        </aside>
        <section class="stock-analysis-stage" data-stock-stage>
          <div class="stock-analysis-empty" data-stock-empty>
            <span class="empty-orbit" aria-hidden="true"></span>
            <strong>选择一只股票查看证据</strong>
            <p>趋势、动量、波动、估值、资金和事件会在这里展开。</p>
          </div>
          <div class="stock-analysis-loading" data-stock-loading hidden>
            <div class="stock-loading-skeleton" aria-hidden="true">
              <i></i><i></i><i></i>
            </div>
            <p>正在读取股票快照…</p>
          </div>
          <div class="stock-analysis-error" data-stock-error hidden></div>
          <article class="stock-analysis-detail" data-stock-detail hidden>
            <header class="stock-detail-head">
              <div><span data-stock-code>—</span><h2 data-stock-name>—</h2></div>
              <div><strong data-stock-price>—</strong><span data-stock-change>—</span></div>
              <div><span>趋势</span><strong data-stock-trend>—</strong></div>
              <button type="button" data-add-current-holding>加入本机持仓</button>
            </header>
            <div class="stock-trend-plane">
              <svg viewBox="0 0 900 150" role="img" aria-label="股票价格趋势" data-stock-chart>
                <path class="stock-chart-grid" d="M20 30H880 M20 75H880 M20 120H880"></path>
                <path class="stock-chart-line" data-stock-chart-line d=""></path>
              </svg>
            </div>
            <div class="stock-dimensions" data-stock-dimensions></div>
            <div class="stock-evidence-layout">
              <section><span>证据</span><div data-stock-evidence></div></section>
              <section><span>风险</span><div data-stock-risks></div></section>
              <section><span>事件</span><div data-stock-events></div></section>
            </div>
          </article>
        </section>
      </div>
    </section>
    """


def render_portfolio_deck() -> str:
    return """
    <section class="analysis-deck portfolio-deck" data-module-deck="portfolio" hidden>
      <header class="deck-heading" tabindex="-1" data-deck-heading>
        <div>
          <span class="status-kicker">LOCAL LEDGER</span>
          <h1>我的持仓</h1>
        </div>
        <p>持仓只保存在当前浏览器，不上传服务器、不写入日志，也不会出现在其他设备。</p>
      </header>
      <section class="portfolio-privacy">
        <strong>PRIVATE TO THIS BROWSER</strong>
        <span>代码、成本和数量仅保存在 localStorage</span>
        <button type="button" data-clear-portfolio>清空本机持仓</button>
      </section>
      <form class="portfolio-form" data-portfolio-form>
        <label>股票代码<input name="code" maxlength="12" required placeholder="例如 300100"></label>
        <label>持仓数量
          <input name="quantity" type="number" min="0.0001" step="0.0001" required>
        </label>
        <label>成本价<input name="cost" type="number" min="0" step="0.01" required></label>
        <button type="submit">保存到当前浏览器</button>
        <p data-portfolio-form-error hidden></p>
      </form>
      <section class="portfolio-summary" aria-label="持仓汇总">
        <div><span>总市值</span><strong data-portfolio-market-value>—</strong></div>
        <div><span>总成本</span><strong data-portfolio-cost>—</strong></div>
        <div><span>浮动盈亏</span><strong data-portfolio-profit>—</strong></div>
        <div><span>收益率</span><strong data-portfolio-return>—</strong></div>
      </section>
      <div class="portfolio-exposure" data-portfolio-exposure>
        <span>组合暴露将在添加持仓后显示</span>
      </div>
      <div class="portfolio-ledger-head" aria-hidden="true">
        <span>股票</span><span>数量 / 成本</span><span>最新价 / 趋势</span>
        <span>市值 / 盈亏</span><span>操作</span>
      </div>
      <div class="portfolio-ledger" data-portfolio-ledger></div>
      <div class="portfolio-empty" data-portfolio-empty>
        <strong>当前浏览器还没有持仓</strong>
        <p>使用上方表单添加股票；不会向服务器发送数量或成本。</p>
      </div>
      <div class="portfolio-recovery" data-portfolio-recovery hidden>
        本机持仓数据已损坏，已忽略并恢复为空账本。
      </div>
    </section>
    """
