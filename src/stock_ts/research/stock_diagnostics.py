from __future__ import annotations

import math

from stock_ts.models import StockRawData

from .stock_dossier_models import DiagnosticBlock


def build_financial_diagnostic(raw: StockRawData) -> DiagnosticBlock:
    metrics = raw.fundamental_metrics
    revenue = _number(metrics.get("operating_revenue"))
    operating_profit = _number(metrics.get("operating_profit"))
    net_profit = _number(metrics.get("net_profit"))
    operating_cash_flow = _number(metrics.get("operating_cash_flow"))
    eps = _number(metrics.get("eps"))
    bps = _number(metrics.get("net_asset_per_share"))
    facts = tuple(
        item
        for item in (
            _metric("EPS", eps),
            _metric("每股净资产", bps),
            _metric("营业利润", operating_profit),
            _metric("净利润", net_profit),
            _metric("经营现金流", operating_cash_flow),
            _ratio("营业利润率", operating_profit, revenue),
            _ratio("净利率", net_profit, revenue),
        )
        if item
    )
    if not facts and not raw.fundamental_history:
        return DiagnosticBlock(
            name="财务质量",
            status="missing",
            conclusion="财务数据缺失，不能判断盈利与现金流质量。",
            facts=(),
            risks=("财务证据缺口",),
            limitation="需要至少一个可用财务截面；趋势判断需要三个可比期间。",
        )

    conclusions: list[str] = []
    risks: list[str] = []
    if net_profit is not None and net_profit < 0:
        conclusions.append("净利润为负，当前处于亏损状态")
        risks.append("盈利为负")
    elif net_profit is not None:
        conclusions.append("净利润为正")
    if operating_profit is not None and operating_profit < 0:
        conclusions.append("营业利润为负")
        risks.append("主营盈利承压")
    if operating_cash_flow is not None and operating_cash_flow > 0:
        if net_profit is not None and net_profit < 0:
            conclusions.append("经营现金流为正，但尚未转化为会计利润")
        else:
            conclusions.append("经营现金流为正")
    elif operating_cash_flow is not None and operating_cash_flow < 0:
        conclusions.append("经营现金流为负")
        risks.append("现金流承压")
    if not conclusions:
        conclusions.append("已有财务截面，但盈利与现金流方向仍不完整")

    period_count = len(raw.fundamental_history)
    status = "complete" if period_count >= 3 and not risks else "degraded"
    limitation = (
        f"财务历史 {period_count} 期；跨期方向仍需结合基数与报告口径复核。"
        if period_count >= 3
        else "仅有财务截面或少量期间，可判断当前状态，不能声称长期趋势。"
    )
    return DiagnosticBlock(
        name="财务质量",
        status=status,
        conclusion="；".join(conclusions) + "。",
        facts=facts,
        risks=tuple(risks),
        limitation=limitation,
    )


def build_valuation_diagnostic(raw: StockRawData) -> DiagnosticBlock:
    valuation = raw.valuation
    latest_close = raw.bars[-1].close if raw.bars else None
    net_profit = _number(raw.fundamental_metrics.get("net_profit"))
    pe = raw.pe_ttm if raw.pe_ttm is not None else _number(valuation.get("pe_ttm"))
    reported_pb = _number(valuation.get("pb"))
    bps = _number(raw.fundamental_metrics.get("net_asset_per_share"))
    derived_pb = (
        latest_close / bps
        if latest_close is not None and latest_close > 0 and bps is not None and bps > 0
        else None
    )
    conflict = (
        reported_pb is not None
        and reported_pb > 0
        and derived_pb is not None
        and abs(reported_pb - derived_pb) / derived_pb > 0.30
    )
    facts = tuple(
        item
        for item in (
            _multiple("PE(TTM)", pe),
            _multiple("来源 PB", reported_pb),
            _multiple("反算 PB", derived_pb),
            _multiple("PS", _number(valuation.get("ps"))),
        )
        if item
    )
    conclusions: list[str] = []
    risks: list[str] = []
    pe_invalid = (pe is not None and pe <= 0) or (net_profit is not None and net_profit < 0)
    if pe_invalid:
        conclusions.append("公司处于亏损状态，PE 失去解释力")
        risks.append("亏损状态下 PE 不可用")
    elif pe is not None:
        conclusions.append(f"PE(TTM) {pe:.2f}x")
    if conflict and reported_pb is not None and derived_pb is not None:
        conclusions.append(
            f"来源 PB {reported_pb:.2f}x；价格/每股净资产反算 {derived_pb:.2f}x，口径冲突"
        )
        risks.append("口径冲突")
    elif reported_pb is not None:
        conclusions.append(f"PB {reported_pb:.2f}x")
    elif derived_pb is not None:
        conclusions.append(f"价格/每股净资产反算 PB {derived_pb:.2f}x")

    industry_median = _number(valuation.get("industry_pe_median"))
    percentile = _number(valuation.get("pe_percentile"))
    comparable = (
        percentile is not None
        and 0 <= percentile <= 100
        or industry_median is not None
        and industry_median > 0
    )
    if not conclusions:
        return DiagnosticBlock(
            name="估值",
            status="missing",
            conclusion="估值证据缺失。",
            facts=(),
            risks=("缺少估值参照",),
            limitation="需要有效盈利口径、历史分位或同行参照。",
        )
    status = "degraded" if pe_invalid or conflict or not comparable else "complete"
    limitation = (
        "估值来源存在冲突，冲突消除前不得使用低估结论。"
        if conflict
        else "缺少历史分位或同行参照时，只描述绝对估值，不判断低估。"
    )
    return DiagnosticBlock(
        name="估值",
        status=status,
        conclusion="；".join(conclusions) + "。",
        facts=facts,
        risks=tuple(risks),
        limitation=limitation,
    )


def _number(value: object) -> float | None:
    if value in {None, ""}:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _metric(label: str, value: float | None) -> str:
    return "" if value is None else f"{label} {value:.2f}"


def _multiple(label: str, value: float | None) -> str:
    return "" if value is None else f"{label} {value:.2f}x"


def _ratio(
    label: str,
    numerator: float | None,
    denominator: float | None,
) -> str:
    if numerator is None or denominator is None or denominator == 0:
        return ""
    return f"{label} {numerator / denominator * 100:.2f}%"
