from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

from .indicators import bollinger_bands, macd, pct_change, rsi, sma, volatility
from .models import (
    CandidatePoolReport,
    CandidateStockAnalysis,
    CandidateStockRawData,
    Holding,
    MarketDimension,
    MarketRawData,
    MarketSnapshot,
    NewsItem,
    PortfolioAnalysisReport,
    PositionAnalysis,
    SectorAnalysis,
    SectorAnalysisReport,
    SectorRawData,
    StockAnalysisDecision,
    StockAnalysisDimension,
    StockAnalysisReport,
    StockRawData,
)
from .news_intelligence import classify_news_item
from .providers.base import StockDataProvider


def analyze_market(raw: MarketRawData) -> MarketSnapshot:
    total = raw.advancing + raw.declining
    advance_ratio = raw.advancing / total if total else 0.0
    breadth_ratio = raw.advancing / max(raw.declining, 1)
    avg_index_pct = sum(index.pct_chg for index in raw.indices) / max(len(raw.indices), 1)
    limit_balance = raw.limit_up - raw.limit_down * 2

    heat_score = int(50 + avg_index_pct * 12 + (advance_ratio - 0.5) * 70 + limit_balance * 0.12)
    if raw.northbound_net_inflow is not None:
        heat_score += int(max(min(raw.northbound_net_inflow, 80), -80) * 0.12)
    heat_score = max(0, min(100, heat_score))

    if heat_score >= 70 and breadth_ratio >= 1.5:
        summary = "市场偏强，赚钱效应扩散"
        regime = "强势进攻"
    elif heat_score <= 35 or breadth_ratio < 0.75:
        summary = "市场偏弱，防守优先"
        regime = "防守退潮"
    else:
        summary = "市场震荡，结构性机会为主"
        regime = "震荡轮动"

    dimensions = _market_dimensions(
        raw=raw,
        heat_score=heat_score,
        breadth_ratio=breadth_ratio,
        avg_index_pct=avg_index_pct,
    )

    opportunities = []
    for name, pct in raw.top_sectors[:3]:
        if pct > 0:
            opportunities.append(f"{name} 板块相对强势，日内涨幅 {pct:.2f}%")
    if raw.limit_up >= 60:
        opportunities.append(f"涨停家数 {raw.limit_up}，短线情绪活跃")

    risks = []
    if raw.limit_down >= 20:
        risks.append(f"跌停家数 {raw.limit_down}，注意高位股回撤")
    if raw.northbound_net_inflow is not None and raw.northbound_net_inflow < -30:
        risks.append(f"北向资金净流出 {raw.northbound_net_inflow:.1f} 亿元")
    if not risks:
        risks.append("未见极端风险信号，但仍需控制仓位与回撤")

    tomorrow_watch = [
        "观察成交额是否继续放大，确认指数反弹或突破的有效性",
        "观察强势板块是否出现第二天延续，而不是一日游轮动",
        "观察跌停家数和高位股反馈，判断短线情绪是否退潮",
    ]
    if raw.northbound_net_inflow is not None:
        tomorrow_watch.append("观察北向资金是否延续净流入，辅助判断外资风险偏好")

    return MarketSnapshot(
        trade_date=raw.trade_date,
        heat_score=heat_score,
        breadth_ratio=round(breadth_ratio, 2),
        summary=summary,
        regime=regime,
        indices=raw.indices,
        top_sectors=raw.top_sectors,
        dimensions=dimensions,
        opportunities=opportunities or ["暂无明确主线，等待量价确认"],
        risks=risks,
        tomorrow_watch=tomorrow_watch,
        northbound_net_inflow=raw.northbound_net_inflow,
        limit_up_count=raw.limit_up,
        limit_down_count=raw.limit_down,
        advancing_count=raw.advancing,
        declining_count=raw.declining,
        unchanged_count=raw.unchanged,
        limit_down_details=raw.limit_down_details,
        history=raw.history,
    )


def _market_dimensions(
    raw: MarketRawData,
    heat_score: int,
    breadth_ratio: float,
    avg_index_pct: float,
) -> list[MarketDimension]:
    sector_score = 50
    if raw.top_sectors:
        positive_sectors = sum(1 for _, pct in raw.top_sectors if pct > 0)
        sector_score = min(100, 45 + positive_sectors * 12 + max(raw.top_sectors[0][1], 0) * 4)
    fund_score = 50
    if raw.northbound_net_inflow is not None:
        fund_score = max(0, min(100, int(50 + raw.northbound_net_inflow * 0.7)))
    risk_score = max(0, min(100, int(80 - raw.limit_down * 1.8 + raw.limit_up * 0.25)))

    return [
        MarketDimension(
            "指数趋势",
            _score(avg_index_pct, 0.8, 0.0),
            _status(avg_index_pct, 0.8, 0),
            f"主要指数平均涨跌幅 {avg_index_pct:.2f}%",
        ),
        MarketDimension(
            "市场广度",
            _score(breadth_ratio, 1.5, 0.8),
            _status(breadth_ratio, 1.5, 0.8),
            f"涨跌家数比 {breadth_ratio:.2f}",
        ),
        MarketDimension(
            "短线情绪",
            heat_score,
            _score_status(heat_score),
            f"涨停 {raw.limit_up} 家，跌停 {raw.limit_down} 家",
        ),
        MarketDimension(
            "资金流",
            fund_score,
            _score_status(fund_score),
            _fund_evidence(raw.northbound_net_inflow),
        ),
        MarketDimension(
            "板块强度",
            int(sector_score),
            _score_status(int(sector_score)),
            _sector_evidence(raw.top_sectors),
        ),
        MarketDimension(
            "风险状态",
            risk_score,
            _score_status(risk_score),
            f"跌停家数 {raw.limit_down}，极端亏钱效应{'偏低' if raw.limit_down < 15 else '需警惕'}",
        ),
    ]


