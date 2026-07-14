from __future__ import annotations

import json

from bs4 import BeautifulSoup

from stock_ts.web import render_page
from stock_ts.webapp.engine_workspace import engine_app_script, render_engine_workspace
from stock_ts.webapp.styles import CSS


class ExplodingProvider:
    def __getattr__(self, name: str):
        raise AssertionError(f"local provider must not be used: {name}")


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
