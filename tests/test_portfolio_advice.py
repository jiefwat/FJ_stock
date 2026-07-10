from stock_ts.analysis import analyze_market, analyze_portfolio
from stock_ts.models import Holding
from stock_ts.portfolio_advice import build_portfolio_advice, render_portfolio_advice_markdown
from stock_ts.providers.sample import SampleDataProvider
from stock_ts.web import render_page


def test_portfolio_advice_explains_where_to_add_holdings_and_actions() -> None:
    provider = SampleDataProvider()
    market = analyze_market(provider.fetch_market())
    portfolio = analyze_portfolio(
        [
            Holding(code="600519", name="贵州茅台", shares=500, cost_price=1500, sector="白酒"),
            Holding(code="000001", name="平安银行", shares=100, cost_price=10.5, sector="银行"),
        ],
        provider,
        market,
    )

    advice = build_portfolio_advice(
        portfolio,
        market=market,
        holdings_path="data/portfolio/holdings.csv",
        transactions_path="data/portfolio/transactions.csv",
    )

    assert advice.holdings_path == "data/portfolio/holdings.csv"
    assert "code,name,shares,cost_price,sector,note" in advice.holdings_template
    assert advice.overall_action
    assert advice.position_advices
    assert any(item.action == "降仓" for item in advice.position_advices)
    assert any("第一大持仓" in item for item in advice.portfolio_actions)
    markdown = render_portfolio_advice_markdown(advice)
    assert "我的持仓在哪添加" in markdown
    assert "组合整体建议" in markdown
    assert "具体持仓处理" in markdown


def test_web_renders_portfolio_advice_and_holding_entry() -> None:
    html = render_page(
        stock_code="大业股份",
        provider_name="sample",
        provider=SampleDataProvider(),
        holdings_path="data/portfolio/holdings.csv",
    )

    assert "持仓风险处置" in html
    assert "我的持仓" in html
    assert "总市值" in html
    assert "累计盈亏" in html
    assert "保存持仓" in html
    assert "添加持仓" in html
    assert "持仓文件" not in html


def test_portfolio_advice_builds_position_overview() -> None:
    provider = SampleDataProvider()
    market = analyze_market(provider.fetch_market())
    portfolio = analyze_portfolio(
        [
            Holding(code="600519", name="贵州茅台", shares=500, cost_price=1500, sector="白酒"),
            Holding(code="000001", name="平安银行", shares=100, cost_price=10.5, sector="银行"),
        ],
        provider,
        market,
    )

    advice = build_portfolio_advice(
        portfolio,
        market=market,
        holdings_path="data/portfolio/holdings.csv",
    )

    overview = " ".join(advice.position_overview)
    assert "记录内股票仓位" in overview
    assert "现金未录入" in overview
    assert "第一大+前三大" in overview
    assert "目标现金/低风险" in overview
    assert "行业暴露" in overview
    markdown = render_portfolio_advice_markdown(advice)
    assert "整体仓位情况" in markdown
    assert "记录内股票仓位" in markdown
