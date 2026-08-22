import sqlite3
from datetime import UTC, datetime, timedelta

from marketdesk.models import DecisionPresentation, DecisionSnapshot, EquityViewFilters
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


def test_saved_equity_view_round_trip_and_user_scope(tmp_path) -> None:
    store = Store(tmp_path / "views.db")
    alpha = store.create_user("alpha@example.com", "Alpha", "hash-alpha")
    beta = store.create_user("beta@example.com", "Beta", "hash-beta")
    filters = EquityViewFilters(
        query="茅台",
        exchange="sh",
        sector="白酒",
        min_change_pct=1,
        min_amount=1_000_000_000,
        complete_only=True,
        page_size=50,
    )

    created = store.create_equity_view("白酒放量", filters, alpha.id)

    assert store.list_equity_views(alpha.id) == [created]
    assert store.list_equity_views(beta.id) == []
    store.delete_equity_view(created.id, beta.id)
    assert store.list_equity_views(alpha.id) == [created]
    store.delete_equity_view(created.id, alpha.id)
    assert store.list_equity_views(alpha.id) == []


def test_decision_events_ignore_columns_from_a_newer_database_schema(tmp_path) -> None:
    database = tmp_path / "forward-compatible.db"
    store = Store(database)
    user = store.create_user("forward@example.com", "Forward", "hash")
    observed_at = datetime.now(UTC)

    def snapshot(action: str, when: datetime) -> DecisionSnapshot:
        return DecisionSnapshot(
            source="holding",
            subject_key="holding-1",
            symbol="SH.600519",
            name="贵州茅台",
            decision=DecisionPresentation(
                action=action,
                summary=f"决定变为{action}",
                severity="high" if action == "建议分批减仓" else "info",
                user_required=action == "建议分批减仓",
                reason_code="holding_trim",
            ),
            href="/holdings",
            observed_at=when,
        )

    store.record_decision_snapshot(user.id, snapshot("继续持有", observed_at))
    store.record_decision_snapshot(
        user.id,
        snapshot("建议分批减仓", observed_at + timedelta(minutes=10)),
    )
    with sqlite3.connect(database) as connection:
        connection.execute("ALTER TABLE decision_events ADD COLUMN future_score REAL")
        connection.execute("UPDATE decision_events SET future_score=0.56")

    events = store.list_decision_events(user.id)

    assert len(events) == 1
    assert events[0].action == "建议分批减仓"
