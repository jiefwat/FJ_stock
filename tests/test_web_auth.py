from __future__ import annotations

import threading
import urllib.error
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer

from stock_ts.auth import AuthConfig, AuthUser, SessionManager, UserStore
from stock_ts.portfolio import load_holdings_csv
from stock_ts.providers.sample import SampleDataProvider
from stock_ts.web import (
    Handler,
    _effective_holdings_path,
    _ensure_user_holdings_file,
    render_login_page,
    render_page,
    should_allow_registration,
    should_require_login,
    user_from_cookie_header,
)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


def _auth_config(tmp_path) -> AuthConfig:
    return AuthConfig(
        enabled=True,
        admin_username="owner@example.com",
        admin_password="secret-password",
        db_path=tmp_path / "users.sqlite3",
        session_secret="session-secret",
        session_ttl_seconds=3600,
    )


def _serve_once(monkeypatch, tmp_path):
    monkeypatch.setenv("STOCK_TS_AUTH_ENABLED", "1")
    monkeypatch.setenv("STOCK_TS_ADMIN_USERNAME", "owner@example.com")
    monkeypatch.setenv("STOCK_TS_ADMIN_PASSWORD", "secret-password")
    monkeypatch.setenv("STOCK_TS_SESSION_SECRET", "session-secret")
    monkeypatch.setenv("STOCK_TS_AUTH_DB_PATH", str(tmp_path / "users.sqlite3"))
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def test_login_page_is_minimal_and_never_echoes_password(tmp_path) -> None:
    config = _auth_config(tmp_path)

    html = render_login_page(config, error="密码错误")

    assert "账号登录" in html
    assert "投研工作台" in html
    assert "持仓隔离" in html
    assert "数据共用" in html
    assert "login-side" in html
    assert "login-panel" in html
    assert "密码错误" in html
    assert "owner@example.com" not in html
    assert "secret-password" not in html
    assert 'method="post" action="/login"' in html
    assert 'type="password"' in html


def test_login_page_keeps_credentials_blank_and_supports_remembered_username(tmp_path) -> None:
    config = _auth_config(tmp_path)

    html = render_login_page(config)

    assert 'data-login-form="login"' in html
    assert 'name="username"' in html
    assert 'name="password"' in html
    assert 'value="owner@example.com"' not in html
    assert 'value="secret-password"' not in html
    assert 'autocomplete="off"' in html
    assert "data-remember-username" in html
    assert 'name="remember_username"' in html
    assert "记住账号" in html
    assert "stockTsRememberedUsername" in html
    assert "setItem(rememberKey, username.value.trim())" in html
    assert "setItem(rememberKey, password" not in html


def test_auth_gate_requires_login_when_enabled(tmp_path) -> None:
    config = _auth_config(tmp_path)

    assert should_require_login("/", headers={}, config=config)
    assert not should_require_login("/login", headers={}, config=config)
    assert not should_require_login("/healthz", headers={}, config=config)


def test_auth_gate_accepts_valid_session_cookie(tmp_path) -> None:
    config = _auth_config(tmp_path)
    store = UserStore(config.db_path)
    user = store.bootstrap_admin(config.admin_username, config.admin_password)
    cookie = SessionManager(config.session_secret).issue_session(
        user_id=user.id,
        username=user.username,
    )

    headers = {"Cookie": f"stock_ts_session={cookie}"}

    assert user_from_cookie_header(headers["Cookie"], config=config) is not None
    assert not should_require_login("/", headers=headers, config=config)


def test_auth_gate_is_open_when_disabled(tmp_path) -> None:
    config = AuthConfig(
        enabled=False,
        admin_username="",
        admin_password="",
        db_path=tmp_path / "users.sqlite3",
        session_secret="",
    )

    assert not should_require_login("/", headers={}, config=config)


def test_http_handler_redirects_workbench_to_login_when_auth_enabled(monkeypatch, tmp_path) -> None:
    server = _serve_once(monkeypatch, tmp_path)
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        url = f"http://127.0.0.1:{server.server_port}/"
        try:
            opener.open(url, timeout=5)
        except urllib.error.HTTPError as exc:
            assert exc.code == 303
            assert exc.headers["Location"].startswith("/login?next=%2F")
        else:  # pragma: no cover - defensive
            raise AssertionError("expected redirect")
    finally:
        server.shutdown()
        server.server_close()


