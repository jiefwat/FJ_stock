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
    assert labels[:2] == ["营业收入[2025]", "营业收入[2024]"]
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
