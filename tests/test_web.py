from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

from aster_market.web import create_server

FIXTURE = Path(__file__).parent / "fixtures" / "market_snapshot.json"


@contextmanager
def running_server() -> Iterator[str]:
    server = create_server("127.0.0.1", 0, snapshot_path=FIXTURE)
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
