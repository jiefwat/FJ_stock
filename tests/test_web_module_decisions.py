import json

from stock_ts.models import DailyBar, SectorRawData, StockRawData
from stock_ts.providers.sample import SampleDataProvider
from stock_ts.providers.tdx_snapshot_provider import TdxSnapshotProvider
from stock_ts.web import render_page


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


def test_four_workspaces_do_not_repeat_global_precision_summary() -> None:
    html = _sample_html()

    assert "精准摘要" not in html
    assert "展开细节" not in html
    assert "precision-detail-fold" not in html
    for workspace in ["market", "portfolio", "stock", "opportunity"]:
        section = _workspace(html, workspace)
        assert "module-title" in section
        assert "detail-shell" in section or "data-table" in section


def test_core_modules_show_decision_state_not_just_raw_data() -> None:
    html = _sample_html()

    assert "仓位动作</span><strong>可以进攻</strong>" in html
    assert "每日大盘" in html
    assert "持仓明细" in html
    assert "股票摘要" in html
    assert "机会状态" in html
    assert "候选列表" in html


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


def test_global_data_center_surfaces_collection_channels_and_alerts() -> None:
    html = _sample_html()

    for text in [
        "专业数据中台",
        "采集渠道",
        "采集状态",
        "更新时间",
        "未采集/缺失",
        "影响分析预警",
        "人工复核入口",
        "核对K线",
        "K线行情",
        "资金面",
        "新闻舆情",
        "公告",
        "基本面",
    ]:
        assert text in html


def test_market_module_uses_real_breadth_counts_instead_of_unreturned() -> None:
    market_html = _workspace(_sample_html(), "market")

    assert "上涨/下跌/平盘" in market_html
    assert "未返回" not in market_html
    assert "风险项" in market_html
    assert "看热点机会" in market_html


def test_daily_market_module_matches_market_gate_design_doc() -> None:
    market_html = _workspace(_sample_html(), "market")

    for text in [
        "市场摘要",
        "市场总闸门",
        "指数表现",
        "市场宽度",
        "板块方向",
        "风险项",
        "数据源",
        "交易日",
        "验证条件",
        "失效条件",
    ]:
        assert text in market_html


def test_daily_market_module_surfaces_conclusion_card_fields() -> None:
    market_html = _workspace(_sample_html(), "market")

    for text in [
        "市场摘要",
        "市场状态",
        "风险暴露",
        "目标现金",
        "主线",
        "下一步",
        "异动清单",
        "事件日历",
        "只观察",
    ]:
        assert text in market_html


def test_opportunity_module_surfaces_theme_sentiment_and_candidates() -> None:
    html = _sample_html()
    opportunity_html = _workspace(html, "opportunity")

    for text in [
        "板块热度",
        "情绪温度",
        "候选观察池",
        "赚钱效应",
        "亏钱效应",
        "入选理由",
        "下一步",
    ]:
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


def test_opportunity_module_uses_strategy_funnel_and_risk_exclusion() -> None:
    opportunity_html = _workspace(_sample_html(), "opportunity")

    for text in [
        "机会状态",
        "策略通道",
        "机会总闸门",
        "主线强势",
        "资金抱团",
        "放量突破",
        "超跌修复",
        "公告催化",
        "风险排除",
        "筛选条件",
        "进入股票分析",
    ]:
        assert text in opportunity_html


def test_opportunity_module_renders_candidate_cards_with_quality_and_actions() -> None:
    opportunity_html = _workspace(_sample_html(), "opportunity")

    for text in [
        "候选列表",
        "策略：",
        "入选证据",
        "主要风险",
        "数据质量",
        "下一步：进入股票分析验证六维证据；不直接买入",
        "可验证",
        "只观察",
        "待补数据",
    ]:
        assert text in opportunity_html


def test_opportunity_candidate_links_carry_source_strategy_and_evidence() -> None:
    opportunity_html = _workspace(_sample_html(), "opportunity")

    assert "candidate_source=opportunity" in opportunity_html
    assert "candidate_strategy_label=" in opportunity_html
    assert "candidate_evidence=" in opportunity_html


