from datetime import UTC, datetime

from marketdesk.services import MarketService
from marketdesk.store import Store


def test_snapshot_round_trip_and_watchlist_crud(tmp_path) -> None:
    store = Store(tmp_path / "marketdesk.db")
    store.save_snapshot("market", datetime.now(UTC), {"score": 61})
    snapshot = store.latest_snapshot("market")

    assert snapshot is not None
    assert snapshot.payload == {"score": 61}

    item = store.create_watchlist("SH.600519", "贵州茅台", "现金流稳定", "跌破长期趋势")
    assert store.list_watchlist()[0].id == item.id
    updated = store.update_watchlist(item.id, status="researching", thesis="等待估值回落")
    assert updated.thesis == "等待估值回落"
    store.delete_watchlist(item.id)
    assert store.list_watchlist() == []


def test_default_market_service_uses_configured_data_dir(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("MARKETDESK_DATA_DIR", str(tmp_path))

    service = MarketService()

    assert service.store.path == tmp_path / "marketdesk.db"
