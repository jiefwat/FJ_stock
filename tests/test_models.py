from dataclasses import FrozenInstanceError

import pytest

from aster_market.models import IndexQuote, MarketSnapshot


def test_market_snapshot_is_immutable() -> None:
    snapshot = MarketSnapshot(
        trade_date="2026-07-18",
        generated_at="2026-07-18T15:10:00+08:00",
        source="market-snapshot",
        indices=(IndexQuote("上证指数", "000001.SH", 3501.26, 0.48),),
        advancing=2841,
        declining=2134,
        limit_up=61,
        limit_down=8,
        northbound_net_inflow=12.4,
        sectors=(),
        candidates=(),
        news=(),
    )

    assert snapshot.indices[0].pct_change == 0.48
    with pytest.raises(FrozenInstanceError):
        snapshot.trade_date = "2026-07-19"  # type: ignore[misc]
