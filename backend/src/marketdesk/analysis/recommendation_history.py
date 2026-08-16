from __future__ import annotations

from datetime import datetime
from typing import Literal

from marketdesk.models import (
    RecommendationHistoryResult,
    RecommendationObservation,
    RecommendationPerformanceDay,
    RecommendationPerformancePick,
    RecommendationPerformanceSummary,
    RecommendationSnapshot,
)


def _return_pct(entry: float | None, price: float | None) -> float | None:
    if entry is None or price is None or entry <= 0:
        return None
    return round((price / entry - 1) * 100, 2)


def _average(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 2) if values else None


def _rate(flags: list[bool]) -> float | None:
    return round(sum(flags) / len(flags), 4) if flags else None


def _performance_pick(
    run: RecommendationSnapshot,
    pick_index: int,
    observations: list[RecommendationObservation],
) -> RecommendationPerformancePick:
    pick = run.picks[pick_index]
    ordered = sorted(observations, key=lambda item: (item.trading_date, item.observed_at))
    later = [item for item in ordered if item.trading_date > run.trading_date]
    current_observation = next(
        (item for item in reversed(ordered) if item.prices.get(pick.symbol) is not None),
        None,
    )

    def price_after(session_count: int) -> float | None:
        if len(later) < session_count:
            return None
        return later[session_count - 1].prices.get(pick.symbol)

    def benchmark_after(session_count: int) -> float | None:
        if len(later) < session_count:
            return None
        return later[session_count - 1].benchmark_price

    current_price = (
        current_observation.prices.get(pick.symbol) if current_observation is not None else None
    )
    current_benchmark = (
        current_observation.benchmark_price if current_observation is not None else None
    )
    return_20d = _return_pct(pick.entry_price, price_after(20))
    benchmark_20d = _return_pct(run.benchmark_price, benchmark_after(20))
    current_return = _return_pct(pick.entry_price, current_price)
    current_benchmark_return = _return_pct(run.benchmark_price, current_benchmark)
    valid_prices = [pick.entry_price] if pick.entry_price is not None else []
    valid_prices.extend(
        price
        for observation in ordered
        if (price := observation.prices.get(pick.symbol)) is not None
    )
    peak_return = (
        _return_pct(pick.entry_price, max(valid_prices)) if valid_prices else None
    )
    max_drawdown: float | None = None
    if valid_prices:
        running_peak = valid_prices[0]
        drawdowns: list[float] = []
        for price in valid_prices:
            running_peak = max(running_peak, price)
            drawdowns.append((price / running_peak - 1) * 100)
        max_drawdown = round(min(drawdowns), 2)
    status: Literal["tracking", "validating", "evaluated", "missing"] = (
        "missing"
        if pick.entry_price is None or current_price is None
        else "evaluated"
        if len(later) >= 20
        else "validating"
        if len(later) >= 5
        else "tracking"
    )
    return RecommendationPerformancePick(
        rank=pick.rank,
        symbol=pick.symbol,
        name=pick.name,
        sector=pick.sector,
        entry_price=pick.entry_price,
        current_price=current_price,
        score=pick.score,
        evidence_coverage=pick.evidence_coverage,
        thesis=pick.thesis,
        risk_flags=pick.risk_flags,
        observed_sessions=len(later),
        return_1d=_return_pct(pick.entry_price, price_after(1)),
        return_5d=_return_pct(pick.entry_price, price_after(5)),
        return_20d=return_20d,
        current_return=current_return,
        benchmark_20d_return=benchmark_20d,
        excess_20d_return=(
            round(return_20d - benchmark_20d, 2)
            if return_20d is not None and benchmark_20d is not None
            else None
        ),
        current_benchmark_return=current_benchmark_return,
        current_excess_return=(
            round(current_return - current_benchmark_return, 2)
            if current_return is not None and current_benchmark_return is not None
            else None
        ),
        peak_return=peak_return,
        max_drawdown=max_drawdown,
        status=status,
    )


def analyse_recommendation_history(
    preset: str,
    series: list[tuple[RecommendationSnapshot, list[RecommendationObservation]]],
    generated_at: datetime,
) -> RecommendationHistoryResult:
    days = [
        RecommendationPerformanceDay(
            preset=run.preset,
            trading_date=run.trading_date,
            observed_at=run.observed_at,
            available=run.available,
            unavailable_reason=run.unavailable_reason,
            summary=run.summary,
            picks=[
                _performance_pick(run, index, observations)
                for index in range(len(run.picks))
            ],
        )
        for run, observations in series
    ]
    days.sort(key=lambda item: (item.trading_date, item.observed_at), reverse=True)
    picks = [pick for day in days for pick in day.picks]
    evaluated = [pick for pick in picks if pick.return_20d is not None]
    evaluated_excess = [
        pick.excess_20d_return
        for pick in evaluated
        if pick.excess_20d_return is not None
    ]
    current_returns = [
        pick.current_return for pick in picks if pick.current_return is not None
    ]
    observed_times = [
        observation.observed_at
        for _, observations in series
        for observation in observations
    ]
    return RecommendationHistoryResult(
        preset=preset,
        generated_at=generated_at,
        first_tracking_date=min((day.trading_date for day in days), default=None),
        last_observed_at=max(observed_times, default=None),
        summary=RecommendationPerformanceSummary(
            run_count=len(days),
            pick_count=len(picks),
            evaluated_count=len(evaluated),
            average_20d_return=_average(
                [pick.return_20d for pick in evaluated if pick.return_20d is not None]
            ),
            hit_rate_20d=_rate(
                [pick.return_20d > 0 for pick in evaluated if pick.return_20d is not None]
            ),
            benchmark_win_rate_20d=_rate([value > 0 for value in evaluated_excess]),
            average_20d_excess=_average(evaluated_excess),
            average_current_return=_average(current_returns),
            current_positive_rate=_rate([value > 0 for value in current_returns]),
        ),
        days=days,
        methodology=[
            "每天每个策略只冻结一次前 3 只候选及当时价格，后续刷新不会改写入选记录。",
            (
                "趋势延续策略随每日自动刷新归档；当天没有候选也会留下空记录。"
                if preset == "trend"
                else "其他策略从首次打开候选或复盘后开始归档，当天只记录一次。"
            ),
            "T+1、T+5、T+20 按后续可用的交易日观察价计算，不把自然日当作交易日。",
            "20 日命中表示区间收益大于 0；跑赢基准表示同期收益高于上证指数。",
            "统计从本功能首次启用后开始，启用前已覆盖的候选不能可靠倒推。",
        ],
    )
