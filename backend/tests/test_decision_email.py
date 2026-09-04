from datetime import UTC, datetime, timedelta

import pytest

from marketdesk.config import Settings
from marketdesk.decision_email import dispatch_decision_emails
from marketdesk.models import DecisionPresentation, DecisionSnapshot
from marketdesk.store import Store


def pending_event(tmp_path, email: str = "holder@valid.cn"):
    store = Store(tmp_path / "email.db")
    user = store.create_user(email, "Holder", "hash")
    holding = store.create_holding(
        symbol="SH.600519",
        name="贵州茅台",
        quantity=10,
        cost_price=1500,
        target_weight=0.2,
        thesis="现金流稳定",
        invalidation="跌破长期均线",
        user_id=user.id,
    )
    assert holding.id == 1
    base = datetime(2026, 8, 16, 1, 0, tzinfo=UTC)

    def decision(action: str, severity: str, observed_at: datetime) -> DecisionSnapshot:
        return DecisionSnapshot.model_validate(
            {
                "source": "holding",
                "subject_key": "1",
                "symbol": "SH.600519",
                "name": "贵州茅台",
                "decision": DecisionPresentation(
                    action=action,
                    summary=f"当前决定是{action}",
                    severity=severity,
                    user_required=severity in {"high", "critical"},
                    reason_code=f"holding_{severity}",
                ),
                "href": "/holdings?symbol=SH.600519",
                "observed_at": observed_at,
            }
        )

    store.record_decision_snapshot(user.id, decision("继续持有", "info", base))
    event = store.record_decision_snapshot(
        user.id, decision("优先减仓或止损", "critical", base + timedelta(minutes=10))
    )
    assert event is not None
    return store, event


def email_settings(tmp_path) -> Settings:
    return Settings(
        data_dir=tmp_path,
        email_sender="sender@valid.cn",
        email_password="secret",
        email_from="sender@valid.cn",
        morning_email_base_url="https://stock.example.cn",
    )


@pytest.mark.asyncio
async def test_dispatch_sends_each_pending_high_risk_event_once(tmp_path, monkeypatch) -> None:
    store, event = pending_event(tmp_path)
    settings = email_settings(tmp_path).model_copy(
        update={"email_receivers": "platform-owner@valid.cn"}
    )
    sent: list[str] = []
    monkeypatch.setattr(
        "marketdesk.decision_email._send_message",
        lambda message, settings: sent.append(str(message["To"])),
    )

    first = await dispatch_decision_emails(store, settings)
    second = await dispatch_decision_emails(store, settings)

    assert first.sent == 1
    assert second.sent == 0
    assert sent == ["holder@valid.cn"]
    assert store.get_decision_event(event.id, 2).email_status == "sent"


@pytest.mark.asyncio
async def test_dispatch_stops_after_three_bounded_failures(tmp_path, monkeypatch) -> None:
    store, event = pending_event(tmp_path)

    def fail(*_args):
        raise OSError("SMTP unavailable")

    monkeypatch.setattr("marketdesk.decision_email._send_message", fail)
    for _ in range(4):
        await dispatch_decision_emails(store, email_settings(tmp_path))

    stored = store.get_decision_event(event.id, 2)
    assert stored.email_status == "failed"
    assert stored.email_attempts == 3
    assert stored.email_error == "OSError"


@pytest.mark.asyncio
async def test_dispatch_skips_non_real_recipient_without_retry_loop(tmp_path) -> None:
    store, event = pending_event(tmp_path, "smoke-user@example.com")

    summary = await dispatch_decision_emails(store, email_settings(tmp_path))

    stored = store.get_decision_event(event.id, 2)
    assert summary.skipped == 1
    assert stored.email_status == "failed"
    assert stored.email_error == "recipient unavailable"


@pytest.mark.asyncio
async def test_dispatch_does_not_redirect_test_account_alerts_to_global_receiver(
    tmp_path, monkeypatch
) -> None:
    store, event = pending_event(tmp_path, "overflow-check@example.com")
    settings = email_settings(tmp_path).model_copy(
        update={"email_receivers": "personal-owner@valid.cn"}
    )
    sent: list[str] = []
    monkeypatch.setattr(
        "marketdesk.decision_email._send_message",
        lambda message, _settings: sent.append(str(message["To"])),
    )

    summary = await dispatch_decision_emails(store, settings)

    assert summary.sent == 0
    assert summary.skipped == 1
    assert sent == []
    stored = store.get_decision_event(event.id, 2)
    assert stored.email_status == "failed"
    assert stored.email_error == "recipient unavailable"


@pytest.mark.asyncio
async def test_dispatch_cancels_alert_when_stock_is_no_longer_held(tmp_path, monkeypatch) -> None:
    store, event = pending_event(tmp_path)
    store.delete_holding(1, 2)
    sent: list[str] = []
    monkeypatch.setattr(
        "marketdesk.decision_email._send_message",
        lambda message, settings: sent.append(str(message["To"])),
    )

    summary = await dispatch_decision_emails(store, email_settings(tmp_path))

    assert summary.sent == 0
    assert summary.skipped == 1
    assert sent == []
    stored = store.get_decision_event(event.id, 2)
    assert stored.email_status == "failed"
    assert stored.email_error == "holding no longer active"
