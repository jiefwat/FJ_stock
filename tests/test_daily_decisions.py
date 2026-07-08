from __future__ import annotations

import json
from pathlib import Path

from stock_ts.daily_decisions import (
    build_decision_artifact,
    read_decision_artifact,
    write_decision_artifact,
)


def test_build_decision_artifact_extracts_trade_actions_and_data_limits() -> None:
    markdown = (
        "# StockTS 每日深度复盘（2026-07-08）\n\n"
        "## 深度结论\n- 市场：市场偏弱，防守优先，状态 防守退潮，热度 17/100\n\n"
        "## 每日大盘情况\n- 市场偏弱，防守优先\n- 涨跌家数比 0.42\n\n"
        "## 持仓分析\n"
        "- 弱势或高风险持仓：甬矽电子、润建股份、大业股份\n"
        "- 大盘环境偏弱，持仓需要降低回撤暴露\n\n"
        "## 持仓明细\n"
        "- 甬矽电子（688362）：市值 54360.00，仓位 11.4%，"
        "盈亏 19019.60（53.82%），趋势 下降趋势，风险 高\n"
        "- 蓝色光标（300058）：市值 46200.00，仓位 9.7%，"
        "盈亏 -10477.95（-18.49%），趋势 上升趋势，风险 低\n"
        "- 大业股份（603278）：市值 48440.00，仓位 10.2%，"
        "盈亏 10295.20（26.99%），趋势 上升趋势，风险 中\n\n"
        "## 候选股票\n"
        "1. 济民健康（603222，未识别主题）：观察分 80/100，最新价 9.20，日涨跌 3.2%\n"
        "   - 入选理由：量能放大，短期均线向上\n"
        "   - 风险提示：追高风险\n"
        "   - 观察条件：回踩承接\n"
    )

    artifact = build_decision_artifact(
        markdown,
        pipeline_status=(
            "status=ok\n"
            "external_enrich=failed:timeout\n"
            "a_share_kline=partial:updated 300\n"
        ),
    )

    assert artifact["schema_version"] == 1
    assert artifact["trade_date"] == "2026-07-08"
    assert artifact["market"]["summary"] == "市场偏弱，防守优先"
    assert artifact["traffic_lights"]["red"][0]["name"] == "甬矽电子"
    assert artifact["traffic_lights"]["red"][0]["action"] == "不加仓；反弹优先锁利润/降风险"
    assert artifact["traffic_lights"]["yellow"][0]["name"] == "蓝色光标"
    assert artifact["traffic_lights"]["green"][0]["name"] == "大业股份"
    assert artifact["opportunities"][0]["name"] == "济民健康"
    assert artifact["opportunities"][0]["action"] == "回踩承接"
    assert "资金面判断不可信" in artifact["data_limits"]
    assert "消息催化判断不可信" in artifact["data_limits"]


def test_write_and_read_decision_artifact_roundtrip(tmp_path: Path) -> None:
    target = tmp_path / "latest_decisions.json"

    write_decision_artifact(
        "# StockTS 每日深度复盘（2026-07-08）\n\n## 深度结论\n- 市场防守\n",
        target,
        pipeline_status="status=ok\nreport=ok\n",
    )

    loaded = read_decision_artifact(target)
    raw = json.loads(target.read_text(encoding="utf-8"))
    assert loaded == raw
    assert loaded["trade_date"] == "2026-07-08"
