from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Barrier

import pytest

from stock_ts.research_delivery import deliver_research
from stock_ts.research_engine import ResearchContext, ResearchWorkspaceResult
from stock_ts.research_snapshots import ResearchSnapshotStore

TZ = timezone(timedelta(hours=8))
NOW = datetime(2026, 7, 15, 8, 0, tzinfo=TZ)


def _payload(*, generated_at: str = "2026-07-15T07:20:00+08:00") -> dict[str, object]:
    return {
        "ok": True,
        "status": "complete",
        "module": "market",
        "generated_at": generated_at,
        "verdict": "趋势已更新",
        "action": "保持观察",
        "primary_risk": "成交缩量",
        "findings": [],
        "details": [],
        "missing_sections": [],
        "module_items": [],
    }


def _result(*, ok: bool = True, status: str = "complete") -> ResearchWorkspaceResult:
    return ResearchWorkspaceResult(
        ok=ok,
        status=status,
        module="market",
        generated_at=NOW.isoformat(timespec="seconds"),
        verdict="趋势已更新" if ok else "服务不可用",
        action="保持观察",
        primary_risk="成交缩量",
    )


class FakeService:
    def __init__(self, result: ResearchWorkspaceResult) -> None:
        self.result = result
        self.calls = 0

    def research(
        self,
        module: str,
        context: ResearchContext,
        *,
        refresh: bool = False,
    ) -> ResearchWorkspaceResult:
        self.calls += 1
        return self.result


class ExplodingService:
    def research(self, *_args, **_kwargs):
        raise RuntimeError("upstream unavailable")


def test_snapshot_store_writes_latest_and_date_archive_atomically(tmp_path) -> None:
    store = ResearchSnapshotStore(tmp_path, clock=lambda: NOW)
    payload = _payload()

    store.save("market", payload)

    assert json.loads((tmp_path / "market/latest.json").read_text()) == payload
    assert json.loads((tmp_path / "market/2026-07-15.json").read_text()) == payload
    assert not list(tmp_path.rglob("*.tmp"))


def test_snapshot_freshness_prefers_fact_as_of_over_generated_at(tmp_path) -> None:
    now = datetime(2026, 7, 16, 16, 0, tzinfo=TZ)
    store = ResearchSnapshotStore(tmp_path, clock=lambda: now)
    store.save(
        "market",
        _payload(generated_at="2026-07-16T15:00:00+08:00")
        | {"as_of": "2026-07-10"},
    )

    assert (tmp_path / "market/2026-07-16.json").exists()
    assert not (tmp_path / "market/2026-07-10.json").exists()
    assert store.load("market") is None
    stale_snapshot = store.load("market", allow_stale=True)
    assert stale_snapshot is not None
    assert stale_snapshot.stale is True
    assert stale_snapshot.age_hours == 96.0


def test_date_only_snapshot_remains_fresh_late_on_the_same_day(tmp_path) -> None:
    now = datetime(2026, 7, 16, 20, 0, tzinfo=TZ)
    store = ResearchSnapshotStore(tmp_path, clock=lambda: now)
    store.save("market", _payload() | {"as_of": "2026-07-16"})

    snapshot = store.load("market")
    assert snapshot is not None
    assert snapshot.stale is False
    assert snapshot.age_hours == 0.0


def test_date_only_snapshot_ignores_weekend_days_for_freshness(tmp_path) -> None:
    monday = datetime(2026, 7, 13, 20, 0, tzinfo=TZ)
    store = ResearchSnapshotStore(tmp_path, clock=lambda: monday)
    store.save("market", _payload() | {"as_of": "2026-07-10"})

    snapshot = store.load("market")
    assert snapshot is not None
    assert snapshot.stale is False
    assert snapshot.age_hours == 24.0


def test_date_only_snapshot_is_stale_after_two_workdays(tmp_path) -> None:
    tuesday = datetime(2026, 7, 14, 20, 0, tzinfo=TZ)
    store = ResearchSnapshotStore(tmp_path, clock=lambda: tuesday)
    store.save("market", _payload() | {"as_of": "2026-07-10"})

    assert store.load("market") is None
    stale_snapshot = store.load("market", allow_stale=True)
    assert stale_snapshot is not None
    assert stale_snapshot.stale is True
    assert stale_snapshot.age_hours == 48.0


