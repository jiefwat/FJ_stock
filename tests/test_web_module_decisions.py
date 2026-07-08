from stock_ts.models import SectorRawData
from stock_ts.providers.sample import SampleDataProvider
from stock_ts.providers.tdx_snapshot_provider import TdxSnapshotProvider
from stock_ts.web import _sector_next_check, _sector_strategy, render_page


def test_workspaces_do_not_repeat_global_precision_summary() -> None:
    html = render_page(
        stock_code="600519",
        provider_name="sample",
        provider=SampleDataProvider(),
        holdings_path="data/portfolio/holdings.csv",
    )

    assert "精准摘要" not in html
    assert "展开细节" not in html
    assert "precision-detail-fold" not in html
    for workspace in [
        "home",
        "market",
        "sector",
        "sentiment",
        "screener",
        "stock",
        "portfolio",
        "watchlist",
        "daily",
        "notify",
        "settings",
    ]:
        start = html.index(f'id="{workspace}"')
        end = html.find('class="workspace-pane', start + 1)
        section = html[start : end if end != -1 else len(html)]
        assert "module-title" in section


def test_dense_workspaces_show_content_without_extra_expand_gate() -> None:
    html = render_page(
        stock_code="600519",
        provider_name="sample",
        provider=SampleDataProvider(),
        holdings_path="data/portfolio/holdings.csv",
    )

    for workspace in ["market", "sector", "screener", "stock", "portfolio", "daily"]:
        start = html.index(f'id="{workspace}"')
        end = html.find('class="workspace-pane', start + 1)
        section = html[start : end if end != -1 else len(html)]
        assert "展开细节" not in section
        assert "precision-detail-fold" not in section


def test_core_modules_show_decision_state_not_just_raw_data() -> None:
    html = render_page(
        stock_code="600519",
        provider_name="sample",
        provider=SampleDataProvider(),
        holdings_path="data/portfolio/holdings.csv",
    )

    assert "仓位动作</span><strong>可以进攻</strong>" in html
    assert "主线状态</span><strong>主线确认</strong>" in html
    assert "情绪周期</span><strong>情绪偏强</strong>" in html
    assert "风险状态</span><strong>亏钱效应可控</strong>" in html


def test_page_surfaces_complete_research_workbench_model() -> None:
    html = render_page(
        stock_code="600519",
        provider_name="sample",
        provider=SampleDataProvider(),
        holdings_path="data/portfolio/holdings.csv",
    )

    assert "今日行动台" in html
    assert "数据可信度" in html
    assert "大盘环境" in html
    assert "主线板块" in html
    assert "候选机会" in html
    assert "组合风险" in html
    assert "每日复盘" in html
    assert "投研工作台" not in html


def test_home_page_surfaces_expert_market_board_not_only_navigation() -> None:
    html = render_page(
        stock_code="600519",
        provider_name="sample",
        provider=SampleDataProvider(),
        holdings_path="data/portfolio/holdings.csv",
    )

    home_start = html.index('id="home"')
    market_start = html.index('id="market"')
    home_html = html[home_start:market_start]

    assert "上涨 / 下跌 / 平盘" in home_html
    assert "领涨板块 Top 5" in home_html
    assert "领跌板块 Top 5" in home_html
    assert "资金与情绪" in home_html
    assert "消息催化" in home_html
    assert "强势股票 20" in home_html
    assert "风险股票 20" in home_html
    assert home_html.count(">分析</a>") >= 20


def test_home_sector_board_hides_abnormal_pct_and_uses_distinct_judgement() -> None:
    class WeirdSectorProvider(SampleDataProvider):
        def fetch_sectors(self) -> list[SectorRawData]:
            return [
                SectorRawData(
                    "医疗器械概念",
                    211.65,
                    1.0,
                    6.38,
                    limit_up_count=1,
                    high_divergence=True,
                ),
                SectorRawData("人工智能", 30.0, 1.0, 2.09, limit_up_count=1, high_divergence=True),
                SectorRawData("芯片", 20.0, 1.0, 26.65, limit_up_count=6, high_divergence=True),
                SectorRawData("创新药", 20.0, 1.0, 8.01, limit_up_count=3, high_divergence=True),
                SectorRawData("ST板块", 19.95, 1.0, 0.02, limit_up_count=1, high_divergence=True),
                SectorRawData("先进封装", 19.06, 1.0, 0.03, limit_up_count=1, high_divergence=True),
            ]

    html = render_page(
        stock_code="600519",
        provider_name="sample",
        provider=WeirdSectorProvider(),
        holdings_path="data/portfolio/holdings.csv",
    )

    home_start = html.index('id="home"')
    market_start = html.index('id="market"')
    home_html = html[home_start:market_start]

    assert "211.65%" not in home_html
    assert "30.00%" not in home_html
    assert "样本异常" in home_html
    assert "样本强度" in home_html
    assert home_html.count("全市场板块多为上涨，该板块属于相对弱势") <= 1


