from stock_ts.announcements import AnnouncementReport
from stock_ts.providers.sample import SampleDataProvider
from stock_ts.web import _is_public_readonly, _server_bind_address, render_page


def test_web_uses_interactive_app_shell_not_long_static_report() -> None:
    html = render_page(
        stock_code="大业股份",
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

    assert "A股大盘" in html
    assert "Jiewat Kaka FJ" in html
    assert "jiewat-kaka-fj.com" in html
    assert "看主线" in html
    assert "涨停板" in html
    assert "跌停家数" in html
    assert "找机会" in html
    assert "分析个股" in html
    assert "处理持仓" in html
    assert "看复盘" in html
    assert "收晨报" in html
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
    assert "workspace-pane active" in html
    assert "function activateWorkspace" in html
    assert "分析参数" not in html
    assert "TDX MCP" in html
    assert ">分析</a>" in html
    assert "history.replaceState" in html


def test_web_server_uses_deploy_env_vars(monkeypatch) -> None:
    monkeypatch.setenv("HOST", "0.0.0.0")
    monkeypatch.setenv("PORT", "9000")
    monkeypatch.setenv("STOCK_TS_PUBLIC_READONLY", "1")

    assert _server_bind_address() == ("0.0.0.0", 9000)
    assert _is_public_readonly() is True


def test_public_readonly_hides_mutating_public_controls(monkeypatch) -> None:
    monkeypatch.setenv("STOCK_TS_PUBLIC_READONLY", "1")

    html = render_page(
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

    assert "线上安全模式" in html
    assert "服务器定时发送" in html
    assert 'method="post" action="/holdings"' not in html
    assert 'method="post" action="/settings"' not in html
    assert 'method="post" action="/notification-test"' not in html
    assert 'method="post" action="/dispatch-daily"' not in html
    assert "保存持仓" not in html
    assert "保存配置" not in html
    assert "发送测试消息" not in html
    assert "发送今日复盘" not in html
    assert 'class="danger-button"' not in html
    assert "确认删除这条持仓记录？" not in html
    assert "个股分析" in html


def test_personal_writable_mode_shows_mutating_controls(monkeypatch) -> None:
    monkeypatch.setenv("STOCK_TS_PUBLIC_READONLY", "0")

    html = render_page(
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

    assert _is_public_readonly() is False
    assert "线上安全模式" not in html
    assert 'method="post" action="/holdings"' in html
    assert 'name="portfolio_action" value="upsert"' in html
    assert 'name="portfolio_action" value="delete"' in html
    assert 'method="post" action="/settings"' in html
    assert 'method="post" action="/notification-test"' in html
    assert 'method="post" action="/dispatch-daily"' in html
    assert "保存持仓" in html
    assert "保存配置" in html
    assert "发送测试消息" in html
    assert "发送今日复盘" in html
    assert "dry-run 复盘" not in html
    assert "确认删除这条持仓记录？" in html


def test_public_readonly_still_feels_like_usable_data_software(monkeypatch) -> None:
    monkeypatch.setenv("STOCK_TS_PUBLIC_READONLY", "1")

    html = render_page(
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

    assert "配置、测试发送和正式发送按钮已隐藏" not in html
    assert "线上页面不会保存凭证，也不会向外部通道发送消息" not in html
    assert "公开只读模式" not in html
    assert "邮件日报" in html
    assert 'data-action="send-dry-run"' in html
    assert "data-copy-report" in html
    assert 'data-action="filter-candidates"' in html
    assert 'class="stock-form" method="get"' in html


def test_web_shell_listens_to_hash_changes_for_workspace_routing() -> None:
    html = render_page(
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

    assert "window.addEventListener('hashchange'" in html


def test_web_shell_sidebar_routes_are_linkable_without_js() -> None:
    html = render_page(
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

    assert 'href="#market"' in html
    assert 'href="#portfolio"' in html
    assert 'href="#settings"' in html


def test_web_shell_bootstraps_even_if_domcontentloaded_already_fired() -> None:
    html = render_page(
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

    assert "document.readyState === 'loading'" in html


def test_research_workbench_is_removed_from_market_workspace() -> None:
    html = render_page(
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

    assert "投研工作台" not in html


def test_each_workspace_contains_its_own_core_module_content() -> None:
    html = render_page(
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

    expected = {
        "home": "今日行动台",
        "market": "A股大盘",
        "sector": "主线板块",
        "sentiment": "涨跌停情绪",
        "screener": "智能选股",
        "stock": "证据链",
        "portfolio": "处理优先级",
        "watchlist": "添加自选",
        "daily": "每日复盘",
        "notify": "消息自动化",
        "settings": "数据质量",
    }
    for workspace, marker in expected.items():
        id_pos = html.index(f'id="{workspace}"')
        start = html.rfind('<section class="workspace-pane', 0, id_pos)
        next_workspace = html.find('<section class="workspace-pane', id_pos + 1)
        chunk = html[start:] if next_workspace == -1 else html[start:next_workspace]
        assert marker in chunk, workspace


def test_engineering_refactor_checklist_is_removed_from_product_page() -> None:
    html = render_page(
        stock_code="600519",
        provider_name="sample",
        provider=SampleDataProvider(),
        holdings_path="data/portfolio/holdings.csv",
    )

    assert "20项改造清单" not in html


def test_global_code_switch_toolbar_is_removed_from_all_workspaces() -> None:
    html = render_page(
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

    assert 'aria-label="分析参数"' not in html
    assert 'class="app-toolbar"' not in html


def test_shell_uses_task_navigation_and_global_data_freshness_bar() -> None:
    html = render_page(
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

    for label in [
        "今日行动",
        "看大盘",
        "看主线",
        "看情绪",
        "找机会",
        "分析个股",
        "处理持仓",
        "收晨报",
    ]:
        assert label in html
    assert "首页总览" not in html
    assert "系统设置" not in html

    assert 'class="freshness-bar"' in html
    assert "交易日" in html
    assert "行情" in html
    assert "K线/资金/新闻/公告" in html
    assert "数据状态" in html
    assert "TDX MCP" in html


def test_shell_has_fast_stock_search_and_copyable_action_plan() -> None:
    html = render_page(
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

    assert 'class="quick-stock-search"' in html
    assert 'placeholder="代码 / 名称"' in html
    assert 'aria-label="快速分析个股"' in html
    assert "stockTsLastStockQuery" in html
    assert "分析个股" in html

    assert "复制今日行动" in html
    assert "data-copy-action-plan" in html
    assert "currentActionPlanText" in html
