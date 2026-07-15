from __future__ import annotations

import json
import shutil
import subprocess

import pytest
from bs4 import BeautifulSoup

from stock_ts.web import render_page
from stock_ts.webapp.engine_workspace import engine_app_script, render_engine_workspace
from stock_ts.webapp.styles import CSS


class ExplodingProvider:
    def __getattr__(self, name: str):
        raise AssertionError(f"local provider must not be used: {name}")


def _run_engine_dom_scenario(scenario: str) -> dict[str, object]:
    if shutil.which("node") is None:
        pytest.skip("node is required for executable DOM contract tests")
    script = engine_app_script()
    source = script.split("<script>", 1)[1].split("</script>", 1)[0]
    source = source.split("if (document.readyState === 'loading')", 1)[0]
    dom_stub = r"""
class FakeClassList {
  constructor(node) { this.node = node; }
  values() { return new Set(this.node.className.split(/\s+/).filter(Boolean)); }
  add(...names) {
    const values = this.values();
    names.forEach((name) => values.add(name));
    this.node.className = [...values].join(' ');
  }
  toggle(name, force) {
    const values = this.values();
    const enabled = force === undefined ? !values.has(name) : Boolean(force);
    if (enabled) values.add(name); else values.delete(name);
    this.node.className = [...values].join(' ');
    return enabled;
  }
}
class FakeNode {
  constructor(tag) {
    this.tagName = String(tag).toUpperCase();
    this.className = '';
    this.children = [];
    this.attributes = {};
    this.dataset = {};
    this.style = {};
    this.hidden = false;
    this._textContent = '';
    this.classList = new FakeClassList(this);
  }
  set textContent(value) { this._textContent = String(value); this.children = []; }
  get textContent() {
    return this._textContent + this.children.map((child) => child.textContent).join('');
  }
  append(...nodes) {
    nodes.forEach((node) => this.children.push(
      typeof node === 'string' ? document.createTextNode(node) : node
    ));
  }
  replaceChildren(...nodes) { this.children = []; this._textContent = ''; this.append(...nodes); }
  setAttribute(name, value) { this.attributes[name] = String(value); }
}
function findByClass(node, className) {
  const found = node.className.split(/\s+/).includes(className) ? [node] : [];
  return found.concat(node.children.flatMap((child) => findByClass(child, className)));
}
global.document = {
  createElement: (tag) => new FakeNode(tag),
  createTextNode: (value) => {
    const node = new FakeNode('#text');
    node.textContent = value;
    return node;
  },
  querySelectorAll: () => []
};
"""
    completed = subprocess.run(
        ["node"],
        input=f"{dom_stub}\n{source}\n{scenario}",
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout.strip().splitlines()[-1])


def test_root_page_renders_four_lazy_workspaces_without_local_provider_calls() -> None:
    html = render_page(
        provider=ExplodingProvider(),
        stock_code="600519",
        holdings_path="data/portfolio/holdings.csv",
    )

    assert html.count('data-engine-workspace="') == 4
    assert "当前判断" in html
    assert "现在怎么做" in html
    assert "最大风险" in html
    assert "重新分析" in html


def test_native_page_removes_global_research_method_narration() -> None:
    html = render_page(stock_code="600519")

    assert html.count('data-engine-workspace="') == 4
    for narration in (
        "STOCKTS / RESEARCH DESK",
        "只看判断、动作与风险",
        "四个工作台按需生成",
    ):
        assert narration not in html


def test_visible_page_copy_is_supplier_neutral() -> None:
    html = render_page(stock_code="600519")

    for forbidden in ("问财", "iWencai", "同花顺", "Skill", "外部证据"):
        assert forbidden not in html


def test_each_primary_workspace_has_one_judgment_band_and_three_finding_slots() -> None:
    soup = BeautifulSoup(render_page(stock_code="600519"), "html.parser")

    for module in ("market", "portfolio", "stock", "opportunity"):
        workspace = soup.select_one(f'[data-engine-workspace="{module}"]')
        assert workspace is not None
        assert len(workspace.select("[data-engine-judgment]")) == 1
        assert len(workspace.select("[data-engine-verdict]")) == 1
        assert len(workspace.select("[data-engine-action]")) == 1
        assert len(workspace.select("[data-engine-risk]")) == 1
        assert len(workspace.select("[data-engine-findings]")) == 1
        details = workspace.select_one("details[data-engine-disclosure]")
        assert details is not None
        assert "open" not in details.attrs


