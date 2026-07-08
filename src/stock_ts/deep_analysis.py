from __future__ import annotations

from .deep_models import (
    AnalysisAngle,
    BatchAnalysisReport,
    DebateRound,
    DeepStockReport,
    UpsidePotential,
)
from .deep_report import (
    render_batch_markdown as render_batch_markdown,
)
from .deep_report import (
    render_daily_deep_markdown as render_daily_deep_markdown,
)
from .deep_report import (
    render_deep_stock_markdown as render_deep_stock_markdown,
)
from .models import (
    MarketSnapshot,
    NewsSentimentReport,
    PortfolioAnalysisReport,
    SectorAnalysisReport,
    StockAnalysisReport,
)
from .symbols import sector_for_code

__all__ = [
    "AnalysisAngle",
    "BatchAnalysisReport",
    "DebateRound",
    "DeepStockReport",
    "UpsidePotential",
    "analyze_batch_stocks",
    "analyze_deep_stock",
    "build_debate_rounds",
    "render_batch_markdown",
    "render_daily_deep_markdown",
    "render_deep_stock_markdown",
]


def analyze_deep_stock(
    stock: StockAnalysisReport,
    *,
    market: MarketSnapshot,
    sectors: SectorAnalysisReport | None = None,
    news: NewsSentimentReport | None = None,
    portfolio: PortfolioAnalysisReport | None = None,
) -> DeepStockReport:
    angles = _build_angles(stock, market, sectors, news, portfolio)
    risks = _risk_points(stock, market, news)
    invalid_conditions = _invalid_conditions(stock, market, sectors)
    upside = _build_upside(stock, angles, risks, invalid_conditions)
    draft = DeepStockReport(
        code=stock.code,
        name=stock.name,
        trade_date=stock.latest_date or market.trade_date,
        latest_close=stock.latest_close,
        trend=stock.trend,
        risk_level=stock.risk_level,
        angles=angles,
        upside=upside,
        debate_rounds=[],
        final_conclusion=_final_conclusion(stock, upside, angles, invalid_conditions),
        action_plan=_action_plan(stock, upside, market),
        risks=risks,
        invalid_conditions=invalid_conditions,
    )
    return DeepStockReport(
        code=draft.code,
        name=draft.name,
        trade_date=draft.trade_date,
        latest_close=draft.latest_close,
        trend=draft.trend,
        risk_level=draft.risk_level,
        angles=draft.angles,
        upside=draft.upside,
        debate_rounds=_build_debate_from_inputs(draft),
        final_conclusion=draft.final_conclusion,
        action_plan=draft.action_plan,
        risks=draft.risks,
        invalid_conditions=draft.invalid_conditions,
    )


def build_debate_rounds(report: DeepStockReport) -> list[DebateRound]:
    return list(report.debate_rounds) or _build_debate_from_inputs(report)


def analyze_batch_stocks(
    reports: list[DeepStockReport],
    *,
    market: MarketSnapshot,
    sectors: SectorAnalysisReport | None = None,
) -> BatchAnalysisReport:
    ranked = sorted(reports, key=lambda item: item.upside.score, reverse=True)
    comparison_notes = [
        "排序依据为趋势、市场、板块、舆情、风险约束的综合观察分。",
        "只作为观察优先级，不代表确定上涨、买入建议或收益承诺。",
        "同分时优先选择风险约束更清晰、失效条件更容易执行的标的。",
    ]
    if ranked:
        comparison_notes.append(f"当前观察优先级第一为 {ranked[0].name}（{ranked[0].code}）。")
    return BatchAnalysisReport(
        trade_date=market.trade_date,
        stocks=ranked,
        market_summary=market.summary,
        sector_mainline=list(sectors.market_mainline if sectors else []),
        comparison_notes=comparison_notes,
    )


def _build_angles(
    stock: StockAnalysisReport,
    market: MarketSnapshot,
    sectors: SectorAnalysisReport | None,
    news: NewsSentimentReport | None,
    portfolio: PortfolioAnalysisReport | None,
) -> list[AnalysisAngle]:
    trend_score = _trend_score(stock)
    volume_score = _volume_score(stock)
    market_score = market.heat_score
    sector_score = _sector_score(stock, sectors)
    news_score = _news_score(news)
    risk_score = _risk_score(stock)
    angles = [
        AnalysisAngle("价格趋势", trend_score, _stance(trend_score), stock.trend),
        AnalysisAngle("量能结构", volume_score, _stance(volume_score), _volume_evidence(stock)),
        AnalysisAngle("市场环境", market_score, _stance(market_score), market.summary),
        AnalysisAngle(
            "板块主线",
            sector_score,
            _stance(sector_score),
            _sector_evidence(stock, sectors),
        ),
        AnalysisAngle("新闻舆情", news_score, _stance(news_score), _news_evidence(news)),
        AnalysisAngle(
            "风险约束",
            risk_score,
            _stance(risk_score),
            f"个股风险等级 {stock.risk_level}",
        ),
    ]
    if portfolio is not None:
        angles.append(_portfolio_angle(stock, portfolio))
    return angles


