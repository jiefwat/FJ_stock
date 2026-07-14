# ruff: noqa: E501
from __future__ import annotations

from html import escape

from .composition import MODULE_TO_WORKSPACE, WORKSPACE_MODULES, WORKSPACES
from .styles import CSS

PUBLIC_SITE_NAME = "Jiewat Kaka FJ"
PUBLIC_SITE_DOMAIN = "jiewat-kaka-fj.com"
PUBLIC_SITE_LOGO = "JK"
PUBLIC_SITE_TAGLINE = "A股投资研究终端"
WEB_DATA_PROVIDER = "tdx-snapshot"

WORKSPACE_PANEL_LABELS = {meta.key: meta.label for meta in WORKSPACES}


def render_sidebar(
    stock_code: str = "",
    holdings_path: str = "",
    *,
    current_username: str = "",
    current_role: str = "",
    auth_enabled: bool = False,
) -> str:
    nav = "".join(
        f'<a class="nav-item" href="#{meta.key}" data-workspace="{meta.key}">{meta.label}<span>{meta.badge}</span></a>'
        for meta in WORKSPACES
    )
    holdings_input = (
        f'<input type="hidden" name="holdings" value="{escape(holdings_path)}" />'
        if holdings_path
        else ""
    )
    account_html = render_account_card(
        current_username=current_username,
        current_role=current_role,
        auth_enabled=auth_enabled,
    )
    return f"""
    <aside class="sidebar">
      <div class="brand-mark"><div class="logo">{PUBLIC_SITE_LOGO}</div><div><div class="brand-title">{PUBLIC_SITE_NAME}</div><div class="brand-subtitle">{PUBLIC_SITE_DOMAIN} · {PUBLIC_SITE_TAGLINE}</div></div></div>
      {account_html}
      <form class="quick-stock-search" method="get" action="/#stock" aria-label="快速分析个股" data-remember-stock-form>
        <input name="code" value="{escape(stock_code)}" placeholder="代码 / 名称" autocomplete="off" data-stock-query />
        <input type="hidden" name="provider" value="{WEB_DATA_PROVIDER}" />
        {holdings_input}
        <button type="submit">分析个股</button>
      </form>
      <nav class="nav-group">{nav}</nav>
    </aside>"""


def render_account_card(
    *,
    current_username: str = "",
    current_role: str = "",
    auth_enabled: bool = False,
) -> str:
    if not auth_enabled:
        return ""
    if not current_username:
        return """
      <div class="sidebar-account-card">
        <span>账户</span>
        <strong>未登录</strong>
        <a class="ghost-button sidebar-account-link" href="/login">登录 / 注册</a>
      </div>"""
    return f"""
      <div class="sidebar-account-card">
        <span>当前账号</span>
        <strong>{escape(current_username)}</strong>
        <small>角色：{escape(current_role or 'member')}</small>
        <div class="sidebar-account-actions">
          <a class="ghost-button sidebar-account-link" href="#account">账户管理</a>
          <form method="post" action="/logout">
            <button class="ghost-button sidebar-account-link" type="submit">退出登录</button>
          </form>
        </div>
      </div>"""


def render_app_toolbar(stock_code: str, provider_name: str, holdings_path: str) -> str:
    return f"""
    <form class="app-toolbar" method="get" action="/#workspace-stock" aria-label="分析参数">
      <label>代码 / 名称<input name="code" value="{escape(stock_code)}" placeholder="输入股票代码或名称" /></label>
      <input type="hidden" name="provider" value="{WEB_DATA_PROVIDER}" />
      <input type="hidden" name="holdings" value="{escape(holdings_path)}" />
      <div class="source-badge" aria-label="当前数据源">TDX MCP</div>
      <button type="submit">切换</button>
    </form>"""


def render_topbar(title_note: str) -> str:
    return title_note


