from __future__ import annotations

from html import escape
from urllib.parse import urlencode

from stock_ts.research.opportunity_dossier_models import (
    CandidateDecision,
    OpportunityDossier,
)


def render_opportunity_workspace(
    dossier: OpportunityDossier,
    *,
    provider_name: str,
    holdings_path: str,
    supporting_html: str = "",
) -> str:
    gate = dossier.gate
    scanned = str(gate.scanned_count) if gate.scanned_count is not None else "未知"
    funnel = "".join(
        "<article class=\"opportunity-funnel-step "
        f"stage-{escape(item.status)}\">"
        f"<span>{escape(item.name)}</span><strong>{item.count}</strong>"
        f"<p>{escape(item.note)}</p></article>"
        for item in dossier.funnel
    )
    risks = "".join(
        "<article class=\"opportunity-risk-item "
        f"severity-{escape(item.severity)}\">"
        f"<div><span>{escape(item.severity.upper())}</span>"
        f"<strong>{escape(item.category)}</strong></div>"
        f"<p>{escape(item.evidence)}</p>"
        f"<small>{escape(item.consequence)}</small></article>"
        for item in dossier.risks
    )
    candidates = "".join(
        _render_candidate(item, provider_name=provider_name, holdings_path=holdings_path)
        for item in dossier.candidates
    )
    if not candidates:
        candidates = (
            '<div class="dossier-empty-state">候选池为空；刷新候选源后重新生成研究漏斗。</div>'
        )
    source_notes = "".join(f"<li>{escape(item)}</li>" for item in dossier.source_notes)
    return f"""
    <section class="opportunity-dossier"
      data-opportunity-state="{escape(gate.state)}">
      <section class="opportunity-gate-brief" data-primary-opportunity-verdict="true"
        aria-labelledby="opportunity-gate-title">
        <div class="opportunity-gate-state">
          <span>机会总闸门</span>
          <h3 id="opportunity-gate-title">{escape(gate.state)}</h3>
          <strong>{escape(gate.action)}</strong>
        </div>
        <div class="opportunity-gate-thesis">
          <p>{escape(gate.thesis)}</p>
          <div class="opportunity-gate-metrics">
            <div><span>市场风险预算</span><strong>{escape(gate.risk_budget)}</strong></div>
            <div><span>扫描范围</span><strong>{escape(scanned)}</strong></div>
            <div><span>证据就绪</span><strong>{gate.evidence_ready_count}</strong></div>
            <div><span>可验证</span><strong>{gate.eligible_count}</strong></div>
          </div>
          <small>数据状态：{escape(gate.data_status)} · 下一步：{escape(gate.next_step)}</small>
        </div>
      </section>
      <section aria-labelledby="opportunity-funnel-title">
        <div class="dossier-section-title"><span>RESEARCH FUNNEL</span>
          <h3 id="opportunity-funnel-title">证据漏斗</h3>
          <p>先校验数据，再排除风险，最后才开放个股验证。</p></div>
        <div class="opportunity-funnel-rail">{funnel}</div>
      </section>
      <div class="opportunity-research-grid">
        <section aria-labelledby="opportunity-candidates-title">
          <div class="dossier-heading"><span>CANDIDATES</span>
            <h3 id="opportunity-candidates-title">研究候选</h3></div>
          <div class="candidate-decision-grid">{candidates}</div>
        </section>
        <section class="opportunity-risk-register" aria-labelledby="opportunity-risks-title">
          <div class="dossier-heading"><span>RISK FIRST</span>
            <h3 id="opportunity-risks-title">风险排除</h3></div>
          {risks}
        </section>
      </div>
      <details class="opportunity-source-ledger">
        <summary>筛选与来源账本</summary>
        <ul>{source_notes}</ul>
      </details>
      {supporting_html}
    </section>"""


def _render_candidate(
    item: CandidateDecision,
    *,
    provider_name: str,
    holdings_path: str,
) -> str:
    evidence = "".join(f"<li>{escape(value)}</li>" for value in item.evidence)
    counter = "".join(f"<li>{escape(value)}</li>" for value in item.counter_evidence)
    query = urlencode(
        {
            "code": item.code,
            "provider": provider_name,
            "holdings": holdings_path,
            "candidate_source": "opportunity",
            "candidate_strategy_label": item.strategy,
            "candidate_evidence": "；".join(item.evidence),
        }
    )
    exclusion = (
        f"<p class=\"candidate-exclusion\">排除原因：{escape(item.exclusion_reason)}</p>"
        if item.exclusion_reason
        else ""
    )
    return f"""
      <article class="candidate-decision-card state-{_state_class(item.state)}"
        data-opportunity-stock-row>
        <header><div><span>{escape(item.code)}</span><strong>{escape(item.name)}</strong></div>
          <em>{escape(item.state)}</em></header>
        <p class="candidate-strategy">{escape(item.sector)} · {escape(item.strategy)}</p>
        <div class="candidate-evidence-pair">
          <div><span>支持证据</span><ul>{evidence}</ul></div>
          <div><span>最大反证</span><ul>{counter}</ul></div>
        </div>
        {exclusion}
        <small>数据：{escape(item.data_status.value)} ·
          {escape(item.data_date or '日期缺失')}</small>
        <p class="candidate-next-step">下一步：{escape(item.next_verification)}</p>
        <a class="primary-button" href="/?{escape(query, quote=True)}#stock">进入个股分析</a>
      </article>"""


def _state_class(state: str) -> str:
    return {
        "可验证": "eligible",
        "只观察": "watch",
        "风险排除": "excluded",
        "待补数据": "blocked",
    }.get(state, "watch")
