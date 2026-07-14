from __future__ import annotations

import json
from html import escape

MODULE_META = {
    "market": ("每日大盘", "市场判断", "判断指数、宏观、主线与风险是否同向"),
    "portfolio": ("我的持仓", "组合诊断", "逐只核对事件、预期与价格风险"),
    "stock": ("个股分析", "公司研究", "核对经营、财务、预期与事件变化"),
    "opportunity": ("热点机会", "机会扫描", "先找方向，再筛候选并排除风险"),
}

CORE_MODULES = ("market", "portfolio", "stock", "opportunity")


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
          <span class="engine-delivery" data-engine-delivery>等待数据</span>
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
          <article class="engine-risk" data-engine-target="risk" tabindex="-1">
            <span>最大风险</span>
            <strong data-engine-risk>研究完成前，不沿用旧结论。</strong>
          </article>
        </div>
      </section>
      <nav class="engine-action-rail" aria-label="结果直达">
        <button type="button" data-engine-jump="risk">先看风险</button>
        <button type="button" data-engine-jump="findings">看三条发现</button>
        <button type="button" data-engine-jump="evidence">展开完整依据</button>
      </nav>
      <section class="engine-findings-block" aria-label="关键发现"
        data-engine-target="findings" tabindex="-1">
        <div class="engine-section-heading">
          <h3>关键发现</h3>
          <div class="engine-section-meta">
            <span class="engine-coverage" data-engine-coverage>已确认维度 0/4</span>
            <small>最多三条</small>
          </div>
        </div>
        <div class="engine-findings" data-engine-findings>
          <div class="engine-empty">生成后显示最重要的三条事实。</div>
        </div>
      </section>
      <section class="engine-module-items" data-engine-module-items hidden>
        <div class="engine-section-heading">
          <h3 data-engine-module-items-title>完整清单</h3>
          <span class="engine-module-items-count" data-engine-module-items-count>0 项</span>
        </div>
        <div class="engine-module-item-grid" data-engine-module-item-grid></div>
      </section>
      <div class="engine-actions">
        <details class="engine-disclosure" data-engine-disclosure
          data-engine-target="evidence" tabindex="-1">
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


