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


def _raw_stock(*, financial: bool = False, events: bool = False) -> StockRawData:
    return StockRawData(
        code="603278",
        name="大业股份",
        bars=_bars(),
        pe_ttm=12.0,
        valuation={"pb": 1.8, "industry_pe_median": 18.0, "source": "fixture"},
        fundamental_metrics=(
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


def _build(raw: StockRawData, *, quality: ResearchInputQuality):
    from stock_ts.research.stock_dossier import build_professional_stock_dossier

    return build_professional_stock_dossier(
        raw,
        technical=_technical(),
        event_radar=_event_radar(),
        input_quality=quality,
        sector_context="高端装备",
    )


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
