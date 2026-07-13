from __future__ import annotations

import math
import re
from statistics import pstdev

from stock_ts.models import StockRawData
from stock_ts.professional_research import EventRadar, TechnicalProfile

from .stock_dossier_models import DiagnosticBlock, RiskItem


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


def build_technical_diagnostic(
    raw: StockRawData,
    technical: TechnicalProfile,
) -> DiagnosticBlock:
    closes = [bar.close for bar in raw.bars]
    if not closes:
        return DiagnosticBlock(
            name="技术结构",
            status="missing",
            conclusion="K 线缺失，不能判断价格结构。",
            facts=(),
            risks=("价格证据缺口",),
            limitation="需要至少两个交易日；多周期判断需要至少 61 个收盘价。",
        )
    return_1 = _period_return(closes, 1)
    return_5 = _period_return(closes, 5)
    return_20 = _period_return(closes, 20)
    return_60 = _period_return(closes, 60)
    recent_60 = closes[-60:]
    high_60 = max(recent_60)
    low_20 = min(closes[-20:])
    latest = closes[-1]
    drawdown_60 = (latest / high_60 - 1) * 100 if high_60 else None
    volatility_20 = _realized_volatility(closes[-21:])
    if (
        technical.ma20 is not None
        and latest < technical.ma20
        and latest <= low_20 * 1.03
    ):
        regime = "破位风险"
    elif return_20 is not None and return_20 <= -10 and (
        (return_1 is not None and return_1 > 0)
        or (return_5 is not None and return_5 > 0)
    ):
        regime = "反弹尝试，尚未修复中期趋势"
    elif (
        technical.ma20 is not None
        and latest < technical.ma20
        and return_20 is not None
        and return_20 < 0
    ):
        regime = "趋势走弱"
    elif (
        technical.ma20 is not None
        and latest >= technical.ma20
        and return_20 is not None
        and return_20 > 0
        and technical.volume_ratio >= 1.0
    ):
        regime = "趋势延续"
    else:
        regime = "区间整理"
    facts = tuple(
        item
        for item in (
            _return_fact("5日", return_5),
            _return_fact("20日", return_20),
            _return_fact("60日", return_60),
            _return_fact("距60日高点", drawdown_60),
            _return_fact("20日年化波动", volatility_20),
            f"支撑 {technical.support:.2f} / 压力 {technical.resistance:.2f}",
            f"RSI14 {technical.rsi14:.1f}" if technical.rsi14 is not None else "",
            technical.macd_status,
            f"量能比 {technical.volume_ratio:.2f}x",
        )
        if item
    )
    risks = []
    if return_20 is not None and return_20 <= -10:
        risks.append("20日价格损伤")
    if drawdown_60 is not None and drawdown_60 <= -20:
        risks.append("距60日高点回撤较大")
    status = "complete" if len(closes) >= 61 else "degraded"
    return DiagnosticBlock(
        name="技术结构",
        status=status,
        conclusion=f"{regime}；{technical.structure}。",
        facts=facts,
        risks=tuple(risks),
        limitation="技术结构定义触发与失效，不证明盈利质量或长期价值。",
    )


def build_capital_diagnostic(raw: StockRawData) -> DiagnosticBlock:
    detail = raw.fund_flow_detail
    source = str(detail.get("source") or "")
    true_money_flow = raw.fund_flow is not None and any(
        marker in source.lower() for marker in ("moneyflow", "fund_flow")
    )
    if true_money_flow:
        direction = "主力净流入" if raw.fund_flow >= 0 else "主力净流出"
        facts = [f"{direction} {abs(raw.fund_flow):.2f} 亿"]
        main_pct = _number(detail.get("main_net_pct"))
        if main_pct is not None:
            facts.append(f"主力净占比 {main_pct:.2f}%")
        return DiagnosticBlock(
            name="资金与交易",
            status="degraded",
            conclusion=f"{direction}证据可用，但仍需价格确认。",
            facts=tuple(facts),
            risks=(),
            limitation="单日资金流不能证明持续性。",
        )
    amount = _number(detail.get("amount_yuan"))
    turnover = _number(detail.get("turnover_rate"))
    facts = tuple(
        item
        for item in (
            f"成交额 {amount / 100_000_000:.2f} 亿" if amount is not None else "",
            f"换手率 {turnover:.2f}%" if turnover is not None else "",
            f"来源 {source}" if source else "",
        )
        if item
    )
    if not facts:
        return DiagnosticBlock(
            name="资金与交易",
            status="missing",
            conclusion="资金与成交活跃度证据缺失。",
            facts=(),
            risks=("资金证据缺口",),
            limitation="不能用成交量代理主力净流入。",
        )
    risk = ("高换手可能代表分歧",) if turnover is not None and turnover >= 8 else ()
    return DiagnosticBlock(
        name="资金与交易",
        status="degraded",
        conclusion="成交活跃度可用，只用于判断交易分歧与承接。",
        facts=facts,
        risks=risk,
        limitation="单日成交活跃不等同主力净流入，也不能证明资金持续性。",
    )


