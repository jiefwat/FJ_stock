from __future__ import annotations

from bs4 import BeautifulSoup, Tag

from stock_ts.providers.sample import SampleDataProvider
from stock_ts.web import render_page
from stock_ts.webapp.research_console import render_iwencai_research_console
from stock_ts.webapp.styles import CSS


def _sample_soup() -> BeautifulSoup:
    return BeautifulSoup(
        render_page(
            stock_code="600519",
            provider_name="sample",
            provider=SampleDataProvider(),
            holdings_path="data/portfolio/holdings.csv",
        ),
        "html.parser",
    )


def _workspace(soup: BeautifulSoup, key: str) -> Tag:
    workspace = soup.select_one(f'.workspace-pane[data-workspace="{key}"]')
    assert isinstance(workspace, Tag)
    return workspace


def _outside_details(nodes: list[Tag]) -> list[Tag]:
    return [node for node in nodes if node.find_parent("details") is None]


def test_four_workspaces_expose_one_verdict_action_and_risk() -> None:
    soup = _sample_soup()
    verdict_selectors = {
        "market": "[data-primary-market-verdict]",
        "portfolio": "[data-primary-portfolio-verdict]",
        "stock": "[data-primary-stock-verdict]",
        "opportunity": "[data-primary-opportunity-verdict]",
    }

    for key, verdict_selector in verdict_selectors.items():
        workspace = _workspace(soup, key)
        assert len(_outside_details(workspace.select(verdict_selector))) == 1, key
        assert len(_outside_details(workspace.select("[data-essence-action]"))) == 1, key
        assert len(_outside_details(workspace.select("[data-essence-risk]"))) == 1, key
        assert len(_outside_details(workspace.select("h3"))) <= 2, key


def test_each_workspace_has_sibling_evidence_and_iwencai_drawers() -> None:
    soup = _sample_soup()
    evidence_selectors = {
        "market": "details.market-evidence",
        "portfolio": "details.portfolio-evidence",
        "stock": "details.stock-evidence",
        "opportunity": "details.opportunity-evidence",
    }

    for key, evidence_selector in evidence_selectors.items():
        workspace = _workspace(soup, key)
        evidence = workspace.select(evidence_selector)
        iwencai = workspace.select("details.iwencai-research-disclosure")
        assert len(evidence) == 1, key
        assert len(iwencai) == 1, key
        assert "open" not in evidence[0].attrs, key
        assert "open" not in iwencai[0].attrs, key
        assert evidence[0].find_parent("details") is None, key
        assert iwencai[0].find_parent("details") is None, key
        assert not evidence[0].select("details"), key


def test_professional_process_stays_inside_closed_evidence_drawers() -> None:
    soup = _sample_soup()
    contracts = {
        "market": (
            "details.market-evidence",
            (".market-decision-rail", ".research-scenario-grid", ".market-dimension-grid"),
        ),
        "portfolio": (
            "details.portfolio-evidence",
            (".portfolio-metric-strip", ".portfolio-exposure-register", ".portfolio-boundary-grid"),
        ),
        "stock": (
            "details.stock-evidence",
            (".decision-rail", ".dossier-diagnostic-grid", ".dossier-scenario-grid"),
        ),
        "opportunity": (
            "details.opportunity-evidence",
            (".opportunity-funnel-rail", ".opportunity-risk-register"),
        ),
    }

    for key, (drawer_selector, hidden_selectors) in contracts.items():
        workspace = _workspace(soup, key)
        drawer = workspace.select_one(drawer_selector)
        assert isinstance(drawer, Tag)
        for selector in hidden_selectors:
            assert drawer.select_one(selector) is not None, f"{key}: {selector}"
            assert not _outside_details(workspace.select(selector)), f"{key}: {selector}"


def test_visible_focus_items_are_capped_at_three() -> None:
    soup = _sample_soup()
    selectors = {
        "portfolio": ".portfolio-queue-item",
        "stock": "[data-core-stock-fact]",
        "opportunity": "[data-opportunity-stock-row]",
    }

    for key, selector in selectors.items():
        workspace = _workspace(soup, key)
        visible = _outside_details(workspace.select(selector))
        assert 1 <= len(visible) <= 3, key

    stock = _workspace(soup, "stock")
    assert _outside_details(stock.select("[data-core-stock-counter]"))


def test_iwencai_console_is_closed_until_requested() -> None:
    soup = BeautifulSoup(
        render_iwencai_research_console(module="stock", status="configured"),
        "html.parser",
    )

    drawer = soup.select_one("details.iwencai-research-disclosure")
    assert isinstance(drawer, Tag)
    assert "open" not in drawer.attrs
    assert "问财核查 · 按需展开" in drawer.get_text(" ", strip=True)
    assert drawer.select_one("[data-iwencai-research]") is not None
    assert drawer.select_one("form[data-iwencai-form]") is not None


def test_three_second_css_prioritizes_decisions_on_desktop_and_mobile() -> None:
    for selector in (
        ".essence-verdict",
        ".essence-action-risk",
        ".essence-focus-list",
        ".stock-core-facts",
        ".iwencai-research-disclosure",
    ):
        assert selector in CSS

    mobile = CSS.split("@media (max-width: 760px)")[-1]
    assert ".essence-action-risk" in mobile
    assert ".stock-core-facts" in mobile
    assert "grid-template-columns:1fr" in mobile
    assert ":focus-visible" in CSS
    assert "prefers-reduced-motion" in CSS


def test_light_decision_cards_override_legacy_dark_text_contracts() -> None:
    decision_layer = CSS.split("/* Three-second decision note", 1)[1]

    for selector in (
        ".dossier-decision-brief .dossier-stance h3",
        ".portfolio-verdict-brief .portfolio-verdict-state h3",
        ".opportunity-gate-brief .opportunity-gate-state h3",
    ):
        assert selector in decision_layer
    assert "color:var(--ink)" in decision_layer
    assert ".portfolio-queue-item header" in decision_layer
    assert "grid-template-columns:minmax(0,1fr) auto" in decision_layer
