from __future__ import annotations

from stock_ts.research_evidence import normalize_capability_rows


def test_finance_skips_identity_and_keeps_financial_periods() -> None:
    raw = {
        "datas": [
            {
                "股票代码": "603278",
                "股票简称": "大业股份",
                "最新价": 8.61,
                "涨跌幅": "1.06%",
                "营业收入[2025]": 5_100_000_000,
                "营业收入[2024]": 4_700_000_000,
                "归母净利润[2025]": 162_000_000,
                "经营现金流[2025]": 91_000_000,
                "净资产收益率ROE[2025]": "7.8%",
            }
        ]
    }

    rows = normalize_capability_rows("finance", raw)

    labels = [fact.label for fact in rows[0]]
    assert "股票代码" not in labels
    assert "股票简称" not in labels
    assert "最新价" not in labels
    assert labels[:4] == [
        "营业收入[2025]",
        "归母净利润[2025]",
        "经营现金流[2025]",
        "净资产收益率ROE[2025]",
    ]
    assert "营业收入[2024]" in labels
    assert rows[0][0].value == "51.00 亿"


def test_identity_only_consensus_is_semantically_empty() -> None:
    raw = {
        "datas": [
            {"股票代码": "603278", "股票简称": "大业股份", "最新价": 8.61}
        ]
    }

    assert normalize_capability_rows("consensus", raw) == ()


def test_business_keeps_products_scope_and_competitors() -> None:
    raw = {
        "datas": [
            {
                "股票代码": "603278",
                "主营产品": "胎圈钢丝、钢帘线",
                "业务范围": "橡胶骨架材料研发与制造",
                "竞争对手": ["江苏兴达", "贝卡尔特"],
            }
        ]
    }

    rows = normalize_capability_rows("business", raw)

    assert [(fact.label, fact.value) for fact in rows[0]] == [
        ("主营产品", "胎圈钢丝、钢帘线"),
        ("业务范围", "橡胶骨架材料研发与制造"),
        ("竞争对手", "江苏兴达、贝卡尔特"),
    ]


def test_consensus_orders_future_profit_forecasts_by_priority() -> None:
    raw = {
        "datas": [
            {
                "股票简称": "大业股份",
                "预测净利润中值[2026]": 265_000_000,
                "预测净利润中值[2027]": 338_000_000,
                "机构评级": "增持",
            }
        ]
    }

    rows = normalize_capability_rows("consensus", raw)

    assert [fact.label for fact in rows[0]] == [
        "预测净利润中值[2026]",
        "预测净利润中值[2027]",
        "机构评级",
    ]
    assert rows[0][0].value == "2.65 亿"


def test_event_keeps_period_change_and_normalizes_date() -> None:
    raw = {
        "datas": [
            {
                "股票简称": "大业股份",
                "营业收入[2026一季]": 1_286_000_000,
                "营业收入同比增长率[2026一季]": "12.4%",
                "归母净利润同比增长率[2026一季]": "-8.7%",
                "公告日期": "20260428",
            }
        ]
    }

    rows = normalize_capability_rows("event", raw)

    facts = {fact.label: fact.value for fact in rows[0]}
    assert facts["营业收入同比增长率[2026一季]"] == "12.4%"
    assert facts["归母净利润同比增长率[2026一季]"] == "-8.7%"
    assert facts["公告日期"] == "2026-04-28"


def test_sector_selector_requires_metric_but_keeps_sector_name() -> None:
    identity_only = {"datas": [{"板块名称": "机器人概念"}]}
    useful = {
        "datas": [
            {"板块名称": "机器人概念", "板块热度排名": 2, "成交额": 98_600_000_000}
        ]
    }

    assert normalize_capability_rows("sector_selector", identity_only) == ()
    rows = normalize_capability_rows("sector_selector", useful)
    assert rows[0][0].label == "板块名称"
    assert rows[0][1].label == "板块热度排名"
    assert rows[0][2].value == "986.00 亿"


def test_sector_selector_accepts_index_name_as_sector_identity() -> None:
    raw = {
        "datas": [
            {
                "指数代码": "886068",
                "指数简称": "机器人概念",
                "板块热度[20260714]": 98.6,
                "成交额[20260714]": 98_600_000_000,
            }
        ]
    }

    rows = normalize_capability_rows("sector_selector", raw)

    assert rows[0][0].value == "机器人概念"


def test_event_report_period_without_event_fact_is_insufficient() -> None:
    raw = {
        "datas": [
            {
                "股票代码": "603278",
                "股票简称": "大业股份",
                "最新价": 8.61,
                "最新涨跌幅": "1.06%",
                "报告期[20260630]": "2026半年报",
            }
        ]
    }

    assert normalize_capability_rows("event", raw) == ()


