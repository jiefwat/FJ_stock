from datetime import UTC, datetime

from marketdesk.models import Freshness
from marketdesk.providers.cn_evidence import AshareEvidenceProvider

NOW = datetime(2026, 7, 28, 8, tzinfo=UTC)


def test_cninfo_org_map_and_announcements_are_source_attributed() -> None:
    provider = AshareEvidenceProvider()
    org_map = provider.normalize_cninfo_org_map(
        {"stockList": [{"code": "601318", "orgId": "9900002221"}]}
    )
    documents = provider.normalize_cninfo_announcements(
        {
            "announcements": [
                {
                    "announcementId": "1224373503",
                    "announcementTitle": "2025 年年度权益分派实施公告",
                    "announcementTypeName": "权益分派",
                    "announcementTime": 1_753_660_800_000,
                }
            ]
        },
        "SH.601318",
        NOW,
    )

    assert org_map == {"601318": "9900002221"}
    assert documents[0].kind == "filing"
    assert documents[0].publisher == "巨潮资讯"
    assert documents[0].published_at.tzinfo is not None
    assert documents[0].source.provider == "cninfo"
    assert documents[0].url.endswith("annoId=1224373503")


def test_eastmoney_reports_keep_rating_and_numeric_eps_only() -> None:
    provider = AshareEvidenceProvider()

    documents = provider.normalize_research_reports(
        {
            "data": [
                {
                    "infoCode": "AP202607281234",
                    "title": "渠道韧性延续，长期价值稳固",
                    "publishDate": "2026-07-28 00:00:00",
                    "orgSName": "测试证券",
                    "emRatingName": "增持",
                    "indvInduName": "白酒",
                    "predictThisYearEps": "68.20",
                    "predictNextYearEps": "--",
                    "predictNextTwoYearEps": 78.4,
                }
            ]
        },
        "SH.600519",
        NOW,
    )

    assert documents[0].kind == "research"
    assert documents[0].rating == "增持"
    assert documents[0].eps_forecasts == {"current_year": 68.2, "year_plus_2": 78.4}
    assert documents[0].source.provider == "eastmoney_report"


def test_themes_and_dragon_tiger_payloads_support_dict_or_list_rows() -> None:
    provider = AshareEvidenceProvider()
    themes = provider.normalize_themes(
        {
            "data": {
                "diff": {
                    "0": {"f12": "BK0896", "f14": "酿酒概念", "f3": 1.8, "f128": "贵州茅台"}
                }
            }
        },
        NOW,
    )
    anomalies = provider.normalize_dragon_tiger(
        {
            "result": {
                "data": [
                    {
                        "SECURITY_CODE": "002475",
                        "SECURITY_NAME_ABBR": "立讯精密",
                        "TRADE_DATE": "2026-07-25 00:00:00",
                        "EXPLANATION": "日涨幅偏离值达 7%",
                        "CLOSE_PRICE": 42.5,
                        "CHANGE_RATE": 9.99,
                        "BILLBOARD_NET_AMT": 120_000_000,
                        "BILLBOARD_BUY_AMT": 350_000_000,
                        "BILLBOARD_SELL_AMT": 230_000_000,
                        "TURNOVERRATE": 8.5,
                    }
                ]
            }
        },
        NOW,
    )

    assert themes[0].name == "酿酒概念"
    assert themes[0].source.capability == "themes"
    assert anomalies[0].symbol == "SZ.002475"
    assert anomalies[0].net_buy == 120_000_000
    assert anomalies[0].source.provider == "eastmoney_datacenter"


def test_cls_payload_normalization_skips_invalid_rows_and_builds_signed_query() -> None:
    provider = AshareEvidenceProvider()
    params = provider.cls_signed_params(20)
    events = provider.normalize_cls_events(
        {
            "data": {
                "roll_data": [
                    {
                        "id": 123,
                        "title": "政策支持设备更新",
                        "content": "多部门部署新一轮设备更新。",
                        "ctime": 1_753_689_600,
                    },
                    {"id": 124, "title": "无时间记录", "ctime": None},
                ]
            }
        },
        NOW,
    )

    assert len(params["sign"]) == 32
    assert params["rn"] == "20"
    assert len(events) == 1
    assert events[0].source == "财联社电报"
    assert events[0].published_at.tzinfo is not None
    assert events[0].url == "https://www.cls.cn/detail/123"


def test_empty_payloads_are_valid_empty_collections() -> None:
    provider = AshareEvidenceProvider()

    assert provider.normalize_cninfo_announcements({}, "SH.600519", NOW) == []
    assert provider.normalize_research_reports({}, "SH.600519", NOW) == []
    assert provider.normalize_themes({}, NOW) == []
    assert provider.normalize_dragon_tiger({}, NOW) == []
    assert provider.normalize_cls_events({}, NOW) == []


def test_old_document_source_is_marked_stale() -> None:
    provider = AshareEvidenceProvider()
    documents = provider.normalize_cninfo_announcements(
        {
            "announcements": [
                {
                    "announcementId": "old",
                    "announcementTitle": "历史公告",
                    "announcementTypeName": "其他",
                    "announcementTime": 1_577_836_800_000,
                }
            ]
        },
        "SH.600519",
        NOW,
    )

    assert documents[0].source.freshness == Freshness.STALE
