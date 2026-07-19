from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from marketdesk.models import EquityQuote, OpportunityResult, StockDossier, WatchlistItem
from marketdesk.services import MarketService


class WatchlistCreate(BaseModel):
    symbol: str
    name: str
    thesis: str = Field(min_length=1)
    invalidation: str = Field(min_length=1)


class WatchlistUpdate(BaseModel):
    status: Literal["new", "researching", "waiting", "invalidated", "archived"] | None = None
    thesis: str | None = Field(default=None, min_length=1)
    invalidation: str | None = Field(default=None, min_length=1)


def create_app(service: MarketService | None = None) -> FastAPI:
    app = FastAPI(title="Market Desk", version="0.1.0")
    market_service = service or MarketService()
    app.state.service = market_service
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/healthz")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/v1/market")
    async def market() -> dict[str, Any]:
        return await market_service.market_payload()

    @app.get("/api/v1/today")
    async def today() -> dict[str, Any]:
        return await market_service.today()

    @app.post("/api/v1/refresh")
    async def refresh() -> dict[str, object]:
        snapshot = await market_service.market(force=True)
        return {"status": "ok", "meta": snapshot.meta}

    @app.get("/api/v1/opportunities")
    async def opportunities(
        preset: str = "trend", limit: int = Query(default=50, ge=1, le=200)
    ) -> OpportunityResult:
        try:
            return await market_service.opportunities(preset, limit)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.get("/api/v1/opportunities/export.csv")
    async def opportunities_csv(preset: str = "trend") -> StreamingResponse:
        result = await market_service.opportunities(preset, 200)
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["symbol", "name", "score", "change_pct", "amount", "risk_flags"])
        for item in result.candidates:
            writer.writerow(
                [
                    item.quote.symbol,
                    item.quote.name,
                    item.score,
                    item.quote.change_pct,
                    item.quote.amount,
                    "|".join(item.risk_flags),
                ]
            )
        return StreamingResponse(
            iter([buffer.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=opportunities.csv"},
        )

    @app.get("/api/v1/search")
    async def search(q: str = Query(min_length=1)) -> list[EquityQuote]:
        return await market_service.search(q)

    @app.get("/api/v1/stocks/{symbol}")
    async def stock(symbol: str) -> StockDossier:
        try:
            return await market_service.stock(symbol.upper())
        except KeyError as error:
            raise HTTPException(status_code=404, detail="stock not found") from error

    @app.get("/api/v1/data-status")
    async def data_status() -> dict[str, Any]:
        return market_service.data_status()

    @app.get("/api/v1/watchlist")
    async def watchlist() -> list[WatchlistItem]:
        return market_service.store.list_watchlist()

    @app.post("/api/v1/watchlist", status_code=201)
    async def create_watchlist(payload: WatchlistCreate) -> WatchlistItem:
        try:
            return market_service.store.create_watchlist(**payload.model_dump())
        except Exception as error:
            raise HTTPException(status_code=409, detail="symbol already exists") from error

    @app.patch("/api/v1/watchlist/{item_id}")
    async def update_watchlist(item_id: int, payload: WatchlistUpdate) -> WatchlistItem:
        try:
            return market_service.store.update_watchlist(
                item_id, **payload.model_dump(exclude_none=True)
            )
        except KeyError as error:
            raise HTTPException(status_code=404, detail="watchlist item not found") from error

    @app.delete("/api/v1/watchlist/{item_id}", status_code=204)
    async def delete_watchlist(item_id: int) -> Response:
        market_service.store.delete_watchlist(item_id)
        return Response(status_code=204)

    frontend = Path(__file__).resolve().parents[3] / "frontend" / "dist"
    if frontend.exists():
        assets = frontend / "assets"
        if assets.exists():
            app.mount("/assets", StaticFiles(directory=assets), name="assets")

        @app.get("/{path:path}")
        async def spa(path: str) -> FileResponse:
            return FileResponse(frontend / "index.html")

    return app


app = create_app()
