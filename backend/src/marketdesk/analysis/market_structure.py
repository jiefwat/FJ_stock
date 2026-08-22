from __future__ import annotations

import math
from collections import Counter
from typing import Literal
from zoneinfo import ZoneInfo

from marketdesk.analysis.market import analyse_market
from marketdesk.analysis.opportunities import STRATEGY_LABELS, STRATEGY_RULES, rank_candidates
from marketdesk.models import (
    Bar,
    EquityQuote,
    LimitLadderLevel,
    LimitLadderResult,
    LimitLadderStock,
    MarketDashboard,
    MarketDistributionBand,
    MarketGroupAnalysis,
    MarketGroupLeader,
    MarketGroupStat,
    MarketSnapshot,
    SectorSnapshot,
    StrategyBoard,
    StrategyBoardCard,
)

STRATEGY_ORDER = (
    "trend",
    "volume_breakout",
    "capital_confirmed",
    "sector_momentum",
    "pullback_support",
    "value_rebound",
    "quality_value",
    "large_cap_stability",
    "oversold_repair",
)

STRATEGY_PRESENTATION = {
    "trend": ("趋势", "跌破 20 日趋势或成交萎缩"),
    "volume_breakout": ("突破", "放量失败或跌回突破区间"),
    "capital_confirmed": ("资金", "资金转为持续净流出"),
    "sector_momentum": ("板块", "板块扩散和资金共振消失"),
    "pullback_support": ("回踩", "支撑失守或下跌惯性延续"),
    "value_rebound": ("反转", "估值逻辑被基本面风险证伪"),
    "quality_value": ("质量", "财务质量或估值安全边际恶化"),
    "large_cap_stability": ("稳健", "流动性和低波结构同时恶化"),
    "oversold_repair": ("修复", "止跌失败并再次扩大跌幅"),
}


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))