def test_market_module_uses_real_breadth_counts_instead_of_unreturned() -> None:
    html = render_page(
        stock_code="600519",
        provider_name="sample",
        provider=SampleDataProvider(),
        holdings_path="data/portfolio/holdings.csv",
    )

    market_start = html.index('id="market"')
    sector_start = html.index('id="sector"')
    market_html = html[market_start:sector_start]

    assert "上涨/下跌/平盘" in market_html
    assert "3620 / 1260 /" in market_html
    assert "未返回 / 未返回" not in market_html


def test_global_data_signal_marks_sample_data_as_degraded() -> None:
    html = render_page(
        stock_code="600519",
        provider_name="sample",
        provider=SampleDataProvider(),
        holdings_path="data/portfolio/holdings.csv",
    )

    assert "全局数据信号" in html
    assert "降级" in html
    assert "数据可信度" in html


def test_global_data_signal_marks_refreshed_tdx_candidate_prices_as_available() -> None:
    html = render_page(
        stock_code="002487",
        provider_name="tdx-snapshot",
        provider=TdxSnapshotProvider("data/imports/tdx_snapshots.json"),
        holdings_path="data/portfolio/holdings.csv",
    )

    assert "全局数据信号" in html
    assert "可用" in html
    assert "候选价格</span><strong>可用" in html
    assert "排序暂停" not in html


def test_sector_module_surfaces_multi_dimension_theme_and_strong_stocks() -> None:
    html = render_page(
        stock_code="600519",
        provider_name="sample",
        provider=SampleDataProvider(),
        holdings_path="data/portfolio/holdings.csv",
    )

    sector_start = html.index('id="sector"')
    sentiment_start = html.index('id="sentiment"')
    sector_html = html[sector_start:sentiment_start]

    assert "主题强弱榜" in sector_html
    assert "扩散" in sector_html
    assert "涨停" in sector_html
    assert "强势个股" in sector_html
    assert "兆易创新" in sector_html
    assert "北方华创" in sector_html


def test_sector_theme_rows_do_not_repeat_the_same_generic_strategy() -> None:
    class Sector:
        def __init__(
            self,
            name: str,
            pct_chg: float,
            amount_change: float,
            limit_up_count: int,
            advancing_ratio: float = 1.0,
            risk: str = "高位分歧风险",
        ) -> None:
            self.name = name
            self.pct_chg = pct_chg
            self.amount_change = amount_change
            self.limit_up_count = limit_up_count
            self.advancing_ratio = advancing_ratio
            self.risk = risk
            self.heat_score = 100

    rows = [
        Sector("芯片", 18.66, 19.5, 3),
        Sector("光刻机", 17.27, 39.2, 2),
        Sector("MicroLED", 315.02, 130.3, 1),
        Sector("消费电子概念", 16.69, 40.3, 2),
    ]
    strategies = [_sector_strategy(item) for item in rows]
    checks = [_sector_next_check(item) for item in rows]

    assert len(set(strategies)) == len(strategies)
    assert len(set(checks)) >= 3
    assert strategies.count("只看前排承接，分歧未消化前不追后排") <= 1


def test_candidate_and_sector_tables_avoid_copy_paste_default_phrases() -> None:
    html = render_page(
        stock_code="600519",
        provider_name="sample",
        provider=SampleDataProvider(),
        holdings_path="data/portfolio/holdings.csv",
    )

    repeated_defaults = [
        "未触发高波动或估值类硬风险，但需等待次日确认",
        "竞价不明显弱于板块龙头",
        "开盘后 30 分钟成交额维持活跃",
        "股价不快速跌破 5 日均线",
        "风险可控，继续看前排承接",
        "所属板块 半导体 强度",
        "轮动观察，先找低位补涨和强势回踩",
        "涨停家数是否继续增加；涨停梯队是否晋级",
    ]
    for phrase in repeated_defaults:
        assert html.count(phrase) <= 2, phrase