def test_http_handler_login_sets_http_only_session_cookie(monkeypatch, tmp_path) -> None:
    server = _serve_once(monkeypatch, tmp_path)
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        payload = urllib.parse.urlencode(
            {
                "username": "owner@example.com",
                "password": "secret-password",
                "next": "/#home",
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"http://127.0.0.1:{server.server_port}/login",
            data=payload,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        try:
            opener.open(request, timeout=5)
        except urllib.error.HTTPError as exc:
            assert exc.code == 303
            assert exc.headers["Location"] == "/#home"
            cookie = exc.headers["Set-Cookie"]
            assert "stock_ts_session=" in cookie
            assert "HttpOnly" in cookie
            assert "SameSite=Lax" in cookie
            assert "secret-password" not in cookie
        else:  # pragma: no cover - defensive
            raise AssertionError("expected redirect")
    finally:
        server.shutdown()
        server.server_close()


def test_settings_page_surfaces_account_system_without_secret_echo(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("STOCK_TS_AUTH_ENABLED", "1")
    monkeypatch.setenv("STOCK_TS_ADMIN_USERNAME", "owner@example.com")
    monkeypatch.setenv("STOCK_TS_ADMIN_PASSWORD", "secret-password")
    monkeypatch.setenv("STOCK_TS_SESSION_SECRET", "session-secret")
    monkeypatch.setenv("STOCK_TS_AUTH_DB_PATH", str(tmp_path / "users.sqlite3"))

    html = render_page(
        stock_code="600519",
        provider_name="sample",
        provider=SampleDataProvider(),
        holdings_path="data/portfolio/holdings.csv",
    )

    assert "每日大盘" in html
    assert "owner@example.com" not in html
    assert 'method="post" action="/logout"' not in html
    assert "secret-password" not in html




def test_authenticated_workbench_has_account_menu_and_logout(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("STOCK_TS_AUTH_ENABLED", "1")
    monkeypatch.setenv("STOCK_TS_ADMIN_USERNAME", "owner@example.com")
    monkeypatch.setenv("STOCK_TS_ADMIN_PASSWORD", "secret-password")
    monkeypatch.setenv("STOCK_TS_SESSION_SECRET", "session-secret")
    monkeypatch.setenv("STOCK_TS_AUTH_DB_PATH", str(tmp_path / "users.sqlite3"))
    user = AuthUser(id=1, username="owner@example.com", role="owner")

    holdings_path = tmp_path / "user-data" / "1" / "holdings.csv"
    holdings_path.parent.mkdir(parents=True)
    holdings_path.write_text("code,name,shares,cost_price,sector,note\n", encoding="utf-8")
    html = render_page(
        stock_code="600519",
        provider_name="sample",
        provider=SampleDataProvider(),
        holdings_path=str(holdings_path),
        current_user=user,
    )

    assert "账户管理" in html
    assert "owner@example.com" in html
    assert "角色：owner" in html
    assert 'method="post" action="/logout"' in html
    assert 'method="post" action="/account/password"' in html
    assert 'data-workspace="account"' in html


def test_member_account_page_hides_global_notification_settings(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("STOCK_TS_AUTH_ENABLED", "1")
    monkeypatch.setenv("STOCK_TS_ADMIN_USERNAME", "owner@example.com")
    monkeypatch.setenv("STOCK_TS_ADMIN_PASSWORD", "secret-password")
    monkeypatch.setenv("STOCK_TS_SESSION_SECRET", "session-secret")
    monkeypatch.setenv("STOCK_TS_AUTH_DB_PATH", str(tmp_path / "users.sqlite3"))
    user = AuthUser(id=2, username="member@example.com", role="member")

    holdings_path = tmp_path / "user-data" / "2" / "holdings.csv"
    holdings_path.parent.mkdir(parents=True)
    holdings_path.write_text("code,name,shares,cost_price,sector,note\n", encoding="utf-8")
    html = render_page(
        stock_code="600519",
        provider_name="sample",
        provider=SampleDataProvider(),
        holdings_path=str(holdings_path),
        current_user=user,
    )
    account_html = html.split('id="account"', 1)[1]

    assert "member@example.com" in account_html
    assert "角色：member" in account_html
    assert "只管理自己的持仓" in account_html
    assert 'method="post" action="/logout"' in account_html
    assert 'method="post" action="/settings"' not in account_html
    assert 'method="post" action="/notification-test"' not in account_html
    assert 'method="post" action="/dispatch-daily"' not in account_html


def test_http_handler_change_password_requires_valid_old_password(monkeypatch, tmp_path) -> None:
    server = _serve_once(monkeypatch, tmp_path)
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        login_payload = urllib.parse.urlencode(
            {
                "username": "owner@example.com",
                "password": "secret-password",
                "next": "/#settings",
            }
        ).encode("utf-8")
        login_request = urllib.request.Request(
            f"http://127.0.0.1:{server.server_port}/login",
            data=login_payload,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        try:
            opener.open(login_request, timeout=5)
        except urllib.error.HTTPError as exc:
            cookie = exc.headers["Set-Cookie"].split(";", 1)[0]
        else:  # pragma: no cover - defensive
            raise AssertionError("expected login redirect")

        change_payload = urllib.parse.urlencode(
            {
                "current_password": "secret-password",
                "new_password": "new-secret-password",
                "confirm_password": "new-secret-password",
            }
        ).encode("utf-8")
        change_request = urllib.request.Request(
            f"http://127.0.0.1:{server.server_port}/account/password",
            data=change_payload,
            method="POST",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Cookie": cookie,
            },
        )
        try:
            opener.open(change_request, timeout=5)
        except urllib.error.HTTPError as exc:
            assert exc.code == 303
            assert "密码已更新" in urllib.parse.unquote(exc.headers["Location"])
        else:  # pragma: no cover - defensive
            raise AssertionError("expected password redirect")

        store = UserStore(tmp_path / "users.sqlite3")
        assert store.authenticate("owner@example.com", "secret-password") is None
        assert store.authenticate("owner@example.com", "new-secret-password") is not None
    finally:
        server.shutdown()
        server.server_close()


def test_settings_page_has_change_password_form(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("STOCK_TS_AUTH_ENABLED", "1")
    monkeypatch.setenv("STOCK_TS_ADMIN_USERNAME", "owner@example.com")
    monkeypatch.setenv("STOCK_TS_ADMIN_PASSWORD", "secret-password")
    monkeypatch.setenv("STOCK_TS_SESSION_SECRET", "session-secret")
    monkeypatch.setenv("STOCK_TS_AUTH_DB_PATH", str(tmp_path / "users.sqlite3"))

    html = render_page(
        stock_code="600519",
        provider_name="sample",
        provider=SampleDataProvider(),
        holdings_path="data/portfolio/holdings.csv",
    )

    assert 'method="post" action="/account/password"' not in html
    assert "每日大盘" in html
    assert "个股分析" in html


def test_login_page_shows_registration_when_enabled(tmp_path) -> None:
    config = AuthConfig(
        enabled=True,
        admin_username="owner@example.com",
        admin_password="secret-password",
        db_path=tmp_path / "users.sqlite3",
        session_secret="session-secret",
        allow_registration=True,
    )

    html = render_login_page(config)

    assert "注册账号" in html
    assert 'method="post" action="/register"' in html
    assert 'name="confirm_password"' in html
    assert "secret-password" not in html
    assert should_allow_registration(config)


def test_http_handler_registers_user_and_sets_session_cookie(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("STOCK_TS_ALLOW_REGISTRATION", "1")
    server = _serve_once(monkeypatch, tmp_path)
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        payload = urllib.parse.urlencode(
            {
                "username": "newuser@example.com",
                "password": "member-secret",
                "confirm_password": "member-secret",
                "next": "/#home",
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"http://127.0.0.1:{server.server_port}/register",
            data=payload,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        try:
            opener.open(request, timeout=5)
        except urllib.error.HTTPError as exc:
            assert exc.code == 303
            assert exc.headers["Location"] == "/#home"
            cookie = exc.headers["Set-Cookie"]
            assert "stock_ts_session=" in cookie
            assert "HttpOnly" in cookie
        else:  # pragma: no cover - defensive
            raise AssertionError("expected register redirect")

        store = UserStore(tmp_path / "users.sqlite3")
        assert store.authenticate("newuser@example.com", "member-secret") is not None
    finally:
        server.shutdown()
        server.server_close()


def test_authenticated_users_get_isolated_holdings_files(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("STOCK_TS_USER_DATA_DIR", str(tmp_path / "user-data"))
    server = _serve_once(monkeypatch, tmp_path)
    opener = urllib.request.build_opener(_NoRedirect)
    store = UserStore(tmp_path / "users.sqlite3")
    alice = store.register_user("alice@example.com", "alice-secret")
    bob = store.register_user("bob@example.com", "bob-secret")

    def cookie_for(user_id: int, username: str) -> str:
        token = SessionManager("session-secret").issue_session(
            user_id=user_id,
            username=username,
        )
        return f"stock_ts_session={token}"

    def post_holding(cookie: str, code: str, name: str) -> None:
        payload = urllib.parse.urlencode(
            {
                "page_code": code,
                "portfolio_action": "upsert",
                "holding_code": code,
                "holding_name": name,
                "holding_shares": "100",
                "holding_cost_price": "10",
                "holding_sector": "测试",
                "holding_note": "账号隔离测试",
                "holdings_path": str(tmp_path / "attacker.csv"),
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"http://127.0.0.1:{server.server_port}/holdings",
            data=payload,
            method="POST",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Cookie": cookie,
            },
        )
        try:
            opener.open(request, timeout=5)
        except urllib.error.HTTPError as exc:
            assert exc.code == 303
            assert "attacker.csv" not in urllib.parse.unquote(exc.headers["Location"])
        else:  # pragma: no cover - defensive
            raise AssertionError("expected holdings redirect")

    try:
        post_holding(cookie_for(alice.id, alice.username), "000001", "平安银行")
        post_holding(cookie_for(bob.id, bob.username), "000002", "万科A")

        alice_path = tmp_path / "user-data" / str(alice.id) / "holdings.csv"
        bob_path = tmp_path / "user-data" / str(bob.id) / "holdings.csv"
        assert alice_path.exists()
        assert bob_path.exists()
        assert not (tmp_path / "attacker.csv").exists()
        assert "000001" in {item.code for item in load_holdings_csv(alice_path)}
        assert "000001" not in {item.code for item in load_holdings_csv(bob_path)}
        assert "000002" in {item.code for item in load_holdings_csv(bob_path)}
    finally:
        server.shutdown()
        server.server_close()


def test_new_authenticated_user_holdings_file_starts_empty(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("STOCK_TS_USER_DATA_DIR", str(tmp_path / "user-data"))
    user = UserStore(tmp_path / "users.sqlite3").register_user(
        "member@example.com",
        "member-secret",
    )

    holdings_path = _ensure_user_holdings_file(user)

    assert holdings_path == tmp_path / "user-data" / str(user.id) / "holdings.csv"
    assert holdings_path.read_text(encoding="utf-8") == (
        "code,name,shares,cost_price,sector,note\n"
    )


def test_effective_holdings_path_keeps_explicit_path_when_auth_disabled(tmp_path) -> None:
    explicit = str(tmp_path / "holdings.csv")

    assert _effective_holdings_path(None, explicit) == explicit


def test_member_cannot_update_global_settings(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("STOCK_TS_USER_DATA_DIR", str(tmp_path / "user-data"))
    server = _serve_once(monkeypatch, tmp_path)
    opener = urllib.request.build_opener(_NoRedirect)
    store = UserStore(tmp_path / "users.sqlite3")
    member = store.register_user("member@example.com", "member-secret")
    token = SessionManager("session-secret").issue_session(
        user_id=member.id,
        username=member.username,
    )
    payload = urllib.parse.urlencode(
        {
            "page_code": "600519",
            "settings_provider": "sample",
            "email_sender": "member@example.com",
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"http://127.0.0.1:{server.server_port}/settings",
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Cookie": f"stock_ts_session={token}",
        },
    )
    try:
        try:
            opener.open(request, timeout=5)
        except urllib.error.HTTPError as exc:
            assert exc.code == 403
        else:  # pragma: no cover - defensive
            raise AssertionError("expected member settings request to be forbidden")
    finally:
        server.shutdown()
        server.server_close()
