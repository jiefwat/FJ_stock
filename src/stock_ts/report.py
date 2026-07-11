from __future__ import annotations

from .agentic_stock_analysis import build_stock_agent_decision_from_report
from .models import (
    CandidatePoolReport,
    CandidateStockAnalysis,
    MarketSnapshot,
    NewsSentimentReport,
    PortfolioAnalysisReport,
    PositionAnalysis,
    SectorAnalysis,
    SectorAnalysisReport,
    StockAnalysisDecision,
    StockAnalysisDimension,
    StockAnalysisReport,
)

DISCLAIMER = "免责声明：本报告仅用于研究与复盘，不构成投资建议。"


def render_market_markdown(snapshot: MarketSnapshot) -> str:
    lines = [
        f"# 每日大盘分析（{snapshot.trade_date}）",
        "",
        DISCLAIMER,
        "",
        "## 市场温度",
        f"- 综合热度：{snapshot.heat_score}/100",
        f"- 涨跌家数比：{snapshot.breadth_ratio:.2f}",
        f"- 市场状态：{snapshot.regime}",
        f"- 结论：{snapshot.summary}",
        "",
        "## 多维度评分",
    ]
    for dimension in snapshot.dimensions:
        lines.append(
            f"- {dimension.name}：{dimension.score}/100（{dimension.status}）- {dimension.evidence}"
        )
    lines.extend(["", "## 主要指数"])
    for index in snapshot.indices:
        lines.append(
            f"- {index.name}（{index.code}）：{index.close:.2f}，涨跌幅 {index.pct_chg:.2f}%"
        )
    lines.extend(["", "## 强势方向（代表强度）"])
    for name, pct in snapshot.top_sectors:
        lines.append(f"- {name}：代表样本 {pct:.2f}%")
    lines.extend(["", "## 机会线索"])
    lines.extend(f"- {item}" for item in snapshot.opportunities)
    lines.extend(["", "## 风险提示"])
    lines.extend(f"- {item}" for item in snapshot.risks)
    lines.extend(["", "## 明日观察"])
    lines.extend(f"- {item}" for item in snapshot.tomorrow_watch)
    return "\n".join(lines) + "\n"


def render_sector_markdown(report: SectorAnalysisReport) -> str:
    lines = [
        f"# 每日板块情况（{report.trade_date}）",
        "",
        DISCLAIMER,
        "",
        "## 市场主线",
    ]
    lines.extend(f"- {name}" for name in report.market_mainline)
    lines.extend(["", "## 板块热度榜"])
    for index, sector in enumerate(report.sectors, start=1):
        lines.append(
            f"{index}. {sector.name}：热度 {sector.heat_score}/100，"
            f"涨跌幅 {sector.pct_chg:.2f}%，{sector.continuity}，"
            f"{sector.fund_status}，{sector.rotation_status}，{sector.risk}"
        )
    lines.extend(["", "## 轮动与持续性"])
    lines.extend(f"- {item}" for item in report.rotation_notes)
    lines.extend(["", "## 板块风险"])
    lines.extend(f"- {item}" for item in report.risk_notes)
    lines.extend(["", "## 板块统一方法链"])
    lines.extend(_sector_method_chain_lines(report.sectors))
    return "\n".join(lines) + "\n"


