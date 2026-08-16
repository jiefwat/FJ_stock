from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from marketdesk.models import (
    FinancialHealth,
    FinancialPeriod,
    StockNewsItem,
    StockNewsSentiment,
)


def financial_period() -> FinancialPeriod:
    return FinancialPeriod(
        report_date=date(2026, 6, 30),
        report_label="2026中报",
        report_type="中报",
        revenue=90_703_000_000,
        revenue_yoy=1.47,
        net_profit=44_517_000_000,
        net_profit_yoy=-1.95,
        roe=18.2,
        gross_margin=91.3,
        operating_cash_flow_per_share=16.8,
        cash_receipts_to_revenue=98.4,
        debt_to_assets=13.1,
    )


def stock_news() -> StockNewsItem:
    return StockNewsItem(
        id="eastmoney:1",
        title="贵州茅台发布半年报",
        summary="营业收入同比增长，归母净利润小幅下降。",
        media="证券时报",
        url="https://finance.eastmoney.com/a/1.html",
        published_at=datetime(2026, 8, 15, 8, tzinfo=UTC),
        sentiment="neutral",
        hard_risk=False,
    )


def test_financial_and_news_models_accept_explicit_available_results() -> None:
    health = FinancialHealth(
        available=True,
        score=68,
        score_impact=2,
        conclusion="盈利稳定，现金回收正常",
        report_date=date(2026, 6, 30),
        risks=["利润同比小幅下降"],
        periods=[financial_period()],
    )
    sentiment = StockNewsSentiment(
        available=True,
        window_days=30,
        conclusion="近30天未见明确硬风险",
        positive_count=0,
        negative_count=0,
        neutral_count=1,
        hard_risk_count=0,
        score_impact=0,
        items=[stock_news()],
    )

    assert health.periods[0].revenue_yoy == 1.47
    assert sentiment.items[0].media == "证券时报"


@pytest.mark.parametrize(
    ("model", "payload"),
    [
        (
            FinancialHealth,
            {
                "available": True,
                "score": 80,
                "score_impact": 7,
                "conclusion": "稳健",
                "report_date": date(2026, 6, 30),
                "periods": [],
            },
        ),
        (
            StockNewsSentiment,
            {
                "available": True,
                "conclusion": "有风险",
                "score_impact": -7,
                "items": [],
            },
        ),
    ],
)
def test_financial_and_news_score_impacts_are_bounded(model, payload) -> None:
    with pytest.raises(ValidationError):
        model(**payload)


def test_stock_news_rejects_non_http_source_url() -> None:
    with pytest.raises(ValidationError, match="http"):
        stock_news().model_copy(update={"url": "javascript:alert(1)"}, deep=True).__class__(
            **stock_news().model_dump(exclude={"url"}),
            url="javascript:alert(1)",
        )


def test_unavailable_results_preserve_the_failure_without_fake_scores() -> None:
    health = FinancialHealth(
        available=False,
        conclusion="财报暂不可用",
        error="upstream timeout",
    )
    sentiment = StockNewsSentiment(
        available=False,
        conclusion="新闻暂不可用",
        error="upstream timeout",
    )

    assert health.score is None
    assert health.score_impact == 0
    assert health.periods == []
    assert sentiment.score_impact == 0
    assert sentiment.items == []
