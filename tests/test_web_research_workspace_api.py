from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from http.server import ThreadingHTTPServer

import pytest

import stock_ts.web as web_module
from stock_ts.providers.sample import SampleDataProvider
from stock_ts.research_engine import (
    ResearchContext,
    ResearchModuleItem,
    ResearchWorkspaceResult,
)
from stock_ts.research_snapshots import ResearchSnapshotStore
from stock_ts.web import (
    Handler,
    ResearchRateLimiter,
    _parse_research_workspace_payload,
)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


def _serve(monkeypatch, tmp_path, *, auth_enabled: bool = False) -> ThreadingHTTPServer:
    monkeypatch.setenv("STOCK_TS_AUTH_ENABLED", "1" if auth_enabled else "0")
    monkeypatch.setenv("STOCK_TS_AUTH_DB_PATH", str(tmp_path / "users.sqlite3"))
    monkeypatch.setenv("STOCK_TS_ADMIN_USERNAME", "owner@example.com")
    monkeypatch.setenv("STOCK_TS_ADMIN_PASSWORD", "secret-password")
    monkeypatch.setenv("STOCK_TS_SESSION_SECRET", "session-secret")
    monkeypatch.setenv("STOCK_TS_PUBLIC_READONLY", "0")
    monkeypatch.setenv("STOCK_TS_IWENCAI_ALLOW_ANONYMOUS", "1")
    monkeypatch.setattr(
        web_module,
        "IWENCAI_RESEARCH_RATE_LIMITER",
        ResearchRateLimiter(limit=20, window_seconds=60),
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
        f"http://127.0.0.1:{server.server_port}/api/research/workspace",
        data=payload,
        method="POST",
        headers={"Content-Type": content_type},
    )
    return urllib.request.build_opener(NoRedirect).open(request, timeout=5)


def _error_json(exc: urllib.error.HTTPError) -> dict[str, object]:
    return json.loads(exc.read().decode("utf-8"))


def test_parse_workspace_payload_keeps_only_product_context() -> None:
    parsed = _parse_research_workspace_payload(
        json.dumps(
            {
                "module": "portfolio",
                "skill": "arbitrary",
                "provider": "arbitrary",
                "refresh": True,
                "context": {
                    "holdings": [
                        {
                            "code": "600519",
                            "name": "贵州茅台",
                            "shares": 100,
                            "cost_price": 1500,
                            "weight": "30%",
                        }
                    ],
                    "account": "private",
                },
            },
            ensure_ascii=False,
        ).encode()
    )

    assert set(parsed) == {"module", "context", "refresh"}
    assert parsed["module"] == "portfolio"
    assert parsed["refresh"] is True
    context = parsed["context"]
    assert context.holdings[0].code == "600519"
    assert context.holdings[0].name == "贵州茅台"
    assert not hasattr(context.holdings[0], "shares")


@pytest.mark.parametrize(
    "payload",
    [
        b"not-json",
        json.dumps({"module": "settings"}).encode(),
        json.dumps({"module": "stock", "refresh": "yes"}).encode(),
        json.dumps({"module": "stock", "context": []}).encode(),
    ],
)
def test_parse_workspace_payload_rejects_invalid_contract(payload: bytes) -> None:
    with pytest.raises(ValueError):
        _parse_research_workspace_payload(payload)


def test_workspace_endpoint_returns_supplier_neutral_product_result(
    monkeypatch,
    tmp_path,
) -> None:
    captured: dict[str, object] = {}

    def fake_response(payload: dict[str, object]) -> dict[str, object]:
        captured.update(payload)
        return {
            "ok": True,
            "status": "complete",
            "module": "stock",
            "generated_at": "2026-07-14T16:00:00+08:00",
            "verdict": "公司核心证据已更新。",
            "action": "先核对关键变化。",
            "primary_risk": "单一变化不能构成买卖依据。",
            "findings": [],
            "details": [],
            "missing_sections": [],
        }

    monkeypatch.setattr(web_module, "_research_workspace_response", fake_response)
    server = _serve(monkeypatch, tmp_path)
    try:
        with _request(
            server,
            json.dumps(
                {
                    "module": "stock",
                    "context": {
                        "code": "600519",
                        "name": "贵州茅台",
                        "holdings_path": "/tmp/browser-controlled.csv",
                    },
                    "refresh": False,
                },
                ensure_ascii=False,
            ).encode(),
        ) as response:
            body = json.loads(response.read().decode())

        assert response.status == 200
        assert response.headers["Cache-Control"] == "no-store"
        assert captured["module"] == "stock"
        assert captured["holdings_path"] == "data/portfolio/holdings.csv"
        serialized = json.dumps(body, ensure_ascii=False)
        for forbidden in (
            "问财",
            "iWencai",
            "同花顺",
            "skill_id",
            "trace_id",
            "openapi",
        ):
            assert forbidden not in serialized
    finally:
        server.shutdown()
        server.server_close()