def test_each_workspace_exposes_three_result_shortcuts() -> None:
    soup = BeautifulSoup(render_page(stock_code="600519"), "html.parser")

    for module in ("market", "portfolio", "stock", "opportunity"):
        workspace = soup.select_one(f'[data-engine-workspace="{module}"]')
        assert workspace is not None
        assert [node["data-engine-jump"] for node in workspace.select("[data-engine-jump]")] == [
            "risk",
            "findings",
            "evidence",
        ]
        for target in ("risk", "findings", "evidence"):
            assert workspace.select_one(f'[data-engine-target="{target}"]') is not None


def test_native_page_has_four_item_mobile_research_dock() -> None:
    soup = BeautifulSoup(render_page(stock_code="600519"), "html.parser")

    docks = soup.select("[data-engine-mobile-dock]")
    assert len(docks) == 1
    buttons = docks[0].select("[data-engine-mobile-nav][data-workspace]")
    assert [button["data-workspace"] for button in buttons] == [
        "market",
        "portfolio",
        "stock",
        "opportunity",
    ]
    assert all(button["data-engine-nav-state"] == "idle" for button in buttons)


def test_only_primary_desktop_navigation_exposes_research_state() -> None:
    soup = BeautifulSoup(render_page(stock_code="600519"), "html.parser")
    stateful_items = soup.select(".sidebar .nav-item[data-engine-nav-state]")

    assert [item["data-workspace"] for item in stateful_items] == [
        "market",
        "portfolio",
        "stock",
        "opportunity",
    ]
    assert all(item["data-engine-nav-state"] == "idle" for item in stateful_items)
    assert not soup.select(
        '.sidebar .nav-item[data-workspace="data-center"][data-engine-nav-state], '
        '.sidebar .nav-item[data-workspace="account"][data-engine-nav-state]'
    )


def test_portfolio_page_context_only_contains_code_and_name(tmp_path) -> None:
    holdings = tmp_path / "holdings.csv"
    holdings.write_text(
        "code,name,shares,cost_price,sector,note\n"
        "600519,贵州茅台,100,1500,白酒,核心仓\n",
        encoding="utf-8",
    )
    soup = BeautifulSoup(
        render_page(stock_code="600519", holdings_path=str(holdings)),
        "html.parser",
    )
    workspace = soup.select_one('[data-engine-workspace="portfolio"]')
    assert workspace is not None

    context = json.loads(workspace["data-engine-context"])

    assert context == {"holdings": [{"code": "600519", "name": "贵州茅台"}]}
    serialized = json.dumps(context, ensure_ascii=False)
    for forbidden in ("shares", "cost_price", "weight", "核心仓", "1500"):
        assert forbidden not in serialized


def test_portfolio_page_context_keeps_twenty_names_and_codes_only(tmp_path) -> None:
    holdings = tmp_path / "holdings.csv"
    rows = [
        f"60{index:04d},持仓{index},100,10,行业,备注{index}"
        for index in range(21)
    ]
    holdings.write_text(
        "code,name,shares,cost_price,sector,note\n" + "\n".join(rows) + "\n",
        encoding="utf-8",
    )
    soup = BeautifulSoup(
        render_page(stock_code="603278", holdings_path=str(holdings)),
        "html.parser",
    )
    workspace = soup.select_one('[data-engine-workspace="portfolio"]')
    assert workspace is not None

    context = json.loads(workspace["data-engine-context"])

    assert len(context["holdings"]) == 20
    assert set(context["holdings"][0]) == {"code", "name"}
    serialized = json.dumps(context, ensure_ascii=False)
    assert "shares" not in serialized
    assert "cost_price" not in serialized
    assert "备注" not in serialized


def test_engine_script_uses_product_endpoint_and_text_only_rendering() -> None:
    script = engine_app_script()

    assert "fetch('/api/research/workspace'" in script
    assert "window.__stockTsInitialHash" in script
    assert ".textContent" in script
    assert ".innerHTML" not in script
    assert "replaceChildren" in script
    for forbidden in ("问财", "iWencai", "同花顺", "Skill", "外部证据"):
        assert forbidden not in script


