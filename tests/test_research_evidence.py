from stock_ts.research.evidence import (
    EvidenceItem,
    EvidenceStatus,
    ResearchInputQuality,
    audit_status,
    fundamental_metric_coverage,
    has_comparable_valuation,
    has_usable_events,
)


def test_audit_status_blocks_stale_required_data() -> None:
    items = [
        EvidenceItem("行情", "tdx", "2026-07-10", EvidenceStatus.STALE, "交易日落后"),
        EvidenceItem("财务", "tushare", "2026-03-31", EvidenceStatus.COMPLETE, "季报"),
    ]

    assert audit_status(items, required={"行情"}) == EvidenceStatus.BLOCKED


def test_audit_status_degrades_when_optional_block_is_missing() -> None:
    items = [
        EvidenceItem("行情", "tdx", "2026-07-11", EvidenceStatus.COMPLETE, "日线"),
        EvidenceItem("估值", "", "", EvidenceStatus.MISSING, "缺历史分位"),
    ]

    assert audit_status(items, required={"行情"}) == EvidenceStatus.DEGRADED


def test_audit_status_is_complete_when_every_block_is_complete() -> None:
    items = [
        EvidenceItem("行情", "tdx", "2026-07-11", EvidenceStatus.COMPLETE, "日线"),
        EvidenceItem("估值", "tushare", "2026-07-11", EvidenceStatus.COMPLETE, "历史分位"),
    ]

    assert audit_status(items, required={"行情"}) == EvidenceStatus.COMPLETE


def test_research_input_quality_defaults_to_safe_empty_evidence() -> None:
    quality = ResearchInputQuality()

    assert quality.quote_status == EvidenceStatus.COMPLETE
    assert quality.fundamental_coverage == 0.0
    assert quality.valuation_comparable is False
    assert quality.event_status == EvidenceStatus.MISSING


def test_metadata_only_fundamentals_have_zero_coverage() -> None:
    assert fundamental_metric_coverage(
        {"source": "tushare", "date": "2026-03-31", "industry": "银行"}
    ) == 0.0


def test_fundamental_coverage_counts_only_numeric_quality_metrics() -> None:
    coverage = fundamental_metric_coverage(
        {"revenue_yoy": 12.0, "roe": "8.5", "gross_margin": "invalid"}
    )

    assert coverage == 2 / 6


def test_comparable_valuation_requires_valid_numeric_reference() -> None:
    assert has_comparable_valuation({"pe_percentile": 20}) is True
    assert has_comparable_valuation({"pe_percentile": 120}) is False
    assert has_comparable_valuation({"pe_ttm": 12, "industry_pe_median": 15}) is True
    assert has_comparable_valuation({"industry_pe_median": "invalid"}) is False


def test_events_require_a_non_blank_title() -> None:
    assert has_usable_events([{"title": "  "}], []) is False
    assert has_usable_events([{"title": "季度经营公告"}], []) is True
