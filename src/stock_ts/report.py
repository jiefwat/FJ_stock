from __future__ import annotations

from .models import (
    CandidatePoolReport,
    MarketSnapshot,
    NewsSentimentReport,
    PortfolioAnalysisReport,
    SectorAnalysisReport,
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
    return "\n".join(lines) + "\n"


def render_stock_markdown(report: StockAnalysisReport) -> str:
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
    return "\n".join(lines) + "\n"


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
