from __future__ import annotations

from bs4 import BeautifulSoup

from stock_ts.providers.sample import SampleDataProvider
from stock_ts.web import render_page
from stock_ts.webapp.styles import CSS


def _sample_html() -> str:
    return render_page(
        stock_code="600519",
        provider_name="sample",
        provider=SampleDataProvider(),
        holdings_path="data/portfolio/holdings.csv",
    )


def test_core_workspaces_remove_narration_and_decorative_labels() -> None:
    html = _sample_html()
    soup = BeautifulSoup(html, "html.parser")

    for key in ("market", "portfolio", "stock", "opportunity", "data-center"):
        workspace = soup.select_one(f'.workspace-pane[data-workspace="{key}"]')
        assert workspace is not None
        assert not workspace.select(".module-desc")

    for phrase in (
        "当前时刻股票涨跌统计、强弱板块与分析。",
        "只维护和分析真实持仓",
        "用一份投委会档案",
        "先过市场与数据闸门",
        "先恢复可信数据，再恢复研究结论。",
        "研究、观察、条件、风险；不做收益承诺。",
        "RISK GOVERNANCE",
        "ACTION QUEUE",
        "RESEARCH FUNNEL",
        "RESTORE ORDER",
        "DOWNSTREAM IMPACT",
    ):
        assert phrase not in html


def test_each_core_workspace_has_one_closed_evidence_entry() -> None:
    soup = BeautifulSoup(_sample_html(), "html.parser")
    selectors = {
        "market": "details.market-evidence",
        "portfolio": "details.portfolio-evidence",
        "stock": "details.stock-evidence",
        "opportunity": "details.opportunity-evidence",
        "data-center": "details.data-source-ledger",
    }

    for key, selector in selectors.items():
        workspace = soup.select_one(f'.workspace-pane[data-workspace="{key}"]')
        assert workspace is not None
        evidence = workspace.select(selector)
        assert len(evidence) == 1, key
        assert "open" not in evidence[0].attrs, key


def test_essence_css_has_mobile_focus_and_reduced_motion_contracts() -> None:
    assert ".essence-evidence" in CSS
    assert ".essence-strip" in CSS
    assert "@media (max-width: 760px)" in CSS
    assert ":focus-visible" in CSS
    assert "prefers-reduced-motion" in CSS