def render_stock_markdown(report: StockAnalysisReport) -> str:
    agentic = build_stock_agent_decision_from_report(report)
    lines = [
        f"# 个股分析：{report.name}（{report.code}）",
        "",
        DISCLAIMER,
        "",
        "## 快速结论",
        f"- 最新日期：{report.latest_date}",
        f"- 最新收盘：{report.latest_close:.2f}",
        f"- 单日涨跌：{report.pct_change:.2f}%",
        f"- 趋势判断：{report.trend}",
        f"- 风险等级：{report.risk_level}",
        "",
        "## 决策摘要",
        f"- 最终判断：{report.decision.verdict}",
        "- 核心矛盾：" + "；".join(report.decision.core_conflicts[:3]),
        f"- 今日动作：{report.decision.today_action}",
        f"- 不能做什么：{report.decision.forbidden_action}",
        f"- 转强条件：{report.decision.strengthen_condition}",
        f"- 离场条件：{report.decision.exit_condition}",
        f"- 数据可信度：{report.decision.data_reliability}",
        "",
        "## 观察点",
    ]
    lines.extend(f"- {item}" for item in report.observations)
    if report.dimensions:
        lines.extend(["", "## 专业评分卡"])
        for item in report.dimensions:
            lines.append(
                f"- {item.name}：{item.score}/100（{item.status}）｜"
                f"证据：{item.evidence}｜动作：{item.action}"
            )
    lines.extend(
        [
            "",
            "## TradingAgents 决策链",
            (
                "- daily_stock_analysis 信号归因："
                f"技术 {agentic.signal_attribution.technical_indicators}%；"
                f"消息 {agentic.signal_attribution.news_sentiment}%；"
                f"基本面 {agentic.signal_attribution.fundamentals}%；"
                f"资金/成交 {agentic.signal_attribution.capital_volume}%"
            ),
            "- 数据包："
            f"可用 {'、'.join(agentic.context_pack.available_blocks) or '暂无'}；"
            f"缺口 {'、'.join(agentic.context_pack.missing_blocks) or '无'}",
            "",
            "### 分析师团队",
        ]
    )
    for item in agentic.analyst_team:
        lines.append(
            f"- {item.role}：{item.verdict}｜"
            f"证据：{'；'.join(item.evidence[:2])}｜动作：{item.action}"
        )
    lines.extend(
        [
            "",
            "### 多空审议",
            f"- 多头观点：{agentic.research_debate.bull_thesis}",
            f"- 空头观点：{agentic.research_debate.bear_thesis}",
            f"- 研究经理裁决：{agentic.research_debate.judge}",
            "",
            "### 交易与风控",
            f"- 交易员执行：{agentic.trader.action}｜"
            f"触发：{agentic.trader.entry_trigger}｜失效：{agentic.trader.invalidation}",
            f"- 仓位规则：{agentic.trader.position_rule}",
            f"- 组合经理最终意见：{agentic.risk_review.portfolio_decision}",
        ]
    )
    lines.extend(["", "## 后续跟踪"])
    lines.extend(f"- {item}" for item in report.watch_points)
    return "\n".join(lines) + "\n"


def render_portfolio_markdown(report: PortfolioAnalysisReport) -> str:
    lines = [
        f"# 每日持仓分析（{report.trade_date}）",
        "",
        DISCLAIMER,
        "",
        "## 组合健康度",
        f"- 健康度：{report.health_score}/100",
        f"- 总市值：{report.total_market_value:.2f}",
        f"- 持仓成本：{report.total_cost:.2f}",
        f"- 浮动盈亏：{report.total_pnl:.2f}（{report.total_pnl_ratio:.2f}%）",
        f"- 估算当日盈亏：{report.daily_pnl:.2f}",
        f"- 第一大持仓占比：{report.top_position_weight:.1%}",
        f"- 说明：{report.cash_position_note}",
        "",
        "## 行业暴露",
    ]
    lines.extend(f"- {sector}：{weight:.1%}" for sector, weight in report.sector_weights)
    lines.extend(["", "## 持仓明细"])
    for position in report.positions:
        lines.append(
            "- "
            f"{position.holding.name}（{position.holding.code}）："
            f"市值 {position.market_value:.2f}，仓位 {position.weight:.1%}，"
            f"盈亏 {position.pnl:.2f}（{position.pnl_ratio:.2f}%），"
            f"趋势 {position.trend}，风险 {position.risk_level}"
        )
    lines.extend(["", "## 风险提示"])
    lines.extend(f"- {item}" for item in report.risk_alerts)
    lines.extend(["", "## 与市场主线匹配"])
    lines.extend(f"- {item}" for item in report.market_alignment)
    lines.extend(["", "## 今日操作检查清单"])
    lines.extend(f"- {item}" for item in report.action_checklist)
    lines.extend(["", "## 持仓股票统一方法链"])
    lines.extend(_portfolio_method_chain_lines(report.positions, trade_date=report.trade_date))
    return "\n".join(lines) + "\n"


