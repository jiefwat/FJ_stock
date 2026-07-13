import json
from pathlib import Path

from stock_ts.models import (
    CandidateStockRawData,
    DailyBar,
    IndexQuote,
    MarketRawData,
    NewsItem,
    SectorRawData,
    StockRawData,
)
from stock_ts.providers.sample import SampleDataProvider
from stock_ts.providers.tdx_snapshot_provider import TdxSnapshotProvider
from stock_ts.web import (
    _manual_refresh_command,
    _render_automation_monitor_panel,
    _render_latest_daily_artifact,
    _resolve_live_stock_news_fetcher,
    _run_manual_refresh_command,
    render_page,
)


def _sample_html(**kwargs) -> str:
    return render_page(
        stock_code=kwargs.pop("stock_code", "600519"),
        provider_name=kwargs.pop("provider_name", "sample"),
        provider=kwargs.pop("provider", SampleDataProvider()),
        holdings_path=kwargs.pop("holdings_path", "data/portfolio/holdings.csv"),
        **kwargs,
    )


def _sample_stock_html(**kwargs) -> str:
    return _workspace(_sample_html(**kwargs), "stock")


def _workspace(html: str, key: str) -> str:
    start = html.index(f'id="{key}"')
    next_workspace = html.find('<section class="workspace-pane', start + 1)
    return html[start:] if next_workspace == -1 else html[start:next_workspace]


def test_tdx_snapshot_page_load_does_not_fetch_live_news_by_default() -> None:
    def explicit_fetcher(symbol: str, limit: int) -> list[NewsItem]:
        return []

    assert (
        _resolve_live_stock_news_fetcher(
            provider_name="tdx-snapshot",
            provider_injected=False,
            stock_news_fetcher=None,
        )
        is None
    )
    assert (
        _resolve_live_stock_news_fetcher(
            provider_name="tdx-snapshot",
            provider_injected=False,
            stock_news_fetcher=explicit_fetcher,
        )
        is explicit_fetcher
    )


def test_four_workspaces_do_not_repeat_global_precision_summary() -> None:
    html = _sample_html()

    assert "精准摘要" not in html
    assert "展开细节" not in html
    assert "precision-detail-fold" not in html
    for workspace in ["market", "portfolio", "stock", "opportunity"]:
        section = _workspace(html, workspace)
        assert "module-title" in section
        assert (
            "detail-shell" in section
            or "data-table" in section
            or "opportunity-dossier" in section
        )


def test_core_modules_show_decision_state_not_just_raw_data() -> None:
    html = _sample_html()

    assert "股票涨跌统计" in html
    assert "每日大盘" in html
    assert "组合风控结论" in html
    assert "分析内容" in html
    assert "机会总闸门" in html
    assert "研究候选" in html


def test_four_modules_keep_copy_functional_and_simple() -> None:
    html = _sample_html()

    for decorative_text in [
        "Market Command Tower",
        "Portfolio X-Ray",
        "Strategy Funnel",
        "Evidence Bench",
        "一个好的大盘页",
        "全市场扫描 -> 策略命中 -> 风险排除 -> 个股验证 -> 自选跟踪",
    ]:
        assert decorative_text not in html


def test_four_modules_do_not_render_narrator_checklist_panels() -> None:
    html = _sample_html()

    for narrator_panel in [
        "<h3>下一步检查单</h3>",
        "<h3>下一步验证</h3>",
        "<h3>盘中检查</h3>",
    ]:
        assert narrator_panel not in html




def test_pages_show_data_statistics_analysis_without_narrator_blocks() -> None:
    html = _sample_html()
    market_html = _workspace(html, "market")

    for text in [
        "数据链路：",
        "缺失的数据只作为风险提示",
        "<h3>下一步：",
        "验证条件：",
        "失效条件：",
        "异动清单：",
        "事件日历：",
    ]:
        assert text not in html

    for text in [
        "上涨/下跌/平盘",
        "涨停",
        "跌停",
        "股票涨跌统计",
        "强势板块Top5",
        "弱势板块Top5",
        "对应股票",
        "分析",
    ]:
        assert text in market_html

def test_global_data_center_is_simple_status_list() -> None:
    html = _sample_html()
    data_center_html = _workspace(html, "data-center")

    for text in [
        "数据中台",
        "数据状态",
        "更新时间",
        "结论",
        "数据",
        "状态",
        "影响",
        "K线行情",
        "资金面",
        "新闻舆情",
        "公告",
        "基本面",
    ]:
        assert text in data_center_html

    for removed in [
        "专业数据中台",
        "采集渠道",
        "覆盖范围",
        "未采集/缺失",
        "人工复核入口",
        "核对K线",
        "可用数据域",
        "覆盖 12/12",
        "个股新闻 5/12",
        "市场消息 2 条",
    ]:
        assert removed not in data_center_html


def test_each_module_header_shows_refresh_time_and_manual_refresh_button() -> None:
    html = _sample_html()

    for workspace in ["market", "portfolio", "stock", "opportunity", "data-center"]:
        section = _workspace(html, workspace)
        assert "数据刷新时间" in section, workspace
        assert 'name="refresh" value="1"' in section, workspace
        assert "手动刷新数据" in section, workspace






def test_daily_market_shows_concise_data_sector_analysis_and_mapped_events() -> None:
    market_html = _workspace(_sample_html(), "market")

    for text in [
        "股票涨跌统计",
        "涨停",
        "&gt;3%",
        "&lt;-3%",
        "强势板块Top5",
        "弱势板块Top5",
        "对应股票",
        "分析",
        "异动事件",
        "事件原因",
        "基本面：",
    ]:
        assert text in market_html

    for removed in [
        "市场摘要",
        "市场结论",
        "风险敞口",
        "最强方向",
        "风险项",
        "市场总闸门",
        "数据源",
        "指数表现",
        "市场宽度",
        "展开指数",
        "板块Top5</strong>",
    ]:
        assert removed not in market_html


def test_daily_market_renders_sector_heatmap_cards() -> None:
    market_html = _workspace(_sample_html(), "market")

    for text in [
        "板块热力图",
        "按主题聚合",
        "颜色=今日涨跌/风险强度",
        "主题",
        "热度",
        "资金",
        "半导体",
        "机器人",
    ]:
        assert text in market_html

    for class_name in [
        "market-sector-heatmap-panel",
        "market-sector-heatmap-grid",
        "market-sector-heat-card",
        "market-sector-heat-cells",
        "market-sector-heat-cell",
    ]:
        assert class_name in market_html


def test_market_ui_uses_concise_data_labels_not_narrative_terms() -> None:
    market_html = _workspace(_sample_html(), "market")

    for removed in [
        "仓位闸门",
        "只回答四件事",
        "今天能不能做",
        "仓位怎么放",
        "主线在哪里",
        "风险是什么",
        "数据链路：K线 / 资金面 / 消息面",
    ]:
        assert removed not in market_html

    for text in ["股票涨跌统计", "强势板块Top5", "弱势板块Top5", "分析"]:
        assert text in market_html

def test_market_module_uses_real_breadth_counts_instead_of_unreturned() -> None:
    market_html = _workspace(_sample_html(), "market")

    assert "上涨/下跌/平盘" in market_html
    assert "未返回" not in market_html
    assert "股票涨跌统计" in market_html
    assert "强势板块Top5" in market_html


def test_daily_market_module_matches_market_gate_design_doc() -> None:
    market_html = _workspace(_sample_html(), "market")

    for text in [
        "股票涨跌统计",
        "涨停",
        "跌停",
        "&gt;3%",
        "&lt;-3%",
        "强势板块Top5",
        "弱势板块Top5",
        "对应股票",
        "分析",
    ]:
        assert text in market_html


def test_daily_market_module_surfaces_conclusion_card_fields() -> None:
    market_html = _workspace(_sample_html(), "market")

    for text in [
        "股票涨跌统计",
        "上涨/下跌/平盘",
        "强势板块Top5",
        "弱势板块Top5",
        "分析",
    ]:
        assert text in market_html


def test_daily_market_analyzes_stocks_moving_more_than_six_percent() -> None:
    class WideMoveProvider(SampleDataProvider):
        def fetch_candidate_universe(self) -> list[CandidateStockRawData]:
            return [
                CandidateStockRawData(
                    code="300001",
                    name="强势机器人A",
                    sector="机器人",
                    bars=[
                        DailyBar("2026-07-09", 10, 10.2, 9.8, 10.0, 1000),
                        DailyBar("2026-07-10", 10.1, 10.9, 10.0, 10.8, 3200),
                    ],
                    fund_flow=1.8,
                    turnover_rate=9.6,
                    amount=18.5,
                ),
                CandidateStockRawData(
                    code="300004",
                    name="强势机器人B",
                    sector="机器人",
                    bars=[
                        DailyBar("2026-07-09", 12, 12.2, 11.8, 12.0, 1000),
                        DailyBar("2026-07-10", 12.1, 13.1, 12.0, 12.9, 2800),
                    ],
                    fund_flow=1.1,
                    turnover_rate=6.6,
                    amount=12.6,
                ),
                CandidateStockRawData(
                    code="600002",
                    name="强势算力",
                    sector="算力",
                    bars=[
                        DailyBar("2026-07-09", 20, 20.2, 19.8, 20.0, 1000),
                        DailyBar("2026-07-10", 20.2, 21.6, 20.0, 21.4, 2600),
                    ],
                    fund_flow=0.9,
                    turnover_rate=5.2,
                    amount=15.0,
                ),
                CandidateStockRawData(
                    code="600005",
                    name="未知强势股",
                    sector="未识别主题",
                    bars=[
                        DailyBar("2026-07-09", 15, 15.2, 14.8, 15.0, 1000),
                        DailyBar("2026-07-10", 15.1, 17.1, 15.0, 16.8, 2600),
                    ],
                    fund_flow=1.5,
                    turnover_rate=12.0,
                    amount=16.0,
                ),
                CandidateStockRawData(
                    code="600003",
                    name="弱势白酒",
                    sector="白酒",
                    bars=[
                        DailyBar("2026-07-09", 30, 30.3, 29.8, 30.0, 1000),
                        DailyBar("2026-07-10", 29.5, 29.7, 27.5, 27.8, 4100),
                    ],
                    fund_flow=-1.3,
                    turnover_rate=8.1,
                    amount=11.2,
                ),
            ]

    market_html = _workspace(
        _sample_html(provider=WideMoveProvider(), provider_name="tdx-snapshot"),
        "market",
    )

    for text in [
        "大涨大跌分析",
        "板块扩散结论",
        "&gt;6%上涨",
        "&lt;-6%下跌",
        "机器人：2只大涨，0只大跌",
        "白酒：0只大涨，1只大跌",
        "机器人出现板块共振",
        "强势机器人A 8.00%",
        "强势机器人B 7.50%",
        "强势算力 7.00%",
        "弱势白酒 -7.33%",
        "未知强势股 12.00%",
        "资金流入",
        "资金流出",
        "&gt;6%上涨 4",
        "&lt;-6%下跌 1",
    ]:
        assert text in market_html
    assert (
        "/?code=300001&amp;provider=tdx-snapshot"
        "&amp;holdings=data%2Fportfolio%2Fholdings.csv#stock"
    ) in market_html
    assert (
        "/?code=600003&amp;provider=tdx-snapshot"
        "&amp;holdings=data%2Fportfolio%2Fholdings.csv#stock"
    ) in market_html
    assert 'aria-label="查看 强势机器人A 个股分析"' in market_html
    assert "未识别主题：1只大涨" not in market_html


