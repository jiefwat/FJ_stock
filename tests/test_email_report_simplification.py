from __future__ import annotations

from pathlib import Path

import scripts.send_morning_report as morning


def test_morning_report_hides_ops_run_card_and_keeps_actionable_sections(tmp_path: Path) -> None:
    daily_dir = tmp_path / "daily"
    html_dir = tmp_path / "html"
    announcement_dir = tmp_path / "announcements"
    daily_dir.mkdir()
    html_dir.mkdir()
    announcement_dir.mkdir()
    (daily_dir / "latest.md").write_text(
        "# StockTS 每日深度复盘（2026-07-08）\n\n"
        "## 深度结论\n- 市场：震荡，状态 震荡轮动，热度 58/100\n"
        "## 每日大盘情况\n- 上证指数震荡\n"
        "## 板块情况\n- 机器人\n"
        "## 持仓分析\n- 持仓先控风险\n"
        "## 个股深度观察\n- 测试股票（688001）：60/100，防守观察\n"
        "  - 今日动作：不追高，等回踩承接\n"
        "  - 消息事件/新闻舆情：风险：股东拟减持\n"
        "## 候选股票池摘要\n1. 机会股票（688002，机器人）：观察分 70/100，最新价 10，日涨跌 2%\n"
        "   - 观察条件：放量突破\n",
        encoding="utf-8",
    )
    (daily_dir / "pipeline.status").write_text("status=ok\nreport=ok\n", encoding="utf-8")
    (announcement_dir / "latest.md").write_text("# 公告\n", encoding="utf-8")

    content = morning.build_morning_report(
        daily_dir=daily_dir,
        html_dir=html_dir,
        announcement_dir=announcement_dir,
    )

    assert "## 研究运行卡" not in content
    assert "Shadow Account" not in content
    assert "## 使用边界" not in content
    assert "## 今日仓位建议" in content
    assert "今天持仓怎么做" in content
    assert "测试股票" in content
    assert "动作：不追高" in content
    assert "股东拟减持" in content
    assert "数据提示" in content


def test_morning_report_marks_trade_date_and_stale_data(tmp_path: Path) -> None:
    daily_dir = tmp_path / "daily"
    html_dir = tmp_path / "html"
    announcement_dir = tmp_path / "announcements"
    daily_dir.mkdir()
    html_dir.mkdir()
    announcement_dir.mkdir()
    (daily_dir / "latest.md").write_text(
        "# StockTS 每日深度复盘（2026-06-26）\n\n"
        "## 深度结论\n- 市场偏弱，先控风险\n"
        "## 每日大盘情况\n- 跌停扩散\n",
        encoding="utf-8",
    )
    (daily_dir / "pipeline.status").write_text(
        "status=ok\ngenerated_at=2026-06-26T18:00:00\nreport=ok\n",
        encoding="utf-8",
    )
    (announcement_dir / "latest.md").write_text("# 公告\n", encoding="utf-8")

    content = morning.build_morning_report(
        daily_dir=daily_dir,
        html_dir=html_dir,
        announcement_dir=announcement_dir,
    )

    assert "基于交易日：2026-06-26" in content
    assert "数据可能滞后" in content
    assert "2026-06-26" in content.splitlines()[0]


def test_morning_report_deduplicates_repeated_opportunities(tmp_path: Path) -> None:
    daily_dir = tmp_path / "daily"
    html_dir = tmp_path / "html"
    announcement_dir = tmp_path / "announcements"
    daily_dir.mkdir()
    html_dir.mkdir()
    announcement_dir.mkdir()
    (daily_dir / "latest.md").write_text(
        "# StockTS 每日深度复盘（2026-07-08）\n\n"
        "## 深度结论\n- 市场震荡，机会只看前排\n\n"
        "## 候选股票池摘要\n"
        "## 候选股票\n"
        "1. 迈赫股份（301199，外骨骼机器人）：观察分 90/100\n"
        "   - 入选理由：板块共振\n"
        "   - 风险提示：高位分歧\n"
        "   - 观察条件：回踩承接\n"
        "2. 迈赫股份（301199，机器人）：观察分 88/100\n"
        "   - 入选理由：重复样本\n"
        "   - 风险提示：重复风险\n"
        "   - 观察条件：重复条件\n"
        "3. 泰胜风能（300129，风电）：观察分 87/100\n"
        "   - 入选理由：趋势强\n"
        "   - 风险提示：追高风险\n"
        "   - 观察条件：不破均线\n",
        encoding="utf-8",
    )
    (daily_dir / "pipeline.status").write_text("status=ok\nreport=ok\n", encoding="utf-8")
    (announcement_dir / "latest.md").write_text("# 公告\n", encoding="utf-8")

    content = morning.build_morning_report(
        daily_dir=daily_dir,
        html_dir=html_dir,
        announcement_dir=announcement_dir,
    )
    opportunity_lines = _lines_between(content, "## 今日机会 10 条", "## 数据状态")

    assert sum("迈赫股份" in line for line in opportunity_lines) == 1
    assert sum("泰胜风能" in line for line in opportunity_lines) == 1
    assert "重复样本" not in "\n".join(opportunity_lines)


def _lines_between(content: str, start: str, end: str) -> list[str]:
    start_index = content.index(start)
    end_index = content.index(end, start_index)
    return content[start_index:end_index].splitlines()
