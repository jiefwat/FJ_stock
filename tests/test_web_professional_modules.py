from stock_ts.web import _format_limit_count, render_page


def test_web_renders_professional_research_framework_for_all_modules() -> None:
    html = render_page(
        stock_code="大业股份",
        provider_name="sample",
        holdings_path="data/portfolio/holdings.csv",
    )

    assert "A股大盘" in html
    assert "今日大盘" in html
    assert "主线板块" in html
    assert "主题强弱榜" in html
    assert "强势个股" in html
    assert "涨停板" in html
    assert "强势样本" in html
    assert "跌停家数" in html
    assert "当前快照未返回跌停明细" in html
    assert "智能选股" in html
    assert "筛选" in html
    assert "按评分" in html
    assert "我的持仓" in html
    assert "持仓列表" in html
    assert "个股分析" in html
    assert "个股决策卡" in html
    assert "渠道配置" in html
    assert "发送通道" in html
    assert "主要数据源" not in html


def test_web_keeps_professional_modules_connected_to_existing_data() -> None:
    html = render_page(
        stock_code="600519",
        provider_name="sample",
        holdings_path="data/portfolio/holdings.csv",
    )

    assert "市场" in html
    assert "持仓健康度" in html
    assert "主线板块" in html
    assert "贵州茅台" in html
    assert "不构成投资建议" not in html


def test_web_candidate_workspace_uses_watchlist_style_filters_and_actions() -> None:
    html = render_page(
        stock_code="大业股份",
        provider_name="sample",
        holdings_path="data/portfolio/holdings.csv",
    )

    assert "筛选" in html
    assert "全部候选" in html
    assert "高优先级" in html
    assert "中优先级" in html
    assert "观察级" in html
    assert "按评分" in html
    assert "入选理由" in html
    assert "风险提醒" in html
    assert "验证条件" in html


def test_limit_modules_do_not_present_tencent_zero_as_real_count() -> None:
    assert _format_limit_count(0, provider_class="TencentProvider") == "未返回"
    assert _format_limit_count(12, provider_class="TencentProvider") == "12"
    assert _format_limit_count(0, provider_class="AkshareProvider") == "0"
