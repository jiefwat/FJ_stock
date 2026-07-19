from __future__ import annotations

from statistics import fmean

from .models import Candidate, MarketSnapshot, SectorPulse, StockProfile


def sector_score(sector: SectorPulse) -> float:
    divergence_penalty = 0.7 if sector.high_divergence else 0.0
    return (
        sector.pct_change
        + (sector.advancing_ratio or 0.0) * 2
        + sector.amount_change * 0.03
        + (sector.consecutive_days or 0) * 0.2
        - divergence_penalty
    )


def _market_state(snapshot: MarketSnapshot) -> tuple[str, str, float]:
    total = snapshot.advancing + snapshot.declining
    breadth = snapshot.advancing / total if total else 0.0
    if breadth >= 0.58 and snapshot.limit_down <= 10:
        regime = "扩张"
    elif breadth <= 0.42 or snapshot.limit_down >= 25:
        regime = "收缩"
    else:
        regime = "轮动"

    if snapshot.limit_down >= 25:
        risk_level = "升高"
    elif snapshot.limit_down >= 10:
        risk_level = "留意"
    else:
        risk_level = "可控"
    return regime, risk_level, breadth


def build_market_analysis(snapshot: MarketSnapshot) -> dict[str, object]:
    regime, risk_level, breadth = _market_state(snapshot)
    index_changes = [quote.pct_change for quote in snapshot.indices]
    index_average = fmean(index_changes) if index_changes else None
    positive_indices = sum(change >= 0 for change in index_changes)
    if not index_changes:
        index_signal = "数据不足"
    elif positive_indices == len(index_changes):
        index_signal = "同步走强"
    elif positive_indices == 0:
        index_signal = "同步走弱"
    else:
        index_signal = "方向分化"

    limit_total = snapshot.limit_up + snapshot.limit_down
    limit_pressure = snapshot.limit_down / limit_total if limit_total else 0.0
    ordered_sectors = sorted(snapshot.sectors, key=sector_score, reverse=True)
    positive_strength = [max(sector_score(sector), 0.0) for sector in ordered_sectors]
    strength_total = sum(positive_strength)
    concentration = positive_strength[0] / strength_total if strength_total else 0.0

    next_checks = {
        "扩张": "观察上涨参与度能否保持在 58% 以上，同时跌停数不超过 10。",
        "轮动": "观察第一主题能否向更多方向扩散，并确认跌停压力没有升高。",
        "收缩": "等待跌停压力回落，并确认指数与市场广度重新同步。",
    }
    return {
        "regime": regime,
        "risk_level": risk_level,
        "conclusion": f"市场处于{regime}状态，当前风险{risk_level}。",
        "evidence": [
            {
                "key": "index_direction",
                "label": "指数方向",
                "value": round(index_average, 2) if index_average is not None else None,
                "unit": "%",
                "signal": index_signal,
            },
            {
                "key": "participation",
                "label": "上涨参与度",
                "value": round(breadth * 100, 1),
                "unit": "%",
                "signal": "广泛" if breadth >= 0.58 else "收窄" if breadth <= 0.42 else "均衡",
            },
            {
                "key": "limit_pressure",
                "label": "跌停压力",
                "value": round(limit_pressure * 100, 1),
                "unit": "%",
                "signal": "升高" if limit_pressure >= 0.25 else "可控",
            },
            {
                "key": "concentration",
                "label": "主题集中度",
                "value": round(concentration * 100, 1),
                "unit": "%",
                "signal": "集中" if concentration >= 0.45 else "分散",
            },
        ],
        "primary_risk": (
            "跌停压力正在压制市场环境"
            if snapshot.limit_down >= 25
            else "主题强度可能集中在少数方向"
            if concentration >= 0.45
            else "当前没有单一高压风险"
        ),
        "next_check": next_checks[regime],
    }


