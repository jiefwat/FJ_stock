from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from marketdesk.models import (
    CapabilityState,
    CapabilityStatus,
    DatasetMeta,
    EvidenceDocument,
    Freshness,
    SourceRef,
)


def test_dataset_meta_rejects_invalid_coverage() -> None:
    now = datetime.now(UTC)

    with pytest.raises(ValidationError):
        DatasetMeta(
            source="eastmoney",
            observed_at=now,
            fetched_at=now,
            freshness=Freshness.FRESH,
            coverage=1.2,
        )


def test_dataset_meta_rejects_naive_timestamp() -> None:
    now = datetime.now(UTC)

    with pytest.raises(ValidationError):
        DatasetMeta(
            source="eastmoney",
            observed_at=datetime.now(),
            fetched_at=now,
            freshness=Freshness.FRESH,
            coverage=1.0,
        )


def test_evidence_source_requires_timezone_aware_timestamps() -> None:
    now = datetime.now(UTC)

    with pytest.raises(ValidationError):
        SourceRef(
            provider="cninfo",
            label="巨潮资讯",
            capability="filings",
            observed_at=datetime.now(),
            fetched_at=now,
            freshness=Freshness.FRESH,
        )


def test_evidence_document_rejects_unknown_kind() -> None:
    now = datetime.now(UTC)
    source = SourceRef(
        provider="eastmoney",
        label="东方财富研报",
        capability="research",
        observed_at=now,
        fetched_at=now,
        freshness=Freshness.FRESH,
    )

    with pytest.raises(ValidationError):
        EvidenceDocument(
            id="r-1",
            kind="news",
            symbol="SH.600519",
            title="贵州茅台研究",
            category="公司研究",
            publisher="测试机构",
            published_at=now,
            url="https://example.com/r-1",
            source=source,
        )


def test_capability_state_distinguishes_empty_from_unavailable() -> None:
    empty = CapabilityState(status=CapabilityStatus.EMPTY, provider="cninfo")
    unavailable = CapabilityState(
        status=CapabilityStatus.UNAVAILABLE,
        provider="cninfo",
        error="upstream timeout",
    )

    assert empty.error is None
    assert unavailable.error == "upstream timeout"
