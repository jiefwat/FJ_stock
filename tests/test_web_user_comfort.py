from stock_ts.announcements import AnnouncementReport
from stock_ts.providers.sample import SampleDataProvider
from stock_ts.web import render_page


def test_overview_guides_user_workflow_and_fast_jumps() -> None:
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

    assert "今天先做什么" not in html
    assert "核心入口" not in html
    assert "今日大盘" in html
    assert "主线板块" in html
    assert "我的持仓" in html
    assert "个股分析" in html
    assert 'data-jump="portfolio"' in html
    assert 'data-jump="stock"' in html
    assert 'data-jump="status"' not in html
    assert "A-Share Desk" not in html
    assert "先确认今天市场能不能做，以及风险偏好处在什么位置。" not in html
    assert "document.querySelectorAll('[data-jump]')" in html
