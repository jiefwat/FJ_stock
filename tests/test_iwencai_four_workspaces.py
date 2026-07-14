from __future__ import annotations

import pytest

from stock_ts.iwencai import (
    build_module_research_query,
    build_module_research_response,
    route_module_research_skill,
)


@pytest.mark.parametrize(
    ("module", "question", "skill_id"),
    [
        ("market", "三大指数当前结构", "hithink-zhishu-query"),
        ("market", "近期宏观变量", "hithink-macro-query"),
        ("market", "筛选当前主线板块", "hithink-sector-selector"),
        ("market", "最近有哪些风险新闻", "news-search"),
        ("opportunity", "筛选盈利改善的A股", "hithink-astock-selector"),
        ("opportunity", "机器人板块持续性", "hithink-sector-selector"),
        ("opportunity", "候选近期事件催化", "hithink-event-query"),
        ("portfolio", "这只持仓是否有业绩风险", "hithink-event-query"),
        ("portfolio", "最近公告是否有风险", "announcement-search"),
        ("portfolio", "机构是否下修预期", "hithink-insresearch-query"),
        ("portfolio", "主力资金是否异动", "hithink-market-query"),
        ("stock", "净利润质量", "hithink-finance-query"),
    ],
)
def test_route_module_research_skill(module: str, question: str, skill_id: str) -> None:
    assert route_module_research_skill(module, question).skill_id == skill_id


def test_route_module_research_skill_rejects_unknown_module() -> None:
    with pytest.raises(ValueError, match="不支持"):
        route_module_research_skill("settings", "系统配置")


def test_module_queries_use_only_allowlisted_context() -> None:
    assert (
        build_module_research_query(
            "market",
            "三大指数当前结构",
            code="600519",
            name="贵州茅台",
            sector="白酒",
        )
        == "三大指数当前结构"
    )
    portfolio = build_module_research_query(
        "portfolio",
        "公告风险",
        code="600519",
        name="贵州茅台",
        sector="白酒",
    )
    opportunity = build_module_research_query(
        "opportunity",
        "板块持续性",
        code="300750",
        name="宁德时代",
        sector="锂电池",
    )

    assert portfolio == "贵州茅台 600519 公告风险"
    assert opportunity == "锂电池 宁德时代 300750 板块持续性"
    for private_value in ("100股", "成本1500", "仓位20%"):
        assert private_value not in portfolio
        assert private_value not in opportunity


def test_module_response_keeps_context_and_audit_boundary() -> None:
    skill = route_module_research_skill("market", "三大指数当前结构")

    result = build_module_research_response(
        {
            "datas": [{"指数简称": "上证指数", "涨跌幅": "0.8%"}],
            "code_count": 1,
            "trace_id": "a" * 64,
        },
        module="market",
        skill=skill,
        question="三大指数当前结构",
        query="三大指数当前结构",
        context_label="市场全局",
        local_as_of="2026-07-14",
        queried_at="2026-07-14T16:00:00+08:00",
    )

    assert result["module"] == "market"
    assert result["context_label"] == "市场全局"
    assert result["facts"] == [{"指数简称": "上证指数", "涨跌幅": "0.8%"}]
    assert result["source"]["trace"] == "aaaaaaaa"
    assert "不自动" in result["relationship"]
