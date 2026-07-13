from __future__ import annotations

from stock_ts.models import (
    CandidatePoolReport,
    CandidateStockAnalysis,
    CandidateStockRawData,
    IndexQuote,
    MarketSnapshot,
)
from stock_ts.research.evidence import EvidenceStatus
from stock_ts.research.market_regime import assess_market_regime
from stock_ts.research.opportunity_dossier import build_opportunity_dossier


def _market(*, heat: int = 68, limit_down: int = 6) -> MarketSnapshot:
    return MarketSnapshot(
        trade_date="2026-07-13",
        heat_score=heat,
        breadth_ratio=1.4,
        summary="结构活跃",
        regime="震荡轮动",
        indices=[IndexQuote("000001", "上证指数", 3500, 0.8, 5200)],
        top_sectors=[("机器人", 2.8)],
        dimensions=[],
        opportunities=[],
        risks=[],
        tomorrow_watch=[],
        limit_up_count=68,
        limit_down_count=limit_down,
        advancing_count=3200,
        declining_count=2200,
    )


def _candidate(
    code: str,
    name: str,
    sector: str,
    score: int,
    *,
    price_reliable: bool = True,
    risks: list[str] | None = None,
) -> CandidateStockAnalysis:
    return CandidateStockAnalysis(
        code=code,
        name=name,
        sector=sector,
        score=score,
        latest_close=10.0,
        pct_change=2.5,
        reasons=[f"{sector}强度靠前", "收盘位于短期均线上方"],
        risks=risks or ["短线涨幅较大，次日追高风险上升"],
        watch_conditions=["等待回踩确认"],
        price_reliable=price_reliable,
    )


def _pool() -> CandidatePoolReport:
    return CandidatePoolReport(
        trade_date="2026-07-13",
        candidates=[
            _candidate("600001", "研究股份", "机器人", 82),
            _candidate("600002", "ST风险股", "机器人", 88),
            _candidate("600003", "缺价股份", "半导体", 78, price_reliable=False),
            _candidate("600004", "观察股份", "未识别主题", 76),
        ],
        method_notes=["按趋势、量价、板块、资金和风险扣分排序"],
        disclaimer="仅用于研究排序",
        price_reliable=False,
    )


def _raw_candidates() -> list[CandidateStockRawData]:
    return [
        CandidateStockRawData(
            item.code,
            item.name,
            item.sector,
            [],
            price_reliable=item.price_reliable,
        )
        for item in _pool().candidates
    ]


def test_stale_quote_blocks_all_opportunity_candidates() -> None:
    dossier = build_opportunity_dossier(
        _pool(),
        market=assess_market_regime(_market(), quote_status=EvidenceStatus.STALE),
        quote_status=EvidenceStatus.STALE,
        candidate_universe=_raw_candidates(),
        metadata={"universe_size": "5200"},
    )

    assert dossier.gate.state == "数据暂停"
    assert dossier.gate.data_status == EvidenceStatus.STALE.value
    assert dossier.gate.eligible_count == 0
    assert dossier.gate.scanned_count == 5200
    assert all(item.state == "待补数据" for item in dossier.candidates)
    assert all(item.data_status is EvidenceStatus.STALE for item in dossier.candidates)
    assert dossier.funnel[-1].name == "可验证"
    assert dossier.funnel[-1].count == 0


def test_candidate_states_are_mutually_exclusive_when_data_is_fresh() -> None:
    pool = _pool()
    pool = CandidatePoolReport(
        trade_date=pool.trade_date,
        candidates=pool.candidates,
        method_notes=pool.method_notes,
        disclaimer=pool.disclaimer,
        price_reliable=True,
    )
    dossier = build_opportunity_dossier(
        pool,
        market=assess_market_regime(_market()),
        quote_status=EvidenceStatus.COMPLETE,
        candidate_universe=_raw_candidates(),
        metadata={"universe_size": "5200"},
    )

    assert {item.code: item.state for item in dossier.candidates} == {
        "600001": "可验证",
        "600004": "只观察",
        "600002": "风险排除",
        "600003": "待补数据",
    }
    assert len({item.code for item in dossier.candidates}) == len(dossier.candidates)
    assert dossier.gate.eligible_count == 1
    assert dossier.candidates[0].counter_evidence


def test_market_data_pause_cannot_be_relaxed_by_fresh_candidate_pool() -> None:
    pool = _pool()
    pool = CandidatePoolReport(
        trade_date=pool.trade_date,
        candidates=pool.candidates,
        method_notes=pool.method_notes,
        disclaimer=pool.disclaimer,
        price_reliable=True,
    )
    dossier = build_opportunity_dossier(
        pool,
        market=assess_market_regime(_market(), quote_status=EvidenceStatus.BLOCKED),
        quote_status=EvidenceStatus.COMPLETE,
        candidate_universe=_raw_candidates(),
        metadata={},
    )

    assert dossier.gate.state == "数据暂停"
    assert dossier.gate.risk_budget == "0%"
    assert dossier.gate.data_status == EvidenceStatus.BLOCKED.value
    assert dossier.gate.scanned_count is None
    assert all(item.state == "待补数据" for item in dossier.candidates)


def test_unreliable_candidate_pool_reports_effective_blocked_status() -> None:
    dossier = build_opportunity_dossier(
        _pool(),
        market=assess_market_regime(_market()),
        quote_status=EvidenceStatus.COMPLETE,
        candidate_universe=_raw_candidates(),
        metadata={},
    )

    assert dossier.gate.state == "数据暂停"
    assert dossier.gate.data_status == EvidenceStatus.BLOCKED.value
    assert all(item.data_status is EvidenceStatus.BLOCKED for item in dossier.candidates)
