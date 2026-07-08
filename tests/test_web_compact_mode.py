from stock_ts.providers.sample import SampleDataProvider
from stock_ts.web import render_page


def test_web_modules_keep_only_core_content_without_narration() -> None:
    html = render_page(
        stock_code="600519",
        provider_name="sample",
        provider=SampleDataProvider(),
        holdings_path="data/portfolio/holdings.csv",
    )

    removed_phrases = [
        "今天先做什么",
        "核心入口",
        "市场执行框架",
        "涨停操作框架",
        "风险回避框架",
        "板块策略台",
        "板块观察名单",
        "组合处理队列",
        "候选处理清单",
        "候选评分梯度",
        "研究筛选框架",
        "推荐操作顺序",
        "主要数据源",
        "请求数据源",
        "实际 Provider",
        "当前会话的输入选择",
        "真实执行时使用的数据适配器",
        "A-Share Desk",
        "候选分层",
        "观察条件",
        "外发前必看",
        "发送前流程",
        "多轮对抗",
        "首页只保留的摘要",
        "主线证据",
        "评分角度",
        "怎么用",
        "真实发送已关闭",
    ]
    for phrase in removed_phrases:
        assert phrase not in html

    required_core = [
        "今日大盘",
        "主线板块",
        "涨跌停情绪",
        "智能选股",
        "我的持仓",
        "个股分析",
        "每日复盘",
        "消息自动化",
        "TDX MCP",
    ]
    for phrase in required_core:
        assert phrase in html


def test_compact_stock_module_has_single_core_surface() -> None:
    html = render_page(
        stock_code="600519",
        provider_name="sample",
        provider=SampleDataProvider(),
        holdings_path="data/portfolio/holdings.csv",
    )

    assert 'class="stock-tabs"' not in html
    assert "data-stock-tab-trigger" not in html
    assert "当前动作" in html
    assert "买点" in html
    assert "止损" in html


def test_error_page_uses_current_workspace_shell() -> None:
    from stock_ts.web import render_error_page

    html = render_error_page("provider failed", provider_name="tdx-snapshot")

    assert 'href="#settings"' in html
    assert 'data-workspace="settings"' in html
    assert "data-view=" not in html
    assert "module-overview" not in html
    assert 'class="app-toolbar"' not in html


def test_web_module_file_has_no_retired_renderers() -> None:
    from pathlib import Path

    source = Path("src/stock_ts/web.py").read_text(encoding="utf-8")
    retired_names = [
        "_render_app_toolbar",
        "_app_script",
        "_appify_modules",
        "_render_topbar",
        "_render_desk_strip",
        "_render_command_center",
        "_render_overview",
        "_render_research_framework",
        "_render_decision_dashboard",
        "_render_market_home",
        "_render_global_summary_strip",
        "_render_limit_up_module",
        "_render_limit_down_module",
        "_render_market_module",
        "_render_sector_module",
        "_render_portfolio_module",
        "_render_stock_module",
        "_render_data_quality_module",
        "_render_report_module",
        "_render_status_module",
        "_render_research_workbench_model",
        "_render_engineering_refactor_items",
        "_render_assist_module",
    ]
    for name in retired_names:
        assert f"def {name}" not in source


def test_web_hides_framework_and_method_packaging_words() -> None:
    html = render_page(
        stock_code="600519",
        provider_name="sample",
        provider=SampleDataProvider(),
        holdings_path="data/portfolio/holdings.csv",
    )

    noisy_words = [
        "研究指挥舱",
        "投研框架",
        "决策仪表盘",
        "专业投研框架",
        "策略透镜",
        "研究团队",
        "数据块完整性",
        "方法</strong>",
        "参考多角色投研框架",
    ]
    for word in noisy_words:
        assert word not in html

    assert "未来机会" in html
    assert "触发" in html
    assert "数据状态" in html