def test_stock_module_surfaces_core_evidence_chain() -> None:
    html = render_page(
        stock_code="600519",
        provider_name="sample",
        provider=SampleDataProvider(),
        holdings_path="data/portfolio/holdings.csv",
    )

    assert "核心证据链" in html
    assert "趋势证据" in html
    assert "风险边界" in html
    assert "公告闸门" in html
    assert "操作条件" in html


def test_stock_module_surfaces_conditional_execution_panel() -> None:
    html = render_page(
        stock_code="600519",
        provider_name="sample",
        provider=SampleDataProvider(),
        holdings_path="data/portfolio/holdings.csv",
    )

    assert "执行条件" in html
    assert "开仓条件" in html
    assert "加仓条件" in html
    assert "止损条件" in html
    assert "降风险条件" in html
    assert "不做事项" in html


def test_portfolio_module_surfaces_handling_priority() -> None:
    html = render_page(
        stock_code="600519",
        provider_name="sample",
        provider=SampleDataProvider(),
        holdings_path="data/portfolio/holdings.csv",
    )

    assert "处理优先级" in html
    assert "组合动作" in html
    assert "第一大仓位" in html
    assert "首要风险" in html
    assert "市场约束" in html


def test_report_module_surfaces_next_day_plan() -> None:
    html = render_page(
        stock_code="600519",
        provider_name="sample",
        provider=SampleDataProvider(),
        holdings_path="data/portfolio/holdings.csv",
    )

    assert "明日计划" in html
    assert "风险复核" in html
    assert "数据复核" in html


def test_daily_module_surfaces_market_sector_portfolio_and_opportunities() -> None:
    html = render_page(
        stock_code="600519",
        provider_name="sample",
        provider=SampleDataProvider(),
        holdings_path="data/portfolio/holdings.csv",
    )

    daily_start = html.index('id="daily"')
    notify_start = html.index('id="notify"')
    daily_html = html[daily_start:notify_start]

    assert "大盘情况" in daily_html
    assert "板块情况" in daily_html
    assert "我的持仓" in daily_html
    assert "未来机会" in daily_html
    assert "主要指数" in daily_html
    assert "主线板块" in daily_html
    assert "组合健康度" in daily_html
    assert "持仓明细" in daily_html
    assert "机会观察" in daily_html
    assert "<li>市场</li>" not in daily_html
    assert "<li>持仓</li>" not in daily_html
    assert "<li>个股</li>" not in daily_html


def test_smart_select_surfaces_research_queue_when_candidates_are_reliable() -> None:
    html = render_page(
        stock_code="600519",
        provider_name="sample",
        provider=SampleDataProvider(),
        holdings_path="data/portfolio/holdings.csv",
    )

    assert "候选池状态" in html
    assert "下一只" in html
    assert "候选可排序" in html


def test_smart_select_surfaces_tdx_research_queue_when_candidates_are_reliable() -> None:
    html = render_page(
        stock_code="002487",
        provider_name="tdx-snapshot",
        provider=TdxSnapshotProvider("data/imports/tdx_snapshots.json"),
        holdings_path="data/portfolio/holdings.csv",
    )

    assert "候选池状态" in html
    assert "候选可排序" in html
    assert "主题覆盖" in html
    assert "候选池缺少真实日线" not in html
    assert 'data-action="filter-candidates"' in html
    assert "<th>分数</th>" in html
    assert "<th>涨跌</th>" in html


def test_smart_select_supports_strategy_filters() -> None:
    html = render_page(
        stock_code="600519",
        provider_name="sample",
        provider=SampleDataProvider(),
        holdings_path="data/portfolio/holdings.csv",
        candidate_strategy="hot",
    )

    screener_start = html.index('id="screener"')
    stock_start = html.index('id="stock"')
    screener_html = html[screener_start:stock_start]

    assert "策略筛选" in screener_html
    assert "资金抱团" in screener_html
    assert "市场热度" in screener_html
    assert "超跌反弹" in screener_html
    assert "强势突破" in screener_html
    assert "低位放量" in screener_html
    assert "趋势共振" in screener_html
    assert "业绩质量" in screener_html
    assert "消息催化" in screener_html
    assert "缩量回踩" in screener_html
    assert "高股息防守" in screener_html
    assert 'name="candidate_strategy"' in screener_html
    assert "当前策略</span><strong>市场热度" in screener_html
    assert "策略命中" in screener_html