def _build_upside(
    stock: StockAnalysisReport,
    angles: list[AnalysisAngle],
    risks: list[str],
    invalid_conditions: list[str],
) -> UpsidePotential:
    weighted = sum(angle.score for angle in angles) / max(len(angles), 1)
    if stock.risk_level == "高":
        weighted -= 8
    score = max(0, min(100, int(round(weighted))))
    label = "高潜力观察" if score >= 75 else "中性偏强观察" if score >= 60 else "谨慎观察"
    drivers = [angle.evidence for angle in angles if angle.score >= 65][:4]
    if not drivers:
        drivers = ["缺少强驱动信号，等待量价、板块或舆情进一步确认"]
    return UpsidePotential(
        score=score,
        label=label,
        base_case=f"若 {stock.name} 维持 {stock.trend} 且大盘不转弱，可继续跟踪强弱变化。",
        bull_case="若板块主线延续、成交放大且风险信号未触发，上涨潜力观察分可上修。",
        bear_case=f"若触发 {invalid_conditions[0]}，优先按风控处理而不是补仓摊低。",
        drivers=drivers,
        invalid_conditions=invalid_conditions,
    )


def _build_debate_from_inputs(report: DeepStockReport) -> list[DebateRound]:
    angles = {angle.name: angle for angle in report.angles}
    strong = [angle for angle in report.angles if angle.score >= 65]
    weak = [angle for angle in report.angles if angle.score < 55]
    bull_evidence = _angle_lines(strong[:3]) or ["暂无压倒性强信号，仅适合保持观察"]
    bear_evidence = _angle_lines(weak[:3]) or report.risks[:2] or ["短线一致性过强时仍需防范回撤"]
    technical = angles.get("价格趋势")
    volume = angles.get("量能结构")
    fundamental = angles.get("风险约束")
    sentiment = angles.get("新闻舆情")
    sector = angles.get("板块主线")
    portfolio = angles.get("持仓影响")
    return [
        DebateRound(
            role="技术分析师",
            thesis=_analyst_thesis(report.name, technical, "技术结构"),
            evidence=_angle_lines([technical, volume]),
            rebuttal="技术结论必须等待开盘承接和 5 日线有效性确认。",
        ),
        DebateRound(
            role="基本面分析师",
            thesis=_analyst_thesis(report.name, fundamental, "估值/风险约束"),
            evidence=_angle_lines([fundamental]),
            rebuttal="基本面和估值信号不能替代短线价格确认。",
        ),
        DebateRound(
            role="新闻情绪分析师",
            thesis=_analyst_thesis(report.name, sentiment, "消息/情绪"),
            evidence=_angle_lines([sentiment, sector]),
            rebuttal="缺少新闻或题材证据时，情绪结论降级为观察项。",
        ),
        DebateRound(
            role="多头研究员",
            thesis=f"{report.name} 的可观察机会来自 {report.upside.label} 与强证据共振。",
            evidence=bull_evidence,
            rebuttal="多头观点只有在量价承接和板块延续同时满足时才成立。",
        ),
        DebateRound(
            role="空头研究员",
            thesis=f"{report.name} 仍有回撤或跑输风险，不能只看单一强指标。",
            evidence=bear_evidence,
            rebuttal="若价格、板块和资金同步改善，空头约束会下降。",
        ),
        DebateRound(
            role="交易员",
            thesis=f"{report.name} 当前只进入条件化执行清单，不做无条件交易。",
            evidence=[
                f"综合观察分 {report.upside.score}/100",
                f"触发条件：{_trade_trigger(report)}",
            ],
            rebuttal="开盘高开过多、承接不足或跌破失效线时不执行。",
        ),
        DebateRound(
            role="风控经理",
            thesis=f"{report.name} 的首要任务是控制失效条件，而不是预测涨幅。",
            evidence=[
                f"风险等级 {report.risk_level}",
                f"反证/失效条件：{report.invalid_conditions[0]}",
                *report.risks[:2],
            ],
            rebuttal="未定义止损/降级条件时，不允许提高观察优先级。",
        ),
        DebateRound(
            role="组合经理",
            thesis=_portfolio_manager_thesis(report, portfolio),
            evidence=_angle_lines([portfolio]) or [f"综合观察分 {report.upside.score}/100"],
            rebuttal="组合动作服从整体仓位和市场热度，不因单票结论孤立加仓。",
        ),
    ]