def render_workspace_shell(workspace_sections: dict[str, str]) -> str:
    panes = []
    for meta in WORKSPACES:
        active = " active" if meta.key == "home" else ""
        modules = WORKSPACE_MODULES[meta.key]
        tabs = ""
        if len(modules) > 1:
            tabs = (
                '<div class="workspace-panel-tabs">'
                + "".join(
                    f'<button class="workspace-panel-tab{" active" if index == 0 else ""}" '
                    f'type="button" data-panel-workspace="{meta.key}" data-panel-target="{module}">'
                    f"{escape(WORKSPACE_PANEL_LABELS.get(module, module))}</button>"
                    for index, module in enumerate(modules)
                )
                + "</div>"
            )
        panes.append(
            f'''<section class="workspace-pane{active}" id="{meta.key}" data-workspace="{meta.key}" data-legacy-id="workspace-{meta.key}">
{tabs}
<div class="workspace-shell">{workspace_sections[meta.key]}</div>
</section>'''
        )
    return "".join(panes)


def app_script() -> str:
    labels = {meta.key: meta.label for meta in WORKSPACES}
    return f"""
  <script>
    const moduleToWorkspace = {MODULE_TO_WORKSPACE!r};
    const workspaceLabels = {labels!r};
    const workspaceModules = {WORKSPACE_MODULES!r};
    const workspaceKeys = new Set(Object.keys(workspaceLabels));
      const legacyWorkspaces = {{
      'home': 'market',
      'sector': 'opportunity',
      'sectors': 'opportunity',
      'sentiment': 'opportunity',
      'limit-up': 'opportunity',
      'limit-down': 'opportunity',
      'screener': 'opportunity',
      'smart-select': 'opportunity',
      'opportunities': 'opportunity',
      'candidates': 'opportunity',
      'report': 'market',
      'daily': 'market',
      'assist': 'stock',
      'chart': 'stock',
      'stock-chart': 'stock',
      'watchlist': 'stock',
      'status': 'market',
      'notify': 'market',
      'settings': 'account',
      'account': 'account',
      'data-quality': 'data-center',
      'data-center': 'data-center'
    }};

    function activatePanel(workspace, moduleKey) {{
      const pane = document.querySelector(`.workspace-pane[data-workspace="${{workspace}}"]`);
      if (!pane) return;
      const modules = workspaceModules[workspace] || [];
      const target = modules.includes(moduleKey) ? moduleKey : modules[0];
      pane.querySelectorAll('.module').forEach((section) => {{
        const id = (section.id || '').replace('module-', '');
        section.classList.toggle('workspace-module-hidden', id !== target);
      }});
      pane.querySelectorAll('.workspace-panel-tab').forEach((button) => {{
        button.classList.toggle('active', button.dataset.panelTarget === target);
      }});
      pane.dataset.activePanel = target;
    }}

    function activateWorkspace(workspace, updateHash = true) {{
      const routed = legacyWorkspaces[workspace] || workspace;
      const normalized = workspaceLabels[routed] ? routed : 'home';
      document.querySelectorAll('.workspace-pane').forEach((section) => {{
        section.classList.toggle('active', section.dataset.workspace === normalized);
      }});
      document.querySelectorAll('.nav-item[data-workspace]').forEach((button) => {{
        button.classList.toggle('active', button.dataset.workspace === normalized);
      }});
      const label = document.getElementById('current-module-label');
      if (label) {{
        label.textContent = workspaceLabels[normalized] || normalized;
      }}
      const pane = document.querySelector(`.workspace-pane[data-workspace="${{normalized}}"]`);
      if (pane) {{
        activatePanel(normalized, pane.dataset.activePanel || (workspaceModules[normalized] || [])[0]);
      }}
      if (window.StockTsKlineScreens && typeof window.StockTsKlineScreens.refresh === 'function') {{
        window.requestAnimationFrame(() => window.StockTsKlineScreens.refresh());
      }}
      if (updateHash) {{
        history.replaceState(null, '', `#${{normalized}}`);
      }}
      keepTop();
    }}

    function openTarget(target) {{
      const normalized = (target || 'home').replace(/^#/, '');
      if (normalized.startsWith('workspace-')) {{
        activateWorkspace(legacyWorkspaces[normalized.replace('workspace-', '')] || normalized.replace('workspace-', ''));
        return;
      }}
      if (workspaceLabels[normalized]) {{
        activateWorkspace(normalized);
        return;
      }}
      let moduleKey = normalized.replace(/^module-/, '');
      const legacyTarget = legacyWorkspaces[moduleKey];
      if (legacyTarget && workspaceKeys.has(legacyTarget)) {{
        activateWorkspace(legacyTarget);
        return;
      }}
      moduleKey = legacyTarget || moduleKey;
      const workspace = moduleToWorkspace[moduleKey] || 'home';
      activateWorkspace(workspace, false);
      activatePanel(workspace, moduleKey);
      history.replaceState(null, '', workspaceKeys.has(moduleKey) ? `#${{moduleKey}}` : `#module-${{moduleKey}}`);
    }}

    function keepTop() {{
      window.scrollTo({{ top: 0, left: 0, behavior: 'auto' }});
    }}

    function showToast(message) {{
      let toast = document.querySelector('[data-toast]');
      if (!toast) {{
        toast = document.createElement('div');
        toast.setAttribute('data-toast', '');
        toast.className = 'toast';
        document.body.appendChild(toast);
      }}
      toast.textContent = message || '已处理';
      toast.hidden = false;
      toast.classList.add('visible');
      window.clearTimeout(showToast.timer);
      showToast.timer = window.setTimeout(() => {{
        toast.classList.remove('visible');
        toast.hidden = true;
      }}, 2200);
    }}

    function currentReportText() {{
      const active = document.querySelector('.workspace-pane.active');
      return (active ? active.innerText : document.body.innerText).replace(/\\n{{3,}}/g, '\\n\\n').trim();
    }}

    function currentActionPlanText() {{
      const home = document.querySelector('#module-home');
      const freshness = document.querySelector('.freshness-bar');
      const pieces = [];
      if (home) pieces.push(home.innerText);
      if (freshness) pieces.push(`数据状态\\n${{freshness.innerText}}`);
      return pieces.join('\\n\\n').replace(/复制今日行动/g, '').replace(/\\n{{3,}}/g, '\\n\\n').trim();
    }}

    async function copyText(text) {{
      if (navigator.clipboard && window.isSecureContext) {{
        try {{
          await navigator.clipboard.writeText(text);
          return;
        }} catch (_error) {{
          // Some embedded browsers deny Clipboard API writes; fall back to a selection copy.
        }}
      }}
      const input = document.createElement('textarea');
      input.value = text;
      input.setAttribute('readonly', '');
      input.style.position = 'fixed';
      input.style.left = '-9999px';
      input.style.top = '0';
      document.body.appendChild(input);
      input.focus();
      input.select();
      const copied = document.execCommand('copy');
      document.body.removeChild(input);
      if (!copied) {{
        throw new Error('copy command rejected');
      }}
    }}

    function revealCopyBuffer(text) {{
      let buffer = document.querySelector('[data-copy-buffer]');
      if (!buffer) {{
        buffer = document.createElement('textarea');
        buffer.setAttribute('data-copy-buffer', '');
        buffer.className = 'copy-buffer';
        document.body.appendChild(buffer);
      }}
      buffer.value = text;
      buffer.hidden = false;
      buffer.focus();
      buffer.select();
    }}

    function iwencaiNode(tag, className, value) {{
      const node = document.createElement(tag);
      if (className) node.className = className;
      if (value !== undefined && value !== null) node.textContent = String(value);
      return node;
    }}

    function renderIwencaiResult(consoleElement, payload) {{
      const researchResult = consoleElement.querySelector('[data-iwencai-result]');
      researchResult.replaceChildren();
      researchResult.hidden = false;

      const heading = iwencaiNode('div', 'iwencai-result-heading');
      const skill = payload.skill || {{}};
      heading.append(
        iwencaiNode('span', '', skill.label || '问财研究'),
        iwencaiNode('strong', '', payload.summary || '查询完成')
      );
      researchResult.append(heading);

      const facts = Array.isArray(payload.facts) ? payload.facts : [];
      if (facts.length) {{
        const grid = iwencaiNode('div', 'iwencai-fact-grid');
        facts.forEach((row) => {{
          const card = iwencaiNode('article', 'iwencai-fact-card');
          Object.entries(row || {{}}).forEach(([label, value]) => {{
            const item = iwencaiNode('div', '');
            item.append(iwencaiNode('span', '', label), iwencaiNode('strong', '', value));
            card.append(item);
          }});
          grid.append(card);
        }});
        researchResult.append(grid);
      }}

      if (payload.relationship) {{
        researchResult.append(iwencaiNode('p', 'iwencai-relationship', payload.relationship));
      }}
      const unknowns = Array.isArray(payload.unknowns) ? payload.unknowns : [];
      if (unknowns.length) {{
        const unknownBlock = iwencaiNode('div', 'iwencai-unknowns');
        unknownBlock.append(iwencaiNode('span', '', '未知与限制'));
        const list = iwencaiNode('ul', '');
        unknowns.forEach((item) => list.append(iwencaiNode('li', '', item)));
        unknownBlock.append(list);
        researchResult.append(unknownBlock);
      }}
      const source = payload.source || {{}};
      const audit = [source.name, source.queried_at, source.trace ? 'trace ' + source.trace : '']
        .filter(Boolean).join(' · ');
      if (audit) researchResult.append(iwencaiNode('small', 'iwencai-audit', audit));
      if (payload.boundary) {{
        researchResult.append(iwencaiNode('small', 'iwencai-boundary', payload.boundary));
      }}
    }}

    function bootstrapIwencaiResearch() {{
      document.querySelectorAll('[data-iwencai-research]').forEach((consoleElement) => {{
        const form = consoleElement.querySelector('[data-iwencai-form]');
        const input = consoleElement.querySelector('[data-iwencai-input]');
        const submit = consoleElement.querySelector('[data-iwencai-submit]');
        const state = consoleElement.querySelector('[data-iwencai-state]');
        consoleElement.querySelectorAll('[data-iwencai-question]').forEach((chip) => {{
          chip.addEventListener('click', () => {{
            input.value = chip.dataset.iwencaiQuestion || '';
            input.focus();
            form.requestSubmit();
          }});
        }});
        form.addEventListener('submit', async (event) => {{
          event.preventDefault();
          const question = input.value.trim();
          if (!question) {{
            state.textContent = '请输入一个具体研究问题。';
            input.focus();
            return;
          }}
          submit.disabled = true;
          submit.textContent = '查询中';
          state.textContent = '正在调用问财官方数据技能…';
          try {{
            const response = await fetch('/api/iwencai/research', {{
              method: 'POST',
              headers: {{'Content-Type': 'application/json'}},
              credentials: 'same-origin',
              body: JSON.stringify({{
                code: consoleElement.dataset.stockCode || '',
                name: consoleElement.dataset.stockName || '',
                local_as_of: consoleElement.dataset.localAsOf || '',
                question: question
              }})
            }});
            const payload = await response.json().catch(() => ({{}}));
            if (!response.ok) throw new Error(payload.message || '外部研究暂不可用');
            renderIwencaiResult(consoleElement, payload);
            state.textContent = '查询完成 · 外部证据不会自动改变 StockTs 结论';
          }} catch (error) {{
            const researchResult = consoleElement.querySelector('[data-iwencai-result]');
            researchResult.replaceChildren(
              iwencaiNode('strong', 'iwencai-error', error.message || '外部研究暂不可用')
            );
            researchResult.hidden = false;
            state.textContent = 'StockTs 本地分析仍可正常使用。';
          }} finally {{
            submit.disabled = false;
            submit.textContent = '查询问财';
          }}
        }});
      }});
    }}

    function bootstrapShell() {{
      bootstrapIwencaiResearch();
      document.querySelectorAll('.nav-item[data-workspace]').forEach((button) => {{
        button.addEventListener('click', (event) => {{
          event.preventDefault();
          event.stopPropagation();
          activateWorkspace(button.dataset.workspace);
        }});
      }});
      document.querySelectorAll('.workspace-panel-tab').forEach((button) => {{
        button.addEventListener('click', (event) => {{
          event.preventDefault();
          event.stopPropagation();
          const workspace = button.dataset.panelWorkspace;
          const target = button.dataset.panelTarget;
          activateWorkspace(workspace, false);
          activatePanel(workspace, target);
          history.replaceState(null, '', `#module-${{target}}`);
        }});
      }});
      document.querySelectorAll('[data-jump]').forEach((button) => {{
        button.addEventListener('click', (event) => {{
          event.preventDefault();
          event.stopPropagation();
          openTarget(`module-${{button.dataset.jump}}`);
        }});
      }});
      document.querySelectorAll('[data-scroll]').forEach((button) => {{
        button.addEventListener('click', (event) => {{
          event.preventDefault();
          event.stopPropagation();
          const target = document.getElementById(button.dataset.scroll);
          history.replaceState(null, '', `#${{button.dataset.scroll}}`);
          if (target) {{
            const placeTarget = () => {{
              const top = target.getBoundingClientRect().top + window.scrollY - 24;
              window.scrollTo({{ top: Math.max(0, top), left: 0, behavior: 'auto' }});
            }};
            placeTarget();
            setTimeout(placeTarget, 0);
            setTimeout(placeTarget, 80);
            setTimeout(placeTarget, 360);
          }}
        }});
      }});
      const actionMessages = {{
        'add-holding': '已定位到持仓表单',
        'filter-candidates': '筛选条件已提交',
        'save-stock-plan': '个股计划已在当前页生成',
        'add-watch-form': '自选研究已记录在当前页',
        'send-dry-run': 'dry-run 预览已生成'
      }};
      document.querySelectorAll('[data-action]').forEach((element) => {{
        const handler = (event) => {{
          if (element.disabled) return;
          if (element.tagName === 'FORM') {{
            event.preventDefault();
            event.stopPropagation();
          }}
          const message = actionMessages[element.dataset.action] || '已处理';
          showToast(message);
        }};
        if (element.tagName === 'FORM') {{
          element.addEventListener('submit', handler);
        }} else {{
          element.addEventListener('click', handler);
        }}
      }});
      document.querySelectorAll('[data-copy-report]').forEach((button) => {{
        button.addEventListener('click', async (event) => {{
          event.preventDefault();
          event.stopPropagation();
          try {{
            await copyText(currentReportText());
            showToast('已复制当前模块内容');
          }} catch (_error) {{
            revealCopyBuffer(currentReportText());
            showToast('内容已选中，请按 Ctrl/Cmd+C');
          }}
        }});
      }});
      document.querySelectorAll('[data-copy-action-plan]').forEach((button) => {{
        button.addEventListener('click', async (event) => {{
          event.preventDefault();
          event.stopPropagation();
          const text = currentActionPlanText();
          try {{
            await copyText(text);
            showToast('已复制今日行动');
          }} catch (_error) {{
            revealCopyBuffer(text);
            showToast('行动内容已选中，请按 Ctrl/Cmd+C');
          }}
        }});
      }});
      document.querySelectorAll('[data-remember-stock-form]').forEach((form) => {{
        const input = form.querySelector('[data-stock-query]');
        const key = 'stockTsLastStockQuery';
        try {{
          const remembered = localStorage.getItem(key);
          if (input && !input.value && remembered) input.value = remembered;
        }} catch (_error) {{
          // 快速搜索不依赖浏览器本地存储。
        }}
        form.addEventListener('submit', () => {{
          try {{
            if (input && input.value.trim()) localStorage.setItem(key, input.value.trim());
          }} catch (_error) {{
            // 搜索提交不依赖浏览器本地存储。
          }}
        }});
      }});
      document.querySelectorAll('.workspace-pane').forEach((pane) => {{
        const workspace = pane.dataset.workspace;
        activatePanel(workspace, (workspaceModules[workspace] || [])[0]);
      }});
      window.addEventListener('hashchange', () => {{
        openTarget(window.location.hash || '#home');
        setTimeout(keepTop, 0);
        setTimeout(keepTop, 120);
      }});
      const initial = window.__stockTsInitialHash || window.location.hash || '#home';
      openTarget(initial);
      requestAnimationFrame(keepTop);
      setTimeout(keepTop, 80);
      setTimeout(keepTop, 300);
      window.addEventListener('load', () => {{
        keepTop();
        setTimeout(keepTop, 250);
      }}, {{ once: true }});
      window.addEventListener('pageshow', () => setTimeout(keepTop, 0), {{ once: true }});
    }}

    if (document.readyState === 'loading') {{
      document.addEventListener('DOMContentLoaded', bootstrapShell, {{ once: true }});
    }} else {{
      bootstrapShell();
    }}
  </script>"""


def render_document(body: str) -> str:
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{PUBLIC_SITE_NAME} 研究分析平台</title>
  <script>
    window.__stockTsInitialHash = window.location.hash;
    if (window.location.hash) {{
      history.replaceState(null, '', window.location.pathname + window.location.search);
    }}
  </script>
  <style>{CSS}</style>
</head>
<body>{body}<div class="toast" data-toast hidden></div></body>
</html>"""
