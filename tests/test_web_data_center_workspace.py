from __future__ import annotations

from dataclasses import dataclass

from stock_ts.research.data_center_dossier import build_data_center_dossier
from stock_ts.webapp.data_center_workspace import render_data_center_workspace


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


def _blocked_dossier():
    return build_data_center_dossier(
        status="影响分析",
        updated_at="2026-07-11 11:32:33 北京时间",
        rows=[
            Row(
                "全链路校验",
                channel="reports/daily/data_chain_status.json",
                status="影响分析",
                missing="持仓 688362 缺少K线",
                impact="全链路存在阻断节点",
                level="blocked",
            ),
            Row(
                "K线行情",
                channel="TDX MCP",
                status="已滞后",
                missing="最近交易日K线",
                impact="影响技术面、候选排序和盘面执行",
                level="blocked",
            ),
            Row(
                "新闻舆情",
                channel="Longbridge MCP",
                status="缺字段",
                missing="市场消息",
                impact="影响消息面和事件催化判断",
                level="warn",
            ),
        ],
    )


def test_data_center_workspace_is_gate_first_and_recovery_ordered() -> None:
    html = render_data_center_workspace(
        _blocked_dossier(),
        refresh_html="<form>refresh</form>",
    )

    assert html.count('data-primary-data-verdict="true"') == 1
    assert html.index("数据就绪闸门") < html.index("恢复运行轨道")
    assert html.index("恢复运行轨道") < html.index("模块影响面")
    assert "停止强结论，按恢复顺序补齐数据" in html
    assert "01" in html
    assert html.index("K线行情") < html.index("全链路校验")
    assert "每日大盘" in html
    assert "我的持仓" in html
    assert "个股分析" in html
    assert "热点机会" in html
    assert '<details class="data-source-ledger">' in html
    assert "查看 3 个数据域的完整来源账本" in html
    assert "<form>refresh</form>" in html
    assert "RESTORE ORDER" not in html
    assert "DOWNSTREAM IMPACT" not in html
    assert "先恢复可信数据，再恢复研究结论。" not in html


def test_data_center_workspace_preserves_complete_ledger_default_closed() -> None:
    html = render_data_center_workspace(_blocked_dossier(), refresh_html="")

    assert html.count('class="data-ledger-card') == 3
    assert "TDX MCP" in html
    assert "Longbridge MCP" in html
    assert "最近交易日K线" in html
    assert "影响技术面、候选排序和盘面执行" in html
    details_start = html.index('<details class="data-source-ledger">')
    details_tag_end = html.index(">", details_start)
    assert " open" not in html[details_start:details_tag_end]


def test_data_center_workspace_escapes_source_and_missing_text() -> None:
    dossier = build_data_center_dossier(
        status="影响分析",
        updated_at="待确认",
        rows=[
            Row(
                "K线行情",
                channel="<script>alert(1)</script>",
                status="缺字段",
                missing="<b>缺口</b>",
                impact="影响技术面",
                level="blocked",
            )
        ],
    )

    html = render_data_center_workspace(dossier, refresh_html="")

    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<b>缺口</b>" not in html
    assert "&lt;b&gt;缺口&lt;/b&gt;" in html


def test_ready_data_center_has_directed_empty_recovery_state() -> None:
    dossier = build_data_center_dossier(
        status="正常",
        updated_at="2026-07-11 11:32:33 北京时间",
        rows=[Row("K线行情"), Row("资金面")],
    )

    html = render_data_center_workspace(dossier, refresh_html="")

    assert "暂无数据域需要恢复" in html
    assert "维持日常校验，关注下次交易日刷新" in html
