from stock_ts.announcements import AnnouncementReport
from stock_ts.providers.sample import SampleDataProvider
from stock_ts.web import _is_public_readonly, _server_bind_address, render_page


def _html() -> str:
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


def test_web_uses_four_business_modules_and_data_center_shell() -> None:
    html = _html()

    assert "Jiewat Kaka FJ" in html
    assert "jiewat-kaka-fj.com" in html
    assert "每日大盘" in html
    assert "我的持仓" in html
    assert "个股分析" in html
    assert "热点机会" in html
    assert html.count('class="workspace-pane') == 6
    for workspace in ["market", "portfolio", "stock", "opportunity", "data-center"]:
        assert f'id="{workspace}"' in html
        assert f'href="#{workspace}"' in html
    for removed in ["看主线", "看情绪", "看复盘", "收晨报", "检查系统"]:
        assert removed not in html
    assert "function activateWorkspace" in html
    assert "history.replaceState" in html


def test_web_server_uses_deploy_env_vars(monkeypatch) -> None:
    monkeypatch.setenv("HOST", "0.0.0.0")
    monkeypatch.setenv("PORT", "9000")
    monkeypatch.setenv("STOCK_TS_PUBLIC_READONLY", "1")

    assert _server_bind_address() == ("0.0.0.0", 9000)
    assert _is_public_readonly() is True


def test_public_readonly_hides_mutating_public_controls(monkeypatch) -> None:
    monkeypatch.setenv("STOCK_TS_PUBLIC_READONLY", "1")

    html = _html()

    assert 'method="post" action="/holdings"' not in html
    assert 'method="post" action="/settings"' not in html
    assert 'method="post" action="/notification-test"' not in html
    assert 'method="post" action="/dispatch-daily"' not in html
    assert "保存持仓" not in html
    assert 'class="stock-form" method="get"' in html


def test_personal_writable_mode_keeps_portfolio_controls(monkeypatch) -> None:
    monkeypatch.setenv("STOCK_TS_PUBLIC_READONLY", "0")

    html = _html()

    assert _is_public_readonly() is False
    assert 'method="post" action="/holdings"' in html
    assert 'name="portfolio_action" value="upsert"' in html
    assert 'name="portfolio_action" value="delete"' in html
    assert "保存持仓" in html
    assert "确认删除这条持仓记录？" in html
    assert "持仓分析" in html


def test_web_shell_listens_and_routes_legacy_hashes() -> None:
    html = _html()

    assert "window.addEventListener('hashchange'" in html
    assert "'sector': 'opportunity'" in html
    assert "'screener': 'opportunity'" in html
    assert "'settings': 'account'" in html
    assert "document.querySelectorAll('[data-jump]')" in html


def test_each_workspace_contains_its_own_core_module_content() -> None:
    html = _html()

    expected = {
        "market": "股票涨跌统计",
        "portfolio": "持仓分析",
        "stock": "分析内容",
        "opportunity": "推荐股票",
    }
    for workspace, marker in expected.items():
        id_pos = html.index(f'id="{workspace}"')
        start = html.rfind('<section class="workspace-pane', 0, id_pos)
        next_workspace = html.find('<section class="workspace-pane', id_pos + 1)
        chunk = html[start:] if next_workspace == -1 else html[start:next_workspace]
        assert marker in chunk, workspace


def test_shell_has_fast_stock_search_and_copyable_action_plan() -> None:
    html = _html()

    assert 'class="quick-stock-search"' in html
    assert 'placeholder="代码 / 名称"' in html
    assert 'aria-label="快速分析个股"' in html
    assert "stockTsLastStockQuery" in html
    assert "复制今日行动" in html
    assert "data-copy-action-plan" in html
    assert "currentActionPlanText" in html
