from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import sqrt
from statistics import pstdev

from .models import DailyBar

MIN_BARS = 20
CONTINUATION_SCORE = 70
BREAKOUT_SCORE = 60
EXCLUDE_SCORE = 45
PULSE_LATEST_RETURN = 5.0
PULSE_CONTRIBUTION = 70.0
OVERHEATED_RETURN_5D = 18.0
OVERHEATED_MA20_DISTANCE = 18.0
OVERHEATED_ANNUALIZED_VOLATILITY = 100.0


@dataclass(frozen=True)
class MultiHorizonProfile:
    as_of: str
    bar_count: int
    latest_return: float
    return_3d: float | None
    return_5d: float | None
    return_10d: float | None
    return_20d: float | None
    up_days_5d: int
    up_days_10d: int
    volume_ratio_5d_to_20d: float | None
    drawdown_10d: float | None
    distance_to_20d_high: float | None
    distance_to_ma20: float | None
    ma_alignment: str
    stale_days: int
    price_reliable: bool
    prior_4d_return: float | None = None
    single_day_contribution: float = 100.0
    annualized_volatility: float | None = None


@dataclass(frozen=True)
class ContinuationAssessment:
    score: int
    stage: str
    confidence: str
    support: str
    counter_evidence: str
    confirmation: str
    invalidation: str


def build_multi_horizon_profile(
    bars: list[DailyBar],
    *,
    market_trade_date: str = "",
    price_reliable: bool = True,
) -> MultiHorizonProfile:
    if not bars:
        return _empty_profile(price_reliable=price_reliable)
    ordered = sorted(bars, key=lambda item: item.date)
    closes = [item.close for item in ordered]
    volumes = [item.volume for item in ordered]
    daily_returns = [
        _pct(closes[index - 1], closes[index])
        for index in range(1, len(closes))
        if closes[index - 1] > 0
    ]
    latest_return = daily_returns[-1] if daily_returns else 0.0
    return_5d = _window_return(closes, 5)
    prior_4d_return = _prior_return(closes, 5)
    positive_5d = sum(max(value, 0.0) for value in daily_returns[-5:])
    contribution = (
        latest_return / positive_5d * 100
        if latest_return > 0 and positive_5d > 0
        else 100.0
    )
    ma5 = _mean(closes[-5:])
    ma10 = _mean(closes[-10:])
    ma20 = _mean(closes[-20:])
    latest = closes[-1]
    return MultiHorizonProfile(
        as_of=ordered[-1].date,
        bar_count=len(ordered),
        latest_return=latest_return,
        return_3d=_window_return(closes, 3),
        return_5d=return_5d,
        return_10d=_window_return(closes, 10),
        return_20d=_window_return(closes, 20),
        up_days_5d=sum(value > 0 for value in daily_returns[-5:]),
        up_days_10d=sum(value > 0 for value in daily_returns[-10:]),
        volume_ratio_5d_to_20d=_ratio(_mean(volumes[-5:]), _mean(volumes[-20:])),
        drawdown_10d=_max_drawdown(closes[-10:]),
        distance_to_20d_high=_pct(max(closes[-20:]), latest) if closes[-20:] else None,
        distance_to_ma20=_pct(ma20, latest) if ma20 else None,
        ma_alignment=_ma_alignment(latest, ma5, ma10, ma20),
        stale_days=_stale_days(ordered[-1].date, market_trade_date),
        price_reliable=price_reliable,
        prior_4d_return=prior_4d_return,
        single_day_contribution=round(contribution, 2),
        annualized_volatility=(
            round(pstdev(daily_returns[-20:]) * sqrt(252), 2)
            if len(daily_returns) >= 2
            else None
        ),
    )


