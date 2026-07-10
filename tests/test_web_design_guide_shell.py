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


def test_design_guide_shell_uses_four_clean_modules() -> None:
    html = _render_sample_page()

    for module_id in ["market", "portfolio", "stock", "opportunity"]:
        assert f'id="{module_id}"' in html
        assert f'href="#{module_id}"' in html
    for label in ["每日大盘", "我的持仓", "个股分析", "热点机会"]:
        assert label in html
    assert html.count('class="workspace-pane') == 4


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
        'data-action="add-holding"',
        'class="stock-form" method="get"',
        "个股三面复核",
        "候选观察池",
        "href='/?code=",
    ]:
        assert text in html


def test_market_page_owns_market_decision_flow() -> None:
    html = _render_sample_page()
    market_start = html.index('id="market"')
    portfolio_start = html.index('id="portfolio"')
    market_html = html[market_start:portfolio_start]

    for text in ["每日大盘", "仓位闸门", "关键证据", "上涨/下跌", "指数", "机会与风险"]:
        assert text in market_html
    assert 'data-jump="opportunity"' in market_html


def test_opportunity_page_combines_theme_sentiment_and_candidates() -> None:
    html = _render_sample_page()
    opportunity_start = html.index('id="opportunity"')
    opportunity_html = html[opportunity_start:]

    for text in [
        "热点机会 · 主题雷达",
        "板块热度",
        "情绪温度",
        "候选观察池",
        "赚钱效应",
        "亏钱效应",
        "入选理由",
    ]:
        assert text in opportunity_html


def test_home_specific_grid_rules_are_retired() -> None:
    assert "#module-home > .precision-brief" not in CSS
