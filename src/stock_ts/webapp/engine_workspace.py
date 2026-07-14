from __future__ import annotations

import json
from html import escape

MODULE_META = {
    "market": ("每日大盘", "市场判断", "判断指数、宏观、主线与风险是否同向"),
    "portfolio": ("我的持仓", "组合诊断", "逐只核对事件、预期与价格风险"),
    "stock": ("个股分析", "公司研究", "核对经营、财务、预期与事件变化"),
    "opportunity": ("热点机会", "机会扫描", "先找方向，再筛候选并排除风险"),
}


def render_engine_workspace(
    module: str,
    *,
    status: str,
    context: dict[str, object] | None = None,
) -> str:
    if module not in MODULE_META:
        raise ValueError("不支持的研究模块。")
    title, label, scope = MODULE_META[module]
    status_label, status_class, available = _service_status(status)
    context_json = json.dumps(
        context or {},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    disabled = "" if available else " disabled"
    return f"""
    <section class="module engine-module" id="module-{escape(module)}"
      data-engine-workspace="{escape(module)}"
      data-engine-context="{escape(context_json, quote=True)}"
      data-engine-available="{'true' if available else 'false'}">
      <header class="engine-header">
        <div><span>{escape(label)}</span><h2>{escape(title)}</h2></div>
        <div class="engine-meta">
          <strong class="engine-service-state state-{status_class}" data-engine-service-state>
            {escape(status_label)}</strong>
          <time data-engine-generated>尚未生成</time>
        </div>
      </header>
      <section class="engine-judgment state-idle" data-engine-judgment>
        <div class="engine-signal-band" aria-hidden="true"><i></i></div>
        <div class="engine-verdict" data-engine-verdict-block>
          <span>当前判断</span>
          <h3 data-engine-verdict>等待生成判断</h3>
          <p>{escape(scope)}</p>
        </div>
        <div class="engine-action-risk">
          <article class="engine-action">
            <span>现在怎么做</span>
            <strong data-engine-action>进入页面后生成本次判断。</strong>
          </article>
          <article class="engine-risk">
            <span>最大风险</span>
            <strong data-engine-risk>研究完成前，不沿用旧结论。</strong>
          </article>
        </div>
      </section>
      <section class="engine-findings-block" aria-label="关键发现">
        <div class="engine-section-heading"><h3>关键发现</h3><small>最多三条</small></div>
        <div class="engine-findings" data-engine-findings>
          <div class="engine-empty">生成后显示最重要的三条事实。</div>
        </div>
      </section>
      <div class="engine-actions">
        <details class="engine-disclosure" data-engine-disclosure>
          <summary>查看完整依据</summary>
          <div class="engine-details" data-engine-details>
            <p>完整依据会按研究维度归档在这里。</p>
          </div>
        </details>
        <button class="engine-run-button" type="button" data-engine-run{disabled}>
          重新分析</button>
      </div>
      <p class="engine-live-state" data-engine-live-state aria-live="polite">
        {escape(status_label)}</p>
    </section>"""


def render_research_service_status(status: str) -> str:
    label, status_class, _available = _service_status(status)
    return f"""
    <section class="module engine-system-module" id="module-data-center">
      <header class="engine-header">
        <div><span>运行状态</span><h2>研究服务</h2></div>
        <strong class="engine-service-state state-{status_class}">{escape(label)}</strong>
      </header>
      <section class="engine-system-card">
        <div><span>页面模式</span><strong>按需生成</strong></div>
        <div><span>结果缓存</span><strong>5 分钟</strong></div>
        <div><span>失败处理</span><strong>暂停判断，不沿用旧结论</strong></div>
        <div><span>账户数据</span><strong>只提交研究对象，不提交仓位隐私</strong></div>
      </section>
    </section>"""


def engine_app_script() -> str:
    return r"""
  <script>
    const engineCache = new Map();

    function engineNode(tag, className, value) {
      const node = document.createElement(tag);
      if (className) node.className = className;
      if (value !== undefined && value !== null) node.textContent = String(value);
      return node;
    }

    function engineContext(workspace) {
      try {
        return JSON.parse(workspace.dataset.engineContext || '{}');
      } catch (_error) {
        return {};
      }
    }

    function engineKey(workspace) {
      return `${workspace.dataset.engineWorkspace}:${workspace.dataset.engineContext || '{}'}`;
    }

    function setEngineLoading(workspace, loading) {
      const button = workspace.querySelector('[data-engine-run]');
      const judgment = workspace.querySelector('[data-engine-judgment]');
      const live = workspace.querySelector('[data-engine-live-state]');
      if (button) {
        button.disabled = loading || workspace.dataset.engineAvailable !== 'true';
        button.textContent = loading ? '分析中' : '重新分析';
      }
      if (judgment) judgment.classList.toggle('is-loading', loading);
      if (live && loading) live.textContent = '正在生成判断…';
    }

    function renderEngineFinding(item) {
      const card = engineNode('article', 'engine-finding-card');
      card.append(engineNode('span', '', item.target || '研究发现'));
      card.append(engineNode('strong', '', item.title || '关键变化'));
      card.append(engineNode('p', '', item.summary || '证据已返回。'));
      const facts = Array.isArray(item.facts) ? item.facts.slice(0, 4) : [];
      if (facts.length) {
        const list = engineNode('dl', 'engine-fact-list');
        facts.forEach((fact) => {
          const row = engineNode('div', '');
          row.append(
            engineNode('dt', '', fact.label || '项目'),
            engineNode('dd', '', fact.value || '—')
          );
          list.append(row);
        });
        card.append(list);
      }
      return card;
    }

    function renderEngineDetails(workspace, payload) {
      const root = workspace.querySelector('[data-engine-details]');
      if (!root) return;
      root.replaceChildren();
      const details = Array.isArray(payload.details) ? payload.details : [];
      details.forEach((detail) => {
        const section = engineNode('section', 'engine-detail-section');
        const heading = engineNode('div', 'engine-detail-heading');
        const detailState = detail.status === 'ready' ? '已返回' : '缺失';
        heading.append(
          engineNode('strong', '', [detail.target, detail.section].filter(Boolean).join(' · ')),
          engineNode('span', `state-${detail.status || 'missing'}`, detailState)
        );
        section.append(heading);
        const findings = Array.isArray(detail.findings) ? detail.findings : [];
        if (findings.length) {
          findings.forEach((item) => section.append(renderEngineFinding(item)));
        } else {
          section.append(engineNode('p', 'engine-detail-empty', '本维度暂未返回可展示事实。'));
        }
        root.append(section);
      });
      const missing = Array.isArray(payload.missing_sections) ? payload.missing_sections : [];
      if (missing.length) {
        const note = engineNode('p', 'engine-missing-note');
        note.append(engineNode('strong', '', '待补证据：'));
        note.append(document.createTextNode(missing.join('、')));
        root.append(note);
      }
      if (!details.length) {
        root.append(engineNode('p', 'engine-detail-empty', '本次没有可展示的完整依据。'));
      }
    }

    function renderEngineResult(workspace, payload) {
      const judgment = workspace.querySelector('[data-engine-judgment]');
      if (judgment) {
        judgment.className = `engine-judgment state-${payload.status || 'partial'}`;
      }
      const verdict = workspace.querySelector('[data-engine-verdict]');
      const action = workspace.querySelector('[data-engine-action]');
      const risk = workspace.querySelector('[data-engine-risk]');
      const generated = workspace.querySelector('[data-engine-generated]');
      const live = workspace.querySelector('[data-engine-live-state]');
      if (verdict) verdict.textContent = payload.verdict || '本次证据不足，判断暂停。';
      if (action) action.textContent = payload.action || '稍后重新分析。';
      if (risk) risk.textContent = payload.primary_risk || '缺少足够证据。';
      if (generated) {
        const date = payload.generated_at ? new Date(payload.generated_at) : null;
        generated.textContent = date && !Number.isNaN(date.getTime())
          ? date.toLocaleString('zh-CN', {hour12: false})
          : '刚刚生成';
      }
      const findingsRoot = workspace.querySelector('[data-engine-findings]');
      if (findingsRoot) {
        findingsRoot.replaceChildren();
        const findings = Array.isArray(payload.findings) ? payload.findings.slice(0, 3) : [];
        if (findings.length) {
          findings.forEach((item) => findingsRoot.append(renderEngineFinding(item)));
        } else {
          findingsRoot.append(engineNode('div', 'engine-empty', '本次没有足够的关键事实。'));
        }
      }
      renderEngineDetails(workspace, payload);
      if (live) {
        live.textContent = payload.status === 'complete'
          ? '判断已更新'
          : '判断已降级，请查看缺口';
      }
    }

    async function runEngineWorkspace(workspace, refresh = false) {
      if (!workspace || workspace.dataset.engineAvailable !== 'true') return;
      const key = engineKey(workspace);
      if (!refresh && engineCache.has(key)) {
        renderEngineResult(workspace, engineCache.get(key));
        return;
      }
      setEngineLoading(workspace, true);
      try {
        const response = await fetch('/api/research/workspace', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          credentials: 'same-origin',
          body: JSON.stringify({
            module: workspace.dataset.engineWorkspace,
            context: engineContext(workspace),
            refresh: Boolean(refresh)
          })
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(payload.message || '研究服务暂时不可用。');
        engineCache.set(key, payload);
        renderEngineResult(workspace, payload);
      } catch (error) {
        renderEngineResult(workspace, {
          status: 'unavailable',
          verdict: '研究服务暂时不可用，当前没有可执行结论。',
          action: '稍后重新分析；当前不沿用旧结论。',
          primary_risk: error.message || '研究请求失败。',
          findings: [],
          details: [],
          missing_sections: []
        });
      } finally {
        setEngineLoading(workspace, false);
      }
    }

    function activateEngineWorkspace(key, updateHash = true) {
      const requestedPane = document.querySelector(
        `.workspace-pane[data-workspace="${key}"]`
      );
      const normalized = requestedPane ? key : 'market';
      document.querySelectorAll('.workspace-pane').forEach((pane) => {
        pane.classList.toggle('active', pane.dataset.workspace === normalized);
      });
      document.querySelectorAll('.nav-item[data-workspace]').forEach((item) => {
        item.classList.toggle('active', item.dataset.workspace === normalized);
      });
      if (updateHash) history.replaceState(null, '', `#${normalized}`);
      const workspace = document.querySelector(
        `.workspace-pane[data-workspace="${normalized}"] [data-engine-workspace]`
      );
      if (workspace && workspace.dataset.engineLoaded !== 'true') {
        workspace.dataset.engineLoaded = 'true';
        runEngineWorkspace(workspace, false);
      }
      window.scrollTo({top: 0, left: 0, behavior: 'auto'});
    }

    function bootstrapEngineWorkspaces() {
      document.querySelectorAll('.nav-item[data-workspace]').forEach((item) => {
        item.addEventListener('click', (event) => {
          event.preventDefault();
          activateEngineWorkspace(item.dataset.workspace || 'market');
        });
      });
      document.querySelectorAll('[data-engine-run]').forEach((button) => {
        button.addEventListener('click', () => {
          const workspace = button.closest('[data-engine-workspace]');
          runEngineWorkspace(workspace, true);
        });
      });
      window.addEventListener('hashchange', () => {
        activateEngineWorkspace((window.location.hash || '#market').replace(/^#/, ''), false);
      });
      const initialHash = window.__stockTsInitialHash || window.location.hash || '#market';
      const initial = initialHash.replace(/^#(?:module-)?/, '');
      activateEngineWorkspace(initial, false);
    }

    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', bootstrapEngineWorkspaces, {once: true});
    } else {
      bootstrapEngineWorkspaces();
    }
  </script>"""


def _service_status(status: str) -> tuple[str, str, bool]:
    if status == "configured":
        return "服务就绪", "ready", True
    if status == "requires_login":
        return "登录后可用", "blocked", False
    return "服务未配置", "missing", False