def test_smart_select_surfaces_strategy_map_and_risk_lane() -> None:
    html = render_page(
        stock_code="600519",
        provider_name="sample",
        provider=SampleDataProvider(),
        holdings_path="data/portfolio/holdings.csv",
        candidate_strategy="risk",
    )

    screener_start = html.index('id="screener"')
    stock_start = html.index('id="stock"')
    screener_html = html[screener_start:stock_start]

    assert "策略地图" in screener_html
    assert "资金抱团" in screener_html
    assert "市场热度" in screener_html
    assert "超跌反弹" in screener_html
    assert "风险排查" in screener_html
    assert "高风险先排除" in screener_html
    assert 'name="candidate_strategy" value="risk"' in screener_html
    assert "当前策略</span><strong>风险排查" in screener_html


def test_smart_select_declares_market_wide_source_not_holdings(tmp_path) -> None:
    holdings_path = tmp_path / "holdings.csv"
    holdings_path.write_text(
        "code,name,shares,cost_price,sector,note\n000001,平安银行,100,10.50,银行,只用于组合测试\n",
        encoding="utf-8",
    )

    html = render_page(
        stock_code="600519",
        provider_name="sample",
        provider=SampleDataProvider(),
        holdings_path=str(holdings_path),
    )

    screener_start = html.index('id="screener"')
    stock_start = html.index('id="stock"')
    screener_html = html[screener_start:stock_start]

    assert "扫描范围" in screener_html
    assert "全市场A股" in screener_html
    assert "全市场候选池" not in screener_html
    assert "来源不是持仓" in screener_html
    assert "<strong>25 只</strong>" in screener_html
    assert "兆易创新" in screener_html
    assert "平安银行" not in screener_html


def test_smart_select_uses_tdx_snapshot_scan_metadata_for_full_market_scope() -> None:
    class MetadataSampleProvider(SampleDataProvider):
        def fetch_candidate_universe_metadata(self) -> dict[str, str]:
            return {
                "scope": "all_a_share",
                "scanned_count": "5128",
                "returned_count": "300",
                "enriched_count": "30",
                "enrichment_status": "partial",
                "enrichment_method": "前排候选已补真实日线/主题，其余为行情截面",
                "selection_method": "全市场行情分页扫描后按涨跌、成交额和量能预筛",
            }

    html = render_page(
        stock_code="600519",
        provider_name="sample",
        provider=MetadataSampleProvider(),
        holdings_path="data/portfolio/holdings.csv",
    )

    screener_start = html.index('id="screener"')
    stock_start = html.index('id="stock"')
    screener_html = html[screener_start:stock_start]

    assert "全市场扫描" in screener_html
    assert "5128 只" in screener_html
    assert "预筛候选" in screener_html
    assert "300 只" in screener_html
    assert "深度补强" in screener_html
    assert "30 / 300" in screener_html
    assert "前排候选已补真实日线/主题" in screener_html
    assert "全市场行情分页扫描" in screener_html


def test_stock_module_surfaces_five_dimension_analysis() -> None:
    html = render_page(
        stock_code="600519",
        provider_name="sample",
        provider=SampleDataProvider(),
        holdings_path="data/portfolio/holdings.csv",
    )

    stock_start = html.index('id="stock"')
    portfolio_start = html.index('id="portfolio"')
    stock_html = html[stock_start:portfolio_start]

    assert "五维分析" in stock_html
    assert "基本面" in stock_html
    assert "资金面" in stock_html
    assert "消息面" in stock_html
    assert "统计面" in stock_html
    assert "概念板块" in stock_html
    assert "专业八维诊断" in stock_html
    assert "技术趋势" in stock_html
    assert "量价结构" in stock_html
    assert "估值位置" in stock_html
    assert "资金行为" in stock_html
    assert "公告舆情" in stock_html
    assert "板块强弱" in stock_html
    assert "持仓成本" in stock_html
    assert "风控边界" in stock_html
    assert "证据充分度" in stock_html
    assert "综合判断" in stock_html


