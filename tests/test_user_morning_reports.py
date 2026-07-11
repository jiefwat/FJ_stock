from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import scripts.send_user_morning_reports as module
from stock_ts.account_settings import save_morning_email_preferences


def test_due_user_morning_reports_send_once_per_day(monkeypatch, tmp_path: Path) -> None:
    user_data = tmp_path / "users"
    save_morning_email_preferences(
        1,
        receiver="alice@example.com",
        send_time="08:30",
        enabled=True,
        user_data_dir=user_data,
    )
    save_morning_email_preferences(
        2,
        receiver="bob@example.com",
        send_time="09:30",
        enabled=True,
        user_data_dir=user_data,
    )
    calls = []

    def fake_send(**kwargs):  # noqa: ANN003, ANN202
        calls.append(kwargs)
        return module.SendResult(ok=True, markdown="# ok\n")

    monkeypatch.setattr(module, "send_morning_report", fake_send)
    now = datetime(2026, 7, 11, 8, 45, tzinfo=timezone(timedelta(hours=8)))

    result = module.dispatch_due_user_reports(
        user_data_dir=user_data,
        now=now,
        dry_run=False,
        skip_if_email_missing=False,
    )
    second = module.dispatch_due_user_reports(
        user_data_dir=user_data,
        now=now,
        dry_run=False,
        skip_if_email_missing=False,
    )

    assert result.sent == 1
    assert second.sent == 0
    assert calls[0]["holdings_path"] == user_data / "1" / "holdings.csv"
    assert calls[0]["email_receivers"] == ["alice@example.com"]


def test_user_morning_reports_skip_when_global_email_missing(monkeypatch, tmp_path: Path) -> None:
    user_data = tmp_path / "users"
    save_morning_email_preferences(
        1,
        receiver="alice@example.com",
        send_time="08:30",
        enabled=True,
        user_data_dir=user_data,
    )

    class MissingEmailSettings:
        email_sender = ""
        email_password = ""

    monkeypatch.setattr(module, "get_settings", lambda: MissingEmailSettings())
    result = module.dispatch_due_user_reports(
        user_data_dir=user_data,
        now=datetime(2026, 7, 11, 8, 45, tzinfo=timezone(timedelta(hours=8))),
        dry_run=False,
        skip_if_email_missing=True,
    )

    assert result.sent == 0
    assert result.skipped >= 1
    assert "邮箱未配置" in result.markdown


def test_user_morning_reports_script_runs_directly(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/send_user_morning_reports.py",
            "--user-data-dir",
            str(tmp_path / "users"),
            "--dry-run",
            "--skip-if-email-missing",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0
    assert "StockTS 账号晨报发送结果" in result.stdout
