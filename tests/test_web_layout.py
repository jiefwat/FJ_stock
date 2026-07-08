from stock_ts.web import render_page


def test_web_page_uses_structured_workbench_layout() -> None:
    html = render_page(stock_code="600519", holdings_path="data/portfolio/holdings.csv")

    assert 'class="app-shell"' in html
    assert 'class="sidebar"' in html
    assert 'id="module-home"' in html
    assert 'id="module-market"' in html
    assert 'id="module-sector"' in html
    assert 'id="module-sentiment"' in html
    assert 'id="module-screener"' in html
    assert 'id="module-portfolio"' in html
    assert 'id="module-stock"' in html
    assert 'id="module-trading"' not in html
    assert 'id="module-backtest"' not in html
    assert 'id="module-watchlist"' in html
    assert 'id="module-daily"' in html
    assert 'id="module-notify"' in html
    assert 'id="module-settings"' in html
    assert 'class="data-table portfolio-table"' in html
    assert "<pre>" not in html


def test_web_page_renders_visual_components_instead_of_markdown_blocks() -> None:
    html = render_page(stock_code="600519", holdings_path="data/portfolio/holdings.csv")

    assert 'class="score-bar"' in html
    assert 'class="risk-pill' in html
    assert "table-note" in html
    assert 'class="report-copy"' not in html
    assert "已配置" in html or "待配置" in html
    assert "消息自动化" in html
    assert "每日复盘" in html


def test_web_daily_module_surfaces_latest_automated_artifact(tmp_path, monkeypatch) -> None:
    report_dir = tmp_path / "daily"
    report_dir.mkdir()
    (report_dir / "latest.md").write_text(
        "\n".join(
            [
                "# StockTS 每日深度复盘",
                "",
                "## 今日一句话",
                "",
                "- 自动报告已生成",
                "",
                "## 持仓分析",
                "",
                "- 组合先看风险。",
                "",
                "## 数据边界",
                "",
                "- 港股 06088 不在 A 股 TDX 全市场刷新范围内。",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (report_dir / "latest.status").write_text(
        "status=ok\nprovider=sample\ntrade_date=2026-06-05\ngenerated_at=2026-06-05T16:30:00\n",
        encoding="utf-8",
    )
    (report_dir / "pipeline.status").write_text(
        "status=ok\n"
        "generated_at=2026-06-05T17:00:00\n"
        "refresh=ok\n"
        "tdx_enrich=ok\n"
        "external_enrich=failed:timeout\n"
        "announcements=ok\n"
        "report=ok\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("STOCK_TS_DAILY_REPORT_DIR", str(report_dir))

    html = render_page(stock_code="600519", holdings_path="data/portfolio/holdings.csv")

    assert "最新自动日报" in html
    assert "自动报告已生成" in html
    assert "2026-06-05T16:30:00" in html
    assert "港股 06088" in html
    assert "latest.html" not in html
    assert "latest.md" not in html
    assert "Markdown" not in html
    assert "HTML" not in html
    assert "查看完整报告" in html
    assert "复制报告" in html
    assert "流水线状态" in html
    assert "外部补强" in html
    assert "failed:timeout" not in html
    assert "失败：超时" in html
    assert "公告" in html


def test_web_home_is_daily_action_desk_with_portfolio_queue_and_stock_drawer() -> None:
    html = render_page(stock_code="600519", holdings_path="data/portfolio/holdings.csv")

    assert "今日行动台" in html
    assert "先处理风险" in html
    assert "再看机会" in html
    assert "最后看数据" in html
    assert "建议仓位" in html
    assert "最大风险持仓" in html
    assert "今日机会首位" in html
    assert "数据更新时间" in html
    assert "class=\"action-desk" in html

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


def test_web_home_surfaces_commuter_decision_brief() -> None:
    html = render_page(stock_code="600519", holdings_path="data/portfolio/holdings.csv")
    home_start = html.index('id="home"')
    market_start = html.index('id="market"')
    home_html = html[home_start:market_start]

    assert "今日交易简报" in home_html
    assert "今天先防守还是进攻" in home_html
    assert "持仓先处理" in home_html
    assert "今日机会 10" in home_html
    assert "今天不要做什么" in home_html
    assert "不是买点不追" in home_html
