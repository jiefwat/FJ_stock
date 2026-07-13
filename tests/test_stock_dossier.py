from __future__ import annotations

from stock_ts.models import DailyBar, Holding, NewsItem, StockRawData
from stock_ts.professional_research import EventRadar, TechnicalProfile
from stock_ts.research.evidence import EvidenceStatus, ResearchInputQuality


def _bars(count: int = 80, *, close: float = 10.0) -> list[DailyBar]:
    return [
        DailyBar(
            date=f"2026-{(index // 28) + 1:02d}-{(index % 28) + 1:02d}",
            open=close - 0.1,
            high=close + 0.2,
            low=close - 0.2,
            close=close,
            volume=1_000_000 + index * 1_000,
        )
        for index in range(count)
    ]


def _raw_stock(
    *,
    financial: bool = False,
    events: bool = False,
    close: float = 10.0,
    pe_ttm: float | None = 12.0,
    valuation: dict[str, float | str | None] | None = None,
    fundamental_metrics: dict[str, float | str | None] | None = None,
    bars: list[DailyBar] | None = None,
    fund_flow: float | None = None,
    fund_flow_detail: dict[str, float | str | None] | None = None,
    news_items: list[NewsItem] | None = None,
) -> StockRawData:
    default_metrics: dict[str, float | str | None] = (
        {
            "eps": 0.3,
            "operating_revenue": 1_000.0,
            "net_profit": 100.0,
            "operating_cash_flow": 120.0,
            "source": "fixture",
            "date": "2026-03-31",
        }
        if financial
        else {}
    )
    return StockRawData(
        code="603278",
        name="大业股份",
        bars=bars if bars is not None else _bars(close=close),
        fund_flow=fund_flow,
        pe_ttm=pe_ttm,
        valuation=(
            valuation
            if valuation is not None
            else {"pb": 1.8, "industry_pe_median": 18.0, "source": "fixture"}
        ),
        fundamental_metrics=(
            fundamental_metrics if fundamental_metrics is not None else default_metrics
        ),
        fund_flow_detail=(
            fund_flow_detail
            if fund_flow_detail is not None
            else {"source": "tdx.quote.turnover", "amount_yuan": 100_000_000.0}
        ),
        news_items=(
            news_items
            if news_items is not None
            else (
                [NewsItem("2026-07-10", "fixture", "季度经营公告", "经营保持稳定")]
                if events
                else []
            )
        ),
        data_sources=["tdx", "fixture"],
    )


def _technical() -> TechnicalProfile:
    return TechnicalProfile(
        support=9.5,
        resistance=10.8,
        invalid_line=9.4,
        ma5=10.0,
        ma10=9.9,
        ma20=9.8,
        rsi14=55.0,
        macd_status="红柱扩张，动能偏强",
        volume_ratio=1.1,
        structure="站上 20 日线",
        checkpoints=["站稳 10.80 后确认"],
    )


def _bars_from_closes(closes: list[float]) -> list[DailyBar]:
    return [
        DailyBar(
            date=f"2026-{(index // 28) + 1:02d}-{(index % 28) + 1:02d}",
            open=value * 0.99,
            high=value * 1.02,
            low=value * 0.98,
            close=value,
            volume=1_000_000 + index * 10_000,
        )
        for index, value in enumerate(closes)
    ]


def _event_radar() -> EventRadar:
    return EventRadar(
        source="fixture",
        total=1,
        returned=1,
        risk_score=20,
        gate="未见标题级风险",
        key_events=["季度经营公告"],
        review_actions=["打开公告原文复核"],
    )


def _build(
    raw: StockRawData,
    *,
    quality: ResearchInputQuality | None = None,
    holding: Holding | None = None,
):
    from stock_ts.research.stock_dossier import build_professional_stock_dossier

    return build_professional_stock_dossier(
        raw,
        technical=_technical(),
        event_radar=_event_radar(),
        holding=holding,
        input_quality=quality or ResearchInputQuality(quote_status=EvidenceStatus.COMPLETE),
        sector_context="高端装备",
    )


def _diagnostic(dossier, name: str):
    return next(item for item in dossier.diagnostics if item.name == name)


def test_complete_score_measures_evidence_not_upside() -> None:
    dossier = _build(
        _raw_stock(financial=True, events=True),
        quality=ResearchInputQuality(quote_status=EvidenceStatus.COMPLETE),
    )

    assert dossier.verdict.evidence_grade in {"A", "B"}
    assert dossier.verdict.confidence >= 70
    assert "上涨概率" not in dossier.verdict.thesis