def test_news_date_without_title_or_summary_is_insufficient() -> None:
    assert normalize_capability_rows(
        "news", {"datas": [{"publish_date": "20260714"}]}
    ) == ()


def test_news_prioritizes_content_before_date_and_url() -> None:
    rows = normalize_capability_rows(
        "news",
        {
            "datas": [
                {
                    "publish_time": 1_781_452_800,
                    "publish_date": "20260714",
                    "url": "https://example.com/research",
                    "title": "政策预期改善市场风险偏好",
                    "summary": "增量资金仍需成交确认。",
                }
            ]
        },
    )

    assert [fact.label for fact in rows[0]][:2] == ["标题", "摘要"]
    assert rows[0][2].label == "发布日期"
    assert rows[0][2].value == "2026-07-14"


def test_english_announcement_fields_count_as_evidence() -> None:
    rows = normalize_capability_rows(
        "announcement",
        {
            "datas": [
                {
                    "publish_date": "20260714",
                    "title": "2026年半年度业绩预告",
                    "summary": "预计净利润同比下降。",
                }
            ]
        },
    )

    assert [fact.label for fact in rows[0]][:2] == ["标题", "摘要"]


def test_growth_rate_formats_as_percent_before_profit_amount() -> None:
    rows = normalize_capability_rows(
        "event",
        {
            "datas": [
                {
                    "净利润增长率上限[20260630]": -241.516,
                    "变动类型[20260630]": "预减",
                }
            ]
        },
    )

    assert rows[0][0].value == "-241.52%"


def test_numeric_change_rate_keeps_upstream_percent_unit() -> None:
    rows = normalize_capability_rows(
        "index",
        {
            "datas": [
                {
                    "指数简称": "深证成指",
                    "最新价": 12_860.1,
                    "最新涨跌幅:前复权": -0.3301,
                }
            ]
        },
    )

    change = next(fact for fact in rows[0] if "涨跌幅" in fact.label)
    assert change.value == "-0.33%"


def test_finance_keeps_previous_revenue_after_balancing_core_metrics() -> None:
    rows = normalize_capability_rows(
        "finance",
        {
            "datas": [
                {
                    "营业收入[20231231]": 4_200_000_000,
                    "营业收入[20241231]": 4_700_000_000,
                    "营业收入[20251231]": 5_100_000_000,
                    "营业收入同比增长率[20251231]": 8.5,
                    "归母净利润[20251231]": 162_000_000,
                    "归母净利润同比增长率[20251231]": 18.6,
                    "经营活动产生的现金流量净额[20251231]": 91_000_000,
                    "净资产收益率[20251231]": 7.8,
                    "资产负债率[20251231]": 58.2,
                }
            ]
        },
    )

    labels = [fact.label for fact in rows[0]]
    assert labels[:4] == [
        "营业收入[20251231]",
        "归母净利润[20251231]",
        "经营活动产生的现金流量净额[20251231]",
        "净资产收益率[20251231]",
    ]
    assert "营业收入[20241231]" in labels


def test_index_keeps_quote_fields_and_prioritizes_shanghai_index() -> None:
    raw = {
        "datas": [
            {
                "指数简称": "创业板指",
                "最新价": 3851.14,
                "最新涨跌幅:前复权": "1.2%",
            },
            {
                "指数简称": "上证指数",
                "最新价": 3576.82,
                "最新涨跌幅:前复权": "0.4%",
            },
        ]
    }

    rows = normalize_capability_rows("index", raw)

    assert rows[0][0].value == "上证指数"
    assert any(fact.label == "最新涨跌幅:前复权" for fact in rows[0])


def test_astock_selector_rejects_quote_only_candidate() -> None:
    quote_only = {
        "datas": [
            {"股票代码": "603278", "股票简称": "大业股份", "最新价": 8.61, "涨跌幅": "1.06%"}
        ]
    }
    useful = {
        "datas": [
            {
                "股票代码": "603278",
                "股票简称": "大业股份",
                "净利润同比增长率": "18.6%",
                "成交额": 920_000_000,
            }
        ]
    }

    assert normalize_capability_rows("astock_selector", quote_only) == ()
    rows = normalize_capability_rows("astock_selector", useful)
    assert [fact.value for fact in rows[0]][:2] == ["603278", "大业股份"]


def test_duplicate_evidence_rows_are_collapsed() -> None:
    row = {"股票代码": "603278", "主营产品": "胎圈钢丝"}

    rows = normalize_capability_rows("business", {"datas": [row, row]})

    assert len(rows) == 1
