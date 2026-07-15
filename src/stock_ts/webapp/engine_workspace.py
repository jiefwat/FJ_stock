from __future__ import annotations

import json
from html import escape

MODULE_META = {
    "market": ("每日大盘", "市场判断"),
    "portfolio": ("我的持仓", "组合诊断"),
    "stock": ("个股分析", "公司研究"),
    "opportunity": ("热点机会", "机会扫描"),
}

CORE_MODULES = ("market", "portfolio", "stock", "opportunity")


def render_engine_workspace(
    module: str,
    *,
    status: str,
    context: dict[str, object] | None = None,
    supplemental_html: str = "",
) -> str:
    if module not in MODULE_META:
        raise ValueError("不支持的研究模块。")
    title, label = MODULE_META[module]
    status_label, status_class, available = _service_status(status)
    context_json = json.dumps(
        context or {},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    disabled = "" if available else " disabled"
    stock_switcher = _render_stock_switcher(context or {}) if module == "stock" else ""
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
      <p class="engine-fallback-reason" data-engine-fallback-reason hidden></p>
      {stock_switcher}
      <section class="engine-judgment state-idle" data-engine-judgment>
        <div class="engine-signal-band" aria-hidden="true"><i></i></div>
        <div class="engine-verdict" data-engine-verdict-block>
          <strong class="engine-decision-label state-idle" data-engine-decision-label>
            待确认</strong>
          <span>当前判断</span>
          <h3 data-engine-verdict>等待生成判断</h3>
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
      <section class="engine-sections" data-engine-sections aria-label="主题与分化" hidden>
        <div class="engine-section-grid" data-engine-section-grid></div>
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
      {supplemental_html}
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


def _render_stock_switcher(context: dict[str, object]) -> str:
    query = str(context.get("code") or context.get("name") or "").strip()
    return f"""
      <section class="engine-stock-switcher" data-engine-stock-switcher>
        <div>
          <span>切换研究对象</span>
          <strong>输入代码或名称，直接生成整股结论</strong>
        </div>
        <form method="get" action="/#stock">
          <input name="code" value="{escape(query, quote=True)}"
            placeholder="例如：600519 / 贵州茅台" autocomplete="off" required />
          <button type="submit">分析这只股票</button>
        </form>
        <a href="#opportunity">进入全市场筛选</a>
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
        <div><span>失败处理</span><strong>自动切换本地证据</strong></div>
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
      if (payload.module === 'opportunity') {
        root.replaceChildren();
        section.hidden = true;
        return;
      }
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
        const title = engineNode(
          'strong',
          '',
          payload.module === 'stock'
            ? item.label || '研究维度'
            : item.name || item.label || '研究项'
        );
        card.append(meta, title, engineNode('p', '', item.summary || '证据待补。'));
        if (item.risk) card.append(engineNode('small', '', item.risk));
        if ((payload.module === 'opportunity' || payload.module === 'portfolio') && item.code) {
          const link = engineNode(
            'a',
            'engine-module-item-link',
            payload.module === 'portfolio' ? '查看完整个股结论' : '进入个股分析'
          );
          link.href = `/?code=${encodeURIComponent(item.code)}#stock`;
          card.append(link);
        }
        root.append(card);
      });
      section.hidden = items.length === 0;
    }

    function engineItemState(item) {
      return item.status === 'ready' ? '已确认' : '待确认';
    }

    function engineSectionItems(section) {
      if (!section || !Array.isArray(section.items)) return [];
      return section.items.filter((item) => item && typeof item === 'object');
    }

    function engineDecisionTone(label) {
      const value = String(label || '').trim();
      if (['偏弱', '基本面承压', '先处理风险'].includes(value)) return 'negative';
      if (['修复中', '等待确认', '主线待确认', '主题待补'].includes(value)) {
        return 'caution';
      }
      if (['偏强', '有主线', '可继续跟踪'].includes(value)) return 'positive';
      return 'neutral';
    }

    function engineFactValue(item, terms) {
      const facts = Array.isArray(item.facts) ? item.facts : [];
      const fact = facts.find((candidate) => terms.some(
        (term) => String(candidate.label || '').includes(term)
      ));
      return fact ? String(fact.value || '') : '';
    }

    function engineNumericValue(value) {
      const match = String(value || '').replace(/,/g, '').match(/-?\d+(?:\.\d+)?/);
      return match ? Number(match[0]) : null;
    }

    function renderEngineSectionHeading(section) {
      const heading = engineNode('header', 'engine-research-section-heading');
      heading.append(
        engineNode('h3', '', section.title || '重点结论'),
        engineNode('p', '', section.conclusion || '证据待确认。')
      );
      return heading;
    }

    function renderEngineThemeSection(section, article) {
      article.classList.add('is-theme');
      const strip = engineNode('div', 'engine-theme-strip');
      strip.setAttribute('tabindex', '0');
      strip.setAttribute('role', 'region');
      strip.setAttribute('aria-label', '主题横向列表');
      const items = engineSectionItems(section);
      items.forEach((item) => {
        const card = engineNode('article', `engine-theme-card state-${item.status || 'ready'}`);
        const meta = engineNode('div', 'engine-theme-card-meta');
        meta.append(
          engineNode('span', '', item.label || '主题'),
          engineNode('i', '', engineItemState(item))
        );
        card.append(
          meta,
          engineNode('strong', '', item.name || '主题待确认'),
          engineNode('p', '', item.summary || '主题证据待确认。')
        );
        strip.append(card);
      });
      if (!items.length) strip.append(engineNode('div', 'engine-section-empty', '主题待确认。'));
      article.append(strip);
    }

    function engineBreadthClass(name) {
      if (name.includes('涨停')) return 'is-limit-up';
      if (name.includes('跌停')) return 'is-limit-down';
      if (name.includes('上涨')) return 'is-rise';
      if (name.includes('下跌')) return 'is-fall';
      return 'is-flat';
    }

    function renderEngineBreadthSection(section, article) {
      const items = engineSectionItems(section);
      if (!items.length) {
        article.append(engineNode('div', 'engine-section-empty', '市场分布待补。'));
        return;
      }
      const returnedMetrics = items.map((item) => ({
        item,
        name: String(item.name || item.label || '分布待确认'),
        value: engineNumericValue(
          item.summary || engineFactValue(
            item,
            ['上涨家数', '下跌家数', '平盘家数', '涨停家数', '跌停家数']
          )
        )
      }));
      const coreBreadthNames = ['上涨家数', '下跌家数', '平盘家数'];
      const breadthNames = [...coreBreadthNames, '涨停家数', '跌停家数'];
      const metrics = breadthNames.map((name) => (
        returnedMetrics.find((metric) => metric.name.includes(name)) || {
          item: {status: 'missing'},
          name,
          value: null
        }
      ));
      const coreBreadthComplete = coreBreadthNames.every((name) => {
        const metric = metrics.find((candidate) => candidate.name.includes(name));
        return metric && metric.value !== null;
      });
      const marketTotal = coreBreadthComplete ? metrics
          .filter((metric) => coreBreadthNames.some(
            (name) => metric.name.includes(name)
          ))
          .reduce((total, metric) => total + metric.value, 0)
        : null;
      const grid = engineNode('div', 'engine-breadth-grid');
      metrics.forEach((metric) => {
        const row = engineNode('div', `engine-breadth-row ${engineBreadthClass(metric.name)}`);
        const ratio = metric.value !== null && marketTotal !== null && marketTotal > 0
          ? Math.min(100, Math.max(0, metric.value / marketTotal * 100))
          : null;
        const ratioLabel = ratio === null ? '比例待补' : `${ratio.toFixed(1)}%`;
        const meta = engineNode('div', 'engine-breadth-meta');
        meta.append(
          engineNode('span', '', metric.name),
          engineNode(
            'strong',
            '',
            metric.value === null
              ? `待确认 · ${ratioLabel}`
              : `${metric.value} 家 · ${ratioLabel}`
          )
        );
        const track = engineNode('div', 'engine-breadth-track');
        const bar = engineNode('i', 'engine-breadth-fill');
        if (ratio !== null) {
          bar.style.width = `${ratio.toFixed(1)}%`;
          track.setAttribute('role', 'meter');
          track.setAttribute('aria-label', metric.name);
          track.setAttribute('aria-valuemin', '0');
          track.setAttribute('aria-valuemax', '100');
          track.setAttribute('aria-valuenow', ratio.toFixed(1));
        } else {
          row.classList.add('is-pending');
          track.setAttribute('role', 'status');
          track.setAttribute('aria-label', `${metric.name}：${ratioLabel}`);
        }
        track.append(bar);
        row.append(meta, track);
        grid.append(row);
      });
      article.append(grid);
    }

    function renderEngineMarketPulseSection(section, article) {
      article.classList.add('is-market-pulse');
      const items = engineSectionItems(section);
      const grid = engineNode('div', 'engine-pulse-grid');
      items.forEach((item) => {
        const state = engineFactValue(item, ['状态']) || '中性';
        const tone = state.includes('强')
          ? 'positive'
          : state.includes('弱')
            ? 'negative'
            : 'caution';
        const card = engineNode('article', `engine-pulse-metric tone-${tone}`);
        card.append(
          engineNode('span', '', item.label || item.name || '统计项'),
          engineNode('strong', '', item.summary || '待补'),
          engineNode('p', '', item.risk || '统计口径待确认。')
        );
        grid.append(card);
      });
      if (!items.length) {
        grid.append(engineNode('div', 'engine-section-empty', '市场统计待补。'));
      }
      article.append(grid);
    }

    function renderEngineStockEvidenceSection(section, article) {
      article.classList.add('is-stock-evidence');
      const items = engineSectionItems(section);
      const grid = engineNode('div', 'engine-evidence-grid');
      items.forEach((item) => {
        const card = engineNode(
          'article',
          `engine-evidence-card state-${item.status || 'partial'}`
        );
        const head = engineNode('div', 'engine-evidence-head');
        head.append(
          engineNode('strong', '', item.label || item.name || '研究维度'),
          engineNode('span', '', engineFactValue(item, ['评分']) || '待评分'),
          engineNode('i', '', engineFactValue(item, ['可信度']) || '低')
        );
        const support = engineNode('div', 'engine-evidence-copy is-support');
        support.append(
          engineNode('span', '', '支持证据'),
          engineNode('p', '', item.summary || '支持证据待补。')
        );
        const counter = engineNode('div', 'engine-evidence-copy is-counter');
        counter.append(
          engineNode('span', '', '反对证据'),
          engineNode('p', '', item.risk || '反对证据待补。')
        );
        const conditions = engineNode('dl', 'engine-evidence-conditions');
        const strengthen = engineNode('div', '');
        strengthen.append(
          engineNode('dt', '', '转强条件'),
          engineNode('dd', '', engineFactValue(item, ['转强条件']) || '待确认')
        );
        const invalidation = engineNode('div', '');
        invalidation.append(
          engineNode('dt', '', '失效条件'),
          engineNode('dd', '', engineFactValue(item, ['失效条件']) || '待确认')
        );
        conditions.append(strengthen, invalidation);
        card.append(head, support, counter, conditions);
        grid.append(card);
      });
      if (!items.length) {
        grid.append(engineNode('div', 'engine-section-empty', '个股证据矩阵待补。'));
      }
      article.append(grid);
    }

    function renderEngineStockDecisionSection(section, article) {
      article.classList.add('is-stock-decision');
      const grid = engineNode('div', 'engine-stock-decision-grid');
      const items = engineSectionItems(section);
      items.forEach((item) => {
        const card = engineNode('article', 'engine-stock-decision-card');
        card.append(
          engineNode('span', '', item.label || '决策项'),
          engineNode('strong', '', item.summary || '结论待确认。')
        );
        if (item.risk) card.append(engineNode('small', '', item.risk));
        grid.append(card);
      });
      if (!items.length) {
        grid.append(engineNode('div', 'engine-section-empty', '整体结论待补。'));
      }
      article.append(grid);
    }

    function engineListCell(label, className, value) {
      const cell = engineNode('div', className, value || '待确认');
      cell.dataset.label = label;
      return cell;
    }

    function engineStockAnalysisLink(item) {
      const link = engineNode('a', 'engine-list-action', '个股分析');
      link.href = `/?code=${encodeURIComponent(item.code || '')}#stock`;
      link.setAttribute('aria-label', `打开 ${item.name || item.code || '候选'} 个股分析`);
      return link;
    }

    function renderEngineMarketMoverSection(section, article) {
      article.classList.add('is-market-movers');
      const list = engineNode('div', 'engine-research-list engine-mover-list');
      const header = engineNode('div', 'engine-research-list-head');
      ['股票', '主题', '涨跌', '异动原因', '确认条件', '失效条件', '操作'].forEach(
        (label) => header.append(engineNode('span', '', label))
      );
      list.append(header);
      const items = engineSectionItems(section);
      items.forEach((item) => {
        const row = engineNode('article', 'engine-research-list-row engine-mover-row');
        row.append(
          engineListCell(
            '股票',
            'engine-list-stock',
            `${item.name || '待确认'} · ${item.code || '—'}`
          ),
          engineListCell('主题', 'engine-list-theme', item.label || '主题待确认'),
          engineListCell('涨跌', 'engine-list-move', engineFactValue(item, ['涨跌幅'])),
          engineListCell(
            '异动原因',
            'engine-list-reason',
            engineFactValue(item, ['异动原因'])
          ),
          engineListCell(
            '确认条件',
            'engine-list-confirm',
            engineFactValue(item, ['确认条件'])
          ),
          engineListCell(
            '失效条件',
            'engine-list-risk',
            engineFactValue(item, ['失效条件'])
          )
        );
        row.append(engineStockAnalysisLink(item));
        list.append(row);
      });
      if (!items.length) {
        list.append(engineNode('div', 'engine-section-empty', '当前扫描没有可分析异动。'));
      }
      article.append(list);
    }

    function renderEngineOpportunityList(section, article) {
      article.classList.add('is-opportunity-list');
      const list = engineNode('div', 'engine-research-list engine-opportunity-list');
      const header = engineNode('div', 'engine-research-list-head');
      ['#', '股票', '主题', '分数 / 涨跌', '入选原因', '风险 / 失效', '确认条件', '操作']
        .forEach((label) => header.append(engineNode('span', '', label)));
      list.append(header);
      const items = engineSectionItems(section);
      items.forEach((item, index) => {
        const row = engineNode('article', 'engine-research-list-row engine-opportunity-row');
        row.append(
          engineListCell('排名', 'engine-list-rank', String(index + 1).padStart(2, '0')),
          engineListCell(
            '股票',
            'engine-list-stock',
            `${item.name || '待确认'} · ${item.code || '—'}`
          ),
          engineListCell('主题', 'engine-list-theme', item.label || '主题待确认'),
          engineListCell(
            '分数 / 涨跌',
            'engine-list-score',
            `${engineFactValue(item, ['观察分']) || '—'} / ${
              engineFactValue(item, ['涨跌幅']) || '—'
            }`
          ),
          engineListCell(
            '入选原因',
            'engine-list-reason',
            engineFactValue(item, ['入选原因'])
          ),
          engineListCell(
            '风险 / 失效',
            'engine-list-risk',
            engineFactValue(item, ['失效条件'])
          ),
          engineListCell(
            '确认条件',
            'engine-list-confirm',
            engineFactValue(item, ['确认条件'])
          )
        );
        row.append(engineStockAnalysisLink(item));
        list.append(row);
      });
      if (!items.length) {
        list.append(engineNode('div', 'engine-section-empty', '当前没有通过风险排除的候选。'));
      }
      article.append(list);
    }

    function renderEngineStockCard(item) {
      const card = engineNode('article', `engine-stock-card state-${item.status || 'ready'}`);
      const meta = engineNode('div', 'engine-stock-card-meta');
      meta.append(
        engineNode('span', '', item.code || '代码待确认'),
        engineNode('i', '', engineItemState(item))
      );
      card.append(
        meta,
        engineNode('strong', '', item.name || '股票待确认'),
        engineNode('span', 'engine-stock-theme', item.label || '主题待确认'),
        engineNode('p', '', item.summary || '入选依据待确认。'),
        engineNode('small', '', item.risk || '风险待确认。')
      );
      return card;
    }

    function renderEngineStockSection(section, article) {
      const grid = engineNode('div', 'engine-stock-card-grid');
      const items = engineSectionItems(section);
      items.forEach((item) => grid.append(renderEngineStockCard(item)));
      if (!items.length) grid.append(engineNode('div', 'engine-section-empty', '候选待确认。'));
      article.append(grid);
    }

    function engineCandidateTheme(label) {
      const normalized = String(label || '').trim().replace(/\s+/g, ' ');
      return normalized || '主题待确认';
    }

    function renderEngineCandidateSection(section, article) {
      const items = engineSectionItems(section);
      const groups = new Map();
      items.forEach((item) => {
        const theme = engineCandidateTheme(item.label);
        if (!groups.has(theme)) groups.set(theme, []);
        groups.get(theme).push(item);
      });
      const entries = [...groups.entries()].sort(([left], [right]) => {
        if (left === '主题待确认') return 1;
        if (right === '主题待确认') return -1;
        return 0;
      });
      entries.forEach(([theme, candidates]) => {
        const group = engineNode('section', 'engine-candidate-group');
        group.append(engineNode('h4', 'engine-candidate-group-title', theme));
        const grid = engineNode('div', 'engine-stock-card-grid');
        candidates.forEach((item) => grid.append(renderEngineStockCard(item)));
        group.append(grid);
        article.append(group);
      });
      if (!entries.length) {
        article.append(engineNode('div', 'engine-section-empty', '候选待确认。'));
      }
    }

    function renderEngineDivergenceSection(section, article) {
      const grid = engineNode('div', 'engine-divergence-grid');
      const items = engineSectionItems(section);
      items.forEach((item) => {
        const card = engineNode(
          'article',
          `engine-divergence-card state-${item.status || 'ready'}`
        );
        card.append(engineNode('strong', '', item.name || '主题待确认'));
        const comparison = engineNode('div', 'engine-divergence-comparison');
        const summary = String(item.summary || '分化待确认。');
        const strong = summary.match(/相对强：([^；。]+)/);
        const weak = summary.match(/相对弱：([^；。]+)/);
        if (strong || weak) {
          comparison.append(
            engineNode('p', 'is-strong', strong ? `相对强 ${strong[1]}` : '相对强 待确认'),
            engineNode('p', 'is-weak', weak ? `相对弱 ${weak[1]}` : '相对弱 待确认')
          );
        } else {
          comparison.append(engineNode('p', 'is-pending', summary));
        }
        card.append(comparison);
        if (item.risk) card.append(engineNode('small', '', item.risk));
        grid.append(card);
      });
      if (!items.length) {
        grid.append(engineNode('div', 'engine-section-empty', '主题内分化待确认。'));
      }
      article.append(grid);
    }

    function renderEngineSections(workspace, payload) {
      const sectionRoot = workspace.querySelector('[data-engine-sections]');
      const grid = workspace.querySelector('[data-engine-section-grid]');
      if (!sectionRoot || !grid) return;
      const sections = Array.isArray(payload.module_sections)
        ? payload.module_sections.filter(
          (section) => section && typeof section === 'object'
        )
        : [];
      grid.replaceChildren();
      sections.forEach((section) => {
        const article = engineNode(
          'article',
          `engine-research-section tone-${section.tone || 'neutral'}`
        );
        article.dataset.engineSectionKey = section.key || '';
        article.append(renderEngineSectionHeading(section));
        if (section.key === 'market-pulse') {
          renderEngineMarketPulseSection(section, article);
        } else if (section.key === 'market-movers') {
          renderEngineMarketMoverSection(section, article);
        } else if (section.key === 'stock-decision') {
          renderEngineStockDecisionSection(section, article);
        } else if (section.key === 'stock-evidence') {
          renderEngineStockEvidenceSection(section, article);
        } else if (section.key === 'market-breadth') {
          renderEngineBreadthSection(section, article);
        } else if (section.key === 'portfolio-divergence') {
          renderEngineDivergenceSection(section, article);
        } else if (section.key === 'opportunity-candidates') {
          renderEngineOpportunityList(section, article);
        } else if (section.key === 'market-hot') {
          renderEngineStockSection(section, article);
        } else if (String(section.key || '').endsWith('-themes')) {
          renderEngineThemeSection(section, article);
        } else {
          renderEngineStockSection(section, article);
        }
        grid.append(article);
      });
      sectionRoot.hidden = sections.length === 0;
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
      const decisionLabel = workspace.querySelector('[data-engine-decision-label]');
      const action = workspace.querySelector('[data-engine-action]');
      const risk = workspace.querySelector('[data-engine-risk]');
      const generated = workspace.querySelector('[data-engine-generated]');
      const live = workspace.querySelector('[data-engine-live-state]');
      const details = Array.isArray(payload.details) ? payload.details : [];
      const coverage = workspace.querySelector('[data-engine-coverage]');
      const delivery = workspace.querySelector('[data-engine-delivery]');
      const fallbackReason = workspace.querySelector('[data-engine-fallback-reason]');
      if (decisionLabel) {
        const label = payload.decision_label || '待确认';
        const tone = engineDecisionTone(label);
        decisionLabel.textContent = label;
        decisionLabel.dataset.engineDecisionTone = tone;
        decisionLabel.className = `engine-decision-label state-${tone}`;
      }
      if (verdict) verdict.textContent = payload.verdict || '本次证据不足，判断暂停。';
      if (action) action.textContent = payload.action || '稍后重新分析。';
      if (risk) risk.textContent = payload.primary_risk || '缺少足够证据。';
      if (generated) {
        const evidenceTime = payload.as_of || payload.generated_at;
        const date = evidenceTime ? new Date(evidenceTime) : null;
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
          live: '实时研究',
          snapshot: '当日快照',
          stale_snapshot: '历史参考',
          local_fallback: '本地证据',
          unavailable: '数据缺失'
        };
        delivery.textContent = payload.data_label
          || deliveryLabels[payload.delivery]
          || '实时研究';
        delivery.classList.toggle('is-stale', Boolean(payload.stale));
      }
      workspace.dataset.engineDelivery = payload.delivery || 'live';
      if (fallbackReason) {
        fallbackReason.textContent = payload.fallback_reason || '';
        fallbackReason.hidden = !fallbackReason.textContent;
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
      renderEngineSections(workspace, payload);
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
        if (engineCache.has(key)) {
          renderEngineResult(workspace, engineCache.get(key));
          const live = workspace.querySelector('[data-engine-live-state]');
          if (live) live.textContent = '刷新失败，已保留现有内容';
        } else {
          renderEngineResult(workspace, {
            status: 'unavailable',
            delivery: 'unavailable',
            data_label: '数据缺失',
            verdict: '研究服务暂时不可用，当前没有可执行结论。',
            action: '稍后重新分析；当前不沿用旧结论。',
            primary_risk: error.message || '研究请求失败。',
            findings: [],
            details: [],
            missing_sections: []
          });
        }
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
    return "本地证据可用", "ready", True
