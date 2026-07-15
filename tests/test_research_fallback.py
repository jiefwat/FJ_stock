from dataclasses import replace

from stock_ts.models import NewsItem
from stock_ts.providers.sample import SampleDataProvider
from stock_ts.research_engine import ResearchContext
from stock_ts.research_fallback import build_local_research


class LocalFixtureProvider(SampleDataProvider):
    def fetch_stock(self, code: str):
        raw = super().fetch_stock(code)
        return replace(
            raw,
            fundamental_metrics={"roe": 12.4, "revenue_yoy": 8.6, "net_profit_yoy": -3.2},
            valuation={"pe_ttm": raw.pe_ttm, "pb": 2.4},
            fund_flow_detail={"main_net_inflow": raw.fund_flow},
            news_items=[
                NewsItem(
                    date="2026-07-15",
                    source="公开新闻",
                    title="公司披露经营进展",
                    summary="收入保持增长，利润仍待修复。",
                )
            ],
            announcements=[{"title": "2026年半年度业绩预告", "date": "2026-07-15"}],
        )


def test_local_stock_fallback_keeps_available_dimensions_and_marks_gaps() -> None:
    result = build_local_research(
        "stock",
        ResearchContext(code="603278", name="大业股份"),
        provider=LocalFixtureProvider(),
    )

    payload = result.to_public_dict()
    assert payload["status"] == "partial"
    assert payload["delivery"] == "local_fallback"
    assert payload["data_label"] == "本地证据"
    assert payload["verdict"]
    assert len(payload["findings"]) >= 2
    assert len(payload["module_items"]) == 8
    assert {item["label"] for item in payload["module_items"]} >= {
        "财务质量",
        "行情资金",
        "公告事项",
    }
    assert "机构预期" in payload["missing_sections"]