def test_engine_script_coordinates_navigation_and_shortcuts() -> None:
    script = engine_app_script()

    for fragment in (
        "setEngineNavigationState",
        "data-engine-nav-state",
        "aria-current",
        "isContentEditable",
        "event.key.toLowerCase() === 'r'",
        "engineKeyboardModules",
        "data-engine-jump",
        "scrollIntoView",
        "event.key === 'Escape'",
        "正在逐只核对，可能需要几秒",
        "window.matchMedia('(prefers-reduced-motion: reduce)')",
    ):
        assert fragment in script


def test_engine_workspace_uses_full_parent_width_on_mobile() -> None:
    engine_css = CSS.split(".engine-module,", 1)[1].split("}", 1)[0]

    assert "width:100%" in engine_css.replace(" ", "")


def test_mobile_research_dock_is_fixed_safe_and_touchable() -> None:
    compact_css = CSS.replace(" ", "")
    mobile_sidebar_selector = ".engine-app-shell .sidebar .nav-item[data-engine-nav-state]"
    assert mobile_sidebar_selector in CSS
    mobile_sidebar_rule = CSS.split(
        mobile_sidebar_selector, 1
    )[1].split("}", 1)[0]

    assert ".engine-mobile-dock" in CSS
    assert "env(safe-area-inset-bottom)" in CSS
    assert "position:fixed" in compact_css
    assert "min-height:44px" in compact_css
    assert "display:none" in mobile_sidebar_rule.replace(" ", "")
    for state in ("idle", "loading", "complete", "partial", "unavailable"):
        assert f'[data-engine-nav-state="{state}"]' in CSS


def test_engine_workspace_exposes_evidence_completeness() -> None:
    html = render_engine_workspace("stock", status="configured")

    assert "data-engine-coverage" in html
    assert "已确认维度" in html


def test_workspace_exposes_module_specific_list_and_delivery_state() -> None:
    html = render_engine_workspace("market", status="configured")

    assert "data-engine-module-items" in html
    assert "data-engine-module-items-title" in html
    assert "data-engine-delivery" in html


def test_engine_script_renders_module_items_without_inner_html() -> None:
    script = engine_app_script()

    assert "renderEngineModuleItems" in script
    assert "payload.module_items" in script
    assert "payload.module === 'stock'" in script
    assert "item.label || '研究维度'" in script
    assert "encodeURIComponent" in script
    assert ".innerHTML" not in script


def test_module_item_grid_is_responsive_and_marks_stale_delivery() -> None:
    assert ".engine-module-item-grid" in CSS
    assert ".engine-delivery.is-stale" in CSS
    assert "grid-template-columns:minmax(0,1fr)" in CSS.replace(" ", "")


def test_finding_cards_have_rank_and_evidence_role() -> None:
    script = engine_app_script()

    assert "engine-finding-rank" in script
    assert "engine-evidence-tag" in script
    assert "item.title" in script
    assert "证据不足" in script
    assert "获取失败" in script


def test_workspace_places_decision_and_sections_before_findings() -> None:
    html = render_engine_workspace("market", status="configured")

    assert html.index("data-engine-decision-label") < html.index("data-engine-verdict>")
    assert html.index("data-engine-verdict>") < html.index("data-engine-sections")
    assert html.index("data-engine-sections") < html.index(
        'data-engine-target="findings"'
    )
    assert "判断指数、宏观、主线与风险是否同向" not in html


def test_engine_script_renders_sections_with_safe_dom_only() -> None:
    script = engine_app_script()

    assert "renderEngineSections" in script
    assert "payload.module_sections" in script
    assert "market-breadth" in script
    assert "bar.style.width" in script
    assert ".innerHTML" not in script


def test_theme_strip_scrolls_without_widening_the_page() -> None:
    compact_css = CSS.replace(" ", "")
    theme_rule = compact_css.split(".engine-theme-strip", 1)[1].split("}", 1)[0]

    assert "overflow-x:auto" in theme_rule
    assert "overscroll-behavior-inline:contain" in theme_rule
    assert ".engine-breadth-fill" in CSS