def _average(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _is_limit_change(change_pct: float | None, limit_pct: float, mode: Literal["up", "down"]) -> bool:
    if change_pct is None:
        return False
    return change_pct >= limit_pct - 0.2 if mode == "up" else change_pct <= -limit_pct + 0.2


def analyse_market_dashboard(snapshot: MarketSnapshot) -> MarketDashboard:
    analysis = analyse_market(snapshot)
    changes = [quote.change_pct for quote in snapshot.equities if quote.change_pct is not None]
    flow_values = [quote.net_flow for quote in snapshot.equities if quote.net_flow is not None]
    amount_values = [quote.amount for quote in snapshot.equities if quote.amount is not None]
    total = analysis.advancing + analysis.declining + analysis.unchanged
    bands = [
        MarketDistributionBand(
            key="strong_down",
            label="≤ -5%",
            count=sum(value <= -5 for value in changes),
            tone="strong_down",
        ),
        MarketDistributionBand(
            key="down",
            label="-5% ~ -1%",
            count=sum(-5 < value < -1 for value in changes),
            tone="down",
        ),
        MarketDistributionBand(
            key="flat",
            label="-1% ~ 1%",
            count=sum(-1 <= value <= 1 for value in changes),
            tone="flat",
        ),
        MarketDistributionBand(
            key="up",
            label="1% ~ 5%",
            count=sum(1 < value < 5 for value in changes),
            tone="up",
        ),
        MarketDistributionBand(
            key="strong_up",
            label="≥ 5%",
            count=sum(value >= 5 for value in changes),
            tone="strong_up",
        ),
    ]
    sectors_with_change = [item for item in snapshot.sectors if item.change_pct is not None]
    strongest = sorted(
        sectors_with_change,
        key=lambda item: (
            item.change_pct if item.change_pct is not None else -math.inf,
            item.net_flow if item.net_flow is not None else -math.inf,
        ),
        reverse=True,
    )[:6]
    weakest = sorted(
        sectors_with_change,
        key=lambda item: (
            item.change_pct if item.change_pct is not None else math.inf,
            item.net_flow if item.net_flow is not None else math.inf,
        ),
    )[:6]
    activity = sorted(
        snapshot.equities,
        key=lambda item: (item.amount is not None, item.amount or 0),
        reverse=True,
    )[:8]
    missing: list[str] = []
    if not amount_values:
        missing.append("全市场成交额")
    if not flow_values:
        missing.append("个股资金流")
    if not sectors_with_change:
        missing.append("板块涨跌")
    return MarketDashboard(
        meta=snapshot.meta,
        score=analysis.score,
        regime=analysis.regime,
        confidence=analysis.confidence,
        breadth_pct=round(analysis.advancing / total * 100, 2) if total else None,
        capital_inflow_pct=(
            round(sum(value > 0 for value in flow_values) / len(flow_values) * 100, 2)
            if flow_values
            else None
        ),
        total_turnover=sum(amount_values) if amount_values else None,
        limit_up_count=sum(
            item.price_limit_pct is not None
            and _is_limit_change(item.change_pct, item.price_limit_pct, "up")
            for item in snapshot.equities
        ),
        limit_down_count=sum(
            item.price_limit_pct is not None
            and _is_limit_change(item.change_pct, item.price_limit_pct, "down")
            for item in snapshot.equities
        ),
        distribution=bands,
        strongest_sectors=strongest,
        weakest_sectors=weakest,
        activity_leaders=activity,
        missing_evidence=(
            missing
            + (["部分标的涨跌停规则"] if any(item.price_limit_pct is None for item in snapshot.equities) else [])
        ),
    )


def build_strategy_board(snapshot: MarketSnapshot) -> StrategyBoard:
    market = analyse_market(snapshot)
    sector_strength = {
        item.name: item.change_pct for item in snapshot.sectors if item.change_pct is not None
    }
    cards: list[StrategyBoardCard] = []
    for preset in STRATEGY_ORDER:
        result = rank_candidates(
            snapshot.equities,
            market.regime,
            preset,
            sector_strength=sector_strength,
        )
        top = result.candidates[0] if result.candidates else None
        coverage = (
            _average([item.evidence_coverage for item in result.candidates[:10]])
            if result.candidates
            else snapshot.meta.coverage * 0.7
        )
        category, exit_signal = STRATEGY_PRESENTATION[preset]
        cards.append(
            StrategyBoardCard(
                id=preset,
                name=STRATEGY_LABELS[preset],
                category=category,
                summary=result.summary,
                entry_signal="；".join(STRATEGY_RULES[preset][:2]),
                exit_signal=exit_signal,
                hit_count=len(result.candidates),
                available=result.available,
                confidence=round(max(0.0, min(1.0, coverage or 0.0)), 2),
                top_candidate=top.quote if top else None,
            )
        )
    return StrategyBoard(meta=snapshot.meta, cards=cards)


def _bar_change(current: Bar, previous: Bar) -> float | None:
    if previous.close <= 0:
        return None
    return (current.close / previous.close - 1) * 100


def _historical_streak(
    bars: list[Bar], limit_pct: float, mode: Literal["up", "down"]
) -> tuple[int, bool | None]:
    ordered = sorted(bars, key=lambda item: item.date)
    if len(ordered) < 2:
        return 1, None
    streak = 0
    for index in range(len(ordered) - 1, 0, -1):
        change = _bar_change(ordered[index], ordered[index - 1])
        if not _is_limit_change(change, limit_pct, mode):
            break
        streak += 1
    latest = ordered[-1]
    tolerance = max(0.001, abs(latest.close) * 0.0005)
    one_word = (
        abs(latest.open - latest.close) <= tolerance
        and abs(latest.high - latest.close) <= tolerance
        and abs(latest.low - latest.close) <= tolerance
    )
    return max(1, streak), one_word


def build_limit_ladder(
    snapshot: MarketSnapshot,
    history_by_symbol: dict[str, list[Bar]],
    mode: Literal["up", "down"] = "up",
) -> LimitLadderResult:
    target_date = snapshot.meta.observed_at.astimezone(ZoneInfo("Asia/Shanghai")).date()
    has_limit_profiles = any(quote.price_limit_pct is not None for quote in snapshot.equities)
    candidates = [
        quote
        for quote in snapshot.equities
        if quote.price_limit_pct is not None
        and _is_limit_change(quote.change_pct, quote.price_limit_pct, mode)
    ]
    stocks: list[LimitLadderStock] = []
    for quote in candidates:
        assert quote.price_limit_pct is not None
        limit_pct = quote.price_limit_pct
        bars = sorted(
            [bar for bar in history_by_symbol.get(quote.symbol, []) if bar.date <= target_date],
            key=lambda item: item.date,
        )
        has_target_bar = bool(bars) and bars[-1].date == target_date
        if "ST" in quote.name.upper() or not has_target_bar:
            streak, one_word = 1, None
        else:
            streak, one_word = _historical_streak(bars, limit_pct, mode)
        confidence = (
            0.4
            + (0.4 if has_target_bar and len(bars) >= 2 else 0)
            + (0.2 if one_word is not None else 0)
        )
        evidence = [f"当日涨跌 {quote.change_pct:+.2f}%", f"该股票涨跌停阈值 {limit_pct:.0f}%"]
        if has_target_bar and len(bars) >= 2:
            evidence.append(f"未复权日线验证为 {streak} 连板")
        elif bars and not has_target_bar:
            evidence.append(f"未复权日线停在 {bars[-1].date.isoformat()}，未用于目标日连板推断")
        else:
            evidence.append("未复权历史日线不足，仅确认当日涨跌停")
        if "ST" in quote.name.upper():
            evidence.append("缺少历史 ST 状态，连续板不跨日推断")
        stocks.append(
            LimitLadderStock(
                quote=quote,
                streak=streak,
                limit_pct=limit_pct,
                one_word=one_word,
                confidence=round(confidence, 2),
                evidence=evidence,
            )
        )
    grouped: dict[int, list[LimitLadderStock]] = {}
    for stock in stocks:
        grouped.setdefault(stock.streak, []).append(stock)
    levels = [
        LimitLadderLevel(
            streak=streak,
            label=f"{streak}板" if streak > 1 else ("首板" if mode == "up" else "首跌停"),
            stocks=sorted(
                rows,
                key=lambda item: (item.quote.amount or 0, item.quote.turnover_rate or 0),
                reverse=True,
            ),
        )
        for streak, rows in sorted(grouped.items(), reverse=True)
    ]
    industries = Counter(item.quote.sector or "行业待补" for item in stocks)
    confidence = _average([item.confidence for item in stocks]) or snapshot.meta.coverage * 0.4
    available = bool(snapshot.equities) and has_limit_profiles
    return LimitLadderResult(
        meta=snapshot.meta,
        mode=mode,
        available=available,
        unavailable_reason=(
            None if available else "当前快照缺少可识别的 A 股涨跌停规则，不能把空结果解释为无涨跌停。"
        ),
        total=len(stocks),
        max_streak=max(grouped, default=0),
        confidence=round(max(0.0, min(1.0, confidence)), 2),
        levels=levels,
        industry_distribution=dict(industries.most_common(12)),
        methodology=[
            "按 ST 5%、主板 10%、创业板/科创板 20%、北交所 30% 的阈值识别。",
            "N/C 新股上市初期不套用普通涨跌停阈值；缺少可确认规则时不进入梯队。",
            "连续板数只使用未复权原始日线验证；原始日线不足时只确认当日状态。",
            "历史 ST 状态缺失时不跨日推断，避免用当前规则污染历史日期。",
            "封单金额缺少盘口证据，本页不作推测。",
        ],
    )


def _leader_score(quote: EquityQuote) -> float:
    components: list[tuple[float, float]] = []
    if quote.change_pct is not None:
        components.append((_clamp(50 + quote.change_pct * 7), 0.4))
    if quote.turnover_rate is not None:
        components.append((_clamp(quote.turnover_rate / 12 * 100), 0.2))
    if quote.amount is not None:
        components.append(
            (_clamp(math.log1p(max(0.0, quote.amount)) / math.log1p(20_000_000_000) * 100), 0.2)
        )
    if quote.net_flow is not None:
        components.append((_clamp(50 + quote.net_flow / 100_000_000 * 8), 0.2))
    total_weight = sum(weight for _, weight in components)
    return _clamp(sum(value * weight for value, weight in components) / total_weight) if total_weight else 0


def analyse_market_groups(
    meta: object,
    groups: list[SectorSnapshot],
    constituents_by_code: dict[str, list[EquityQuote]],
    kind: Literal["concept", "industry"],
    unavailable_reason: str | None = None,
    degraded: bool = False,
) -> MarketGroupAnalysis:
    from marketdesk.models import DatasetMeta

    dataset_meta = DatasetMeta.model_validate(meta)
    stats: list[MarketGroupStat] = []
    for group in groups:
        constituents = constituents_by_code.get(group.code, [])
        changes = [item.change_pct for item in constituents if item.change_pct is not None]
        turnovers = [item.turnover_rate for item in constituents if item.turnover_rate is not None]
        amounts = [item.amount for item in constituents if item.amount is not None]
        advancing = sum(value > 0 for value in changes)
        declining = sum(value < 0 for value in changes)
        average_change = _average(changes)
        breadth = advancing / len(changes) * 100 if changes else None
        leader_quote = max(constituents, key=_leader_score, default=None)
        leader = (
            MarketGroupLeader(quote=leader_quote, score=round(_leader_score(leader_quote), 2))
            if leader_quote
            else None
        )
        heat_inputs = [
            50 + (group.change_pct or 0) * 8 if group.change_pct is not None else None,
            breadth,
            leader.score if leader else None,
            50 + group.net_flow / 100_000_000 * 3 if group.net_flow is not None else None,
        ]
        heat_available = [value for value in heat_inputs if value is not None]
        heat = _clamp(_average(heat_available) or 50)
        missing: list[str] = []
        if group.change_pct is None:
            missing.append("板块涨跌")
        if group.net_flow is None:
            missing.append("板块资金流")
        if not constituents:
            missing.append("成分股")
        present = 3 - len(missing)
        stats.append(
            MarketGroupStat(
                code=group.code,
                name=group.name,
                kind=kind,
                change_pct=group.change_pct,
                net_flow=group.net_flow,
                constituent_count=len(constituents),
                advancing=advancing,
                declining=declining,
                average_change_pct=round(average_change, 2) if average_change is not None else None,
                average_turnover_rate=(
                    round(_average(turnovers) or 0, 2) if turnovers else None
                ),
                total_amount=sum(amounts) if amounts else None,
                heat_score=round(heat, 2),
                risk_score=round(_clamp(100 - heat + max(0, declining - advancing) * 2), 2),
                evidence_coverage=round(present / 3, 2),
                leader=leader,
                constituents=sorted(constituents, key=_leader_score, reverse=True)[:30],
                missing_evidence=missing,
            )
        )
    stats.sort(
        key=lambda item: (
            item.heat_score,
            item.net_flow if item.net_flow is not None else -math.inf,
        ),
        reverse=True,
    )
    available = bool(stats)
    label = "概念" if kind == "concept" else "行业"
    summary = (
        f"当前覆盖 {len(stats)} 个{label}，按涨跌扩散、资金和龙头强度排序。"
        if stats
        else f"暂未取得{label}目录，不能据空结果判断市场没有主线。"
    )
    return MarketGroupAnalysis(
        meta=dataset_meta,
        kind=kind,
        available=available,
        degraded=degraded or unavailable_reason is not None,
        unavailable_reason=unavailable_reason,
        summary=summary,
        groups=stats,
        methodology=[
            "热度由板块涨跌、成分股扩散、资金和龙头强度共同计算。",
            "当前只比较最新横截面；尚无板块历史序列时不展示伪轮动趋势。",
            "个股参与判断仍以 Stock Lab 的完整证据账本为准。",
        ],
    )
