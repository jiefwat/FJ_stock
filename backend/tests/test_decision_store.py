from datetime import UTC, datetime, timedelta

import pytest

from marketdesk.models import DecisionPresentation, DecisionSnapshot
from marketdesk.store import Store

BASE_TIME = datetime(2026, 8, 16, 1, 0, tzinfo=UTC)


def create_user(store: Store, email: str):
    return store.create_user(email, email.split("@")[0], "test-hash")


def snapshot(
    action: str,
    *,
    observed_at: datetime = BASE_TIME,
    severity: str = "info",
    user_required: bool = False,
    source: str = "opportunity",
    subject_key: str = "trend",
) -> DecisionSnapshot:
    return DecisionSnapshot.model_validate(
        {
            "source": source,
            "subject_key": subject_key,
            "symbol": "SZ.002517",
            "name": "恺英网络",
            "strategy": "trend" if source == "opportunity" else None,
            "decision": DecisionPresentation(
                action=action,
                summary=f"当前决定是{action}",
                severity=severity,
                user_required=user_required,
                reason_code=f"reason_{action}",
            ),
            "href": "/stocks?symbol=SZ.002517",
            "observed_at": observed_at,
        }
    )


def test_first_snapshot_is_baseline_and_action_change_creates_one_event(tmp_path) -> None:
    store = Store(tmp_path / "decision.db")
    user = create_user(store, "one@example.test")

    assert store.record_decision_snapshot(user.id, snapshot("仅观察")) is None
    event = store.record_decision_snapshot(
        user.id,
        snapshot(
            "可小仓试探",
            observed_at=BASE_TIME + timedelta(minutes=10),
            severity="action",
            user_required=True,
        ),
    )

    assert event is not None
    assert event.previous_action == "仅观察"
    assert event.action == "可小仓试探"
    assert event.email_status == "not_required"
    assert store.record_decision_snapshot(
        user.id,
        snapshot("可小仓试探", observed_at=BASE_TIME + timedelta(minutes=20)),
    ) is None
    assert len(store.list_decision_events(user.id)) == 1


def test_decision_events_are_account_scoped_and_read_state_is_owned(tmp_path) -> None:
    store = Store(tmp_path / "isolated.db")
    first = create_user(store, "first@example.test")
    second = create_user(store, "second@example.test")
    store.record_decision_snapshot(first.id, snapshot("继续持有", source="holding", subject_key="1"))
    event = store.record_decision_snapshot(
        first.id,
        snapshot(
            "优先减仓或止损",
            source="holding",
            subject_key="1",
            observed_at=BASE_TIME + timedelta(minutes=10),
            severity="critical",
            user_required=True,
        ),
    )

    assert event is not None
    assert store.list_decision_events(second.id) == []
    with pytest.raises(KeyError):
        store.mark_decision_event_read(event.id, second.id)
    read = store.mark_decision_event_read(event.id, first.id)
    assert read.read_at is not None


def test_removed_holding_snapshot_establishes_a_new_baseline(tmp_path) -> None:
    store = Store(tmp_path / "removed.db")
    user = create_user(store, "holder@example.test")
    store.record_decision_snapshot(
        user.id, snapshot("继续持有", source="holding", subject_key="7")
    )

    assert store.delete_missing_holding_decision_snapshots(user.id, set()) == 1
    assert store.record_decision_snapshot(
        user.id,
        snapshot(
            "优先减仓或止损",
            source="holding",
            subject_key="7",
            observed_at=BASE_TIME + timedelta(minutes=10),
            severity="critical",
            user_required=True,
        ),
    ) is None
    assert store.list_decision_events(user.id) == []


def test_high_risk_event_enters_bounded_email_queue(tmp_path) -> None:
    store = Store(tmp_path / "email.db")
    user = create_user(store, "risk@example.test")
    store.record_decision_snapshot(
        user.id, snapshot("继续持有", source="holding", subject_key="3")
    )
    event = store.record_decision_snapshot(
        user.id,
        snapshot(
            "建议分批减仓",
            source="holding",
            subject_key="3",
            observed_at=BASE_TIME + timedelta(minutes=10),
            severity="high",
            user_required=True,
        ),
    )

    assert event is not None
    assert event.email_status == "pending"
    assert [(account.id, queued.id) for account, queued in store.list_pending_decision_emails()] == [
        (user.id, event.id)
    ]
    store.mark_decision_email_result(event.id, sent=False, error="SMTPError")
    assert store.list_decision_events(user.id)[0].email_attempts == 1
    store.mark_decision_email_result(event.id, sent=True)
    assert store.list_pending_decision_emails() == []