def test_stale_quote_forces_grade_d_and_zero_confidence() -> None:
    dossier = _build(
        _raw_stock(financial=True, events=True),
        quality=ResearchInputQuality(
            quote_status=EvidenceStatus.STALE,
            blockers=("行情日期落后",),
        ),
    )

    assert dossier.verdict.stance == "数据暂停"
    assert dossier.verdict.evidence_grade == "D"
    assert dossier.verdict.confidence == 0
    assert dossier.position.position_cap == "0%"


def test_absolute_financial_snapshot_is_not_reported_missing() -> None:
    dossier = _build(
        _raw_stock(
            fundamental_metrics={
                "eps": -0.07,
                "net_asset_per_share": 5.665,
                "operating_revenue": 1_136_418.25,
                "operating_profit": -27_039.40,
                "net_profit": -24_557.60,
                "operating_cash_flow": 29_811.00,
                "source": "tdx.profile.finance",
                "date": "2026-05-18",
            }
        )
    )
    financial = _diagnostic(dossier, "财务质量")

    assert financial.status == "degraded"
    assert "亏损" in financial.conclusion
    assert "经营现金流为正" in financial.conclusion
    assert "财务数据缺失" not in financial.conclusion


def test_negative_pe_is_not_a_valuation_anchor() -> None:
    dossier = _build(_raw_stock(pe_ttm=-79.96, fundamental_metrics={"net_profit": -10.0}))
    valuation = _diagnostic(dossier, "估值")

    assert "PE 失去解释力" in valuation.conclusion
    assert "低估" not in valuation.conclusion


def test_reported_pb_conflict_is_exposed() -> None:
    dossier = _build(
        _raw_stock(
            close=10.05,
            valuation={"pb": 0.177},
            fundamental_metrics={"net_asset_per_share": 5.665},
        )
    )
    valuation = _diagnostic(dossier, "估值")

    assert valuation.status == "degraded"
    assert "来源 PB 0.18x" in valuation.conclusion
    assert "价格/每股净资产反算 1.77x" in valuation.conclusion
    assert "口径冲突" in valuation.risks


def test_one_day_rebound_after_twenty_day_damage_is_not_reversal() -> None:
    closes = [15.0] * 60 + [15.0 - index * 0.28 for index in range(19)] + [10.5]
    dossier = _build(_raw_stock(bars=_bars_from_closes(closes)))
    technical = _diagnostic(dossier, "技术结构")

    assert "反弹尝试" in technical.conclusion
    assert "趋势反转" not in technical.conclusion
    assert any("20日" in fact for fact in technical.facts)
    assert any("60日高点" in fact for fact in technical.facts)


def test_turnover_proxy_is_not_called_main_fund_flow() -> None:
    dossier = _build(
        _raw_stock(
            fund_flow=None,
            fund_flow_detail={
                "source": "tdx.quote.turnover",
                "amount_yuan": 306_457_952.0,
                "turnover_rate": 8.84,
            },
        )
    )
    capital = _diagnostic(dossier, "资金与交易")

    assert "成交活跃" in capital.conclusion
    assert "主力净流入" not in capital.conclusion
    assert "单日" in capital.limitation


def test_high_pledge_and_loss_constrain_non_holder_to_zero_position() -> None:
    raw = _raw_stock(
        fundamental_metrics={"net_profit": -24_557.6},
        news_items=[
            NewsItem(
                date="2026-05-25",
                source="fixture",
                title="控股股东累计质押占其持股65.72%",
                summary="质押融资用于公司生产经营",
                sentiment="negative",
            )
        ],
    )
    dossier = _build(raw)

    assert dossier.verdict.stance == "风险规避"
    assert dossier.position.position_cap == "0%"
    assert any(
        item.severity == "high" and item.category == "股权质押"
        for item in dossier.risks
    )
    assert "追反弹" in dossier.position.prohibited_action


def test_holder_guidance_uses_cost_without_calling_cost_bullish() -> None:
    dossier = _build(
        _raw_stock(close=9.5, financial=True, events=True),
        holding=Holding("603278", "大业股份", 1_000, 11.0, "高端装备"),
    )

    assert dossier.verdict.stance == "持仓管理"
    assert dossier.position.audience == "已持仓"
    assert "成本 11.00" in dossier.position.current_action
    assert "成本优势" not in dossier.verdict.thesis
    assert dossier.position.reduce_trigger
    assert dossier.position.invalidation


def test_decision_rail_has_exactly_five_ordered_steps() -> None:
    dossier = _build(_raw_stock(financial=True, events=True))

    assert [item.label for item in dossier.decision_steps] == [
        "当前状态",
        "转强触发",
        "加仓确认",
        "降级触发",
        "失效退出",
    ]