def _score(value: float, strong: float, weak: float) -> int:
    if value >= strong:
        return 82
    if value <= weak:
        return 38
    return 60


def _status(value: float, strong: float, weak: float) -> str:
    if value >= strong:
        return "强"
    if value <= weak:
        return "弱"
    return "中性"


def _score_status(score: int) -> str:
    if score >= 70:
        return "强"
    if score <= 40:
        return "弱"
    return "中性"


def _fund_evidence(northbound_net_inflow: float | None) -> str:
    if northbound_net_inflow is None:
        return "暂无资金流样例字段，等待真实数据源补充"
    direction = "净流入" if northbound_net_inflow >= 0 else "净流出"
    return f"北向资金{direction} {abs(northbound_net_inflow):.1f} 亿元"


def _sector_evidence(top_sectors: list[tuple[str, float]]) -> str:
    if not top_sectors:
        return "暂无板块强弱数据"
    name, pct = top_sectors[0]
    return f"最强方向 {name}，涨幅 {pct:.2f}%"


def analyze_stock(raw: StockRawData) -> StockAnalysisReport:
    raw = replace(raw, news_items=_normalize_news_items(raw.news_items))
    if not raw.bars:
        raise ValueError("stock bars cannot be empty")

    closes = [bar.close for bar in raw.bars]
    volumes = [bar.volume for bar in raw.bars]
    latest = raw.bars[-1]
    previous_close = raw.bars[-2].close if len(raw.bars) >= 2 else latest.close
    change = pct_change(previous_close, latest.close)
    ma3 = sma(closes, min(3, len(closes)))
    ma5 = sma(closes, min(5, len(closes)))
    recent_volatility = volatility(closes[-10:])

    if ma3 is not None and ma5 is not None and latest.close >= ma3 >= ma5 and change >= 0:
        trend = "上升趋势"
    elif ma3 is not None and latest.close < ma3 and change < 0:
        trend = "下降趋势"
    else:
        trend = "震荡整理"

    observations = [
        f"最新收盘 {latest.close:.2f}，较前一交易日 {change:.2f}%",
        f"短期趋势判断：{trend}",
    ]
    if len(volumes) >= 3:
        avg_recent_volume = sum(volumes[-3:]) / 3
        avg_base_volume = sum(volumes) / len(volumes)
        if avg_recent_volume > avg_base_volume * 1.2:
            observations.append("量能明显放大，需结合价格位置判断持续性")
        elif avg_recent_volume < avg_base_volume * 0.8:
            observations.append("量能收缩，趋势延续需要更多成交配合")
        else:
            observations.append("量能维持均衡，等待方向选择")
    if raw.fund_flow is not None:
        direction = "净流入" if raw.fund_flow >= 0 else "净流出"
        observations.append(f"主力资金{direction} {abs(raw.fund_flow):.2f} 亿元")

    if len(closes) >= 20:
        macd_values = macd(closes)
        latest_macd = macd_values["macd"][-1]
        latest_dif = macd_values["dif"][-1]
        momentum_status = "偏强" if latest_macd >= 0 else "偏弱"
        observations.append(
            f"MACD：DIF {latest_dif:.3f}，柱值 {latest_macd:.3f}，动能{momentum_status}"
        )
        rsi_values = rsi(closes, 14)
        latest_rsi = rsi_values[-1]
        if latest_rsi is not None:
            if latest_rsi >= 70:
                rsi_status = "偏热"
            elif latest_rsi <= 30:
                rsi_status = "偏弱或超卖"
            else:
                rsi_status = "中性"
            observations.append(f"RSI：{latest_rsi:.1f}，强弱状态 {rsi_status}")
        bands = bollinger_bands(closes, 20)
        upper = bands["upper"][-1]
        middle = bands["middle"][-1]
        lower = bands["lower"][-1]
        if upper is not None and middle is not None and lower is not None:
            if latest.close >= upper:
                boll_status = "接近上轨，注意追高风险"
            elif latest.close <= lower:
                boll_status = "接近下轨，关注止跌确认"
            elif latest.close >= middle:
                boll_status = "位于中轨上方，结构偏强"
            else:
                boll_status = "位于中轨下方，结构偏弱"
            observations.append(
                f"BOLL：上轨 {upper:.2f}，中轨 {middle:.2f}，下轨 {lower:.2f}，{boll_status}"
            )

    risk_score = 0
    if recent_volatility >= 8:
        risk_score += 2
    elif recent_volatility >= 4:
        risk_score += 1
    if change <= -5:
        risk_score += 2
    if raw.pe_ttm is not None and raw.pe_ttm > 80:
        risk_score += 1
    risk_level = "高" if risk_score >= 3 else "中" if risk_score >= 1 else "低"

    watch_points = [
        "观察 5 日均线得失和成交量是否同步放大",
        "结合大盘热度决定仓位，不单独依据单一指标操作",
    ]
    if raw.pe_ttm is not None:
        watch_points.append(f"估值 PE(TTM) {raw.pe_ttm:.2f}，需与行业分位比较")

    dimensions = _stock_professional_dimensions(
        raw=raw,
        trend=trend,
        risk_level=risk_level,
        change=change,
        recent_volatility=recent_volatility,
        latest_close=latest.close,
        ma5=ma5,
        observations=observations,
    )
    decision = _stock_decision_summary(
        raw=raw,
        dimensions=dimensions,
        trend=trend,
        risk_level=risk_level,
        latest_close=latest.close,
        ma5=ma5,
    )

    return StockAnalysisReport(
        code=raw.code,
        name=raw.name,
        latest_date=latest.date,
        latest_close=latest.close,
        pct_change=round(change, 2),
        trend=trend,
        risk_level=risk_level,
        observations=observations,
        watch_points=watch_points,
        fund_flow=raw.fund_flow,
        pe_ttm=raw.pe_ttm,
        dimensions=dimensions,
        decision=decision,
    )


