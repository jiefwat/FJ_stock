from stock_ts.web import render_page


def test_web_page_uses_structured_workbench_layout() -> None:
    html = render_page(stock_code="600519", holdings_path="data/portfolio/holdings.csv")

    assert 'class="app-shell"' in html
    assert 'class="sidebar"' in html
    assert 'id="module-market"' in html
    assert 'id="module-portfolio"' in html
    assert 'id="module-stock"' in html
    assert 'id="module-opportunity"' in html
    assert 'id="module-data-center"' in html
    assert html.count('class="workspace-pane') == 5
    assert 'data-workspace="market"' in html
    assert 'data-workspace="portfolio"' in html
    assert 'data-workspace="stock"' in html
    assert 'data-workspace="opportunity"' in html
    assert 'data-workspace="data-center"' in html
    assert "每日大盘" in html
    assert "我的持仓" in html
    assert "个股分析" in html
    assert "热点机会" in html
    assert "数据中台" in html
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
    assert 'class="data-table portfolio-analysis-table"' in html
    assert "<pre>" not in html


def test_four_modules_explain_professional_data_flow() -> None:
    html = render_page(stock_code="600519", holdings_path="data/portfolio/holdings.csv")

    assert "数据链路：" not in html
    assert "每日大盘" in html
    assert "持仓股票分析" in html
    assert "对应板块分析" in html
    assert "仓位/成本分析" in html
    assert "分析内容" in html
    assert "热门板块主题" in html
    assert "股票机会" in html
    assert "候选列表" in html


def test_web_page_renders_visual_components_instead_of_markdown_blocks() -> None:
    html = render_page(stock_code="600519", holdings_path="data/portfolio/holdings.csv")

    assert 'class="market-distribution-row"' in html
    assert 'class="risk-pill' in html
    assert "table-note" in html
    assert 'class="report-copy"' not in html
    assert "数据中台" in html
    assert "热点机会" in html


def test_portfolio_and_stock_surfaces_keep_action_content() -> None:
    html = render_page(stock_code="600519", holdings_path="data/portfolio/holdings.csv")

    assert "持仓股票分析" in html
    assert "趋势/量价" in html
    assert "资金/成交" in html
    assert "基本面/估值" in html
    assert "消息/公告" in html
    assert "板块/主题" in html
    assert "持仓/成本" in html
    assert "分析入口" in html
    assert "K线数据" in html
    assert "后续建议" in html
    assert "未来涨跌预测" in html


def test_four_module_grid_drops_home_specific_rules() -> None:
    from stock_ts.webapp.styles import CSS

    assert "#module-home > .action-desk" not in CSS
    assert "#module-home > .home-brief" not in CSS
