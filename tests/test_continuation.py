from __future__ import annotations

from datetime import date, timedelta

import pytest

from stock_ts.continuation import (
    assess_continuation,
    build_multi_horizon_profile,
)
from stock_ts.models import DailyBar


def _bars(closes: list[float], *, start: date = date(2026, 6, 1)) -> list[DailyBar]:
    return [
        DailyBar(
            date=(start + timedelta(days=index)).isoformat(),
            open=close * 0.995,
            high=close * 1.01,
            low=close * 0.99,
            close=close,
            volume=1_000_000 + index * 10_000,
        )
        for index, close in enumerate(closes)
    ]


def test_profile_exposes_reproducible_multi_horizon_statistics() -> None:
    bars = _bars([100 + index for index in range(25)])

    profile = build_multi_horizon_profile(
        bars,
        market_trade_date=bars[-1].date,
        price_reliable=True,
    )

    assert profile.return_5d == pytest.approx((124 / 119 - 1) * 100)
    assert profile.return_10d == pytest.approx((124 / 114 - 1) * 100)
    assert profile.return_20d == pytest.approx((124 / 104 - 1) * 100)
    assert profile.up_days_5d == 5
    assert profile.up_days_10d == 10
    assert profile.volume_ratio_5d_to_20d is not None
    assert profile.drawdown_10d == pytest.approx(0.0)
    assert profile.ma_alignment == "多头排列"
    assert assess_continuation(profile, theme_confirmed=True).stage == "延续观察"


def test_one_day_spike_without_prior_trend_is_pulse_not_continuation() -> None:
    bars = _bars([100.0] * 24 + [106.0])

    assessment = assess_continuation(
        build_multi_horizon_profile(bars, market_trade_date=bars[-1].date)
    )

    assert assessment.stage == "脉冲待验证"
    assert "单日" in assessment.counter_evidence


def test_overextended_five_day_move_is_marked_overheated() -> None:
    bars = _bars([100.0] * 19 + [101, 106, 112, 118, 124, 130])

    assessment = assess_continuation(
        build_multi_horizon_profile(bars, market_trade_date=bars[-1].date)
    )

    assert assessment.stage == "过热回避"
    assert assessment.score < 70


@pytest.mark.parametrize(
    ("bars", "market_date", "price_reliable"),
    [
        (_bars([100 + index for index in range(19)]), "2026-06-19", True),
        (_bars([100 + index for index in range(25)]), "2026-06-26", True),
        (_bars([100 + index for index in range(25)]), "2026-06-25", False),
    ],
)
def test_unusable_price_history_is_excluded(
    bars: list[DailyBar],
    market_date: str,
    price_reliable: bool,
) -> None:
    assessment = assess_continuation(
        build_multi_horizon_profile(
            bars,
            market_trade_date=market_date,
            price_reliable=price_reliable,
        )
    )

    assert assessment.stage == "剔除"
    assert assessment.confidence == "阻断"


def test_missing_fund_flow_never_receives_default_positive_points() -> None:
    bars = _bars([100 + index * 0.7 for index in range(25)])
    profile = build_multi_horizon_profile(bars, market_trade_date=bars[-1].date)

    missing = assess_continuation(profile, theme_confirmed=True, fund_flow=None)
    positive = assess_continuation(profile, theme_confirmed=True, fund_flow=2.0)

    assert positive.score > missing.score