def _stock_decision_summary(
    *,
    raw: StockRawData,
    dimensions: list[StockAnalysisDimension],
    trend: str,
    risk_level: str,
    latest_close: float,
    ma5: float | None,
) -> StockAnalysisDecision:
    by_name = {item.name: item for item in dimensions}
    trade_score = by_name.get("交易计划").score if by_name.get("交易计划") else 50
    fund_score = by_name.get("资金行为").score if by_name.get("资金行为") else 45
    event_score = by_name.get("消息事件").score if by_name.get("消息事件") else 45
    valuation_score = by_name.get("估值基本面").score if by_name.get("估值基本面") else 45
    priority = {
        "资金行为": 0,
        "估值基本面": 1,
        "消息事件": 2,
        "风险约束": 3,
        "技术趋势": 4,
        "量价结构": 5,
        "统计位置": 6,
        "交易计划": 7,
    }
    low_dimensions = sorted(
        [item for item in dimensions if item.score <= 45],
        key=lambda item: priority.get(item.name, 99),
    )
    conflicts = [f"{item.name}偏弱：{item.evidence}" for item in low_dimensions[:3]]
    if not conflicts:
        conflicts = [_positive_conflict_summary(dimensions)]

    if risk_level == "高" or trade_score <= 40:
        verdict = "降风险"
        today_action = "不加仓；反弹先处理风险，等趋势和资金修复后再看。"
    elif trend == "下降趋势" or fund_score < 45:
        verdict = "防守观察"
        today_action = "不加仓；先等重新站回短期均线并出现资金回流。"
    elif trade_score >= 65 and trend == "上升趋势":
        verdict = "谨慎进攻"
        today_action = "只接受回踩承接或放量突破，不追高。"
    else:
        verdict = "观察"
        today_action = "观察为主；等技术、资金、事件至少两项确认。"

    forbidden_action = _stock_forbidden_action(
        verdict=verdict,
        risk_level=risk_level,
        fund_score=fund_score,
        valuation_score=valuation_score,
    )
    strengthen_condition = _stock_strengthen_condition(ma5, fund_score, event_score)
    exit_condition = _stock_exit_condition(latest_close, ma5, risk_level)
    data_reliability = _stock_data_reliability(raw, fund_score, event_score)
    return StockAnalysisDecision(
        verdict=verdict,
        core_conflicts=conflicts,
        today_action=today_action,
        forbidden_action=forbidden_action,
        strengthen_condition=strengthen_condition,
        exit_condition=exit_condition,
        data_reliability=data_reliability,
    )


def _positive_conflict_summary(dimensions: list[StockAnalysisDimension]) -> str:
    strong = [item.name for item in dimensions if item.score >= 65]
    if strong:
        return f"优势集中在{'、'.join(strong[:3])}，仍需避免追高。"
    return "各维度没有明显极端信号，等待价格选择方向。"


def _stock_forbidden_action(
    *,
    verdict: str,
    risk_level: str,
    fund_score: int,
    valuation_score: int,
) -> str:
    if verdict in {"降风险", "防守观察"}:
        return "不能补仓摊低；不能因为跌多了就买；不能在资金未回流前加仓。"
    if valuation_score < 45:
        return "不能把高估值当安全垫；不能追高放大仓位。"
    if fund_score < 45:
        return "不能忽略资金流出；不能只看技术形态买入。"
    if risk_level == "中":
        return "不能一次性加满；不能无止损持有。"
    return "不能追高；不能脱离止损线和板块环境单独交易。"


def _stock_strengthen_condition(ma5: float | None, fund_score: int, event_score: int) -> str:
    ma_text = f"站回并稳住 MA5 {ma5:.2f}" if ma5 is not None else "站回短期均线"
    conditions = [ma_text, "放量不跌回开盘价"]
    if fund_score < 50:
        conditions.append("资金由流出转为流入")
    if event_score < 50:
        conditions.append("新闻/公告风险补齐并未见负面")
    return "；".join(conditions)


def _stock_exit_condition(latest_close: float, ma5: float | None, risk_level: str) -> str:
    line = min(latest_close * 0.95, ma5 * 0.98) if ma5 is not None else latest_close * 0.95
    if risk_level == "高":
        return f"跌破 {line:.2f} 或继续放量下跌，优先降风险。"
    return f"跌破 {line:.2f} 且 30 分钟不能收回，降低观察优先级。"


def _stock_data_reliability(raw: StockRawData, fund_score: int, event_score: int) -> str:
    missing = 0
    if not raw.bars:
        missing += 1
    if raw.fund_flow is None and not raw.fund_flow_detail:
        missing += 1
    if not raw.news_items:
        missing += 1
    if raw.pe_ttm is None and not raw.valuation:
        missing += 1
    if fund_score < 45 or event_score < 45:
        missing += 1
    if missing >= 3:
        return "低可信"
    if missing >= 1:
        return "部分可信"
    return "较可信"


