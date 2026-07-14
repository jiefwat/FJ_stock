from __future__ import annotations

from html import escape
from urllib.parse import urlencode

from stock_ts.research.opportunity_dossier_models import (
    CandidateDecision,
    OpportunityDossier,
)
from stock_ts.webapp.research_console import (
    ResearchContextOption,
    render_iwencai_research_console,
)


def render_opportunity_workspace(
    dossier: OpportunityDossier,
    *,
    provider_name: str,
    holdings_path: str,
    supporting_html: str = "",
    iwencai_status: str = "missing",
) -> str:
    gate = dossier.gate
    scanned = str(gate.scanned_count) if gate.scanned_count is not None else "未知"
    funnel = "".join(
        "<article class=\"opportunity-funnel-step "
        f"stage-{escape(item.status)}\">"
        f"<span>{escape(item.name)}</span><strong>{item.count}</strong></article>"
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
    front_candidates = dossier.candidates[:3]
    overflow_candidates = dossier.candidates[3:]
    candidates = "".join(
        _render_candidate(item, provider_name=provider_name, holdings_path=holdings_path)
        for item in front_candidates
    )
    overflow_cards = "".join(
        _render_candidate(
            item,
            provider_name=provider_name,
            holdings_path=holdings_path,
        )
        for item in overflow_candidates
    )
    if not candidates:
        candidates = (
            '<div class="dossier-empty-state">候选池为空；刷新候选源后重新生成研究漏斗。</div>'
    )
    source_notes = "".join(f"<li>{escape(item)}</li>" for item in dossier.source_notes)
    candidate_audit = "".join(_render_candidate_audit(item) for item in dossier.candidates)
    overflow_section = (
        f"<h4>其余 {len(overflow_candidates)} 只候选</h4>"
        f'<div class="candidate-decision-grid">{overflow_cards}</div>'
        if overflow_cards
        else ""
    )
    evidence = f"""
      <details class="opportunity-evidence essence-evidence">
        <summary>展开筛选依据</summary>
        <div class="essence-evidence-body">
          <section aria-labelledby="opportunity-funnel-title">
            <h3 id="opportunity-funnel-title">证据漏斗</h3>
            <div class="opportunity-funnel-rail essence-strip">{funnel}</div>
          </section>
          <div class="opportunity-gate-metrics">
            <div><span>数据状态</span><strong>{escape(gate.data_status)}</strong></div>
            <div><span>市场风险预算</span><strong>{escape(gate.risk_budget)}</strong></div>
            <div><span>扫描范围</span><strong>{escape(scanned)}</strong></div>
            <div><span>证据就绪</span><strong>{gate.evidence_ready_count}</strong></div>
            <div><span>可验证</span><strong>{gate.eligible_count}</strong></div>
          </div>
          <p class="essence-detail-meta">数据状态：{escape(gate.data_status)}</p>
          <section class="opportunity-risk-register" aria-labelledby="opportunity-risks-title">
            <h3 id="opportunity-risks-title">风险排除</h3>
            {risks}
          </section>
          {overflow_section}
          <div class="candidate-audit-grid">{candidate_audit}</div>
          <h3>筛选与来源账本</h3>
          <ul>{source_notes}</ul>
          {supporting_html}
        </div>
      </details>"""
    research_options = _research_context_options(dossier)
    primary_risk = (
        dossier.risks[0].evidence
        if dossier.risks
        else f"数据状态为 {gate.data_status}，候选必须逐只复核。"
    )
    return f"""
    <section class="opportunity-dossier"
      data-opportunity-state="{escape(gate.state)}">
      <section class="opportunity-gate-brief" data-primary-opportunity-verdict="true"
        aria-labelledby="opportunity-gate-title">
        <div class="opportunity-gate-state">
          <span>机会总闸门</span>
          <h3 id="opportunity-gate-title">{escape(gate.state)}</h3>
        </div>
        <div class="opportunity-gate-thesis">
          <p>{escape(gate.thesis)}</p>
          <div class="essence-action-risk">
            <div class="essence-action" data-essence-action>
              <span>今天怎么做</span><strong>{escape(gate.action)}</strong>
            </div>
            <div class="essence-risk" data-essence-risk>
              <span>最大风险</span><strong>{escape(primary_risk)}</strong>
            </div>
          </div>
          <small>下一步：{escape(gate.next_step)}</small>
        </div>
      </section>
      <section class="essence-focus-list" aria-labelledby="opportunity-candidates-title">
        <h3 id="opportunity-candidates-title">研究候选</h3>
        <div class="candidate-decision-grid">{candidates}</div>
      </section>
      {render_iwencai_research_console(
          module="opportunity",
          status=iwencai_status,
          context_options=research_options,
      )}
      {evidence}
    </section>"""


def _research_context_options(
    dossier: OpportunityDossier,
) -> tuple[ResearchContextOption, ...]:
    sectors = tuple(dict.fromkeys(item.sector for item in dossier.candidates if item.sector))[:5]
    sector_options = tuple(
        ResearchContextOption(sector=sector, label=f"{sector} · 板块")
        for sector in sectors
    )
    candidate_options = tuple(
        ResearchContextOption(
            code=item.code,
            name=item.name,
            sector=item.sector,
            label=f"{item.name} · {item.code}",
        )
        for item in dossier.candidates[:8]
    )
    return sector_options + candidate_options


def _render_candidate(
    item: CandidateDecision,
    *,
    provider_name: str,
    holdings_path: str,
) -> str:
    evidence = "".join(f"<li>{escape(value)}</li>" for value in item.evidence[:1])
    counter = "".join(f"<li>{escape(value)}</li>" for value in item.counter_evidence[:1])
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


def _render_candidate_audit(item: CandidateDecision) -> str:
    evidence = "".join(f"<li>{escape(value)}</li>" for value in item.evidence)
    counter = "".join(f"<li>{escape(value)}</li>" for value in item.counter_evidence)
    return (
        '<article class="candidate-audit-card">'
        f"<strong>{escape(item.name)} · {escape(item.code)}</strong>"
        f"<div><span>支持证据</span><ul>{evidence}</ul></div>"
        f"<div><span>最大反证</span><ul>{counter}</ul></div>"
        "</article>"
    )