def render_candidate_pool_markdown(report: CandidatePoolReport) -> str:
    lines = [
        f"# 候选股票池 Top {len(report.candidates)}（{report.trade_date}）",
        "",
        DISCLAIMER,
        "",
        f"说明：{report.disclaimer}",
        "",
        "## 观察重点",
    ]
    lines.extend(f"- {item.replace('排序', '观察')}" for item in report.method_notes)
    lines.extend(["", "## 候选股票"])
    for index, candidate in enumerate(report.candidates, start=1):
        lines.append(
            f"{index}. {candidate.name}（{candidate.code}，{candidate.sector}）："
            f"观察分 {candidate.score}/100，最新价 {candidate.latest_close:.2f}，"
            f"日涨跌 {candidate.pct_change:.2f}%"
        )
        lines.append(f"   - 入选理由：{'；'.join(candidate.reasons)}")
        lines.append(f"   - 风险提示：{'；'.join(candidate.risks)}")
        lines.append(f"   - 观察条件：{'；'.join(candidate.watch_conditions)}")
    lines.extend(["", "## 候选股票统一方法链"])
    lines.extend(_candidate_method_chain_lines(report.candidates, trade_date=report.trade_date))
    return "\n".join(lines) + "\n"


def _portfolio_method_chain_lines(
    positions: list[PositionAnalysis], *, trade_date: str
) -> list[str]:
    if not positions:
        return ["- 未提供持仓股票，本次不生成持仓个股方法链。"]
    lines: list[str] = []
    for position in positions:
        report = _stock_report_from_position(position, trade_date=trade_date)
        lines.extend(_compact_agentic_lines(report))
    return lines


def _candidate_method_chain_lines(
    candidates: list[CandidateStockAnalysis], *, trade_date: str
) -> list[str]:
    if not candidates:
        return ["- 候选股票为空，本次不生成候选个股方法链。"]
    lines: list[str] = []
    for candidate in candidates:
        report = _stock_report_from_candidate(candidate, trade_date=trade_date)
        lines.extend(_compact_agentic_lines(report))
    return lines


def _compact_agentic_lines(report: StockAnalysisReport) -> list[str]:
    agentic = build_stock_agent_decision_from_report(report)
    analysts = "；".join(
        f"{item.role}{item.verdict}：{'、'.join(item.evidence[:1]) or '证据待补'}"
        for item in agentic.analyst_team
    )
    return [
        (
            f"- {report.name}（{report.code}）：daily_stock_analysis 信号归因："
            f"技术 {agentic.signal_attribution.technical_indicators}%；"
            f"消息 {agentic.signal_attribution.news_sentiment}%；"
            f"基本面 {agentic.signal_attribution.fundamentals}%；"
            f"资金/成交 {agentic.signal_attribution.capital_volume}%；"
            f"最强正向：{agentic.signal_attribution.strongest_bullish_signal}；"
            f"最强约束：{agentic.signal_attribution.strongest_bearish_signal}"
        ),
        f"  - TradingAgents 分析师团队：{analysts}",
        (
            f"  - 多空审议：{agentic.research_debate.bull_thesis}；"
            f"{agentic.research_debate.bear_thesis}；{agentic.research_debate.judge}"
        ),
        (
            f"  - 交易员/组合经理：{agentic.trader.action}；"
            f"触发：{agentic.trader.entry_trigger}；失效：{agentic.trader.invalidation}；"
            f"{agentic.risk_review.portfolio_decision}"
        ),
    ]


