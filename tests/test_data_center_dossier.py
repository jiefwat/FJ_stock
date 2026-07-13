from __future__ import annotations

from dataclasses import dataclass

from stock_ts.research.data_center_dossier import build_data_center_dossier


@dataclass(frozen=True)
class Row:
    category: str
    channel: str = "source"
    status: str = "可用"
    latest_at: str = "2026-07-11"
    coverage: str = "全部"
    missing: str = "无"
    impact: str = "不影响分析"
    level: str = "ok"


def test_blocked_dossier_orders_recovery_and_preserves_ledger() -> None:
    rows = [
        Row(
            "新闻舆情",
            status="已滞后",
            missing="市场消息",
            impact="影响消息面和事件催化判断",
            level="warn",
        ),
        Row(
            "K线行情",
            status="已滞后",
            missing="最近交易日K线",
            impact="影响技术面、候选排序和盘面执行",
            level="blocked",
        ),
        Row("基本面"),
        Row(
            "全链路校验",
            status="影响分析",
            missing="持仓 688362 缺少K线",
            impact="全链路存在阻断节点",
            level="blocked",
        ),
    ]

    dossier = build_data_center_dossier(
        status="影响分析",
        updated_at="2026-07-11 11:32:33 北京时间",
        rows=rows,
    )

    assert dossier.gate.state == "影响分析"
    assert dossier.gate.action == "停止强结论，按恢复顺序补齐数据"
    assert dossier.gate.blocked_count == 2
    assert dossier.gate.warning_count == 1
    assert dossier.gate.ready_count == 1
    assert [item.category for item in dossier.recovery_steps] == [
        "全链路校验",
        "K线行情",
        "新闻舆情",
    ]
    assert dossier.gate.next_step == "先处理全链路校验：持仓 688362 缺少K线"
    assert len(dossier.ledger) == len(rows)
    assert [item.category for item in dossier.ledger] == [row.category for row in rows]


def test_warning_dossier_only_degrades_modules_that_depend_on_warning() -> None:
    dossier = build_data_center_dossier(
        status="需复核",
        updated_at="2026-07-11 11:32:33 北京时间",
        rows=[
            Row(
                "资金面",
                status="缺字段",
                missing="资金流明细",
                impact="影响资金面证据和承接判断",
                level="warn",
            ),
            Row("K线行情"),
            Row("大盘行情"),
            Row("新闻舆情"),
        ],
    )

    impacts = {item.key: item for item in dossier.impacts}
    assert dossier.gate.action == "降低结论强度，先复核异常数据域"
    assert impacts["market"].status == "ready"
    assert impacts["portfolio"].status == "warn"
    assert impacts["stock"].affected_domains == ("资金面",)
    assert impacts["opportunity"].status == "warn"


def test_ready_dossier_has_no_recovery_steps() -> None:
    dossier = build_data_center_dossier(
        status="正常",
        updated_at="2026-07-11 11:32:33 北京时间",
        rows=[Row("K线行情"), Row("资金面"), Row("新闻舆情")],
    )

    assert dossier.gate.action == "数据可用，允许进入研究流程"
    assert dossier.gate.next_step == "维持日常校验，关注下次交易日刷新"
    assert dossier.recovery_steps == ()


def test_empty_dossier_is_blocked_with_directed_recovery() -> None:
    dossier = build_data_center_dossier(
        status="正常",
        updated_at="待确认",
        rows=[],
    )

    assert dossier.gate.state == "影响分析"
    assert dossier.gate.total_count == 0
    assert dossier.gate.blocked_count == 1
    assert dossier.recovery_steps[0].category == "数据域清单"
    assert dossier.recovery_steps[0].issue == "数据域清单为空"
    assert dossier.ledger == ()


def test_gate_next_step_compacts_long_issue_without_truncating_ledger() -> None:
    long_issue = "持仓缺少基本面、资金面、个股新闻、公告；" * 5
    dossier = build_data_center_dossier(
        status="影响分析",
        updated_at="待确认",
        rows=[
            Row(
                "全链路校验",
                status="影响分析",
                missing=long_issue,
                impact="全链路存在阻断节点",
                level="blocked",
            )
        ],
    )

    assert dossier.gate.next_step.endswith("…")
    assert len(dossier.gate.next_step) <= 64
    assert dossier.recovery_steps[0].issue == long_issue
    assert dossier.ledger[0].missing == long_issue
