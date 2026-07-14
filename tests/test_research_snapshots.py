from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Barrier

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
    store.save("market", _payload())
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
    assert service.calls == 0


def test_delivery_falls_back_to_stale_snapshot_after_live_failure(tmp_path) -> None:
    store = ResearchSnapshotStore(tmp_path, clock=lambda: NOW)
    store.save("market", _payload(generated_at="2026-07-13T07:20:00+08:00"))
    service = FakeService(_result(ok=False, status="unavailable"))

    delivered = deliver_research(
        service,
        store,
        "market",
        ResearchContext(),
        refresh=False,
    )

    assert delivered["delivery"] == "stale_snapshot"
    assert delivered["stale"] is True
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