def test_workspace_response_prefers_fresh_global_snapshot(monkeypatch, tmp_path) -> None:
    snapshot_dir = tmp_path / "research"
    monkeypatch.setenv("STOCK_TS_RESEARCH_SNAPSHOT_DIR", str(snapshot_dir))
    store = ResearchSnapshotStore(snapshot_dir)
    store.save(
        "market",
        {
            "ok": True,
            "status": "complete",
            "module": "market",
            "generated_at": "2026-07-15T07:20:00+08:00",
            "verdict": "快照判断",
            "action": "保持观察",
            "primary_risk": "成交缩量",
            "findings": [],
            "details": [],
            "missing_sections": [],
            "module_items": [],
            "module_sections": [
                {"key": "market-pulse", "items": []},
                {"key": "market-continuation", "items": []},
                {"key": "market-movers", "items": []},
            ],
        },
    )

    class ExplodingService:
        def research(self, *_args, **_kwargs):
            raise AssertionError("fresh snapshot must avoid live research")

    monkeypatch.setattr(web_module, "RESEARCH_WORKSPACE_SERVICE", ExplodingService())

    response = web_module._research_workspace_response(
        {"module": "market", "context": ResearchContext(), "refresh": False}
    )

    assert response["verdict"] == "快照判断"
    assert response["delivery"] == "snapshot"


def test_workspace_response_uses_stale_snapshot_when_service_is_unconfigured(
    monkeypatch,
    tmp_path,
) -> None:
    snapshot_dir = tmp_path / "research"
    monkeypatch.setenv("STOCK_TS_RESEARCH_SNAPSHOT_DIR", str(snapshot_dir))
    monkeypatch.delenv("IWENCAI_API_KEY", raising=False)
    generated_at = (
        datetime.now(timezone(timedelta(hours=8))) - timedelta(days=2)
    ).isoformat(timespec="seconds")
    ResearchSnapshotStore(snapshot_dir).save(
        "market",
        {
            "ok": True,
            "status": "partial",
            "module": "market",
            "generated_at": generated_at,
            "verdict": "历史快照判断",
            "action": "等待服务恢复",
            "primary_risk": "数据已过期",
            "findings": [],
            "details": [],
            "missing_sections": [],
            "module_items": [],
            "module_sections": [
                {"key": "market-pulse", "items": []},
                {"key": "market-continuation", "items": []},
                {"key": "market-movers", "items": []},
            ],
        },
    )

    response = web_module._research_workspace_response(
        {"module": "market", "context": ResearchContext(), "refresh": True}
    )

    assert response["verdict"] == "历史快照判断"
    assert response["delivery"] == "stale_snapshot"
    assert response["stale"] is True


def test_workspace_response_rebuilds_incompatible_market_snapshot(
    monkeypatch,
    tmp_path,
) -> None:
    snapshot_dir = tmp_path / "research"
    monkeypatch.setenv("STOCK_TS_RESEARCH_SNAPSHOT_DIR", str(snapshot_dir))
    monkeypatch.delenv("IWENCAI_API_KEY", raising=False)
    monkeypatch.setattr(web_module, "create_provider", lambda _name: SampleDataProvider())
    ResearchSnapshotStore(snapshot_dir).save(
        "market",
        {
            "ok": True,
            "status": "partial",
            "module": "market",
            "generated_at": "2026-07-15T07:20:00+08:00",
            "verdict": "旧协议快照",
            "action": "等待",
            "primary_risk": "旧协议没有异动列表",
            "findings": [],
            "details": [],
            "missing_sections": [],
            "module_items": [],
            "module_sections": [
                {"key": "market-pulse", "items": []},
                {"key": "market-movers", "items": []},
            ],
        },
    )

    response = web_module._research_workspace_response(
        {"module": "market", "context": ResearchContext(), "refresh": False}
    )

    assert response["verdict"] != "旧协议快照"
    assert response["delivery"] == "local_fallback"
    keys = {section["key"] for section in response["module_sections"]}
    assert {"market-pulse", "market-continuation", "market-movers"} <= keys