def assess_continuation(
    profile: MultiHorizonProfile,
    *,
    theme_confirmed: bool = False,
    fund_flow: float | None = None,
    evidence_count: int = 0,
) -> ContinuationAssessment:
    blocked_reason = _blocked_reason(profile)
    if blocked_reason:
        return ContinuationAssessment(
            score=0,
            stage="剔除",
            confidence="阻断",
            support="历史行情仍可复盘，但不能支持当前方向判断。",
            counter_evidence=blocked_reason,
            confirmation="等待可靠行情更新至市场交易日且至少保留 20 根真实日线。",
            invalidation="数据仍未更新时维持剔除。",
        )

    score = _base_score(
        profile,
        theme_confirmed=theme_confirmed,
        fund_flow=fund_flow,
        evidence_count=evidence_count,
    )
    pulse = _is_pulse(profile)
    overheated = _is_overheated(profile)
    if pulse:
        score = max(0, score - 18)
        stage = "脉冲待验证"
    elif overheated:
        score = min(69, max(0, score - 25))
        stage = "过热回避"
    elif _is_continuation(profile, score):
        stage = "延续观察"
    elif _is_breakout(profile, score):
        stage = "突破待确认"
    elif (profile.return_5d or 0) > 0 and (
        (profile.return_20d or 0) <= 0 or profile.ma_alignment == "长期线下"
    ):
        stage = "反弹待验证"
    elif score < EXCLUDE_SCORE:
        stage = "剔除"
    else:
        stage = "突破待确认"
    return ContinuationAssessment(
        score=int(max(0, min(100, score))),
        stage=stage,
        confidence=_confidence(stage, evidence_count),
        support=_support(profile, theme_confirmed),
        counter_evidence=_counter(profile, stage, fund_flow),
        confirmation=_confirmation(stage),
        invalidation=_invalidation(profile, stage),
    )


def _empty_profile(*, price_reliable: bool) -> MultiHorizonProfile:
    return MultiHorizonProfile(
        as_of="",
        bar_count=0,
        latest_return=0.0,
        return_3d=None,
        return_5d=None,
        return_10d=None,
        return_20d=None,
        up_days_5d=0,
        up_days_10d=0,
        volume_ratio_5d_to_20d=None,
        drawdown_10d=None,
        distance_to_20d_high=None,
        distance_to_ma20=None,
        ma_alignment="数据不足",
        stale_days=0,
        price_reliable=price_reliable,
    )


def _window_return(closes: list[float], days: int) -> float | None:
    if len(closes) <= days or closes[-days - 1] <= 0:
        return None
    return _pct(closes[-days - 1], closes[-1])


def _prior_return(closes: list[float], days: int) -> float | None:
    if len(closes) <= days or closes[-days - 1] <= 0:
        return None
    return _pct(closes[-days - 1], closes[-2])


def _pct(start: float, end: float) -> float:
    return (end / start - 1) * 100 if start else 0.0


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _ratio(value: float | None, base: float | None) -> float | None:
    if value is None or base in {None, 0}:
        return None
    return round(value / base, 4)


def _max_drawdown(closes: list[float]) -> float | None:
    if not closes:
        return None
    peak = closes[0]
    worst = 0.0
    for close in closes:
        peak = max(peak, close)
        if peak:
            worst = max(worst, (peak - close) / peak * 100)
    return round(worst, 4)


def _ma_alignment(
    latest: float,
    ma5: float | None,
    ma10: float | None,
    ma20: float | None,
) -> str:
    if None in {ma5, ma10, ma20}:
        return "数据不足"
    if latest >= ma5 >= ma10 >= ma20:  # type: ignore[operator]
        return "多头排列"
    if latest >= ma10 >= ma20:  # type: ignore[operator]
        return "中期偏强"
    if latest < ma20:  # type: ignore[operator]
        return "长期线下"
    return "结构整理"


def _stale_days(as_of: str, market_trade_date: str) -> int:
    if not as_of or not market_trade_date:
        return 0
    try:
        return max((date.fromisoformat(market_trade_date) - date.fromisoformat(as_of)).days, 0)
    except ValueError:
        return 0


def _blocked_reason(profile: MultiHorizonProfile) -> str:
    if not profile.price_reliable:
        return "价格可靠性未通过。"
    if profile.bar_count < MIN_BARS:
        return f"真实日线仅 {profile.bar_count} 根，少于持续性判断所需的 {MIN_BARS} 根。"
    if profile.stale_days > 0:
        return f"行情日期落后市场 {profile.stale_days} 天。"
    return ""


