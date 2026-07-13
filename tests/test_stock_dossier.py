from __future__ import annotations

from stock_ts.models import DailyBar, NewsItem, StockRawData
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
        bars=_bars(close=close),
        pe_ttm=pe_ttm,
        valuation=(
            valuation
            if valuation is not None
            else {"pb": 1.8, "industry_pe_median": 18.0, "source": "fixture"}
        ),
        fundamental_metrics=(
            fundamental_metrics if fundamental_metrics is not None else default_metrics
        ),
        fund_flow_detail={"source": "tdx.quote.turnover", "amount_yuan": 100_000_000.0},
        news_items=(
            [NewsItem("2026-07-10", "fixture", "季度经营公告", "经营保持稳定")] if events else []
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


def _build(raw: StockRawData, *, quality: ResearchInputQuality | None = None):
    from stock_ts.research.stock_dossier import build_professional_stock_dossier

    return build_professional_stock_dossier(
        raw,
        technical=_technical(),
        event_radar=_event_radar(),
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
