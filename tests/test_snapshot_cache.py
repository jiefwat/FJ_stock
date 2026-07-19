from __future__ import annotations

import importlib
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

FIXTURE = Path(__file__).parent / "fixtures" / "market_snapshot.json"


def _cache_module():
    try:
        return importlib.import_module("aster_market.snapshot_cache")
    except ModuleNotFoundError:
        pytest.fail("SnapshotCache has not been implemented")


def test_unchanged_snapshot_is_parsed_once(tmp_path: Path, monkeypatch) -> None:
    cache_module = _cache_module()
    path = tmp_path / "snapshot.json"
    path.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    calls = 0
    real_loader = cache_module.load_snapshot

    def counting_loader(candidate: Path):
        nonlocal calls
        calls += 1
        return real_loader(candidate)

    monkeypatch.setattr(cache_module, "load_snapshot", counting_loader)
    cache = cache_module.SnapshotCache()

    assert cache.get(path).view["status"] == "ready"
    assert cache.get(path).view["status"] == "ready"
    assert calls == 1


def test_atomic_snapshot_replacement_invalidates_cache(tmp_path: Path) -> None:
    cache_module = _cache_module()
    path = tmp_path / "snapshot.json"
    path.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    cache = cache_module.SnapshotCache()

    first = cache.get(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["market"]["trade_date"] = "2026-07-19"
    replacement = path.with_suffix(".staging")
    replacement.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    replacement.replace(path)
    second = cache.get(path)

    assert first.view["trade_date"] == "2026-07-18"
    assert second.view["trade_date"] == "2026-07-19"
    assert second.fingerprint != first.fingerprint


def test_concurrent_requests_parse_snapshot_once(tmp_path: Path, monkeypatch) -> None:
    cache_module = _cache_module()
    path = tmp_path / "snapshot.json"
    path.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    calls = 0
    real_loader = cache_module.load_snapshot

    def slow_loader(candidate: Path):
        nonlocal calls
        calls += 1
        time.sleep(0.02)
        return real_loader(candidate)

    monkeypatch.setattr(cache_module, "load_snapshot", slow_loader)
    cache = cache_module.SnapshotCache()

    with ThreadPoolExecutor(max_workers=8) as executor:
        states = list(executor.map(cache.get, [path] * 8))

    assert calls == 1
    assert all(state is states[0] for state in states)


def test_missing_snapshot_recovers_when_file_appears(tmp_path: Path) -> None:
    cache_module = _cache_module()
    path = tmp_path / "snapshot.json"
    cache = cache_module.SnapshotCache()

    assert cache.get(path).view["status"] == "unavailable"
    path.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")

    assert cache.get(path).view["status"] == "ready"
