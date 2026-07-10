from stock_ts.web import render_page


def test_web_resolves_chinese_name_and_renders_professional_deep_sections() -> None:
    html = render_page(
        stock_code="大业股份",
        provider_name="sample",
        holdings_path="data/portfolio/holdings.csv",
    )

    assert "大业股份" in html
    assert "603278" in html
    assert "示例股票（大业股份）" not in html
    assert "个股分析" in html
    assert "综合机会评分" in html
    assert "多轮对抗" not in html
    assert "失效" in html
    assert "数据状态" in html
    assert "TDX MCP" in html
    assert "行情日期早于大盘交易日" not in html


def test_web_topbar_keeps_provider_copy_compact() -> None:
    html = render_page(
        stock_code="600519",
        provider_name="sample",
        holdings_path="data/portfolio/holdings.csv",
    )

    assert "数据源" in html
    assert "TDX MCP" in html
    assert "请求数据源" not in html
    assert "实际 Provider" not in html
    assert "真实执行时使用的数据适配器" not in html
