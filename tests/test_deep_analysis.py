from stock_ts.deep_analysis import (
    analyze_batch_stocks,
    analyze_deep_stock,
    build_debate_rounds,
    render_batch_markdown,
    render_deep_stock_markdown,
)
from stock_ts.models import NewsItem
from stock_ts.news import analyze_news
from stock_ts.providers.sample import SampleDataProvider
from stock_ts.workflows import (
    build_market_report,
    build_sector_report,
    build_stock_report,
)


def test_deep_stock_analysis_has_multi_angles_debate_and_potential() -> None:
    provider = SampleDataProvider()
    market = build_market_report(provider)
    sectors = build_sector_report(provider, market=market)
    stock = build_stock_report(provider, "600519")
    news = analyze_news(
        [
            NewsItem(
                date=market.trade_date,
                source="sample",
                title="行业需求改善",
                summary="样例新闻用于深度分析测试",
                sentiment="positive",
            )
        ],
        trade_date=market.trade_date,
    )

    report = analyze_deep_stock(stock, market=market, sectors=sectors, news=news)

    assert report.code == "600519"
    assert report.upside.score >= 0
    assert report.upside.label
    assert len(report.angles) >= 6
    assert {angle.name for angle in report.angles} >= {
        "价格趋势",
        "量能结构",
        "市场环境",
        "板块主线",
        "新闻舆情",
        "风险约束",
    }
    assert len(report.debate_rounds) >= 3
    assert {round_.role for round_ in report.debate_rounds} >= {
        "技术分析师",
        "基本面分析师",
        "新闻情绪分析师",
        "多头研究员",
        "空头研究员",
        "交易员",
        "风控经理",
        "组合经理",
    }
    assert report.final_conclusion
    assert report.invalid_conditions


def test_debate_rounds_compare_bull_bear_and_judge_viewpoints() -> None:
    provider = SampleDataProvider()
    market = build_market_report(provider)
    sectors = build_sector_report(provider, market=market)
    stock = build_stock_report(provider, "300750")
    report = analyze_deep_stock(stock, market=market, sectors=sectors)

    rounds = build_debate_rounds(report)

    assert [round_.role for round_ in rounds[:4]] == [
        "技术分析师",
        "基本面分析师",
        "新闻情绪分析师",
        "多头研究员",
    ]
    assert "组合经理" == rounds[-1].role
    assert all(round_.thesis for round_ in rounds)
    assert all(round_.evidence for round_ in rounds)
    assert any("反证" in item or "失效" in item for item in rounds[-2].evidence)


def test_deep_stock_markdown_is_a_real_conclusion_report() -> None:
    provider = SampleDataProvider()
    market = build_market_report(provider)
    sectors = build_sector_report(provider, market=market)
    report = analyze_deep_stock(
        build_stock_report(provider, "600519"),
        market=market,
        sectors=sectors,
    )

    markdown = render_deep_stock_markdown(report)

    assert "多角度深度分析" in markdown
    assert "多轮对抗" in markdown
    assert "技术分析师" in markdown
    assert "多头研究员" in markdown
    assert "交易员" in markdown
    assert "风控经理" in markdown
    assert "组合经理" in markdown
    assert "综合机会评分" in markdown
    assert "不构成投资建议" in markdown


def test_batch_analysis_ranks_multiple_stocks_and_keeps_safety_wording() -> None:
    provider = SampleDataProvider()
    market = build_market_report(provider)
    sectors = build_sector_report(provider, market=market)
    reports = [
        analyze_deep_stock(build_stock_report(provider, code), market=market, sectors=sectors)
        for code in ["600519", "000001", "300750"]
    ]

    batch = analyze_batch_stocks(reports, market=market, sectors=sectors)
    markdown = render_batch_markdown(batch)

    assert len(batch.stocks) == 3
    assert batch.stocks[0].upside.score >= batch.stocks[-1].upside.score
    assert "批量个股深度对比" in markdown
    assert "600519" in markdown
    assert "000001" in markdown
    assert "300750" in markdown
    assert "只作为观察优先级" in markdown


def test_deep_stock_final_conclusions_are_evidence_based_not_templates() -> None:
    provider = SampleDataProvider()
    market = build_market_report(provider)
    sectors = build_sector_report(provider, market=market)
    reports = [
        analyze_deep_stock(build_stock_report(provider, code), market=market, sectors=sectors)
        for code in ["600519", "000001", "300750"]
    ]

    conclusions = [report.final_conclusion for report in reports]

    assert len(set(conclusions)) == len(conclusions)
    forbidden_templates = ["当前信号不足", "处于中性偏强观察区", "不适合给出确定性判断"]
    assert not any(
        template in conclusion for template in forbidden_templates for conclusion in conclusions
    )
    for report in reports:
        conclusion = report.final_conclusion
        assert report.name in conclusion
        assert any(token in conclusion for token in ["优势", "矛盾", "风险", "触发", "失效"])
        assert any(angle.evidence[:4] in conclusion for angle in report.angles if angle.evidence)


def test_deep_stock_conclusion_prioritizes_stock_specific_evidence_over_market_context() -> None:
    provider = SampleDataProvider()
    market = build_market_report(provider)
    sectors = build_sector_report(provider, market=market)
    reports = [
        analyze_deep_stock(build_stock_report(provider, code), market=market, sectors=sectors)
        for code in ["600519", "000001", "300750"]
    ]

    for report in reports:
        assert "优势是市场环境" not in report.final_conclusion
        assert any(
            f"优势是{name}" in report.final_conclusion
            for name in ["价格趋势", "量能结构", "板块主线", "风险约束", "持仓影响"]
        )


def test_deep_stock_conclusion_never_uses_unknown_evidence_as_advantage() -> None:
    provider = SampleDataProvider()
    market = build_market_report(provider)
    sectors = build_sector_report(provider, market=market)
    stock = build_stock_report(provider, "600519")
    unknown = stock.__class__(
        code="999999",
        name="未知样本",
        latest_date=stock.latest_date,
        latest_close=stock.latest_close,
        pct_change=-3.2,
        trend="下降趋势",
        risk_level="高",
        observations=[],
        watch_points=stock.watch_points,
        fund_flow=stock.fund_flow,
        pe_ttm=stock.pe_ttm,
        dimensions=stock.dimensions,
        decision=stock.decision,
    )

    report = analyze_deep_stock(unknown, market=market, sectors=sectors)

    assert "优势是板块主线：未识别" not in report.final_conclusion
    assert "优势是价格趋势：下降趋势" not in report.final_conclusion
    assert "优势暂不明确" in report.final_conclusion