def test_portfolio_module_surfaces_overall_diagnosis() -> None:
    html = render_page(
        stock_code="600519",
        provider_name="sample",
        provider=SampleDataProvider(),
        holdings_path="data/portfolio/holdings.csv",
    )

    portfolio_start = html.index('id="portfolio"')
    watchlist_start = html.index('id="watchlist"')
    portfolio_html = html[portfolio_start:watchlist_start]

    assert "组合整体诊断" in portfolio_html
    assert "集中度" in portfolio_html
    assert "盈亏贡献" in portfolio_html
    assert "行业暴露" in portfolio_html
    assert "风险共振" in portfolio_html
    assert "处理顺序" in portfolio_html


def test_tdx_snapshot_defensive_market_does_not_show_attack_action() -> None:
    html = render_page(
        stock_code="002487",
        provider_name="tdx-snapshot",
        provider=TdxSnapshotProvider("data/imports/tdx_snapshots.json"),
        holdings_path="data/portfolio/holdings.csv",
    )

    assert "仓位动作</span><strong>防守观察</strong>" in html
    assert "主线状态</span><strong>分歧复核</strong>" in html
    assert "风险状态</span><strong>退潮风险</strong>" in html
    assert "仓位动作</span><strong>可以进攻</strong>" not in html


def test_sentiment_explains_limit_down_count_without_detail_rows() -> None:
    provider = TdxSnapshotProvider("data/imports/tdx_snapshots.json")
    html = render_page(
        stock_code="002487",
        provider_name="tdx-snapshot",
        provider=provider,
        holdings_path="data/portfolio/holdings.csv",
    )

    sentiment_start = html.index('id="sentiment"')
    screener_start = html.index('id="screener"')
    sentiment_html = html[sentiment_start:screener_start]

    expected_limit_down = provider.fetch_market().limit_down
    assert f"跌停家数</span><strong>{expected_limit_down}" in sentiment_html
    assert "当前快照未返回跌停明细" in sentiment_html
    assert "当前快照没有跌停个股明细" in sentiment_html
    assert "候选跌停样本" not in sentiment_html
    assert "弱势样本" not in sentiment_html


def test_limit_down_module_does_not_use_candidate_pool_as_market_weakness() -> None:
    html = render_page(
        stock_code="002487",
        provider_name="tdx-snapshot",
        provider=TdxSnapshotProvider("data/imports/tdx_snapshots.json"),
        holdings_path="data/portfolio/holdings.csv",
    )

    limit_down_start = html.index('id="sentiment"')
    screener_start = html.index('id="screener"')
    limit_down_html = html[limit_down_start:screener_start]

    assert "跌停家数" in limit_down_html
    assert "当前快照未返回跌停明细" in limit_down_html
    assert "当前快照没有跌停个股明细" in limit_down_html
    assert "候选跌停样本" not in limit_down_html
    assert "候选弱势样本" not in limit_down_html
    assert "弱势样本" not in limit_down_html
    assert "最弱下跌" not in limit_down_html


def test_page_surfaces_unified_risk_gate_components() -> None:
    html = render_page(
        stock_code="600519",
        provider_name="sample",
        provider=SampleDataProvider(),
        holdings_path="data/portfolio/holdings.csv",
    )

    assert "风险闸门" in html
    assert "大盘环境" in html
    assert "短线情绪" in html
    assert "数据可信度" in html
    assert "组合风险" in html


def test_tdx_snapshot_risk_gate_blocks_action_when_data_paused() -> None:
    html = render_page(
        stock_code="002487",
        provider_name="tdx-snapshot",
        provider=TdxSnapshotProvider("data/imports/tdx_snapshots.json"),
        holdings_path="data/portfolio/holdings.csv",
    )

    assert "暂停行动" in html
    assert "数据可信度" in html
    assert "暂停" in html
    assert "风险状态</span><strong>退潮风险</strong>" in html
    assert "风险闸门</span><strong>可以进攻</strong>" not in html


def test_data_quality_module_surfaces_source_route_without_fake_precision() -> None:
    html = render_page(
        stock_code="002487",
        provider_name="tdx-snapshot",
        provider=TdxSnapshotProvider("data/imports/tdx_snapshots.json"),
        holdings_path="data/portfolio/holdings.csv",
    )

    assert "数据源路由" in html
    assert "主源</span><strong>TDX MCP" in html
    assert "兜底</span><strong>Tushare" in html
    assert "补充</span><strong>AKShare" in html
    assert "跨市场</span><strong>港股 / 美股" in html
    assert "候选价格</span><strong>可用" in html