def test_timestamp_snapshot_freshness_remains_hour_based(tmp_path) -> None:
    now = datetime(2026, 7, 16, 20, 0, tzinfo=TZ)
    store = ResearchSnapshotStore(tmp_path, clock=lambda: now)
    store.save("market", _payload() | {"as_of": "2026-07-15T20:00:00+08:00"})

    assert store.load("market") is None
    stale_snapshot = store.load("market", allow_stale=True)
    assert stale_snapshot is not None
    assert stale_snapshot.stale is True
    assert stale_snapshot.age_hours == 24.0


def test_snapshot_freshness_rejects_non_empty_invalid_as_of(tmp_path) -> None:
    now = datetime(2026, 7, 16, 16, 0, tzinfo=TZ)
    store = ResearchSnapshotStore(tmp_path, clock=lambda: now)
    store.save(
        "market",
        _payload(generated_at="2026-07-16T15:00:00+08:00")
        | {"as_of": "invalid"},
    )

    assert store.load("market") is None
    assert store.load("market", allow_stale=True) is None


def test_snapshot_freshness_falls_back_when_as_of_is_empty(tmp_path) -> None:
    now = datetime(2026, 7, 16, 16, 0, tzinfo=TZ)
    store = ResearchSnapshotStore(tmp_path, clock=lambda: now)
    store.save(
        "market",
        _payload(generated_at="2026-07-16T15:00:00+08:00") | {"as_of": ""},
    )

    snapshot = store.load("market")
    assert snapshot is not None
    assert snapshot.stale is False
    assert snapshot.age_hours == 1.0


def test_concurrent_snapshot_writers_use_independent_temp_files(
    tmp_path,
    monkeypatch,
) -> None:
    store = ResearchSnapshotStore(tmp_path, clock=lambda: NOW)
    barrier = Barrier(2)
    original_write_text = Path.write_text

    def delayed_write_text(path, content, *args, **kwargs):
        written = original_write_text(path, content, *args, **kwargs)
        if path.name == "latest.json.tmp":
            barrier.wait(timeout=2)
        return written

    monkeypatch.setattr(Path, "write_text", delayed_write_text)
    payloads = [
        _payload() | {"verdict": "并发写入一"},
        _payload() | {"verdict": "并发写入二"},
    ]

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(store.save, "market", payload) for payload in payloads]
        for future in futures:
            future.result()

    latest = json.loads((tmp_path / "market/latest.json").read_text())
    assert latest["verdict"] in {"并发写入一", "并发写入二"}
    assert not list(tmp_path.rglob("*.tmp"))


def test_delivery_prefers_fresh_snapshot_without_live_call(tmp_path) -> None:
    store = ResearchSnapshotStore(tmp_path, clock=lambda: NOW)
    fresh_payload = _payload() | {
        "decision_label": "等待确认",
        "findings": [{"title": "当日事实"}],
        "module_items": [{"label": "实时评分", "value": "72"}],
        "module_sections": [{"key": "market-pulse", "items": []}],
    }
    store.save("market", fresh_payload)
    service = FakeService(_result(ok=False, status="unavailable"))

    delivered = deliver_research(
        service,
        store,
        "market",
        ResearchContext(),
        refresh=False,
    )

    assert delivered["delivery"] == "snapshot"
    assert delivered["stale"] is False
    assert delivered["decision_label"] == "等待确认"
    assert delivered["verdict"] == "趋势已更新"
    assert delivered["action"] == "保持观察"
    assert delivered["primary_risk"] == "成交缩量"
    assert delivered["findings"] == [{"title": "当日事实"}]
    assert delivered["module_items"] == [{"label": "实时评分", "value": "72"}]
    assert delivered["module_sections"] == [{"key": "market-pulse", "items": []}]
    assert service.calls == 0


