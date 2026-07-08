import os
import sys
from pathlib import Path
from subprocess import run

from stock_ts.config import get_settings, load_dotenv_values, save_dotenv_values
from stock_ts.providers import create_provider
from stock_ts.web import save_settings_from_form
from stock_ts.workflows import build_daily_report, run_doctor


def cli_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    return env


def test_load_dotenv_values_and_settings_redact_token(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "STOCK_TS_PROVIDER=sample\n"
        "STOCK_TS_HOLDINGS_PATH=data/portfolio/holdings.csv\n"
        "STOCK_TS_CACHE_DIR=data/cache-test\n"
        "TUSHARE_TOKEN=secret-token-value\n",
        encoding="utf-8",
    )

    values = load_dotenv_values(env_file)
    settings = get_settings(env_file=env_file)

    assert values["TUSHARE_TOKEN"] == "secret-token-value"
    assert settings.provider == "sample"
    assert settings.holdings_path == "data/portfolio/holdings.csv"
    assert settings.cache_dir == "data/cache-test"
    assert settings.has_tushare_token is True
    assert "secret-token-value" not in settings.safe_summary()["tushare_token"]
    assert settings.safe_summary()["tushare_token"] == "configured"


def test_settings_defaults_to_auto_provider_when_env_is_missing(tmp_path: Path) -> None:
    settings = get_settings(env_file=tmp_path / ".env")

    assert settings.provider == "auto"


def test_doctor_reports_sample_flow_and_dependency_status() -> None:
    report = run_doctor(create_provider("sample"), provider_name="sample")

    assert report.ok is True
    assert any(item.name == "sample_daily_flow" and item.ok for item in report.items)
    assert "Tushare token" in report.markdown
    assert "iTick API Key" in report.markdown
    assert "secret" not in report.markdown.lower()


def test_daily_report_uses_cache_unless_refresh(tmp_path: Path) -> None:
    provider = create_provider("sample")
    first = build_daily_report(
        provider,
        holdings_path="data/portfolio/holdings.csv",
        candidate_limit=20,
        cache_dir=tmp_path,
        refresh=True,
    )
    cache_file = tmp_path / "reports" / "daily-sample-2026-06-05.json"

    assert first.cache_hit is False
    assert cache_file.exists()

    cache_file.write_text(
        '{"metadata":{"source":"sample","trade_date":"2026-06-05"},'
        '"payload":{"markdown":"# cached daily report"}}',
        encoding="utf-8",
    )
    second = build_daily_report(
        provider,
        holdings_path="data/portfolio/holdings.csv",
        candidate_limit=20,
        cache_dir=tmp_path,
        refresh=False,
    )

    assert second.cache_hit is True
    assert second.markdown == "# cached daily report"


def test_save_dotenv_values_merges_and_quotes(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text('APP_ENV="local"\nEMAIL_SENDER="old@example.com"\n', encoding="utf-8")

    save_dotenv_values(
        {
            "EMAIL_SENDER": "new@example.com",
            "EMAIL_RECEIVERS": "a@example.com,b@example.com",
        },
        path=env_file,
    )

    text = env_file.read_text(encoding="utf-8")
    assert 'APP_ENV="local"' in text
    assert 'EMAIL_SENDER="new@example.com"' in text
    assert 'EMAIL_RECEIVERS="a@example.com,b@example.com"' in text


def test_save_settings_from_form_keeps_secret_fields_when_left_blank(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        'STOCK_TS_PROVIDER="sample"\n'
        'EMAIL_SENDER="old@example.com"\n'
        'EMAIL_SENDER_NAME="Old Name"\n'
        'EMAIL_PASSWORD="old-secret"\n'
        'WECHAT_WEBHOOK_URL="https://example.com/webhook"\n'
        'FEISHU_WEBHOOK_URL="https://example.com/feishu"\n'
        'WECHAT_MSG_TYPE="markdown"\n'
        'WECHAT_MAX_BYTES="4000"\n'
        'ITICK_API_KEY="old-itick"\n',
        encoding="utf-8",
    )

    provider = save_settings_from_form(
        {
            "settings_provider": ["auto"],
            "email_sender": ["new@example.com"],
            "email_sender_name": ["StockTS"],
            "email_receivers": ["a@example.com, b@example.com"],
            "email_password": [""],
            "wechat_webhook_url": [""],
            "feishu_webhook_url": [""],
            "wechat_msg_type": ["text"],
            "wechat_max_bytes": ["5000"],
            "notification_report_channels": ["email,wechat,feishu"],
            "notification_report_style": ["digest"],
            "itick_api_key": [""],
        },
        env_file=env_file,
    )

    settings = get_settings(env_file=env_file)
    assert provider == "auto"
    assert settings.provider == "auto"
    assert settings.email_sender == "new@example.com"
    assert settings.email_password == "old-secret"
    assert settings.wechat_webhook_url == "https://example.com/webhook"
    assert settings.feishu_webhook_url == "https://example.com/feishu"
    assert settings.wechat_msg_type == "text"
    assert settings.wechat_max_bytes == 5000
    assert settings.notification_report_channels == ["email", "wechat", "feishu"]
    assert settings.notification_report_style == "digest"
    assert settings.itick_api_key == "old-itick"


def test_cli_doctor_and_daily_cache_options(tmp_path: Path) -> None:
    doctor = run(
        [sys.executable, "-m", "stock_ts.cli", "doctor", "--provider", "sample"],
        capture_output=True,
        text=True,
        check=False,
        env=cli_env(),
    )
    daily = run(
        [
            sys.executable,
            "-m",
            "stock_ts.cli",
            "daily",
            "--provider",
            "sample",
            "--holdings",
            "data/portfolio/holdings.csv",
            "--cache-dir",
            str(tmp_path),
            "--refresh",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=cli_env(),
    )

    assert doctor.returncode == 0
    assert "StockTS 运行体检" in doctor.stdout
    assert daily.returncode == 0
    assert "# StockTS 每日复盘" in daily.stdout
    assert (tmp_path / "reports" / "daily-sample-2026-06-05.json").exists()


def test_save_settings_from_form_updates_itick_api_key(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"

    save_settings_from_form(
        {
            "settings_provider": ["auto"],
            "email_sender": [""],
            "email_sender_name": ["StockTS"],
            "email_receivers": [""],
            "email_password": [""],
            "wechat_webhook_url": [""],
            "feishu_webhook_url": [""],
            "wechat_msg_type": ["markdown"],
            "wechat_max_bytes": ["4000"],
            "notification_report_channels": ["email"],
            "notification_report_style": ["digest"],
            "itick_api_key": ["new-itick"],
        },
        env_file=env_file,
    )

    assert get_settings(env_file=env_file).itick_api_key == "new-itick"