def _opportunity_stage(sector: SectorPulse) -> str:
    if (
        sector.advancing_ratio is None
        or sector.consecutive_days is None
        or sector.high_divergence is None
    ):
        return "方向分歧"
    if sector.high_divergence:
        return "分歧"
    if sector.advancing_ratio >= 0.70 and sector.consecutive_days >= 2:
        return "扩散"
    if sector.pct_change >= 5 or sector.amount_change >= 20:
        return "加速"
    return "观察"


def _market_permission(snapshot: MarketSnapshot) -> dict[str, str]:
    regime, risk_level, _ = _market_state(snapshot)
    if regime == "扩张" and risk_level == "可控":
        return {
            "label": "主动跟踪",
            "tone": "constructive",
            "reason": "市场扩张且风险可控",
        }
    if regime == "收缩" or risk_level == "升高":
        return {
            "label": "防守等待",
            "tone": "defensive",
            "reason": f"市场{regime}且风险{risk_level}",
        }
    return {
        "label": "结构确认",
        "tone": "selective",
        "reason": "市场轮动，等待强度扩散",
    }


def _candidate_summary(candidate: Candidate) -> dict[str, object]:
    return {
        "code": candidate.code,
        "name": candidate.name,
        "pct_change": (
            round(candidate.pct_change, 2) if candidate.pct_change is not None else None
        ),
        "latest_price": round(candidate.latest_price, 2),
    }


def build_opportunities(snapshot: MarketSnapshot) -> list[dict[str, object]]:
    invalidations = {
        "扩散": "上涨占比跌破 50% 或分歧升高",
        "加速": "成交变化转负或上涨占比跌破 50%",
        "分歧": "分歧持续扩大或上涨占比跌破 50%",
        "方向分歧": "补齐参与度、连续性和分歧证据后重新判断",
        "逆势异动": "市场广度未修复或跌停压力继续升高",
        "观察": "强度跌出前八或上涨占比跌破 50%",
    }
    permission = _market_permission(snapshot)
    ordered = sorted(snapshot.sectors, key=sector_score, reverse=True)[:8]
    opportunities = []
    for sector in ordered:
        raw_stage = _opportunity_stage(sector)
        stage = "逆势异动" if permission["tone"] == "defensive" else raw_stage
        matching = sorted(
            (candidate for candidate in snapshot.candidates if candidate.sector == sector.name),
            key=lambda item: item.pct_change if item.pct_change is not None else float("-inf"),
            reverse=True,
        )[:5]
        opportunities.append(
            {
                "theme": sector.name,
                "stage": stage,
                "strength": round(sector_score(sector), 2),
                "pct_change": round(sector.pct_change, 2),
                "advancing_ratio": (
                    round(sector.advancing_ratio, 3)
                    if sector.advancing_ratio is not None
                    else None
                ),
                "amount_change": round(sector.amount_change, 2),
                "consecutive_days": sector.consecutive_days,
                "evidence": [
                    (
                        f"上涨参与度 {sector.advancing_ratio * 100:.0f}%"
                        if sector.advancing_ratio is not None
                        else "上涨参与度 —"
                    ),
                    f"成交变化 {sector.amount_change:+.1f}%",
                    (
                        f"连续 {sector.consecutive_days} 日"
                        if sector.consecutive_days is not None
                        else "连续性 —"
                    ),
                ],
                "candidates": [_candidate_summary(candidate) for candidate in matching],
                "invalidation": invalidations[stage],
            }
        )
    return opportunities


