from stock_ts.data_quality import DataSourceAttempt, summarize_data_quality


def test_data_quality_marks_fallback_and_missing_fields() -> None:
    summary = summarize_data_quality(
        primary_source="tushare.daily",
        payload={"bars": [{"close": 10}], "news_items": []},
        required_fields=["bars", "valuation", "fund_flow_detail", "news_items"],
        attempts=[
            DataSourceAttempt("tushare", ok=True, fields=["bars"]),
            DataSourceAttempt("akshare", ok=False, reason="timeout"),
        ],
    )

    assert summary.primary_source == "tushare.daily"
    assert summary.data_quality == "partial"
    assert summary.fallback_from == ["akshare"]
    assert summary.missing_fields == ["valuation", "fund_flow_detail", "news_items"]
    assert "partial" in summary.to_payload()["data_quality"]


def test_data_quality_is_good_when_required_fields_are_present() -> None:
    summary = summarize_data_quality(
        primary_source="multi-source",
        payload={"bars": [1], "valuation": {"pe_ttm": 18}, "news_items": [{"title": "x"}]},
        required_fields=["bars", "valuation", "news_items"],
        attempts=[DataSourceAttempt("tushare", ok=True), DataSourceAttempt("akshare", ok=True)],
    )

    assert summary.data_quality == "good"
    assert summary.missing_fields == []
    assert summary.fallback_from == []