def test_page_removes_twenty_engineering_refactor_items() -> None:
    html = render_page(
        stock_code="600519",
        provider_name="sample",
        provider=SampleDataProvider(),
        holdings_path="data/portfolio/holdings.csv",
    )

    assert "20项改造清单" not in html
    assert "5位工程师" not in html
    assert "模块单一目标" not in html


def test_portfolio_module_surfaces_position_overview() -> None:
    html = render_page(
        stock_code="600519",
        provider_name="sample",
        provider=SampleDataProvider(),
        holdings_path="data/portfolio/holdings.csv",
    )

    portfolio_start = html.index('id="portfolio"')
    watchlist_start = html.index('id="watchlist"')
    portfolio_html = html[portfolio_start:watchlist_start]

    assert "整体仓位情况" in portfolio_html
    assert "记录内股票仓位" in portfolio_html
    assert "目标现金/低风险" in portfolio_html
    assert "第一大+前三大" in portfolio_html
    assert "现金未录入" in portfolio_html


def test_sentiment_renders_limit_down_details_from_tdx_snapshot(tmp_path) -> None:
    def bars(latest: float = 10.0) -> list[dict]:
        return [
            {
                "date": "2026-06-25",
                "open": latest,
                "high": latest * 1.05,
                "low": latest * 0.95,
                "close": latest,
                "volume": 1000,
            },
            {
                "date": "2026-06-26",
                "open": latest,
                "high": latest * 1.05,
                "low": latest * 0.95,
                "close": latest * 1.05,
                "volume": 1200,
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
    stocks = {code: {"code": code, "name": code, "bars": bars()} for code in holding_codes}
    stocks["600100"] = {"code": "600100", "name": "强势样本", "bars": bars()}
    snapshot = {
        "market": {
            "trade_date": "2026-06-26",
            "indices": [
                {
                    "code": "000001",
                    "name": "上证指数",
                    "close": 3000,
                    "pct_chg": -1.2,
                    "amount": 5000,
                }
            ],
            "advancing": 1200,
            "declining": 3800,
            "limit_up": 20,
            "limit_down": 2,
            "top_sectors": [["机器人", 2.1]],
            "limit_down_details": [
                {
                    "code": "600001",
                    "name": "风险一号",
                    "sector": "房地产",
                    "pct_chg": -10.01,
                    "latest_close": 4.56,
                    "reason": "退潮扩散",
                },
                {
                    "code": "300002",
                    "name": "风险二号",
                    "sector": "消费电子",
                    "pct_chg": -20.0,
                    "latest_close": 12.34,
                    "reason": "高位补跌",
                },
            ],
        },
        "sectors": [
            {
                "name": "机器人",
                "pct_chg": 2.1,
                "advancing_ratio": 0.6,
                "amount_change": 8.0,
                "limit_up_count": 2,
            }
        ],
        "stocks": stocks,
        "candidate_universe": {
            "items": [
                {
                    "code": "600100",
                    "name": "强势样本",
                    "sector": "机器人",
                    "bars": bars(),
                }
            ]
        },
    }
    path = tmp_path / "tdx.json"
    import json

    path.write_text(json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")

    html = render_page(
        stock_code="600100",
        provider_name="tdx-snapshot",
        provider=TdxSnapshotProvider(path),
        holdings_path="data/portfolio/holdings.csv",
    )
    sentiment_html = html[html.index('id="sentiment"') : html.index('id="screener"')]

    assert "跌停风险 / 跌停明细" in sentiment_html
    assert "涨停原因" in sentiment_html
    assert "跌停原因" in sentiment_html
    assert "风险一号" in sentiment_html
    assert "风险二号" in sentiment_html
    assert "事件线索：退潮扩散" in sentiment_html
    assert "房地产方向退潮或分歧扩散" in sentiment_html
    assert "消费电子方向退潮或分歧扩散" in sentiment_html
    assert "题材驱动：机器人" in sentiment_html
    assert "当前快照未返回跌停明细" not in sentiment_html


def test_sentiment_computes_limit_down_details_from_snapshot_bars(tmp_path) -> None:
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
                {
                    "code": "300002",
                    "name": "二十厘米跌停",
                    "sector": "机器人",
                    "bars": bars(10, 8),
                }
            ]
        },
    }
    path = tmp_path / "tdx.json"
    import json

    path.write_text(json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")

    html = render_page(
        stock_code="300002",
        provider_name="tdx-snapshot",
        provider=TdxSnapshotProvider(path),
        holdings_path="data/portfolio/holdings.csv",
    )
    sentiment_html = html[html.index('id="sentiment"') : html.index('id="screener"')]

    assert "二十厘米跌停" in sentiment_html
    assert "机器人方向退潮或分歧扩散" in sentiment_html
    assert "20cm高弹性跌停" in sentiment_html
    assert "当前快照未返回跌停明细" not in sentiment_html


def test_stock_module_combines_kline_screen_filter_and_conditional_trade_plan() -> None:
    html = render_page(
        stock_code="600519",
        provider_name="sample",
        provider=SampleDataProvider(),
        holdings_path="data/portfolio/holdings.csv",
    )

    trading_start = html.index('id="stock"')
    portfolio_start = html.index('id="portfolio"')
    trading_html = html[trading_start:portfolio_start]

    assert "股票筛选" in trading_html
    assert "候选前排" in trading_html
    assert 'class="panel stock-switch-panel"' in trading_html
    assert trading_html.count('class="stock-quick-lane"') == 2
    assert "stock-quick-lanes" in trading_html
    assert "K线交易屏" in trading_html
    assert "KLineChart" in trading_html
    assert "data-kline-screen" in trading_html
    assert "klinecharts@9.6.0" in trading_html
    assert "分时交易" in trading_html
    assert "分钟数据未接入" in trading_html
    assert "建议买点 / 卖点" in trading_html
    assert "买点" in trading_html
    assert "卖点/止损" in trading_html
    assert "未来5天交易趋势" in trading_html
    assert "情景推演" in trading_html
    assert "不承诺涨跌" in trading_html
    assert "个股交易屏" not in html
    assert "回测策略" not in html


def test_stock_module_surfaces_professional_scorecard_actions() -> None:
    html = render_page(
        stock_code="600519",
        provider_name="sample",
        provider=SampleDataProvider(),
        holdings_path="data/portfolio/holdings.csv",
    )

    stock_start = html.index('id="stock"')
    portfolio_start = html.index('id="portfolio"')
    stock_html = html[stock_start:portfolio_start]

    assert "专业评分卡" in stock_html
    assert "维度评分" in stock_html
    assert "证据" in stock_html
    assert "动作" in stock_html
    assert "估值基本面" in stock_html
    assert "消息事件" in stock_html
    assert "交易计划" in stock_html


def test_stock_module_surfaces_decision_summary_before_scorecard() -> None:
    html = render_page(
        stock_code="600519",
        provider_name="sample",
        provider=SampleDataProvider(),
        holdings_path="data/portfolio/holdings.csv",
    )

    stock_start = html.index('id="stock"')
    portfolio_start = html.index('id="portfolio"')
    stock_html = html[stock_start:portfolio_start]

    assert "决策摘要" in stock_html
    assert "最终判断" in stock_html
    assert "核心矛盾" in stock_html
    assert "今日动作" in stock_html
    assert "不能做什么" in stock_html
    assert "转强条件" in stock_html
    assert "离场条件" in stock_html
    assert "数据可信度" in stock_html
    assert stock_html.index("决策摘要") < stock_html.index("专业评分卡")


def test_stock_module_surfaces_holding_cost_perspective_when_position_exists(tmp_path) -> None:
    holdings = tmp_path / "holdings.csv"
    holdings.write_text(
        "code,name,shares,cost_price,sector,note\n600519,贵州茅台,10,1500.00,白酒,测试持仓\n",
        encoding="utf-8",
    )
    html = render_page(
        stock_code="600519",
        provider_name="sample",
        provider=SampleDataProvider(),
        holdings_path=str(holdings),
    )
    stock_start = html.index('id="stock"')
    portfolio_start = html.index('id="portfolio"')
    stock_html = html[stock_start:portfolio_start]

    assert "持仓成本视角" in stock_html
    assert "成本 1500.00" in stock_html
    assert "保护利润" in stock_html or "修复观察" in stock_html or "问题仓" in stock_html
