from stock_ts.webapp.shell import app_script, render_app_toolbar, render_sidebar, render_topbar


def test_toolbar_locks_visible_web_source_to_tdx_mcp() -> None:
    html = render_app_toolbar(
        "603278",
        provider_name="auto",
        holdings_path="data/portfolio/holdings.csv",
    )

    assert 'name="provider" value="tdx-snapshot"' in html
    assert "TDX MCP" in html
    assert "<select" not in html
    assert "tencent" not in html
    assert "akshare" not in html
    assert "sample" not in html


def test_shell_copy_stays_compact_without_long_guidance() -> None:
    sidebar = render_sidebar()
    topbar = render_topbar("<div></div>")

    assert "从大盘判断环境" not in sidebar
    assert "current-module-desc" not in topbar
    assert "当前模块" not in topbar


def test_workspace_hash_changes_do_not_scroll_into_large_modules() -> None:
    script = app_script()

    assert "scrollIntoView" not in script
    assert "history.replaceState" in script
    assert "window.scrollTo" in script


def test_data_scroll_buttons_move_to_target_without_scroll_into_view() -> None:
    script = app_script()

    assert "document.getElementById(button.dataset.scroll)" in script
    assert "target.getBoundingClientRect().top" in script
    assert "scrollIntoView" not in script


def test_workspace_click_handler_only_binds_sidebar_navigation() -> None:
    script = app_script()

    assert "document.querySelectorAll('[data-workspace]')" not in script
    assert "document.querySelectorAll('.nav-item[data-workspace]')" in script


def test_sidebar_navigation_prevents_anchor_scroll_from_hiding_sidebar() -> None:
    script = app_script()

    assert "event.preventDefault()" in script
    assert "event.stopPropagation()" in script
    assert "keepTop()" in script