def _stock_professional_dimensions(
    *,
    raw: StockRawData,
    trend: str,
    risk_level: str,
    change: float,
    recent_volatility: float,
    latest_close: float,
    ma5: float | None,
    observations: list[str],
) -> list[StockAnalysisDimension]:
    volume_score, volume_evidence, volume_action = _stock_volume_dimension(raw)
    fund_score, fund_evidence, fund_action = _stock_fund_dimension(raw)
    valuation_score, valuation_evidence, valuation_action = _stock_valuation_dimension(raw)
    event_score, event_evidence, event_action = _stock_event_dimension(raw)
    stat_score, stat_evidence, stat_action = _stock_stat_dimension(
        change=change,
        recent_volatility=recent_volatility,
        observations=observations,
    )
    risk_score, risk_evidence, risk_action = _stock_risk_dimension(
        risk_level=risk_level,
        recent_volatility=recent_volatility,
        change=change,
    )
    trade_score, trade_evidence, trade_action = _stock_trade_dimension(
        trend=trend,
        risk_level=risk_level,
        latest_close=latest_close,
        ma5=ma5,
        fund_score=fund_score,
        event_score=event_score,
    )
    trend_score = _stock_trend_score(trend, change)
    return [
        StockAnalysisDimension(
            "技术趋势",
            trend_score,
            _score_status(trend_score),
            f"{trend}，单日涨跌 {change:.2f}%",
            _stock_trend_action(trend, change),
        ),
        StockAnalysisDimension(
            "量价结构",
            volume_score,
            _score_status(volume_score),
            volume_evidence,
            volume_action,
        ),
        StockAnalysisDimension(
            "资金行为",
            fund_score,
            _score_status(fund_score),
            fund_evidence,
            fund_action,
        ),
        StockAnalysisDimension(
            "估值基本面",
            valuation_score,
            _score_status(valuation_score),
            valuation_evidence,
            valuation_action,
        ),
        StockAnalysisDimension(
            "消息事件",
            event_score,
            _score_status(event_score),
            event_evidence,
            event_action,
        ),
        StockAnalysisDimension(
            "统计位置",
            stat_score,
            _score_status(stat_score),
            stat_evidence,
            stat_action,
        ),
        StockAnalysisDimension(
            "风险约束",
            risk_score,
            _score_status(risk_score),
            risk_evidence,
            risk_action,
        ),
        StockAnalysisDimension(
            "交易计划",
            trade_score,
            _score_status(trade_score),
            trade_evidence,
            trade_action,
        ),
    ]


def _stock_trend_score(trend: str, change: float) -> int:
    if trend == "上升趋势":
        return 78 if change >= 0 else 65
    if trend == "下降趋势":
        return 30 if change < 0 else 42
    return 55


def _stock_trend_action(trend: str, change: float) -> str:
    if trend == "上升趋势" and change >= 0:
        return "持有观察；只在回踩不破短均线时考虑低吸"
    if trend == "下降趋势":
        return "不加仓；先等重新站回短期均线"
    return "等待方向选择；不因单日波动追涨杀跌"


def _stock_volume_dimension(raw: StockRawData) -> tuple[int, str, str]:
    volumes = [bar.volume for bar in raw.bars if bar.volume > 0]
    if len(volumes) < 5:
        return 50, "成交量样本不足，不能判断量价配合", "只观察，不把量能作为买点依据"
    recent = sum(volumes[-3:]) / 3
    base = sum(volumes) / len(volumes)
    ratio = recent / base if base else 0.0
    latest = raw.bars[-1]
    prev = raw.bars[-2] if len(raw.bars) >= 2 else latest
    price_up = latest.close >= prev.close
    if ratio >= 1.3 and price_up:
        return 76, f"近3日量能为均量 {ratio:.2f} 倍，价格同步走强", "看承接；高开过多不追"
    if ratio >= 1.3 and not price_up:
        return 35, f"近3日量能为均量 {ratio:.2f} 倍，但价格走弱", "放量下跌先降风险"
    if ratio <= 0.75:
        return 45, f"近3日量能为均量 {ratio:.2f} 倍，成交不足", "缩量反弹不追，等放量确认"
    return 58, f"近3日量能为均量 {ratio:.2f} 倍，量价中性", "等待放量方向选择"


def _stock_fund_dimension(raw: StockRawData) -> tuple[int, str, str]:
    value = raw.fund_flow
    if value is None:
        value = _optional_float(raw.fund_flow_detail.get("main_net_inflow"))
    if value is None:
        volume_score, volume_evidence, volume_action = _stock_volume_dimension(raw)
        if "样本不足" not in volume_evidence:
            return (
                volume_score,
                f"成交侧替代观察：{volume_evidence}",
                f"{volume_action}；不把成交侧替代值当作主力净流",
            )
        return 45, "资金流未接入，不能确认主力态度", "资金面不作为买入理由"
    direction = "净流入" if value >= 0 else "净流出"
    score = max(15, min(90, int(55 + value * 8)))
    action = "资金配合，可观察回踩承接" if value > 0 else "不加仓；先等资金回流"
    return score, f"主力资金{direction} {abs(value):.2f} 亿元", action


def _stock_valuation_dimension(raw: StockRawData) -> tuple[int, str, str]:
    pe = raw.pe_ttm
    pb = _optional_float(raw.valuation.get("pb"))
    if pe is None and pb is None:
        return 45, "估值/基本面数据未接入", "不把基本面当作买入依据"
    parts = []
    if pe is not None:
        parts.append(f"PE(TTM) {pe:.2f}")
    if pb is not None:
        parts.append(f"PB {pb:.2f}")
    if pe is not None and pe > 80:
        return 32, "，".join(parts) + "，估值偏高", "高估值票只做趋势交易，跌破趋势先降风险"
    if pe is not None and pe > 0 and pe <= 25:
        return 70, "，".join(parts) + "，估值相对可控", "可结合行业景气和资金确认"
    return 55, "，".join(parts) + "，估值需结合行业分位", "等待行业对比，不单独下结论"


