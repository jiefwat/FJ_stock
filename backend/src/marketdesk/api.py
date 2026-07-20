from __future__ import annotations

import asyncio
import contextlib
import csv
import io
import logging
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from marketdesk.config import Settings
from marketdesk.models import (
    EquityQuote,
    HoldingDossier,
    MarketEventResult,
    OpportunityResult,
    SectorDossier,
    StockDossier,
    WatchlistItem,
)
from marketdesk.services import MarketService

logger = logging.getLogger(__name__)


class WatchlistCreate(BaseModel):
    symbol: str
    name: str
    thesis: str = Field(min_length=1)
    invalidation: str = Field(min_length=1)


class WatchlistUpdate(BaseModel):
    status: Literal["new", "researching", "waiting", "invalidated", "archived"] | None = None
    thesis: str | None = Field(default=None, min_length=1)
    invalidation: str | None = Field(default=None, min_length=1)


class HoldingCreate(BaseModel):
    symbol: str
    name: str
    quantity: float = Field(gt=0)
    cost_price: float = Field(gt=0)
    target_weight: float = Field(ge=0, le=1)
    thesis: str = Field(min_length=1)
    invalidation: str = Field(min_length=1)


class HoldingUpdate(BaseModel):
    quantity: float | None = Field(default=None, gt=0)
    cost_price: float | None = Field(default=None, gt=0)
    target_weight: float | None = Field(default=None, ge=0, le=1)
    thesis: str | None = Field(default=None, min_length=1)
    invalidation: str | None = Field(default=None, min_length=1)
    status: Literal["holding", "trimming", "watching_exit", "closed"] | None = None


async def _safe_auto_refresh(service: MarketService) -> None:
    try:
        await service.market(force=True)
    except Exception:
        logger.exception("scheduled market data refresh failed")


async def _auto_refresh_loop(
    service: MarketService,
    interval_seconds: float,
    run_immediately: bool,
) -> None:
    if run_immediately:
        await _safe_auto_refresh(service)
    while True:
        await asyncio.sleep(interval_seconds)
        await _safe_auto_refresh(service)


def create_app(
    service: MarketService | None = None,
    *,
    auto_refresh_interval_seconds: float | None = None,
    auto_refresh_run_immediately: bool | None = None,
) -> FastAPI:
    settings = Settings()
    market_service = service or MarketService()
    configured_interval = (
        auto_refresh_interval_seconds
        if auto_refresh_interval_seconds is not None
        else settings.auto_refresh_interval_seconds
        if service is None and settings.auto_refresh_enabled
        else None
    )
    configured_run_immediately = (
        auto_refresh_run_immediately
        if auto_refresh_run_immediately is not None
        else settings.auto_refresh_run_immediately
    )

    @contextlib.asynccontextmanager
    async def lifespan(app_: FastAPI) -> AsyncIterator[None]:
        if configured_interval is not None and configured_interval > 0:
            app_.state.auto_refresh_task = asyncio.create_task(
                _auto_refresh_loop(market_service, configured_interval, configured_run_immediately)
            )
        try:
            yield
        finally:
            task = app_.state.auto_refresh_task
            if task is not None:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task

    app = FastAPI(title="Market Desk", version="0.1.0", lifespan=lifespan)
    app.state.service = market_service
    app.state.auto_refresh_interval_seconds = configured_interval
    app.state.auto_refresh_run_immediately = configured_run_immediately
    app.state.auto_refresh_task = None
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

    @app.get("/api/v1/market-events")
    async def market_events(limit: int = Query(default=30, ge=1, le=100)) -> MarketEventResult:
        return await market_service.market_events(limit)

    @app.get("/api/v1/sectors/{code}")
    async def sector(code: str) -> SectorDossier:
        try:
            return await market_service.sector(code)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="sector not found") from error

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
        status = market_service.data_status()
        status["auto_refresh"] = {
            "enabled": configured_interval is not None and configured_interval > 0,
            "interval_seconds": configured_interval,
            "run_immediately": configured_run_immediately,
        }
        return status

    @app.get("/api/v1/watchlist")
    async def watchlist() -> list[WatchlistItem]:
        return market_service.store.list_watchlist()

    @app.get("/api/v1/holdings")
    async def holdings() -> list[HoldingDossier]:
        return await market_service.holdings()

    @app.post("/api/v1/holdings", status_code=201)
    async def create_holding(payload: HoldingCreate) -> HoldingDossier:
        try:
            return await market_service.create_holding(payload.model_dump())
        except Exception as error:
            raise HTTPException(status_code=409, detail="holding already exists") from error

    @app.patch("/api/v1/holdings/{item_id}")
    async def update_holding(item_id: int, payload: HoldingUpdate) -> HoldingDossier:
        try:
            return await market_service.update_holding(item_id, payload.model_dump(exclude_none=True))
        except KeyError as error:
            raise HTTPException(status_code=404, detail="holding not found") from error

    @app.delete("/api/v1/holdings/{item_id}", status_code=204)
    async def delete_holding(item_id: int) -> Response:
        market_service.delete_holding(item_id)
        return Response(status_code=204)

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
