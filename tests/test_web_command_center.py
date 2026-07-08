from stock_ts.announcements import AnnouncementReport
from stock_ts.providers.sample import SampleDataProvider
from stock_ts.web import render_page


def test_web_renders_research_command_center_and_evidence_rail() -> None:
    html = render_page(
        stock_code="大业股份",
        provider_name="sample",
        provider=SampleDataProvider(),
        announcement_fetcher=lambda query, limit=5: AnnouncementReport(
            query=query,
            total=0,
            items=[],
            risk_events=[],
        ),
    )

    assert "A股大盘" in html
    assert "今日大盘" in html
    assert "我的持仓" in html
    assert "个股分析" in html
    assert "今天先做什么" not in html