def _base_score(
    profile: MultiHorizonProfile,
    *,
    theme_confirmed: bool,
    fund_flow: float | None,
    evidence_count: int,
) -> int:
    score = 0
    if (profile.return_5d or 0) > 0:
        score += 8
    if (profile.return_10d or 0) > 0:
        score += 8
    if (profile.return_20d or 0) > 0:
        score += 5
    if (profile.return_5d or 0) > 0 and (profile.return_10d or 0) > 0:
        score += 4
    score += 8 if profile.up_days_5d >= 3 else 4 if profile.up_days_5d >= 2 else 0
    score += 7 if profile.up_days_10d >= 6 else 3 if profile.up_days_10d >= 4 else 0
    score += {"多头排列": 15, "中期偏强": 10, "结构整理": 5}.get(
        profile.ma_alignment, 0
    )
    ratio = profile.volume_ratio_5d_to_20d
    if ratio is not None and 0.9 <= ratio <= 1.8:
        score += 10
    elif ratio is not None and 0.7 <= ratio <= 2.2:
        score += 6
    else:
        score += 2
    drawdown = profile.drawdown_10d
    if drawdown is not None and drawdown <= 5:
        score += 10
    elif drawdown is not None and drawdown <= 8:
        score += 6
    elif drawdown is not None and drawdown <= 12:
        score += 2
    volatility = profile.annualized_volatility
    if volatility is not None and volatility <= 40:
        score += 5
    elif volatility is not None and volatility <= 65:
        score += 2
    score += 10 if theme_confirmed else 0
    if fund_flow is not None and fund_flow > 0:
        score += 5
    score += min(max(evidence_count, 0), 5)
    return int(min(score, 100))


def _is_pulse(profile: MultiHorizonProfile) -> bool:
    return (
        profile.latest_return >= PULSE_LATEST_RETURN
        and profile.single_day_contribution >= PULSE_CONTRIBUTION
        and (profile.prior_4d_return or 0) <= 1
    )


def _is_overheated(profile: MultiHorizonProfile) -> bool:
    return (
        (profile.return_5d or 0) >= OVERHEATED_RETURN_5D
        or (profile.distance_to_ma20 or 0) >= OVERHEATED_MA20_DISTANCE
        or (profile.annualized_volatility or 0) >= OVERHEATED_ANNUALIZED_VOLATILITY
    )


def _is_continuation(profile: MultiHorizonProfile, score: int) -> bool:
    return (
        score >= CONTINUATION_SCORE
        and (profile.return_5d or 0) > 0
        and (profile.return_10d or 0) > 0
        and profile.up_days_5d >= 3
        and profile.ma_alignment in {"多头排列", "中期偏强"}
    )


def _is_breakout(profile: MultiHorizonProfile, score: int) -> bool:
    return (
        score >= BREAKOUT_SCORE
        and (profile.return_5d or 0) > 0
        and (profile.distance_to_20d_high or -999) >= -1
    )


def _confidence(stage: str, evidence_count: int) -> str:
    if stage in {"剔除", "过热回避"}:
        return "阻断"
    if stage == "延续观察" and evidence_count >= 2:
        return "高"
    return "中"


def _support(profile: MultiHorizonProfile, theme_confirmed: bool) -> str:
    theme = "，主题同步确认" if theme_confirmed else ""
    return (
        f"5日 {_format_pct(profile.return_5d)}，10日 {_format_pct(profile.return_10d)}，"
        f"近5日 {profile.up_days_5d} 天上涨，{profile.ma_alignment}{theme}。"
    )


def _counter(
    profile: MultiHorizonProfile,
    stage: str,
    fund_flow: float | None,
) -> str:
    if stage == "脉冲待验证":
        return f"单日贡献度 {profile.single_day_contribution:.0f}%，上涨可能集中于一天。"
    if stage == "过热回避":
        return "短期涨幅或均线偏离过大，继续追涨的回撤风险上升。"
    if fund_flow is None:
        return "资金流证据缺失，不将成交代理当作主力资金确认。"
    return f"近10日最大回撤 {_format_pct(profile.drawdown_10d, positive=True)}。"


def _confirmation(stage: str) -> str:
    if stage == "延续观察":
        return "下一交易日不跌破 10 日均线，且量能不出现明显衰竭。"
    if stage == "突破待确认":
        return "突破后至少一个交易日站稳，并保持强于所属主题。"
    if stage == "反弹待验证":
        return "先站回 20 日均线，再观察上涨天数是否继续增加。"
    if stage == "脉冲待验证":
        return "不追高，等待回踩承接和第二个交易日确认。"
    return "等待过热程度回落或数据闸门解除。"


def _invalidation(profile: MultiHorizonProfile, stage: str) -> str:
    if stage in {"延续观察", "突破待确认"}:
        return "跌破 10 日均线或放量冲高回落时移出观察。"
    if stage == "反弹待验证":
        return "反弹未能站回 20 日均线或再创新低时失效。"
    if stage == "脉冲待验证":
        return "次日无法承接或跌回启动位时失效。"
    return "风险闸门未解除前不进入候选。"


def _format_pct(value: float | None, *, positive: bool = False) -> str:
    if value is None:
        return "待补"
    if positive:
        return f"{abs(value):.2f}%"
    return f"{value:+.2f}%"