def _angle_lines(angles: list[AnalysisAngle | None]) -> list[str]:
    return [f"{angle.name}：{angle.score}/100，{angle.evidence}" for angle in angles if angle]


def _trade_trigger(report: DeepStockReport) -> str:
    return report.action_plan[1] if len(report.action_plan) > 1 else report.action_plan[0]


def _analyst_thesis(stock_name: str, angle: AnalysisAngle | None, domain: str) -> str:
    if angle is None:
        return f"{stock_name} 的{domain}证据不足，暂不作为主判断。"
    if angle.score >= 70:
        stance = "支持继续跟踪"
    elif angle.score < 55:
        stance = "构成主要约束"
    else:
        stance = "处于待验证状态"
    return f"{stock_name} 的{domain}{stance}。"


def _portfolio_manager_thesis(
    report: DeepStockReport,
    portfolio: AnalysisAngle | None,
) -> str:
    if portfolio is None:
        return f"{report.name} 未识别组合暴露，只能作为观察池标的处理。"
    if portfolio.score >= 65:
        return f"{report.name} 对组合影响可控，可保留观察但不脱离总仓位纪律。"
    return f"{report.name} 对组合形成压力，先降风险或降低观察优先级。"


def _trend_score(stock: StockAnalysisReport) -> int:
    if stock.trend == "上升趋势":
        return 78 if stock.pct_change >= 0 else 68
    if stock.trend == "下降趋势":
        return 35
    return 56


def _volume_score(stock: StockAnalysisReport) -> int:
    joined = "；".join(stock.observations)
    if "明显放大" in joined:
        return 70
    if "收缩" in joined:
        return 45
    return 58


def _sector_score(stock: StockAnalysisReport, sectors: SectorAnalysisReport | None) -> int:
    if sectors is None:
        return 50
    guessed = _guess_sector(stock)
    if guessed and guessed in sectors.market_mainline:
        return 74
    if guessed:
        matched = next((item for item in sectors.sectors if item.name == guessed), None)
        return matched.heat_score if matched else 58
    return 58


def _news_score(news: NewsSentimentReport | None) -> int:
    if news is None:
        return 50
    score = 50 + news.positive_count * 8 - news.negative_count * 12
    return max(0, min(100, score))


def _risk_score(stock: StockAnalysisReport) -> int:
    return {"低": 78, "中": 58, "高": 35}.get(stock.risk_level, 55)


def _stance(score: int) -> str:
    if score >= 70:
        return "偏多"
    if score <= 45:
        return "偏空"
    return "中性"


def _guess_sector(stock: StockAnalysisReport) -> str:
    mapped = sector_for_code(stock.code)
    if mapped:
        return mapped
    if stock.code == "300750" or "宁德" in stock.name:
        return "新能源车"
    if stock.code == "000001" or "银行" in stock.name:
        return "银行"
    if stock.code == "600519" or "茅台" in stock.name or "五粮液" in stock.name:
        return "白酒"
    return ""


def _sector_evidence(stock: StockAnalysisReport, sectors: SectorAnalysisReport | None) -> str:
    if sectors is None:
        return "未接入板块报告，保持中性"
    guessed = _guess_sector(stock)
    if guessed:
        matched = next((item for item in sectors.sectors if item.name == guessed), None)
        in_mainline = guessed in sectors.market_mainline
        if matched:
            status = "在主线内" if in_mainline else "不在前三主线"
            return (
                f"所属方向 {guessed} {status}，板块热度 {matched.heat_score}/100，"
                f"涨跌 {matched.pct_chg:.2f}%"
            )
        status = "在主线内" if in_mainline else "不在当前主线"
        return f"所属方向 {guessed} {status}，当前主线为 {'、'.join(sectors.market_mainline)}"
    return f"未识别明确行业映射，当前主线为 {'、'.join(sectors.market_mainline)}"


def _volume_evidence(stock: StockAnalysisReport) -> str:
    return next((item for item in stock.observations if "量能" in item), "暂无量能描述")


def _news_evidence(news: NewsSentimentReport | None) -> str:
    if news is None:
        return "未提供新闻舆情，保持中性"
    return news.summary


