from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from http.server import ThreadingHTTPServer

import pytest
from bs4 import BeautifulSoup

import stock_ts.web as web_module
from stock_ts.auth import SessionManager, UserStore
from stock_ts.iwencai import (
    SKILLS,
    IwencaiConfigurationError,
    IwencaiError,
    IwencaiGatewayError,
)
from stock_ts.providers.sample import SampleDataProvider
from stock_ts.research_engine import (
    ResearchContext,
    ResearchModuleItem,
    ResearchWorkspaceResult,
)
from stock_ts.research_snapshots import RESEARCH_CONTRACT_VERSION, ResearchSnapshotStore
from stock_ts.stock_deep_research import StockDeepResearchService
from stock_ts.web import (
    Handler,
    ResearchRateLimiter,
    _parse_prediction_feedback_payload,
    _parse_research_workspace_payload,
    _parse_stock_deep_research_payload,
)
from stock_ts.webapp.engine_workspace import engine_app_script


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


def _deep_request(
    server: ThreadingHTTPServer,
    payload: bytes,
    *,
    content_type: str = "application/json",
    cookie: str = "",
):
    headers = {"Content-Type": content_type}
    if cookie:
        headers["Cookie"] = cookie
    request = urllib.request.Request(
        f"http://127.0.0.1:{server.server_port}/api/research/stock/deep",
        data=payload,
        method="POST",
        headers=headers,
    )
    return urllib.request.build_opener(NoRedirect).open(request, timeout=5)


def _authenticated_cookie(tmp_path) -> str:
    user = UserStore(tmp_path / "users.sqlite3").bootstrap_admin(
        "owner@example.com",
        "secret-password",
    )
    token = SessionManager("session-secret").issue_session(
        user_id=user.id,
        username=user.username,
    )
    return f"stock_ts_session={token}"


def _cookie_for_user(user) -> str:  # noqa: ANN001
    token = SessionManager("session-secret").issue_session(
        user_id=user.id,
        username=user.username,
    )
    return f"stock_ts_session={token}"


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


def test_parse_prediction_feedback_payload_allowlists_product_values() -> None:
    parsed = _parse_prediction_feedback_payload(
        json.dumps(
            {
                "prediction_id": "abc123",
                "usefulness": "有用",
                "reason_accuracy": "原因正确",
                "disposition": "已关注",
                "provider": "must-be-ignored",
            },
            ensure_ascii=False,
        ).encode()
    )

    assert parsed == {
        "prediction_id": "abc123",
        "usefulness": "有用",
        "reason_accuracy": "原因正确",
        "disposition": "已关注",
    }


@pytest.mark.parametrize(
    "field,value",
    [
        ("prediction_id", ""),
        ("usefulness", "一般"),
        ("reason_accuracy", "不知道"),
        ("disposition", "已买入"),
    ],
)
def test_parse_prediction_feedback_payload_rejects_unknown_values(field, value) -> None:
    payload = {
        "prediction_id": "abc123",
        "usefulness": "有用",
        "reason_accuracy": "原因正确",
        "disposition": "已关注",
    }
    payload[field] = value

    with pytest.raises(ValueError):
        _parse_prediction_feedback_payload(json.dumps(payload, ensure_ascii=False).encode())


