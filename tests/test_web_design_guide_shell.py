import re

from stock_ts.announcements import AnnouncementReport
from stock_ts.providers.sample import SampleDataProvider
from stock_ts.web import render_page
from stock_ts.webapp.styles import CSS


def _render_sample_page() -> str:
    return render_page(
        stock_code="600519",
        provider_name="sample",
        provider=SampleDataProvider(),
        holdings_path="data/portfolio/holdings.csv",
        announcement_fetcher=lambda query, limit=5: AnnouncementReport(
            query=query,
            total=0,
            items=[],
            risk_events=[],
        ),
    )


def test_design_guide_shell_uses_four_business_modules_with_bottom_data_center() -> None:
    html = _render_sample_page()

    for module_id in ["market", "portfolio", "stock", "opportunity", "data-center"]:
        assert f'id="{module_id}"' in html
        assert f'href="#{module_id}"' in html
    for label in ["每日大盘", "我的持仓", "个股分析", "热点机会", "数据中台"]:
        assert label in html
    assert "账户管理" in html
    assert html.count('class="workspace-pane') == 6


def test_ui_skin_uses_professional_terminal_visual_system() -> None:
    html = _render_sample_page()

    for token in [
        "--surface-1",
        "--up",
        "--down",
        "repeating-linear-gradient",
        ".summary-card::before",
        ".data-table tbody tr:hover",
        ".module::before",
    ]:
        assert token in html


def test_editorial_terminal_skin_has_explicit_typography_density_and_accessibility_contract(
) -> None:
    for token in [
        "StockTS editorial research terminal skin",
        '--display: "Avenir Next", "IBM Plex Sans"',
        '--body: "IBM Plex Sans", "HarmonyOS Sans SC"',
        '--number: "IBM Plex Mono", "SFMono-Regular"',
        "font-variant-numeric: tabular-nums",
        ".engine-app-shell .sidebar",
        ".engine-judgment::before",
        ".engine-research-list-row:hover",
        "@media (max-width: 640px)",
        "@media (prefers-reduced-motion: reduce)",
    ]:
        assert token in CSS

    editorial_skin = CSS.split("StockTS editorial research terminal skin", 1)[-1]
    assert "grid-template-columns: 214px minmax(0, 1fr)" in editorial_skin
    assert "max-width: 1580px" in editorial_skin
    assert "border-radius: 4px" in editorial_skin
    assert "linear-gradient(90deg, var(--copper)" in editorial_skin


def test_engine_first_screen_has_compact_neutral_research_status_contract() -> None:
    editorial_skin = CSS.split("StockTS editorial research terminal skin", 1)[-1]
    compact_skin = editorial_skin.replace(" ", "")

    assert ".engine-headerh2" in compact_skin
    assert "font:700clamp(28px,3vw,32px)" in compact_skin
    assert ".engine-verdict{gap:11px;padding:24px" in compact_skin
    assert ".engine-session-line" in editorial_skin
    assert "grid-template-columns:repeat(4,minmax(0,1fr))" in compact_skin
    for selector in (
        '.engine-module[data-engine-delivery="live"] .engine-delivery',
        '.engine-module[data-engine-delivery="unavailable"] .engine-delivery',
        ".engine-coverage.is-complete",
        ".engine-detail-heading .state-ready",
        ".engine-detail-heading .state-failed",
        ".engine-detail-heading .state-missing",
        '[data-engine-nav-state="complete"] .engine-nav-state-dot',
        '[data-engine-nav-state="unavailable"] .engine-nav-state-dot',
        ".engine-service-state.state-ready",
        ".engine-service-state.state-blocked",
        ".engine-decision-label.state-positive",
        ".engine-decision-label.state-negative",
    ):
        assert selector in editorial_skin
        rule = editorial_skin.split(selector, 1)[1].split("}", 1)[0]
        assert "#0e6a5c" not in rule
        assert "#b64a3c" not in rule
        assert "#9a4036" not in rule

    assert ".engine-action { box-shadow:inset 3px 0 0 var(--copper); }" in editorial_skin
    assert ".engine-risk { box-shadow:inset 3px 0 0 var(--amber); }" in editorial_skin

    neutral_research_rules = {
        ".engine-theme-card.state-ready": "var(--navy-2)",
        ".engine-evidence-card.state-ready": "var(--navy-2)",
        ".engine-module-item.state-ready": "var(--copper)",
        ".engine-stock-decision-card:nth-child(1)": "var(--navy-2)",
        ".engine-stock-decision-card:nth-child(2)": "var(--copper)",
        ".engine-stock-decision-card:nth-child(3)": "var(--amber)",
        ".engine-stock-decision-card:nth-child(4)": "var(--muted)",
        ".engine-finding-card:nth-child(1)": "var(--navy-2)",
        ".engine-finding-card:nth-child(2)": "var(--copper)",
        ".engine-finding-card:nth-child(3)": "var(--amber)",
    }
    for selector, color in neutral_research_rules.items():
        assert selector in editorial_skin
        rule = editorial_skin.split(selector, 1)[1].split("}", 1)[0]
        assert color in rule

    forbidden_research_colors = (
        "#4f9284",
        "#258273",
        "#0e6a5c",
        "#b64a3c",
        "#9a4036",
        "var(--up)",
        "var(--down)",
    )
    for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", editorial_skin):
        selector, declarations = match.groups()
        if ".engine" not in selector:
            continue
        if any(color in declarations for color in forbidden_research_colors):
            assert ".engine-breadth-row.is-rise" in selector or (
                ".engine-breadth-row.is-fall" in selector
            ), selector

    assert "--up:" in CSS
    assert "--down:" in CSS
    assert ".engine-breadth-row.is-rise" in CSS
    assert ".engine-breadth-row.is-fall" in CSS
    assert ".engine-action-railbutton:focus-visible" in CSS.replace(" ", "")
    assert "@media(max-width:640px)" in compact_skin
    assert "@media(prefers-reduced-motion:reduce)" in compact_skin