def _normalize_news_items(items: list[NewsItem]) -> list[NewsItem]:
    normalized: list[NewsItem] = []
    for item in items:
        if item.sentiment and item.sentiment != "neutral":
            normalized.append(item)
            continue
        classification = classify_news_item(item.title, item.summary)
        normalized.append(replace(item, sentiment=classification.sentiment))
    return normalized


def _stock_event_dimension(raw: StockRawData) -> tuple[int, str, str]:
    news_count = len(raw.news_items)
    if news_count == 0:
        return 45, "新闻/公告事件未接入或为空", "消息催化不可信，按价格和风险线执行"
    negative_items = [
        item for item in raw.news_items if getattr(item, "sentiment", "") == "negative"
    ]
    positive_items = [
        item for item in raw.news_items if getattr(item, "sentiment", "") == "positive"
    ]
    negative = len(negative_items)
    positive = len(positive_items)
    score = max(20, min(85, 55 + positive * 8 - negative * 12))
    evidence_parts = [f"新闻 {news_count} 条，正面 {positive}，负面 {negative}"]
    if positive_items:
        evidence_parts.append(
            "催化：" + "；".join(_news_title(item) for item in positive_items[:2])
        )
    if negative_items:
        evidence_parts.append(
            "风险：" + "；".join(_news_title(item) for item in negative_items[:2])
        )
    if negative:
        action = "先复核负面消息，未排除前不加仓"
    elif positive:
        action = "有催化但需看盘中承接，避免利好兑现"
    else:
        action = "消息中性，回到技术和资金确认"
    return score, "；".join(evidence_parts), action


def _news_title(item: object) -> str:
    title = str(getattr(item, "title", "") or "").strip()
    source = str(getattr(item, "source", "") or "").strip()
    return f"{title}（{source}）" if title and source else title or source or "未命名消息"


def _stock_stat_dimension(
    *,
    change: float,
    recent_volatility: float,
    observations: list[str],
) -> tuple[int, str, str]:
    rsi_text = next((item for item in observations if item.startswith("RSI")), "")
    score = 60
    if recent_volatility >= 8:
        score -= 20
    elif recent_volatility >= 4:
        score -= 10
    if change > 5:
        score -= 8
    if change < -5:
        score -= 12
    evidence = f"近10日波动 {recent_volatility:.2f}%"
    if rsi_text:
        evidence += f"，{rsi_text}"
    action = "波动高时降低仓位" if recent_volatility >= 4 else "统计风险可控，继续看趋势确认"
    return max(10, min(90, score)), evidence, action


def _stock_risk_dimension(
    *,
    risk_level: str,
    recent_volatility: float,
    change: float,
) -> tuple[int, str, str]:
    mapping = {"低": 75, "中": 55, "高": 30}
    score = mapping.get(risk_level, 50)
    evidence = f"风险等级 {risk_level}，波动 {recent_volatility:.2f}%"
    if change <= -5:
        evidence += f"，单日下跌 {abs(change):.2f}%"
    action = "严格按失效线执行，不补仓摊低" if risk_level == "高" else "保留仓位纪律"
    return score, evidence, action


def _stock_trade_dimension(
    *,
    trend: str,
    risk_level: str,
    latest_close: float,
    ma5: float | None,
    fund_score: int,
    event_score: int,
) -> tuple[int, str, str]:
    score = 50
    if trend == "上升趋势":
        score += 15
    if risk_level == "高":
        score -= 18
    if fund_score < 45:
        score -= 10
    if event_score < 45:
        score -= 8
    ma_text = f"MA5 {ma5:.2f}" if ma5 is not None else "MA5 缺失"
    evidence = f"现价 {latest_close:.2f}，{ma_text}，资金分 {fund_score}，事件分 {event_score}"
    if score >= 65:
        action = "只接受回踩承接或放量突破，不追高"
    elif score <= 40:
        action = "不加仓；反弹先处理风险"
    else:
        action = "观察为主，等趋势、资金、事件三项至少两项确认"
    return max(10, min(90, score)), evidence, action


