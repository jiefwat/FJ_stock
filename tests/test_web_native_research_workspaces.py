from __future__ import annotations

import json

from bs4 import BeautifulSoup

from stock_ts.web import render_page
from stock_ts.webapp.engine_workspace import engine_app_script
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


def test_engine_script_uses_product_endpoint_and_text_only_rendering() -> None:
    script = engine_app_script()

    assert "fetch('/api/research/workspace'" in script
    assert "window.__stockTsInitialHash" in script
    assert ".textContent" in script
    assert ".innerHTML" not in script
    assert "replaceChildren" in script
    for forbidden in ("问财", "iWencai", "同花顺", "Skill", "外部证据"):
        assert forbidden not in script


def test_engine_workspace_uses_full_parent_width_on_mobile() -> None:
    engine_css = CSS.split(".engine-module,", 1)[1].split("}", 1)[0]

    assert "width:100%" in engine_css.replace(" ", "")
