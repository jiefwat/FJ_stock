from __future__ import annotations

from html import escape

from stock_ts.research.stock_dossier_models import DiagnosticBlock, ProfessionalStockDossier
from stock_ts.research.stock_memo import ResearchSection, StockResearchMemo


def render_stock_workspace(
    dossier: ProfessionalStockDossier | StockResearchMemo,
    *,
    identity_html: str = "",
    supporting_evidence_html: str = "",
    technical_html: str = "",
    trade_plan_html: str = "",
    agent_debate_html: str = "",
    refresh_html: str = "",
) -> str:
    if isinstance(dossier, StockResearchMemo):
        return _render_memo_workspace(
            dossier,
            identity_html=identity_html,
            technical_html=technical_html,
            trade_plan_html=trade_plan_html,
            agent_debate_html=agent_debate_html,
            refresh_html=refresh_html,
        )
    supporting = supporting_evidence_html + technical_html + trade_plan_html + agent_debate_html
    return _render_dossier_workspace(
        dossier,
        identity_html=identity_html,
        supporting_evidence_html=supporting,
        refresh_html=refresh_html,
    )


def _render_dossier_workspace(
    dossier: ProfessionalStockDossier,
    *,
    identity_html: str,
    supporting_evidence_html: str,
    refresh_html: str,
) -> str:
    verdict = dossier.verdict
    decision_steps = "".join(
        "<article class=\"decision-rail-step "
        f"{escape(item.state)}\">"
        f"<span>{escape(item.label)}</span>"
        "<div>"
        f"<strong>{escape(item.condition)}</strong>"
        f"<p>{escape(item.consequence)}</p>"
        "</div></article>"
        for item in dossier.decision_steps
    )
    risk_rows = "".join(
        "<article class=\"risk-register-item "
        f"severity-{escape(item.severity)}\">"
        f"<div><span>{escape(item.severity.upper())}</span><strong>{escape(item.category)}</strong></div>"
        f"<p>{escape(item.evidence)}</p>"
        f"<small>影响：{escape(item.consequence)} · 复核：{escape(item.monitor)}</small>"
        "</article>"
        for item in dossier.risks
    )
    if not risk_rows:
        risk_rows = (
            '<div class="dossier-empty-state">未识别高等级标题风险；仍需持续复核公告原文。</div>'
        )
    diagnostic_cards = "".join(_render_diagnostic(item) for item in dossier.diagnostics)
    scenario_cards = "".join(
        "<article class=\"dossier-scenario-card\">"
        f"<span>{escape(item.name)}</span>"
        f"<strong>{escape(item.premise)}</strong>"
        f"<p><b>确认</b>{escape(item.confirmation)}</p>"
        f"<p><b>动作</b>{escape(item.action)}</p>"
        f"<p><b>失效</b>{escape(item.invalidation)}</p>"
        f"<small>证据：{escape(item.evidence_source)}</small>"
        "</article>"
        for item in dossier.scenarios
    )
    evidence_rows = "".join(
        "<tr>"
        f"<td>{escape(item.block)}</td>"
        f"<td><span class=\"evidence-status {escape(item.status.value)}\">"
        f"{escape(item.status.value)}</span></td>"
        f"<td>{escape(item.source or '来源缺失')}</td>"
        f"<td>{escape(item.as_of or '日期缺失')}</td>"
        f"<td>{escape(item.detail)}</td>"
        "</tr>"
        for item in dossier.evidence
    )
    position = dossier.position
    supporting = (
        "<details class=\"dossier-supporting-evidence\">"
        "<summary>展开原始诊断与支持证据</summary>"
        f"{supporting_evidence_html}</details>"
        if supporting_evidence_html
        else ""
    )
    return f"""
    <section class="stock-research-workspace stock-dossier"
      data-research-status="{escape(verdict.stance)}"
      data-evidence-grade="{escape(verdict.evidence_grade)}">
      <header class="stock-identity-strip">
        <div><span>研究标的</span>
          <strong>{escape(dossier.name)} · {escape(dossier.code)}</strong></div>
        <div><span>现价</span>
          <strong class="dossier-price">{dossier.latest_close:.2f}</strong></div>
        <div><span>数据日期</span><strong>{escape(dossier.trade_date or '日期缺失')}</strong></div>
        {refresh_html}
      </header>
      {identity_html}
      <section class="dossier-decision-brief" data-primary-stock-verdict="true"
        aria-labelledby="dossier-verdict-title">
        <div class="dossier-stance">
          <span>投委会结论</span>
          <h3 id="dossier-verdict-title">{escape(verdict.stance)}</h3>
          <strong>{escape(verdict.action)}</strong>
        </div>
        <div class="dossier-thesis">
          <div class="dossier-grade"><span>证据完整度</span>
            <strong>{escape(verdict.evidence_grade)} · {verdict.confidence}/100</strong></div>
          <p>{escape(verdict.thesis)}</p>
          <div class="dossier-evidence-pair">
            <div><span>最强证据</span><strong>{escape(verdict.strongest_evidence)}</strong></div>
            <div><span>最大反证</span><strong>{escape(verdict.strongest_counter_evidence)}</strong></div>
          </div>
          <small>适用周期：{escape(verdict.horizon)} ·
            下次复核：{escape(verdict.next_review)}</small>
        </div>
      </section>
      <div class="stock-dossier-grid">
        <section class="dossier-panel" aria-labelledby="decision-rail-title">
          <div class="dossier-heading"><span>DECISION</span>
            <h3 id="decision-rail-title">五步决策轨道</h3></div>
          <div class="decision-rail">{decision_steps}</div>
        </section>
        <section class="dossier-panel risk-register" aria-labelledby="risk-register-title">
          <div class="dossier-heading"><span>RISK FIRST</span>
            <h3 id="risk-register-title">风险登记表</h3></div>
          {risk_rows}
        </section>
      </div>
      <section class="dossier-position-panel" aria-labelledby="position-guidance-title">
        <div class="dossier-heading"><span>{escape(position.audience)}</span>
          <h3 id="position-guidance-title">仓位与执行边界</h3></div>
        <div class="dossier-position-grid">
          <div><span>当前动作</span><strong>{escape(position.current_action)}</strong></div>
          <div><span>仓位上限</span><strong>{escape(position.position_cap)}</strong></div>
          <div><span>风险预算</span><strong>{escape(position.risk_budget)}</strong></div>
          <div><span>入场触发</span><strong>{escape(position.entry_trigger)}</strong></div>
          <div><span>加仓确认</span><strong>{escape(position.add_trigger)}</strong></div>
          <div><span>减仓触发</span><strong>{escape(position.reduce_trigger)}</strong></div>
          <div><span>失效条件</span><strong>{escape(position.invalidation)}</strong></div>
          <div class="prohibited"><span>禁止动作</span>
            <strong>{escape(position.prohibited_action)}</strong></div>
        </div>
      </section>
      <section aria-labelledby="diagnostic-title">
        <div class="dossier-section-title"><span>RESEARCH FILE</span>
          <h3 id="diagnostic-title">诊断底稿</h3>
          <p>每项结论同时展示事实、风险与口径限制。</p></div>
        <div class="dossier-diagnostic-grid">{diagnostic_cards}</div>
      </section>
      <section aria-labelledby="dossier-scenarios-title">
        <div class="dossier-section-title"><span>SCENARIOS</span>
          <h3 id="dossier-scenarios-title">三种情景</h3>
          <p>不填虚假概率，只定义确认、动作和失效。</p></div>
        <div class="dossier-scenario-grid">{scenario_cards}</div>
      </section>
      <details class="evidence-audit dossier-evidence-ledger">
        <summary>证据账本 · 来源、日期、状态与限制</summary>
        <table class="data-table"><thead><tr>
          <th>证据块</th><th>状态</th><th>来源</th><th>日期</th><th>结论与限制</th>
        </tr></thead><tbody>{evidence_rows}</tbody></table>
      </details>
      {supporting}
    </section>"""


