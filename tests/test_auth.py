from __future__ import annotations

import time

from stock_ts.auth import (
    AuthConfig,
    PasswordHasher,
    SessionManager,
    UserStore,
    is_auth_enabled,
)


def test_password_hash_verifies_without_storing_plaintext() -> None:
    encoded = PasswordHasher.hash_password("correct horse battery staple")

    assert "correct" not in encoded
    assert PasswordHasher.verify_password("correct horse battery staple", encoded)
    assert not PasswordHasher.verify_password("wrong password", encoded)


def test_user_store_bootstraps_admin_idempotently(tmp_path) -> None:
    store = UserStore(tmp_path / "users.sqlite3")

    user = store.bootstrap_admin(username="owner@example.com", password="secret-password")
    again = store.bootstrap_admin(username="owner@example.com", password="secret-password")

    assert user.username == "owner@example.com"
    assert again.id == user.id
    assert store.authenticate("owner@example.com", "secret-password") is not None
    assert store.authenticate("owner@example.com", "bad") is None
    assert "secret-password" not in str((tmp_path / "users.sqlite3").read_bytes())


def test_session_manager_signs_and_expires_cookie() -> None:
    manager = SessionManager(secret="test-secret", ttl_seconds=1)

    cookie = manager.issue_session(user_id=7, username="owner")
    session = manager.verify_session(cookie)

    assert session is not None
    assert session.user_id == 7
    assert session.username == "owner"
    assert manager.verify_session(cookie + "tampered") is None

    expired = SessionManager(secret="test-secret", ttl_seconds=1).issue_session(
        user_id=7,
        username="owner",
        now=int(time.time()) - 10,
    )
    assert manager.verify_session(expired) is None


def test_auth_config_requires_explicit_enable_and_admin_credentials(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_TS_AUTH_ENABLED", raising=False)
    monkeypatch.delenv("STOCK_TS_ADMIN_PASSWORD", raising=False)
    assert not is_auth_enabled(AuthConfig.from_env())

    monkeypatch.setenv("STOCK_TS_AUTH_ENABLED", "1")
    monkeypatch.setenv("STOCK_TS_ADMIN_USERNAME", "owner")
    monkeypatch.setenv("STOCK_TS_ADMIN_PASSWORD", "secret-password")
    monkeypatch.setenv("STOCK_TS_AUTH_DB_PATH", str(tmp_path / "users.sqlite3"))
    monkeypatch.setenv("STOCK_TS_SESSION_SECRET", "session-secret")

    config = AuthConfig.from_env()
    assert is_auth_enabled(config)
    assert config.admin_username == "owner"
    assert config.db_path == tmp_path / "users.sqlite3"


def test_auth_config_reads_dotenv_file_when_process_env_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_TS_AUTH_ENABLED", raising=False)
    monkeypatch.delenv("STOCK_TS_ADMIN_USERNAME", raising=False)
    monkeypatch.delenv("STOCK_TS_ADMIN_PASSWORD", raising=False)
    monkeypatch.delenv("STOCK_TS_SESSION_SECRET", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        'STOCK_TS_AUTH_ENABLED="1"\n'
        'STOCK_TS_ADMIN_USERNAME="owner@example.com"\n'
        'STOCK_TS_ADMIN_PASSWORD="secret-password"\n'
        'STOCK_TS_SESSION_SECRET="session-secret"\n'
        'STOCK_TS_AUTH_DB_PATH="data/auth/users.sqlite3"\n',
        encoding="utf-8",
    )

    config = AuthConfig.from_env(env_file=env_file)

    assert is_auth_enabled(config)
    assert config.admin_username == "owner@example.com"
    assert config.admin_password == "secret-password"


def test_user_store_changes_password_after_checking_old_password(tmp_path) -> None:
    store = UserStore(tmp_path / "users.sqlite3")
    user = store.bootstrap_admin("owner@example.com", "old-secret")

    assert store.change_password(user.id, "wrong-old", "new-secret") is False
    assert store.authenticate("owner@example.com", "old-secret") is not None

    assert store.change_password(user.id, "old-secret", "new-secret") is True
    assert store.authenticate("owner@example.com", "old-secret") is None
    assert store.authenticate("owner@example.com", "new-secret") is not None


def test_user_store_registers_member_with_login_permission(tmp_path) -> None:
    store = UserStore(tmp_path / "users.sqlite3")

    user = store.register_user("NewUser@Example.com", "member-secret")

    assert user.username == "newuser@example.com"
    assert user.role == "member"
    assert store.authenticate("newuser@example.com", "member-secret") is not None
    assert store.authenticate("newuser@example.com", "wrong") is None


def test_auth_config_reads_registration_flag(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_TS_ALLOW_REGISTRATION", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        'STOCK_TS_AUTH_ENABLED="1"\n'
        'STOCK_TS_ADMIN_USERNAME="owner@example.com"\n'
        'STOCK_TS_ADMIN_PASSWORD="secret-password"\n'
        'STOCK_TS_ALLOW_REGISTRATION="1"\n',
        encoding="utf-8",
    )

    config = AuthConfig.from_env(env_file=env_file)

    assert config.allow_registration is True