def test_workspace_response_uses_local_stock_evidence_when_service_is_unconfigured(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("STOCK_TS_RESEARCH_SNAPSHOT_DIR", str(tmp_path / "research"))
    monkeypatch.delenv("IWENCAI_API_KEY", raising=False)
    monkeypatch.setattr(web_module, "create_provider", lambda _name: SampleDataProvider())

    response = web_module._research_workspace_response(
        {
            "module": "stock",
            "context": ResearchContext(code="603278", name="大业股份"),
            "refresh": True,
            "holdings_path": str(tmp_path / "private-holdings.csv"),
        }
    )

    assert response["delivery"] == "local_fallback"
    assert response["verdict"]
    assert response["findings"]
    assert response["module_items"]


def test_workspace_response_keeps_local_decision_when_enrichment_succeeds(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("STOCK_TS_RESEARCH_SNAPSHOT_DIR", str(tmp_path / "research"))
    monkeypatch.setenv("IWENCAI_API_KEY", "configured-for-test")
    monkeypatch.setattr(web_module, "create_provider", lambda _name: SampleDataProvider())

    class EnrichedService:
        def research(self, *_args, **_kwargs):
            return ResearchWorkspaceResult(
                ok=True,
                status="complete",
                module="stock",
                generated_at="2026-07-15T20:00:00+08:00",
                verdict="外部结论不应接管",
                action="外部动作不应接管",
                primary_risk="外部风险不应接管",
                module_items=(
                    ResearchModuleItem(
                        kind="stock_dimension",
                        label="财务质量",
                        summary="营收与利润证据已补齐。",
                        risk="现金流仍需复核。",
                        status="ready",
                    ),
                ),
                decision_label="外部买入",
            )

    monkeypatch.setattr(web_module, "RESEARCH_WORKSPACE_SERVICE", EnrichedService())

    response = web_module._research_workspace_response(
        {
            "module": "stock",
            "context": ResearchContext(code="603278", name="大业股份"),
            "refresh": True,
            "holdings_path": str(tmp_path / "private-holdings.csv"),
        }
    )

    assert response["delivery"] == "hybrid"
    assert response["data_label"] == "综合证据"
    assert response["verdict"] != "外部结论不应接管"
    assert response["action"] != "外部动作不应接管"
    assert response["decision_label"] != "外部买入"
    financial = next(
        item for item in response["module_items"] if item["label"] == "财务质量"
    )
    assert financial["status"] == "ready"
    assert "营收与利润" in financial["summary"]


def test_workspace_endpoint_requires_login_when_auth_is_enabled(
    monkeypatch,
    tmp_path,
) -> None:
    server = _serve(monkeypatch, tmp_path, auth_enabled=True)
    try:
        with pytest.raises(urllib.error.HTTPError) as caught:
            _request(
                server,
                json.dumps({"module": "market", "context": {}}).encode(),
            )

        assert caught.value.code == 401
        assert _error_json(caught.value)["status"] == "login_required"
    finally:
        server.shutdown()
        server.server_close()


def test_workspace_endpoint_rejects_wrong_content_type_and_large_body(
    monkeypatch,
    tmp_path,
) -> None:
    server = _serve(monkeypatch, tmp_path)
    try:
        with pytest.raises(urllib.error.HTTPError) as wrong_type:
            _request(server, b"module=market", content_type="application/x-www-form-urlencoded")
        assert wrong_type.value.code == 415

        with pytest.raises(urllib.error.HTTPError) as too_large:
            _request(server, b"{" + b"x" * (16 * 1024) + b"}")
        assert too_large.value.code == 413
    finally:
        server.shutdown()
        server.server_close()
