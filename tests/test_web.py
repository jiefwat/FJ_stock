from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import urlopen

from aster_market.snapshot_cache import SnapshotCache
from aster_market.web import create_server

FIXTURE = Path(__file__).parent / "fixtures" / "market_snapshot.json"


@contextmanager
def running_server(
    snapshot_path: Path = FIXTURE,
    snapshot_cache: SnapshotCache | None = None,
) -> Iterator[str]:
    server = create_server(
        "127.0.0.1",
        0,
        snapshot_path=snapshot_path,
        snapshot_cache=snapshot_cache,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _get(url: str) -> tuple[int, dict[str, str], bytes]:
    with urlopen(url, timeout=2) as response:
        return response.status, dict(response.headers.items()), response.read()


def test_health_and_snapshot_are_public_no_store_endpoints() -> None:
    with running_server() as base_url:
        health_status, health_headers, health_body = _get(f"{base_url}/healthz")
        api_status, api_headers, api_body = _get(f"{base_url}/api/snapshot")

    payload = json.loads(api_body)
    assert health_status == 200
    assert health_body == b"ok"
    assert health_headers["Cache-Control"] == "no-store"
    assert health_headers["X-Content-Type-Options"] == "nosniff"
    assert api_status == 200
    assert api_headers["Cache-Control"] == "no-store"
    assert payload["status"] == "ready"
    assert payload["regime"] == "轮动"
    assert payload["decision_brief"]["mainline"]["theme"] == "机器人"
    assert "candidate_universe" not in payload


def test_home_and_assets_are_served_without_login() -> None:
    with running_server() as base_url:
        status, headers, body = _get(f"{base_url}/")
        css_status, css_headers, css_body = _get(f"{base_url}/assets/app.css")

    html = body.decode("utf-8")
    assert status == 200
    assert headers["Cache-Control"] == "no-store"
    assert 'data-aster-app="market-horizon"' in html
    assert "login" not in html.lower()
    assert css_status == 200
    assert css_headers["Cache-Control"] == "public, max-age=300"
    assert b"--cobalt" in css_body


def test_unknown_route_returns_404() -> None:
    with running_server() as base_url:
        try:
            _get(f"{base_url}/not-a-route")
        except HTTPError as error:
            assert error.code == 404
            assert error.headers["X-Content-Type-Options"] == "nosniff"
        else:
            raise AssertionError("unknown route should return 404")


def test_analysis_routes_return_supplier_neutral_json() -> None:
    with running_server() as base_url:
        market_status, market_headers, market_body = _get(
            f"{base_url}/api/analysis/market"
        )
        _, _, opportunities_body = _get(f"{base_url}/api/opportunities")
        _, _, stocks_body = _get(f"{base_url}/api/stocks?query={quote('机器人')}")
        _, _, detail_body = _get(f"{base_url}/api/stocks/300100")

    market = json.loads(market_body)
    opportunities = json.loads(opportunities_body)
    stocks = json.loads(stocks_body)
    detail = json.loads(detail_body)
    assert market_status == 200
    assert market_headers["Cache-Control"] == "no-store"
    assert market["regime"] == "轮动"
    assert opportunities["items"][0]["theme"] == "机器人"
    assert stocks["items"][0]["code"] == "300100"
    assert detail["code"] == "300100"
    assert "fund_flow_detail" not in detail


def test_analysis_routes_enforce_query_and_not_found_contracts() -> None:
    with running_server() as base_url:
        try:
            _get(f"{base_url}/api/stocks/000000")
        except HTTPError as error:
            assert error.code == 404
            assert json.loads(error.read())["status"] == "not_found"
        else:
            raise AssertionError("unknown stock should return 404")

        try:
            _get(f"{base_url}/api/stocks?query={'x' * 41}")
        except HTTPError as error:
            assert error.code == 400
            assert json.loads(error.read())["status"] == "invalid_query"
        else:
            raise AssertionError("long query should return 400")


def test_analysis_routes_return_503_when_snapshot_is_missing(tmp_path: Path) -> None:
    with running_server(tmp_path / "missing.json") as base_url:
        try:
            _get(f"{base_url}/api/analysis/market")
        except HTTPError as error:
            assert error.code == 503
            assert error.headers["Cache-Control"] == "no-store"
            assert json.loads(error.read())["status"] == "unavailable"
        else:
            raise AssertionError("missing snapshot should return 503")


def test_routes_share_one_snapshot_cache(tmp_path: Path, monkeypatch) -> None:
    from aster_market import snapshot_cache as cache_module

    path = tmp_path / "snapshot.json"
    path.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    calls = 0
    real_loader = cache_module.load_snapshot

    def counting_loader(candidate: Path):
        nonlocal calls
        calls += 1
        return real_loader(candidate)

    monkeypatch.setattr(cache_module, "load_snapshot", counting_loader)
    cache = SnapshotCache()

    with running_server(path, snapshot_cache=cache) as base_url:
        _get(f"{base_url}/")
        _get(f"{base_url}/api/analysis/market")
        _get(f"{base_url}/api/stocks/300100")

    assert calls == 1


def test_server_reloads_snapshot_after_atomic_replacement(tmp_path: Path) -> None:
    path = tmp_path / "snapshot.json"
    path.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")

    with running_server(path) as base_url:
        first = json.loads(_get(f"{base_url}/api/snapshot")[2])
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["market"]["trade_date"] = "2026-07-19"
        replacement = path.with_suffix(".staging")
        replacement.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        replacement.replace(path)
        second = json.loads(_get(f"{base_url}/api/snapshot")[2])

    assert first["trade_date"] == "2026-07-18"
    assert second["trade_date"] == "2026-07-19"