def test_partial_breadth_never_uses_an_incomplete_market_total() -> None:
    script = engine_app_script()

    assert "const coreBreadthNames = ['上涨家数', '下跌家数', '平盘家数']" in script
    assert "coreBreadthNames.every" in script
    assert "coreBreadthComplete ?" in script
    assert "比例待补" in script


def test_complete_breadth_prints_the_calculated_ratio_next_to_the_count() -> None:
    script = engine_app_script()

    assert "ratio.toFixed(1)" in script
    assert "`${metric.value} 家 · ${ratioLabel}`" in script


def test_breadth_dom_distinguishes_empty_partial_and_complete_data() -> None:
    result = _run_engine_dom_scenario(
        r"""
function breadthItem(name, value) {
  return {name, summary: String(value), status: 'ready', facts: []};
}
function renderBreadth(items) {
  const article = new FakeNode('article');
  renderEngineBreadthSection({items}, article);
  const tracks = findByClass(article, 'engine-breadth-track');
  return {
    text: article.textContent,
    rows: findByClass(article, 'engine-breadth-row').length,
    empty: findByClass(article, 'engine-section-empty').length,
    meters: tracks
      .filter((track) => track.attributes.role === 'meter')
      .map((track) => ({
        min: track.attributes['aria-valuemin'],
        max: track.attributes['aria-valuemax'],
        now: track.attributes['aria-valuenow']
      }))
  };
}
console.log(JSON.stringify({
  empty: renderBreadth([]),
  partial: renderBreadth([breadthItem('上涨家数', 3681)]),
  complete: renderBreadth([
    breadthItem('上涨家数', 3681),
    breadthItem('下跌家数', 1771),
    breadthItem('平盘家数', 71),
    breadthItem('涨停家数', 63),
    breadthItem('跌停家数', 16)
  ])
}));
"""
    )

    assert result["empty"] == {
        "text": "市场分布待补。",
        "rows": 0,
        "empty": 1,
        "meters": [],
    }
    assert result["partial"]["rows"] == 5
    assert result["partial"]["meters"] == []
    assert "3681 家 · 比例待补" in result["partial"]["text"]
    assert "待确认 · 比例待补" in result["partial"]["text"]
    assert "3681 家 · 66.6%" in result["complete"]["text"]
    assert len(result["complete"]["meters"]) == 5
    assert all(
        meter["min"] == "0" and meter["max"] == "100" and meter["now"]
        for meter in result["complete"]["meters"]
    )


def test_decision_tone_is_semantic_and_independent_from_completion() -> None:
    result = _run_engine_dom_scenario(
        """
console.log(JSON.stringify({
  weak: engineDecisionTone('偏弱'),
  stressed: engineDecisionTone('基本面承压'),
  risk: engineDecisionTone('先处理风险'),
  repairing: engineDecisionTone('修复中'),
  strong: engineDecisionTone('偏强'),
  unknown: engineDecisionTone('分化中')
}));
"""
    )

    assert result == {
        "weak": "negative",
        "stressed": "negative",
        "risk": "negative",
        "repairing": "caution",
        "strong": "positive",
        "unknown": "neutral",
    }
    assert ".engine-decision-label.state-negative" in CSS
    assert ".engine-decision-label.state-positive" in CSS


def test_opportunity_candidates_group_by_theme_but_market_hot_does_not() -> None:
    result = _run_engine_dom_scenario(
        r"""
const candidateArticle = new FakeNode('article');
renderEngineCandidateSection({items: [
  {code: '001', name: '甲', label: ' 半导体 ', summary: '依据甲'},
  {code: '002', name: '乙', label: '半导体', summary: '依据乙'},
  {code: '003', name: '丙', label: '创新药', summary: '依据丙'},
  {code: '004', name: '丁', label: '', summary: '依据丁'}
]}, candidateArticle);
const hotArticle = new FakeNode('article');
renderEngineStockSection({items: [
  {code: '001', name: '甲', label: '半导体'},
  {code: '003', name: '丙', label: '创新药'}
]}, hotArticle);
console.log(JSON.stringify({
  groups: findByClass(candidateArticle, 'engine-candidate-group').map(
    (node) => findByClass(node, 'engine-candidate-group-title')[0].textContent
  ),
  hotGroups: findByClass(hotArticle, 'engine-candidate-group').length,
  candidateCards: findByClass(candidateArticle, 'engine-stock-card').length
}));
"""
    )

    assert result["groups"] == ["半导体", "创新药", "主题待确认"]
    assert result["hotGroups"] == 0
    assert result["candidateCards"] == 4


