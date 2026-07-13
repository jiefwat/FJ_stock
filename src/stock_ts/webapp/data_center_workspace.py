from __future__ import annotations

from html import escape

from stock_ts.research.data_center_dossier_models import (
    DataCenterDossier,
    DataImpactLane,
    DataLedgerEntry,
    DataRecoveryStep,
)


def render_data_center_workspace(
    dossier: DataCenterDossier,
    *,
    refresh_html: str,
) -> str:
    gate = dossier.gate
    recovery = "".join(_render_recovery_step(item) for item in dossier.recovery_steps)
    if not recovery:
        recovery = (
            '<div class="data-recovery-empty"><strong>暂无数据域需要恢复</strong>'
            f"<p>{escape(gate.next_step)}</p></div>"
        )
    impacts = "".join(_render_impact_lane(item) for item in dossier.impacts)
    ledger = "".join(_render_ledger_entry(item) for item in dossier.ledger)
    if not ledger:
        ledger = (
            '<tr class="data-ledger-empty"><td colspan="7">'
            "数据域清单尚未生成；刷新后重新复核。</td></tr>"
        )
    gate_class = {
        "影响分析": "blocked",
        "需复核": "warn",
        "正常": "ready",
    }.get(gate.state, "warn")
    return f"""
      <section class="module panel data-command-center" id="module-data-center"
        aria-label="数据中台">
        <div class="editor-toolbar data-command-toolbar">
          <div><h3>数据中台</h3>
            <p class="section-subtitle">先恢复可信数据，再恢复研究结论。</p></div>
          <div class="module-header-meta">
            <span class="portfolio-chip">{escape(gate.state)} · {escape(dossier.updated_at)}</span>
            {refresh_html}
          </div>
        </div>
        <section class="data-readiness-brief state-{escape(gate_class)}"
          data-primary-data-verdict="true" aria-labelledby="data-readiness-title">
          <div class="data-readiness-state">
            <span>数据就绪闸门</span>
            <h3 id="data-readiness-title">{escape(gate.state)}</h3>
            <strong>{escape(gate.action)}</strong>
          </div>
          <div class="data-readiness-thesis">
            <p>{escape(gate.thesis)}</p>
            <div class="data-readiness-metrics">
              <div><span>阻断域</span><strong>{gate.blocked_count}</strong></div>
              <div><span>复核域</span><strong>{gate.warning_count}</strong></div>
              <div><span>可用域</span><strong>{gate.ready_count}</strong></div>
              <div><span>总域数</span><strong>{gate.total_count}</strong></div>
            </div>
            <small><span>下一步</span>{escape(gate.next_step)}</small>
          </div>
        </section>
        <div class="data-operations-grid">
          <section class="data-recovery-section" aria-labelledby="data-recovery-title">
            <div class="dossier-heading"><span>RESTORE ORDER</span>
              <h3 id="data-recovery-title">恢复运行轨道</h3>
              <p>按依赖顺序处理；每一步都要用更新时间或覆盖结果复核。</p></div>
            <div class="data-recovery-rail">{recovery}</div>
          </section>
          <section class="data-impact-section" aria-labelledby="data-impact-title">
            <div class="dossier-heading"><span>DOWNSTREAM IMPACT</span>
              <h3 id="data-impact-title">模块影响面</h3>
              <p>同一数据缺口会同时降低多个研究模块的结论强度。</p></div>
            <div class="data-impact-grid">{impacts}</div>
          </section>
        </div>
        <details class="data-source-ledger">
          <summary>查看 {len(dossier.ledger)} 个数据域的完整来源账本</summary>
          <div class="data-ledger-scroll">
            <table class="data-ledger-table">
              <thead><tr><th>数据域</th><th>状态</th><th>来源</th><th>日期 / 更新</th>
                <th>覆盖</th><th>缺口</th><th>研究影响</th></tr></thead>
              <tbody>{ledger}</tbody>
            </table>
          </div>
        </details>
      </section>"""


def _render_recovery_step(item: DataRecoveryStep) -> str:
    return f"""
      <article class="data-recovery-step severity-{escape(item.severity)}">
        <span class="data-recovery-number">{item.priority:02d}</span>
        <div class="data-recovery-copy">
          <header><strong>{escape(item.category)}</strong><em>{escape(item.status)}</em></header>
          <p><span>当前缺口</span>{escape(item.issue)}</p>
          <p><span>业务后果</span>{escape(item.consequence)}</p>
          <small><span>复核证据</span>{escape(item.verification)}</small>
        </div>
      </article>"""


def _render_impact_lane(item: DataImpactLane) -> str:
    status_label = {
        "blocked": "阻断",
        "warn": "降级",
        "ready": "可用",
    }.get(item.status, "复核")
    affected = "、".join(item.affected_domains) if item.affected_domains else "无"
    return f"""
      <article class="data-impact-lane state-{escape(item.status)}">
        <header><strong>{escape(item.label)}</strong><em>{escape(status_label)}</em></header>
        <p>{escape(item.guidance)}</p>
        <small>影响域：{escape(affected)}</small>
      </article>"""


def _render_ledger_entry(item: DataLedgerEntry) -> str:
    return f"""
      <tr id="{escape(_data_domain_anchor(item.category))}"
        class="data-ledger-card state-{escape(item.level)}">
        <td data-label="数据域"><strong>{escape(item.category)}</strong></td>
        <td data-label="状态"><span>{escape(item.status)}</span></td>
        <td data-label="来源">{escape(item.channel)}</td>
        <td data-label="日期 / 更新">{escape(item.latest_at)}</td>
        <td data-label="覆盖">{escape(item.coverage)}</td>
        <td data-label="缺口">{escape(item.missing)}</td>
        <td data-label="研究影响">{escape(item.impact)}</td>
      </tr>"""


def _data_domain_anchor(category: str) -> str:
    mapping = {
        "大盘行情": "data-domain-market",
        "K线行情": "data-domain-kline",
        "技术面": "data-domain-technical",
        "候选池": "data-domain-candidates",
        "资金面": "data-domain-fund",
        "新闻舆情": "data-domain-news",
        "公告": "data-domain-announcement",
        "基本面": "data-domain-fundamental",
        "全链路校验": "data-domain-chain",
    }
    return mapping.get(category, "data-domain-other")
