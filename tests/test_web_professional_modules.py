from stock_ts.web import _format_limit_count, render_page


def test_web_renders_professional_four_module_framework() -> None:
    html = render_page(
        stock_code="大业股份",
        provider_name="sample",
        holdings_path="data/portfolio/holdings.csv",
    )

    assert "每日大盘" in html
    assert "股票涨跌统计" in html
    assert "我的持仓" in html
    assert "持仓股票分析" in html
    assert "对应板块分析" in html
    assert "仓位/成本分析" in html
    assert "个股分析" in html
    assert "分析入口" in html
    assert "未来涨跌预测" in html
    assert "热点机会" in html
    assert "热门板块主题" in html
    assert "热门板块主题" in html
    assert "股票机会" in html
    assert "股票机会" in html
    assert "主要数据源" not in html


def test_web_keeps_professional_modules_connected_to_existing_data() -> None:
    html = render_page(
        stock_code="600519",
        provider_name="sample",
        holdings_path="data/portfolio/holdings.csv",
    )

    assert "市场" in html
    assert "持仓股票分析" in html
    assert "贵州茅台" in html
    assert "持仓/成本" in html
    assert 'href="/?code=' in html
    assert "不构成投资建议" not in html


def test_web_candidate_workspace_uses_observation_actions() -> None:
    html = render_page(
        stock_code="大业股份",
        provider_name="sample",
        holdings_path="data/portfolio/holdings.csv",
    )

    assert "股票机会" in html
    assert "原因" in html
    assert "进入个股分析" in html
    assert 'href="/?code=' in html


def test_limit_modules_do_not_present_tencent_zero_as_real_count() -> None:
    assert _format_limit_count(0, provider_class="TencentProvider") == "未返回"
    assert _format_limit_count(12, provider_class="TencentProvider") == "12"
    assert _format_limit_count(0, provider_class="AkshareProvider") == "0"