def _optional_float(value: object) -> float | None:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def analyze_portfolio(
    holdings: list[Holding],
    provider: StockDataProvider,
    market: MarketSnapshot,
) -> PortfolioAnalysisReport:
    max_workers = min(max(len(holdings), 1), 4)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        raw_stocks = list(
            executor.map(lambda holding: provider.fetch_stock(holding.code), holdings)
        )
    analyzed_stocks = [analyze_stock(raw) for raw in raw_stocks]
    stock_reports = list(zip(holdings, raw_stocks, analyzed_stocks))

    raw_positions = []
    total_market_value = 0.0
    total_cost = 0.0
    daily_pnl = 0.0
    for holding, raw, stock in stock_reports:
        market_value = stock.latest_close * holding.shares
        cost_value = holding.cost_price * holding.shares
        previous_close = raw.bars[-2].close if len(raw.bars) >= 2 else stock.latest_close
        position_daily_pnl = (stock.latest_close - previous_close) * holding.shares
        pnl = market_value - cost_value
        daily_pnl_ratio = (
            (stock.latest_close - previous_close) / previous_close * 100 if previous_close else 0.0
        )
        raw_positions.append(
            (
                holding,
                stock,
                previous_close,
                market_value,
                cost_value,
                position_daily_pnl,
                daily_pnl_ratio,
                pnl,
            )
        )
        total_market_value += market_value
        total_cost += cost_value
        daily_pnl += position_daily_pnl

    positions = []
    for (
        holding,
        stock,
        previous_close,
        market_value,
        cost_value,
        position_daily_pnl,
        daily_pnl_ratio,
        pnl,
    ) in raw_positions:
        weight = market_value / total_market_value if total_market_value else 0.0
        pnl_ratio = pnl / cost_value * 100 if cost_value else 0.0
        observations = [
            f"仓位占比 {weight:.1%}",
            f"当日盈亏 {position_daily_pnl:.2f}，日内涨跌 {daily_pnl_ratio:.2f}%",
            f"浮动盈亏 {pnl:.2f}，收益率 {pnl_ratio:.2f}%",
            f"趋势 {stock.trend}，风险等级 {stock.risk_level}",
        ]
        positions.append(
            PositionAnalysis(
                holding=holding,
                latest_price=stock.latest_close,
                previous_close=previous_close,
                market_value=market_value,
                cost_value=cost_value,
                daily_pnl=position_daily_pnl,
                daily_pnl_ratio=daily_pnl_ratio,
                pnl=pnl,
                pnl_ratio=pnl_ratio,
                weight=weight,
                trend=stock.trend,
                risk_level=stock.risk_level,
                observations=observations,
            )
        )

    positions.sort(key=lambda item: item.market_value, reverse=True)
    top_position_weight = positions[0].weight if positions else 0.0
    total_pnl = total_market_value - total_cost
    total_pnl_ratio = total_pnl / total_cost * 100 if total_cost else 0.0
    sector_weights = _sector_weights(positions)
    risk_alerts = _portfolio_risks(positions, top_position_weight, market)
    market_alignment = _market_alignment(positions, market)
    health_score = _portfolio_health_score(positions, top_position_weight, market, total_pnl_ratio)

    return PortfolioAnalysisReport(
        trade_date=market.trade_date,
        total_market_value=total_market_value,
        total_cost=total_cost,
        total_pnl=total_pnl,
        total_pnl_ratio=total_pnl_ratio,
        daily_pnl=daily_pnl,
        health_score=health_score,
        cash_position_note="当前仅统计持仓，不含现金；仓位比例按持仓市值内部计算",
        top_position_weight=top_position_weight,
        sector_weights=sector_weights,
        positions=positions,
        risk_alerts=risk_alerts,
        market_alignment=market_alignment,
        action_checklist=[
            "检查高仓位个股是否仍满足买入逻辑",
            "检查持仓行业是否贴近当日市场主线",
            "检查弱势股是否跌破关键均线或出现放量下跌",
            "记录今日没有操作的理由，避免情绪化交易",
        ],
    )


def _sector_weights(positions: list[PositionAnalysis]) -> list[tuple[str, float]]:
    total = sum(position.market_value for position in positions)
    if total <= 0:
        return []
    weights: dict[str, float] = {}
    for position in positions:
        sector = position.holding.sector or "未分类"
        weights[sector] = weights.get(sector, 0.0) + position.market_value / total
    return sorted(weights.items(), key=lambda item: item[1], reverse=True)


def _portfolio_risks(
    positions: list[PositionAnalysis],
    top_position_weight: float,
    market: MarketSnapshot,
) -> list[str]:
    risks: list[str] = []
    if not positions:
        return ["当前账号还没有录入持仓，先添加股票、成本价和数量后再做组合风险判断"]
    if top_position_weight >= 0.5:
        risks.append(f"单票仓位过高，第一大持仓占比 {top_position_weight:.1%}")
    weak_positions = [
        item for item in positions if item.risk_level == "高" or item.trend == "下降趋势"
    ]
    if weak_positions:
        names = "、".join(item.holding.name for item in weak_positions[:3])
        risks.append(f"弱势或高风险持仓：{names}")
    if market.heat_score < 45:
        risks.append("大盘环境偏弱，持仓需要降低回撤暴露")
    if not risks:
        risks.append("组合未触发集中度或趋势类硬风险，继续跟踪量价变化")
    return risks


def _market_alignment(
    positions: list[PositionAnalysis],
    market: MarketSnapshot,
) -> list[str]:
    if not positions:
        return ["当前账号还没有录入持仓，暂不判断持仓与市场主线的匹配度"]
    strong_sectors = {name for name, pct in market.top_sectors[:3] if pct > 0}
    holding_sectors = {position.holding.sector for position in positions if position.holding.sector}
    overlap = sorted(strong_sectors & holding_sectors)
    if overlap:
        return [f"持仓覆盖市场主线：{'、'.join(overlap)}"]
    return ["持仓与今日市场主线匹配度不高，注意是否跑输指数或错过强势方向"]


def _portfolio_health_score(
    positions: list[PositionAnalysis],
    top_position_weight: float,
    market: MarketSnapshot,
    total_pnl_ratio: float,
) -> int:
    score = 70
    score += 8 if market.heat_score >= 70 else -8 if market.heat_score < 45 else 0
    score -= 18 if top_position_weight >= 0.5 else 8 if top_position_weight >= 0.35 else 0
    score += 8 if total_pnl_ratio > 5 else -8 if total_pnl_ratio < -5 else 0
    score -= sum(8 for position in positions if position.risk_level == "高")
    return max(0, min(100, score))


