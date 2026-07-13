from stock_ts.announcements import AnnouncementItem, AnnouncementReport
from stock_ts.professional_research import (
    build_event_radar,
    build_technical_profile,
    render_professional_appendix,
)
from stock_ts.providers.sample import SampleDataProvider
from stock_ts.web import render_page


def test_technical_profile_builds_levels_and_trade_structure():
    raw = SampleDataProvider().fetch_stock("603278")

    profile = build_technical_profile(raw)

    assert profile.support < profile.resistance
    assert profile.invalid_line < raw.bars[-1].close
    assert profile.ma5 is not None
    assert profile.volume_ratio > 0
    assert "支撑" in profile.structure
    assert profile.checkpoints


def test_event_radar_scores_title_risks_and_review_actions():
    report = AnnouncementReport(
        query="603278",
        total=2,
        items=[
            AnnouncementItem(
                code="603278",
                name="大业股份",
                title="部分高级管理人员减持股份结果公告",
                date="2026-06-11",
                url="http://example.com/a.pdf",
                risk_flags=["减持"],
            ),
            AnnouncementItem(
                code="603278",
                name="大业股份",
                title="年度业绩说明会公告",
                date="2026-06-05",
                url="http://example.com/b.pdf",
                risk_flags=[],
            ),
        ],
        risk_events=[],
    )

    radar = build_event_radar(report)

    assert radar.risk_score >= 65
    assert radar.gate == "事件需复核"
    assert "减持" in radar.key_events[0]
    assert any("PDF" in action for action in radar.review_actions)


def test_professional_appendix_renders_technical_and_event_evidence():
    raw = SampleDataProvider().fetch_stock("603278")
    technical = build_technical_profile(raw)
    announcements = AnnouncementReport(
        query="603278",
        total=1,
        items=[
            AnnouncementItem(
                code="603278",
                name="大业股份",
                title="部分高级管理人员减持股份结果公告",
                date="2026-06-11",
                url="http://example.com/a.pdf",
                risk_flags=["减持"],
            )
        ],
        risk_events=[],
    )
    radar = build_event_radar(announcements)

    markdown = render_professional_appendix(technical, radar, announcements)

    assert "盘口技术结构" in markdown
    assert "公告事件雷达" in markdown
    assert "减持股份结果公告" in markdown


def test_web_renders_professional_technical_and_announcement_sections():
    report = AnnouncementReport(
        query="603278",
        total=1,
        items=[
            AnnouncementItem(
                code="603278",
                name="大业股份",
                title="部分高级管理人员减持股份结果公告",
                date="2026-06-11",
                url="http://example.com/a.pdf",
                risk_flags=["减持"],
            )
        ],
        risk_events=[],
    )

    html = render_page(
        stock_code="大业股份",
        provider_name="sample",
        provider=SampleDataProvider(),
        announcement_fetcher=lambda query, limit=5: report,
    )

    assert "分析内容" in html
    assert "消息/公告" in html
    assert "减持股份结果公告" in html
    assert "风险登记表" in html
    assert "仓位与执行边界" in html
    assert "禁止动作" in html
