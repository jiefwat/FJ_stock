from __future__ import annotations

from html import escape

from stock_ts.research.stock_memo import ResearchSection, StockResearchMemo


def render_stock_workspace(
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