def _stock_report_from_position(
    position: PositionAnalysis, *, trade_date: str
) -> StockAnalysisReport:
    holding = position.holding
    dimensions = [
        StockAnalysisDimension(
            name="技术趋势",
            score=_trend_score(position.trend),
            status=position.trend,
            evidence=f"趋势 {position.trend}，日内涨跌 {position.daily_pnl_ratio:.2f}%",
            action="趋势未破坏时持有观察，转弱时降低仓位",
        ),
        StockAnalysisDimension(
            name="资金行为",
            score=_pct_score(position.daily_pnl_ratio),
            status="成交侧代理",
            evidence=f"当日盈亏 {position.daily_pnl:.2f}，日内涨跌 {position.daily_pnl_ratio:.2f}%",
            action="用量价承接复核资金，不把单日涨跌当作资金流",
        ),
        StockAnalysisDimension(
            name="估值基本面",
            score=50,
            status="待复核",
            evidence=f"所属板块 {holding.sector or '未识别'}，持仓备注 {holding.note or '无'}",
            action="结合财报和估值后再上调基本面权重",
        ),
        StockAnalysisDimension(
            name="消息事件",
            score=48,
            status="待验证",
            evidence=f"持仓主题 {holding.sector or '未识别'} 需继续核对新闻、公告和舆情",
            action="无明确事件催化时不把消息面作为加仓理由",
        ),
        StockAnalysisDimension(
            name="风险约束",
            score=_risk_score(position.risk_level),
            status=position.risk_level,
            evidence=(
                f"仓位 {position.weight:.1%}，"
                f"浮动盈亏 {position.pnl:.2f}（{position.pnl_ratio:.2f}%）"
            ),
            action="按成本、仓位和失效线先控制回撤",
        ),
    ]
    decision = StockAnalysisDecision(
        verdict=_verdict_from_position(position),
        core_conflicts=[
            f"趋势 {position.trend} 与风险 {position.risk_level}",
            f"成本收益率 {position.pnl_ratio:.2f}% 与仓位 {position.weight:.1%}",
        ],
        today_action=_action_from_position(position),
        forbidden_action="不因持仓成本或亏损摊低而替代股票自身证据。",
        strengthen_condition="站稳短期均线、放量承接且所属板块继续强于市场",
        exit_condition="跌破成本风控线或短期趋势失效时降低仓位",
        data_reliability="部分可信",
    )
    return StockAnalysisReport(
        code=holding.code,
        name=holding.name,
        latest_date=trade_date,
        latest_close=position.latest_price,
        pct_change=position.daily_pnl_ratio,
        trend=position.trend,
        risk_level=position.risk_level,
        observations=position.observations,
        watch_points=[
            "复核板块主题是否仍在市场主线",
            "复核新闻公告是否存在新增催化或风险",
            "复核成本线、止损线和仓位暴露",
        ],
        dimensions=dimensions,
        decision=decision,
    )


def _stock_report_from_candidate(
    candidate: CandidateStockAnalysis, *, trade_date: str
) -> StockAnalysisReport:
    risk_text = "高" if candidate.pct_change > 6 or candidate.score < 50 else "中"
    dimensions = [
        StockAnalysisDimension(
            name="技术趋势",
            score=_pct_score(candidate.pct_change),
            status="趋势候选",
            evidence=f"最新涨跌 {candidate.pct_change:.2f}%，观察分 {candidate.score}/100",
            action="只在回踩承接或突破后不回落时继续跟踪",
        ),
        StockAnalysisDimension(
            name="资金行为",
            score=max(35, min(75, candidate.score - 8)),
            status="成交侧代理",
            evidence="；".join(candidate.reasons[:2]) or "候选池未给出资金证据",
            action="用成交额、换手和主力资金二次确认",
        ),
        StockAnalysisDimension(
            name="估值基本面",
            score=50,
            status="待复核",
            evidence=f"所属板块 {candidate.sector}，需继续核对估值和财报质量",
            action="财务质量未确认前不放大仓位",
        ),
        StockAnalysisDimension(
            name="消息事件",
            score=52 if candidate.reasons else 45,
            status="待验证",
            evidence="；".join(candidate.reasons[:3]) or "暂无明确事件线索",
            action="将板块主题、新闻公告和舆情放入次日复核",
        ),
        StockAnalysisDimension(
            name="风险约束",
            score=40 if candidate.pct_change > 6 else 55,
            status=risk_text,
            evidence="；".join(candidate.risks[:2]) or "候选风险待复核",
            action="高开或连续放量冲高时不追，等承接",
        ),
    ]
    decision = StockAnalysisDecision(
        verdict="谨慎进攻" if candidate.score >= 70 and candidate.pct_change <= 6 else "观察",
        core_conflicts=[
            f"候选观察分 {candidate.score}/100",
            f"板块 {candidate.sector} 与短线涨跌 {candidate.pct_change:.2f}%",
        ],
        today_action="加入观察池；只在板块延续、量价承接和消息面确认后考虑。",
        forbidden_action="不因候选排名靠前就追高买入。",
        strengthen_condition="板块延续、个股回踩不破且资金继续承接",
        exit_condition="跌回触发位或板块主线退潮时移出机会清单",
        data_reliability="部分可信" if candidate.price_reliable else "低可信",
    )
    return StockAnalysisReport(
        code=candidate.code,
        name=candidate.name,
        latest_date=trade_date,
        latest_close=candidate.latest_close,
        pct_change=candidate.pct_change,
        trend="上升趋势" if candidate.score >= 65 else "震荡观察",
        risk_level=risk_text,
        observations=candidate.reasons,
        watch_points=candidate.watch_conditions,
        dimensions=dimensions,
        decision=decision,
    )