def build_event_diagnostic(
    raw: StockRawData,
    event_radar: EventRadar,
) -> tuple[DiagnosticBlock, tuple[RiskItem, ...]]:
    rows: list[tuple[str, str]] = []
    for item in raw.announcements:
        title = str(item.get("title") or "").strip()
        summary = str(item.get("summary") or "").strip()
        if title:
            rows.append((title, summary))
    rows.extend(
        (item.title.strip(), item.summary.strip())
        for item in raw.news_items
        if item.title.strip()
    )
    risks: list[RiskItem] = []
    seen: set[tuple[str, str]] = set()
    for title, summary in rows:
        risk = _event_risk(title, summary)
        if risk is None or (risk.category, risk.evidence) in seen:
            continue
        risks.append(risk)
        seen.add((risk.category, risk.evidence))
    if not rows:
        return (
            DiagnosticBlock(
                name="事件风险",
                status="missing",
                conclusion="新闻公告缺失，不能排除事件风险。",
                facts=(),
                risks=("事件证据缺口",),
                limitation="缺少事件数据不代表没有事件风险。",
            ),
            (),
        )
    high_count = sum(item.severity in {"critical", "high"} for item in risks)
    if any(item.severity == "critical" for item in risks):
        conclusion = "存在关键级事件风险，新开仓必须暂停。"
        status = "blocked"
    elif high_count:
        conclusion = f"识别到 {high_count} 项高等级事件风险，动作必须降级。"
        status = "degraded"
    else:
        conclusion = "未识别关键级标题风险，但仍需复核公告原文。"
        status = "degraded"
    facts = tuple(title for title, _ in rows[:5])
    return (
        DiagnosticBlock(
            name="事件风险",
            status=status,
            conclusion=f"{conclusion} 事件闸门：{event_radar.gate}。",
            facts=facts,
            risks=tuple(item.evidence for item in risks),
            limitation="标题与摘要分类只用于筛查，未代替公告原文复核。",
        ),
        tuple(risks),
    )


def _event_risk(title: str, summary: str) -> RiskItem | None:
    text = f"{title} {summary}".strip()
    critical_markers = {
        "退市": "退市风险",
        "立案调查": "监管立案",
        "重大诉讼": "重大诉讼",
        "重大处罚": "监管处罚",
    }
    for marker, category in critical_markers.items():
        if marker in text:
            return RiskItem(
                "critical",
                category,
                title,
                "暂停新开仓并优先核对影响范围",
                "等待公告原文、金额与处置进度",
            )
    if "质押" in text:
        percentages = [float(value) for value in re.findall(r"(\d+(?:\.\d+)?)%", text)]
        pledge = max(percentages, default=None)
        evidence = f"{title}（识别质押比例 {pledge:.2f}%）" if pledge is not None else title
        monitor = (
            "复核累计质押比例、补充质押用途与平仓风险"
            if pledge is not None
            else "原文复核累计质押比例与平仓风险"
        )
        return RiskItem(
            "high",
            "股权质押",
            evidence,
            "限制新开仓与加仓，防止控制权或流动性风险扩散",
            monitor,
        )
    high_markers = {
        "减持": "股东减持",
        "财务资助": "财务资助",
        "担保": "对外担保",
        "业绩预亏": "业绩亏损",
        "亏损": "业绩亏损",
    }
    for marker, category in high_markers.items():
        if marker in text:
            return RiskItem(
                "high",
                category,
                title,
                "动作上限降为等待或风险控制",
                "复核金额、期限、对象与实际影响",
            )
    return None


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


def _period_return(closes: list[float], sessions: int) -> float | None:
    if len(closes) <= sessions or closes[-sessions - 1] == 0:
        return None
    return (closes[-1] / closes[-sessions - 1] - 1) * 100


def _realized_volatility(closes: list[float]) -> float | None:
    if len(closes) < 3:
        return None
    returns = [
        current / previous - 1
        for previous, current in zip(closes, closes[1:])
        if previous > 0
    ]
    return pstdev(returns) * math.sqrt(252) * 100 if len(returns) >= 2 else None


def _return_fact(label: str, value: float | None) -> str:
    return "" if value is None else f"{label} {value:+.2f}%"
