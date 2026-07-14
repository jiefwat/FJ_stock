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
    iwencai_status: str = "missing",
) -> str:
    if isinstance(dossier, StockResearchMemo):
        return _render_memo_workspace(
            dossier,
            identity_html=identity_html,
            technical_html=technical_html,
            trade_plan_html=trade_plan_html,
            agent_debate_html=agent_debate_html,
            refresh_html=refresh_html,
            iwencai_status=iwencai_status,
        )
    supporting = supporting_evidence_html + technical_html + trade_plan_html + agent_debate_html
    return _render_dossier_workspace(
        dossier,
        identity_html=identity_html,
        supporting_evidence_html=supporting,
        refresh_html=refresh_html,
        iwencai_status=iwencai_status,
    )


def _render_dossier_workspace(
    dossier: ProfessionalStockDossier,
    *,
    identity_html: str,
    supporting_evidence_html: str,
    refresh_html: str,
    iwencai_status: str,
) -> str:
    verdict = dossier.verdict
    decision_conditions = "".join(
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
        for item in dossier.risks[:3]
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
    thesis_chain = "".join(
        "<article class=\"thesis-spine-step\">"
        f"<span>{escape(label)}</span><strong>{escape(item)}</strong>"
        "</article>"
        for label, item in zip(("事实", "推断", "验证"), dossier.thesis.causal_chain)
    )
    weighted_evidence = "".join(
        "<article class=\"weighted-evidence-row\" "
        f'data-direction="{escape(item.direction)}">'
        "<header>"
        f"<span>{escape(item.dimension)}</span>"
        f"<em>{escape(item.importance)}权重</em>"
        f"<strong>{escape(item.direction)}</strong>"
        "</header>"
        "<div>"
        f"<p><b>事实</b>{escape(item.fact)}</p>"
        f"<p><b>推断</b>{escape(item.inference)}</p>"
        f"<small><b>未知</b>{escape(item.unknown)}</small>"
        "</div></article>"
        for item in dossier.weighted_evidence
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
    evidence = f"""
      <details class="stock-evidence essence-evidence">
        <summary>证据账本</summary>
        <div class="essence-evidence-body">
          <div class="dossier-diagnostic-grid">{diagnostic_cards}</div>
          <table class="data-table"><thead><tr>
            <th>证据块</th><th>状态</th><th>来源</th><th>日期</th><th>结论与限制</th>
          </tr></thead><tbody>{evidence_rows}</tbody></table>
          {supporting_evidence_html}
        </div>
      </details>"""
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
      <section class="dossier-decision-brief" data-primary-stock-verdict="true"
        aria-labelledby="dossier-verdict-title">
        <div class="dossier-stance">
          <span>投资判断</span>
          <h3 id="dossier-verdict-title">{escape(verdict.stance)}</h3>
          <strong>{escape(verdict.action)}</strong>
        </div>
        <div class="dossier-thesis">
          <div class="dossier-grade"><span>研究假设</span>
            <strong>{escape(verdict.evidence_grade)} ·
              完整度 {verdict.confidence}/100</strong></div>
          <p>{escape(dossier.thesis.headline)}</p>
          <div class="dossier-core-conflict">
            <span>核心矛盾</span><strong>{escape(dossier.thesis.core_conflict)}</strong>
          </div>
          <div class="dossier-research-meta">
            <div><span>预期差</span><strong>{escape(dossier.thesis.expectation_gap)}</strong></div>
            <div><span>估值匹配</span><strong>{escape(dossier.thesis.valuation_fit)}</strong></div>
            <div><span>关键未知</span><strong>{escape(dossier.thesis.key_unknown)}</strong></div>
          </div>
          <small>适用周期：{escape(verdict.horizon)} ·
            下次复核：{escape(verdict.next_review)}</small>
        </div>
      </section>
      {identity_html}
      <div class="dossier-action-grid">
        <section class="dossier-panel" aria-labelledby="decision-rail-title">
          <h3 id="decision-rail-title">决策条件</h3>
          <div class="decision-rail">{decision_conditions}</div>
        </section>
        <section class="dossier-position-panel" aria-labelledby="position-guidance-title">
          <h3 id="position-guidance-title">执行边界</h3>
          <div class="dossier-position-grid">
            <div><span>当前动作</span><strong>{escape(position.current_action)}</strong></div>
            <div><span>仓位 / 风险预算</span>
              <strong>{escape(position.position_cap)} ·
                {escape(position.risk_budget)}</strong></div>
            <div><span>入场 / 加仓</span>
              <strong>{escape(position.entry_trigger)}；{escape(position.add_trigger)}</strong></div>
            <div><span>减仓 / 退出</span>
              <strong>{escape(position.reduce_trigger)}；{escape(position.invalidation)}</strong></div>
            <div class="prohibited"><span>禁止动作</span>
              <strong>{escape(position.prohibited_action)}</strong></div>
          </div>
        </section>
      </div>
      <section class="dossier-thesis-spine" aria-labelledby="thesis-spine-title">
        <h3 id="thesis-spine-title">论点链</h3>
        <div class="thesis-spine">{thesis_chain}</div>
      </section>
      <section class="weighted-evidence" aria-labelledby="weighted-evidence-title">
        <h3 id="weighted-evidence-title">关键证据</h3>
        <div class="weighted-evidence-list">{weighted_evidence}</div>
      </section>
      {_render_iwencai_research_console(
          dossier.code, dossier.name, dossier.trade_date, iwencai_status
      )}
      <section class="dossier-panel risk-register" aria-labelledby="risk-register-title">
        <h3 id="risk-register-title">风险反证</h3>
        {risk_rows}
      </section>
      <section aria-labelledby="dossier-scenarios-title">
        <h3 id="dossier-scenarios-title">三情景</h3>
        <div class="dossier-scenario-grid">{scenario_cards}</div>
      </section>
      {evidence}
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
    iwencai_status: str = "missing",
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
        <h3 id="investment-memo-title">投资备忘录</h3>
        <div class="investment-memo-grid">{memo_sections}</div>
      </section>
      <section aria-labelledby="stock-scenarios-title">
        <h3 id="stock-scenarios-title">三情景推演</h3>
        <div class="research-scenario-grid">{scenario_html}</div>
      </section>
      <section aria-labelledby="stock-evidence-title">
        <h3 id="stock-evidence-title">六类证据</h3>
        <div class="stock-evidence-grid">{evidence_html}</div>
      </section>
      {_render_iwencai_research_console(memo.code, memo.name, memo.trade_date, iwencai_status)}
      <section class="research-actions" aria-labelledby="research-actions-title">
        <span>下一步研究动作</span>
        <h3 id="research-actions-title">{escape(memo.verdict.next_review)}</h3>
      </section>
      <section class="trade-plan-section" aria-labelledby="trade-plan-title">
        <h3 id="trade-plan-title">交易计划</h3>
        {trade_plan_html}
      </section>
      <details class="stock-evidence essence-evidence">
        <summary>证据账本</summary>
        <div class="essence-evidence-body">
          <div class="investment-memo-grid">{secondary_sections}</div>
          {technical_html}
          <table class="data-table"><thead><tr>
            <th>证据块</th><th>状态</th><th>来源</th><th>日期</th><th>限制</th>
          </tr></thead><tbody>{audit_rows}</tbody></table>
          {agent_debate_html}
        </div>
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


def _render_iwencai_research_console(
    code: str,
    name: str,
    local_as_of: str,
    status: str,
) -> str:
    configured = status == "configured"
    blocked = status == "requires_login"
    status_label = "已连接" if configured else ("需启用登录" if blocked else "未配置")
    status_class = "connected" if configured else ("blocked" if blocked else "missing")
    disabled = " disabled" if blocked else ""
    suggestions = (
        ("财务质量", "收入、利润和现金流质量是否同步改善？"),
        ("机构预期", "未来两年盈利预期和机构评级如何变化？"),
        ("事件风险", "近期是否有解禁、质押、监管或业绩预告风险？"),
        ("行业位置", "当前行业估值和盈利排名处于什么位置？"),
    )
    suggestion_html = "".join(
        '<button type="button" class="iwencai-question-chip" '
        f'data-iwencai-question="{escape(question)}"{disabled}>{escape(label)}</button>'
        for label, question in suggestions
    )
    return f"""
      <section class="iwencai-research-console" data-iwencai-research="true"
        data-stock-code="{escape(code)}" data-stock-name="{escape(name)}"
        data-local-as-of="{escape(local_as_of)}" data-config-status="{escape(status)}"
        aria-labelledby="iwencai-research-title">
        <header class="iwencai-research-header">
          <div><span>股票研究 · 外部证据</span>
            <h3 id="iwencai-research-title">问财研究追问</h3></div>
          <strong class="iwencai-connection {status_class}">
            {status_label}</strong>
        </header>
        <div class="iwencai-question-rail">{suggestion_html}</div>
        <form class="iwencai-research-form" data-iwencai-form>
          <label class="sr-only" for="iwencai-question-{escape(code)}">研究问题</label>
          <textarea id="iwencai-question-{escape(code)}" name="question" maxlength="200"
            rows="2" required data-iwencai-input{disabled}
            placeholder="例如：未来两年盈利预期是否改善？"></textarea>
          <button type="submit" data-iwencai-submit{disabled}>查询问财</button>
        </form>
        <p class="iwencai-console-state" data-iwencai-state>
          {'启用登录后可查询问财。' if blocked else '问财结果只作证据补充，不改写本地结论。'}</p>
        <div class="iwencai-research-result" data-iwencai-result hidden aria-live="polite"></div>
      </section>"""
