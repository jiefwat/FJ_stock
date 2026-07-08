from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class DataSourceAttempt:
    source: str
    ok: bool
    reason: str = ""
    latency_ms: int = 0
    fields: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"source": self.source, "ok": self.ok}
        if self.reason:
            payload["reason"] = self.reason
        if self.latency_ms:
            payload["latency_ms"] = self.latency_ms
        if self.fields:
            payload["fields"] = list(self.fields)
        return payload


@dataclass(frozen=True)
class DataQualitySummary:
    primary_source: str
    data_quality: str
    missing_fields: list[str]
    fallback_from: list[str]
    attempts: list[DataSourceAttempt]
    stale_seconds: int | None = None

    def is_degraded(self) -> bool:
        return self.data_quality in {"partial", "poor", "stale"}

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "primary_source": self.primary_source,
            "data_quality": self.data_quality,
            "missing_fields": list(self.missing_fields),
            "fallback_from": list(self.fallback_from),
            "attempts": [attempt.to_payload() for attempt in self.attempts],
        }
        if self.stale_seconds is not None:
            payload["stale_seconds"] = self.stale_seconds
        return payload


def summarize_data_quality(
    *,
    primary_source: str,
    payload: dict[str, Any],
    required_fields: list[str],
    attempts: list[DataSourceAttempt] | None = None,
    stale_seconds: int | None = None,
) -> DataQualitySummary:
    source_attempts = attempts or []
    missing = [field for field in required_fields if _is_missing(payload.get(field))]
    failed_sources = [attempt.source for attempt in source_attempts if not attempt.ok]
    if stale_seconds is not None and stale_seconds > 60 * 60 * 8:
        quality = "stale"
    elif len(missing) == len(required_fields) or (
        source_attempts and not any(attempt.ok for attempt in source_attempts)
    ):
        quality = "poor"
    elif missing or failed_sources:
        quality = "partial"
    else:
        quality = "good"
    return DataQualitySummary(
        primary_source=primary_source,
        data_quality=quality,
        missing_fields=missing,
        fallback_from=failed_sources,
        attempts=source_attempts,
        stale_seconds=stale_seconds,
    )


def format_data_quality_line(summary: DataQualitySummary) -> str:
    missing = "、".join(summary.missing_fields) if summary.missing_fields else "无"
    fallback = "、".join(summary.fallback_from) if summary.fallback_from else "无"
    return (
        f"数据质量 {summary.data_quality}｜主源 {summary.primary_source}｜"
        f"缺失 {missing}｜失败/降级 {fallback}"
    )


def _is_missing(value: Any) -> bool:
    if value is None or value == "":
        return True
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    return False
