from __future__ import annotations

from .deep_models import BatchAnalysisReport, DailyDeepReport, DebateRound, DeepStockReport
from .report import (
    render_candidate_pool_markdown,
    render_portfolio_markdown,
    render_sector_markdown,
)


def render_deep_stock_markdown(report: DeepStockReport) -> str:
    lines = [
        f"# 多角度深度分析：{report.name}（{report.code}）",
        "",
        report.disclaimer,
        "",
        "## 核心结论",
        f"- 最新日期：{report.trade_date}",
        f"- 最新收盘：{report.latest_close:.2f}",
        f"- 趋势：{report.trend}",
        f"- 风险等级：{report.risk_level}",
        f"- 结论：{report.final_conclusion}",
        f"- 综合机会评分：{report.upside.score}/100（{report.upside.label}）",
        "",
        "## 多角度评分",
    ]
    for angle in report.angles:
        lines.append(f"- {angle.name}：{angle.score}/100（{angle.stance}）- {angle.evidence}")
    lines.extend(
        [
            "",
            "## 情景推演",
            f"- 基准情景：{report.upside.base_case}",
            f"- 乐观情景：{report.upside.bull_case}",
            f"- 悲观情景：{report.upside.bear_case}",
            "",
            "## 驱动因素",
        ]
    )
    lines.extend(f"- {item}" for item in report.upside.drivers)
    lines.extend(["", "## 多轮对抗"])
    for debate in _debate_rounds(report):
        lines.extend(
            [
                f"### {debate.role}",
                f"- 观点：{debate.thesis}",
                f"- 证据：{'；'.join(debate.evidence)}",
                f"- 反驳/约束：{debate.rebuttal}",
                "",
            ]
        )
    lines.extend(["## 风险与失效条件"])
    lines.extend(f"- {item}" for item in report.invalid_conditions)
    lines.extend(["", "## 跟踪计划"])
    lines.extend(f"- {item}" for item in report.action_plan)
    return "\n".join(lines).strip() + "\n"


def render_batch_markdown(report: BatchAnalysisReport) -> str:
    lines = [
        f"# 批量个股深度对比（{report.trade_date}）",
        "",
        report.disclaimer,
        "",
        "## 排名结论",
        f"- 大盘背景：{report.market_summary}",
    ]
    if report.sector_mainline:
        lines.append(f"- 市场主线：{'、'.join(report.sector_mainline)}")
    lines.extend(["", "## 对比表"])
    for index, stock in enumerate(report.stocks, start=1):
        lines.append(
            f"{index}. {stock.name}（{stock.code}）：综合机会评分 "
            f"{stock.upside.score}/100（{stock.upside.label}），趋势 {stock.trend}，"
            f"风险 {stock.risk_level}"
        )
        lines.append(f"   - 结论：{stock.final_conclusion}")
        lines.append(f"   - 失效条件：{'；'.join(stock.invalid_conditions[:2])}")
    lines.extend(["", "## 使用说明"])
    lines.extend(f"- {item}" for item in report.comparison_notes)
    return "\n".join(lines).strip() + "\n"


def render_daily_deep_markdown(report: DailyDeepReport) -> str:
    lines = [
        f"# StockTS 每日深度复盘（{report.trade_date}）",
        "",
        report.disclaimer,
        "",
        "## 深度结论",
        (
            f"- 市场：{report.market.summary}，状态 {report.market.regime}，"
            f"热度 {report.market.heat_score}/100"
        ),
        f"- 板块：{'、'.join(report.sectors.market_mainline)}",
            f"- 候选：{len(report.candidates.candidates)} 只观察票，必须等待次日确认条件。",
    ]
    if report.portfolio is not None:
        lines.append(
            f"- 持仓：组合健康度 {report.portfolio.health_score}/100，"
            f"浮动盈亏 {report.portfolio.total_pnl:.2f}。"
        )
    if report.news is not None:
        lines.append(f"- 新闻舆情：{report.news.summary}")
    lines.extend(
        [
            "",
            "## 今日重点",
            *_daily_focus_lines(report),
            "",
            "## 每日大盘情况",
            f"- {report.market.summary}",
            f"- 涨跌家数比 {report.market.breadth_ratio:.2f}",
            "",
            "## 板块情况",
        ]
    )
    lines.extend(f"- {name}" for name in report.sectors.market_mainline)
    lines.extend(
        [
            "",
            "## 板块统一方法链",
            _extract_embedded_section(render_sector_markdown(report.sectors), "## 板块统一方法链"),
        ]
    )
    lines.extend(["", "## 持仓分析"])
    if report.portfolio is None:
        lines.append("- 未提供持仓，本次不生成组合暴露分析。")
    else:
        lines.extend(f"- {item}" for item in report.portfolio.risk_alerts)
        lines.extend(
            [
                "",
                "## 持仓股票统一方法链",
                _extract_embedded_section(
                    render_portfolio_markdown(report.portfolio),
                    "## 持仓股票统一方法链",
                ),
            ]
        )
    lines.extend(["", "## 新闻舆情"])
    if report.news is None:
        lines.append("- 未提供新闻舆情输入。")
    else:
        lines.append(f"- {report.news.summary}")
        lines.extend(f"- {item}" for item in report.news.risks)
    lines.extend(["", "## 个股深度观察"])
    for stock in report.stocks:
        lines.extend(_daily_stock_latest_method_lines(stock))
    lines.extend(["", "## 多轮对抗摘要"])
    for stock in report.stocks[:3]:
        lines.extend(_daily_debate_summary_lines(stock))
    lines.extend(
        [
            "",
            "## 候选股票池摘要",
            _strip_embedded_disclaimers(render_candidate_pool_markdown(report.candidates)),
        ]
    )
    return "\n".join(lines).strip() + "\n"


