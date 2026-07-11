from pathlib import Path


def test_stock_ts_daily_timer_uses_required_refresh_windows() -> None:
    timer = Path("deploy/systemd/stock-ts-daily-analysis.timer")
    text = timer.read_text(encoding="utf-8")

    assert "OnCalendar=*-*-* 00:00:00" in text
    assert "OnCalendar=*-*-* 06:00:00" in text
    assert "OnCalendar=*-*-* 09:00:00" in text
    assert "OnCalendar=*-*-* 12:30:00" in text
    assert "OnCalendar=*-*-* 14:00:00" in text
    assert "02,04,06,08,10,12,14,16,18,20,22" not in text


def test_stock_ts_daily_service_runs_full_pipeline_with_enough_timeout() -> None:
    service = Path("deploy/systemd/stock-ts-daily-analysis.service")
    text = service.read_text(encoding="utf-8")

    assert "TimeoutStartSec=3600" in text
    assert "scripts/run_daily_pipeline.py" in text
    assert "--provider tdx-snapshot" in text
    assert "--external-enrich-timeout 300" in text
