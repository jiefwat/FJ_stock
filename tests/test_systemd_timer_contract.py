from pathlib import Path


def test_stock_ts_daily_timer_uses_required_refresh_windows() -> None:
    timer = Path("deploy/systemd/stock-ts-daily-analysis.timer")
    text = timer.read_text(encoding="utf-8")

    assert "OnCalendar=*-*-* 00:00:00" in text
    assert "OnCalendar=*-*-* 09:00:00" in text
    assert "OnCalendar=*-*-* 13:00:00" in text
    assert "OnCalendar=*-*-* 06:00:00" not in text
    assert "OnCalendar=*-*-* 12:30:00" not in text
    assert "OnCalendar=*-*-* 14:00:00" not in text
    assert "02,04,06,08,10,12,14,16,18,20,22" not in text


def test_stock_ts_daily_service_runs_full_pipeline_with_enough_timeout() -> None:
    service = Path("deploy/systemd/stock-ts-daily-analysis.service")
    text = service.read_text(encoding="utf-8")

    assert "TimeoutStartSec=3600" in text
    assert "scripts/run_daily_pipeline.py" in text
    assert "--provider tdx-snapshot" in text
    assert "--external-enrich-timeout 300" in text


def test_stock_ts_morning_email_timer_sends_at_0830() -> None:
    timer = Path("deploy/systemd/stock-ts-morning-email.timer")
    service = Path("deploy/systemd/stock-ts-morning-email.service")

    timer_text = timer.read_text(encoding="utf-8")
    service_text = service.read_text(encoding="utf-8")

    assert "OnCalendar=*-*-* 08:30:00" in timer_text
    assert "Persistent=true" in timer_text
    assert "scripts/send_morning_report.py" in service_text
    assert "--channels email" in service_text
    assert "--style digest" in service_text


def test_public_auth_dropin_opens_registration_without_readonly_mode() -> None:
    dropin = Path("deploy/systemd/stock-ts-auth-open.conf")
    text = dropin.read_text(encoding="utf-8")

    assert "Environment=STOCK_TS_PUBLIC_READONLY=0" in text
    assert "Environment=STOCK_TS_AUTH_ENABLED=1" in text
    assert "Environment=STOCK_TS_ALLOW_REGISTRATION=1" in text
    assert "STOCK_TS_ADMIN_PASSWORD" not in text
    assert "STOCK_TS_SESSION_SECRET" not in text
