from __future__ import annotations

from html import escape

from stock_ts.research.portfolio_dossier_models import (
    PortfolioBoundary,
    PortfolioDossier,
    PortfolioQueueItem,
)
from stock_ts.webapp.research_console import (
    ResearchContextOption,
    render_iwencai_research_console,
)


def render_portfolio_workspace(
    dossier: PortfolioDossier,
    *,
    supporting_evidence_html: str = "",
    iwencai_status: str = "missing",
) -> str:
    verdict = dossier.verdict
    metrics = "".join(
        f'<article class="portfolio-metric status-{escape(item.status)}">'
        f"<span>{escape(item.label)}</span><strong>{escape(item.value)}</strong></article>"
        for item in dossier.metrics
    )
    queue = "".join(_render_queue_item(item) for item in dossier.queue[:3])
    queue_audit = "".join(_render_queue_audit_item(item) for item in dossier.queue)
    if not queue:
        queue = '<div class="dossier-empty-state">暂无持仓；录入真实持仓后生成处置队列。</div>'
    exposures = "".join(
        f'<article class="portfolio-exposure severity-{escape(item.severity)}">'
        f"<div><strong>{escape(item.name)}</strong><span>{item.weight:.1%}</span></div>"
        f"<p>{escape(item.consequence)}</p></article>"
        for item in dossier.exposures
    )
    if not exposures:
        exposures = '<div class="dossier-empty-state">暂无需要登记的集中度暴露。</div>'
    boundaries = "".join(_render_boundary(item) for item in dossier.boundaries)
    if not boundaries:
        boundaries = '<div class="dossier-empty-state">暂无持仓边界。</div>'
    queue_rest_label = (
        f"<h4>其余 {len(dossier.queue[3:])} 项处置</h4>" if len(dossier.queue) > 3 else ""
    )
    evidence = f"""
      <details class="portfolio-evidence essence-evidence">
        <summary>展开持仓依据</summary>
        <div class="essence-evidence-body">
          <div class="portfolio-verdict-metrics">
            <div><span>市场风险预算</span><strong>{escape(verdict.risk_budget)}</strong></div>
            <div><span>证据完整度</span><strong>{verdict.confidence}/100</strong></div>
          </div>
          <h4>组合指标</h4>
          <div class="portfolio-metric-strip">{metrics}</div>
          <section class="portfolio-exposure-register"
            aria-labelledby="portfolio-exposure-title">
            <h3 id="portfolio-exposure-title">风险暴露登记表</h3>
            {exposures}
          </section>
          {queue_rest_label}
          <h4>完整处置队列</h4>
          <div class="portfolio-queue-audit">{queue_audit}</div>
          <h4>持仓边界</h4>
          <div class="portfolio-boundary-grid">{boundaries}</div>
          {supporting_evidence_html}
        </div>
      </details>"""
    research_options = tuple(
        ResearchContextOption(
            code=item.code,
            name=item.name,
            label=f"{item.name} · {item.code}",
        )
        for item in dossier.queue
    )
    return f"""
    <section class="portfolio-dossier" data-portfolio-state="{escape(verdict.state)}">
      <section class="portfolio-verdict-brief" data-primary-portfolio-verdict="true"
        aria-labelledby="portfolio-verdict-title">
        <div class="portfolio-verdict-state">
          <span>组合风控结论</span>
          <h3 id="portfolio-verdict-title">{escape(verdict.state)}</h3>
        </div>
        <div class="portfolio-verdict-thesis">
          <p>{escape(verdict.thesis)}</p>
          <div class="essence-action-risk">
            <div class="essence-action" data-essence-action>
              <span>今天怎么做</span><strong>{escape(verdict.action)}</strong>
            </div>
            <div class="essence-risk" data-essence-risk>
              <span>最大风险</span><strong>{escape(verdict.primary_risk)}</strong>
            </div>
          </div>
          <small>{escape(verdict.risk_budget)} · 下次复核：{escape(verdict.next_review)}</small>
        </div>
      </section>
      <section class="essence-focus-list" aria-labelledby="portfolio-queue-title">
        <h3 id="portfolio-queue-title">优先处理</h3>
        <div class="portfolio-treatment-queue">{queue}</div>
      </section>
      {render_iwencai_research_console(
          module="portfolio",
          status=iwencai_status,
          context_options=research_options,
      )}
      {evidence}
    </section>"""


def _render_queue_item(item: PortfolioQueueItem) -> str:
    return (
        f'<article class="portfolio-queue-item state-{_state_class(item.state)}">'
        f'<header><div><strong>{escape(item.name)}</strong>'
        f"<small>{escape(item.code)} · 当前权重 {item.current_weight:.1%}</small></div>"
        f"<em>{escape(item.state)}</em></header>"
        '<div class="portfolio-queue-reason"><span>处置依据</span>'
        f"<p>{escape(item.reason)}</p></div>"
        '<div class="portfolio-invalidation"><span>失效条件</span>'
        f"<strong>{escape(item.invalidation)}</strong></div></article>"
    )


def _render_queue_audit_item(item: PortfolioQueueItem) -> str:
    return (
        '<article class="portfolio-queue-audit-item">'
        f"<header><strong>{escape(item.name)} · {escape(item.code)}</strong>"
        f"<em>{escape(item.state)}</em></header>"
        f"<p>{escape(item.cost_context)}</p>"
        f"<dl><div><dt>处置依据</dt><dd>{escape(item.reason)}</dd></div>"
        f"<div><dt>复核触发</dt><dd>{escape(item.trigger)}</dd></div>"
        f"<div><dt>失效条件</dt><dd>{escape(item.invalidation)}</dd></div></dl>"
        "</article>"
    )


def _render_boundary(item: PortfolioBoundary) -> str:
    return (
        '<article class="portfolio-boundary-card">'
        f"<header><div><strong>{escape(item.name)}</strong><small>{escape(item.code)}</small></div>"
        f"<em>{escape(item.current_action)}</em></header>"
        f'<dl><div><dt>持仓边界</dt><dd>{escape(item.target_range)}</dd></div>'
        f"<div><dt>降低风险触发</dt><dd>{escape(item.reduce_trigger)}</dd></div>"
        f"<div><dt>失效条件</dt><dd>{escape(item.invalidation)}</dd></div></dl>"
        '<p class="portfolio-prohibited"><span>禁止动作</span>'
        f"{escape(item.prohibited_action)}</p></article>"
    )


def _state_class(state: str) -> str:
    return {
        "必须处理": "critical",
        "重点观察": "watch",
        "可继续持有": "steady",
        "待补数据": "blocked",
    }.get(state, "watch")