def test_local_opportunity_response_appends_prediction_feedback(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("STOCK_TS_RESEARCH_SNAPSHOT_DIR", str(tmp_path / "research"))
    monkeypatch.setenv("STOCK_TS_PREDICTION_DB", str(tmp_path / "predictions.sqlite3"))
    monkeypatch.delenv("IWENCAI_API_KEY", raising=False)
    monkeypatch.setattr(web_module, "create_provider", lambda _name: SampleDataProvider())

    response = web_module._research_workspace_response(
        {"module": "opportunity", "context": ResearchContext(), "refresh": True}
    )

    feedback = next(
        section
        for section in response["module_sections"]
        if section["key"] == "opportunity-feedback"
    )
    assert feedback["conclusion"] == "暂无可回评样本"
    rendered_feedback = json.dumps(feedback, ensure_ascii=False)
    assert "3日命中率" not in rendered_feedback
    assert "平均超额" not in rendered_feedback
    assert "平均MAE" not in rendered_feedback
    assert "0.0%" not in rendered_feedback
    assert "provider" not in rendered_feedback.lower()


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
    generated_at = datetime.now(timezone(timedelta(hours=8))).isoformat(
        timespec="seconds"
    )
    store = ResearchSnapshotStore(snapshot_dir)
    store.save(
        "market",
        {
            "research_contract_version": RESEARCH_CONTRACT_VERSION,
            "ok": True,
            "status": "complete",
            "module": "market",
            "generated_at": generated_at,
            "verdict": "快照判断",
            "action": "保持观察",
            "primary_risk": "成交缩量",
            "findings": [],
            "details": [],
            "missing_sections": [],
            "module_items": [],
                "module_sections": [
                    {"key": "market-pulse", "items": []},
                    {"key": "market-breadth", "items": []},
                    {"key": "market-themes", "items": []},
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


def test_native_page_embeds_latest_market_snapshot_for_instant_open(
    monkeypatch,
    tmp_path,
) -> None:
    snapshot_dir = tmp_path / "research"
    report_dir = tmp_path / "daily"
    report_dir.mkdir()
    monkeypatch.setenv("STOCK_TS_RESEARCH_SNAPSHOT_DIR", str(snapshot_dir))
    monkeypatch.setenv("STOCK_TS_DAILY_REPORT_DIR", str(report_dir))
    monkeypatch.setenv("STOCK_TS_AUTH_ENABLED", "0")
    monkeypatch.setenv("STOCK_TS_PUBLIC_READONLY", "0")
    monkeypatch.setenv("STOCK_TS_IWENCAI_ALLOW_ANONYMOUS", "1")
    monkeypatch.delenv("IWENCAI_API_KEY", raising=False)
    (report_dir / "pipeline.status").write_text(
        "status=ok\ncompleted_at=2026-07-18T09:31:38+08:00\n"
        "snapshot_version=published-v1\n",
        encoding="utf-8",
    )
    ResearchSnapshotStore(snapshot_dir).save(
        "market",
        {
            "research_contract_version": RESEARCH_CONTRACT_VERSION,
            "source_snapshot_version": "published-v1",
            "source_pipeline_completed_at": "2026-07-18T09:31:38+08:00",
            "ok": True,
            "status": "complete",
            "module": "market",
            "generated_at": "2026-07-18T09:31:50+08:00",
            "verdict": "定时快照已经准备好",
            "action": "打开页面直接查看。",
            "primary_risk": "等待下一次定时更新。",
            "findings": [],
            "details": [],
            "missing_sections": [],
            "module_items": [],
            "module_sections": [
                {"key": "market-pulse", "items": []},
                {"key": "market-breadth", "items": []},
                {"key": "market-themes", "items": []},
                {"key": "market-movers", "items": []},
            ],
        },
    )

    soup = BeautifulSoup(web_module.render_page(stock_code="600519"), "html.parser")
    bootstrap = soup.select_one(
        '#market [data-engine-workspace="market"] script[data-engine-bootstrap-payload]'
    )

    assert bootstrap is not None
    payload = json.loads(bootstrap.get_text())
    assert payload["verdict"] == "定时快照已经准备好"
    assert payload["delivery"] == "snapshot"


def test_engine_bootstrap_uses_embedded_result_without_open_request() -> None:
    script = engine_app_script()

    assert "function hydrateEngineBootstrap" in script
    assert "const hydrated = hydrateEngineBootstrap(workspace);" in script
    assert "if (!hydrated) runEngineWorkspace(workspace, false);" in script


def test_native_page_does_not_preload_previous_pipeline_snapshot(
    monkeypatch,
    tmp_path,
) -> None:
    snapshot_dir = tmp_path / "research"
    report_dir = tmp_path / "daily"
    report_dir.mkdir()
    monkeypatch.setenv("STOCK_TS_RESEARCH_SNAPSHOT_DIR", str(snapshot_dir))
    monkeypatch.setenv("STOCK_TS_DAILY_REPORT_DIR", str(report_dir))
    (report_dir / "pipeline.status").write_text(
        "status=ok\nsnapshot_version=published-v2\n",
        encoding="utf-8",
    )
    ResearchSnapshotStore(snapshot_dir).save(
        "market",
        {
            "research_contract_version": RESEARCH_CONTRACT_VERSION,
            "source_snapshot_version": "published-v1",
            "ok": True,
            "status": "complete",
            "module": "market",
            "generated_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
            "verdict": "上一轮判断",
            "action": "不能直出",
            "primary_risk": "数据版本已经变化",
            "module_sections": [
                {"key": "market-pulse", "items": []},
                {"key": "market-breadth", "items": []},
                {"key": "market-themes", "items": []},
                {"key": "market-movers", "items": []},
            ],
        },
    )

    assert web_module._load_initial_research_snapshot("market") is None


def test_workspace_response_rejects_snapshot_older_than_latest_pipeline(
    monkeypatch,
    tmp_path,
) -> None:
    snapshot_dir = tmp_path / "research"
    report_dir = tmp_path / "daily"
    report_dir.mkdir()
    monkeypatch.setenv("STOCK_TS_RESEARCH_SNAPSHOT_DIR", str(snapshot_dir))
    monkeypatch.setenv("STOCK_TS_DAILY_REPORT_DIR", str(report_dir))
    monkeypatch.setenv("IWENCAI_API_KEY", "configured-for-test")
    monkeypatch.setattr(web_module, "create_provider", lambda _name: SampleDataProvider())
    (report_dir / "pipeline.status").write_text(
        "status=ok\ncompleted_at=2026-07-16T09:24:29+08:00\n"
        "snapshot_version=published-v2\n",
        encoding="utf-8",
    )
    ResearchSnapshotStore(snapshot_dir).save(
        "market",
        {
            "research_contract_version": RESEARCH_CONTRACT_VERSION,
            "ok": True,
            "status": "partial",
            "module": "market",
            "generated_at": "2026-07-16T07:20:00+08:00",
            "source_snapshot_version": "published-v1",
            "verdict": "过期的半成品快照",
            "action": "等待",
            "primary_risk": "快照落后",
            "findings": [],
            "details": [],
            "missing_sections": [],
            "module_items": [],
            "module_sections": [
                {"key": "market-pulse", "items": []},
                {"key": "market-breadth", "items": []},
                {"key": "market-themes", "items": []},
                {"key": "market-movers", "items": []},
            ],
        },
    )

    class ExplodingService:
        def research(self, *_args, **_kwargs):
            raise AssertionError("opening fallback must not block on remote research")

    monkeypatch.setattr(web_module, "RESEARCH_WORKSPACE_SERVICE", ExplodingService())

    response = web_module._research_workspace_response(
        {"module": "market", "context": ResearchContext(), "refresh": False}
    )

    assert response["verdict"] != "过期的半成品快照"
    assert response["delivery"] == "local_fallback"
    assert response["stale"] is False


def test_workspace_open_uses_local_facts_without_waiting_for_remote(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("STOCK_TS_RESEARCH_SNAPSHOT_DIR", str(tmp_path / "research"))
    monkeypatch.setenv("IWENCAI_API_KEY", "configured-for-test")
    monkeypatch.setattr(web_module, "create_provider", lambda _name: SampleDataProvider())
    calls = 0

    class CountingService:
        def research(self, *_args, **_kwargs):
            nonlocal calls
            calls += 1
            raise AssertionError("page open must not wait for remote research")

    monkeypatch.setattr(web_module, "RESEARCH_WORKSPACE_SERVICE", CountingService())

    response = web_module._research_workspace_response(
        {"module": "market", "context": ResearchContext(), "refresh": False}
    )

    assert calls == 0
    assert response["delivery"] == "local_fallback"
    assert response["verdict"]


def _write_opportunity_snapshot(
    snapshot_dir,
    *,
    version: str | None,
    generated_at: str,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "ok": True,
        "status": "complete",
        "module": "opportunity",
        "generated_at": generated_at,
        "verdict": "旧机会快照判断",
        "action": "沿用旧候选动作",
        "primary_risk": "旧风险",
        "findings": [{"title": "旧候选600519"}],
        "module_items": [{"label": "旧候选600519", "summary": "旧动作"}],
        "module_sections": [
            {
                "key": "opportunity-candidates",
                "items": [
                    {
                        "label": "旧候选600519",
                        "summary": "旧动作",
                        "facts": [
                            {"label": label, "value": "旧值"}
                            for label in (
                                "阶段判断",
                                "持续性评分",
                                "5日表现",
                                "10日表现",
                                "20日表现",
                                "入选原因",
                                "确认条件",
                                "失效条件",
                            )
                        ],
                    }
                ],
            }
        ],
    }
    if version is not None:
        payload["research_contract_version"] = version
    path = snapshot_dir / "opportunity/latest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return payload


@pytest.mark.parametrize(
    ("version", "age_days"),
    [
        (None, 0),
        ("2026-07-16.legacy.v1", 0),
        (RESEARCH_CONTRACT_VERSION, 2),
    ],
)
def test_stock_local_fallback_rejects_incompatible_or_stale_opportunity_snapshot(
    monkeypatch,
    tmp_path,
    version: str | None,
    age_days: int,
) -> None:
    snapshot_dir = tmp_path / "research"
    generated_at = (
        datetime.now(timezone(timedelta(hours=8))) - timedelta(days=age_days)
    ).isoformat(timespec="seconds")
    _write_opportunity_snapshot(
        snapshot_dir,
        version=version,
        generated_at=generated_at,
    )
    monkeypatch.setenv("STOCK_TS_RESEARCH_SNAPSHOT_DIR", str(snapshot_dir))
    monkeypatch.delenv("IWENCAI_API_KEY", raising=False)
    monkeypatch.setattr(web_module, "create_provider", lambda _name: SampleDataProvider())
    original_build = web_module.build_local_research
    captured: list[dict[str, object] | None] = []

    def capturing_build(module, context, **kwargs):
        captured.append(kwargs.get("opportunity_snapshot"))
        return original_build(module, context, **kwargs)

    monkeypatch.setattr(web_module, "build_local_research", capturing_build)

    response = web_module._research_workspace_response(
        {
            "module": "stock",
            "context": ResearchContext(code="600519", name="贵州茅台"),
            "refresh": True,
        }
    )

    assert captured == [None]
    serialized = json.dumps(response, ensure_ascii=False)
    assert "旧机会快照判断" not in serialized
    assert "沿用旧候选动作" not in serialized
    assert "旧候选600519" not in serialized


def test_stock_local_fallback_accepts_only_fresh_compatible_opportunity_snapshot(
    monkeypatch,
    tmp_path,
) -> None:
    snapshot_dir = tmp_path / "research"
    expected = _write_opportunity_snapshot(
        snapshot_dir,
        version=RESEARCH_CONTRACT_VERSION,
        generated_at=datetime.now(timezone(timedelta(hours=8))).isoformat(
            timespec="seconds"
        ),
    )
    monkeypatch.setenv("STOCK_TS_RESEARCH_SNAPSHOT_DIR", str(snapshot_dir))
    monkeypatch.delenv("IWENCAI_API_KEY", raising=False)
    monkeypatch.setattr(web_module, "create_provider", lambda _name: SampleDataProvider())
    original_build = web_module.build_local_research
    captured: list[dict[str, object] | None] = []

    def capturing_build(module, context, **kwargs):
        captured.append(kwargs.get("opportunity_snapshot"))
        return original_build(module, context, **kwargs)

    monkeypatch.setattr(web_module, "build_local_research", capturing_build)

    web_module._research_workspace_response(
        {
            "module": "stock",
            "context": ResearchContext(code="600519", name="贵州茅台"),
            "refresh": True,
        }
    )

    assert captured == [expected]


def test_workspace_local_fallback_retries_when_snapshot_version_changes(
    monkeypatch,
    tmp_path,
) -> None:
    report_dir = tmp_path / "daily"
    report_dir.mkdir()
    status_path = report_dir / "pipeline.status"
    status_path.write_text("status=ok\nsnapshot_version=published-v1\n", encoding="utf-8")
    monkeypatch.setenv("STOCK_TS_DAILY_REPORT_DIR", str(report_dir))
    monkeypatch.setenv("STOCK_TS_RESEARCH_SNAPSHOT_DIR", str(tmp_path / "research"))
    monkeypatch.setenv("IWENCAI_API_KEY", "configured-for-test")

    class VersionedProvider(SampleDataProvider):
        def __init__(self, version: str) -> None:
            super().__init__()
            self.version = version

        def fetch_candidate_universe_metadata(self) -> dict[str, str]:
            return {"snapshot_version": self.version}

    versions = iter(["published-v1", "published-v2"])
    monkeypatch.setattr(
        web_module,
        "create_provider",
        lambda _name: VersionedProvider(next(versions)),
    )
    original_build = web_module.build_local_research
    builds: list[str] = []

    def switching_build(module, context, *, provider, **kwargs):
        builds.append(provider.version)
        result = original_build(module, context, provider=provider, **kwargs)
        if provider.version == "published-v1":
            status_path.write_text(
                "status=ok\nsnapshot_version=published-v2\n", encoding="utf-8"
            )
        return result

    monkeypatch.setattr(web_module, "build_local_research", switching_build)

    response = web_module._research_workspace_response(
        {"module": "market", "context": ResearchContext(), "refresh": False}
    )

    assert builds == ["published-v1", "published-v2"]
    assert response["source_snapshot_version"] == "published-v2"
    saved = ResearchSnapshotStore(tmp_path / "research").load(
        "market", allow_stale=True
    )
    assert saved is not None
    assert saved.payload["source_snapshot_version"] == "published-v2"


@pytest.mark.parametrize("module", ["market", "opportunity"])
def test_workspace_response_blocks_stale_snapshot_actions_and_candidates(
    monkeypatch,
    tmp_path,
    module: str,
) -> None:
    snapshot_dir = tmp_path / "research"
    monkeypatch.setenv("STOCK_TS_RESEARCH_SNAPSHOT_DIR", str(snapshot_dir))
    monkeypatch.delenv("IWENCAI_API_KEY", raising=False)
    generated_at = (
        datetime.now(timezone(timedelta(hours=8))) - timedelta(days=2)
    ).isoformat(timespec="seconds")
    ResearchSnapshotStore(snapshot_dir).save(
        module,
        {
            "research_contract_version": RESEARCH_CONTRACT_VERSION,
            "ok": True,
            "status": "partial",
            "module": module,
            "generated_at": generated_at,
            "verdict": "历史快照判断",
            "decision_label": "可以执行",
            "action": "沿用旧执行条件",
            "primary_risk": "成交缩量",
            "findings": [{"title": "旧候选"}],
            "details": [],
            "missing_sections": [],
            "module_items": [{"label": "观察分", "value": "88"}],
            "module_sections": (
                [
                    {"key": "market-pulse", "items": []},
                    {"key": "market-breadth", "items": []},
                    {"key": "market-themes", "items": []},
                    {"key": "market-movers", "items": []},
                ]
                if module == "market"
                else [{"key": "opportunity-candidates", "items": []}]
            ),
        },
    )

    response = web_module._research_workspace_response(
        {"module": module, "context": ResearchContext(), "refresh": True}
    )

    assert response["delivery"] == "stale_snapshot"
    assert response["stale"] is True
    assert response["data_label"] == "历史参考"
    assert response["decision_label"] == "历史参考"
    assert response["verdict"] == "历史记录：历史快照判断"
    assert response["action"] == "历史数据仅供复盘，不作为今天的操作依据。"
    assert "数据过期" in str(response["primary_risk"])
    assert response["findings"] == []
    assert response["module_items"] == []
    assert response["module_sections"] == []


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
            "research_contract_version": RESEARCH_CONTRACT_VERSION,
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
    assert {"market-pulse", "market-breadth", "market-themes", "market-movers"} <= keys
    assert "market-continuation" not in keys


def test_snapshot_workspace_gate_rejects_incompatible_contract_version() -> None:
    payload = {
        "research_contract_version": "2026-07-16.legacy.v1",
        "module_sections": [
            {"key": "market-pulse", "items": []},
            {"key": "market-breadth", "items": []},
            {"key": "market-themes", "items": []},
            {"key": "market-movers", "items": []},
        ],
    }

    assert web_module._snapshot_supports_workspace("market", payload) is False


def test_snapshot_gate_accepts_fact_only_market_movers_from_daily_job() -> None:
    payload = {
        "research_contract_version": RESEARCH_CONTRACT_VERSION,
        "module_sections": [
            {"key": "market-pulse", "items": []},
            {"key": "market-breadth", "items": []},
            {"key": "market-themes", "items": []},
            {
                "key": "market-movers",
                "items": [
                    {
                        "label": "机器人",
                        "facts": [
                            {"label": "涨跌幅", "value": "+4.2%"},
                            {"label": "异动原因", "value": "板块内多股同步走强"},
                            {"label": "风险", "value": "单日上涨不代表趋势形成"},
                        ],
                    }
                ],
            },
        ],
    }

    assert web_module._snapshot_supports_workspace("market", payload) is True


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


@pytest.mark.parametrize(
    ("error", "expected_http", "expected_status", "expected_message"),
    [
        (
            ValueError("opportunity snapshot missing stock 600519"),
            400,
            "stock_not_in_snapshot",
            "当前股票数据尚未进入研究快照，请先刷新数据或选择其他股票。",
        ),
        (
            ValueError("secret /Users/service/private/holdings.csv"),
            400,
            "invalid_request",
            "研究请求无效，请检查研究对象后重试。",
        ),
        (
            json.JSONDecodeError("gateway secret", "/srv/private/upstream.json", 0),
            502,
            "unavailable",
            "研究服务暂时不可用，请稍后重试。",
        ),
    ],
)
def test_workspace_endpoint_maps_internal_value_errors_to_product_language(
    monkeypatch,
    tmp_path,
    error: ValueError,
    expected_http: int,
    expected_status: str,
    expected_message: str,
) -> None:
    def failing_response(_payload):
        raise error

    monkeypatch.setattr(web_module, "_research_workspace_response", failing_response)
    server = _serve(monkeypatch, tmp_path)
    try:
        with pytest.raises(urllib.error.HTTPError) as caught:
            _request(
                server,
                json.dumps(
                    {
                        "module": "stock",
                        "context": {"code": "600519", "name": "贵州茅台"},
                    },
                    ensure_ascii=False,
                ).encode(),
            )

        body = _error_json(caught.value)
        assert caught.value.code == expected_http
        assert body["status"] == expected_status
        assert body["message"] == expected_message
        serialized = json.dumps(body, ensure_ascii=False)
        for forbidden in (
            "opportunity snapshot missing",
            "secret",
            "/Users/",
            "/srv/",
            "gateway",
            "upstream.json",
        ):
            assert forbidden.casefold() not in serialized.casefold()
    finally:
        server.shutdown()
        server.server_close()


def test_parse_stock_deep_research_payload_has_a_strict_public_contract() -> None:
    parsed = _parse_stock_deep_research_payload(
        json.dumps(
            {
                "code": "600519",
                "name": "贵州茅台",
                "focus": "finance",
                "question": "过去四个季度现金流如何",
                "refresh": True,
            },
            ensure_ascii=False,
        ).encode()
    )

    assert parsed == {
        "code": "600519",
        "name": "贵州茅台",
        "focus": "finance",
        "question": "过去四个季度现金流如何",
        "refresh": True,
    }

    for private_field in (
        "holdings",
        "cost",
        "weight",
        "account",
        "skill_id",
        "gateway",
        "cache_scope",
    ):
        with pytest.raises(ValueError, match="请求字段"):
            _parse_stock_deep_research_payload(
                json.dumps(
                    {"code": "600519", private_field: "browser-controlled"},
                    ensure_ascii=False,
                ).encode()
            )

    with pytest.raises(ValueError, match="研究范围"):
        _parse_stock_deep_research_payload(b'{"code":"600519","focus":"unknown"}')


def _capturing_deep_service():
    factory_calls: list[object] = []
    queries: list[str] = []

    class CapturingClient:
        def query(self, skill: object, query: str) -> dict[str, object]:
            queries.append(query)
            capability = next(key for key, value in SKILLS.items() if value == skill)
            rows = {
                "basicinfo": {"公司名称": "贵州茅台股份有限公司"},
                "business": {"主营产品": "白酒"},
                "management": {"股东户数": 120000},
                "finance": {"营业收入[2025]": 180_000_000_000},
                "industry": {"行业名称": "白酒"},
                "consensus": {"机构评级": "增持"},
                "report": {"title": "盈利质量稳定", "publish_date": "20260716"},
                "market": {"收盘价": 1480.0, "交易日期": "20260716"},
                "event": {"业绩预告类型": "预增"},
                "announcement": {"公告标题": "经营数据公告", "公告日期": "20260716"},
                "news": {"新闻标题": "渠道库存改善", "新闻日期": "20260716"},
            }
            return {"datas": [rows[capability]]}

    def factory() -> CapturingClient:
        client = CapturingClient()
        factory_calls.append(client)
        return client

    return StockDeepResearchService(client_factory=factory), factory_calls, queries


@pytest.mark.parametrize(
    "question",
    [
        "我1500元买了100股，现在怎么办",
        "帮我分析，我买了100手",
        "我的买价是1500",
        "本人120元购入2手",
        "我建仓100股",
        "我的成交价",
        "我的购入价",
        "1500元买了100股",
        "建仓100股",
        "我想问1500元买入了100股的止损条件",
        "请问1500元买入了100股的卖出条件",
        "1500元买入100股，后面怎么看",
        "bought 100 shares at $10, what now",
        "我想问我持有100股的买入条件",
        "我想问本人持有100股后的买入条件",
        "1500元100股怎么办",
        "1500元，100股，后面怎么处理",
        "成本1500，100股怎么办",
        "我在公司买入了100股",
        "公司买入了100万股，1500元100股怎么办",
        "机构买入100万股，1500元100股怎么办",
        "1500元100股",
        "成本1500，100股",
        "买价1500，100股",
        "机构买入100万股，我当前浮亏10%",
        "公司回购100万股，我持仓100股",
    ],
)
def test_stock_deep_api_rejects_personal_trade_ownership_before_client_factory(
    monkeypatch,
    tmp_path,
    question: str,
) -> None:
    service, factory_calls, queries = _capturing_deep_service()
    monkeypatch.setattr(web_module, "STOCK_DEEP_RESEARCH_SERVICE", service)
    server = _serve(monkeypatch, tmp_path, auth_enabled=True)
    try:
        with pytest.raises(urllib.error.HTTPError) as caught:
            _deep_request(
                server,
                json.dumps(
                    {
                        "code": "600519",
                        "name": "贵州茅台",
                        "focus": "all",
                        "question": question,
                        "refresh": False,
                    },
                    ensure_ascii=False,
                ).encode(),
                cookie=_authenticated_cookie(tmp_path),
            )

        assert caught.value.code == 400
        assert factory_calls == []
        assert queries == []
    finally:
        server.shutdown()
        server.server_close()


@pytest.mark.parametrize(
    "question",
    [
        "机构买入100万股",
        "公司回购100万股",
        "我想问买入条件",
        "买入条件是什么",
        "我想问100元买入条件",
        "我想研究买入100元以下的公司",
        "公司买入了100万股",
        "请问公司买入了100万股意味着什么",
        "该公司买入了100万股意味着什么",
        "机构持仓100万股",
    ],
)
def test_stock_deep_api_allows_public_trade_research(
    monkeypatch,
    tmp_path,
    question: str,
) -> None:
    service, factory_calls, queries = _capturing_deep_service()
    monkeypatch.setattr(web_module, "STOCK_DEEP_RESEARCH_SERVICE", service)
    server = _serve(monkeypatch, tmp_path, auth_enabled=True)
    try:
        with _deep_request(
            server,
            json.dumps(
                {
                    "code": "600519",
                    "name": "贵州茅台",
                    "focus": "all",
                    "question": question,
                    "refresh": False,
                },
                ensure_ascii=False,
            ).encode(),
            cookie=_authenticated_cookie(tmp_path),
        ) as response:
            body = json.loads(response.read().decode())

        assert response.status == 200
        assert body["ok"] is True
        assert len(factory_calls) == 1
        assert len(queries) == 1
    finally:
        server.shutdown()
        server.server_close()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("code", "我1500元买了100股"),
        ("name", "我1500元买了100股"),
        ("name", "1500元买了100股"),
    ],
)
def test_stock_deep_api_rejects_private_identity_before_client_factory(
    monkeypatch,
    tmp_path,
    field: str,
    value: str,
) -> None:
    service, factory_calls, queries = _capturing_deep_service()
    monkeypatch.setattr(web_module, "STOCK_DEEP_RESEARCH_SERVICE", service)
    payload = {
        "code": "600519",
        "name": "贵州茅台",
        "focus": "finance",
        "question": "",
        "refresh": False,
    }
    payload[field] = value
    server = _serve(monkeypatch, tmp_path, auth_enabled=True)
    try:
        with pytest.raises(urllib.error.HTTPError) as caught:
            _deep_request(
                server,
                json.dumps(payload, ensure_ascii=False).encode(),
                cookie=_authenticated_cookie(tmp_path),
            )

        assert caught.value.code == 400
        assert factory_calls == []
        assert queries == []
    finally:
        server.shutdown()
        server.server_close()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("code", "ABC"),
        ("code", "600519.X"),
        ("name", "请帮我分析这只股票"),
        ("name", "贵州 茅台"),
    ],
)
def test_stock_deep_api_rejects_invalid_stock_identity_before_client_factory(
    monkeypatch,
    tmp_path,
    field: str,
    value: str,
) -> None:
    service, factory_calls, queries = _capturing_deep_service()
    monkeypatch.setattr(web_module, "STOCK_DEEP_RESEARCH_SERVICE", service)
    payload = {
        "code": "600519",
        "name": "贵州茅台",
        "focus": "finance",
        "question": "",
        "refresh": False,
    }
    payload[field] = value
    server = _serve(monkeypatch, tmp_path, auth_enabled=True)
    try:
        with pytest.raises(urllib.error.HTTPError) as caught:
            _deep_request(
                server,
                json.dumps(payload, ensure_ascii=False).encode(),
                cookie=_authenticated_cookie(tmp_path),
            )

        assert caught.value.code == 400
        assert factory_calls == []
        assert queries == []
    finally:
        server.shutdown()
        server.server_close()


@pytest.mark.parametrize(
    ("code", "name"),
    [
        ("600519", "贵州茅台"),
        ("600519.SH", "贵州茅台"),
        ("000001.SZ", "平安银行"),
        ("430047.BJ", "诺思兰德"),
        ("600519", "*ST示例"),
    ],
)
def test_stock_deep_api_allows_valid_stock_identity(
    monkeypatch,
    tmp_path,
    code: str,
    name: str,
) -> None:
    service, factory_calls, queries = _capturing_deep_service()
    monkeypatch.setattr(web_module, "STOCK_DEEP_RESEARCH_SERVICE", service)
    server = _serve(monkeypatch, tmp_path, auth_enabled=True)
    try:
        with _deep_request(
            server,
            json.dumps(
                {
                    "code": code,
                    "name": name,
                    "focus": "finance",
                    "question": "",
                    "refresh": False,
                },
                ensure_ascii=False,
            ).encode(),
            cookie=_authenticated_cookie(tmp_path),
        ) as response:
            body = json.loads(response.read().decode())

        assert response.status == 200
        assert body["code"] == code
        assert body["name"] == name
        assert len(factory_calls) == 1
        assert queries
    finally:
        server.shutdown()
        server.server_close()


def test_stock_deep_api_treats_duplicated_chinese_name_as_name_only_query(
    monkeypatch,
    tmp_path,
) -> None:
    service, factory_calls, queries = _capturing_deep_service()
    monkeypatch.setattr(web_module, "STOCK_DEEP_RESEARCH_SERVICE", service)
    server = _serve(monkeypatch, tmp_path, auth_enabled=True)
    try:
        with _deep_request(
            server,
            json.dumps(
                {
                    "code": "招商银行",
                    "name": "招商银行",
                    "focus": "finance",
                    "question": "",
                    "refresh": False,
                },
                ensure_ascii=False,
            ).encode(),
            cookie=_authenticated_cookie(tmp_path),
        ) as response:
            body = json.loads(response.read().decode())

        assert response.status == 200
        assert body["code"] == ""
        assert body["name"] == "招商银行"
        assert len(factory_calls) == 1
        assert len(queries) == 1
        assert queries[0].count("招商银行") == 1
    finally:
        server.shutdown()
        server.server_close()


def test_stock_deep_api_cache_is_isolated_by_authenticated_user(
    monkeypatch,
    tmp_path,
) -> None:
    service, factory_calls, queries = _capturing_deep_service()
    monkeypatch.setattr(web_module, "STOCK_DEEP_RESEARCH_SERVICE", service)
    users = UserStore(tmp_path / "users.sqlite3")
    owner = users.bootstrap_admin("owner@example.com", "secret-password")
    member = users.register_user("member@example.com", "member-password")
    payload = json.dumps(
        {
            "code": "600519",
            "name": "贵州茅台",
            "focus": "finance",
            "question": "",
            "refresh": False,
        },
        ensure_ascii=False,
    ).encode()
    server = _serve(monkeypatch, tmp_path, auth_enabled=True)
    bodies = []
    try:
        for user in (owner, member, owner):
            with _deep_request(
                server,
                payload,
                cookie=_cookie_for_user(user),
            ) as response:
                bodies.append(json.loads(response.read().decode()))

        assert len(factory_calls) == 2
        assert len(queries) == 2
        assert bodies[0]["cached"] is False
        assert bodies[1]["cached"] is False
        assert bodies[2]["cached"] is True
        serialized = json.dumps(bodies, ensure_ascii=False)
        assert "cache_scope" not in serialized
        assert "user:" not in serialized
        assert "account" not in serialized.casefold()
        assert all("user:" not in query for query in queries)
        assert all("example.com" not in query for query in queries)
    finally:
        server.shutdown()
        server.server_close()


def test_stock_deep_endpoint_returns_neutral_partial_result_without_private_context(
    monkeypatch,
    tmp_path,
) -> None:
    captured: dict[str, object] = {}

    class PartialResult:
        def to_public_dict(self) -> dict[str, object]:
            return {
                "ok": True,
                "status": "partial",
                "code": "600519",
                "name": "贵州茅台",
                "focus": "all",
                "groups": [
                    {
                        "key": "finance",
                        "title": "财务与估值",
                        "status": "partial",
                        "facts": [],
                        "recovery": "部分事实待补，请稍后重试。",
                    }
                ],
                "coverage": {"ready": 9, "total": 11},
                "cached": False,
                "as_of": "2026-07-17T10:00:00+08:00",
                "recovery": "",
            }

    class FakeService:
        def research(self, **kwargs):
            captured.update(kwargs)
            return PartialResult()

    monkeypatch.setattr(web_module, "STOCK_DEEP_RESEARCH_SERVICE", FakeService())
    server = _serve(monkeypatch, tmp_path, auth_enabled=True)
    try:
        with _deep_request(
            server,
            json.dumps(
                {
                    "code": "600519",
                    "name": "贵州茅台",
                    "focus": "all",
                    "question": "",
                    "refresh": False,
                },
                ensure_ascii=False,
            ).encode(),
            cookie=_authenticated_cookie(tmp_path),
        ) as response:
            body = json.loads(response.read().decode())

        assert response.status == 200
        assert response.headers["Cache-Control"] == "no-store"
        assert captured == {
            "code": "600519",
            "name": "贵州茅台",
            "focus": "all",
            "question": "",
            "refresh": False,
            "cache_scope": "user:1",
        }
        serialized = json.dumps(body, ensure_ascii=False)
        for forbidden in (
            "问财",
            "同花顺",
            "skill_id",
            "trace",
            "gateway",
            "api_key",
            "持仓",
            "成本",
            "权重",
            "账号",
            "Cookie",
        ):
            assert forbidden.casefold() not in serialized.casefold()
    finally:
        server.shutdown()
        server.server_close()


def test_stock_deep_endpoint_enforces_media_size_and_rate_limits(
    monkeypatch,
    tmp_path,
) -> None:
    server = _serve(monkeypatch, tmp_path, auth_enabled=True)
    cookie = _authenticated_cookie(tmp_path)
    try:
        with pytest.raises(urllib.error.HTTPError) as wrong_type:
            _deep_request(
                server,
                b"code=600519",
                content_type="application/x-www-form-urlencoded",
                cookie=cookie,
            )
        assert wrong_type.value.code == 415

        with pytest.raises(urllib.error.HTTPError) as too_large:
            _deep_request(server, b"{" + b"x" * (16 * 1024) + b"}", cookie=cookie)
        assert too_large.value.code == 413

        monkeypatch.setattr(
            web_module,
            "IWENCAI_RESEARCH_RATE_LIMITER",
            ResearchRateLimiter(limit=0, window_seconds=60),
        )
        with pytest.raises(urllib.error.HTTPError) as limited:
            _deep_request(server, b'{"code":"600519"}', cookie=cookie)
        assert limited.value.code == 429
        assert _error_json(limited.value)["status"] == "rate_limited"
    finally:
        server.shutdown()
        server.server_close()


@pytest.mark.parametrize(
    ("error_type", "expected_status"),
    [
        (IwencaiConfigurationError, 503),
        (IwencaiGatewayError, 502),
    ],
)
def test_stock_deep_endpoint_maps_real_service_zero_success_errors(
    monkeypatch,
    tmp_path,
    error_type: type[IwencaiError],
    expected_status: int,
) -> None:
    class FailingClient:
        def query(self, _skill: object, _query: str) -> dict[str, object]:
            raise error_type("gateway trace secret /private/path")

    monkeypatch.setattr(
        web_module,
        "STOCK_DEEP_RESEARCH_SERVICE",
        StockDeepResearchService(client_factory=FailingClient),
    )
    server = _serve(monkeypatch, tmp_path, auth_enabled=True)
    try:
        with pytest.raises(urllib.error.HTTPError) as caught:
            _deep_request(
                server,
                json.dumps(
                    {"code": "600519", "name": "贵州茅台", "focus": "all"},
                    ensure_ascii=False,
                ).encode(),
                cookie=_authenticated_cookie(tmp_path),
            )

        assert caught.value.code == expected_status
        serialized = json.dumps(_error_json(caught.value), ensure_ascii=False)
        for forbidden in ("gateway", "trace", "secret", "/private/path", "问财", "同花顺"):
            assert forbidden.casefold() not in serialized.casefold()
    finally:
        server.shutdown()
        server.server_close()


def test_stock_deep_endpoint_keeps_real_service_partial_success_neutral(
    monkeypatch,
    tmp_path,
) -> None:
    rows = {
        "basicinfo": {"公司名称": "贵州茅台股份有限公司"},
        "business": {"主营产品": "白酒"},
    }

    class PartialClient:
        def query(self, skill: object, _query: str) -> dict[str, object]:
            capability = next(key for key, value in SKILLS.items() if value == skill)
            if capability == "management":
                raise IwencaiGatewayError("gateway trace secret /private/path")
            return {"datas": [rows[capability]]}

    monkeypatch.setattr(
        web_module,
        "STOCK_DEEP_RESEARCH_SERVICE",
        StockDeepResearchService(client_factory=PartialClient),
    )
    server = _serve(monkeypatch, tmp_path, auth_enabled=True)
    try:
        with _deep_request(
            server,
            json.dumps(
                {"code": "600519", "name": "贵州茅台", "focus": "company"},
                ensure_ascii=False,
            ).encode(),
            cookie=_authenticated_cookie(tmp_path),
        ) as response:
            body = json.loads(response.read().decode())

        assert response.status == 200
        assert body["status"] == "partial"
        assert body["coverage"] == {"ready": 1, "total": 3}
        serialized = json.dumps(body, ensure_ascii=False)
        for forbidden in ("gateway", "trace", "secret", "/private/path", "问财", "同花顺"):
            assert forbidden.casefold() not in serialized.casefold()
    finally:
        server.shutdown()
        server.server_close()


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        (ValueError("secret/path/to/private"), 400),
        (RuntimeError("gateway trace secret"), 502),
    ],
)
def test_stock_deep_endpoint_sanitizes_service_errors(
    monkeypatch,
    tmp_path,
    error: Exception,
    expected_status: int,
) -> None:
    class FailingService:
        def research(self, **_kwargs):
            raise error

    monkeypatch.setattr(web_module, "STOCK_DEEP_RESEARCH_SERVICE", FailingService())
    server = _serve(monkeypatch, tmp_path, auth_enabled=True)
    try:
        with pytest.raises(urllib.error.HTTPError) as caught:
            _deep_request(
                server,
                b'{"code":"600519","focus":"all"}',
                cookie=_authenticated_cookie(tmp_path),
            )

        assert caught.value.code == expected_status
        serialized = json.dumps(_error_json(caught.value), ensure_ascii=False)
        for forbidden in ("secret", "path", "gateway", "trace", "RuntimeError"):
            assert forbidden.casefold() not in serialized.casefold()
    finally:
        server.shutdown()
        server.server_close()
