from stock_ts.announcements import AnnouncementReport
from stock_ts.providers.sample import SampleDataProvider
from stock_ts.web import render_page


def test_web_uses_professional_product_copy() -> None:
    html = render_page(
        stock_code="大业股份",
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

    assert "href='/?code=" in html
    assert "每日大盘" in html
    assert "今天先做什么" not in html
    assert "核心入口" not in html
    assert "Jiewat Kaka FJ" in html
    assert "一键分析" not in html
    assert "再看个股执行" not in html
    assert "去处理" not in html
    assert "进入模块" not in html
