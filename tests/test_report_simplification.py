from __future__ import annotations

from pathlib import Path

from stock_ts.deep_report import render_daily_deep_markdown, render_deep_stock_markdown
from stock_ts.providers.sample import SampleDataProvider
from stock_ts.report import render_stock_markdown
from stock_ts.workflows import (
    build_daily_deep_report,
    build_daily_report,
    build_deep_stock_report,
    build_stock_report,
)


def test_stock_markdown_hides_method_explainer_but_keeps_decision_fields() -> None:
    stock = build_stock_report(SampleDataProvider(), "600519")
    markdown = render_stock_markdown(stock)

    assert "最新分析方法" not in markdown
    assert "八维评分" not in markdown
    assert "## 决策摘要" in markdown
    assert "## 专业评分卡" in markdown
    assert "消息事件" in markdown


def test_deep_stock_markdown_has_single_disclaimer_and_no_method_explainer() -> None:
    report = build_deep_stock_report(SampleDataProvider(), "600519")
    markdown = render_deep_stock_markdown(report)

    assert markdown.count("不构成投资建议") == 1
    assert "最新分析方法" not in markdown
    assert "TradingAgents 式角色链" not in markdown
    assert "## 多角度评分" in markdown
    assert "## 多轮对抗" in markdown


def test_daily_deep_markdown_removes_raw_report_duplication_and_duplicate_disclaimers() -> None:
    report = build_daily_deep_report(SampleDataProvider(), candidate_limit=3)
    markdown = render_daily_deep_markdown(report)

    assert markdown.count("不构成投资建议") == 1
    assert "## 原始日报摘要" not in markdown
    assert "最新分析方法" not in markdown
    assert "## 研究运行卡" not in markdown
    assert "Shadow Account" not in markdown
    assert "## 今日重点" in markdown
    assert "## 个股深度观察" in markdown
    assert "今日动作" in markdown
    assert "消息事件/新闻舆情" in markdown


def test_daily_markdown_uses_dual_git_method_chain_for_all_surfaces(
    tmp_path: Path,
) -> None:
    holdings = tmp_path / "holdings.csv"
    holdings.write_text(
        "code,name,shares,cost_price,sector,note\n"
        "600519,贵州茅台,100,1500,白酒,核心持仓\n",
        encoding="utf-8",
    )

    daily = build_daily_report(
        SampleDataProvider(),
        holdings_path=holdings,
        candidate_limit=3,
    )
    markdown = daily.markdown

    assert "## 持仓股票统一方法链" in markdown
    assert "贵州茅台（600519）" in markdown
    assert "daily_stock_analysis 信号归因" in markdown
    assert "TradingAgents 分析师团队" in markdown
    assert "多空审议" in markdown
    assert "组合经理最终意见" in markdown
    assert "## 候选股票统一方法链" in markdown
    assert "## 板块统一方法链" in markdown
    assert "板块方法链" in markdown
    assert "TradingAgents 板块审议" in markdown


def test_daily_deep_markdown_uses_dual_git_method_chain_for_sectors_and_portfolio(
    tmp_path: Path,
) -> None:
    holdings = tmp_path / "holdings.csv"
    holdings.write_text(
        "code,name,shares,cost_price,sector,note\n"
        "600519,贵州茅台,100,1500,白酒,核心持仓\n",
        encoding="utf-8",
    )

    report = build_daily_deep_report(
        SampleDataProvider(),
        holdings_path=holdings,
        candidate_limit=2,
    )
    markdown = render_daily_deep_markdown(report)

    assert "## 板块统一方法链" in markdown
    assert "板块方法链" in markdown
    assert "TradingAgents 板块审议" in markdown
    assert "## 持仓股票统一方法链" in markdown
    assert "贵州茅台（600519）" in markdown
    assert "daily_stock_analysis 信号归因" in markdown
    assert "组合经理最终意见" in markdown