def _sector_method_chain_lines(sectors: list[SectorAnalysis]) -> list[str]:
    if not sectors:
        return ["- 未读取到板块数据，本次不生成板块方法链。"]
    lines: list[str] = []
    for sector in sectors:
        available = ["涨跌幅", "扩散率", "成交变化"]
        if sector.limit_up_count:
            available.append("涨停情绪")
        if "资金" in sector.fund_status and "不足" not in sector.fund_status:
            available.append("资金")
        missing = []
        if "资金" not in sector.fund_status or "不足" in sector.fund_status:
            missing.append("真实资金明细")
        if sector.limit_up_count == 0:
            missing.append("涨停梯队")
        bull = (
            f"强势证据：涨跌 {sector.pct_chg:.2f}%，扩散 {sector.advancing_ratio:.0%}，"
            f"热度 {sector.heat_score}/100，{sector.continuity}"
        )
        bear = f"约束证据：{sector.risk}；{sector.rotation_status}；{sector.fund_status}"
        lines.append(
            f"- {sector.name}：板块方法链：daily_stock_analysis 上下文包："
            f"可用 {'、'.join(available)}；缺口 {'、'.join(missing) if missing else '无'}"
        )
        lines.append(
            "  - daily_stock_analysis 信号归因：涨跌/扩散/成交/涨停综合解释板块强弱，"
            "不只按单日涨幅排序。"
        )
        lines.append(
            f"  - TradingAgents 板块审议：板块分析师团队：技术/资金/情绪/风险；"
            f"多空审议：{bull}；{bear}"
        )
        lines.append(
            f"  - 组合经理最终意见：{sector.name} 仅在扩散率、成交变化和代表股承接"
            "继续同步时维持主线观察。"
        )
    return lines


def _trend_score(trend: str) -> int:
    if "上升" in trend:
        return 68
    if "下降" in trend:
        return 35
    return 52


def _risk_score(risk: str) -> int:
    if risk == "高":
        return 35
    if risk == "中":
        return 50
    return 62


def _pct_score(pct: float) -> int:
    if pct >= 6:
        return 72
    if pct >= 3:
        return 64
    if pct >= 0:
        return 55
    if pct >= -3:
        return 45
    return 34


def _verdict_from_position(position: PositionAnalysis) -> str:
    if position.risk_level == "高" or "下降" in position.trend:
        return "降风险"
    if position.trend == "上升趋势" and position.pnl_ratio >= 0:
        return "持有观察"
    return "防守观察"


def _action_from_position(position: PositionAnalysis) -> str:
    if position.risk_level == "高" or "下降" in position.trend:
        return "不加仓；若反弹但量价不能修复，先降低风险。"
    if position.pnl_ratio < 0:
        return "不补亏；等待重新站回短期均线并有资金承接。"
    return "持有观察；不追高，跌破短期趋势或成本风控线再处理。"


def render_news_markdown(report: NewsSentimentReport) -> str:
    lines = [
        f"# 新闻舆情摘要（{report.trade_date}）",
        "",
        DISCLAIMER,
        "",
        "## 舆情概览",
        f"- 结论：{report.summary}",
        (
            f"- 正面：{report.positive_count} 条；"
            f"负面：{report.negative_count} 条；中性：{report.neutral_count} 条"
        ),
        "",
        "## 重点消息",
    ]
    for item in report.items:
        sentiment_label = {
            "positive": "正面",
            "negative": "负面",
            "neutral": "中性",
        }.get(item.sentiment, "中性")
        url_part = f"（{item.url}）" if item.url else ""
        lines.append(
            f"- [{sentiment_label}] {item.title}｜{item.source}｜"
            f"{item.date}{url_part}：{item.summary}"
        )
    lines.extend(["", "## 舆情风险"])
    lines.extend(f"- {item}" for item in report.risks)
    return "\n".join(lines) + "\n"


def _strip_title_and_disclaimer(markdown: str, title: str) -> str:
    text = markdown.replace(title + "\n\n", "", 1)
    text = text.replace(DISCLAIMER + "\n\n", "", 1)
    return text.strip()


def _daily_one_liner(
    market: MarketSnapshot,
    portfolio: PortfolioAnalysisReport | None,
    sectors: SectorAnalysisReport | None,
) -> str:
    sector_part = (
        f"，主线板块为{sectors.market_mainline[0]}" if sectors and sectors.market_mainline else ""
    )
    portfolio_part = ""
    if portfolio is not None:
        portfolio_part = f"，组合健康度 {portfolio.health_score}/100"
    return f"{market.summary}{sector_part}{portfolio_part}。"