def _render_diagnostic(item: DiagnosticBlock) -> str:
    facts = "".join(f"<li>{escape(value)}</li>" for value in item.facts)
    risks = "".join(f"<li>{escape(value)}</li>" for value in item.risks)
    return (
        f'<article class="dossier-diagnostic-card status-{escape(item.status)}">'
        f"<div><span>{escape(item.status)}</span><h4>{escape(item.name)}</h4></div>"
        f"<strong>{escape(item.conclusion)}</strong>"
        f'<ul class="diagnostic-facts">{facts}</ul>'
        f'<ul class="diagnostic-risks">{risks}</ul>'
        f"<small>{escape(item.limitation)}</small>"
        "</article>"
    )


def _render_memo_workspace(
    memo: StockResearchMemo,
    *,
    identity_html: str = "",
    technical_html: str = "",
    trade_plan_html: str = "",
    agent_debate_html: str = "",
    refresh_html: str = "",
) -> str:
    scenario_html = "".join(
        "<article class='research-scenario-card'>"
        f"<span>{escape(item.name)}情景</span>"
        f"<strong>{escape(item.premises)}</strong>"
        f"<p>观察：{escape(item.signals)}</p>"
        f"<p>动作：{escape(item.action)}</p>"
        f"<small>证伪：{escape(item.invalidation)}</small>"
        "</article>"
        for item in memo.scenarios
    )
    evidence_html = "".join(
        "<article class='stock-evidence-card'>"
        f"<div><span>{escape(item.block)}</span>"
        f"<em class='evidence-status {escape(item.status.value)}'>"
        f"{escape(item.status.value)}</em></div>"
        f"<strong>{escape(item.detail)}</strong>"
        f"<small>{escape(item.source or '来源缺失')} · {escape(item.as_of or '日期缺失')}</small>"
        "</article>"
        for item in memo.evidence
    )
    audit_rows = "".join(
        "<tr>"
        f"<td>{escape(item.block)}</td><td>{escape(item.status.value)}</td>"
        f"<td>{escape(item.source or '来源缺失')}</td>"
        f"<td>{escape(item.as_of or '日期缺失')}</td><td>{escape(item.detail)}</td>"
        "</tr>"
        for item in memo.evidence
    )
    memo_sections = "".join(
        _render_section(section)
        for section in (memo.business, memo.quality, memo.valuation, memo.expectation_gap)
    )
    secondary_sections = "".join(
        _render_section(section)
        for section in (memo.technical, memo.capital, memo.events, memo.portfolio)
    )
    return f"""
    <section class="stock-research-workspace"
      data-research-status="{escape(memo.verdict.status)}">
      <header class="stock-identity-strip">
        <div><span>研究标的</span><strong>{escape(memo.name)} · {escape(memo.code)}</strong></div>
        <div><span>价格</span><strong>{memo.latest_close:.2f}</strong></div>
        <div><span>数据日期</span><strong>{escape(memo.trade_date)}</strong></div>
        {refresh_html}
      </header>
      {identity_html}
      <section class="stock-thesis-board" aria-labelledby="stock-thesis-title">
        <div class="stock-thesis-status">
          <span>研究结论</span>
          <h3 id="stock-thesis-title">{escape(memo.verdict.status)}</h3>
          <strong>置信度 {memo.verdict.confidence}/100</strong>
        </div>
        <div class="thesis-conflict">
          <span>核心矛盾</span><strong>{escape(memo.verdict.core_conflict)}</strong>
          <div class="thesis-evidence-pair">
            <p><b>最强证据</b>{escape(memo.verdict.strongest_evidence)}</p>
            <p><b>最强反证</b>{escape(memo.verdict.strongest_counter_evidence)}</p>
          </div>
        </div>
      </section>
      <section aria-labelledby="investment-memo-title">
        <div class="research-section-heading">
          <span>01</span><div><h3 id="investment-memo-title">投资备忘录</h3>
          <p>把公司质量、市场预期和估值约束放在价格信号之前。</p></div>
        </div>
        <div class="investment-memo-grid">{memo_sections}</div>
      </section>
      <section aria-labelledby="stock-scenarios-title">
        <div class="research-section-heading">
          <span>02</span><div><h3 id="stock-scenarios-title">三情景推演</h3>
          <p>不预测确定收益，只定义前提、信号、动作和证伪。</p></div>
        </div>
        <div class="research-scenario-grid">{scenario_html}</div>
      </section>
      <section aria-labelledby="stock-evidence-title">
        <div class="research-section-heading">
          <span>03</span><div><h3 id="stock-evidence-title">六类证据</h3>
          <p>经营、估值、技术、资金、事件和组合上下文分别审计。</p></div>
        </div>
        <div class="stock-evidence-grid">{evidence_html}</div>
        <div class="investment-memo-grid">{secondary_sections}</div>
        {technical_html}
      </section>
      <section class="research-actions" aria-labelledby="research-actions-title">
        <span>下一步研究动作</span>
        <h3 id="research-actions-title">{escape(memo.verdict.next_review)}</h3>
      </section>
      <section class="trade-plan-section" aria-labelledby="trade-plan-title">
        <div class="research-section-heading">
          <span>04</span><div><h3 id="trade-plan-title">交易计划</h3>
          <p>交易触发不能反向证明投资逻辑。</p></div>
        </div>
        {trade_plan_html}
      </section>
      <details class="evidence-audit">
        <summary>证据审计 · 来源、日期与研究限制</summary>
        <table class="data-table"><thead><tr>
          <th>证据块</th><th>状态</th><th>来源</th><th>日期</th><th>限制</th>
        </tr></thead><tbody>{audit_rows}</tbody></table>
      </details>
      <details class="agent-debate">
        <summary>完整角色审议 · 多空、交易员与风险经理</summary>
        {agent_debate_html}
      </details>
    </section>"""


def _render_section(section: ResearchSection) -> str:
    facts = "".join(f"<li>{escape(item)}</li>" for item in section.facts)
    checks = "".join(f"<li>{escape(item)}</li>" for item in section.next_checks)
    return (
        "<article class='investment-memo-card'>"
        f"<span>{escape(section.title)}</span>"
        f"<strong>{escape(section.conclusion)}</strong>"
        f"<ul>{facts}</ul>"
        f"<p>{escape(section.limitations)}</p>"
        f"<ul class='memo-next-checks'>{checks}</ul>"
        "</article>"
    )
