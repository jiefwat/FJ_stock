from stock_ts.analysis import analyze_market, analyze_stock
from stock_ts.models import DailyBar, IndexQuote, MarketRawData, StockRawData
from stock_ts.report import render_market_markdown, render_stock_markdown


def test_market_analysis_summarizes_breadth_and_heat() -> None:
    raw = MarketRawData(
        trade_date="2026-06-05",
        indices=[
            IndexQuote(code="000001", name="上证指数", close=3120.5, pct_chg=0.82, amount=5123.4),
            IndexQuote(code="399001", name="深证成指", close=9850.2, pct_chg=1.12, amount=6421.8),
        ],
        advancing=3620,
        declining=1260,
        limit_up=78,
        limit_down=8,
        top_sectors=[("半导体", 3.8), ("机器人", 2.9), ("银行", -0.4)],
        northbound_net_inflow=42.6,
    )

    snapshot = analyze_market(raw)

    assert snapshot.heat_score >= 70
    assert snapshot.breadth_ratio > 2
    assert snapshot.summary.startswith("市场偏强")
    assert "半导体" in snapshot.opportunities[0]


def test_analyze_market_preserves_breadth_counts_for_display() -> None:
    snapshot = analyze_market(
        MarketRawData(
            trade_date="2026-06-26",
            indices=[
                IndexQuote(
                    code="000001",
                    name="上证指数",
                    close=3200.0,
                    pct_chg=0.2,
                    amount=5000.0,
                )
            ],
            advancing=2500,
            declining=1800,
            unchanged=300,
            limit_up=42,
            limit_down=12,
            top_sectors=[("机器人", 2.3)],
        )
    )

    assert snapshot.advancing_count == 2500
    assert snapshot.declining_count == 1800
    assert snapshot.unchanged_count == 300


def test_stock_analysis_flags_trend_and_risk() -> None:
    bars = [
        DailyBar(date="2026-05-27", open=10.0, high=10.5, low=9.8, close=10.2, volume=1000),
        DailyBar(date="2026-05-28", open=10.2, high=10.8, low=10.1, close=10.7, volume=1200),
        DailyBar(date="2026-05-29", open=10.7, high=11.2, low=10.5, close=11.0, volume=1800),
        DailyBar(date="2026-06-01", open=11.0, high=11.5, low=10.9, close=11.4, volume=2100),
        DailyBar(date="2026-06-02", open=11.4, high=12.1, low=11.2, close=11.9, volume=2600),
        DailyBar(date="2026-06-03", open=11.9, high=12.4, low=11.7, close=12.2, volume=2800),
    ]
    raw = StockRawData(code="000001", name="平安银行", bars=bars, fund_flow=1.8, pe_ttm=6.2)

    report = analyze_stock(raw)

    assert report.trend == "上升趋势"
    assert report.latest_close == 12.2
    assert any("量能" in item for item in report.observations)
    assert report.risk_level in {"低", "中"}


def test_stock_analysis_includes_enhanced_indicator_observations() -> None:
    bars = [
        DailyBar(
            date=f"2026-05-{day:02d}",
            open=10 + day * 0.1,
            high=10.5 + day * 0.1,
            low=9.8 + day * 0.1,
            close=10 + day * 0.12,
            volume=1000 + day * 20,
        )
        for day in range(1, 25)
    ]

    report = analyze_stock(StockRawData(code="000001", name="平安银行", bars=bars))

    observations = "\n".join(report.observations)
    assert "MACD" in observations
    assert "RSI" in observations
    assert "BOLL" in observations


def test_markdown_reports_include_disclaimer_and_sections() -> None:
    market = analyze_market(
        MarketRawData(
            trade_date="2026-06-05",
            indices=[
                IndexQuote(
                    code="000001", name="上证指数", close=3120.5, pct_chg=0.82, amount=5123.4
                )
            ],
            advancing=2000,
            declining=1800,
            limit_up=45,
            limit_down=18,
            top_sectors=[("人工智能", 2.1)],
        )
    )
    stock = analyze_stock(
        StockRawData(
            code="600519",
            name="贵州茅台",
            bars=[
                DailyBar(date="2026-06-01", open=1500, high=1520, low=1490, close=1510, volume=100),
                DailyBar(date="2026-06-02", open=1510, high=1530, low=1505, close=1525, volume=110),
                DailyBar(date="2026-06-03", open=1525, high=1540, low=1510, close=1532, volume=120),
            ],
        )
    )

    market_md = render_market_markdown(market)
    stock_md = render_stock_markdown(stock)

    assert "# 每日大盘分析" in market_md
    assert "## 市场温度" in market_md
    assert "# 个股分析：贵州茅台" in stock_md
    assert "不构成投资建议" in market_md
    assert "不构成投资建议" in stock_md


def test_market_markdown_labels_top_sectors_as_representative_strength_not_board_pct() -> None:
    market = analyze_market(
        MarketRawData(
            trade_date="2026-07-03",
            indices=[IndexQuote("000001", "上证指数", 4043.64, 0.37, 1000)],
            advancing=3803,
            declining=1628,
            limit_up=167,
            limit_down=45,
            top_sectors=[("外骨骼机器人", 20.02)],
        )
    )

    markdown = render_market_markdown(market)

    assert "## 强势方向（代表强度）" in markdown
    assert "外骨骼机器人：代表样本 20.02%" in markdown
    assert "外骨骼机器人：20.02%" not in markdown


