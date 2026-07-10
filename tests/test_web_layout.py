from stock_ts.web import render_page


def test_web_page_uses_structured_workbench_layout() -> None:
    html = render_page(stock_code="600519", holdings_path="data/portfolio/holdings.csv")

    assert 'class="app-shell"' in html
    assert 'class="sidebar"' in html
    assert 'id="module-market"' in html
    assert 'id="module-portfolio"' in html
    assert 'id="module-stock"' in html
    assert 'id="module-opportunity"' in html
    assert html.count('class="workspace-pane') == 4
    assert 'data-workspace="market"' in html
    assert 'data-workspace="portfolio"' in html
    assert 'data-workspace="stock"' in html
    assert 'data-workspace="opportunity"' in html
    assert "每日大盘" in html
    assert "我的持仓" in html
    assert "个股分析" in html
    assert "热点机会" in html
    for removed in [
        'id="module-home"',
        'id="module-sector"',
        'id="module-sentiment"',
        'id="module-screener"',
        'id="module-trading"',
        'id="module-backtest"',
        'id="module-watchlist"',
        'id="module-daily"',
        'id="module-notify"',
        'id="module-settings"',
    ]:
        assert removed not in html
    assert 'class="data-table portfolio-table"' in html
    assert "<pre>" not in html


def test_four_modules_explain_professional_data_flow() -> None:
    html = render_page(stock_code="600519", holdings_path="data/portfolio/holdings.csv")

    assert "数据链路：K线 / 资金面 / 消息面" in html
    assert "每日大盘 · 仓位闸门" in html
    assert "持仓风险处置" in html
    assert "个股三面复核" in html
    assert "热点机会 · 主题雷达" in html
    assert "板块热度" in html
    assert "情绪温度" in html
    assert "候选观察池" in html


def test_web_page_renders_visual_components_instead_of_markdown_blocks() -> None:
    html = render_page(stock_code="600519", holdings_path="data/portfolio/holdings.csv")

    assert 'class="score-bar"' in html
    assert 'class="risk-pill' in html
    assert "table-note" in html
    assert 'class="report-copy"' not in html
    assert "TDX MCP" in html
    assert "热点机会" in html


def test_portfolio_and_stock_surfaces_keep_action_content() -> None:
    html = render_page(stock_code="600519", holdings_path="data/portfolio/holdings.csv")

    assert "持仓处理队列" in html
    assert "必须先处理" in html
    assert "保护利润" in html
    assert "修复观察" in html
    assert "继续持有" in html
    assert "个股证据抽屉" in html
    assert "交易触发" in html
    assert "风险原因" in html
    assert "消息事件" in html
    assert "数据状态" in html


def test_four_module_grid_drops_home_specific_rules() -> None:
    from stock_ts.webapp.styles import CSS

    assert "#module-home > .action-desk" not in CSS
    assert "#module-home > .home-brief" not in CSS
