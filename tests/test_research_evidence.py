from stock_ts.research.evidence import EvidenceItem, EvidenceStatus, audit_status


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
