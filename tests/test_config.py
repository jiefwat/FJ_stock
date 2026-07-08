from __future__ import annotations

from stock_ts.config import Settings, get_settings, save_dotenv_values


def test_settings_safe_summary_masks_itick_api_key(tmp_path):
    settings = Settings(itick_api_key="secret-itick")

    assert settings.has_itick_api_key is True
    assert settings.safe_summary()["itick"] == "configured"
    assert "secret-itick" not in str(settings.safe_summary())


def test_save_and_load_dotenv_values_supports_itick_api_key(tmp_path):
    env_path = tmp_path / ".env"

    save_dotenv_values({"ITICK_API_KEY": "secret-itick"}, path=env_path, merge=False)

    assert get_settings(env_path).itick_api_key == "secret-itick"


def test_settings_accepts_explicit_smtp_environment(tmp_path, monkeypatch):
    for key in [
        "SMTP_HOST",
        "SMTP_PORT",
        "SMTP_TLS",
        "SMTP_USER",
        "SMTP_FROM",
        "SMTP_PASSWORD",
        "EMAIL_SENDER",
        "EMAIL_PASSWORD",
    ]:
        monkeypatch.delenv(key, raising=False)
    env_path = tmp_path / ".env"
    save_dotenv_values(
        {
            "SMTP_HOST": "smtp.gmail.com",
            "SMTP_PORT": "465",
            "SMTP_TLS": "ssl",
            "SMTP_USER": "sender@example.com",
            "SMTP_FROM": "from@example.com",
            "SMTP_PASSWORD": "secret-password",
            "EMAIL_RECEIVERS": "to@example.com",
        },
        path=env_path,
        merge=False,
    )

    settings = get_settings(env_path)

    assert settings.smtp_host == "smtp.gmail.com"
    assert settings.smtp_port == 465
    assert settings.smtp_tls == "ssl"
    assert settings.email_sender == "sender@example.com"
    assert settings.email_from == "from@example.com"
    assert settings.email_password == "secret-password"
    assert settings.email_receivers == ["to@example.com"]
    assert settings.safe_summary()["email"] == "configured"
    assert "secret-password" not in str(settings.safe_summary())