def test_theme_strip_is_keyboard_focusable_and_malformed_items_do_not_throw() -> None:
    result = _run_engine_dom_scenario(
        r"""
const themeArticle = new FakeNode('article');
renderEngineThemeSection({title: '主题', items: [null, {}, {facts: null}]}, themeArticle);
const strip = findByClass(themeArticle, 'engine-theme-strip')[0];
const breadthArticle = new FakeNode('article');
renderEngineBreadthSection({items: [null, {}, {facts: null}]}, breadthArticle);
const candidateArticle = new FakeNode('article');
renderEngineCandidateSection({items: [null, {}, {facts: null}]}, candidateArticle);
console.log(JSON.stringify({
  tabindex: strip.attributes.tabindex,
  role: strip.attributes.role,
  label: strip.attributes['aria-label'],
  breadthRows: findByClass(breadthArticle, 'engine-breadth-row').length,
  candidateCards: findByClass(candidateArticle, 'engine-stock-card').length
}));
"""
    )

    assert result["tabindex"] == "0"
    assert result["role"] == "region"
    assert result["label"] == "主题横向列表"
    assert result["breadthRows"] == 5
    assert result["candidateCards"] == 2
    assert ".engine-theme-strip:focus-visible" in CSS


def test_390px_workspace_is_single_column_and_clips_page_overflow() -> None:
    compact_css = CSS.replace(" ", "")
    mobile_css = compact_css.rsplit("@media(max-width:640px)", 1)[1]
    root_rule = mobile_css.split(".engine-workspace-root", 1)[1].split("}", 1)[0]
    sections_rule = mobile_css.split(".engine-section-grid", 1)[1].split("}", 1)[0]

    assert "max-width:100%" in root_rule
    assert "min-width:0" in root_rule
    assert "overflow-x:clip" in root_rule or "overflow-x:hidden" in root_rule
    assert "grid-template-columns:minmax(0,1fr)" in sections_rule


def test_390px_first_screen_uses_compact_chrome_without_clipping_content() -> None:
    compact_css = CSS.replace(" ", "")
    mobile_css = compact_css.rsplit("@media(max-width:640px)", 1)[1]
    sidebar_rule = mobile_css.split(".engine-app-shell.sidebar", 1)[1].split("}", 1)[0]
    judgment_rule = mobile_css.split(".engine-judgment", 1)[1].split("}", 1)[0]
    action_rule = mobile_css.split(".engine-action-risk", 1)[1].split("}", 1)[0]
    verdict_rule = mobile_css.split(".engine-verdict", 1)[1].split("}", 1)[0]

    assert "padding:8px10px6px" in sidebar_rule
    assert "grid-template-columns:minmax(0,1fr)" in judgment_rule
    assert "grid-template-columns:repeat(2,minmax(0,1fr))" in action_rule
    assert "padding:12px" in verdict_rule
    assert "height:" not in judgment_rule
    assert "max-height:" not in judgment_rule


def test_390px_keeps_ios_input_and_key_research_labels_readable() -> None:
    compact_css = "".join(CSS.split())
    mobile_css = compact_css.rsplit("@media(max-width:640px)", 1)[1]
    input_rule = mobile_css.split(
        ".engine-app-shell.quick-stock-searchinput{", 1
    )[1].split("}", 1)[0]
    delivery_rule = mobile_css.split(
        ".engine-metatime,.engine-delivery", 1
    )[1].split("}", 1)[0]
    judgment_labels = mobile_css.split(
        ".engine-verdict>span,.engine-actionspan,.engine-riskspan", 1
    )[1].split("}", 1)[0]
    decision_label = mobile_css.split(
        ".engine-decision-label{", 1
    )[1].split("}", 1)[0]

    assert "font-size:16px" in input_rule
    assert "font-size:10px" in delivery_rule
    assert "font-size:10px" in judgment_labels
    assert "font-size:10px" in decision_label
