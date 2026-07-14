from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

import stock_ts.web as web_module
from stock_ts.web import (
    Handler,
    ResearchRateLimiter,
    _build_iwencai_stock_query,
    _parse_iwencai_research_payload,
    _research_client_key,
)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


def _serve(
    monkeypatch,
    tmp_path,
    *,
    auth_enabled: bool = False,
    public_readonly: bool = False,
    allow_anonymous: bool = True,
) -> ThreadingHTTPServer:
    monkeypatch.setenv("STOCK_TS_AUTH_ENABLED", "1" if auth_enabled else "0")
    monkeypatch.setenv("STOCK_TS_AUTH_DB_PATH", str(tmp_path / "users.sqlite3"))
    monkeypatch.setenv("STOCK_TS_ADMIN_USERNAME", "owner@example.com")
    monkeypatch.setenv("STOCK_TS_ADMIN_PASSWORD", "secret-password")
    monkeypatch.setenv("STOCK_TS_SESSION_SECRET", "session-secret")
    monkeypatch.setenv("STOCK_TS_PUBLIC_READONLY", "1" if public_readonly else "0")
    monkeypatch.setenv(
        "STOCK_TS_IWENCAI_ALLOW_ANONYMOUS",
        "1" if allow_anonymous else "0",
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def _request(
    server: ThreadingHTTPServer,
    payload: bytes,
    *,
    content_type: str = "application/json",
):
    request = urllib.request.Request(
        f"http://127.0.0.1:{server.server_port}/api/iwencai/research",
        data=payload,
        method="POST",
        headers={"Content-Type": content_type},
    )
    return urllib.request.build_opener(NoRedirect).open(request, timeout=5)


def _error_json(exc: urllib.error.HTTPError) -> dict[str, object]:
    return json.loads(exc.read().decode("utf-8"))


def test_parse_research_payload_rejects_invalid_or_oversized_questions() -> None:
    with pytest.raises(ValueError, match="JSON"):
        _parse_iwencai_research_payload(b"not-json")
    with pytest.raises(ValueError, match="200"):
        _parse_iwencai_research_payload(
            json.dumps({"code": "600519", "name": "贵州茅台", "question": "问" * 201}).encode()
        )


def test_parse_module_payloads_keep_only_allowlisted_context() -> None:
    market = _parse_iwencai_research_payload(
        json.dumps(
            {
                "module": "market",
                "question": "三大指数结构",
                "context": {"local_as_of": "2026-07-14", "code": "600519"},
            },
            ensure_ascii=False,
        ).encode()
    )
    portfolio = _parse_iwencai_research_payload(
        json.dumps(
            {
                "module": "portfolio",
                "question": "公告风险",
                "context": {
                    "code": "600519",
                    "name": "贵州茅台",
                    "shares": "100",
                    "cost_price": "1500",
                    "weight": "20%",
                },
            },
            ensure_ascii=False,
        ).encode()
    )

    assert market == {
        "module": "market",
        "code": "",
        "name": "",
        "sector": "",
        "question": "三大指数结构",
        "local_as_of": "2026-07-14",
    }
    assert portfolio == {
        "module": "portfolio",
        "code": "600519",
        "name": "贵州茅台",
        "sector": "",
        "question": "公告风险",
        "local_as_of": "",
    }
    assert "shares" not in portfolio
    assert "cost_price" not in portfolio
    assert "weight" not in portfolio


@pytest.mark.parametrize(
    "payload",
    [
        {"module": "settings", "question": "配置"},
        {"module": "portfolio", "question": "公告风险", "context": {}},
        {"module": "opportunity", "question": "板块持续性", "context": {}},
    ],
)
def test_parse_module_payload_rejects_invalid_context(payload: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        _parse_iwencai_research_payload(json.dumps(payload, ensure_ascii=False).encode())


def test_parse_research_payload_keeps_legacy_stock_contract() -> None:
    payload = _parse_iwencai_research_payload(
        json.dumps(
            {"code": "600519", "name": "贵州茅台", "question": "净利润"},
            ensure_ascii=False,
        ).encode()
    )

    assert payload["module"] == "stock"
    assert payload["code"] == "600519"
    assert payload["name"] == "贵州茅台"


def test_build_stock_query_binds_question_to_current_stock_and_removes_controls() -> None:
    query = _build_iwencai_stock_query(
        code="600519\x00",
        name="贵州茅台\n",
        question="未来两年盈利预期？\r",
    )

    assert query == "贵州茅台 600519 未来两年盈利预期？"


def test_research_rate_limiter_expires_old_requests() -> None:
    limiter = ResearchRateLimiter(limit=2, window_seconds=60)

    assert limiter.allow("127.0.0.1", now=100)
    assert limiter.allow("127.0.0.1", now=101)
    assert not limiter.allow("127.0.0.1", now=102)
    assert limiter.allow("127.0.0.1", now=161)


def test_research_client_key_only_trusts_proxy_headers_from_loopback() -> None:
    assert _research_client_key(
        {"X-Real-IP": "203.0.113.8"},
        ("127.0.0.1", 51234),
    ) == "ip:203.0.113.8"
    assert _research_client_key(
        {"X-Real-IP": "198.51.100.99"},
        ("203.0.113.9", 51234),
    ) == "ip:203.0.113.9"
    assert _research_client_key(
        {"X-Real-IP": "not-an-ip"},
        ("127.0.0.1", 51234),
    ) == "ip:127.0.0.1"


def test_research_endpoint_requires_login_when_auth_is_enabled(monkeypatch, tmp_path) -> None:
    server = _serve(monkeypatch, tmp_path, auth_enabled=True)
    try:
        with pytest.raises(urllib.error.HTTPError) as caught:
            _request(
                server,
                json.dumps({"code": "600519", "name": "贵州茅台", "question": "净利润"}).encode(),
            )

        assert caught.value.code == 401
        assert _error_json(caught.value)["status"] == "login_required"
    finally:
        server.shutdown()
        server.server_close()


def test_research_endpoint_reports_missing_server_key_in_local_mode(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.delenv("IWENCAI_API_KEY", raising=False)
    server = _serve(monkeypatch, tmp_path)
    try:
        with pytest.raises(urllib.error.HTTPError) as caught:
            _request(
                server,
                json.dumps({"code": "600519", "name": "贵州茅台", "question": "净利润"}).encode(),
            )

        body = _error_json(caught.value)
        assert caught.value.code == 503
        assert body["status"] == "missing_config"
        assert body["config"] == {"status": "missing", "provider": "同花顺问财"}
        assert "IWENCAI_API_KEY" in body["message"]
    finally:
        server.shutdown()
        server.server_close()


def test_public_readonly_endpoint_is_disabled_when_auth_is_off(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("IWENCAI_API_KEY", "iwc-endpoint-secret")
    server = _serve(monkeypatch, tmp_path, public_readonly=True)
    try:
        with pytest.raises(urllib.error.HTTPError) as caught:
            _request(
                server,
                json.dumps({"code": "600519", "name": "贵州茅台", "question": "净利润"}).encode(),
            )

        assert caught.value.code == 401
        body = _error_json(caught.value)
        assert body["status"] == "login_required"
        assert "公网" in body["message"]
    finally:
        server.shutdown()
        server.server_close()


def test_endpoint_is_secure_by_default_when_auth_is_off(monkeypatch, tmp_path) -> None:
    server = _serve(monkeypatch, tmp_path, allow_anonymous=False)
    try:
        with pytest.raises(urllib.error.HTTPError) as caught:
            _request(
                server,
                json.dumps({"code": "600519", "name": "贵州茅台", "question": "净利润"}).encode(),
            )

        assert caught.value.code == 401
        assert _error_json(caught.value)["status"] == "login_required"
    finally:
        server.shutdown()
        server.server_close()


def test_research_endpoint_returns_structured_result_without_secret(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("IWENCAI_API_KEY", "iwc-endpoint-secret")
    captured: dict[str, object] = {}

    def fake_ask(payload: dict[str, str]) -> dict[str, object]:
        captured.update(payload)
        return {
            "ok": True,
            "status": "complete",
            "summary": "返回 1 条事实",
            "facts": [{"股票简称": "贵州茅台", "净利润": "862.3亿"}],
        }

    monkeypatch.setattr(web_module, "_ask_iwencai_stock_research", fake_ask)
    server = _serve(monkeypatch, tmp_path)
    try:
        with _request(
            server,
            json.dumps(
                {
                    "code": "600519",
                    "name": "贵州茅台",
                    "question": "净利润质量怎么样",
                    "local_as_of": "2026-07-13",
                },
                ensure_ascii=False,
            ).encode("utf-8"),
        ) as response:
            body = json.loads(response.read().decode("utf-8"))

        assert response.status == 200
        assert response.headers["Content-Type"] == "application/json; charset=utf-8"
        assert body["facts"][0]["净利润"] == "862.3亿"
        assert captured["question"] == "净利润质量怎么样"
        assert "iwc-endpoint-secret" not in json.dumps(body, ensure_ascii=False)
    finally:
        server.shutdown()
        server.server_close()


def test_market_endpoint_passes_only_normalized_module_payload(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("IWENCAI_API_KEY", "iwc-endpoint-secret")
    captured: dict[str, object] = {}

    def fake_ask(payload: dict[str, str]) -> dict[str, object]:
        captured.update(payload)
        return {
            "ok": True,
            "status": "complete",
            "module": "market",
            "summary": "返回市场事实",
            "facts": [{"指数简称": "上证指数"}],
        }

    monkeypatch.setattr(web_module, "_ask_iwencai_stock_research", fake_ask)
    server = _serve(monkeypatch, tmp_path)
    try:
        with _request(
            server,
            json.dumps(
                {
                    "module": "market",
                    "question": "三大指数结构",
                    "context": {
                        "local_as_of": "2026-07-14",
                        "shares": "100",
                        "cost_price": "1500",
                    },
                },
                ensure_ascii=False,
            ).encode(),
        ) as response:
            body = json.loads(response.read().decode())

        assert response.status == 200
        assert body["module"] == "market"
        assert captured["module"] == "market"
        assert "shares" not in captured
        assert "cost_price" not in captured
    finally:
        server.shutdown()
        server.server_close()


def test_research_endpoint_rejects_wrong_content_type_and_large_body(monkeypatch, tmp_path) -> None:
    server = _serve(monkeypatch, tmp_path)
    try:
        with pytest.raises(urllib.error.HTTPError) as wrong_type:
            _request(server, b"question=test", content_type="application/x-www-form-urlencoded")
        assert wrong_type.value.code == 415

        with pytest.raises(urllib.error.HTTPError) as too_large:
            _request(server, b"{" + b"x" * (16 * 1024) + b"}")
        assert too_large.value.code == 413
    finally:
        server.shutdown()
        server.server_close()


def test_research_endpoint_returns_429_when_client_is_rate_limited(monkeypatch, tmp_path) -> None:
    class DenyAll:
        def allow(self, _key: str) -> bool:
            return False

    monkeypatch.setattr(web_module, "IWENCAI_RESEARCH_RATE_LIMITER", DenyAll())
    server = _serve(monkeypatch, tmp_path)
    try:
        with pytest.raises(urllib.error.HTTPError) as caught:
            _request(
                server,
                json.dumps({"code": "600519", "name": "贵州茅台", "question": "净利润"}).encode(),
            )

        assert caught.value.code == 429
        assert _error_json(caught.value)["status"] == "rate_limited"
    finally:
        server.shutdown()
        server.server_close()