def analyze_sectors(
    raw_sectors: list[SectorRawData], trade_date: str = "2026-06-05"
) -> SectorAnalysisReport:
    if not raw_sectors:
        raise ValueError("raw_sectors cannot be empty")

    sectors = []
    for sector in raw_sectors:
        pct_chg = _normalized_sector_pct(sector.pct_chg)
        pct_is_abnormal = pct_chg != sector.pct_chg
        normalized_sector = SectorRawData(
            name=sector.name,
            pct_chg=pct_chg,
            advancing_ratio=sector.advancing_ratio,
            amount_change=sector.amount_change,
            fund_flow=sector.fund_flow,
            consecutive_days=sector.consecutive_days,
            limit_up_count=sector.limit_up_count,
            high_divergence=sector.high_divergence,
        )
        heat_score = _sector_heat_score(normalized_sector)
        if sector.consecutive_days >= 3 and pct_chg > 0:
            continuity = "持续性强"
        elif sector.consecutive_days >= 2 and pct_chg > 0:
            continuity = "持续性观察"
        elif pct_chg > 0:
            continuity = "首日启动"
        else:
            continuity = "退潮或调整"

        fund_status = "资金活跃" if (sector.fund_flow or 0) > 5 else "资金一般"
        if (sector.fund_flow or 0) < 0:
            fund_status = "资金流出"

        if heat_score >= 75 and sector.consecutive_days >= 2:
            rotation_status = "市场主线"
        elif heat_score >= 60:
            rotation_status = "轮动增强"
        elif heat_score <= 40:
            rotation_status = "退潮方向"
        else:
            rotation_status = "中性观察"

        if pct_is_abnormal:
            risk = "样本涨跌异常，需复核真实板块指数"
        elif sector.high_divergence:
            risk = "高位分歧风险"
        elif sector.amount_change < 0 and pct_chg > 0:
            risk = "缩量上涨风险"
        elif pct_chg < 0:
            risk = "板块走弱风险"
        else:
            risk = "风险可控"

        sectors.append(
            SectorAnalysis(
                name=sector.name,
                pct_chg=pct_chg,
                heat_score=heat_score,
                advancing_ratio=sector.advancing_ratio,
                amount_change=sector.amount_change,
                limit_up_count=sector.limit_up_count,
                continuity=continuity,
                fund_status=fund_status,
                rotation_status=rotation_status,
                risk=risk,
            )
        )

    sectors.sort(key=lambda item: item.heat_score, reverse=True)
    market_mainline = [item.name for item in sectors if item.rotation_status == "市场主线"][:3]
    if not market_mainline:
        market_mainline = [item.name for item in sectors[:3]]

    rotation_notes = [
        f"{sectors[0].name} 强度领先，持续性取决于成交额和龙头反馈",
        "关注强势板块是否扩散到低位补涨，避免只追高位一致方向",
        "若昨日强势板块跌出前三，说明轮动加快，仓位需要更分散",
    ]
    risk_notes = [f"{item.name} 存在{item.risk}" for item in sectors if item.risk != "风险可控"][:4]
    if not risk_notes:
        risk_notes = ["板块层面暂无极端风险，但仍需观察高位分歧和缩量上涨风险"]

    return SectorAnalysisReport(
        trade_date=trade_date,
        sectors=sectors,
        market_mainline=market_mainline,
        rotation_notes=rotation_notes,
        risk_notes=risk_notes,
    )


def _normalized_sector_pct(pct_chg: float) -> float:
    # TDX theme snapshots can be built from a small strong-stock sample. Values
    # above one A-share daily limit are not reliable full-sector percentages.
    if abs(pct_chg) > 20.5:
        return 0.0
    return pct_chg


def _sector_heat_score(sector: SectorRawData) -> int:
    score = 50
    score += sector.pct_chg * 7
    score += (sector.advancing_ratio - 0.5) * 55
    score += sector.amount_change * 0.45
    score += (sector.fund_flow or 0) * 0.55
    score += min(sector.consecutive_days, 4) * 4
    score += min(sector.limit_up_count, 15) * 1.1
    if sector.high_divergence:
        score -= 12
    return max(0, min(100, int(score)))


def analyze_candidates(
    universe: list[CandidateStockRawData],
    sectors: SectorAnalysisReport,
    market: MarketSnapshot,
    limit: int = 20,
) -> CandidatePoolReport:
    if limit <= 0:
        raise ValueError("limit must be positive")
    if not universe:
        raise ValueError("candidate universe cannot be empty")

    sector_scores = {sector.name: sector.heat_score for sector in sectors.sectors}
    analyses = [
        _analyze_candidate(raw, sector_scores, sectors.market_mainline, market) for raw in universe
    ]
    analyses.sort(key=lambda item: item.score, reverse=True)
    selected = analyses[:limit]
    title_limit = min(limit, len(selected))
    return CandidatePoolReport(
        trade_date=market.trade_date,
        candidates=selected,
        method_notes=[
            f"按趋势、量价、板块、资金和风险扣分排序，取前 {title_limit} 只",
            "候选只代表次日观察优先级，不代表确定上涨或买入建议",
            "次日需要结合竞价、开盘承接、板块延续和大盘环境二次确认",
        ],
        disclaimer="候选股票池用于研究排序，不构成投资建议，也不承诺短期上涨。",
        price_reliable=all(item.price_reliable for item in selected),
    )


