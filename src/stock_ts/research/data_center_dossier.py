from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from stock_ts.research.data_center_dossier_models import (
    DataCenterDossier,
    DataImpactLane,
    DataLedgerEntry,
    DataReadinessGate,
    DataRecoveryStep,
)


class DataCenterRowLike(Protocol):
    category: str
    channel: str
    status: str
    latest_at: str
    coverage: str
    missing: str
    impact: str
    level: str


_RECOVERY_RANK = {
    "全链路校验": 0,
    "大盘行情": 1,
    "K线行情": 1,
    "技术面": 2,
    "候选池": 2,
    "资金面": 2,
    "新闻舆情": 3,
    "公告": 4,
    "基本面": 4,
}

_MODULE_DOMAINS = (
    ("market", "每日大盘", ("大盘行情", "K线行情", "新闻舆情", "全链路校验")),
    ("portfolio", "我的持仓", ("大盘行情", "K线行情", "资金面", "基本面", "全链路校验")),
    (
        "stock",
        "个股分析",
        ("K线行情", "技术面", "资金面", "新闻舆情", "公告", "基本面", "全链路校验"),
    ),
    (
        "opportunity",
        "热点机会",
        ("大盘行情", "K线行情", "候选池", "资金面", "新闻舆情", "全链路校验"),
    ),
)


def build_data_center_dossier(
    *,
    status: str,
    updated_at: str,
    rows: Sequence[DataCenterRowLike],
) -> DataCenterDossier:
    ledger = tuple(_to_ledger_entry(row) for row in rows)
    if not ledger:
        return _empty_dossier(updated_at)

    blocked_count = sum(item.level == "blocked" for item in ledger)
    warning_count = sum(item.level == "warn" for item in ledger)
    ready_count = len(ledger) - blocked_count - warning_count
    recovery_steps = _build_recovery_steps(ledger)
    state = _gate_state(status, blocked_count, warning_count)
    gate = DataReadinessGate(
        state=state,
        action=_gate_action(state),
        thesis=_gate_thesis(blocked_count, warning_count, ready_count),
        blocked_count=blocked_count,
        warning_count=warning_count,
        ready_count=ready_count,
        total_count=len(ledger),
        next_step=_next_step(recovery_steps),
    )
    return DataCenterDossier(
        gate=gate,
        recovery_steps=recovery_steps,
        impacts=_build_impacts(ledger),
        ledger=ledger,
        updated_at=updated_at,
    )


def _to_ledger_entry(row: DataCenterRowLike) -> DataLedgerEntry:
    return DataLedgerEntry(
        category=row.category,
        channel=row.channel,
        status=row.status,
        latest_at=row.latest_at,
        coverage=row.coverage,
        missing=row.missing,
        impact=row.impact,
        level=row.level,
    )


def _build_recovery_steps(
    ledger: tuple[DataLedgerEntry, ...],
) -> tuple[DataRecoveryStep, ...]:
    problem_rows = [
        (index, item)
        for index, item in enumerate(ledger)
        if item.level in {"blocked", "warn"}
    ]
    problem_rows.sort(
        key=lambda pair: (
            _RECOVERY_RANK.get(pair[1].category, 99),
            0 if pair[1].level == "blocked" else 1,
            pair[0],
        )
    )
    return tuple(
        DataRecoveryStep(
            priority=priority,
            category=item.category,
            status=item.status,
            severity=item.level,
            issue=_issue(item),
            consequence=item.impact,
            verification=item.latest_at,
        )
        for priority, (_, item) in enumerate(problem_rows, start=1)
    )


def _issue(item: DataLedgerEntry) -> str:
    if item.missing and item.missing != "无":
        return item.missing
    return item.status


def _gate_state(status: str, blocked_count: int, warning_count: int) -> str:
    if blocked_count:
        return "影响分析"
    if warning_count:
        return "需复核"
    return "正常" if status not in {"影响分析", "需复核"} else status


def _gate_action(state: str) -> str:
    if state == "影响分析":
        return "停止强结论，按恢复顺序补齐数据"
    if state == "需复核":
        return "降低结论强度，先复核异常数据域"
    return "数据可用，允许进入研究流程"


def _gate_thesis(blocked_count: int, warning_count: int, ready_count: int) -> str:
    if blocked_count:
        return f"{blocked_count} 个数据域阻断研究，{warning_count} 个数据域仍需复核。"
    if warning_count:
        return f"没有阻断域，但 {warning_count} 个数据域需要人工复核。"
    return f"{ready_count} 个数据域通过校验，当前没有影响分析的缺口。"


def _next_step(recovery_steps: tuple[DataRecoveryStep, ...]) -> str:
    if not recovery_steps:
        return "维持日常校验，关注下次交易日刷新"
    first = recovery_steps[0]
    return f"先处理{first.category}：{_compact_text(first.issue, limit=46)}"


def _compact_text(value: str, *, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip("；、，。 ") + "…"


def _build_impacts(
    ledger: tuple[DataLedgerEntry, ...],
) -> tuple[DataImpactLane, ...]:
    by_category = {item.category: item for item in ledger}
    lanes = []
    for key, label, required_domains in _MODULE_DOMAINS:
        problems = tuple(
            domain
            for domain in required_domains
            if domain in by_category and by_category[domain].level in {"blocked", "warn"}
        )
        levels = {by_category[domain].level for domain in problems}
        lane_status = "blocked" if "blocked" in levels else "warn" if levels else "ready"
        lanes.append(
            DataImpactLane(
                key=key,
                label=label,
                status=lane_status,
                affected_domains=problems,
                guidance=_impact_guidance(lane_status, problems),
            )
        )
    return tuple(lanes)


def _impact_guidance(status: str, affected_domains: tuple[str, ...]) -> str:
    if status == "blocked":
        return f"暂停强结论；先恢复{'、'.join(affected_domains)}"
    if status == "warn":
        return f"允许降级研究；复核{'、'.join(affected_domains)}"
    return "证据链可用"


def _empty_dossier(updated_at: str) -> DataCenterDossier:
    recovery = DataRecoveryStep(
        priority=1,
        category="数据域清单",
        status="未生成",
        severity="blocked",
        issue="数据域清单为空",
        consequence="无法判断任何研究模块的数据就绪状态",
        verification="重新生成数据质量清单后复核",
    )
    impacts = tuple(
        DataImpactLane(
            key=key,
            label=label,
            status="blocked",
            affected_domains=("数据域清单",),
            guidance="暂停强结论；先生成数据质量清单",
        )
        for key, label, _ in _MODULE_DOMAINS
    )
    return DataCenterDossier(
        gate=DataReadinessGate(
            state="影响分析",
            action="停止强结论，按恢复顺序补齐数据",
            thesis="数据域清单为空，当前无法证明任何研究结论可用。",
            blocked_count=1,
            warning_count=0,
            ready_count=0,
            total_count=0,
            next_step="先处理数据域清单：数据域清单为空",
        ),
        recovery_steps=(recovery,),
        impacts=impacts,
        ledger=(),
        updated_at=updated_at,
    )
