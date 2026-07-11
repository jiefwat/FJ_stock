from typing import Optional

from stock_ts.announcements import (
    fetch_cninfo_announcements,
    fetch_hkex_announcements,
    render_announcement_markdown,
)


def test_fetch_cninfo_announcements_parses_items_and_risk_flags() -> None:
    payload = {
        "totalAnnouncement": 2,
        "announcements": [
            {
                "secCode": "603278",
                "secName": "<em>大业股份</em>",
                "announcementTitle": "<em>大业股份</em>部分高级管理人员减持股份结果公告",
                "announcementTime": 1781107200000,
                "adjunctUrl": "finalpage/2026-06-11/1225362611.PDF",
            },
            {
                "secCode": "603278",
                "secName": "大业股份",
                "announcementTitle": "2025年年度报告摘要",
                "announcementTime": 1777910400000,
                "adjunctUrl": "finalpage/2026-05-05/report.PDF",
            },
        ],
    }

    report = fetch_cninfo_announcements(
        "603278",
        limit=5,
        post_form=lambda _url, _data, _headers: payload,
    )

    assert report.query == "603278"
    assert report.total == 2
    assert report.items[0].date == "2026-06-11"
    assert report.items[0].title == "大业股份部分高级管理人员减持股份结果公告"
    assert report.items[0].risk_flags == ["减持"]
    assert report.items[0].url.endswith("1225362611.PDF")


def test_fetch_cninfo_announcements_uses_exchange_from_code_prefix() -> None:
    captured: dict[str, str] = {}

    def fake_post(_url: str, data: dict[str, str], _headers: dict[str, str]) -> dict:
        captured.update(data)
        return {"totalAnnouncement": 0, "announcements": []}

    fetch_cninfo_announcements("300058", post_form=fake_post)

    assert captured["column"] == "szse"
    assert captured["plate"] == "sz"

    fetch_cninfo_announcements("688362", post_form=fake_post)

    assert captured["column"] == "sse"
    assert captured["plate"] == "sh"


def test_fetch_hkex_announcements_parses_pdf_items_and_financial_flags() -> None:
    def fake_hkex_open(url: str, data: Optional[bytes], _headers: dict[str, str]) -> bytes:
        if "partial.do" in url:
            return (
                b'callback({"more":"0","stockInfo":['
                b'{"stockId":147704,"code":"06088","name":"FIT HON TENG"}'
                b"]});"
            )
        assert data is not None
        assert b"stockId=147704" in data
        return b"""
        <html><body>
          <div class="total-records">Total records found: 46</div>
          <a href="/listedco/listconews/sehk/2026/0707/2026070700470.pdf">
            Monthly Return of Equity Issuer on Movements in Securities
          </a>
          <a href="/listedco/listconews/sehk/2026/0511/2026051100402.pdf">
            CERTAIN FINANCIAL INFORMATION FOR THE THREE MONTHS ENDED MARCH 31, 2026
          </a>
        </body></html>
        """

    report = fetch_hkex_announcements("06088", limit=5, open_url=fake_hkex_open)

    assert report.source == "hkexnews"
    assert report.query == "06088"
    assert report.total == 46
    assert report.items[0].date == "2026-07-07"
    assert report.items[0].url == (
        "https://www1.hkexnews.hk/listedco/listconews/sehk/2026/0707/2026070700470.pdf"
    )
    assert report.items[1].risk_flags == ["财报/业绩"]


def test_render_announcement_markdown_contains_professional_sections() -> None:
    report = fetch_cninfo_announcements(
        "603278",
        post_form=lambda _url, _data, _headers: {
            "totalAnnouncement": 1,
            "announcements": [
                {
                    "secCode": "603278",
                    "secName": "大业股份",
                    "announcementTitle": "关于收到监管工作函的公告",
                    "announcementTime": 1781107200000,
                    "adjunctUrl": "finalpage/2026-06-11/a.PDF",
                }
            ],
        },
    )

    markdown = render_announcement_markdown(report)

    assert "公告/财报事件" in markdown
    assert "风险事件" in markdown
    assert "监管" in markdown
    assert "不构成投资建议" in markdown