def build_decision_brief(snapshot: MarketSnapshot) -> dict[str, object]:
    market = build_market_analysis(snapshot)
    opportunities = build_opportunities(snapshot)
    regime = str(market["regime"])
    permission = _market_permission(snapshot)

    top = opportunities[0] if opportunities else None
    if top is None:
        status, label = "none", "未形成主线"
        reason = "当前快照没有可用主题证据"
        summary = "当前没有足够主题证据形成主线判断。"
    elif permission["tone"] == "defensive":
        status, label = "countertrend", "逆势异动"
        reason = "市场环境不支持确认主线"
        summary = f"尚未形成可确认主线，{top['theme']}属于逆势异动。"
    elif permission["tone"] == "constructive" and top["stage"] == "扩散":
        status, label = "confirmed", "确认主线"
        reason = "市场扩张，主题参与度和连续性同步确认"
        summary = f"已形成可确认主线，{top['theme']}处于扩散阶段。"
    elif permission["tone"] == "selective" and top["stage"] in {"扩散", "加速"}:
        status, label = "candidate", "候选主线"
        reason = "主题证据领先，但市场仍需确认扩散"
        summary = f"尚未确认主线，{top['theme']}是当前候选方向。"
    else:
        status, label = "divergent", "方向分歧"
        reason = "第一主题分歧较高或连续性不足"
        summary = f"尚未形成可确认主线，{top['theme']}仍处于方向分歧。"

    trigger_labels = {
        "扩张": "保持广度与低跌停",
        "轮动": "等待强度扩散",
        "收缩": "等待广度修复",
    }
    theme = top["theme"] if top is not None else None
    mainline = {
        "status": status,
        "label": label,
        "theme": theme,
        "stage": top["stage"] if top is not None else None,
        "strength": top["strength"] if top is not None else None,
        "reason": reason,
        "invalidation": top["invalidation"] if top is not None else "等待主题证据",
        "candidates": top["candidates"] if top is not None else [],
    }
    return {
        "permission": permission,
        "mainline": mainline,
        "headline": f"市场{regime}，当前以{permission['label']}为主",
        "summary": summary,
        "next_trigger": market["next_check"],
        "chain": [
            {"key": "environment", "label": "市场环境", "value": regime},
            {"key": "permission", "label": "参与许可", "value": permission["label"]},
            {"key": "mainline", "label": "主线判定", "value": label},
            {"key": "validation", "label": "验证对象", "value": theme or "暂无"},
            {
                "key": "trigger",
                "label": "升级条件",
                "value": trigger_labels.get(regime, "等待新证据"),
            },
        ],
    }


def find_stock(snapshot: MarketSnapshot, code: str) -> StockProfile | None:
    normalized = code.strip().upper()
    return next((stock for stock in snapshot.stocks if stock.code.upper() == normalized), None)


def _moving_average(stock: StockProfile, window: int) -> float | None:
    if len(stock.bars) < window:
        return None
    return fmean(bar.close for bar in stock.bars[-window:])


def _period_return(stock: StockProfile, periods: int) -> float | None:
    if len(stock.bars) <= periods:
        return None
    previous = stock.bars[-periods - 1].close
    if not previous:
        return None
    return (stock.bars[-1].close - previous) / previous * 100


def _range_volatility(stock: StockProfile) -> float | None:
    ranges = [
        (bar.high - bar.low) / bar.close * 100
        for bar in stock.bars[-10:]
        if bar.high is not None and bar.low is not None and bar.close
    ]
    return fmean(ranges) if ranges else None


def _trend(stock: StockProfile) -> tuple[str, float | None, float | None]:
    average_5d = _moving_average(stock, 5)
    average_20d = _moving_average(stock, 20)
    if average_5d is None:
        return "样本不足", None, average_20d
    latest = stock.bars[-1].close
    reference = average_20d if average_20d is not None else average_5d
    if latest >= reference * 1.02:
        label = "强"
    elif latest <= reference * 0.98:
        label = "弱"
    else:
        label = "平"
    return label, average_5d, average_20d


def _quality_label(value: str) -> str:
    return {
        "complete": "完整",
        "good": "完整",
        "partial": "部分",
        "poor": "有限",
        "limited": "有限",
    }.get(value.lower(), value or "有限")


