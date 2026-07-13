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
    assert "grid-template-columns:1fr" in compact_mobile
