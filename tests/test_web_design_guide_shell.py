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


def test_design_guide_shell_uses_eleven_clean_modules() -> None:
    html = _render_sample_page()

    for module_id in [
        "home",
        "market",
        "sector",
        "sentiment",
        "screener",
        "stock",
        "portfolio",
        "watchlist",
        "daily",
        "notify",
        "settings",
    ]:
        assert f'id="{module_id}"' in html
        assert f'href="#{module_id}"' in html

    for label in [
        "今日行动",
        "看大盘",
        "看主线",
        "看情绪",
        "找机会",
        "分析个股",
        "处理持仓",
        "自选研究",
        "看复盘",
        "收晨报",
        "检查系统",
    ]:
        assert label in html


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
        "板块分析",
        "持仓分析",
    ]
    for text in forbidden:
        assert text not in html


def test_design_guide_shell_keeps_module_owned_actions() -> None:
    html = _render_sample_page()

    for text in [
        'data-action="filter-candidates"',
        'data-action="add-holding"',
        'data-action="add-watch-form"',
        "data-copy-report",
        'data-action="send-dry-run"',
        "保存个股计划",
    ]:
        assert text in html


def test_home_page_is_action_overview_with_expert_market_board() -> None:
    html = _render_sample_page()

    home_start = html.index('id="home"')
    market_start = html.index('id="market"')
    home_html = html[home_start:market_start]

    for text in [
        "今日先做这三件事",
        "核心数据",
        "分析个股",
        "找机会",
        "上涨 / 下跌 / 平盘",
        "领涨板块 Top 5",
        "领跌板块 Top 5",
        "强势股票 20",
        "风险股票 20",
    ]:
        assert text in home_html

    for duplicated in [
        "指数快照",
    ]:
        assert duplicated not in home_html


def test_home_precision_summary_spans_full_grid_width() -> None:
    html = _render_sample_page()
    home_start = html.index('id="home"')
    market_start = html.index('id="market"')
    home_html = html[home_start:market_start]

    assert 'id="module-home"' in home_html
    assert "precision-brief" not in home_html
    assert "#module-home > .precision-brief" not in CSS
    assert "grid-column: 1 / -1" in CSS
    assert "#module-home > .module-header + .panel" in CSS


def test_market_page_owns_market_breadth_and_ranked_reasons() -> None:
    html = _render_sample_page()

    market_start = html.index('id="market"')
    sector_start = html.index('id="sector"')
    market_html = html[market_start:sector_start]

    for text in [
        "A股大盘",
        "关键证据",
        "上涨/下跌",
        "领涨板块 Top 5",
        "市场分析维度",
        "涨停",
        "跌停",
    ]:
        assert text in market_html


def test_market_page_has_distinct_title_and_actions() -> None:
    html = _render_sample_page()

    market_start = html.index('id="market"')
    sector_start = html.index('id="sector"')
    market_html = html[market_start:sector_start]

    assert "A股大盘" in market_html
    assert "看板块" in market_html
    assert 'data-jump="sector"' in market_html
    assert 'data-jump="screener"' in market_html
    assert "市场分析维度" in market_html
    assert "机会与风险" in market_html


def test_market_page_has_clear_decision_flow() -> None:
    html = _render_sample_page()

    market_start = html.index('id="market"')
    sector_start = html.index('id="sector"')
    market_html = html[market_start:sector_start]

    for text in [
        "市场结论",
        "判断依据",
        "关键证据",
        "指数",
        "领涨板块 Top 5",
        "机会 / 风险 / 明日",
        "为什么",
    ]:
        assert text in market_html


def test_sector_page_explains_theme_strength_and_next_checks() -> None:
    html = _render_sample_page()

    sector_start = html.index('id="sector"')
    sentiment_start = html.index('id="sentiment"')
    sector_html = html[sector_start:sentiment_start]

    for text in [
        "板块结论",
        "为什么强",
        "持续性判断",
        "代表个股",
        "风险点",
        "下一步验证",
        "操作策略",
    ]:
        assert text in sector_html


def test_sentiment_page_explains_limit_up_limit_down_and_risk_actions() -> None:
    html = _render_sample_page()

    sentiment_start = html.index('id="sentiment"')
    screener_start = html.index('id="screener"')
    sentiment_html = html[sentiment_start:screener_start]

    for text in [
        "情绪结论",
        "涨停分析",
        "跌停风险",
        "风险提醒",
        "下一步验证",
        "风险处理",
        "强势样本分析",
        "跌停明细",
        "涨停原因",
        "跌停原因",
    ]:
        assert text in sentiment_html


def test_paused_screener_still_shows_observable_candidates() -> None:
    html = _render_sample_page()

    screener_start = html.index('id="screener"')
    stock_start = html.index('id="stock"')
    screener_html = html[screener_start:stock_start]

    assert "候选观察名单" in screener_html
    assert ">分析</a>" in screener_html


def test_screener_explains_market_coverage_and_scoring_angles() -> None:
    html = _render_sample_page()

    screener_start = html.index('id="screener"')
    stock_start = html.index('id="stock"')
    screener_html = html[screener_start:stock_start]

    for text in [
        "扫描范围",
        "当前快照覆盖",
        "覆盖完整性",
        "覆盖不足",
        "策略地图",
        "资金抱团",
        "市场热度",
        "强势突破",
        "超跌反弹",
        "风险排查",
        "入选理由",
        "风险提醒",
        "验证条件",
    ]:
        assert text in screener_html


def test_client_actions_have_visible_feedback_handlers() -> None:
    html = _render_sample_page()

    for text in [
        "function showToast",
        "data-toast",
        "data-copy-report",
        "save-stock-plan",
        "send-dry-run",
    ]:
        assert text in html