def test_stock_module_surfaces_decision_chain_and_holding_cost() -> None:
    html = _sample_html(stock_code="603278")
    stock_html = _workspace(html, "stock")

    for text in [
        "个股三面复核",
        "个股证据抽屉",
        "持仓成本视角",
        "交易触发",
        "风险原因",
        "消息事件",
        "数据状态",
    ]:
        assert text in stock_html


def test_stock_module_uses_six_dimension_evidence_wall() -> None:
    stock_html = _workspace(_sample_html(stock_code="603278"), "stock")

    for text in [
        "当前结论",
        "六类证据",
        "技术面",
        "基本面",
        "资金面",
        "消息公告",
        "板块主题",
        "成本位置",
        "多空反证",
        "禁止动作",
    ]:
        assert text in stock_html


def test_stock_module_surfaces_single_stock_verdict_fields() -> None:
    stock_html = _workspace(_sample_html(stock_code="603278"), "stock")

    for text in [
        "当前结论",
        "当前动作",
        "最强证据",
        "最大反证",
        "组合影响",
        "仓位上限",
        "当前持仓状态",
    ]:
        assert text in stock_html


def test_stock_module_requires_kline_fund_news_and_fundamental_blocks() -> None:
    stock_html = _workspace(_sample_html(stock_code="603278"), "stock")

    for text in [
        "数据质量",
        "K线数据",
        "资金面",
        "消息面",
        "基本面",
        "已用于分析",
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

    assert "K线数据" in stock_html
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

    assert "数据中台预警：资金面" in html
    assert "资金流/成交侧明细" in html
    assert "数据中台预警：公告" in html
    assert "影响风险公告、财报事件和监管风险判断" in html


def test_stock_module_shows_candidate_source_context_when_entered_from_opportunity() -> None:
    stock_html = _sample_stock_html(
        stock_code="603278",
        candidate_source="opportunity",
        candidate_strategy_label="主线强势 + 放量突破",
        candidate_evidence="所属主题排名前 5，成交额放大",
    )

    assert "来源上下文" in stock_html
    assert "股市机会" in stock_html
    assert "主线强势 + 放量突破" in stock_html
    assert "所属主题排名前 5，成交额放大" in stock_html


def test_portfolio_module_surfaces_overall_diagnosis_and_position_overview() -> None:
    portfolio_html = _workspace(_sample_html(), "portfolio")

    for text in [
        "我的持仓",
        "持仓明细",
        "处理队列",
        "账本状态",
        "组合整体诊断",
        "处理优先级",
        "目标现金/低风险",
    ]:
        assert text in portfolio_html


def test_portfolio_module_reads_like_disposal_console_before_table() -> None:
    portfolio_html = _workspace(_sample_html(), "portfolio")

    for text in [
        "组合摘要",
        "今日先处理",
        "最大风险",
        "行业暴露",
        "账本状态",
        "下一步复核",
    ]:
        assert text in portfolio_html

    assert portfolio_html.index("今日先处理") < portfolio_html.index("持仓风险处置")


def test_portfolio_module_uses_four_lane_disposal_queue() -> None:
    portfolio_html = _workspace(_sample_html(), "portfolio")

    for text in [
        "处理队列",
        "必须处理",
        "观察",
        "可继续",
        "待补数据",
        "风险预算",
        "成本位置",
        "持仓账本来源",
        "公开只读",
    ]:
        assert text in portfolio_html


def test_portfolio_module_surfaces_health_light_and_execution_boundaries() -> None:
    portfolio_html = _workspace(_sample_html(), "portfolio")

    for text in [
        "组合摘要",
        "组合状态",
        "现金比例",
        "操作边界",
        "失效线",
        "仓位上限",
        "禁止动作",
    ]:
        assert text in portfolio_html


def test_tdx_snapshot_defensive_market_keeps_defensive_action() -> None:
    html = _sample_html(
        stock_code="002487",
        provider_name="tdx-snapshot",
        provider=TdxSnapshotProvider("data/imports/tdx_snapshots.json"),
    )

    assert "仓位动作</span><strong>防守观察</strong>" in html
    assert "暂停行动" in html
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

    assert "亏钱效应" in opportunity_html
    assert "跌停" in opportunity_html


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


def test_data_center_surfaces_mcp_market_news_channel_metadata() -> None:
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

    assert "longbridge.mcp" in html
    assert "2026-07-11T01:00:00Z" in html
