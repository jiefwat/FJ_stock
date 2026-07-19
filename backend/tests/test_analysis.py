from datetime import UTC, date, datetime, timedelta

from marketdesk.analysis.market import analyse_market
from marketdesk.analysis.opportunities import rank_candidates
from marketdesk.analysis.stock import analyse_stock
from marketdesk.models import (
    Bar,
    DatasetMeta,
    EquityQuote,
    Freshness,
    IndexQuote,
    MarketSnapshot,
    SectorSnapshot,
)


def meta() -> DatasetMeta:
    now = datetime.now(UTC)
    return DatasetMeta(
        source="fixture", observed_at=now, fetched_at=now, freshness=Freshness.FRESH, coverage=1
    )


def equity(name: str = "示例科技", **overrides: object) -> EquityQuote:
    values: dict[str, object] = {
        "symbol": "SH.600001",
        "code": "600001",
        "name": name,
        "price": 12.0,
        "change_pct": 2.5,
        "amount": 600_000_000,
        "turnover_rate": 4.2,
        "volume_ratio": 1.5,
        "pe": 28.0,
        "pb": 3.0,
        "market_cap": 50_000_000_000,
        "net_flow": 30_000_000,
        "sector": "半导体",
    }
    values.update(overrides)
    return EquityQuote(**values)


def snapshot() -> MarketSnapshot:
    return MarketSnapshot(
        meta=meta(),
        indices=[
            IndexQuote(
                symbol="SH.000001",
                name="上证指数",
                price=3500,
                change_pct=1.2,
                amount=500_000_000_000,
            )
        ],
        equities=[
            equity(),
            equity(
                name="下跌公司",
                symbol="SZ.000002",
                code="000002",
                change_pct=-1.0,
                net_flow=-10_000_000,
            ),
        ],
        sectors=[SectorSnapshot(code="BK1", name="半导体", change_pct=2.2, net_flow=100_000_000)],
    )


def test_market_analysis_renormalizes_missing_external_factor() -> None:
    result = analyse_market(snapshot())

    available = [factor for factor in result.factors if factor.available]
    assert round(sum(factor.weight for factor in available), 6) == 1
    assert result.confidence < 1
    assert result.regime in {"risk_off", "cautious", "balanced", "risk_on"}
    assert result.factors[0].evidence == "上涨 1 / 下跌 1 / 平盘 0"


def test_opportunity_excludes_st_and_explains_score() -> None:
    result = rank_candidates([equity(), equity(name="*ST 风险")], market_regime="balanced")

    assert result.funnel["universe"] == 2
    assert result.funnel["ranked"] == 1
    assert result.excluded[0].reasons == ["special_treatment"]
    assert (
        round(sum(part.weighted_score for part in result.candidates[0].components), 2)
        == result.candidates[0].score
    )


def test_opportunity_does_not_score_missing_evidence_as_neutral() -> None:
    result = rank_candidates([equity(sector=None, net_flow=None)], market_regime="balanced")

    candidate = result.candidates[0]
    assert {part.key for part in candidate.components} == {
        "trend",
        "liquidity",
        "valuation",
    }
    assert "板块归属暂缺" in candidate.risk_flags
    assert round(sum(part.weight for part in candidate.components), 6) == 1


def test_opportunity_presets_are_distinct_and_explain_unavailable_data() -> None:
    rows = [
        equity(symbol="SH.600010", code="600010", change_pct=10.0),
        equity(symbol="SH.600011", code="600011", change_pct=3.0),
        equity(symbol="SH.600012", code="600012", change_pct=-3.0),
    ]

    trend = rank_candidates(rows, "balanced", "trend")
    oversold = rank_candidates(rows, "balanced", "oversold_rebound")
    capital = rank_candidates(
        [equity(symbol="SH.600013", code="600013", net_flow=None)],
        "balanced",
        "capital_confirmed",
    )
    sector = rank_candidates(
        [equity(symbol="SH.600014", code="600014", sector=None)],
        "balanced",
        "sector_improving",
    )

    assert [item.quote.symbol for item in trend.candidates] == ["SH.600011"]
    assert [item.quote.symbol for item in oversold.candidates] == ["SH.600012"]
    assert capital.available is False
    assert capital.unavailable_reason is not None and "资金流" in capital.unavailable_reason
    assert sector.available is False
    assert sector.unavailable_reason is not None and "行业映射" in sector.unavailable_reason


def test_risk_off_penalty_is_visible() -> None:
    candidate = rank_candidates(
        [equity(change_pct=3.0)], market_regime="risk_off", preset="trend"
    ).candidates[0]

    assert candidate.context_penalty == 15
    assert candidate.score == candidate.base_score - candidate.context_penalty
    assert candidate.evidence_coverage == 0.7


def test_capital_strategy_enforces_its_displayed_turnover_rule() -> None:
    rows = [
        equity(symbol="SH.600020", code="600020", change_pct=1.0, amount=60_000_000, net_flow=1),
        equity(symbol="SH.600021", code="600021", change_pct=1.0, amount=120_000_000, net_flow=1),
    ]

    result = rank_candidates(rows, "balanced", "capital_confirmed")

    assert [item.quote.symbol for item in result.candidates] == ["SH.600021"]


def test_sector_strategy_requires_strength_evidence_not_just_a_sector_name() -> None:
    result = rank_candidates(
        [equity(symbol="SH.600022", code="600022", change_pct=2.0, sector="银行")],
        "balanced",
        "sector_improving",
    )

    assert result.available is False
    assert result.unavailable_reason is not None and "板块强度" in result.unavailable_reason


def test_stock_analysis_is_insufficient_without_history() -> None:
    result = analyse_stock(equity(), [])
    assert result.stance == "insufficient_data"
    assert "历史行情" in result.missing_evidence


def test_stock_analysis_calculates_moving_averages() -> None:
    bars = [
        Bar(
            date=datetime(2026, 1, day, tzinfo=UTC).date(),
            open=10,
            high=11,
            low=9,
            close=float(day),
            volume=1000 + day,
            amount=10_000,
        )
        for day in range(1, 21)
    ]

    result = analyse_stock(equity(), bars)

    assert result.technical is not None
    assert result.technical.ma5 == 18.0
    assert result.technical.ma20 == 10.5


def test_stock_stance_uses_multiple_visible_factors() -> None:
    start = date(2026, 1, 1)
    bars = [
        Bar(
            date=start + timedelta(days=index),
            open=10 + index * 0.1,
            high=10.5 + index * 0.1,
            low=9.5 + index * 0.1,
            close=10 + index * 0.1,
            volume=1000 + index,
            amount=10_000 + index,
        )
        for index in range(80)
    ]

    result = analyse_stock(equity(pe=24, change_pct=2), bars)

    assert 0 < result.evidence_coverage < 1
    assert {item.key for item in result.score_factors} >= {
        "price_ma20",
        "ma5_ma20",
        "ma20_ma60",
        "rsi",
        "volatility",
        "valuation",
    }
    assert round(50 + sum(item.impact for item in result.score_factors), 2) == result.stance_score


def test_high_volatility_creates_bear_evidence() -> None:
    start = date(2026, 1, 1)
    closes = [100 + (25 if index % 2 else -20) + index * 0.2 for index in range(80)]
    bars = [
        Bar(
            date=start + timedelta(days=index),
            open=close,
            high=close + 2,
            low=close - 2,
            close=close,
            volume=1000 + index,
            amount=100_000 + index,
        )
        for index, close in enumerate(closes)
    ]

    result = analyse_stock(equity(), bars)

    assert any("波动" in item for item in result.bear_case)
