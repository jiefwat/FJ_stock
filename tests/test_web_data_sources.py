from stock_ts.web import render_page


def test_web_renders_multi_source_matrix_with_skills_and_mcp() -> None:
    html = render_page(
        stock_code="大业股份",
        provider_name="sample",
        holdings_path="/Users/fangjie/Documents/StockTs/data/portfolio/holdings.csv",
    )

    assert "TDX MCP" in html
    assert "主要数据源" not in html
    assert "Tencent 行情" in html
    assert "数据源路由" in html
    assert "AKShare" in html
    assert "智能选股" in html
    assert "涨跌停情绪" in html


def test_web_status_page_renders_editable_settings_form_without_secret_echo(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        'STOCK_TS_PROVIDER="auto"\n'
        'EMAIL_SENDER="demo@example.com"\n'
        'EMAIL_PASSWORD="secret-password"\n'
        'WECHAT_WEBHOOK_URL="https://example.com/hook"\n',
        encoding="utf-8",
    )

    html = render_page(
        stock_code="大业股份",
        provider_name="sample",
        holdings_path="/Users/fangjie/Documents/StockTs/data/portfolio/holdings.csv",
    )

    assert 'method="post" action="/settings"' in html
    assert "保存配置" in html
    assert 'name="settings_provider"' in html
    assert 'name="email_sender"' in html
    assert 'name="email_password"' in html
    assert 'name="wechat_webhook_url"' in html
    assert 'name="feishu_webhook_url"' in html
    assert 'name="itick_api_key"' in html
    assert 'name="notification_report_channels"' in html
    assert 'name="notification_report_style"' in html
    assert 'method="post" action="/notification-test"' in html
    assert 'method="post" action="/dispatch-daily"' in html
    assert "发送测试消息" in html
    assert "发送今日复盘" in html
    assert "dry-run 复盘" not in html
    assert "消息自动化" in html
    assert "渠道配置" in html
    assert "测试" in html
    assert "发送" in html
    assert "企业微信" in html
    assert "待配置" in html or "已配置" in html
    assert ".env" not in html
    assert 'value="demo@example.com"' in html
    assert "secret-password" not in html
    assert "https://example.com/hook" not in html
    assert "old-itick" not in html


def test_web_status_page_explains_email_password_and_dry_run_requirements(
    tmp_path, monkeypatch
) -> None:
    for key in ["SMTP_USER", "SMTP_FROM", "SMTP_PASSWORD", "EMAIL_SENDER", "EMAIL_PASSWORD"]:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        'EMAIL_SENDER="demo@example.com"\nNOTIFICATION_REPORT_CHANNELS="email"\n',
        encoding="utf-8",
    )

    html = render_page(
        stock_code="大业股份",
        provider_name="sample",
        holdings_path="/Users/fangjie/Documents/StockTs/data/portfolio/holdings.csv",
    )

    assert "缺邮箱授权码" in html
    assert "dry-run 不会真实发送" in html