def _analyze_candidate(
    raw: CandidateStockRawData,
    sector_scores: dict[str, int],
    market_mainline: list[str],
    market: MarketSnapshot,
) -> CandidateStockAnalysis:
    closes = [bar.close for bar in raw.bars]
    volumes = [bar.volume for bar in raw.bars]
    latest = raw.bars[-1]
    previous = raw.bars[-2] if len(raw.bars) >= 2 else latest
    pct = pct_change(previous.close, latest.close)
    ma5 = sma(closes, min(5, len(closes))) or latest.close
    ma10 = sma(closes, min(10, len(closes))) or ma5
    ma20 = sma(closes, min(20, len(closes))) or ma10
    trend_score = 18 if latest.close >= ma5 >= ma10 >= ma20 else 10 if latest.close >= ma10 else 4
    volume_score = _candidate_volume_score(volumes)
    sector_score = int(sector_scores.get(raw.sector, 50) * 0.22)
    fund_score = 10 if (raw.fund_flow or 0) > 1 else 6 if (raw.fund_flow or 0) >= 0 else 0
    market_score = 8 if market.heat_score >= 70 else 4 if market.heat_score >= 45 else 0
    risk_deduction = _candidate_risk_deduction(raw, pct, closes)
    score = max(
        0,
        min(
            100,
            42
            + trend_score
            + volume_score
            + sector_score
            + fund_score
            + market_score
            - risk_deduction,
        ),
    )

    reasons = [
        f"{raw.name}所在{raw.sector}强度 {sector_scores.get(raw.sector, 50)}/100",
        f"{raw.name}收盘价位于短期均线{'上方' if latest.close >= ma5 else '下方'}",
    ]
    if raw.sector in market_mainline:
        reasons.append(f"{raw.name}跟随{raw.sector}进入市场主线")
    if (raw.fund_flow or 0) > 0:
        reasons.append(f"{raw.name}样例资金净流入 {raw.fund_flow:.2f} 亿元")
    if volume_score >= 8:
        reasons.append(f"{raw.name}近期量能放大，关注承接")

    risks = []
    if pct > 6:
        risks.append("短线涨幅较大，次日追高风险上升")
    if volatility(closes[-10:]) > 5:
        risks.append("近期波动偏高，需控制回撤")
    if raw.pe_ttm is not None and raw.pe_ttm > 60:
        risks.append(f"估值 PE(TTM) {raw.pe_ttm:.1f} 偏高")
    if not risks:
        risks.append(
            _candidate_default_risk(
                raw,
                pct=pct,
                volume_score=volume_score,
                market_mainline=market_mainline,
            )
        )

    watch_conditions = _candidate_watch_conditions(
        raw,
        pct=pct,
        score=score,
        volume_score=volume_score,
        market_mainline=market_mainline,
    )
    return CandidateStockAnalysis(
        code=raw.code,
        name=raw.name,
        sector=raw.sector,
        score=score,
        latest_close=latest.close,
        pct_change=round(pct, 2),
        reasons=reasons,
        risks=risks,
        watch_conditions=watch_conditions,
        price_reliable=raw.price_reliable,
    )


def _candidate_default_risk(
    raw: CandidateStockRawData,
    *,
    pct: float,
    volume_score: int,
    market_mainline: list[str],
) -> str:
    if pct >= 3:
        return f"{raw.name}短线已有涨幅，避免开盘情绪追高"
    if pct <= -2:
        return f"{raw.name}仍在回落，先确认止跌承接"
    if volume_score >= 8:
        return f"{raw.name}量能放大后需防冲高回落"
    if (raw.fund_flow or 0) > 1:
        return f"{raw.name}资金正流入，但仍要价格确认"
    if raw.sector in market_mainline:
        return f"{raw.sector}主线内部分化，优先比较前排强度"
    return f"{raw.name}暂无硬风险，重点看开盘承接"


def _candidate_watch_conditions(
    raw: CandidateStockRawData,
    *,
    pct: float,
    score: int,
    volume_score: int,
    market_mainline: list[str],
) -> list[str]:
    if pct >= 6:
        first = f"{raw.name}高开超过 3% 不追，等回落承接"
    elif pct >= 2:
        first = f"{raw.name}冲高不能缩量回落，否则降优先级"
    elif pct < 0:
        first = f"{raw.name}先看能否翻红并强于{raw.sector}"
    else:
        first = f"{raw.name}平开附近看量能是否温和放大"

    if volume_score >= 8:
        second = f"{raw.name}放量后 30 分钟不能跌回开盘价"
    elif (raw.fund_flow or 0) > 1:
        second = f"{raw.name}资金净流入方向需要继续维持"
    elif raw.sector in market_mainline:
        second = f"{raw.sector}前排不退潮再看"
    else:
        second = f"{raw.sector}板块排名不能继续下滑"

    if score >= 90:
        third = f"{raw.name}高分候选只接受回踩不破 5 日线"
    elif raw.pe_ttm is not None and raw.pe_ttm > 60:
        third = f"{raw.name}估值偏高时只允许小仓试错"
    elif pct <= -2:
        third = f"{raw.name}跌破前低直接移出今日机会"
    else:
        third = f"{raw.name}必须强于指数才保留"
    return [first, second, third]


def _candidate_volume_score(volumes: list[float]) -> int:
    if len(volumes) < 6:
        return 4
    recent = sum(volumes[-3:]) / 3
    base = sum(volumes[-10:]) / min(10, len(volumes))
    if base == 0:
        return 0
    ratio = recent / base
    if ratio >= 1.3:
        return 12
    if ratio >= 1.1:
        return 8
    if ratio >= 0.8:
        return 5
    return 1


def _candidate_risk_deduction(
    raw: CandidateStockRawData,
    pct: float,
    closes: list[float],
) -> int:
    deduction = 0
    if pct > 7:
        deduction += 10
    if volatility(closes[-10:]) > 8:
        deduction += 10
    if raw.pe_ttm is not None and raw.pe_ttm > 80:
        deduction += 8
    return deduction
