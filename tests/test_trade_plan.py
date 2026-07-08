from stock_ts.announcements import AnnouncementReport
from stock_ts.professional_research import build_event_radar, build_technical_profile
from stock_ts.providers.sample import SampleDataProvider
from stock_ts.trade_plan import build_trade_plan, render_trade_plan_markdown
from stock_ts.web import render_page


def test_trade_plan_outputs_explicit_action_and_price_rules() -> None:
    raw = SampleDataProvider().fetch_stock("603278")
    technical = build_technical_profile(raw)
    event_radar = build_event_radar(
        AnnouncementReport(query="603278", total=0, items=[], risk_events=[])
    )

    plan = build_trade_plan(
        stock_name="大业股份",
        latest_close=raw.bars[-1].close,
        upside_score=58,
        risk_level="中",
        trend="下降趋势",
        technical=technical,
        event_radar=event_radar,
        data_quality_warnings=[],
    )

    assert plan.verdict in {"观望", "减仓", "小仓试错", "持有"}
    assert plan.target_position
    assert plan.entry_trigger
    assert plan.stop_loss
    assert plan.forbidden_actions
    markdown = render_trade_plan_markdown(plan)
    assert "明确操作建议" in markdown
    assert "目标仓位" in markdown
    assert "触发条件" in markdown


def test_web_renders_concrete_trade_plan_not_generic_words() -> None:
    html = render_page(
        stock_code="大业股份",
        provider_name="sample",
        provider=SampleDataProvider(),
        announcement_fetcher=lambda query, limit=5: AnnouncementReport(
            query=query,
            total=0,
            items=[],
            risk_events=[],
        ),
    )

    assert "明确操作建议" in html
    assert "目标仓位" in html
    assert "买入触发" in html
    assert "加仓" in html
    assert "止损" in html
    assert "禁止动作" not in html
