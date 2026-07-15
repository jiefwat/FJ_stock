from __future__ import annotations

from datetime import datetime
from typing import Any

from .analysis import analyze_stock
from .providers.base import StockDataProvider
from .research_engine import (
    ResearchContext,
    ResearchFact,
    ResearchFinding,
    ResearchModuleItem,
    ResearchWorkspaceResult,
)

FALLBACK_REASON = "实时研究暂不可用，已使用本地证据。"


def build_local_research(
    module: str,
    context: ResearchContext,
    *,
    provider: StockDataProvider,
    holdings_path: str | None = None,
) -> ResearchWorkspaceResult:
    del holdings_path
    if module != "stock":
        raise ValueError(f"unsupported local research module: {module}")
    return _build_stock_research(context, provider)


def _build_stock_research(
    context: ResearchContext,
    provider: StockDataProvider,
) -> ResearchWorkspaceResult:
    raw = provider.fetch_stock(context.code)
    report = analyze_stock(raw)
    industry = str(raw.fundamental_metrics.get("industry") or "").strip()
    items = (
        _stock_item("财务质量", _fundamental_summary(raw.fundamental_metrics), bool(raw.fundamental_metrics)),
        _stock_item("经营结构", "经营结构需要实时研究恢复后补充。", False),
        _stock_item("机构预期", "机构预期需要实时研究恢复后补充。", False),
        _stock_item("事件风险", _event_summary(raw), bool(raw.news_items or raw.announcements)),
        _stock_item("行情资金", _market_summary(report), True),
        _stock_item(
            "行业位置",
            f"当前行业归属：{industry}。行业相对位置待实时研究恢复后复核。"
            if industry
            else "行业归属与相对位置需要实时研究恢复后补充。",
            bool(industry),
        ),
        _stock_item("公告事项", _announcement_summary(raw.announcements), bool(raw.announcements)),
        _stock_item("研报观点", "研报观点需要实时研究恢复后补充。", False),
    )
    available_items = tuple(item for item in items if item.status == "ready")
    missing = tuple(item.label for item in items if item.status != "ready")
    findings = (
        ResearchFinding(
            title="价格与资金",
            summary=_market_summary(report),
            target=report.name,
            facts=(
                ResearchFact(label="最新收盘", value=f"{report.latest_close:.2f}"),
                ResearchFact(label="短期趋势", value=report.trend),
            ),
        ),
        ResearchFinding(
            title="主要限制",
            summary=_primary_constraint(raw, report),
            target=report.name,
        ),
        ResearchFinding(
            title="下一步验证",
            summary=report.decision.strengthen_condition,
            target=report.name,
        ),
    )
    generated_at = datetime.now().astimezone().isoformat(timespec="seconds")
    return ResearchWorkspaceResult(
        ok=True,
        status="partial",
        module="stock",
        generated_at=generated_at,
        verdict=(
            f"{report.name}当前为{report.decision.verdict}：{report.trend}，"
            f"先按{report.risk_level}风险级别处理，等待下一项确认。"
        ),
        action=report.decision.today_action,
        primary_risk=_primary_constraint(raw, report),
        findings=findings,
        missing_sections=missing,
        subject_count=1,
        coverage_ready=len(available_items),
        coverage_total=len(items),
        delivery="local_fallback",
        data_label="本地证据",
        fallback_reason=FALLBACK_REASON,
        as_of=report.latest_date,
        module_items=items,
        decision_label=report.decision.verdict,
    )


def _stock_item(label: str, summary: str, available: bool) -> ResearchModuleItem:
    return ResearchModuleItem(
        kind="stock_dimension",
        label=label,
        summary=summary,
        risk="证据待补，结论强度已降低。" if not available else "按条件验证，不作单点判断。",
        status="ready" if available else "missing",
    )


def _fundamental_summary(metrics: dict[str, Any]) -> str:
    if not metrics:
        return "财务质量需要实时研究恢复后补充。"
    labels = {
        "roe": "ROE",
        "revenue_yoy": "营收同比",
        "net_profit_yoy": "净利润同比",
        "gross_margin": "毛利率",
        "debt_to_assets": "资产负债率",
    }
    facts = []
    for key, label in labels.items():
        value = metrics.get(key)
        if value not in {None, ""}:
            suffix = "%" if isinstance(value, (int, float)) else ""
            facts.append(f"{label} {value}{suffix}")
    return "；".join(facts[:4]) or "已有财务快照，但关键指标仍需补充。"


def _market_summary(report: Any) -> str:
    fund = "资金数据待补"
    if report.fund_flow is not None:
        direction = "净流入" if report.fund_flow >= 0 else "净流出"
        fund = f"主力资金{direction} {abs(report.fund_flow):.2f} 亿元"
    return (
        f"最新收盘 {report.latest_close:.2f}，单日 {report.pct_change:+.2f}%，"
        f"短期为{report.trend}，{fund}。"
    )


def _event_summary(raw: Any) -> str:
    if raw.announcements:
        title = str(raw.announcements[0].get("title") or "最新公告")
        return f"最新事项：{title}。需核对其对盈利与预期的实际影响。"
    if raw.news_items:
        return f"最新公开信息：{raw.news_items[0].title}。需继续核对事实与影响。"
    return "近期事件证据不足，实时研究恢复后补充。"


def _announcement_summary(announcements: list[dict[str, object]]) -> str:
    if not announcements:
        return "公告事项需要实时研究恢复后补充。"
    latest = announcements[0]
    date = str(latest.get("date") or "日期待核对")
    title = str(latest.get("title") or "公告标题待核对")
    return f"{date}：{title}。"


def _primary_constraint(raw: Any, report: Any) -> str:
    if not raw.fundamental_metrics:
        return "财务与经营证据不完整，不能只按价格趋势行动。"
    if report.risk_level == "高":
        return "价格波动风险较高，确认信号出现前先控制风险暴露。"
    if raw.fundamental_metrics.get("net_profit_yoy") not in {None, ""}:
        value = raw.fundamental_metrics["net_profit_yoy"]
        if isinstance(value, (int, float)) and value < 0:
            return f"净利润同比 {value:.1f}%，盈利修复尚未确认。"
    return "机构预期与研报观点缺失，当前结论只用于条件复核。"