def _portfolio_angle(
    stock: StockAnalysisReport,
    portfolio: PortfolioAnalysisReport,
) -> AnalysisAngle:
    position = next(
        (item for item in portfolio.positions if item.holding.code == stock.code),
        None,
    )
    if position is None:
        return AnalysisAngle("持仓影响", 55, "中性", "当前未持仓，不产生组合集中度影响")
    score = 72 if position.pnl_ratio >= 0 and position.weight < 0.35 else 48
    return AnalysisAngle(
        "持仓影响",
        score,
        _stance(score),
        f"仓位 {position.weight:.1%}，浮动盈亏 {position.pnl_ratio:.2f}%",
    )


def _risk_points(
    stock: StockAnalysisReport,
    market: MarketSnapshot,
    news: NewsSentimentReport | None,
) -> list[str]:
    risks = [f"个股风险等级为 {stock.risk_level}"]
    if market.heat_score < 45:
        risks.append("市场热度偏低，个股信号容易失真")
    if stock.pct_change > 5:
        risks.append("短线涨幅偏大，追高回撤风险上升")
    if news is not None:
        risks.extend(news.risks[:2])
    return list(dict.fromkeys(risks))


def _invalid_conditions(
    stock: StockAnalysisReport,
    market: MarketSnapshot,
    sectors: SectorAnalysisReport | None,
) -> list[str]:
    conditions = [
        "跌破 5 日均线且成交额放大",
        "大盘热度跌破 45/100 或涨跌家数比明显恶化",
        "出现放量长阴或连续两日弱于所属板块",
    ]
    if sectors is not None:
        conditions.append("所属板块跌出市场主线并出现资金流出")
    if stock.risk_level == "高":
        conditions.insert(0, "高风险状态未修复前不提高观察优先级")
    return conditions


def _final_conclusion(
    stock: StockAnalysisReport,
    upside: UpsidePotential,
    angles: list[AnalysisAngle],
    invalid_conditions: list[str],
) -> str:
    stock_specific = [
        angle
        for angle in angles
        if angle.name in {"价格趋势", "量能结构", "板块主线", "风险约束", "持仓影响"}
    ] or angles
    weak_candidates = [
        angle
        for angle in stock_specific
        if not (angle.name == "新闻舆情" and "未提供" in angle.evidence)
    ] or stock_specific
    primary_candidates = [
        angle
        for angle in stock_specific
        if not any(token in angle.evidence for token in ["未识别", "未提供", "未接入", "暂无"])
    ] or stock_specific
    strong = sorted(primary_candidates, key=lambda item: item.score, reverse=True)
    weak = sorted(weak_candidates, key=lambda item: item.score)
    primary = strong[0] if strong else AnalysisAngle("综合", upside.score, "中性", stock.trend)
    blocker = next((angle for angle in weak if angle.score < 58), weak[0] if weak else primary)
    action = _conclusion_action(upside.score, stock.risk_level)
    blocker_label = "主要矛盾" if blocker.score < 58 else "待验证点"
    advantage = (
        f"优势是{primary.name}：{_compact_evidence(primary.evidence)}"
        if primary.score >= 58
        else f"优势暂不明确：{_compact_evidence(primary.evidence)}"
    )
    return (
        f"{stock.name}：{action}。{advantage}；"
        f"{blocker_label}是{blocker.name}：{_compact_evidence(blocker.evidence)}；"
        f"触发条件看量价承接和板块延续，失效条件为{invalid_conditions[0]}。"
    )


def _conclusion_action(score: int, risk_level: str) -> str:
    if risk_level == "高" or score < 50:
        return "防守观察，先确认风险是否收敛"
    if score >= 75:
        return "高优先级观察，只等开盘承接确认"
    if score >= 60:
        return "条件观察，强弱取决于板块和量能能否同步"
    return "低优先级观察，暂不提高风险暴露"


def _compact_evidence(value: str) -> str:
    clean = " ".join(str(value).strip().split())
    return clean if len(clean) <= 36 else clean[:35].rstrip() + "…"


def _action_plan(
    stock: StockAnalysisReport,
    upside: UpsidePotential,
    market: MarketSnapshot,
) -> list[str]:
    min_market_heat = max(45, market.heat_score - 10)
    return [
        "开盘前确认所属板块是否仍在市场主线或资金活跃方向。",
        "盘中观察 30 分钟承接，避免仅因昨日报告直接行动。",
        f"若观察分维持 {upside.score}/100 且市场热度不低于 "
        f"{min_market_heat}/100，再进入下一轮复盘。",
        f"若触发失效条件，降低 {stock.name} 的观察优先级。",
    ]