@pytest.mark.parametrize("module", ["market", "opportunity"])
def test_delivery_blocks_stale_snapshot_actions_and_candidates(
    tmp_path,
    module: str,
) -> None:
    store = ResearchSnapshotStore(tmp_path, clock=lambda: NOW)
    store.save(
        module,
        _payload(generated_at="2026-07-13T07:20:00+08:00")
        | {
            "module": module,
            "decision_label": "可以执行",
            "verdict": "旧快照仍看多",
            "action": "按旧条件买入",
            "primary_risk": "成交缩量",
            "findings": [{"title": "旧评分候选"}],
            "module_items": [{"label": "观察分", "value": "88"}],
            "module_sections": [{"key": f"{module}-legacy", "items": [{"score": 88}]}],
        },
    )
    service = FakeService(_result(ok=False, status="unavailable"))

    delivered = deliver_research(
        service,
        store,
        module,
        ResearchContext(),
        refresh=False,
    )

    assert delivered["delivery"] == "stale_snapshot"
    assert delivered["stale"] is True
    assert delivered["data_label"] == "历史参考"
    assert delivered["decision_label"] == "历史参考"
    assert delivered["verdict"] == "历史记录：旧快照仍看多"
    assert delivered["action"] == "历史数据仅供复盘，不作为今天的操作依据。"
    assert "数据过期" in str(delivered["primary_risk"])
    assert delivered["findings"] == []
    assert delivered["module_items"] == []
    assert delivered["module_sections"] == []
    assert service.calls == 1


def test_delivery_falls_back_to_stale_snapshot_after_live_exception(tmp_path) -> None:
    store = ResearchSnapshotStore(tmp_path, clock=lambda: NOW)
    store.save("market", _payload(generated_at="2026-07-13T07:20:00+08:00"))

    delivered = deliver_research(
        ExplodingService(),
        store,
        "market",
        ResearchContext(),
        refresh=True,
    )

    assert delivered["delivery"] == "stale_snapshot"
    assert delivered["stale"] is True


def test_live_success_replaces_global_snapshot(tmp_path) -> None:
    store = ResearchSnapshotStore(tmp_path, clock=lambda: NOW)
    service = FakeService(_result())

    delivered = deliver_research(
        service,
        store,
        "market",
        ResearchContext(),
        refresh=True,
    )

    assert delivered["delivery"] == "live"
    assert json.loads((tmp_path / "market/latest.json").read_text())["ok"] is True


def test_portfolio_never_reads_or_writes_shared_snapshot(tmp_path) -> None:
    store = ResearchSnapshotStore(tmp_path, clock=lambda: NOW)
    service = FakeService(_result())

    delivered = deliver_research(
        service,
        store,
        "portfolio",
        ResearchContext(),
        refresh=False,
    )

    assert delivered["delivery"] == "live"
    assert service.calls == 1
    assert not (tmp_path / "portfolio").exists()


def test_non_global_unavailable_result_uses_local_fallback(tmp_path) -> None:
    calls = []

    def fallback(module, context):
        calls.append((module, context))
        return ResearchWorkspaceResult(
            ok=True,
            status="partial",
            module="stock",
            generated_at=NOW.isoformat(),
            verdict="本地结论",
            action="条件观察",
            primary_risk="部分维度待补",
            delivery="local_fallback",
        )

    delivered = deliver_research(
        FakeService(_result(ok=False, status="unavailable")),
        ResearchSnapshotStore(tmp_path),
        "stock",
        ResearchContext(code="603278"),
        fallback=fallback,
    )

    assert delivered["delivery"] == "local_fallback"
    assert len(calls) == 1


def test_live_success_never_calls_local_fallback(tmp_path) -> None:
    def fallback(*_args):
        raise AssertionError("live success must not call fallback")

    delivered = deliver_research(
        FakeService(_result(ok=True, status="complete")),
        ResearchSnapshotStore(tmp_path),
        "stock",
        ResearchContext(code="603278"),
        fallback=fallback,
    )

    assert delivered["delivery"] == "live"
