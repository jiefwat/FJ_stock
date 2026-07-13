from __future__ import annotations

from html import escape

from stock_ts.research.market_regime import MarketRegimeAssessment


def render_market_workspace(
    assessment: MarketRegimeAssessment,
    *,
    distribution_html: str = "",
    sectors_html: str = "",
    events_html: str = "",
    refresh_html: str = "",
    supporting_html: str = "",
) -> str:
    rail_state, rail_items = _market_decision_steps(assessment)
    decision_rail = "".join(
        '<article class="market-decision-rail-step '
        f'{escape(state)}"><span>{index:02d}</span><div>'
        f"<small>{escape(label)}</small><strong>{escape(condition)}</strong>"
        f"<p>{escape(consequence)}</p></div></article>"
        for index, (label, condition, consequence, state) in enumerate(
            rail_items, start=1
        )
    )
    support = "".join(f"<li>{escape(item)}</li>" for item in assessment.supporting_evidence)
    counters = "".join(f"<li>{escape(item)}</li>" for item in assessment.counter_evidence)
    dimensions = "".join(
        "<article class='market-dimension-card'>"
        f"<div><span>{escape(item.name)}</span>"
        f"<em class='evidence-status {escape(item.status.value)}'>"
        f"{escape(item.status.value)}</em></div>"
        f"<strong>{escape(item.conclusion)}</strong>"
        f"<p>{escape(item.evidence)}</p>"
        f"<small>置信度 {item.confidence}/100</small>"
        "</article>"
        for item in assessment.dimensions
    )
    scenarios = "".join(
        "<article class='research-scenario-card'>"
        f"<span>{escape(item.name)}情景</span>"
        f"<strong>{escape(item.trigger)}</strong>"
        f"<p>风险动作：{escape(item.action)}</p>"
        f"<small>证伪：{escape(item.invalidation)}</small>"
        "</article>"
        for item in assessment.scenarios
    )
    audit_rows = "".join(
        "<tr>"
        f"<td>{escape(item.name)}</td>"
        f"<td>{escape(item.status.value)}</td>"
        f"<td>{escape(item.evidence)}</td>"
        f"<td>{escape('、'.join(item.missing_fields) or '无')}</td>"
        "</tr>"
        for item in assessment.dimensions
    )
    return f"""
    <section class="market-research-workspace" data-market-stage="{escape(assessment.stage)}">
      <header class="market-state-strip">
        <div><span>市场状态</span><strong>{escape(assessment.stage)}</strong></div>
        <div><span>市场风险预算</span><strong>{escape(assessment.risk_budget)}</strong></div>
        <div><span>研究置信度</span><strong>{assessment.confidence}/100</strong></div>
        <div><span>数据日期</span><strong>{escape(assessment.trade_date)}</strong></div>
        {refresh_html}
      </header>
      <section class="market-thesis-board" data-primary-market-verdict="true"
        aria-labelledby="market-thesis-title">
        <div class="market-thesis-main">
          <span>核心判断</span><h3 id="market-thesis-title">{escape(assessment.thesis)}</h3>
          <ul>{support}</ul>
        </div>
        <div class="market-risk-card">
          <span>最大风险</span><strong>{escape(assessment.primary_risk)}</strong>
          <ul>{counters}</ul>
          <small>判断失效：{escape(assessment.invalidate_condition)}</small>
        </div>
      </section>
      <section class="market-decision-panel" data-market-rail-state="{rail_state}"
        aria-labelledby="market-decision-rail-title">
        <div class="dossier-section-title"><span>RISK GOVERNANCE</span>
          <h3 id="market-decision-rail-title">五步风险决策轨道</h3>
          <p>大盘判断只在这条链路中转化为总风险预算，不直接生成个股动作。</p></div>
        <div class="market-decision-rail">{decision_rail}</div>
      </section>
      <section aria-labelledby="market-structure-title">
        <div class="research-section-heading">
          <span>02</span><div><h3 id="market-structure-title">趋势与宽度</h3>
          <p>先看参与度和风险结构，再看热点。</p></div>
        </div>
        <div class="market-dimension-grid">{dimensions}</div>
        {distribution_html}
      </section>
      <section aria-labelledby="market-style-title">
        <div class="research-section-heading">
          <span>03</span><div><h3 id="market-style-title">风格与主线</h3>
          <p>识别扩散、依赖与退潮信号。</p></div>
        </div>
        {sectors_html}
      </section>
      <section aria-labelledby="market-scenarios-title">
        <div class="research-section-heading">
          <span>04</span><div><h3 id="market-scenarios-title">三情景推演</h3>
          <p>情景变化决定风险预算变化。</p></div>
        </div>
        <div class="research-scenario-grid">{scenarios}</div>
      </section>
      <section aria-labelledby="market-events-title">
        <div class="research-section-heading">
          <span>05</span><div><h3 id="market-events-title">流动性与事件</h3>
          <p>事件和极端波动优先进入风险审计。</p></div>
        </div>
        {events_html}
      </section>
      {supporting_html}
      <details class="evidence-audit">
        <summary>证据审计 · 数据来源、缺口与降级</summary>
        <table class="data-table"><thead><tr>
          <th>维度</th><th>状态</th><th>依据</th><th>缺口</th>
        </tr></thead><tbody>{audit_rows}</tbody></table>
      </details>
    </section>"""


def _market_decision_steps(
    assessment: MarketRegimeAssessment,
) -> tuple[str, tuple[tuple[str, str, str, str], ...]]:
    if assessment.stage == "数据暂停":
        return (
            "paused",
            (
                ("当前市场阶段", "数据暂停", "暂停沿用旧盘面结论，等待行情刷新。", "paused"),
                ("进攻确认", "暂停确认", "刷新宽度、情绪和指数证据后重新确认。", "paused"),
                ("仓位预算", "暂停新增风险", "刷新行情前不开放新的市场风险预算。", "paused"),
                ("降级触发", "暂停沿用旧触发", "刷新数据后重建风险触发条件。", "paused"),
                ("重新评估", "等待刷新", "最近交易日数据刷新并通过校验后重评。", "paused"),
            ),
        )
    support = assessment.supporting_evidence[0] if assessment.supporting_evidence else "证据待补"
    return (
        "active",
        (
            ("当前市场阶段", assessment.stage, assessment.thesis, "current"),
            ("进攻确认", support, "支持证据持续成立，才允许使用当前风险预算。", "confirm"),
            (
                "仓位预算",
                assessment.risk_budget,
                "该预算是组合总风险上限，下游模块只能收紧，不能放松。",
                "budget",
            ),
            (
                "降级触发",
                assessment.primary_risk,
                f"触发后收紧预算；判断失效条件：{assessment.invalidate_condition}",
                "downgrade",
            ),
            (
                "重新评估",
                f"{assessment.trade_date} 后续交易日",
                "收盘后重检数据质量、市场宽度、流动性、风格和情绪。",
                "review",
            ),
        ),
    )
