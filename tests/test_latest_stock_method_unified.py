from __future__ import annotations

from stock_ts.models import (
    CandidateStockRawData,
    DailyBar,
    IndexQuote,
    MarketRawData,
    NewsItem,
    SectorRawData,
    StockRawData,
)
from stock_ts.providers.base import StockDataProvider
from stock_ts.report import render_stock_markdown
from stock_ts.web import render_page
from stock_ts.workflows import build_deep_stock_report, build_stock_report


class LatestMethodProvider(StockDataProvider):
    def fetch_market(self) -> MarketRawData:
        return MarketRawData(
            trade_date="2026-07-08",
            indices=[IndexQuote("000001", "上证指数", 3200, 0.4)],
            advancing=2800,
            declining=1900,
            limit_up=60,
            limit_down=8,
            top_sectors=[("机器人", 2.8)],
        )

    def fetch_stock(self, code: str) -> StockRawData:
        bars = [
            DailyBar("2026-07-01", 10, 10.4, 9.8, 10.0, 1000),
            DailyBar("2026-07-02", 10, 10.6, 9.9, 10.3, 1100),
            DailyBar("2026-07-03", 10.3, 10.8, 10.1, 10.6, 1200),
            DailyBar("2026-07-06", 10.6, 11.1, 10.5, 10.9, 1400),
            DailyBar("2026-07-07", 10.9, 11.4, 10.8, 11.2, 1700),
        ]
        return StockRawData(
            code=code,
            name="测试股份",
            bars=bars,
            news_items=[
                NewsItem("2026-07-08", "公告", "股东拟减持", "减持计划", sentiment="neutral"),
                NewsItem("2026-07-08", "快讯", "机器人订单增长", "中标大单", sentiment="neutral"),
            ],
        )

    def fetch_sectors(self) -> list[SectorRawData]:
        return [SectorRawData("机器人", 2.8, 0.7, 1.5, limit_up_count=6)]

    def fetch_candidate_universe(self):
        return [
            CandidateStockRawData(
                code="688001",
                name="测试股份",
                sector="机器人",
                bars=self.fetch_stock("688001").bars,
                turnover_rate=5.2,
                amount=120000000,
            )
        ]


def test_basic_stock_analysis_reclassifies_raw_neutral_news_with_latest_method() -> None:
    report = build_stock_report(LatestMethodProvider(), "688001")
    event = next(item for item in report.dimensions if item.name == "消息事件")
    markdown = render_stock_markdown(report)

    assert "股东拟减持" in event.evidence
    assert "机器人订单增长" in event.evidence
    assert "负面 1" in event.evidence
    assert "正面 1" in event.evidence
    assert "最新分析方法" not in markdown
    assert "消息事件" in markdown


def test_deep_stock_analysis_uses_stock_specific_news_when_no_news_csv_is_passed() -> None:
    report = build_deep_stock_report(LatestMethodProvider(), "688001")
    news_angle = next(item for item in report.angles if item.name == "新闻舆情")

    assert "消息面" in news_angle.evidence
    assert any("股东拟减持" in risk for risk in report.risks)
    assert any(round_.role == "新闻情绪分析师" for round_ in report.debate_rounds)


def test_web_stock_module_uses_latest_stock_specific_news_method(tmp_path) -> None:
    holdings = tmp_path / "holdings.csv"
    holdings.write_text(
        "code,name,shares,cost_price,sector,note\n688001,测试股份,100,10.0,机器人,测试\n",
        encoding="utf-8",
    )

    html = render_page(
        stock_code="688001",
        provider_name="tdx-snapshot",
        provider=LatestMethodProvider(),
        holdings_path=str(holdings),
    )

    assert "股东拟减持" in html
    assert "机器人订单增长" in html
    assert "消息事件" in html


def test_daily_deep_markdown_exposes_latest_method_per_stock() -> None:
    from stock_ts.deep_report import render_daily_deep_markdown
    from stock_ts.workflows import build_daily_deep_report

    report = build_daily_deep_report(LatestMethodProvider(), candidate_limit=1)
    markdown = render_daily_deep_markdown(report)

    assert "消息事件" in markdown
    assert "新闻情绪分析师" in markdown
    assert "今日动作" in markdown
    assert "股东拟减持" in markdown
