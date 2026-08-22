from datetime import UTC, date, datetime, timedelta

from marketdesk.analysis.events import analyse_market_events
from marketdesk.analysis.holding import analyse_holding
from marketdesk.analysis.market import analyse_market
from marketdesk.analysis.market_structure import (
    analyse_market_dashboard,
    analyse_market_groups,
    build_limit_ladder,
    build_strategy_board,
)
from marketdesk.analysis.opportunities import rank_candidates
from marketdesk.analysis.stock import analyse_stock
from marketdesk.analysis.stock_intelligence import analyse_financial_health, analyse_stock_news
from marketdesk.models import (
    Bar,
    DatasetMeta,
    EquityQuote,
    FinancialPeriod,
    Freshness,
    HoldingItem,
    IndexQuote,
    MarketEventRaw,
    MarketSnapshot,
    SectorSnapshot,
    StockNewsItem,
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


def holding_item(**overrides: object) -> HoldingItem:
    now = datetime.now(UTC)
    values: dict[str, object] = {
        "id": 1,
        "symbol": "SH.688249",
        "name": "晶合集成",
        "quantity": 800,
        "cost_price": 54.7482,
        "target_weight": 0.125,
        "thesis": "来自截图批量录入：先做持仓诊断，再逐个进入个股页复核。",
        "invalidation": "若组合结论提示继续恶化或个股证据转弱，优先复核。",
        "status": "holding",
        "created_at": now,
        "updated_at": now,
    }
    values.update(overrides)
    return HoldingItem(**values)


def trending_bars(count: int = 160) -> list[Bar]:
    start = date(2025, 1, 1)
    closes = [20 + index * 0.08 + index * index * 0.0015 for index in range(count)]
    return [
        Bar(
            date=start + timedelta(days=index),
            open=close - 0.2,
            high=close + 0.6,
            low=close - 0.6,
            close=close,
            volume=1_000_000 + index * 5_000,
            amount=120_000_000 + index * 1_000_000,
        )
        for index, close in enumerate(closes)
    ]


def volatile_bars(count: int = 140) -> list[Bar]:
    start = date(2025, 1, 1)
    closes = [100 + (8 if index % 2 else -8) + index * 0.05 for index in range(count)]
    return [
        Bar(
            date=start + timedelta(days=index),
            open=close,
            high=close + 5,
            low=close - 5,
            close=close,
            volume=1_000_000 + index,
            amount=200_000_000 + index,
        )
        for index, close in enumerate(closes)
    ]


def overheated_bars(count: int = 120) -> list[Bar]:
    start = date(2025, 1, 1)
    closes = [30 + index * 0.05 for index in range(count - 1)] + [52.0]
    return [
        Bar(
            date=start + timedelta(days=index),
            open=close - 0.3,
            high=close + 0.8,
            low=close - 0.8,
            close=close,
            volume=1_000_000 if index < count - 1 else 6_000_000,
            amount=150_000_000 + index * 500_000,
        )
        for index, close in enumerate(closes)
    ]


def test_market_analysis_renormalizes_missing_external_factor() -> None:
    result = analyse_market(snapshot())

    available = [factor for factor in result.factors if factor.available]
    assert round(sum(factor.weight for factor in available), 6) == 1
    assert result.confidence < 1
    assert result.regime in {"risk_off", "cautious", "balanced", "risk_on"}
    assert result.factors[0].evidence == "上涨 1 / 下跌 1 / 平盘 0"


def test_market_dashboard_uses_one_snapshot_for_breadth_distribution_and_limits() -> None:
    source = snapshot().model_copy(
        update={
            "equities": [
                equity(change_pct=10.0, price_limit_pct=10.0, amount=800_000_000),
                equity(
                    name="下跌公司",
                    symbol="SZ.000002",
                    code="000002",
                    change_pct=-5.2,
                    price_limit_pct=10.0,
                    amount=200_000_000,
                ),
            ]
        }
    )

    result = analyse_market_dashboard(source)

    assert result.breadth_pct == 50
    assert result.total_turnover == 1_000_000_000
    assert result.limit_up_count == 1
    assert result.limit_down_count == 0
    assert sum(item.count for item in result.distribution) == 2
    assert result.meta.observed_at == source.meta.observed_at


def test_strategy_board_reuses_opportunity_presets_and_reports_evidence_confidence() -> None:
    result = build_strategy_board(snapshot())

    assert [card.id for card in result.cards[:3]] == [
        "trend",
        "volume_breakout",
        "capital_confirmed",
    ]
    assert all(card.entry_signal and card.exit_signal for card in result.cards)
    assert all(0 <= card.confidence <= 1 for card in result.cards)


def test_limit_ladder_uses_raw_daily_prices_and_keeps_st_history_unresolved() -> None:
    source = snapshot().model_copy(
        update={
            "meta": meta().model_copy(
                update={
                    "observed_at": datetime(2026, 8, 21, 7, tzinfo=UTC),
                    "fetched_at": datetime(2026, 8, 21, 7, 1, tzinfo=UTC),
                }
            ),
            "equities": [
                equity(change_pct=10.0, price_limit_pct=10.0),
                equity(
                    name="ST 示例",
                    symbol="SZ.000003",
                    code="000003",
                    change_pct=5.0,
                    price_limit_pct=5.0,
                ),
            ]
        }
    )
    bars = [
        Bar(date=date(2026, 8, 19), open=10, high=10, low=10, close=10, volume=1, amount=1),
        Bar(date=date(2026, 8, 20), open=11, high=11, low=11, close=11, volume=1, amount=1),
        Bar(date=date(2026, 8, 21), open=12.1, high=12.1, low=12.1, close=12.1, volume=1, amount=1),
    ]

    result = build_limit_ladder(
        source,
        {"SH.600001": bars, "SZ.000003": bars},
        "up",
    )

    assert result.total == 2
    assert result.max_streak == 2
    assert result.levels[0].stocks[0].one_word is True
    st_row = next(
        item for level in result.levels for item in level.stocks if item.quote.name == "ST 示例"
    )
    assert st_row.streak == 1
    assert any("历史 ST 状态" in item for item in st_row.evidence)


def test_limit_ladder_does_not_reuse_previous_day_streak_as_target_day_evidence() -> None:
    source = snapshot().model_copy(
        update={
            "meta": meta().model_copy(
                update={
                    "observed_at": datetime(2026, 8, 21, 7, tzinfo=UTC),
                    "fetched_at": datetime(2026, 8, 21, 7, 1, tzinfo=UTC),
                }
            ),
            "equities": [equity(change_pct=10.0, price_limit_pct=10.0)],
        }
    )
    delayed_bars = [
        Bar(date=date(2026, 8, 19), open=10, high=10, low=10, close=10, volume=1, amount=1),
        Bar(date=date(2026, 8, 20), open=11, high=11, low=11, close=11, volume=1, amount=1),
    ]

    result = build_limit_ladder(source, {"SH.600001": delayed_bars}, "up")
    row = result.levels[0].stocks[0]

    assert row.streak == 1
    assert row.one_word is None
    assert row.confidence == 0.4
    assert any("停在 2026-08-20" in item for item in row.evidence)


def test_group_analysis_keeps_missing_constituents_out_of_zero_statistics() -> None:
    group = SectorSnapshot(code="BK100", name="机器人", change_pct=2.5, net_flow=80_000_000)
    result = analyse_market_groups(
        meta(),
        [group],
        {"BK100": [equity(change_pct=3.0), equity(change_pct=None)]},
        "concept",
    )

    assert result.available is True
    assert result.groups[0].advancing == 1
    assert result.groups[0].declining == 0
    assert result.groups[0].average_change_pct == 3.0
    assert result.groups[0].leader is not None


def test_market_event_analysis_infers_readable_sector_names_from_news_text() -> None:
    result = analyse_market_events(
        [
            MarketEventRaw(
                id="news-1",
                title="中信证券：银行板块兼具绝对和相对收益",
                summary="低波稳健型资金关注银行板块。",
                source="fixture",
                published_at=datetime.now(UTC),
                related_sectors=["BK0475"],
            )
        ]
    )

    assert "银行" in result.summary[0]
    assert "BK0475" not in result.summary[0]
    assert "银行" in result.events[0].tags


def test_opportunity_excludes_st_and_explains_score() -> None:
    result = rank_candidates([equity(), equity(name="*ST 风险")], market_regime="balanced")

    assert result.funnel["universe"] == 2
    assert result.funnel["ranked"] == 1
    assert result.excluded[0].reasons == ["special_treatment"]
    assert (
        round(sum(part.weighted_score for part in result.candidates[0].components), 2)
        == result.candidates[0].base_score
    )
    assert result.candidates[0].score == result.candidates[0].upside_score
    assert result.candidates[0].upside_label


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


def test_opportunity_presets_are_distinct_and_effective_with_current_fields() -> None:
    rows = [
        equity(
            symbol="SH.600010",
            code="600010",
            change_pct=3.0,
            amount=400_000_000,
            pe=42,
            volume_ratio=1.1,
        ),
        equity(
            symbol="SH.600011",
            code="600011",
            change_pct=6.0,
            amount=1_200_000_000,
            pe=48,
            volume_ratio=2.1,
        ),
        equity(
            symbol="SH.600012",
            code="600012",
            change_pct=0.4,
            amount=300_000_000,
            pe=15,
            pb=1.8,
            volume_ratio=1.0,
        ),
        equity(
            symbol="SH.600013",
            code="600013",
            change_pct=-3.0,
            amount=180_000_000,
            pe=22,
            volume_ratio=0.9,
        ),
    ]

    trend = rank_candidates(rows, "balanced", "trend")
    breakout = rank_candidates(rows, "balanced", "volume_breakout")
    value = rank_candidates(rows, "balanced", "value_rebound")
    oversold = rank_candidates(rows, "balanced", "oversold_repair")

    assert {item.quote.symbol for item in trend.candidates} == {"SH.600010", "SH.600011"}
    assert [item.quote.symbol for item in breakout.candidates] == ["SH.600011"]
    assert [item.quote.symbol for item in value.candidates] == ["SH.600012"]
    assert [item.quote.symbol for item in oversold.candidates] == ["SH.600013"]
    assert all(result.available for result in [trend, breakout, value, oversold])


def test_strategy_profiles_rank_different_specialists_from_the_same_pool() -> None:
    rows = [
        equity(
            name="趋势专家",
            symbol="SH.600301",
            code="600301",
            change_pct=5.5,
            amount=300_000_000,
            turnover_rate=1.5,
            volume_ratio=1.0,
            net_flow=20_000_000,
            pe=40,
            sector="冷门板块",
        ),
        equity(
            name="资金专家",
            symbol="SH.600302",
            code="600302",
            change_pct=0.5,
            amount=300_000_000,
            turnover_rate=1.5,
            volume_ratio=1.0,
            net_flow=150_000_000,
            pe=40,
            sector="中性板块",
        ),
        equity(
            name="板块专家",
            symbol="SH.600303",
            code="600303",
            change_pct=2.5,
            amount=300_000_000,
            turnover_rate=1.5,
            volume_ratio=1.0,
            net_flow=20_000_000,
            pe=40,
            sector="强势板块",
        ),
    ]
    sector_strength = {"冷门板块": -2.0, "中性板块": 0.0, "强势板块": 5.0}

    trend = rank_candidates(rows, "balanced", "trend", sector_strength=sector_strength)
    capital = rank_candidates(
        rows, "balanced", "capital_confirmed", sector_strength=sector_strength
    )
    sector = rank_candidates(rows, "balanced", "sector_momentum", sector_strength=sector_strength)

    assert trend.candidates[0].quote.name == "趋势专家"
    assert capital.candidates[0].quote.name == "资金专家"
    assert sector.candidates[0].quote.name == "板块专家"
    assert (
        len(
            {
                trend.candidates[0].quote.symbol,
                capital.candidates[0].quote.symbol,
                sector.candidates[0].quote.symbol,
            }
        )
        == 3
    )


def test_sector_strategy_requires_matching_strength_when_snapshot_is_available() -> None:
    rows = [
        equity(
            name="板块已覆盖",
            symbol="SH.600304",
            code="600304",
            sector="强势板块",
        ),
        equity(
            name="板块未覆盖",
            symbol="SH.600305",
            code="600305",
            sector="未知板块",
        ),
    ]

    result = rank_candidates(
        rows,
        "balanced",
        "sector_momentum",
        sector_strength={"强势板块": 3.0},
    )

    assert [item.quote.name for item in result.candidates] == ["板块已覆盖"]
    assert result.candidates[0].strategy_validation.checks[1] == "板块强度已覆盖"
    assert result.excluded[0].reasons == ["sector_strength_missing"]


def test_opportunity_candidates_include_history_confirmation() -> None:
    rows = [
        equity(symbol="SH.600040", code="600040", name="稳健趋势", change_pct=3.0),
        equity(symbol="SH.600041", code="600041", name="过热趋势", change_pct=3.1),
    ]

    result = rank_candidates(
        rows,
        "balanced",
        "trend",
        history_by_symbol={
            "SH.600040": trending_bars(120),
            "SH.600041": overheated_bars(),
        },
    )

    assert result.candidates[0].quote.symbol == "SH.600040"
    stable = result.candidates[0]
    overheated = next(item for item in result.candidates if item.quote.symbol == "SH.600041")
    assert stable.history_check is not None
    assert stable.history_check.available is True
    assert stable.history_check.lookback_days == 120
    assert stable.evidence_coverage == 0.9
    assert any(part.key == "history_confirmation" for part in stable.components)
    assert any(item.key == "history_confirmation" for item in stable.dimensions)
    assert overheated.history_check is not None
    assert "远离MA20，追高风险" in overheated.risk_flags


def test_risk_off_penalty_is_visible() -> None:
    candidate = rank_candidates(
        [equity(change_pct=3.0)], market_regime="risk_off", preset="trend"
    ).candidates[0]

    assert candidate.context_penalty == 15
    assert candidate.score == candidate.upside_score
    assert candidate.score < candidate.base_score
    assert candidate.evidence_coverage == 0.7


def test_volume_breakout_strategy_enforces_its_displayed_turnover_rule() -> None:
    rows = [
        equity(
            symbol="SH.600020", code="600020", change_pct=2.0, amount=300_000_000, volume_ratio=2.0
        ),
        equity(
            symbol="SH.600021", code="600021", change_pct=2.0, amount=650_000_000, volume_ratio=2.0
        ),
    ]

    result = rank_candidates(rows, "balanced", "volume_breakout")

    assert [item.quote.symbol for item in result.candidates] == ["SH.600021"]


def test_value_rebound_strategy_does_not_require_sector_mapping() -> None:
    result = rank_candidates(
        [equity(symbol="SH.600022", code="600022", change_pct=0.2, pe=18, pb=2.0, sector=None)],
        "balanced",
        "value_rebound",
    )

    assert result.available is True
    assert [item.quote.symbol for item in result.candidates] == ["SH.600022"]
    assert "板块归属暂缺" in result.candidates[0].risk_flags


def test_additional_strategies_are_strictly_validated() -> None:
    rows = [
        equity(
            symbol="SH.600101",
            code="600101",
            change_pct=2.2,
            amount=700_000_000,
            net_flow=45_000_000,
        ),
        equity(
            symbol="SH.600102",
            code="600102",
            change_pct=2.2,
            amount=700_000_000,
            net_flow=-5_000_000,
        ),
    ]

    result = rank_candidates(rows, "balanced", "capital_confirmed")

    assert [item.quote.symbol for item in result.candidates] == ["SH.600101"]
    assert result.candidates[0].strategy_validation.passed is True
    assert "资金净流入 >= 2000 万" in result.candidates[0].strategy_validation.checks
    assert any(item.key == "strategy_validation" for item in result.candidates[0].dimensions)
    assert "capital_not_confirmed" in result.excluded[0].reasons


def test_new_effective_strategy_presets_use_available_quote_fields() -> None:
    assert [
        item.quote.symbol
        for item in rank_candidates(
            [
                equity(
                    symbol="SH.600201",
                    code="600201",
                    change_pct=1.6,
                    sector="半导体",
                    amount=700_000_000,
                    volume_ratio=1.2,
                ),
                equity(
                    symbol="SH.600299",
                    code="600299",
                    change_pct=1.6,
                    sector=None,
                    amount=700_000_000,
                ),
            ],
            "balanced",
            "sector_momentum",
        ).candidates
    ] == ["SH.600201"]
    assert [
        item.quote.symbol
        for item in rank_candidates(
            [
                equity(
                    symbol="SH.600202",
                    code="600202",
                    change_pct=-1.2,
                    net_flow=8_000_000,
                    amount=260_000_000,
                    pe=22,
                ),
                equity(
                    symbol="SH.600298",
                    code="600298",
                    change_pct=-1.2,
                    net_flow=-8_000_000,
                    amount=260_000_000,
                ),
            ],
            "balanced",
            "pullback_support",
        ).candidates
    ] == ["SH.600202"]
    assert [
        item.quote.symbol
        for item in rank_candidates(
            [
                equity(
                    symbol="SH.600203",
                    code="600203",
                    change_pct=0.6,
                    pe=18,
                    pb=1.8,
                    market_cap=18_000_000_000,
                    amount=220_000_000,
                ),
                equity(
                    symbol="SH.600297",
                    code="600297",
                    change_pct=0.6,
                    pe=38,
                    pb=1.8,
                    market_cap=18_000_000_000,
                    amount=220_000_000,
                ),
            ],
            "balanced",
            "quality_value",
        ).candidates
    ] == ["SH.600203"]
    assert [
        item.quote.symbol
        for item in rank_candidates(
            [
                equity(
                    symbol="SH.600204",
                    code="600204",
                    change_pct=1.1,
                    market_cap=90_000_000_000,
                    amount=900_000_000,
                    turnover_rate=2.0,
                    pe=24,
                ),
                equity(
                    symbol="SH.600296",
                    code="600296",
                    change_pct=1.1,
                    market_cap=9_000_000_000,
                    amount=900_000_000,
                    turnover_rate=2.0,
                    pe=24,
                ),
            ],
            "balanced",
            "large_cap_stability",
        ).candidates
    ] == ["SH.600204"]


def test_financial_health_rewards_profitable_growth_with_sound_cash_conversion() -> None:
    health = analyse_financial_health(
        [
            FinancialPeriod(
                report_date=date(2026, 6, 30),
                report_label="2026中报",
                report_type="中报",
                revenue_yoy=10.2,
                net_profit_yoy=12.5,
                roe=16.8,
                gross_margin=42.0,
                operating_cash_flow_per_share=1.3,
                cash_receipts_to_revenue=104.0,
                debt_to_assets=35.0,
            )
        ]
    )

    assert health.available is True
    assert health.score is not None and health.score >= 65
    assert 0 < health.score_impact <= 6
    assert health.report_date == date(2026, 6, 30)


def test_financial_health_penalizes_profit_cash_and_leverage_risks() -> None:
    health = analyse_financial_health(
        [
            FinancialPeriod(
                report_date=date(2026, 6, 30),
                report_label="2026中报",
                report_type="中报",
                revenue_yoy=2.0,
                net_profit_yoy=-38.0,
                roe=3.0,
                operating_cash_flow_per_share=-0.2,
                cash_receipts_to_revenue=55.0,
                debt_to_assets=76.0,
            )
        ]
    )

    assert -10 <= health.score_impact < 0
    assert any("盈利" in item for item in health.risks)
    assert any("现金" in item for item in health.risks)
    assert any("负债" in item for item in health.risks)


def test_financial_health_does_not_treat_missing_values_as_zero() -> None:
    health = analyse_financial_health(
        [
            FinancialPeriod(
                report_date=date(2026, 6, 30),
                report_label="2026中报",
                report_type="中报",
            )
        ]
    )

    assert health.available is True
    assert health.score is None
    assert health.score_impact == 0
    assert health.risks == []


def test_financial_health_detects_multi_period_growth_slowdown() -> None:
    health = analyse_financial_health(
        [
            FinancialPeriod(
                report_date=date(2026, 6, 30),
                report_label="2026中报",
                report_type="中报",
                revenue_yoy=2.0,
                net_profit_yoy=3.0,
                operating_cash_flow_per_share=1.0,
            ),
            FinancialPeriod(
                report_date=date(2026, 3, 31),
                report_label="2026一季报",
                report_type="一季报",
                revenue_yoy=12.0,
                net_profit_yoy=16.0,
                operating_cash_flow_per_share=0.8,
            ),
            FinancialPeriod(
                report_date=date(2025, 12, 31),
                report_label="2025年报",
                report_type="年报",
                revenue_yoy=18.0,
                net_profit_yoy=24.0,
                operating_cash_flow_per_share=2.0,
            ),
        ]
    )

    assert "营业收入增速连续放缓" in health.risks
    assert "盈利增速连续放缓" in health.risks
    assert health.score_impact <= 1


def stock_news_item(
    title: str,
    *,
    published_at: datetime,
    summary: str = "",
) -> StockNewsItem:
    return StockNewsItem(
        id=f"news:{title}",
        title=title,
        summary=summary,
        media="测试媒体",
        url="https://example.com/news",
        published_at=published_at,
    )


def test_stock_news_only_penalizes_recent_explicit_hard_risks() -> None:
    now = datetime(2026, 8, 16, 12, tzinfo=UTC)
    sentiment = analyse_stock_news(
        [
            stock_news_item("公司被证监会立案调查", published_at=now - timedelta(days=2)),
            stock_news_item("行业需求短期承压", published_at=now - timedelta(days=3)),
            stock_news_item("公司订单增长", published_at=now - timedelta(days=4)),
            stock_news_item("公司收到监管处罚", published_at=now - timedelta(days=45)),
        ],
        now=now,
    )

    assert sentiment.available is True
    assert sentiment.hard_risk_count == 1
    assert -6 <= sentiment.score_impact < 0
    assert len(sentiment.items) == 3
    assert next(item for item in sentiment.items if "立案" in item.title).hard_risk is True
    assert next(item for item in sentiment.items if "承压" in item.title).hard_risk is False


def test_positive_stock_news_never_raises_the_stock_score() -> None:
    now = datetime(2026, 8, 16, 12, tzinfo=UTC)
    sentiment = analyse_stock_news(
        [stock_news_item("公司订单增长并获批新产品", published_at=now)],
        now=now,
    )

    assert sentiment.positive_count == 1
    assert sentiment.score_impact == 0


def test_stock_news_deduplicates_the_same_syndicated_event() -> None:
    now = datetime(2026, 8, 16, 12, tzinfo=UTC)
    sentiment = analyse_stock_news(
        [
            stock_news_item("公司被证监会立案调查", published_at=now - timedelta(hours=2)),
            stock_news_item("公司被证监会立案调查！", published_at=now - timedelta(hours=3)),
        ],
        now=now,
    )

    assert sentiment.hard_risk_count == 1
    assert sentiment.negative_count == 1
    assert len(sentiment.items) == 1
    assert sentiment.score_impact == -3


def test_stock_analysis_is_insufficient_without_history() -> None:
    result = analyse_stock(equity(), [])
    assert result.stance == "insufficient_data"
    assert "证据不足" in result.conclusion
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


def test_stock_analysis_adds_independent_momentum_and_risk_factors() -> None:
    result = analyse_stock(equity(pe=22), trending_bars())

    assert result.technical is not None
    assert result.technical.macd_histogram is not None
    assert result.technical.atr_pct is not None
    assert result.technical.bollinger_position is not None
    assert result.technical.max_drawdown60 is not None
    assert {factor.key for factor in result.score_factors} >= {
        "macd_momentum",
        "atr_risk",
        "bollinger_position",
        "drawdown_risk",
    }
    assert any(item.key == "signal_confluence" for item in result.analysis_dimensions)


def test_historical_validation_is_descriptive_and_does_not_change_live_score() -> None:
    result = analyse_stock(equity(pe=22), trending_bars())
    expected_score = round(
        max(0, min(100, 50 + sum(item.impact for item in result.score_factors))), 2
    )

    assert result.stance_score == expected_score
    assert result.signal_validation.available is True
    assert result.signal_validation.horizon_days == 20
    assert result.signal_validation.sample_count >= 3
    assert "MA5/MA20 与 MACD 共振条件" in result.signal_validation.summary
    assert "不直接计入实时评分" in result.signal_validation.summary


def test_short_history_returns_unavailable_validation() -> None:
    result = analyse_stock(equity(), trending_bars(30))

    assert result.signal_validation.available is False
    assert result.signal_validation.sample_count == 0


def test_macd_roundoff_near_zero_is_not_treated_as_negative_momentum() -> None:
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

    result = analyse_stock(equity(), bars)
    momentum = next(item for item in result.score_factors if item.key == "macd_momentum")

    assert momentum.impact == 0
    assert "接近零" in momentum.evidence


def test_atr_changes_stop_and_caps_position_for_high_volatility() -> None:
    bars = volatile_bars()
    result = analyse_stock(equity(price=bars[-1].close, pe=22), bars)

    assert result.technical and result.technical.atr_pct
    assert result.technical.atr_pct > 5
    assert "ATR" in result.investment_advice.stop_loss
    assert "5%" in result.investment_advice.position_hint
    risk_control = next(item for item in result.analysis_dimensions if item.key == "risk_controls")
    assert "ATR" in risk_control.summary


def test_atr_target_is_used_when_resistance_is_not_above_price() -> None:
    start = date(2026, 1, 1)
    closes = [100.0] * 79 + [120.0]
    bars = [
        Bar(
            date=start + timedelta(days=index),
            open=close,
            high=close + 1,
            low=close - 1,
            close=close,
            volume=1_000_000 + index,
            amount=200_000_000 + index,
        )
        for index, close in enumerate(closes)
    ]

    result = analyse_stock(equity(price=120, pe=22), bars)

    assert "ATR" in result.investment_advice.take_profit


def test_stock_analysis_generates_a_conclusion_from_visible_evidence() -> None:
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

    result = analyse_stock(equity(pe=24, change_pct=8.5, sector=None, net_flow=None), bars)

    assert result.conclusion.startswith("总结论：")
    assert "观察" in result.conclusion
    assert "收盘价位于 20 日均线之上" in result.conclusion
    assert "当日涨幅 8.5% 偏高" in result.conclusion
    assert "跌破近 20 日支撑" in result.conclusion
    assert "个股行业映射、资金流数据" in result.conclusion


def test_stock_analysis_returns_future_trend_forecast() -> None:
    start = date(2026, 1, 1)
    bars = [
        Bar(
            date=start + timedelta(days=index),
            open=20 + index * 0.2,
            high=20.5 + index * 0.2,
            low=19.5 + index * 0.2,
            close=20 + index * 0.2,
            volume=1000 + index,
            amount=10_000 + index,
        )
        for index in range(80)
    ]

    result = analyse_stock(equity(pe=24, change_pct=2, net_flow=60_000_000), bars)

    assert result.trend_forecast.horizon == "未来 1-4 周"
    assert result.trend_forecast.direction in {"震荡上行", "偏强震荡"}
    assert result.trend_forecast.confidence > 0.5
    assert "MA5/MA20" in result.trend_forecast.summary
    assert len(result.trend_forecast.drivers) >= 3
    assert result.trend_forecast.invalidation


def test_holding_conclusion_leads_with_action_and_key_reasons() -> None:
    result = analyse_holding(
        holding_item(),
        equity(
            name="晶合集成",
            symbol="SH.688249",
            code="688249",
            price=43.4,
            change_pct=-1.1,
            pe=120.6,
            pb=4.4,
            amount=450_000_000,
            turnover_rate=2.8,
            net_flow=-20_000_000,
        ),
        total_market_value=270_233,
    )

    assert result.action == "exit_watch"
    assert result.conclusion.startswith("建议动作：优先减仓或止损")
    assert "分析维度：" not in result.conclusion
    assert "亏损 -20.73% 已触发风控" in result.conclusion
    assert "估值压力偏高，PE 120.60" in result.conclusion
    assert "建议优先减仓或止损" in result.conclusion
    assert "当前盈亏" not in result.conclusion
    assert "持仓数量 800 股" not in result.conclusion


def test_holding_conclusion_does_not_add_from_target_gap() -> None:
    result = analyse_holding(
        holding_item(
            symbol="SH.600001",
            name="示例科技",
            quantity=1000,
            cost_price=10,
            target_weight=0.3,
            thesis="趋势仍在，等待回踩后补仓。",
            invalidation="跌破中期支撑。",
        ),
        equity(price=12, pe=18, pb=2.0, net_flow=30_000_000),
        total_market_value=120_000,
    )

    assert result.action == "hold"
    assert result.conclusion.startswith("建议动作：继续持有")
    assert "分析维度：" not in result.conclusion
    assert "不使用目标比例" in result.conclusion
    assert "估值相对温和" in result.conclusion
    assert "可加仓" not in result.conclusion


def test_holding_exit_watch_never_suggests_adding_when_under_target() -> None:
    result = analyse_holding(
        holding_item(
            symbol="SH.600002",
            name="风控样本",
            quantity=4300,
            cost_price=5.7226,
            target_weight=0.125,
            thesis="等待修复。",
            invalidation="跌破成本后风控复核。",
        ),
        equity(symbol="SH.600002", code="600002", name="风控样本", price=3.73, change_pct=-6.98),
        total_market_value=270_233,
    )

    assert result.action == "exit_watch"
    assert result.rebalance_quantity is None
    assert "建议优先减仓或止损" in result.conclusion
    assert "可加仓" not in result.conclusion
    assert "补仓约" not in result.conclusion
    assert all(
        "可加仓" not in action and "补足目标仓位" not in action for action in result.next_actions
    )


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


def test_stock_analysis_returns_rich_dimension_cards_and_next_actions() -> None:
    start = date(2026, 1, 1)
    bars = [
        Bar(
            date=start + timedelta(days=index),
            open=100 + index * 0.8,
            high=102 + index * 0.8,
            low=98 + index * 0.8,
            close=100 + index * 0.8,
            volume=1_000_000 + index * 10_000,
            amount=120_000_000 + index * 1_000_000,
        )
        for index in range(80)
    ]

    result = analyse_stock(
        equity(
            pe=24,
            pb=4.2,
            change_pct=2.2,
            amount=850_000_000,
            turnover_rate=3.4,
            volume_ratio=1.6,
            net_flow=48_000_000,
            sector="白酒",
        ),
        bars,
        research_evidence=["公告显示现金分红稳定", "研报关注渠道库存修复"],
    )

    dimension_keys = {item.key for item in result.analysis_dimensions}
    assert dimension_keys >= {
        "trend",
        "risk_reward",
        "valuation",
        "liquidity",
        "capital_flow",
        "sector",
        "research",
    }
    assert any("风险收益比" in item.summary for item in result.analysis_dimensions)
    assert any(
        "放量" in item.summary or "成交额" in item.summary for item in result.analysis_dimensions
    )
    assert result.next_actions
    assert "技术面" in result.conclusion
    assert "估值" in result.conclusion
    assert "流动性" in result.conclusion
    assert "资金" in result.conclusion
    assert "下一步" in result.conclusion
    assert "研究逻辑" not in result.conclusion


def test_stock_analysis_includes_non_technical_research_dimensions() -> None:
    start = date(2026, 1, 1)
    bars = [
        Bar(
            date=start + timedelta(days=index),
            open=80 + index * 0.35,
            high=82 + index * 0.35,
            low=78 + index * 0.35,
            close=80 + index * 0.35,
            volume=1_000_000 + index * 20_000,
            amount=220_000_000 + index * 2_000_000,
        )
        for index in range(90)
    ]

    result = analyse_stock(
        equity(
            name="多维研究样本",
            pe=18,
            pb=2.4,
            amount=900_000_000,
            turnover_rate=4.1,
            volume_ratio=1.7,
            market_cap=88_000_000_000,
            net_flow=96_000_000,
            sector="高端制造",
        ),
        bars,
        research_evidence=["公告提示订单同比改善", "研报关注毛利率修复", "行业政策催化延续"],
    )

    keys = {item.key for item in result.analysis_dimensions}
    assert keys >= {
        "fundamental_quality",
        "catalyst",
        "capital_flow",
        "sector",
        "liquidity",
        "risk_controls",
    }
    assert len(result.analysis_dimensions) >= 10
    assert len(result.next_actions) >= 5
    assert "基本面" in result.conclusion
    assert "催化" in result.conclusion
    assert "处理纪律" in result.conclusion


def test_stock_analysis_returns_direct_advice_and_comparisons() -> None:
    start = date(2026, 1, 1)
    bars = [
        Bar(
            date=start + timedelta(days=index),
            open=100 + index * 0.9,
            high=102 + index * 0.9,
            low=98 + index * 0.9,
            close=100 + index * 0.9,
            volume=1_000_000 + index * 8_000,
            amount=180_000_000 + index * 2_000_000,
        )
        for index in range(130)
    ]
    peers = [
        equity(
            symbol="SH.600001",
            code="600001",
            name="目标股",
            sector="白酒",
            pe=22,
            amount=900_000_000,
            change_pct=2.6,
            net_flow=80_000_000,
        ),
        equity(
            symbol="SH.600002",
            code="600002",
            name="同业A",
            sector="白酒",
            pe=35,
            amount=300_000_000,
            change_pct=0.4,
            net_flow=-20_000_000,
        ),
        equity(
            symbol="SH.600003",
            code="600003",
            name="同业B",
            sector="白酒",
            pe=18,
            amount=600_000_000,
            change_pct=1.1,
            net_flow=10_000_000,
        ),
        equity(
            symbol="SH.600004",
            code="600004",
            name="异业",
            sector="半导体",
            pe=55,
            amount=1_200_000_000,
            change_pct=5.0,
            net_flow=30_000_000,
        ),
    ]

    result = analyse_stock(
        peers[0], bars, research_evidence=["研报提示需求修复"], peer_quotes=peers
    )

    assert result.investment_advice.action in {"可小仓试错", "持有观察", "等待回踩", "暂不参与"}
    assert result.investment_advice.position_hint
    assert result.investment_advice.entry_plan
    assert result.investment_advice.stop_loss
    assert result.investment_advice.take_profit
    assert "不是保证收益" in result.investment_advice.disclaimer
    horizontal_keys = {item.key for item in result.horizontal_comparison}
    vertical_keys = {item.key for item in result.vertical_comparison}
    assert horizontal_keys >= {
        "sector_change_rank",
        "sector_pe_position",
        "sector_liquidity_rank",
        "sector_capital_rank",
    }
    assert vertical_keys >= {"return_20d", "return_60d", "drawdown_60d", "range_position_60d"}
    assert any(
        "同业" in item.summary or "行业" in item.summary for item in result.horizontal_comparison
    )
    assert any("过去 60 日" in item.summary for item in result.vertical_comparison)
    assert "处理意见" in result.conclusion
    assert "横向对比" in result.conclusion
    assert "纵向对比" in result.conclusion


def test_stock_vertical_comparison_marks_far_above_ma20_as_chase_risk() -> None:
    start = date(2026, 1, 1)
    closes = [100.0 for _ in range(79)] + [120.0]
    bars = [
        Bar(
            date=start + timedelta(days=index),
            open=close,
            high=close + 1,
            low=close - 1,
            close=close,
            volume=1_000_000 + index,
            amount=200_000_000 + index,
        )
        for index, close in enumerate(closes)
    ]

    result = analyse_stock(equity(price=120), bars)
    ma20_distance = next(item for item in result.vertical_comparison if item.key == "ma20_distance")

    assert ma20_distance.signal == "negative"
    assert "追高" in ma20_distance.summary


def test_stock_conclusion_does_not_repeat_section_labels() -> None:
    start = date(2026, 1, 1)
    bars = [
        Bar(
            date=start + timedelta(days=index),
            open=100 + index,
            high=102 + index,
            low=98 + index,
            close=100 + index,
            volume=1_000_000 + index,
            amount=200_000_000 + index,
        )
        for index in range(80)
    ]

    result = analyse_stock(
        equity(pe=19, pb=5, amount=700_000_000, net_flow=-100_000_000, sector="白酒"), bars
    )

    assert "技术面：技术面" not in result.conclusion
    assert "估值：估值" not in result.conclusion
    assert "流动性：流动性" not in result.conclusion
    assert "资金/行业：资金：" not in result.conclusion


def test_opportunity_result_has_strategy_diagnostics_and_candidate_playbook() -> None:
    rows = [
        equity(
            symbol="SH.600030",
            code="600030",
            change_pct=3.2,
            amount=680_000_000,
            net_flow=26_000_000,
            sector="券商",
        ),
        equity(
            symbol="SH.600031",
            code="600031",
            change_pct=9.2,
            amount=900_000_000,
            net_flow=30_000_000,
            sector="机械",
        ),
        equity(
            symbol="SH.600032",
            code="600032",
            change_pct=-2.0,
            amount=120_000_000,
            net_flow=-5_000_000,
            sector=None,
        ),
    ]

    result = rank_candidates(rows, "cautious", "trend")

    assert result.summary
    assert {item.key for item in result.diagnostics} >= {
        "market_fit",
        "selection_pressure",
        "data_quality",
        "risk_control",
    }
    assert result.next_actions
    candidate = result.candidates[0]
    assert candidate.thesis.startswith("趋势延续线索")
    assert "系统会继续复查完整个股判断" in candidate.thesis
    assert {item.key for item in candidate.dimensions} >= {
        "future_probability",
        "trend_persistence",
        "upside_space",
        "timing_quality",
        "trigger",
        "confirmation",
        "risk_control",
        "execution",
    }
    assert candidate.upside_summary.startswith(candidate.upside_label)
    assert candidate.upside_drivers or candidate.upside_risks
    assert candidate.invalidation
    assert candidate.next_actions
    assert "环境" in candidate.next_actions[0] or candidate.context_penalty > 0


def test_opportunity_candidate_thesis_has_clean_readable_punctuation() -> None:
    result = rank_candidates(
        [equity(change_pct=3.2, amount=680_000_000, net_flow=26_000_000)], "balanced", "trend"
    )

    assert result.candidates[0].thesis.startswith("趋势延续线索：价格变化")
    assert "系统会继续复查完整个股判断" in result.candidates[0].thesis
    assert "：，" not in result.candidates[0].thesis


def test_opportunity_candidate_has_multi_dimension_decision_playbook() -> None:
    result = rank_candidates(
        [
            equity(
                symbol="SH.600040",
                code="600040",
                change_pct=2.8,
                amount=980_000_000,
                turnover_rate=4.8,
                volume_ratio=1.9,
                pe=22,
                pb=2.8,
                market_cap=60_000_000_000,
                net_flow=88_000_000,
                sector="机器人",
            )
        ],
        "balanced",
        "trend",
    )

    candidate = result.candidates[0]
    keys = {item.key for item in candidate.dimensions}
    assert keys >= {
        "future_probability",
        "trend_persistence",
        "upside_space",
        "timing_quality",
        "trigger",
        "confirmation",
        "capital_flow",
        "sector_context",
        "liquidity_depth",
        "valuation_fit",
        "catalyst_check",
        "follow_up_plan",
    }
    assert len(candidate.next_actions) >= 5
    assert any("公告" in action or "研报" in action for action in candidate.next_actions)


def test_holding_analysis_uses_quantity_and_cost_without_target_rebalance() -> None:
    from marketdesk.analysis.holding import analyse_holding
    from marketdesk.models import HoldingItem

    now = datetime.now(UTC)
    item = HoldingItem(
        id=1,
        symbol="SH.600519",
        name="贵州茅台",
        quantity=100,
        cost_price=1400,
        target_weight=0.4,
        thesis="现金流稳定",
        invalidation="跌破成本价",
        status="holding",
        created_at=now,
        updated_at=now,
    )
    quote = equity(symbol="SH.600519", code="600519", name="贵州茅台", price=1500)

    result = analyse_holding(item, quote, total_market_value=150_000)

    assert result.market_value == 150_000
    assert result.cost_value == 140_000
    assert result.pnl == 10_000
    assert result.pnl_pct == 7.14
    assert result.target_market_value is None
    assert result.rebalance_value is None
    assert result.rebalance_quantity is None
    assert result.break_even_price == 1400
    assert result.price_gap_to_cost_pct == 7.14
    assert {item.key for item in result.analysis_dimensions} >= {
        "position",
        "cost",
        "risk",
    }
    assert "rebalance" not in {item.key for item in result.analysis_dimensions}
    assert result.conclusion.startswith("建议动作：继续持有")
    assert "分析维度：" not in result.conclusion
    assert "不使用目标比例" in result.conclusion
    assert "盈亏 +7.14% 未触发止损" in result.conclusion
    assert "持仓数量 100 股" not in result.conclusion
    assert "成本价 1400.00" not in result.conclusion
    assert "建议先减仓" not in result.conclusion


def test_holding_analysis_splits_total_daily_three_day_and_five_day_pnl() -> None:
    start = date(2026, 1, 1)
    bars = [
        Bar(
            date=start + timedelta(days=index),
            open=100 + index,
            high=101 + index,
            low=99 + index,
            close=100 + index,
            volume=1000,
            amount=10_000,
        )
        for index in range(6)
    ]

    result = analyse_holding(
        holding_item(quantity=100, cost_price=90, target_weight=0.2),
        equity(price=110, change_pct=10),
        total_market_value=110_000,
        bars=bars,
    )

    assert result.pnl == 2000
    assert result.pnl_pct == 22.22
    assert result.day_pnl == 1000
    assert result.day_pnl_pct == 10
    assert result.three_day_pnl == 800
    assert result.three_day_pnl_pct == 7.84
    assert result.five_day_pnl == 1000
    assert result.five_day_pnl_pct == 10
    assert [change.date for change in result.recent_daily_changes] == [
        date(2026, 1, 2),
        date(2026, 1, 3),
        date(2026, 1, 4),
        date(2026, 1, 5),
        date(2026, 1, 6),
    ]
    assert [change.change_pct for change in result.recent_daily_changes] == [
        1.0,
        0.99,
        0.98,
        0.97,
        0.96,
    ]


def test_holding_analysis_adds_portfolio_context_and_non_kline_advice() -> None:
    from marketdesk.analysis.holding import analyse_holding
    from marketdesk.models import HoldingItem

    now = datetime.now(UTC)
    item = HoldingItem(
        id=2,
        symbol="SZ.000001",
        name="平安银行",
        quantity=3000,
        cost_price=10,
        target_weight=0.2,
        thesis="低估值修复与分红稳定",
        invalidation="净息差继续恶化",
        status="holding",
        created_at=now,
        updated_at=now,
    )
    quote = equity(
        symbol="SZ.000001",
        code="000001",
        name="平安银行",
        price=11,
        pe=6.2,
        pb=0.55,
        amount=1_200_000_000,
        turnover_rate=1.8,
        net_flow=-120_000_000,
        sector="银行",
    )

    result = analyse_holding(item, quote, total_market_value=300_000)

    keys = {item.key for item in result.analysis_dimensions}
    assert keys >= {"liquidity", "valuation", "sector_context", "thesis_quality"}
    assert len(result.analysis_dimensions) >= 7
    assert len(result.next_actions) >= 5
    assert any("资金流" in action for action in result.next_actions)
    assert "估值" in result.conclusion
    assert "板块" in result.conclusion