def test_market_wide_move_does_not_leave_unknown_research_copy() -> None:
    class UnknownWideMoveProvider(SampleDataProvider):
        def fetch_candidate_universe(self) -> list[CandidateStockRawData]:
            return [
                CandidateStockRawData(
                    code="600005",
                    name="未知强势股",
                    sector="未识别主题",
                    bars=[
                        DailyBar("2026-07-09", 15, 15.2, 14.8, 15.0, 1000),
                        DailyBar("2026-07-10", 15.1, 17.1, 15.0, 16.8, 2600),
                    ],
                    turnover_rate=12.0,
                    amount=16.0,
                )
            ]

    market_html = _workspace(
        _sample_html(provider=UnknownWideMoveProvider(), provider_name="tdx-snapshot"),
        "market",
    )
    wide_move_html = market_html[
        market_html.index("大涨大跌分析") : market_html.index("market-sector-duo")
    ]

    assert "大涨大跌分析" in wide_move_html
    assert "未识别明确消息/公告/基本面原因" not in wide_move_html
    assert "需继续查新闻" not in wide_move_html
    assert "联网核验未见可验证新增催化" not in wide_move_html
    assert "未知强势股 12.00%" in wide_move_html
    assert "未知强势股上涨 12.00%" not in wide_move_html
    assert "题材未识别，先按个股独立异动观察" in wide_move_html
    assert "换手 12.0%" in wide_move_html


def test_market_wide_move_analysis_explains_cause_not_price_result() -> None:
    class CauseProvider(SampleDataProvider):
        def fetch_candidate_universe(self) -> list[CandidateStockRawData]:
            return [
                CandidateStockRawData(
                    code="300111",
                    name="订单驱动",
                    sector="机器人",
                    bars=[
                        DailyBar("2026-07-09", 10, 10.2, 9.8, 10.0, 1000),
                        DailyBar("2026-07-10", 10.1, 11.2, 10.0, 11.0, 2600),
                    ],
                    fund_flow=2.4,
                    turnover_rate=9.0,
                    amount=18.0,
                    pe_ttm=24.0,
                    news_items=[
                        NewsItem(
                            date="2026-07-10",
                            source="东方财富",
                            title="订单驱动签订机器人订单",
                            summary="订单增长",
                            sentiment="positive",
                        )
                    ],
                )
            ]

    market_html = _workspace(
        _sample_html(provider=CauseProvider(), provider_name="tdx-snapshot"),
        "market",
    )
    wide_move_html = market_html[
        market_html.index("大涨大跌分析") : market_html.index("market-sector-duo")
    ]

    assert "原因：" in wide_move_html
    assert "消息催化" in wide_move_html
    assert "资金行为" in wide_move_html
    assert "基本面" in wide_move_html
    assert "盘面原因" not in wide_move_html
    assert "上涨 8.91%" not in wide_move_html


def test_market_wide_move_uses_live_news_when_snapshot_missing() -> None:
    class NewslessWideMoveProvider(SampleDataProvider):
        def fetch_candidate_universe(self) -> list[CandidateStockRawData]:
            return [
                CandidateStockRawData(
                    code="600005",
                    name="联网强势股",
                    sector="机器人",
                    bars=[
                        DailyBar("2026-07-09", 10, 10.2, 9.8, 10.0, 1000),
                        DailyBar("2026-07-10", 10.1, 11.2, 10.0, 11.0, 2600),
                    ],
                    fund_flow=1.6,
                    turnover_rate=9.5,
                    amount=12.0,
                )
            ]

    def stock_news_fetcher(symbol: str, limit: int) -> list[NewsItem]:
        if symbol == "600005":
            return [
                NewsItem(
                    date="2026-07-10",
                    source="联网新闻",
                    title="联网强势股获得机器人订单",
                    summary="订单催化",
                    sentiment="positive",
                )
            ][:limit]
        return []

    market_html = _workspace(
        _sample_html(
            provider=NewslessWideMoveProvider(),
            provider_name="tdx-snapshot",
            stock_news_fetcher=stock_news_fetcher,
        ),
        "market",
    )

    assert "联网强势股获得机器人订单" in market_html
    assert "未识别明确消息/公告/基本面原因" not in market_html


def test_daily_market_uses_professional_market_diagnosis_not_shallow_summary() -> None:
    market_html = _workspace(_sample_html(), "market")

    for text in [
        "专业大盘研判",
        "研判等级",
        "市场环境",
        "赚钱效应",
        "亏钱效应",
        "主线质量",
        "资金持续性",
        "结论",
        "依据",
    ]:
        assert text in market_html

    for shallow_text in [
        "强势集中在",
        "弱势集中在",
    ]:
        assert shallow_text not in market_html


def test_opportunity_module_focuses_on_gate_candidates_and_evidence() -> None:
    opportunity_html = _workspace(_sample_html(), "opportunity")

    for text in ["机会总闸门", "证据漏斗", "研究候选", "支持证据", "最大反证"]:
        assert text in opportunity_html

    for noisy_text in [
        "热门板块主题",
        "股票机会",
        "候选列表",
        "板块方向",
        "策略通道",
        "情绪温度",
        "赚钱效应",
        "亏钱效应",
        "方法说明",
        "数据链路",
        "推荐买入",
        "推荐股票",
    ]:
        assert noisy_text not in opportunity_html


def test_opportunity_reasons_show_support_and_counter_evidence() -> None:
    opportunity_html = _workspace(_sample_html(), "opportunity")

    for text in ["支持证据", "最大反证", "下一步：", "数据："]:
        assert text in opportunity_html
    assert "上涨概率" not in opportunity_html


def test_opportunity_stock_reasons_use_week_trend_fund_technical_and_news() -> None:
    class DiverseCandidateProvider(SampleDataProvider):
        def fetch_candidate_universe(self) -> list[CandidateStockRawData]:
            return [
                CandidateStockRawData(
                    code="300111",
                    name="趋势强股",
                    sector="机器人",
                    bars=[
                        DailyBar("2026-07-06", 10.0, 10.2, 9.9, 10.0, 1000),
                        DailyBar("2026-07-07", 10.1, 10.7, 10.0, 10.6, 1300),
                        DailyBar("2026-07-08", 10.7, 11.2, 10.5, 11.0, 1700),
                        DailyBar("2026-07-09", 11.0, 11.7, 10.9, 11.5, 2200),
                        DailyBar("2026-07-10", 11.5, 12.4, 11.4, 12.2, 3200),
                    ],
                    fund_flow=2.3,
                    turnover_rate=8.8,
                    amount=22.5,
                    pe_ttm=38,
                    news_items=[
                        NewsItem(
                            date="2026-07-10",
                            source="东方财富",
                            title="趋势强股获得机器人订单",
                            summary="订单催化",
                            sentiment="positive",
                        )
                    ],
                ),
                CandidateStockRawData(
                    code="300222",
                    name="冲高回落",
                    sector="机器人",
                    bars=[
                        DailyBar("2026-07-06", 20.0, 20.5, 19.8, 20.2, 2000),
                        DailyBar("2026-07-07", 20.3, 22.5, 20.1, 22.0, 4200),
                        DailyBar("2026-07-08", 22.2, 23.0, 21.6, 21.8, 3900),
                        DailyBar("2026-07-09", 21.7, 22.1, 20.9, 21.1, 3600),
                        DailyBar("2026-07-10", 21.0, 21.2, 20.0, 20.4, 3300),
                    ],
                    fund_flow=-0.7,
                    turnover_rate=11.2,
                    amount=18.0,
                    pe_ttm=72,
                ),
            ]

    opportunity_html = _workspace(
        _sample_html(provider=DiverseCandidateProvider(), provider_name="tdx-snapshot"),
        "opportunity",
    )

    for text in ["支持证据", "最大反证", "资金面", "消息面"]:
        assert text in opportunity_html

    assert "趋势强股" in opportunity_html
    assert "冲高回落" in opportunity_html
    assert "净流入" in opportunity_html
    assert "趋势强股获得机器人订单" in opportunity_html


def test_opportunity_reasons_do_not_use_repeated_fallback_copy() -> None:
    opportunity_html = _workspace(_sample_html(), "opportunity")

    for repeated_copy in [
        "基本面：估值待补，不能用低估值解释机会",
        "入选原因：价格可靠，进入复核名单",
        "消息面：未接入个股新闻，不作为推荐理由",
        "基本面/估值：需用代表个股财报和估值继续确认",
        "等待消息/公告/基本面确认",
    ]:
        assert repeated_copy not in opportunity_html


def test_opportunity_module_surfaces_theme_stocks_and_reasons() -> None:
    html = _sample_html()
    opportunity_html = _workspace(html, "opportunity")

    for text in ["板块与市场支持证据", "研究候选", "支持证据", "最大反证"]:
        assert text in opportunity_html


def test_opportunity_module_hides_abnormal_sector_pct_as_trade_signal() -> None:
    class WeirdSectorProvider(SampleDataProvider):
        def fetch_sectors(self) -> list[SectorRawData]:
            return [
                SectorRawData(
                    "医疗器械概念", 211.65, 1.0, 6.38, limit_up_count=1, high_divergence=True
                ),
                SectorRawData("人工智能", 30.0, 1.0, 2.09, limit_up_count=1, high_divergence=True),
            ]

    opportunity_html = _workspace(_sample_html(provider=WeirdSectorProvider()), "opportunity")

    assert "医疗器械概念" in opportunity_html
    assert "涨跌异常" in opportunity_html or "复核真实板块指数" in opportunity_html


def test_opportunity_module_uses_auditable_funnel_without_strategy_tabs() -> None:
    opportunity_html = _workspace(_sample_html(), "opportunity")

    for text in ["机会总闸门", "证据漏斗", "研究候选", "筛选与来源账本"]:
        assert text in opportunity_html
    for removed in ["策略通道", "推荐买入", "推荐股票"]:
        assert removed not in opportunity_html


def test_opportunity_module_renders_candidate_cards_with_research_links() -> None:
    opportunity_html = _workspace(_sample_html(), "opportunity")

    for text in ["研究候选", "支持证据", "最大反证", "进入个股分析"]:
        assert text in opportunity_html
    for removed in ["推荐买入", "推荐股票", "买入条件"]:
        assert removed not in opportunity_html


def test_opportunity_candidate_links_carry_source_strategy_and_evidence() -> None:
    opportunity_html = _workspace(_sample_html(), "opportunity")

    assert 'href="/?code=' in opportunity_html
    assert "candidate_source=opportunity" in opportunity_html
    assert "candidate_strategy_label=" in opportunity_html
    assert "candidate_evidence=" in opportunity_html


def test_opportunity_primary_surface_uses_evidence_cards_not_recommendation_table() -> None:
    opportunity_html = _workspace(_sample_html(), "opportunity")

    assert "<th>推荐原因</th>" not in opportunity_html
    assert "candidate-decision-card" in opportunity_html
    assert "candidate-evidence-pair" in opportunity_html
    assert "opportunity-dimension-table" not in opportunity_html


