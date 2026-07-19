from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from marketdesk.models import DatasetMeta, Freshness


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
