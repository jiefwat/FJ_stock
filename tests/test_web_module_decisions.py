import json

from stock_ts.models import SectorRawData
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
    assert "每日大盘 · 仓位闸门" in html
    assert "持仓风险处置" in html
    assert "个股三面复核" in html
    assert "热点机会 · 主题雷达" in html
    assert "候选观察池" in html


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


def test_market_module_uses_real_breadth_counts_instead_of_unreturned() -> None:
    market_html = _workspace(_sample_html(), "market")

    assert "上涨/下跌/平盘" in market_html
    assert "未返回" not in market_html
    assert "机会与风险" in market_html
    assert "看热点机会" in market_html


def test_daily_market_module_matches_market_gate_design_doc() -> None:
    market_html = _workspace(_sample_html(), "market")

    for text in [
        "市场气压计",
        "市场总闸门",
        "指数脊柱",
        "宽度温度计",
        "板块主线热力地图",
        "风险红灯",
        "数据源",
        "交易日",
        "验证条件",
        "失效条件",
    ]:
        assert text in market_html


def test_daily_market_module_surfaces_conclusion_card_fields() -> None:
    market_html = _workspace(_sample_html(), "market")

    for text in [
        "市场结论卡",
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
        "策略漏斗",
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
        "候选卡列表",
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
        "最终判决卡",
        "六维证据墙",
        "技术面",
        "基本面",
        "资金面",
        "消息/公告",
        "概念板块",
        "成本位置",
        "多空反证",
        "禁止动作",
    ]:
        assert text in stock_html


def test_stock_module_surfaces_single_stock_verdict_fields() -> None:
    stock_html = _workspace(_sample_html(stock_code="603278"), "stock")

    for text in [
        "单股判决卡",
        "最终动作",
        "最强证据",
        "最大反证",
        "组合影响",
        "仓位上限",
        "当前持仓状态",
    ]:
        assert text in stock_html


def test_portfolio_module_surfaces_overall_diagnosis_and_position_overview() -> None:
    portfolio_html = _workspace(_sample_html(), "portfolio")

    for text in [
        "我的持仓",
        "持仓风险处置",
        "持仓处理队列",
        "整体仓位情况",
        "组合整体诊断",
        "处理优先级",
        "目标现金/低风险",
    ]:
        assert text in portfolio_html


def test_portfolio_module_reads_like_disposal_console_before_table() -> None:
    portfolio_html = _workspace(_sample_html(), "portfolio")

    for text in [
        "组合处置台",
        "今日先处理",
        "最大风险",
        "行业暴露地图",
        "账本状态",
        "下一步复核",
    ]:
        assert text in portfolio_html

    assert portfolio_html.index("今日先处理") < portfolio_html.index("持仓风险处置")


def test_portfolio_module_uses_four_lane_disposal_queue() -> None:
    portfolio_html = _workspace(_sample_html(), "portfolio")

    for text in [
        "处置队列四车道",
        "必须处理",
        "观察",
        "可继续",
        "待补数据",
        "风险预算条",
        "成本位置",
        "持仓账本来源",
        "公开只读",
    ]:
        assert text in portfolio_html


def test_portfolio_module_surfaces_health_light_and_execution_boundaries() -> None:
    portfolio_html = _workspace(_sample_html(), "portfolio")

    for text in [
        "组合健康灯",
        "组合处置摘要",
        "组合状态",
        "现金比例",
        "执行边界",
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
