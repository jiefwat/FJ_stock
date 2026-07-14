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
    assert "组合风控结论" in html
    assert "对应板块分析" not in html
    assert "仓位/成本分析" not in html
    assert "个股分析" in html
    assert "分析入口" in html
    assert "三情景" in html
    assert "决策条件" in html
    assert "风险反证" in html
    assert "热点机会" in html
    assert "机会总闸门" in html
    assert "证据漏斗" in html
    assert "研究候选" in html
    assert "风险排除" in html
    assert "主要数据源" not in html


def test_web_keeps_professional_modules_connected_to_existing_data() -> None:
    html = render_page(
        stock_code="600519",
        provider_name="sample",
        holdings_path="data/portfolio/holdings.csv",
    )

    assert "市场" in html
    assert "组合风控结论" in html
    assert "贵州茅台" in html
    assert "持仓/成本" in html
    assert 'href="/?code=' in html
    assert "不构成投资建议" in html


def test_web_candidate_workspace_uses_observation_actions() -> None:
    html = render_page(
        stock_code="大业股份",
        provider_name="sample",
        holdings_path="data/portfolio/holdings.csv",
    )

    assert "研究候选" in html
    assert "支持证据" in html
    assert "最大反证" in html
    assert "推荐买入" not in html
    assert 'href="/?code=' in html


def test_limit_modules_do_not_present_tencent_zero_as_real_count() -> None:
    assert _format_limit_count(0, provider_class="TencentProvider") == "未返回"
    assert _format_limit_count(12, provider_class="TencentProvider") == "12"
    assert _format_limit_count(0, provider_class="AkshareProvider") == "0"
