from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

from .analysis import (
    analyze_stock,
    build_market_analysis,
    build_opportunities,
    find_stock,
    search_stocks,
)
from .snapshot_cache import SnapshotCache
from .ui import asset_text, render_app

DEFAULT_SNAPSHOT_PATH = Path("data/market_snapshot.json")

def create_handler(
    snapshot_path: Path | None = None,
    snapshot_cache: SnapshotCache | None = None,
) -> type[BaseHTTPRequestHandler]:
    cache = snapshot_cache or SnapshotCache()

    class AsterRequestHandler(BaseHTTPRequestHandler):
        server_version = "AsterMarket/0.1"
        sys_version = ""

        def _snapshot_path(self) -> Path:
            if snapshot_path is not None:
                return snapshot_path
            return Path(os.getenv("ASTER_SNAPSHOT_PATH", str(DEFAULT_SNAPSHOT_PATH)))

        def _snapshot_state(self):
            return cache.get(self._snapshot_path())

        def _send(
            self,
            status: HTTPStatus,
            body: bytes,
            content_type: str,
            cache_control: str = "no-store",
        ) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", cache_control)
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; style-src 'self' 'unsafe-inline'; "
                "script-src 'self'; img-src 'self' data:; frame-ancestors 'none'",
            )
            self.end_headers()
            self.wfile.write(body)

        def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
            self._send(status, body, "application/json; charset=utf-8")

        def _load_analysis_snapshot(self):
            result = self._snapshot_state().result
            if result.snapshot is None:
                self._send_json(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    {"status": result.status, "message": result.message},
                )
                return None
            return result.snapshot

        def do_GET(self) -> None:  # noqa: N802
            request = urlsplit(self.path)
            path = request.path
            if path == "/healthz":
                self._send(HTTPStatus.OK, b"ok", "text/plain; charset=utf-8")
                return

            if path == "/api/snapshot":
                view = self._snapshot_state().view
                status = (
                    HTTPStatus.OK
                    if view["status"] == "ready"
                    else HTTPStatus.SERVICE_UNAVAILABLE
                )
                self._send_json(status, view)
                return

            if path == "/api/analysis/market":
                snapshot = self._load_analysis_snapshot()
                if snapshot is not None:
                    self._send_json(HTTPStatus.OK, build_market_analysis(snapshot))
                return

            if path == "/api/opportunities":
                snapshot = self._load_analysis_snapshot()
                if snapshot is not None:
                    self._send_json(
                        HTTPStatus.OK,
                        {
                            "status": "ready",
                            "trade_date": snapshot.trade_date,
                            "items": build_opportunities(snapshot),
                        },
                    )
                return

            if path == "/api/stocks":
                query = parse_qs(request.query, keep_blank_values=True).get("query", [""])[0]
                if len(query) > 40:
                    self._send_json(
                        HTTPStatus.BAD_REQUEST,
                        {"status": "invalid_query", "message": "搜索内容不能超过 40 个字符"},
                    )
                    return
                snapshot = self._load_analysis_snapshot()
                if snapshot is not None:
                    self._send_json(
                        HTTPStatus.OK,
                        {
                            "status": "ready",
                            "query": query,
                            "items": search_stocks(snapshot, query),
                        },
                    )
                return

            if path.startswith("/api/stocks/"):
                code = path.removeprefix("/api/stocks/").strip()
                snapshot = self._load_analysis_snapshot()
                if snapshot is None:
                    return
                stock = find_stock(snapshot, code)
                if stock is None:
                    self._send_json(
                        HTTPStatus.NOT_FOUND,
                        {"status": "not_found", "message": "没有找到这只股票"},
                    )
                else:
                    self._send_json(HTTPStatus.OK, analyze_stock(stock))
                return

            if path == "/":
                view = self._snapshot_state().view
                body = render_app(view).encode("utf-8")
                self._send(HTTPStatus.OK, body, "text/html; charset=utf-8")
                return

            assets = {
                "/assets/app.css": ("app.css", "text/css; charset=utf-8"),
                "/assets/modules.css": ("modules.css", "text/css; charset=utf-8"),
                "/assets/app.js": ("app.js", "text/javascript; charset=utf-8"),
                "/assets/portfolio.js": ("portfolio.js", "text/javascript; charset=utf-8"),
            }
            if path in assets:
                name, content_type = assets[path]
                self._send(
                    HTTPStatus.OK,
                    asset_text(name).encode("utf-8"),
                    content_type,
                    cache_control="public, max-age=300",
                )
                return

            self._send_json(HTTPStatus.NOT_FOUND, {"status": "not_found", "path": path})

        def log_message(self, format_string: str, *args: object) -> None:
            print(f"{self.address_string()} - {format_string % args}")

    return AsterRequestHandler


def create_server(
    host: str,
    port: int,
    snapshot_path: Path | None = None,
    snapshot_cache: SnapshotCache | None = None,
) -> ThreadingHTTPServer:
    return ThreadingHTTPServer(
        (host, port),
        create_handler(snapshot_path, snapshot_cache=snapshot_cache),
    )


def main() -> None:
    host = os.getenv("HOST", "127.0.0.1")
    try:
        port = int(os.getenv("PORT", "8501"))
    except ValueError:
        port = 8501
    server = create_server(host, port)
    print(f"Aster Market listening on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
