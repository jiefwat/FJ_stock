from stock_ts.agentic_stock_analysis import build_stock_agent_decision
from stock_ts.analysis import analyze_stock
from stock_ts.models import DailyBar, NewsItem, StockRawData
from stock_ts.providers.sample import SampleDataProvider
from stock_ts.web import render_page


def _bars(start: float = 10.0, step: float = 0.18) -> list[DailyBar]:
    return [
        DailyBar(
            date=f"2026-06-{day:02d}",
            open=start + day * step - 0.05,
            high=start + day * step + 0.25,
            low=start + day * step - 0.18,
            close=start + day * step,
            volume=1000 + day * 75,
        )
        for day in range(1, 25)
    ]


def test_agentic_stock_method_builds_context_pack_roles_and_signal_attribution() -> None:
    raw = StockRawData(
        code="688362",
        name="甬矽电子",
        bars=_bars(18, 0.11),
        fund_flow=-1.6,
        pe_ttm=390.8,
        valuation={"pb": 8.9, "source": "tushare", "date": "2026-07-08"},
        fund_flow_detail={
            "main_net_inflow": -1.6,
            "main_net_pct": -3.2,
            "source": "tushare_moneyflow",
        },
        news_items=[
            NewsItem(
                date="2026-07-08",
                source="财联社",
                title="扩产项目进入量产爬坡",
                summary="先进封装订单释放",
                sentiment="positive",
            ),
            NewsItem(
                date="2026-07-08",
                source="证券时报",
                title="高估值半导体股午后回落",
                summary="板块分歧加剧",
                sentiment="negative",
            ),
        ],
        data_sources=["tushare.daily", "akshare.news", "tdx-snapshot"],
    )
    report = analyze_stock(raw)

    decision = build_stock_agent_decision(raw, report)

    assert decision.context_pack.subject == "甬矽电子(688362)"
    assert decision.context_pack.trade_date == "2026-06-24"
    assert "估值" in decision.context_pack.available_blocks
    assert "资金" in decision.context_pack.available_blocks
    assert "新闻" in decision.context_pack.available_blocks
    assert decision.signal_attribution.total == 100
    assert (
        decision.signal_attribution.strongest_bullish_signal
        != decision.signal_attribution.strongest_bearish_signal
    )
    roles = [finding.role for finding in decision.analyst_team]
    assert roles == ["技术分析师", "基本面分析师", "新闻/情绪分析师", "资金/成交分析师"]
    assert any("PE(TTM) 390.80" in item for item in decision.analyst_team[1].evidence)
    assert any("扩产项目" in item for item in decision.analyst_team[2].evidence)
    assert any("主力资金净流出" in item for item in decision.analyst_team[3].evidence)
    assert "甬矽电子" in decision.research_debate.bull_thesis
    assert "甬矽电子" in decision.research_debate.bear_thesis
    assert "PE(TTM) 390.80" in decision.research_debate.bear_thesis
    assert decision.trader.entry_trigger
    assert decision.trader.invalidation
    assert decision.trader.position_rule
    assert (
        "低可信" in decision.risk_review.portfolio_decision
        or "高估值" in decision.risk_review.portfolio_decision
    )


def test_agentic_stock_method_is_stock_specific_not_boilerplate() -> None:
    strong_raw = StockRawData(
        code="603278",
        name="大业股份",
        bars=_bars(10, 0.2),
        fund_flow=1.2,
        pe_ttm=18.5,
        news_items=[
            NewsItem(
                date="2026-07-08",
                source="财联社",
                title="机器人零部件订单增加",
                summary="金属制品需求改善",
                sentiment="positive",
            )
        ],
    )
    risky_raw = StockRawData(
        code="688362",
        name="甬矽电子",
        bars=_bars(25, -0.16),
        fund_flow=-2.2,
        pe_ttm=390.8,
        news_items=[
            NewsItem(
                date="2026-07-08",
                source="证券时报",
                title="半导体高估值回撤",
                summary="资金兑现",
                sentiment="negative",
            )
        ],
    )

    strong = build_stock_agent_decision(strong_raw, analyze_stock(strong_raw))
    risky = build_stock_agent_decision(risky_raw, analyze_stock(risky_raw))

    assert strong.research_debate.bull_thesis != risky.research_debate.bull_thesis
    assert strong.research_debate.bear_thesis != risky.research_debate.bear_thesis
    assert strong.trader.action != risky.trader.action
    assert "大业股份" in strong.risk_review.portfolio_decision
    assert "甬矽电子" in risky.risk_review.portfolio_decision
    assert "PE(TTM) 390.80" in risky.risk_review.portfolio_decision


def test_web_stock_page_surfaces_tradingagents_chain_and_signal_attribution() -> None:
    html = render_page(
        stock_code="603278",
        provider_name="sample",
        provider=SampleDataProvider(),
        holdings_path="data/portfolio/holdings.csv",
    )
    stock_start = html.index('id="stock"')
    next_workspace = html.find('<section class="workspace-pane', stock_start + 1)
    stock_html = html[stock_start:] if next_workspace == -1 else html[stock_start:next_workspace]

    assert "分析入口" in stock_html
    assert "综合结论" in stock_html
    assert "分析内容" in stock_html
    assert "后续建议" in stock_html
    assert "未来涨跌预测" in stock_html
    assert "大业股份" in stock_html


def test_stock_markdown_renders_agentic_method_chain() -> None:
    from stock_ts.report import render_stock_markdown

    raw = StockRawData(
        code="603278",
        name="大业股份",
        bars=_bars(10, 0.2),
        fund_flow=1.2,
        pe_ttm=18.5,
        news_items=[
            NewsItem(
                date="2026-07-08",
                source="财联社",
                title="机器人零部件订单增加",
                summary="金属制品需求改善",
                sentiment="positive",
            )
        ],
    )
    markdown = render_stock_markdown(analyze_stock(raw))

    assert "## TradingAgents 决策链" in markdown
    assert "daily_stock_analysis 信号归因" in markdown
    assert "技术分析师" in markdown
    assert "多头观点" in markdown
    assert "组合经理最终意见" in markdown


def test_stock_page_keeps_agentic_method_but_hides_noisy_detail_by_default() -> None:
    html = render_page(
        stock_code="603278",
        provider_name="sample",
        provider=SampleDataProvider(),
        holdings_path="data/portfolio/holdings.csv",
    )
    stock_start = html.index('id="stock"')
    next_workspace = html.find('<section class="workspace-pane', stock_start + 1)
    stock_html = html[stock_start:] if next_workspace == -1 else html[stock_start:next_workspace]

    assert "分析内容" in stock_html
    assert "未来涨跌预测" in stock_html
    assert "TradingAgents 决策链" not in stock_html
    assert "专业评分卡" not in stock_html
    assert "核心证据链 / 6 维判断 / 6个证据" not in stock_html
    assert "明确操作建议 / 执行条件 / 操作条件" not in stock_html
    assert "3个风险" not in stock_html
    assert stock_html.count("summary-card") < 42