def _strip_embedded_disclaimers(markdown: str) -> str:
    lines = []
    for line in markdown.strip().splitlines():
        stripped = line.strip()
        if not stripped:
            lines.append(line)
            continue
        if stripped.startswith("免责声明："):
            continue
        if "不构成投资建议" in stripped:
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def _extract_embedded_section(markdown: str, heading: str) -> str:
    lines = markdown.splitlines()
    capture = False
    captured: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped == heading:
            capture = True
            continue
        if capture and stripped.startswith("## "):
            break
        if capture:
            captured.append(line)
    return _strip_embedded_disclaimers("\n".join(captured)).strip()


def _daily_focus_lines(report: DailyDeepReport) -> list[str]:
    lines = [
        (
            f"- 大盘：{report.market.regime}，热度 {report.market.heat_score}/100；"
            "先看涨跌家数和跌停扩散。"
        ),
        f"- 主线：{'、'.join(report.sectors.market_mainline[:4]) or '未识别主线'}。",
    ]
    if report.portfolio is None:
        lines.append("- 持仓：未提供持仓；只看市场和候选，不做组合动作。")
    else:
        risks = "、".join(report.portfolio.risk_alerts[:2]) or "暂无高优先级风险"
        lines.append(
            f"- 持仓：健康度 {report.portfolio.health_score}/100；先处理 {risks}。"
        )
    if report.candidates.candidates:
        top = report.candidates.candidates[0]
        lines.append(
            f"- 机会：先看 {top.name}（{top.sector}）；只在开盘承接和板块延续时观察。"
        )
    else:
        lines.append("- 机会：候选池为空；不临时扩大战线。")
    return lines


def _debate_rounds(report: DeepStockReport) -> list[DebateRound]:
    if report.debate_rounds:
        return report.debate_rounds
    return [_fallback_judge(report)]


def _judge_round(report: DeepStockReport) -> DebateRound:
    return next(
        (round_ for round_ in report.debate_rounds if round_.role == "裁判结论"),
        report.debate_rounds[-1] if report.debate_rounds else _fallback_judge(report),
    )


def _daily_stock_latest_method_lines(report: DeepStockReport) -> list[str]:
    news = next((item for item in report.angles if item.name == "新闻舆情"), None)
    action = report.action_plan[0] if report.action_plan else "今日动作：等待量价和风险信号确认"
    lines = [
        f"- {report.name}（{report.code}）：{report.upside.score}/100，{report.final_conclusion}",
        f"  - 今日动作：{action}",
    ]
    if news is not None:
        lines.append(f"  - 消息事件/新闻舆情：{news.evidence}")
    if report.risks:
        lines.append(f"  - 主要风险：{'；'.join(report.risks[:2])}")
    return lines


def _daily_debate_summary_lines(report: DeepStockReport) -> list[str]:
    rounds = {item.role: item for item in report.debate_rounds}
    roles = ["技术分析师", "新闻情绪分析师", "多头研究员", "空头研究员", "风控经理", "组合经理"]
    lines = [f"- {report.name}："]
    for role in roles:
        item = rounds.get(role)
        if item is None:
            continue
        lines.append(f"  - {role}：{item.thesis}；约束：{item.rebuttal}")
    if len(lines) == 1:
        judge = _judge_round(report)
        lines.append(f"  - 裁判结论：{judge.thesis}；约束：{judge.rebuttal}")
    return lines


def _fallback_judge(report: DeepStockReport) -> DebateRound:
    return DebateRound(
        role="裁判结论",
        thesis=report.final_conclusion,
        evidence=[f"综合观察分 {report.upside.score}/100", f"风险等级 {report.risk_level}"],
        rebuttal="缺少完整多轮对抗明细，按规则结论保持观察。",
    )