def analyze_stock(stock: StockProfile) -> dict[str, object]:
    trend_label, average_5d, average_20d = _trend(stock)
    inside = stock.flow.inside_volume
    outside = stock.flow.outside_volume
    order_balance = None
    if inside is not None and outside is not None and inside + outside:
        order_balance = (outside - inside) / (inside + outside) * 100

    latest = stock.bars[-1]
    latest_change = latest.pct_change
    if latest_change is None and len(stock.bars) > 1:
        previous = stock.bars[-2].close
        latest_change = (latest.close - previous) / previous * 100 if previous else None

    risks = []
    if len(stock.bars) < 20:
        risks.append("历史样本不足 20 个交易日")
    if not stock.price_reliable:
        risks.append("最新价格可靠性有限")
    if stock.missing_fields:
        risks.append(f"缺失字段：{'、'.join(stock.missing_fields[:4])}")

    return {
        "code": stock.code,
        "name": stock.name,
        "sector": stock.sector,
        "latest_price": round(latest.close, 2),
        "pct_change": round(latest_change, 2) if latest_change is not None else None,
        "as_of": latest.date,
        "trend": {
            "label": trend_label,
            "average_5d": round(average_5d, 2) if average_5d is not None else None,
            "average_20d": round(average_20d, 2) if average_20d is not None else None,
            "points": [round(bar.close, 2) for bar in stock.bars[-30:]],
        },
        "momentum": {
            "return_5d": (
                round(value, 2) if (value := _period_return(stock, 5)) is not None else None
            ),
            "return_20d": (
                round(value, 2) if (value := _period_return(stock, 20)) is not None else None
            ),
        },
        "volatility": {
            "range_10d": (
                round(value, 2) if (value := _range_volatility(stock)) is not None else None
            )
        },
        "valuation": {
            "pe_ttm": stock.valuation.pe_ttm,
            "pb": stock.valuation.pb,
            "ps": stock.valuation.ps,
            "total_market_value": stock.valuation.total_market_value,
        },
        "flow": {
            "amount_yuan": stock.flow.amount_yuan,
            "turnover_rate": stock.flow.turnover_rate,
            "order_balance": round(order_balance, 2) if order_balance is not None else None,
        },
        "events": [
            {
                "published_at": item.published_at,
                "source": item.source,
                "title": item.title,
                "summary": item.summary,
            }
            for item in stock.events[:5]
        ],
        "quality": {
            "label": _quality_label(stock.data_quality),
            "price_reliable": stock.price_reliable,
            "primary_source": stock.primary_source,
            "missing_fields": list(stock.missing_fields),
        },
        "evidence": [
            f"趋势状态：{trend_label}",
            f"最近 5 日动量：{_period_return(stock, 5):+.2f}%"
            if _period_return(stock, 5) is not None
            else "最近 5 日动量：样本不足",
            f"最近 10 日平均振幅：{_range_volatility(stock):.2f}%"
            if _range_volatility(stock) is not None
            else "最近 10 日平均振幅：数据不足",
        ],
        "risks": risks or ["当前快照未识别到显著数据风险"],
    }


def _stock_summary(stock: StockProfile) -> dict[str, object]:
    detail = analyze_stock(stock)
    return {
        "code": stock.code,
        "name": stock.name,
        "sector": stock.sector,
        "latest_price": detail["latest_price"],
        "pct_change": detail["pct_change"],
        "trend": detail["trend"]["label"],
        "quality": detail["quality"]["label"],
    }


def search_stocks(
    snapshot: MarketSnapshot, query: str, limit: int = 20
) -> list[dict[str, object]]:
    normalized = query.strip().lower()
    matched = [
        stock
        for stock in snapshot.stocks
        if not normalized
        or normalized in stock.code.lower()
        or normalized in stock.name.lower()
        or normalized in stock.sector.lower()
    ]
    return [_stock_summary(stock) for stock in matched[: max(0, min(limit, 20))]]
