from stock_ts.providers.sample import SampleDataProvider
from stock_ts.research_playbook import build_decision_dashboard
from stock_ts.symbols import resolve_stock_query
from stock_ts.web import render_page
from stock_ts.workflows import build_daily_report, build_deep_stock_report


def test_decision_dashboard_has_dsa_and_tradingagents_inspired_blocks() -> None:
    provider = SampleDataProvider()
    daily = build_daily_report(provider, holdings_path="data/portfolio/holdings.csv")
    stock = build_deep_stock_report(
        provider,
        resolve_stock_query("大业股份").code,
        market=daily.market,
        sectors=daily.sectors,
        portfolio=daily.portfolio,
    )

    dashboard = build_decision_dashboard(
        stock=stock,
        market=daily.market,
        sectors=daily.sectors,
        portfolio=daily.portfolio,
        candidates=daily.candidates,
        data_warnings=["示例数据"],
    )

    assert dashboard.confidence_score < stock.upside.score
    assert dashboard.strategy_lenses
    assert {item.name for item in dashboard.strategy_lenses} >= {"均线趋势", "量能承接", "风险回撤"}
    assert dashboard.research_team
    assert {item.role for item in dashboard.research_team} >= {"技术分析师", "风险经理", "组合经理"}
    assert dashboard.source_blocks
    assert dashboard.observation_levels.support < stock.latest_close
    assert stock.latest_close < dashboard.observation_levels.resistance
    assert dashboard.checklist


def test_web_renders_decision_dashboard_and_strategy_lenses() -> None:
    html = render_page(
        stock_code="大业股份",
        provider_name="sample",
        holdings_path="data/portfolio/holdings.csv",
    )

    assert "每日大盘" in html
    assert "市场" in html
    assert "热点机会" in html
    assert "持仓分析" in html
    assert "今天先做什么" not in html