def _attention_items(
    market: MarketSnapshot,
    portfolio: PortfolioAnalysisReport | None,
    sectors: SectorAnalysisReport | None,
    candidates: CandidatePoolReport | None,
) -> list[str]:
    items = [market.tomorrow_watch[0] if market.tomorrow_watch else "观察指数和成交额是否同步确认"]
    if sectors is not None and sectors.market_mainline:
        items.append(f"跟踪主线板块 {sectors.market_mainline[0]} 的持续性和高位分歧")
    if portfolio is not None and portfolio.risk_alerts:
        items.append(portfolio.risk_alerts[0])
    if candidates is not None and candidates.candidates:
        top = candidates.candidates[0]
        items.append(f"候选股票池排名第一的 {top.name} 仍需满足开盘承接条件后再进入跟踪")
    return items[:3]


def _portfolio_risk_top3(portfolio: PortfolioAnalysisReport | None) -> list[str]:
    if portfolio is None:
        return ["未提供持仓文件，本次日报不包含持仓风险排序"]
    risks = list(portfolio.risk_alerts)
    for position in portfolio.positions[:3]:
        position_summary = (
            f"{position.holding.name}：仓位 {position.weight:.1%}，"
            f"趋势 {position.trend}，风险 {position.risk_level}"
        )
        risks.append(position_summary)
    return risks[:3]


def _candidate_heading(report: CandidatePoolReport) -> str:
    return f"# 候选股票池 Top {len(report.candidates)}（{report.trade_date}）\n\n"


def render_daily_markdown(
    market: MarketSnapshot,
    portfolio: PortfolioAnalysisReport | None = None,
    stocks: list[StockAnalysisReport] | None = None,
    sectors: SectorAnalysisReport | None = None,
    candidates: CandidatePoolReport | None = None,
    news: NewsSentimentReport | None = None,
) -> str:
    attention = _attention_items(market, portfolio, sectors, candidates)
    portfolio_risks = _portfolio_risk_top3(portfolio)
    lines = [
        f"# StockTS 每日复盘（{market.trade_date}）",
        "",
        DISCLAIMER,
        "",
        "## 今日一句话",
        f"- {_daily_one_liner(market, portfolio, sectors)}",
        "",
        "## 最需要关注的 3 件事",
    ]
    lines.extend(f"{index}. {item}" for index, item in enumerate(attention, start=1))
    lines.extend(["", "## 持仓风险 Top 3"])
    lines.extend(f"{index}. {item}" for index, item in enumerate(portfolio_risks, start=1))
    lines.extend(
        [
            "",
            "## 每日大盘分析",
            "",
            _strip_title_and_disclaimer(
                render_market_markdown(market),
                f"# 每日大盘分析（{market.trade_date}）",
            ),
        ]
    )
    if sectors is not None:
        lines.extend(
            [
                "",
                "## 每日板块情况",
                "",
                _strip_title_and_disclaimer(
                    render_sector_markdown(sectors),
                    f"# 每日板块情况（{sectors.trade_date}）",
                ),
            ]
        )
    if portfolio is not None:
        lines.extend(
            [
                "",
                "## 每日持仓分析",
                "",
                _strip_title_and_disclaimer(
                    render_portfolio_markdown(portfolio),
                    f"# 每日持仓分析（{portfolio.trade_date}）",
                ),
            ]
        )
    if candidates is not None:
        lines.extend(
            [
                "",
                f"## 候选股票池 Top {len(candidates.candidates)}",
                "",
                _strip_title_and_disclaimer(
                    render_candidate_pool_markdown(candidates),
                    _candidate_heading(candidates).strip(),
                ),
            ]
        )
    if news is not None:
        lines.extend(
            [
                "",
                "## 新闻舆情摘要",
                "",
                _strip_title_and_disclaimer(
                    render_news_markdown(news),
                    f"# 新闻舆情摘要（{news.trade_date}）",
                ),
            ]
        )
    if stocks:
        lines.extend(["", "## 个股分析"])
        for stock in stocks:
            lines.extend(["", render_stock_markdown(stock).strip()])
    lines.extend(["", "---", DISCLAIMER])
    return "\n".join(lines).strip() + "\n"