def test_design_guide_shell_removes_old_global_project_blocks() -> None:
    html = _render_sample_page()

    forbidden = [
        'class="topbar"',
        'class="app-toolbar"',
        'aria-label="分析参数"',
        "投研工作台",
        "20项改造清单",
        "辅助验证",
        "每日复盘报告",
        "消息渠道",
    ]
    for text in forbidden:
        assert text not in html


def test_four_modules_keep_module_owned_actions() -> None:
    html = _render_sample_page()

    for text in [
        'class="stock-form" method="get"',
        "组合风控结论",
        "分析内容",
        "研究候选",
        'href="/?code=',
    ]:
        assert text in html


def test_market_page_owns_market_decision_flow() -> None:
    html = _render_sample_page()
    market_start = html.index('id="market"')
    portfolio_start = html.index('id="portfolio"')
    market_html = html[market_start:portfolio_start]

    for text in ["每日大盘", "股票涨跌统计", "上涨/下跌", "强势板块Top5", "弱势板块Top5"]:
        assert text in market_html
    assert 'data-jump="opportunity"' not in market_html


def test_opportunity_page_combines_theme_sentiment_and_candidates() -> None:
    html = _render_sample_page()
    opportunity_start = html.index('id="opportunity"')
    opportunity_html = html[opportunity_start:]

    for text in ["板块与市场支持证据", "研究候选", "支持证据", "最大反证"]:
        assert text in opportunity_html


def test_dense_pages_use_compact_readable_layout_rules() -> None:
    assert ".portfolio-overall-summary .grid-3" in CSS
    assert "align-items:start" in CSS
    assert ".opportunity-dimension-table" in CSS
    assert "table-layout:fixed" in CSS
    assert ".cell-clamp" in CSS
    assert ".portfolio-analysis-table" in CSS
    assert ".portfolio-analysis-line span" in CSS
    assert ".market-event-card-list" in CSS
    assert "grid-template-columns:repeat(2,minmax(0,1fr))" in CSS
    assert ".opportunity-dimension-table th:nth-child(n+3)" not in CSS


def test_home_specific_grid_rules_are_retired() -> None:
    assert "#module-home > .precision-brief" not in CSS


def test_research_tape_and_mobile_shell_have_explicit_density_rules() -> None:
    for selector in [
        ".research-tape-primary",
        ".research-tape-item.secondary",
        ".research-tape-data-link",
        '.research-tape[data-gate-level="high"]',
    ]:
        assert selector in CSS
    mobile = CSS.split("@media (max-width: 680px)")[-1]
    compact_mobile = mobile.replace(" ", "")
    assert ".quick-stock-search" in mobile
    assert "grid-template-columns:minmax(0,1fr)auto" in compact_mobile
    assert ".research-tape-item.secondary" in mobile
    assert "display:none" in compact_mobile
    assert ".research-tape-data-link:focus-visible" in CSS


def test_dense_research_records_use_shared_disclosure_visuals() -> None:
    for selector in [
        ".research-overflow",
        ".research-overflow summary",
        ".candidate-overflow",
        ".portfolio-queue-overflow",
        ".portfolio-boundary-overflow",
    ]:
        assert selector in CSS
    assert "position:sticky" in CSS.replace(" ", "")
    assert ".opportunity-risk-register" in CSS


def test_data_command_center_has_operations_rail_and_mobile_ledger_rules() -> None:
    for selector in [
        ".data-readiness-brief",
        ".data-recovery-rail",
        ".data-recovery-step::before",
        ".data-impact-grid",
        ".data-source-ledger",
        ".data-ledger-card",
    ]:
        assert selector in CSS
    mobile = CSS.split("@media (max-width:680px)")[-1]
    compact_mobile = mobile.replace(" ", "")
    assert ".data-operations-grid" in mobile
    assert "grid-template-columns:1fr" in compact_mobile
    assert ".data-ledger-table" in mobile
    assert "display:block" in compact_mobile


def test_market_session_playbook_has_ruler_disclosure_and_mobile_sequence() -> None:
    for selector in [
        ".market-session-ruler",
        ".market-session-phase",
        ".market-session-heading",
        ".market-intraday-ledger",
        ".market-intraday-ledger summary:focus-visible",
    ]:
        assert selector in CSS
    mobile = CSS.split("@media (max-width:680px)")[-1]
    compact_mobile = mobile.replace(" ", "")
    assert ".market-session-ruler" in mobile
    assert ".market-session-phase" in mobile
    assert ".market-intraday-ledger .data-table" in mobile
    assert ".market-intraday-ledger .data-table th:last-child" in mobile
    assert "grid-template-columns:1fr" in compact_mobile
    assert "min-width:92px" in compact_mobile
    assert "min-width:260px" in compact_mobile
