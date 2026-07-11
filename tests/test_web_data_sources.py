from stock_ts.web import render_page


def test_web_renders_research_data_flow_without_source_matrix_noise() -> None:
    html = render_page(
        stock_code="大业股份",
        provider_name="sample",
        holdings_path="/Users/fangjie/Documents/StockTs/data/portfolio/holdings.csv",
    )

    assert "数据中台" in html
    assert "主要数据源" not in html
    assert "数据链路：" not in html
    assert "K线行情" in html
    assert "资金面" in html
    assert "消息面" in html
    assert "热点机会" in html


def test_removed_settings_module_does_not_echo_secrets(tmp_path, monkeypatch) -> None:
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

    assert 'method="post" action="/settings"' not in html
    assert "secret-password" not in html
    assert "https://example.com/hook" not in html
    assert "demo@example.com" not in html