def render_engine_mobile_dock() -> str:
    buttons = []
    for index, module in enumerate(CORE_MODULES, start=1):
        label = MODULE_META[module][0]
        buttons.append(
            f'''<button type="button" data-engine-mobile-nav data-workspace="{module}"
              data-engine-nav-label="{label}"
              data-engine-nav-state="idle" aria-label="{label}，未分析">
              <span class="engine-mobile-dock-index" aria-hidden="true">0{index}</span>
              <strong>{label}</strong>
              <i class="engine-nav-state-dot" aria-hidden="true"></i>
              <span class="sr-only" data-engine-nav-status>未分析</span>
            </button>'''
        )
    return f'''
    <nav class="engine-mobile-dock" data-engine-mobile-dock aria-label="核心研究模块">
      {"".join(buttons)}
    </nav>'''


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
    const engineKeyboardModules = ['market', 'portfolio', 'stock', 'opportunity'];
    const engineStateLabels = {
      idle: '未分析',
      loading: '分析中',
      complete: '已完成',
      partial: '待补证据',
      unavailable: '暂不可用'
    };

    function normalizeEngineNavigationState(status) {
      if (status === 'complete') return 'complete';
      if (status === 'partial' || status === 'empty') return 'partial';
      if (status === 'unavailable') return 'unavailable';
      return 'partial';
    }

    function setEngineNavigationState(module, state) {
      const label = engineStateLabels[state] || engineStateLabels.idle;
      document.querySelectorAll(
        `[data-workspace="${module}"][data-engine-nav-state]`
      ).forEach((item) => {
        item.dataset.engineNavState = state;
        const status = item.querySelector('[data-engine-nav-status]');
        if (status) status.textContent = label;
        item.setAttribute('aria-label', `${item.dataset.engineNavLabel || module}，${label}`);
      });
    }

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
      if (live && loading) {
        live.textContent = workspace.dataset.engineWorkspace === 'portfolio'
          ? '正在逐只核对，可能需要几秒'
          : '正在生成判断…';
      }
      if (loading) setEngineNavigationState(workspace.dataset.engineWorkspace, 'loading');
    }

    function renderEngineFinding(item, index = 0) {
      const card = engineNode('article', 'engine-finding-card');
      const meta = engineNode('div', 'engine-finding-meta');
      meta.append(
        engineNode('span', 'engine-finding-rank', String(index + 1).padStart(2, '0')),
        engineNode('span', 'engine-evidence-tag', item.target || '研究证据')
      );
      card.append(meta, engineNode('strong', '', item.title || '关键变化'));
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
        const detailStates = {
          ready: '已确认',
          insufficient: '证据不足',
          failed: '获取失败',
          missing: '暂无数据'
        };
        const detailState = detailStates[detail.status] || '暂无数据';
        heading.append(
          engineNode('strong', '', [detail.target, detail.section].filter(Boolean).join(' · ')),
          engineNode('span', `state-${detail.status || 'missing'}`, detailState)
        );
        section.append(heading);
        const findings = Array.isArray(detail.findings) ? detail.findings : [];
        if (findings.length) {
          findings.forEach((item, index) => section.append(renderEngineFinding(item, index)));
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

    function renderEngineModuleItems(workspace, payload) {
      const section = workspace.querySelector('[data-engine-module-items]');
      const root = workspace.querySelector('[data-engine-module-item-grid]');
      const heading = workspace.querySelector('[data-engine-module-items-title]');
      const count = workspace.querySelector('[data-engine-module-items-count]');
      if (!section || !root || !heading || !count) return;
      const items = Array.isArray(payload.module_items) ? payload.module_items : [];
      const titles = {
        market: '指数趋势',
        portfolio: '全部持仓',
        stock: '八维覆盖',
        opportunity: '今日机会'
      };
      heading.textContent = titles[payload.module] || '完整清单';
      count.textContent = payload.module === 'portfolio' && payload.subject_count
        ? `已分析 ${items.length}/${payload.subject_count}`
        : `${items.length} 项`;
      root.replaceChildren();
      items.forEach((item) => {
        const card = engineNode('article', `engine-module-item state-${item.status || 'ready'}`);
        const meta = engineNode('div', 'engine-module-item-meta');
        meta.append(
          engineNode('span', '', item.code || item.label || '研究项'),
          engineNode('i', '', item.status === 'ready' ? '已确认' : '待补')
        );
        const title = engineNode('strong', '', item.name || item.label || '研究项');
        card.append(meta, title, engineNode('p', '', item.summary || '证据待补。'));
        if (item.risk) card.append(engineNode('small', '', item.risk));
        if (payload.module === 'opportunity' && item.code) {
          const link = engineNode('a', 'engine-module-item-link', '进入个股分析');
          link.href = `/?code=${encodeURIComponent(item.code)}#stock`;
          card.append(link);
        }
        root.append(card);
      });
      section.hidden = items.length === 0;
    }

    function renderEngineResult(workspace, payload) {
      const navigationState = normalizeEngineNavigationState(payload.status);
      workspace.dataset.engineResultStatus = navigationState;
      setEngineNavigationState(workspace.dataset.engineWorkspace, navigationState);
      const judgment = workspace.querySelector('[data-engine-judgment]');
      if (judgment) {
        judgment.className = `engine-judgment state-${payload.status || 'partial'}`;
      }
      const verdict = workspace.querySelector('[data-engine-verdict]');
      const action = workspace.querySelector('[data-engine-action]');
      const risk = workspace.querySelector('[data-engine-risk]');
      const generated = workspace.querySelector('[data-engine-generated]');
      const live = workspace.querySelector('[data-engine-live-state]');
      const details = Array.isArray(payload.details) ? payload.details : [];
      const coverage = workspace.querySelector('[data-engine-coverage]');
      const delivery = workspace.querySelector('[data-engine-delivery]');
      if (verdict) verdict.textContent = payload.verdict || '本次证据不足，判断暂停。';
      if (action) action.textContent = payload.action || '稍后重新分析。';
      if (risk) risk.textContent = payload.primary_risk || '缺少足够证据。';
      if (generated) {
        const date = payload.generated_at ? new Date(payload.generated_at) : null;
        generated.textContent = date && !Number.isNaN(date.getTime())
          ? date.toLocaleString('zh-CN', {hour12: false})
          : '刚刚生成';
      }
      if (coverage) {
        const readyDetails = details.filter((detail) => detail.status === 'ready').length;
        const ready = payload.coverage?.ready ?? readyDetails;
        const total = payload.coverage?.total ?? (details.length || 4);
        coverage.textContent = `已确认维度 ${ready}/${total}`;
        coverage.classList.toggle('is-complete', ready > 0 && ready === total);
      }
      if (delivery) {
        const deliveryLabels = {
          live: '实时结果',
          snapshot: '今日快照',
          stale_snapshot: '历史快照'
        };
        delivery.textContent = deliveryLabels[payload.delivery] || '实时结果';
        delivery.classList.toggle('is-stale', Boolean(payload.stale));
      }
      const findingsRoot = workspace.querySelector('[data-engine-findings]');
      if (findingsRoot) {
        findingsRoot.replaceChildren();
        const findings = Array.isArray(payload.findings) ? payload.findings.slice(0, 3) : [];
        if (findings.length) {
          findings.forEach((item, index) => findingsRoot.append(renderEngineFinding(item, index)));
        } else {
          findingsRoot.append(engineNode('div', 'engine-empty', '本次没有足够的关键事实。'));
        }
      }
      renderEngineDetails(workspace, payload);
      renderEngineModuleItems(workspace, payload);
      if (live) {
        live.textContent = navigationState === 'complete'
          ? '判断已更新'
          : navigationState === 'unavailable'
            ? '研究暂不可用'
            : '判断已降级，请查看缺口';
      }
    }

    async function runEngineWorkspace(workspace, refresh = false) {
      if (!workspace) return;
      if (workspace.dataset.engineAvailable !== 'true') {
        setEngineNavigationState(workspace.dataset.engineWorkspace, 'unavailable');
        return;
      }
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

    function engineJumpTo(workspace, targetName) {
      if (!workspace) return;
      const target = workspace.querySelector(`[data-engine-target="${targetName}"]`);
      if (!target) return;
      let focusTarget = target;
      if (targetName === 'evidence' && target.tagName === 'DETAILS') {
        target.open = true;
        focusTarget = target.querySelector('summary') || target;
      }
      const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      focusTarget.scrollIntoView({behavior: reducedMotion ? 'auto' : 'smooth', block: 'start'});
      focusTarget.focus({preventScroll: true});
    }

    function closeActiveEngineDisclosure() {
      const disclosure = document.querySelector(
        '.workspace-pane.active details[data-engine-disclosure][open]'
      );
      if (!disclosure) return false;
      disclosure.open = false;
      const summary = disclosure.querySelector('summary');
      if (summary) summary.focus({preventScroll: true});
      return true;
    }

    function activateEngineWorkspace(key, updateHash = true) {
      const requestedPane = document.querySelector(
        `.workspace-pane[data-workspace="${key}"]`
      );
      const normalized = requestedPane ? key : 'market';
      document.querySelectorAll('.workspace-pane').forEach((pane) => {
        pane.classList.toggle('active', pane.dataset.workspace === normalized);
      });
      document.querySelectorAll(
        '.nav-item[data-workspace], [data-engine-mobile-nav][data-workspace]'
      ).forEach((item) => {
        const active = item.dataset.workspace === normalized;
        item.classList.toggle('active', active);
        if (active) item.setAttribute('aria-current', 'page');
        else item.removeAttribute('aria-current');
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
      document.querySelectorAll(
        '.nav-item[data-workspace], [data-engine-mobile-nav][data-workspace]'
      ).forEach((item) => {
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
      document.querySelectorAll('[data-engine-jump]').forEach((button) => {
        button.addEventListener('click', () => {
          const workspace = button.closest('[data-engine-workspace]');
          engineJumpTo(workspace, button.dataset.engineJump || 'risk');
        });
      });
      document.addEventListener('keydown', (event) => {
        const target = event.target;
        if (target && (
          ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName) || target.isContentEditable
        )) return;
        if (event.metaKey || event.ctrlKey || event.altKey) return;
        if (event.key === 'Escape') {
          if (closeActiveEngineDisclosure()) event.preventDefault();
          return;
        }
        const numericIndex = Number(event.key) - 1;
        if (Number.isInteger(numericIndex) && engineKeyboardModules[numericIndex]) {
          event.preventDefault();
          activateEngineWorkspace(engineKeyboardModules[numericIndex]);
          return;
        }
        if (event.key.toLowerCase() === 'r') {
          const active = document.querySelector(
            '.workspace-pane.active [data-engine-workspace]'
          );
          if (active && engineKeyboardModules.includes(active.dataset.engineWorkspace)) {
            event.preventDefault();
            runEngineWorkspace(active, true);
          }
        }
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