def test_opportunity_candidates_open_stock_analysis_without_buy_rating(
    monkeypatch,
    tmp_path,
) -> None:
    daily_dir = tmp_path / "daily"
    daily_dir.mkdir()
    (daily_dir / "pipeline.status").write_text(
        "status=ok\ngenerated_at=2026-07-12T09:00:00\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("STOCK_TS_DAILY_REPORT_DIR", str(daily_dir))

    class BuyableOpportunityProvider(SampleDataProvider):
        def fetch_market(self) -> MarketRawData:
            return MarketRawData(
                trade_date="2026-07-10",
                indices=[
                    IndexQuote(
                        code="000001",
                        name="上证指数",
                        close=3200.0,
                        pct_chg=0.8,
                        amount=5200.0,
                    )
                ],
                advancing=3600,
                declining=1200,
                limit_up=80,
                limit_down=4,
                top_sectors=[("机器人", 3.2)],
                northbound_net_inflow=40.0,
            )

        def fetch_sectors(self) -> list[SectorRawData]:
            return [
                SectorRawData(
                    name="机器人",
                    pct_chg=3.2,
                    advancing_ratio=0.82,
                    amount_change=28.0,
                    fund_flow=5.1,
                    limit_up_count=5,
                )
            ]

        def fetch_candidate_universe(self) -> list[CandidateStockRawData]:
            return [
                CandidateStockRawData(
                    code="300777",
                    name="可买强股",
                    sector="机器人",
                    bars=[
                        DailyBar("2026-07-06", 10.0, 10.2, 9.9, 10.0, 1000),
                        DailyBar("2026-07-07", 10.0, 10.4, 9.9, 10.3, 1400),
                        DailyBar("2026-07-08", 10.3, 10.8, 10.2, 10.7, 1700),
                        DailyBar("2026-07-09", 10.7, 11.0, 10.6, 10.9, 2100),
                        DailyBar("2026-07-10", 10.9, 11.3, 10.8, 11.2, 2600),
                    ],
                    fund_flow=3.6,
                    turnover_rate=7.2,
                    amount=26.0,
                    pe_ttm=24.0,
                    news_items=[
                        NewsItem(
                            date="2026-07-10",
                            source="东方财富",
                            title="可买强股机器人订单落地",
                            summary="订单催化",
                            sentiment="positive",
                        )
                    ],
                )
            ]

    opportunity_html = _workspace(
        _sample_html(provider=BuyableOpportunityProvider()),
        "opportunity",
    )

    assert "可买强股" in opportunity_html
    assert "个股分析" in opportunity_html
    assert 'class="primary-button"' in opportunity_html
    assert 'href="/?code=300777&amp;provider=sample' in opportunity_html
    assert "动作：建议买入" not in opportunity_html
    assert "动作：可小仓买入" not in opportunity_html


def test_opportunity_list_keeps_counter_evidence_instead_of_hiding_candidates() -> None:
    class MixedOpportunityProvider(SampleDataProvider):
        def fetch_market(self) -> MarketRawData:
            return MarketRawData(
                trade_date="2026-07-10",
                indices=[
                    IndexQuote(
                        code="000001",
                        name="上证指数",
                        close=3200.0,
                        pct_chg=0.9,
                        amount=5600.0,
                    )
                ],
                advancing=3500,
                declining=1100,
                limit_up=75,
                limit_down=3,
                top_sectors=[("机器人", 3.5)],
                northbound_net_inflow=35.0,
            )

        def fetch_sectors(self) -> list[SectorRawData]:
            return [
                SectorRawData(
                    name="机器人",
                    pct_chg=3.5,
                    advancing_ratio=0.82,
                    amount_change=30.0,
                    fund_flow=5.0,
                    limit_up_count=6,
                )
            ]

        def fetch_candidate_universe(self) -> list[CandidateStockRawData]:
            return [
                CandidateStockRawData(
                    code="300781",
                    name="推荐买入票",
                    sector="机器人",
                    bars=[
                        DailyBar("2026-07-06", 10.0, 10.2, 9.9, 10.0, 1000),
                        DailyBar("2026-07-07", 10.0, 10.3, 9.9, 10.2, 1300),
                        DailyBar("2026-07-08", 10.2, 10.6, 10.1, 10.5, 1600),
                        DailyBar("2026-07-09", 10.5, 10.8, 10.4, 10.7, 1900),
                        DailyBar("2026-07-10", 10.7, 11.1, 10.6, 11.0, 2400),
                    ],
                    fund_flow=3.2,
                    turnover_rate=7.2,
                    amount=26.0,
                    pe_ttm=24.0,
                    news_items=[
                        NewsItem(
                            date="2026-07-10",
                            source="东方财富",
                            title="推荐买入票机器人订单落地",
                            summary="订单催化",
                            sentiment="positive",
                        )
                    ],
                ),
                CandidateStockRawData(
                    code="300782",
                    name="负资金票",
                    sector="机器人",
                    bars=[
                        DailyBar("2026-07-06", 10.0, 10.2, 9.9, 10.0, 1000),
                        DailyBar("2026-07-07", 10.0, 10.3, 9.9, 10.2, 1200),
                        DailyBar("2026-07-08", 10.2, 10.6, 10.1, 10.5, 1500),
                        DailyBar("2026-07-09", 10.5, 10.8, 10.4, 10.7, 1800),
                        DailyBar("2026-07-10", 10.7, 11.1, 10.6, 10.9, 2100),
                    ],
                    fund_flow=-2.5,
                    turnover_rate=9.0,
                    amount=30.0,
                    pe_ttm=30.0,
                ),
            ]

    opportunity_html = _workspace(
        _sample_html(provider=MixedOpportunityProvider()),
        "opportunity",
    )

    assert "研究候选" in opportunity_html
    assert "推荐买入票" in opportunity_html
    assert "负资金票" in opportunity_html
    assert "资金面：净流出" in opportunity_html
    assert "推荐买入候选" not in opportunity_html


def test_opportunity_overheated_candidates_surface_chase_risk_before_validation() -> None:
    class OverheatedOpportunityProvider(SampleDataProvider):
        def fetch_market(self) -> MarketRawData:
            return MarketRawData(
                trade_date="2026-07-10",
                indices=[
                    IndexQuote(
                        code="000001",
                        name="上证指数",
                        close=3200.0,
                        pct_chg=0.6,
                        amount=5100.0,
                    )
                ],
                advancing=3200,
                declining=1400,
                limit_up=60,
                limit_down=6,
                top_sectors=[("机器人", 3.1)],
                northbound_net_inflow=20.0,
            )

        def fetch_sectors(self) -> list[SectorRawData]:
            return [
                SectorRawData(
                    name="机器人",
                    pct_chg=3.1,
                    advancing_ratio=0.78,
                    amount_change=24.0,
                    fund_flow=4.2,
                    limit_up_count=4,
                )
            ]

        def fetch_candidate_universe(self) -> list[CandidateStockRawData]:
            return [
                CandidateStockRawData(
                    code="300778",
                    name="高位强股",
                    sector="机器人",
                    bars=[
                        DailyBar("2026-07-06", 10.0, 10.2, 9.9, 10.0, 1000),
                        DailyBar("2026-07-07", 10.0, 10.3, 9.9, 10.2, 1200),
                        DailyBar("2026-07-08", 10.2, 10.5, 10.1, 10.4, 1400),
                        DailyBar("2026-07-09", 10.4, 10.6, 10.2, 10.3, 1500),
                        DailyBar("2026-07-10", 10.3, 11.7, 10.3, 11.5, 2600),
                    ],
                    fund_flow=2.8,
                    turnover_rate=8.0,
                    amount=24.0,
                    pe_ttm=26.0,
                    news_items=[
                        NewsItem(
                            date="2026-07-10",
                            source="证券时报",
                            title="高位强股机器人订单增长",
                            summary="订单催化",
                            sentiment="positive",
                        )
                    ],
                )
            ]

    opportunity_html = _workspace(
        _sample_html(provider=OverheatedOpportunityProvider()),
        "opportunity",
    )

    assert "高位强股" in opportunity_html
    assert "最大反证" in opportunity_html
    assert "短线涨幅较大" in opportunity_html
    assert "进入个股分析" in opportunity_html
    assert "为什么推荐买" not in opportunity_html


def test_opportunity_uses_support_counter_and_next_verification_contract() -> None:
    opportunity_html = _workspace(_sample_html(), "opportunity")

    for text in ["支持证据", "最大反证", "下一步：", "进入个股分析"]:
        assert text in opportunity_html

    for old_header in [
        "<th>趋势/强度</th>",
        "<th>技术/位置</th>",
        "<th>统一个股分析</th>",
        "<th>趋势/量价原因</th>",
        "<th>资金/成交原因</th>",
        "<th>基本面/估值原因</th>",
        "<th>消息/公告原因</th>",
        "<th>板块/主题原因</th>",
    ]:
        assert old_header not in opportunity_html


def test_opportunity_page_prioritizes_research_without_probability_wording() -> None:
    class ForwardOpportunityProvider(SampleDataProvider):
        def fetch_sectors(self) -> list[SectorRawData]:
            return [
                SectorRawData(
                    name="先进制造",
                    pct_chg=2.8,
                    advancing_ratio=0.74,
                    amount_change=22.0,
                    fund_flow=3.2,
                    limit_up_count=3,
                ),
                SectorRawData(
                    name="冷门周期",
                    pct_chg=-1.2,
                    advancing_ratio=0.32,
                    amount_change=-8.0,
                    fund_flow=-1.4,
                    limit_up_count=0,
                ),
            ]

        def fetch_candidate_universe(self) -> list[CandidateStockRawData]:
            return [
                CandidateStockRawData(
                    code="300901",
                    name="趋势潜力",
                    sector="先进制造",
                    bars=[
                        DailyBar("2026-07-06", 10.0, 10.2, 9.9, 10.0, 1000),
                        DailyBar("2026-07-07", 10.1, 10.5, 10.0, 10.4, 1300),
                        DailyBar("2026-07-08", 10.4, 10.8, 10.3, 10.7, 1600),
                        DailyBar("2026-07-09", 10.7, 11.0, 10.6, 10.9, 1900),
                        DailyBar("2026-07-10", 10.9, 11.4, 10.8, 11.2, 2600),
                    ],
                    fund_flow=2.6,
                    turnover_rate=6.8,
                    amount=18.0,
                    pe_ttm=28.0,
                    news_items=[
                        NewsItem(
                            date="2026-07-10",
                            source="东方财富",
                            title="趋势潜力获得产业订单",
                            summary="先进制造订单催化",
                            sentiment="positive",
                        )
                    ],
                ),
                CandidateStockRawData(
                    code="300902",
                    name="单日追高",
                    sector="先进制造",
                    bars=[
                        DailyBar("2026-07-06", 10.0, 10.1, 9.8, 10.0, 1000),
                        DailyBar("2026-07-07", 10.0, 10.2, 9.8, 10.1, 1100),
                        DailyBar("2026-07-08", 10.1, 10.3, 9.9, 10.2, 1200),
                        DailyBar("2026-07-09", 10.2, 10.3, 10.0, 10.1, 1300),
                        DailyBar("2026-07-10", 10.1, 11.4, 10.1, 11.3, 5200),
                    ],
                    fund_flow=-2.2,
                    turnover_rate=18.0,
                    amount=35.0,
                    pe_ttm=88.0,
                ),
                CandidateStockRawData(
                    code="300903",
                    name="冷门反弹",
                    sector="冷门周期",
                    bars=[
                        DailyBar("2026-07-06", 8.0, 8.1, 7.9, 8.0, 1000),
                        DailyBar("2026-07-07", 8.0, 8.1, 7.8, 7.9, 1000),
                        DailyBar("2026-07-08", 7.9, 8.0, 7.7, 7.8, 1000),
                        DailyBar("2026-07-09", 7.8, 7.9, 7.6, 7.7, 1000),
                        DailyBar("2026-07-10", 7.7, 8.0, 7.6, 7.9, 1100),
                    ],
                    fund_flow=0.1,
                    turnover_rate=3.0,
                    amount=4.0,
                    pe_ttm=18.0,
                ),
            ]

    opportunity_html = _workspace(
        _sample_html(provider=ForwardOpportunityProvider()), "opportunity"
    )

    assert "研究候选" in opportunity_html
    assert "支持证据" in opportunity_html
    assert "资金面：净流入" in opportunity_html
    assert "消息面" in opportunity_html
    assert "先进制造" in opportunity_html
    assert "概率" not in opportunity_html
    assert "综合排序 71/100" not in opportunity_html
    assert "最大反证" in opportunity_html


def test_opportunity_focus_conclusion_is_gate_and_verification_not_trade_advice() -> None:
    class GuidanceProvider(SampleDataProvider):
        def fetch_sectors(self) -> list[SectorRawData]:
            return [
                SectorRawData(
                    name="先进制造",
                    pct_chg=2.8,
                    advancing_ratio=0.74,
                    amount_change=22.0,
                    fund_flow=3.2,
                    limit_up_count=3,
                )
            ]

        def fetch_candidate_universe(self) -> list[CandidateStockRawData]:
            return [
                CandidateStockRawData(
                    code="300901",
                    name="未来指导",
                    sector="先进制造",
                    bars=[
                        DailyBar("2026-07-06", 10.0, 10.2, 9.9, 10.0, 1000),
                        DailyBar("2026-07-07", 10.1, 10.5, 10.0, 10.4, 1300),
                        DailyBar("2026-07-08", 10.4, 10.8, 10.3, 10.7, 1600),
                        DailyBar("2026-07-09", 10.7, 11.0, 10.6, 10.9, 1900),
                        DailyBar("2026-07-10", 10.9, 11.4, 10.8, 11.2, 2600),
                    ],
                    fund_flow=2.6,
                    turnover_rate=6.8,
                    amount=18.0,
                    pe_ttm=28.0,
                )
            ]

    opportunity_html = _workspace(
        _sample_html(provider=GuidanceProvider()), "opportunity"
    )

    assert "重点结论：未来指导观察，等确认" not in opportunity_html
    assert "重点结论：未来指导" not in opportunity_html
    assert "机会总闸门" in opportunity_html
    assert "下一步：" in opportunity_html
    assert "最大反证" in opportunity_html
    assert "买入条件：" not in opportunity_html


def test_final_conclusions_use_research_style_action_driver_trigger_risk() -> None:
    html = _sample_html(stock_code="603278")
    portfolio_html = _workspace(html, "portfolio")
    stock_html = _workspace(html, "stock")
    opportunity_html = _workspace(html, "opportunity")

    for text in ["组合风控结论", "处置依据", "复核触发", "失效条件", "禁止动作"]:
        assert text in portfolio_html

    for text in ["机会总闸门", "支持证据", "最大反证", "下一步："]:
        assert text in opportunity_html

    for text in ["投委会结论", "转强触发", "失效退出", "最大反证"]:
        assert text in stock_html

    for stale_phrase in [
        "趋势和风险结构较好，可继续跟踪。",
        "证据还不够强，等趋势、资金或消息确认。",
        "观察不买，不追高",
    ]:
        assert stale_phrase not in portfolio_html
        assert stale_phrase not in opportunity_html


def test_core_modules_show_explicit_execution_boundaries_not_only_analysis() -> None:
    html = _sample_html(stock_code="603278")
    market_html = _workspace(html, "market")
    for text in ["买卖指导", "买入触发", "卖出/减仓", "仓位上限", "止损/失效"]:
        assert text in market_html

    portfolio_html = _workspace(html, "portfolio")
    for text in ["组合风控结论", "处置队列", "持仓边界", "禁止动作"]:
        assert text in portfolio_html
    assert "买卖指导" not in portfolio_html
    assert "买入触发" not in portfolio_html

    stock_html = _workspace(html, "stock")
    for text in ["仓位与执行边界", "入场触发", "减仓触发", "仓位上限", "失效条件"]:
        assert text in stock_html

    opportunity_html = _workspace(html, "opportunity")
    assert "机会总闸门" in opportunity_html
    assert "进入个股分析" in opportunity_html
    assert "买入触发" not in opportunity_html
    assert "卖出/减仓" not in opportunity_html

    for vague_text in [
        "继续观察即可",
        "自行判断买卖",
        "只看分析不做计划",
    ]:
        assert vague_text not in html


def test_opportunity_page_limits_full_market_to_top_30_stocks() -> None:
    class ThirtyFiveCandidateProvider(SampleDataProvider):
        def fetch_candidate_universe_metadata(self) -> dict[str, str]:
            return {
                "scope": "all_a_share",
                "returned_count": "35",
                "scanned_count": "35",
            }

        def fetch_candidate_universe(self) -> list[CandidateStockRawData]:
            return [
                CandidateStockRawData(
                    code=f"300{index:03d}",
                    name=f"综合候选{index:02d}",
                    sector="机器人",
                    bars=[
                        DailyBar("2026-07-06", 10.0, 10.2, 9.9, 10.0, 1000),
                        DailyBar("2026-07-07", 10.1, 10.4, 10.0, 10.2, 1300),
                        DailyBar("2026-07-08", 10.2, 10.5, 10.1, 10.4, 1500),
                        DailyBar("2026-07-09", 10.4, 10.7, 10.3, 10.6, 1700),
                        DailyBar("2026-07-10", 10.6, 10.9, 10.5, 10.8, 1900),
                    ],
                    fund_flow=1.0,
                    turnover_rate=5.0,
                    amount=12.0,
                    pe_ttm=28.0,
                )
                for index in range(35)
            ]

    opportunity_html = _workspace(
        _sample_html(provider=ThirtyFiveCandidateProvider()), "opportunity"
    )

    assert "综合候选29" in opportunity_html
    assert "综合候选30" not in opportunity_html
    assert opportunity_html.count("data-opportunity-stock-row") == 30


def test_opportunity_stocks_hide_dual_git_method_chain_summary_only() -> None:
    opportunity_html = _workspace(_sample_html(), "opportunity")

    for text in ["支持证据", "最大反证", "下一步："]:
        assert text in opportunity_html

    for text in [
        "daily_stock_analysis 信号归因",
        "TradingAgents",
        "分析师团队",
        "多空审议",
        "交易员",
        "组合经理",
    ]:
        assert text not in opportunity_html


def test_stock_module_leads_from_entry_to_research_memo_and_execution() -> None:
    html = _sample_html(stock_code="603278")
    stock_html = _workspace(html, "stock")

    for text in [
        "分析入口",
        "开始分析",
        "投委会结论",
        "五步决策轨道",
        "风险登记表",
        "仓位与执行边界",
        "诊断底稿",
        "三种情景",
        "证据账本",
    ]:
        assert text in stock_html

    assert stock_html.index("分析入口") < stock_html.index("投委会结论")
    assert stock_html.index("投委会结论") < stock_html.index("五步决策轨道")
    assert stock_html.index("五步决策轨道") < stock_html.index("风险登记表")
    assert stock_html.index("风险登记表") < stock_html.index("仓位与执行边界")
    assert stock_html.index("仓位与执行边界") < stock_html.index("诊断底稿")
    assert stock_html.index("诊断底稿") < stock_html.index("三种情景")
    assert "K线数据" not in stock_html
    kline_table_header = (
        "<th>日期</th><th>开盘</th><th>最高</th><th>最低</th><th>收盘</th><th>成交量</th>"
    )
    assert kline_table_header not in stock_html


def test_stock_analysis_uses_multi_day_theme_and_relative_comparison() -> None:
    stock_html = _workspace(_sample_html(stock_code="603278"), "stock")

    for text in [
        "多日趋势原因",
        "最近5日",
        "最近10日",
        "多日收盘",
        "主题板块对比",
        "所属主题",
        "主线板块",
        "综合对比结论",
    ]:
        assert text in stock_html
    assert "近一日 " not in stock_html


def test_stock_analysis_keeps_multi_role_method_in_supporting_evidence() -> None:
    stock_html = _workspace(_sample_html(stock_code="603278"), "stock")

    for text in [
        "多角色分析方法",
        "技术分析师",
        "基本面分析师",
        "新闻事件分析师",
        "情绪/资金分析师",
        "多空辩论",
        "交易员",
        "风控经理",
        "输入",
        "判断",
    ]:
        assert text in stock_html

    assert stock_html.index("投委会结论") < stock_html.index("诊断底稿")
    assert stock_html.index("诊断底稿") < stock_html.index("多角色分析方法")
    assert stock_html.index("展开原始诊断与支持证据") < stock_html.index("多角色分析方法")
    assert "完整方法链" not in stock_html


def test_stock_bull_bear_debate_does_not_use_user_position_as_bullish_reason() -> None:
    stock_html = _workspace(_sample_html(stock_code="603278"), "stock")

    debate_start = stock_html.index("多空辩论")
    debate_end = stock_html.index("交易员", debate_start)
    debate_html = stock_html[debate_start:debate_end]

    assert "看多依据：仓位" not in debate_html
    assert "看多依据：持仓影响" not in debate_html
    assert "浮动盈亏" not in debate_html
    assert "仓位" in stock_html


def test_live_stock_news_fallback_feeds_stock_and_opportunity_when_snapshot_missing() -> None:
    class MissingNewsProvider(SampleDataProvider):
        def fetch_stock(self, code: str) -> StockRawData:
            raw = super().fetch_stock(code)
            return StockRawData(
                code=raw.code,
                name=raw.name,
                bars=raw.bars,
                fund_flow=raw.fund_flow,
                pe_ttm=raw.pe_ttm,
                valuation=raw.valuation,
                fundamental_metrics=raw.fundamental_metrics,
                fund_flow_detail=raw.fund_flow_detail,
                data_sources=raw.data_sources,
            )

        def fetch_candidate_universe(self) -> list[CandidateStockRawData]:
            return [
                CandidateStockRawData(
                    code="300222",
                    name="联网候选",
                    sector="机器人",
                    bars=[
                        DailyBar("2026-07-06", 20.0, 20.5, 19.8, 20.2, 2000),
                        DailyBar("2026-07-07", 20.3, 22.5, 20.1, 22.0, 4200),
                        DailyBar("2026-07-08", 22.2, 23.0, 21.6, 21.8, 3900),
                        DailyBar("2026-07-09", 21.7, 22.1, 20.9, 21.1, 3600),
                        DailyBar("2026-07-10", 21.0, 22.2, 20.0, 22.0, 4300),
                    ],
                    fund_flow=1.1,
                    turnover_rate=7.2,
                    amount=16.8,
                    pe_ttm=32,
                )
            ]

    def fake_news_fetcher(symbol: str, limit: int) -> list[NewsItem]:
        return [
            NewsItem(
                date="2026-07-11",
                source="联网新闻",
                title=f"{symbol} 签订机器人订单",
                summary="订单催化",
                sentiment="positive",
            )
        ][:limit]

    html = _sample_html(
        stock_code="603278",
        provider=MissingNewsProvider(),
        provider_name="tdx-snapshot",
        stock_news_fetcher=fake_news_fetcher,
    )
    stock_html = _workspace(html, "stock")
    opportunity_html = _workspace(html, "opportunity")

    assert "联网新闻：603278 签订机器人订单" in stock_html
    assert "消息面：300222 签订机器人订单" in opportunity_html
    assert "300222 签订机器人订单" in opportunity_html
    assert "消息面：未接入个股新闻" not in opportunity_html


def test_stock_scenarios_avoid_false_probability_precision() -> None:
    stock_html = _workspace(_sample_html(stock_code="603278"), "stock")

    for text in [
        "三种情景",
        "改善",
        "基准",
        "恶化",
        "确认",
        "动作",
        "失效",
        "证据完整度",
    ]:
        assert text in stock_html

    for false_precision in ["上涨概率", "震荡概率", "下跌概率", "目标价"]:
        assert false_precision not in stock_html


def test_stock_module_removes_extra_research_panels() -> None:
    stock_html = _workspace(_sample_html(stock_code="603278"), "stock")

    for text in {
        "专业个股结论",
        "多维诊断",
        "综合总结",
        "个股证据抽屉",
        "股票摘要",
        "来源上下文",
        "数据质量与K线详情",
        "K线交易屏",
        "保存个股计划",
        "我的持仓",
        "候选前排",
    }:
        assert text not in stock_html


def test_stock_module_surfaces_single_stock_verdict_fields() -> None:
    stock_html = _workspace(_sample_html(stock_code="603278"), "stock")

    for text in [
        "当前判断",
        "趋势/量价",
        "资金/成交",
        "基本面/估值",
        "消息/公告",
        "板块/主题",
        "持仓/成本",
    ]:
        assert text in stock_html


def test_stock_module_explains_causes_not_only_indicator_states() -> None:
    stock_html = _workspace(_sample_html(stock_code="603278"), "stock")

    for text in [
        "原因分析",
        "影响/验证",
        "趋势/量价原因",
        "资金/成交原因",
        "基本面/估值原因",
        "消息/公告原因",
        "板块/主题原因",
        "持仓/成本原因",
        "技术原因",
        "资金原因",
        "估值原因",
        "事件原因",
        "板块原因",
        "成本原因",
    ]:
        assert text in stock_html

    for shallow_text in [
        "趋势/量价</td><td>上升趋势",
        "资金/成交</td><td>主力净流入",
        "基本面/估值</td><td>PE(TTM)",
        "消息/公告</td><td>公告待补充",
        "板块/主题</td><td>主线：",
    ]:
        assert shallow_text not in stock_html


def test_stock_module_requires_kline_fund_news_and_fundamental_blocks() -> None:
    stock_html = _workspace(_sample_html(stock_code="603278"), "stock")

    for text in [
        "K线行情",
        "资金面",
        "消息面",
        "基本面",
        "数据来源",
    ]:
        assert text in stock_html


def test_stock_module_downgrades_missing_required_data_blocks() -> None:
    class MinimalStockProvider(SampleDataProvider):
        def fetch_stock(self, code: str) -> StockRawData:
            return StockRawData(
                code=code,
                name="缺数样本",
                bars=[
                    DailyBar(
                        date="2026-07-01",
                        open=10,
                        high=10.2,
                        low=9.8,
                        close=10.1,
                        volume=1000,
                    ),
                    DailyBar(
                        date="2026-07-02",
                        open=10.1,
                        high=10.3,
                        low=10.0,
                        close=10.2,
                        volume=1100,
                    ),
                ],
                data_sources=["sample.kline"],
            )

    stock_html = _workspace(_sample_html(provider=MinimalStockProvider()), "stock")

    assert "K线行情" in stock_html
    assert "资金面" in stock_html
    assert "消息面" in stock_html
    assert "基本面" in stock_html
    assert stock_html.count("不作为买入理由") >= 3
    assert "缺失降级" in stock_html


def test_data_center_warns_when_required_stock_context_is_missing() -> None:
    class MinimalStockProvider(SampleDataProvider):
        def fetch_stock(self, code: str) -> StockRawData:
            return StockRawData(
                code=code,
                name="缺数样本",
                bars=[
                    DailyBar(
                        date="2026-07-10",
                        open=10,
                        high=10.2,
                        low=9.8,
                        close=10.1,
                        volume=1000,
                    )
                ],
                data_sources=["sample.kline"],
            )

    html = _sample_html(provider=MinimalStockProvider(), provider_name="tdx-snapshot")
    data_center_html = _workspace(html, "data-center")

    assert "资金面" in data_center_html
    assert "资金流/成交侧明细" in data_center_html
    assert "公告" in data_center_html
    assert "影响风险公告、财报事件和监管风险判断" in data_center_html
    assert data_center_html.count('class="data-center-alert"') <= 3
    assert "数据中台预警：" not in data_center_html


def test_stock_module_shows_candidate_source_context_when_entered_from_opportunity() -> None:
    stock_html = _sample_stock_html(
        stock_code="603278",
        candidate_source="opportunity",
        candidate_strategy_label="主线强势 + 放量突破",
        candidate_evidence="所属主题排名前 5，成交额放大",
    )

    assert "分析入口" in stock_html
    assert "综合结论" in stock_html
    assert "来源上下文" not in stock_html
    assert "主线强势 + 放量突破" not in stock_html


def test_portfolio_module_uses_single_editable_multidimensional_list() -> None:
    portfolio_html = _workspace(_sample_html(), "portfolio")

    for text in [
        "我的持仓",
        "组合风控结论",
        "处置队列",
        "风险暴露登记表",
        "持仓边界",
        "持仓证据",
        "新增持仓",
        "编辑",
        "删除",
        "保存持仓",
    ]:
        assert text in portfolio_html

    for text in ["处置依据", "复核触发", "失效条件", "禁止动作"]:
        assert text in portfolio_html

    for obsolete_text in ["组合整体总结", "看好", "建议轻仓", "继续观察", "买卖指导"]:
        assert obsolete_text not in portfolio_html

    for old_section in [
        "对应板块分析",
        "仓位/成本分析",
        "趋势/量价原因",
        "资金/成交原因",
        "基本面/估值原因",
        "消息/公告原因",
        "板块/主题原因",
        "仓位原因",
    ]:
        assert old_section not in portfolio_html

    assert portfolio_html.index("组合风控结论") < portfolio_html.index("处置队列")
    assert portfolio_html.index("处置队列") < portfolio_html.index("持仓证据")


def test_portfolio_analysis_explains_causes_not_only_statuses() -> None:
    portfolio_html = _workspace(_sample_html(), "portfolio")

    for text in ["处置依据", "复核触发", "失效条件", "首要风险", "历史暴露"]:
        assert text in portfolio_html

    for shallow_text in [
        "技术面</strong>上升趋势；日内",
        "资金面</strong>市场成交一般",
        "仓位成本</strong>亏损",
    ]:
        assert shallow_text not in portfolio_html


def test_portfolio_reasons_are_stock_specific_not_repeated_market_copy() -> None:
    portfolio_html = _workspace(_sample_html(), "portfolio")

    for repeated_copy in [
        "趋势向上且风险低，日内 0.91% 用于确认承接",
        "市场情绪偏强，但公告未确认前不把消息面作为加仓理由",
    ]:
        assert portfolio_html.count(repeated_copy) <= 1


def test_portfolio_uses_same_stock_analysis_method_as_stock_module() -> None:
    portfolio_html = _workspace(_sample_html(), "portfolio")

    for text in ["组合风控结论", "处置依据", "复核触发", "失效条件"]:
        assert text in portfolio_html

    for old_label in ["技术面原因", "板块情绪原因", "分析师团队", "多空审议", "交易员/组合经理"]:
        assert old_label not in portfolio_html


def test_portfolio_module_uses_research_dossier_not_legacy_console() -> None:
    portfolio_html = _workspace(_sample_html(), "portfolio")

    for text in {
        "组合摘要",
        "今日先处理",
        "持仓风险处置",
        "处理队列",
        "操作边界",
        "持仓明细",
        "持仓明细和维护",
        "数据链路",
    }:
        assert text not in portfolio_html
    for text in ["市场风险预算", "处置队列", "风险暴露登记表", "持仓边界"]:
        assert text in portfolio_html


def test_tdx_snapshot_defensive_market_keeps_defensive_action() -> None:
    html = _sample_html(
        stock_code="002487",
        provider_name="tdx-snapshot",
        provider=TdxSnapshotProvider("data/imports/tdx_snapshots.json"),
    )

    assert "股票涨跌统计" in html
    assert "数据可信度" in html


def test_opportunity_module_handles_limit_down_details_from_snapshot(tmp_path) -> None:
    def bars(previous: float, latest: float) -> list[dict]:
        return [
            {
                "date": "2026-06-25",
                "open": previous,
                "high": previous,
                "low": previous,
                "close": previous,
                "volume": 1000,
            },
            {
                "date": "2026-06-26",
                "open": latest,
                "high": latest,
                "low": latest,
                "close": latest,
                "volume": 1000,
            },
        ]

    holding_codes = [
        "603278",
        "688362",
        "603268",
        "300058",
        "06088",
        "600481",
        "300516",
        "000560",
        "002383",
        "002929",
        "002487",
    ]
    stocks = {code: {"code": code, "name": code, "bars": bars(10, 10.2)} for code in holding_codes}
    stocks["300002"] = {
        "code": "300002",
        "name": "二十厘米跌停",
        "sector": "机器人",
        "bars": bars(10, 8),
    }
    snapshot = {
        "market": {
            "trade_date": "2026-06-26",
            "indices": [],
            "advancing": 1000,
            "declining": 4000,
            "limit_up": 10,
            "limit_down": 0,
            "top_sectors": [["机器人", 1.2]],
        },
        "sectors": [
            {
                "name": "机器人",
                "pct_chg": 1.2,
                "advancing_ratio": 0.55,
                "amount_change": 5.0,
                "limit_up_count": 1,
            }
        ],
        "stocks": stocks,
        "candidate_universe": {
            "items": [
                {"code": "300002", "name": "二十厘米跌停", "sector": "机器人", "bars": bars(10, 8)}
            ]
        },
    }
    path = tmp_path / "tdx.json"
    path.write_text(json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")

    html = _sample_html(
        stock_code="300002",
        provider_name="tdx-snapshot",
        provider=TdxSnapshotProvider(path),
    )
    opportunity_html = _workspace(html, "opportunity")

    assert "二十厘米跌停" in opportunity_html
    assert "风险排除" in opportunity_html or "待补数据" in opportunity_html
    assert "推荐买入" not in opportunity_html


def test_structured_daily_decisions_do_not_recreate_home_module(tmp_path, monkeypatch) -> None:
    report_dir = tmp_path / "daily"
    report_dir.mkdir()
    (report_dir / "latest_decisions.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "trade_date": "2026-07-08",
                "market": {"summary": "结构化大盘：先防守"},
                "opportunities": [{"name": "结构化机会", "sector": "商业航天", "reason": "主线强"}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("STOCK_TS_DAILY_REPORT_DIR", str(report_dir))

    html = _sample_html()

    assert 'id="home"' not in html
    assert "每日大盘" in html
    assert "热点机会" in html


def test_data_center_keeps_mcp_market_news_status_simple() -> None:
    from stock_ts.models import NewsItem

    class McpNewsProvider(SampleDataProvider):
        def fetch_market_news(self) -> list[NewsItem]:
            return [
                NewsItem(
                    date="2026-07-11",
                    source="longbridge.mcp.新闻",
                    title="A股半导体板块走强",
                    summary="Longbridge MCP 市场新闻",
                    sentiment="positive",
                )
            ]

        def fetch_candidate_universe_metadata(self) -> dict[str, str]:
            return {
                "snapshot_source": "tdx-mcp-eltdx-bridge",
                "snapshot_generated_at": "2026-07-11T00:30:00Z",
                "mcp_market_news_refresh_source": "longbridge.mcp",
                "mcp_market_news_refresh_generated_at": "2026-07-11T01:00:00Z",
                "mcp_market_news_refresh_imported_count": "4",
            }

    html = _sample_html(provider=McpNewsProvider(), provider_name="tdx-snapshot")
    data_center_html = _workspace(html, "data-center")

    assert "新闻舆情" in data_center_html
    assert "2026-07-11 09:00:00 北京时间" in data_center_html
    assert "2026-07-11T01:00:00Z" not in data_center_html
    assert "longbridge.mcp" not in data_center_html


def test_data_refresh_times_render_as_beijing_time() -> None:
    class UtcRefreshProvider(SampleDataProvider):
        def fetch_candidate_universe_metadata(self) -> dict[str, str]:
            return {
                "snapshot_source": "tdx-mcp-eltdx-bridge",
                "snapshot_generated_at": "2026-07-11T06:06:19.966626+00:00",
                "mcp_market_news_refresh_generated_at": "2026-07-11T01:00:00Z",
            }

    html = _sample_html(provider=UtcRefreshProvider(), provider_name="tdx-snapshot")

    assert "2026-07-11 14:06:19 北京时间" in html
    assert "2026-07-11T06:06:19.966626+00:00" not in html
    assert "2026-07-11T01:00:00Z" not in html


def test_module_refresh_time_uses_latest_data_chain_timestamp(tmp_path: Path, monkeypatch) -> None:
    report_dir = tmp_path / "daily"
    report_dir.mkdir()
    (report_dir / "pipeline.status").write_text(
        "status=ok\ngenerated_at=2026-07-11T14:28:15\nrefresh=ok\nreport=ok\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("STOCK_TS_DAILY_REPORT_DIR", str(report_dir))

    class MixedRefreshProvider(SampleDataProvider):
        def fetch_candidate_universe_metadata(self) -> dict[str, str]:
            return {
                "snapshot_source": "tdx-mcp-eltdx-bridge",
                "snapshot_generated_at": "2026-07-11T06:06:19.966626+00:00",
                "kline_refresh_generated_at": "2026-07-11T14:07:52",
                "announcement_refresh_generated_at": "2026-07-11T14:28:12",
            }

    html = _sample_html(provider=MixedRefreshProvider(), provider_name="tdx-snapshot")

    assert "数据刷新时间：2026-07-11 14:28:15 北京时间" in html
    assert "数据刷新时间：2026-07-11 14:06:19 北京时间" not in html


def test_module_header_shows_manual_refresh_request_status(
    tmp_path: Path, monkeypatch
) -> None:
    report_dir = tmp_path / "daily"
    report_dir.mkdir()
    (report_dir / "pipeline.status").write_text(
        "status=ok\ngenerated_at=2026-07-11T14:28:15\nrefresh=ok\nreport=ok\n",
        encoding="utf-8",
    )
    (report_dir / "manual_refresh.status").write_text(
        "status=started\nrequested_at=2026-07-11T21:04:37+08:00\ncommand=demo\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("STOCK_TS_DAILY_REPORT_DIR", str(report_dir))
    monkeypatch.setenv("STOCK_TS_NOW", "2026-07-11T21:05:00+08:00")

    html = _sample_html()
    market_html = _workspace(html, "market")

    assert "数据刷新时间：2026-07-11 14:28:15 北京时间" in market_html
    assert "刷新请求：2026-07-11 21:04:37 北京时间（进行中）" in market_html


def test_manual_refresh_command_runs_real_pipeline(monkeypatch) -> None:
    monkeypatch.delenv("STOCK_TS_MANUAL_REFRESH_COMMAND", raising=False)

    command = _manual_refresh_command()

    assert "scripts/run_daily_pipeline.py" in command
    assert "--snapshot" in command
    assert "data/imports/tdx_snapshots.json" in command
    assert "--provider" in command
    assert "tdx-snapshot" in command


def test_manual_refresh_worker_writes_completion_status(tmp_path: Path) -> None:
    request_path = tmp_path / "manual_refresh.status"
    log_path = tmp_path / "manual_refresh.log"

    _run_manual_refresh_command(
        ["/bin/sh", "-c", "echo refreshed"],
        request_path,
        log_path,
        "2026-07-11T21:04:37+08:00",
    )

    status = request_path.read_text(encoding="utf-8")
    assert "status=ok" in status
    assert "completed_at=" in status
    assert "exit_code=0" in status
    assert "refreshed" in log_path.read_text(encoding="utf-8")


def test_pipeline_refresh_times_render_as_beijing_time(tmp_path: Path, monkeypatch) -> None:
    report_dir = tmp_path / "daily"
    report_dir.mkdir()
    (report_dir / "latest.md").write_text(
        "# 每日复盘\n\n## 今日一句话\n- 数据时间显示用北京时间。\n",
        encoding="utf-8",
    )
    (report_dir / "latest.status").write_text(
        "status=ok\ntrade_date=2026-07-11\ngenerated_at=2026-07-11T06:06:19.966626+00:00\n",
        encoding="utf-8",
    )
    (report_dir / "pipeline.status").write_text(
        "status=ok\ngenerated_at=2026-07-11T06:06:19.966626+00:00\nrefresh=ok\nreport=ok\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("STOCK_TS_DAILY_REPORT_DIR", str(report_dir))

    html = _render_latest_daily_artifact() + _render_automation_monitor_panel()

    assert "2026-07-11 14:06:19 北京时间" in html
    assert "2026-07-11T06:06:19.966626+00:00" not in html


def test_data_center_warns_when_pipeline_steps_were_skipped(tmp_path: Path, monkeypatch) -> None:
    report_dir = tmp_path / "daily"
    report_dir.mkdir()
    (report_dir / "pipeline.status").write_text(
        "\n".join(
            [
                "status=ok",
                "generated_at=2026-07-11T10:31:56",
                "refresh=skipped",
                "tdx_enrich=skipped",
                "a_share_kline=skipped",
                "external_enrich=skipped",
                "announcements=skipped",
                "report=ok",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("STOCK_TS_DAILY_REPORT_DIR", str(report_dir))
    monkeypatch.setenv("STOCK_TS_NOW", "2026-07-11T11:00:00+08:00")

    html = _sample_html(provider_name="tdx-snapshot")

    assert "自动更新未完整" in html
    assert "全市场刷新" in html
    assert "公告" in html




def test_global_freshness_bar_stays_ok_when_only_optional_stock_context_is_missing(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("STOCK_TS_DAILY_REPORT_DIR", str(tmp_path))
    monkeypatch.setenv("STOCK_TS_NOW", "2026-07-11T21:05:00+08:00")
    (tmp_path / "pipeline.status").write_text(
        "status=ok\n"
        "generated_at=2026-07-11T14:28:15\n"
        "refresh=ok\n"
        "data_chain=ok\n",
        encoding="utf-8",
    )
    (tmp_path / "data_chain_status.json").write_text(
        json.dumps({"status": "ok", "generated_at": "2026-07-11T14:28:15"}),
        encoding="utf-8",
    )

    class OptionalGapProvider(SampleDataProvider):
        def _fresh_bars(self, close: float) -> list[DailyBar]:
            return [
                DailyBar("2026-07-08", close * 0.98, close, close * 0.97, close * 0.99, 1000),
                DailyBar("2026-07-09", close * 0.99, close * 1.01, close * 0.98, close, 1200),
                DailyBar("2026-07-10", close, close * 1.02, close * 0.99, close * 1.01, 1500),
            ]

        def fetch_market(self) -> MarketRawData:
            return MarketRawData(
                trade_date="2026-07-10",
                indices=[IndexQuote("000001", "上证指数", 3996.16, -1.0, 15631.0)],
                advancing=3771,
                declining=1678,
                limit_up=134,
                limit_down=8,
                top_sectors=[("半导体", 3.1)],
            )

        def fetch_stock(self, code: str) -> StockRawData:
            return StockRawData(
                code="600519",
                name="贵州茅台",
                bars=self._fresh_bars(1500),
                fund_flow=1.2,
                fund_flow_detail={"date": "2026-07-10", "source": "akshare", "net_inflow": 1.2},
                news_items=[
                    NewsItem(
                        date="2026-07-11",
                        source="market-news",
                        title="贵州茅台市场新闻",
                        summary="新闻已采集",
                    )
                ],
                announcements=[],
                fundamental_metrics={},
                valuation={},
                data_sources=["tdx", "akshare"],
            )

        def fetch_candidate_universe(self) -> list[CandidateStockRawData]:
            return [
                CandidateStockRawData(
                    code="600000",
                    name="候选A",
                    sector="半导体",
                    bars=self._fresh_bars(20),
                    fund_flow=0.8,
                    turnover_rate=4.0,
                    amount=10.0,
                    pe_ttm=20,
                )
            ]

        def fetch_candidate_universe_metadata(self) -> dict[str, str]:
            return {
                "snapshot_source": "tdx-snapshot",
                "snapshot_generated_at": "2026-07-11T06:06:19+00:00",
                "snapshot_bars_count": "1",
                "snapshot_fund_flow_detail_count": "1",
                "snapshot_news_items_count": "1",
                "snapshot_market_news_count": "1",
                "snapshot_announcements_count": "0",
                "snapshot_fundamental_metrics_count": "0",
            }

        def fetch_market_news(self) -> list[NewsItem]:
            return [
                NewsItem(
                    date="2026-07-11",
                    source="market-news",
                    title="市场新闻",
                    summary="市场消息已采集",
                )
            ]

    html = _sample_html(
        provider=OptionalGapProvider(),
        provider_name="tdx-snapshot",
        stock_code="600519",
    )
    freshness_start = html.index('aria-label="全局研究状态"')
    freshness_end = html.index('aria-label="数据中台摘要"')
    freshness_html = html[freshness_start:freshness_end]
    data_center_html = _workspace(html, "data-center")

    assert "多维数据缺口" not in freshness_html
    assert "降级" not in freshness_html
    assert "暂停行动" not in freshness_html
    assert "可用" in freshness_html
    assert "公告" in data_center_html
    assert "基本面" in data_center_html


def test_data_center_hides_snapshot_coverage_details() -> None:
    class CoverageProvider(SampleDataProvider):
        def fetch_candidate_universe_metadata(self) -> dict[str, str]:
            return {
                "snapshot_stock_count": "12",
                "snapshot_bars_count": "12",
                "snapshot_fund_flow_detail_count": "4",
                "snapshot_news_items_count": "5",
                "snapshot_announcements_count": "0",
                "snapshot_fundamental_metrics_count": "3",
                "snapshot_valuation_count": "10",
                "snapshot_market_news_count": "2",
            }

    html = _sample_html(provider=CoverageProvider(), provider_name="tdx-snapshot")
    data_center_html = _workspace(html, "data-center")

    assert "K线行情" in data_center_html
    assert "资金面" in data_center_html
    assert "新闻舆情" in data_center_html
    assert "覆盖 12/12" not in data_center_html
    assert "覆盖 4/12" not in data_center_html
    assert "个股新闻 5/12" not in data_center_html
    assert "市场消息 2 条" not in data_center_html
    assert "公告 0/12" not in data_center_html
    assert "财务指标 3/12" not in data_center_html


def test_data_center_moves_to_bottom_workspace_and_top_keeps_one_line_summary() -> None:
    html = _sample_html()
    workspace_start = html.index('<section class="workspace-pane')
    summary_start = html.index('aria-label="数据中台摘要"')
    full_panel_start = html.index('aria-label="数据中台"')

    assert html.count('aria-label="数据中台"') == 1
    assert html.count('aria-label="数据中台摘要"') == 1
    assert summary_start < workspace_start
    assert full_panel_start > html.index('data-workspace="opportunity"')
    assert 'data-workspace="data-center"' in html
    assert 'href="#data-center"' in html


def test_data_center_surfaces_full_chain_validation_artifact(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("STOCK_TS_DAILY_REPORT_DIR", str(tmp_path))
    (tmp_path / "data_chain_status.json").write_text(
        json.dumps(
            {
                "status": "failed",
                "generated_at": "2026-07-11T09:00:00",
                "blockers": ["持仓 688362 缺少K线"],
                "warnings": ["自动任务未完整：external_enrich=skipped"],
                "modules": {
                    "market": {"status": "ok"},
                    "portfolio": {"status": "failed"},
                    "stock": {"status": "failed"},
                    "opportunities": {"status": "ok"},
                    "automation": {"status": "warn"},
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    html = _sample_html()
    data_center_html = _workspace(html, "data-center")

    assert "全链路校验" in data_center_html
    assert "持仓 688362 缺少K线" in data_center_html
    assert "market:ok" not in data_center_html
    assert "portfolio:failed" not in data_center_html
    assert "全链路存在阻断节点" in data_center_html
    assert "数据中台预警：" not in data_center_html


def test_data_center_does_not_warn_for_complete_hk_yahoo_and_hkex_context(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("STOCK_TS_DAILY_REPORT_DIR", str(tmp_path))
    (tmp_path / "data_chain_status.json").write_text(
        json.dumps(
            {
                "status": "ok",
                "generated_at": "2026-07-11T12:37:57",
                "blockers": [],
                "warnings": [],
                "modules": {"stock": {"status": "ok"}, "portfolio": {"status": "ok"}},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    class CompleteHkProvider(SampleDataProvider):
        def fetch_stock(self, code: str) -> StockRawData:
            return StockRawData(
                code="06088",
                name="FIT HON TENG",
                bars=[
                    DailyBar(
                        date="2026-07-10",
                        open=6.47,
                        high=6.70,
                        low=6.02,
                        close=6.07,
                        volume=35326209,
                    )
                ],
                fund_flow_detail={
                    "source": "derived.kline_turnover",
                    "date": "2026-07-10",
                    "amount_yuan": 214430094.69,
                },
                news_items=[
                    NewsItem(
                        date="2026-07-10T08:00:00+00:00",
                        source="Yahoo Finance",
                        title="FIT HON TENG AI server demand grows",
                        summary="AI data center connectivity demand remains active.",
                    )
                ],
                announcements=[
                    {
                        "date": "2026-07-07",
                        "source": "hkexnews",
                        "title": "Monthly Return of Equity Issuer",
                    }
                ],
                fundamental_metrics={
                    "source": "yahoo.timeseries",
                    "date": "2025-12-31",
                    "operating_revenue": 5002827000.0,
                    "net_profit": 156060000.0,
                },
                data_sources=["yahoo", "hkexnews.announcement"],
            )

    html = _sample_html(
        stock_code="06088", provider=CompleteHkProvider(), provider_name="tdx-snapshot"
    )
    data_center_html = _workspace(html, "data-center")

    assert "数据中台预警：公告" not in data_center_html
    assert "数据中台预警：基本面" not in data_center_html
    assert "公告已滞后" not in data_center_html
    assert "基本面缺字段" not in data_center_html




def test_daily_market_does_not_show_unmapped_event_noise() -> None:
    market_html = _workspace(_sample_html(), "market")

    assert "下一步验证" not in market_html
    assert "ETF行情" not in market_html
    assert "美联储" not in market_html

def test_daily_market_sector_direction_lists_top5_stocks_with_analysis() -> None:
    market_html = _workspace(_sample_html(), "market")

    assert "强势板块Top5" in market_html
    assert "弱势板块Top5" in market_html
    assert "对应股票" in market_html
    assert "分析" in market_html
    assert "兆易创新" in market_html
    assert "北方华创" in market_html
    assert "走强原因" in market_html
    assert "走弱原因" in market_html or "相对弱势原因" in market_html
    assert "强势；扩散" not in market_html
    assert "弱势；扩散" not in market_html
    assert "等待新闻、公告和基本面形成交叉验证" not in market_html


def test_market_sector_direction_explains_catalyst_not_market_snapshot() -> None:
    market_html = _workspace(_sample_html(), "market")
    sector_html = market_html[
        market_html.index("强势板块Top5") : market_html.index("专业大盘研判")
    ]

    assert "原因：" in sector_html
    assert "资金行为" in sector_html
    assert "催化" in sector_html
    assert "基本面" in sector_html
    assert "盘面证据：涨跌" not in sector_html
    assert "热度 100/100，扩散" not in sector_html
    assert "资金配合一般，作为持续性扣分项" not in sector_html


def test_professional_market_diagnosis_uses_reason_chain_not_metric_snapshot() -> None:
    market_html = _workspace(_sample_html(), "market")
    diagnosis_html = market_html[
        market_html.index("专业大盘研判") : market_html.index("异动事件")
    ]

    for text in ["资金行为", "催化核验", "基本面", "代表股"]:
        assert text in diagnosis_html

    for shallow_text in [
        "板块热度 100/100，扩散",
        "板块扩散 78%",
        "强势板块成交改善",
        ">6%资金流入样本",
    ]:
        assert shallow_text not in diagnosis_html


def test_market_mainline_summary_does_not_restate_price_results_as_reason() -> None:
    market_html = _workspace(_sample_html(), "market")
    summary_html = market_html[
        market_html.index("主线") : market_html.index("大涨大跌分析")
    ]

    for text in ["主线逻辑", "资金行为", "基本面"]:
        assert text in summary_html

    for shallow_text in [
        "涨跌 3.80%",
        "扩散 78%，涨停",
        "强度：扩散",
    ]:
        assert shallow_text not in summary_html


def test_daily_market_sections_use_distinct_research_style_conclusions() -> None:
    market_html = _workspace(_sample_html(), "market")

    for text in [
        "市场定性：",
        "主线性质：",
        "配置含义：",
        "强势归因：",
        "弱势归因：",
        "大幅波动归因：",
        "事件解读：",
        "跟踪重点：",
    ]:
        assert text in market_html

    repeated_fragments = [
        "原因：催化核验",
        "资金行为：",
        "基本面：代表股估值/财务待补",
    ]
    for fragment in repeated_fragments:
        assert market_html.count(fragment) <= 6

    for stale_phrase in [
        "赚钱效应强，优先看板块前排和持续放量个股",
        "当前不是全面行情，是结构性机会",
        "市场以轮动为主",
    ]:
        assert stale_phrase not in market_html


def test_market_sector_analysis_shows_conclusion_not_full_method_chain() -> None:
    market_html = _workspace(_sample_html(), "market")

    assert "结论" in market_html
    for text in [
        "板块方法链",
        "daily_stock_analysis 信号归因",
        "TradingAgents 板块审议",
        "板块分析师团队",
        "多空审议",
        "组合经理",
    ]:
        assert text not in market_html


def test_portfolio_stocks_hide_dual_git_method_chain_summary_only() -> None:
    portfolio_html = _workspace(_sample_html(), "portfolio")

    for text in ["组合风控结论", "处置依据", "复核触发", "失效条件"]:
        assert text in portfolio_html

    for text in [
        "daily_stock_analysis 信号归因",
        "TradingAgents",
        "分析师团队",
        "多空审议",
        "交易员",
        "组合经理最终意见",
    ]:
        assert text not in portfolio_html


def test_market_sector_top5_representatives_use_live_news_when_snapshot_missing() -> None:
    class SectorNewsProvider(SampleDataProvider):
        def fetch_sectors(self) -> list[SectorRawData]:
            return [
                SectorRawData(
                    name="海洋经济",
                    pct_chg=3.2,
                    advancing_ratio=0.76,
                    amount_change=18.0,
                    fund_flow=2.4,
                    limit_up_count=2,
                ),
                SectorRawData(
                    name="机器人",
                    pct_chg=2.4,
                    advancing_ratio=0.74,
                    amount_change=16.0,
                    fund_flow=2.2,
                    limit_up_count=2,
                ),
            ]

        def fetch_candidate_universe(self) -> list[CandidateStockRawData]:
            higher_ranked = [
                CandidateStockRawData(
                    code=f"3001{index:02d}",
                    name=f"高分候选{index}",
                    sector="机器人",
                    bars=[
                        DailyBar("2026-07-06", 10.0, 10.2, 9.9, 10.0, 1000),
                        DailyBar("2026-07-07", 10.2, 10.6, 10.1, 10.5, 1300),
                        DailyBar("2026-07-08", 10.5, 11.0, 10.4, 10.9, 1700),
                        DailyBar("2026-07-09", 10.9, 11.4, 10.8, 11.3, 2200),
                        DailyBar("2026-07-10", 11.3, 11.8, 11.2, 11.7, 3200),
                    ],
                    fund_flow=3.0,
                    turnover_rate=7.0,
                    amount=25.0,
                    pe_ttm=28.0,
                )
                for index in range(9)
            ]
            return higher_ranked + [
                CandidateStockRawData(
                    code="300065",
                    name="海兰信",
                    sector="海洋经济",
                    bars=[
                        DailyBar("2026-07-09", 10.0, 10.2, 9.8, 10.0, 1000),
                        DailyBar("2026-07-10", 10.2, 10.5, 10.1, 10.3, 1600),
                    ],
                    fund_flow=0.2,
                    turnover_rate=8.6,
                    amount=8.0,
                    pe_ttm=34.0,
                )
            ]

    def stock_news_fetcher(symbol: str, limit: int) -> list[NewsItem]:
        if symbol == "300065":
            return [
                NewsItem(
                    date="2026-07-10",
                    source="联网新闻",
                    title="海兰信中标海洋监测项目",
                    summary="订单催化",
                    sentiment="positive",
                )
            ][:limit]
        return []

    market_html = _workspace(
        _sample_html(
            provider=SectorNewsProvider(),
            provider_name="tdx-snapshot",
            stock_news_fetcher=stock_news_fetcher,
        ),
        "market",
    )

    assert "强势板块Top5" in market_html
    assert "海兰信中标海洋监测项目" in market_html
    assert "海洋经济" in market_html
    assert "联网核验未见可验证新增催化" not in market_html


def test_daily_market_explains_mainline_and_lists_top6_strongest_stocks() -> None:
    def stock_news_fetcher(symbol: str, limit: int) -> list[NewsItem]:
        return [
            NewsItem(
                date="2026-07-10",
                source="东方财富",
                title=f"{symbol}主线强股消息",
                summary="主线方向存在产业催化",
                sentiment="positive",
            )
        ][:limit]

    market_html = _workspace(_sample_html(stock_news_fetcher=stock_news_fetcher), "market")

    assert "主线介绍" in market_html
    assert "最强股票Top6" in market_html
    assert "主线逻辑" in market_html
    assert "一周趋势" in market_html
    assert "资金面" in market_html
    assert "主线强股消息" in market_html
    assert "半导体" in market_html
    assert "机器人" in market_html
    assert "人工智能" in market_html
    assert "兆易创新" in market_html
    assert "寒武纪" in market_html
    assert "中信证券" in market_html
    assert market_html.count("mainline-stock-row") >= 6
    assert "主线在哪里" not in market_html


def test_market_sector_and_wide_move_causes_use_news_fundamental_not_price_only() -> None:
    class CausalProvider(SampleDataProvider):
        def fetch_sectors(self) -> list[SectorRawData]:
            return [
                SectorRawData(
                    name="机器人",
                    pct_chg=3.2,
                    advancing_ratio=0.76,
                    amount_change=18.0,
                    fund_flow=2.4,
                    limit_up_count=3,
                ),
                SectorRawData(
                    name="白酒",
                    pct_chg=-2.1,
                    advancing_ratio=0.32,
                    amount_change=-10.0,
                    fund_flow=-1.8,
                    limit_up_count=0,
                ),
            ]

        def fetch_candidate_universe(self) -> list[CandidateStockRawData]:
            return [
                CandidateStockRawData(
                    code="300111",
                    name="订单机器人",
                    sector="机器人",
                    bars=[
                        DailyBar("2026-07-09", 10.0, 10.2, 9.8, 10.0, 1000),
                        DailyBar("2026-07-10", 10.2, 11.0, 10.1, 10.8, 2600),
                    ],
                    fund_flow=2.1,
                    turnover_rate=8.6,
                    amount=18.0,
                    pe_ttm=24.0,
                    news_items=[
                        NewsItem(
                            date="2026-07-10",
                            source="东方财富",
                            title="订单机器人签下机器人订单",
                            summary="订单增长",
                            sentiment="positive",
                        )
                    ],
                    announcements=[
                        {
                            "title": "订单机器人关于重大合同的公告",
                            "date": "2026-07-10",
                        }
                    ],
                ),
                CandidateStockRawData(
                    code="600333",
                    name="风险白酒",
                    sector="白酒",
                    bars=[
                        DailyBar("2026-07-09", 20.0, 20.2, 19.8, 20.0, 1000),
                        DailyBar("2026-07-10", 19.8, 20.0, 18.3, 18.5, 3100),
                    ],
                    fund_flow=-1.8,
                    turnover_rate=7.2,
                    amount=15.0,
                    pe_ttm=68.0,
                    news_items=[
                        NewsItem(
                            date="2026-07-10",
                            source="财联社",
                            title="风险白酒库存压力上升",
                            summary="渠道压力",
                            sentiment="negative",
                        )
                    ],
                ),
            ]

    market_html = _workspace(
        _sample_html(provider=CausalProvider(), provider_name="tdx-snapshot"),
        "market",
    )

    for text in [
        "消息面：订单机器人签下机器人订单",
        "公告：订单机器人关于重大合同的公告",
        "基本面：订单机器人PE(TTM) 24.0",
        "消息面：风险白酒库存压力上升",
        "基本面：风险白酒PE(TTM) 68.0",
    ]:
        assert text in market_html
    for phenomenon in [
        "多数成份同步上涨",
        "板块内多数个股同步上涨",
        "成交额改善",
        "成交额 18.0 亿",
        "价格大幅波动",
    ]:
        assert phenomenon not in market_html


def test_market_module_surfaces_mcp_market_movers_as_events() -> None:
    from stock_ts.models import NewsItem

    class MoverProvider(SampleDataProvider):
        def fetch_market_news(self) -> list[NewsItem]:
            return [
                NewsItem(
                    date="2026-07-11",
                    source="longbridge.mcp.市场异动",
                    title="中芯国际异动：波动超 20 日均值",
                    summary="半导体厂商；涨跌幅 -5.62%",
                    sentiment="neutral",
                ),
                NewsItem(
                    date="2026-07-11",
                    source="longbridge.mcp.新闻",
                    title="A股半导体板块走强",
                    summary="硬科技方向活跃",
                    sentiment="positive",
                ),
                NewsItem(
                    date="2026-07-11",
                    source="longbridge.mcp.新闻",
                    title="商业航天板块引爆ETF行情 有ETF单日净申购近21亿元",
                    summary="泛ETF新闻，没有对应个股",
                    sentiment="neutral",
                ),
                NewsItem(
                    date="2026-07-11",
                    source="longbridge.mcp.新闻",
                    title="美联储半年度政策报告：关税和中东推高通胀",
                    summary="宏观新闻，没有对应A股主题或个股",
                    sentiment="neutral",
                ),
                NewsItem(
                    date="2026-07-11",
                    source="longbridge.mcp.新闻",
                    title="美联储半年度政策报告：关税和中东推高通胀 AI成双刃剑",
                    summary="宏观政策新闻，不应因 AI 关键词进入股票异动",
                    sentiment="neutral",
                ),
            ]

    market_html = _workspace(
        _sample_html(provider=MoverProvider(), provider_name="tdx-snapshot"), "market"
    )

    assert "异动事件" in market_html
    assert "对应主题" in market_html
    assert "对应股票" in market_html
    assert "事件原因" in market_html
    assert "半导体" in market_html
    assert "中芯国际" in market_html
    assert "2026-07-11" in market_html
    assert "波动超 20 日均值" in market_html
    assert "商业航天" not in market_html
    assert "ETF单日净申购" not in market_html
    assert "美联储半年度政策报告" not in market_html
    assert "宏观政策新闻" not in market_html
    assert "longbridge.mcp.市场异动" not in market_html
    assert "需要看对应股票承接" not in market_html


def test_market_module_builds_price_movers_from_candidate_scan_without_news() -> None:
    market_html = _workspace(_sample_html(), "market")

    assert "异动事件" in market_html
    assert "对应主题" in market_html
    assert "对应股票" in market_html
    assert "事件原因" in market_html
    assert "价格异动" not in market_html


def test_market_event_panel_uses_compact_card_layout_not_wide_table() -> None:
    html = _sample_html()
    market_html = _workspace(html, "market")

    assert 'class="market-event-card-list"' in market_html
    assert 'class="market-event-card"' in market_html
    assert "market-event-summary-list" not in html


def test_market_event_theme_level_events_show_top3_stock_moves() -> None:
    from stock_ts.models import NewsItem

    class ThemeEventProvider(SampleDataProvider):
        def fetch_market_news(self) -> list[NewsItem]:
            return [
                NewsItem(
                    date="2026-07-11 10:15",
                    source="longbridge.mcp.新闻",
                    title="半导体板块盘中走强",
                    summary="先进制程与存储方向活跃",
                    sentiment="positive",
                )
            ]

        def fetch_candidate_universe(self) -> list[CandidateStockRawData]:
            return [
                CandidateStockRawData(
                    code="300111",
                    name="强芯一号",
                    sector="半导体",
                    bars=[
                        DailyBar("2026-07-10", 10.0, 10.1, 9.9, 10.0, 1000),
                        DailyBar("2026-07-11", 10.1, 11.0, 10.0, 10.8, 2400),
                    ],
                    amount=12.0,
                ),
                CandidateStockRawData(
                    code="300222",
                    name="强芯二号",
                    sector="半导体",
                    bars=[
                        DailyBar("2026-07-10", 20.0, 20.2, 19.8, 20.0, 1000),
                        DailyBar("2026-07-11", 20.1, 21.5, 20.0, 21.0, 2200),
                    ],
                    amount=10.0,
                ),
                CandidateStockRawData(
                    code="300333",
                    name="强芯三号",
                    sector="半导体",
                    bars=[
                        DailyBar("2026-07-10", 30.0, 30.2, 29.8, 30.0, 1000),
                        DailyBar("2026-07-11", 30.1, 31.0, 30.0, 30.9, 1800),
                    ],
                    amount=8.0,
                ),
                CandidateStockRawData(
                    code="300444",
                    name="强芯四号",
                    sector="半导体",
                    bars=[
                        DailyBar("2026-07-10", 40.0, 40.2, 39.8, 40.0, 1000),
                        DailyBar("2026-07-11", 40.1, 40.8, 40.0, 40.4, 1600),
                    ],
                    amount=6.0,
                ),
            ]

    market_html = _workspace(
        _sample_html(provider=ThemeEventProvider(), provider_name="tdx-snapshot"),
        "market",
    )
    event_html = market_html[market_html.index("异动事件") :]

    assert "异动事件" in event_html
    assert "对应主题：半导体" in event_html
    assert "强芯一号 8.00%" in event_html
    assert "强芯二号 5.00%" in event_html
    assert "强芯三号 3.00%" in event_html
    assert "强芯四号" not in event_html


def test_market_event_extracted_stock_uses_event_pct_when_quote_missing() -> None:
    from stock_ts.models import NewsItem

    class ExtractedStockProvider(SampleDataProvider):
        def fetch_market_news(self) -> list[NewsItem]:
            return [
                NewsItem(
                    date="2026-07-11 10:18",
                    source="longbridge.mcp.市场异动",
                    title="中芯国际异动：波动超 20 日均值",
                    summary="半导体厂商；涨跌幅 -5.62%",
                    sentiment="neutral",
                )
            ]

    market_html = _workspace(
        _sample_html(provider=ExtractedStockProvider(), provider_name="tdx-snapshot"),
        "market",
    )

    assert "中芯国际 -5.62%" in market_html