def test_stock_analysis_builds_professional_scorecard_dimensions() -> None:
    bars = [
        DailyBar(
            date=f"2026-06-{day:02d}",
            open=10 + day * 0.08,
            high=10.4 + day * 0.1,
            low=9.8 + day * 0.05,
            close=10 + day * 0.12,
            volume=1000 + day * 80,
        )
        for day in range(1, 25)
    ]
    report = analyze_stock(
        StockRawData(
            code="688362",
            name="甬矽电子",
            bars=bars,
            fund_flow=-1.8,
            pe_ttm=96.0,
            valuation={"pb": 8.2, "source": "tushare"},
            fund_flow_detail={"main_net_inflow": -1.8, "super_large_net_inflow": -0.7},
            data_sources=["tushare.daily", "tdx-snapshot"],
        )
    )

    names = [item.name for item in report.dimensions]
    assert names == [
        "技术趋势",
        "量价结构",
        "资金行为",
        "估值基本面",
        "消息事件",
        "统计位置",
        "风险约束",
        "交易计划",
    ]
    assert all(0 <= item.score <= 100 for item in report.dimensions)
    assert any("主力资金净流出" in item.evidence for item in report.dimensions)
    assert any("PE(TTM) 96.00" in item.evidence for item in report.dimensions)
    assert any("不加仓" in item.action for item in report.dimensions)


def test_stock_markdown_renders_professional_scorecard() -> None:
    bars = [
        DailyBar(
            date=f"2026-06-{day:02d}",
            open=20,
            high=21 + day * 0.05,
            low=19,
            close=20 + day * 0.08,
            volume=2000 + day * 30,
        )
        for day in range(1, 25)
    ]
    report = analyze_stock(StockRawData(code="603278", name="大业股份", bars=bars, pe_ttm=18.5))

    markdown = render_stock_markdown(report)

    assert "## 专业评分卡" in markdown
    assert "技术趋势" in markdown
    assert "资金行为" in markdown
    assert "估值基本面" in markdown
    assert "交易计划" in markdown
    assert "动作：" in markdown


def test_stock_analysis_summarizes_decision_conflicts_and_conditions() -> None:
    bars = [
        DailyBar(
            date=f"2026-06-{day:02d}",
            open=30 - day * 0.05,
            high=31 - day * 0.04,
            low=29 - day * 0.08,
            close=30 - day * 0.12,
            volume=2000 + day * 120,
        )
        for day in range(1, 25)
    ]
    report = analyze_stock(
        StockRawData(
            code="688362",
            name="甬矽电子",
            bars=bars,
            fund_flow=-2.4,
            pe_ttm=96.0,
            valuation={"pb": 8.2},
        )
    )

    assert report.decision.verdict in {"降风险", "防守观察"}
    assert report.decision.today_action.startswith("不加仓")
    assert "补仓" in report.decision.forbidden_action
    assert "站回" in report.decision.strengthen_condition
    assert "跌破" in report.decision.exit_condition
    assert any("资金" in item for item in report.decision.core_conflicts)
    assert any("估值" in item for item in report.decision.core_conflicts)
    assert report.decision.data_reliability in {"部分可信", "低可信"}


def test_stock_markdown_renders_decision_summary_before_scorecard() -> None:
    bars = [
        DailyBar(
            date=f"2026-06-{day:02d}",
            open=10 + day * 0.05,
            high=10.5 + day * 0.07,
            low=9.8 + day * 0.03,
            close=10 + day * 0.08,
            volume=1000 + day * 40,
        )
        for day in range(1, 25)
    ]
    report = analyze_stock(StockRawData(code="603278", name="大业股份", bars=bars, pe_ttm=18.5))
    markdown = render_stock_markdown(report)

    assert markdown.index("## 决策摘要") < markdown.index("## 专业评分卡")
    assert "最终判断" in markdown
    assert "核心矛盾" in markdown
    assert "今日动作" in markdown
    assert "不能做什么" in markdown
    assert "转强条件" in markdown
    assert "离场条件" in markdown
    assert "数据可信度" in markdown


def test_stock_event_dimension_names_concrete_catalyst_and_risk_news() -> None:
    from stock_ts.analysis import analyze_stock
    from stock_ts.models import DailyBar, NewsItem, StockRawData

    bars = [
        DailyBar("2026-07-01", 10, 10.5, 9.8, 10, 1000),
        DailyBar("2026-07-02", 10, 10.8, 9.9, 10.5, 1300),
        DailyBar("2026-07-03", 10.5, 11, 10.2, 10.8, 1400),
        DailyBar("2026-07-06", 10.8, 11.2, 10.6, 11.0, 1500),
        DailyBar("2026-07-07", 11.0, 11.4, 10.9, 11.2, 1600),
    ]
    report = analyze_stock(
        StockRawData(
            code="688362",
            name="甬矽电子",
            bars=bars,
            news_items=[
                NewsItem(
                    "2026-07-07",
                    "东方财富",
                    "公司订单增长",
                    "先进封装订单增加",
                    sentiment="positive",
                ),
                NewsItem("2026-07-07", "公告", "股东拟减持", "减持计划", sentiment="negative"),
            ],
        )
    )

    event = next(item for item in report.dimensions if item.name == "消息事件")
    assert "公司订单增长" in event.evidence
    assert "股东拟减持" in event.evidence
    assert "先复核负面消息" in event.action
