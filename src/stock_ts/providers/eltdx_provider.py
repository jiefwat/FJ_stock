from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import warnings
from functools import lru_cache
from pathlib import Path
from threading import RLock
from typing import Any, Callable

from stock_ts.models import (
    CandidateStockRawData,
    DailyBar,
    IndexQuote,
    MarketRawData,
    SectorRawData,
    StockRawData,
)
from stock_ts.providers.base import DataProviderError, StockDataProvider
from stock_ts.providers.sample import SampleDataProvider
from stock_ts.providers.tencent_provider import TencentProvider
from stock_ts.sector_labels import localize_sector_name

_CACHE_TTL_SECONDS = 90.0
_CACHE_LOCK = RLock()
_MARKET_CACHE: dict[tuple[str, float], tuple[float, MarketRawData]] = {}
_STOCK_CACHE: dict[tuple[str, float], tuple[float, StockRawData]] = {}
_SECTOR_CACHE: dict[tuple[str, float], tuple[float, list[SectorRawData]]] = {}
_CANDIDATE_CACHE: dict[tuple[str, float], tuple[float, list[CandidateStockRawData]]] = {}


BridgeRunner = Callable[[str, dict[str, Any], str], dict[str, Any]]


class EltdxProvider(StockDataProvider):
    """Latest-data provider backed by the eltdx bridge."""

    def __init__(
        self,
        *,
        python_executable: str | None = None,
        runner: BridgeRunner | None = None,
        request_timeout: float = 8.0,
        bridge_script: str | None = None,
    ) -> None:
        self.python_executable = python_executable or _default_bridge_python()
        self.request_timeout = request_timeout
        self.bridge_script = (
            Path(bridge_script)
            if bridge_script
            else Path(__file__).resolve().parents[3] / "scripts" / "eltdx_bridge.py"
        )
        if runner is None:
            self._runner = lambda operation, payload, python_executable: _run_bridge(
                operation,
                payload,
                python_executable,
                self.bridge_script,
            )
        else:
            self._runner = runner

    def fetch_market(self) -> MarketRawData:
        cache_key = (self.python_executable, self.request_timeout)
        cached = _load_cache(_MARKET_CACHE, cache_key)
        if cached is not None:
            return cached
        try:
            payload = self._runner(
                "market",
                {"timeout": self.request_timeout},
                self.python_executable,
            )
            result = MarketRawData(
                trade_date=str(payload.get("trade_date") or "latest"),
                indices=[
                    IndexQuote(
                        code=str(item.get("code") or ""),
                        name=str(item.get("name") or item.get("code") or ""),
                        close=float(item.get("close", 0.0)),
                        pct_chg=float(item.get("pct_chg", 0.0)),
                        amount=float(item.get("amount", 0.0)),
                    )
                    for item in _as_list(payload.get("indices"))
                ],
                advancing=int(payload.get("advancing", 0)),
                declining=int(payload.get("declining", 0)),
                limit_up=int(payload.get("limit_up", 0)),
                limit_down=int(payload.get("limit_down", 0)),
                top_sectors=[
                    (localize_sector_name(item[0]), float(item[1]))
                    for item in _as_list(payload.get("top_sectors"))
                    if isinstance(item, (list, tuple)) and len(item) >= 2
                ],
                northbound_net_inflow=_optional_float(payload.get("northbound_net_inflow")),
            )
            _store_cache(_MARKET_CACHE, cache_key, result)
            return result
        except Exception as exc:
            warnings.warn(
                f"eltdx market unavailable, falling back to Tencent/sample: {exc}",
                RuntimeWarning,
                stacklevel=2,
            )
            try:
                return TencentProvider(request_timeout=1.5).fetch_market()
            except Exception:
                return SampleDataProvider().fetch_market()

    def fetch_stock(self, code: str) -> StockRawData:
        normalized_code = code.strip()
        cache_key = (normalized_code, self.request_timeout)
        cached = _load_cache(_STOCK_CACHE, cache_key)
        if cached is not None:
            return cached
        try:
            payload = self._runner(
                "stock",
                {"code": normalized_code, "timeout": self.request_timeout},
                self.python_executable,
            )
            bars = [_bar_from_dict(item) for item in _as_list(payload.get("bars"))]
            result = StockRawData(
                code=str(payload.get("code") or normalized_code),
                name=str(payload.get("name") or normalized_code),
                bars=bars or SampleDataProvider().fetch_stock(normalized_code).bars,
                fund_flow=_optional_float(payload.get("fund_flow")),
                pe_ttm=_optional_float(payload.get("pe_ttm")),
            )
            _store_cache(_STOCK_CACHE, cache_key, result)
            return result
        except Exception as exc:
            warnings.warn(
                f"eltdx stock {normalized_code} unavailable, falling back to Tencent/sample: {exc}",
                RuntimeWarning,
                stacklevel=2,
            )
            try:
                return TencentProvider(request_timeout=1.5).fetch_stock(normalized_code)
            except Exception:
                return SampleDataProvider().fetch_stock(normalized_code)

    def fetch_sectors(self) -> list[SectorRawData]:
        cache_key = (self.python_executable, self.request_timeout)
        cached = _load_cache(_SECTOR_CACHE, cache_key)
        if cached is not None:
            return cached
        try:
            payload = self._runner(
                "sectors",
                {"timeout": self.request_timeout, "limit": 10},
                self.python_executable,
            )
            sectors = [
                SectorRawData(
                    name=localize_sector_name(item.get("name")),
                    pct_chg=float(item.get("pct_chg", 0.0)),
                    advancing_ratio=float(item.get("advancing_ratio", 0.0)),
                    amount_change=float(item.get("amount_change", 0.0)),
                    fund_flow=_optional_float(item.get("fund_flow")),
                    consecutive_days=int(item.get("consecutive_days", 1)),
                    limit_up_count=int(item.get("limit_up_count", 0)),
                    high_divergence=bool(item.get("high_divergence", False)),
                )
                for item in _as_list(payload.get("sectors"))
            ]
            if sectors:
                _store_cache(_SECTOR_CACHE, cache_key, sectors)
                return sectors
        except Exception as exc:
            warnings.warn(
                f"eltdx sectors unavailable, falling back to sample sectors: {exc}",
                RuntimeWarning,
                stacklevel=2,
            )
        sectors = SampleDataProvider().fetch_sectors()
        _store_cache(_SECTOR_CACHE, cache_key, sectors)
        return sectors

    def fetch_candidate_universe(self) -> list[CandidateStockRawData]:
        cache_key = (self.python_executable, self.request_timeout)
        cached = _load_cache(_CANDIDATE_CACHE, cache_key)
        if cached is not None:
            return cached
        try:
            payload = self._runner(
                "candidate_universe",
                {"timeout": self.request_timeout, "limit": 120},
                self.python_executable,
            )
            candidates = [
                _candidate_from_bridge_item(item) for item in _as_list(payload.get("items"))
            ]
            if candidates:
                _store_cache(_CANDIDATE_CACHE, cache_key, candidates)
                return candidates
        except Exception as exc:
            warnings.warn(
                f"eltdx candidate universe unavailable, falling back to sample: {exc}",
                RuntimeWarning,
                stacklevel=2,
            )
        candidates = SampleDataProvider().fetch_candidate_universe()
        _store_cache(_CANDIDATE_CACHE, cache_key, candidates)
        return candidates


@lru_cache(maxsize=1)
def is_eltdx_bridge_available(python_executable: str | None = None) -> bool:
    executable = python_executable or _default_bridge_python()
    if not shutil.which(executable):
        return False
    script = "import eltdx"
    result = subprocess.run(
        [executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=8,
        check=False,
    )
    return result.returncode == 0


def _default_bridge_python() -> str:
    return os.getenv("STOCK_TS_ELTDX_PYTHON") or os.getenv("STOCK_TS_TDX_PYTHON") or sys.executable


def _run_bridge(
    operation: str,
    payload: dict[str, Any],
    python_executable: str,
    script_path: Path,
) -> dict[str, Any]:
    if not script_path.exists():
        raise DataProviderError(f"eltdx bridge script not found: {script_path}")
    result = subprocess.run(
        [python_executable, str(script_path), operation],
        input=json.dumps(payload, ensure_ascii=False),
        capture_output=True,
        text=True,
        timeout=max(float(payload.get("timeout", 8.0)) + 90.0, 120.0),
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise DataProviderError(detail or f"eltdx bridge failed for operation {operation}")
    try:
        return json.loads(result.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise DataProviderError("eltdx bridge returned invalid JSON") from exc


def _load_cache(
    cache: dict[tuple[str, float], tuple[float, Any]],
    key: tuple[str, float],
) -> Any | None:
    now = time.monotonic()
    with _CACHE_LOCK:
        entry = cache.get(key)
        if entry is None:
            return None
        created_at, value = entry
        if now - created_at > _CACHE_TTL_SECONDS:
            cache.pop(key, None)
            return None
        return value


def _store_cache(
    cache: dict[tuple[str, float], tuple[float, Any]],
    key: tuple[str, float],
    value: Any,
) -> None:
    with _CACHE_LOCK:
        cache[key] = (time.monotonic(), value)


def _bar_from_dict(item: object) -> DailyBar:
    if not isinstance(item, dict):
        raise DataProviderError("eltdx bridge bar must be an object")
    return DailyBar(
        date=str(item.get("date") or ""),
        open=float(item.get("open", 0.0)),
        high=float(item.get("high", 0.0)),
        low=float(item.get("low", 0.0)),
        close=float(item.get("close", 0.0)),
        volume=float(item.get("volume", 0.0)),
    )


def _candidate_from_bridge_item(item: object) -> CandidateStockRawData:
    if not isinstance(item, dict):
        raise DataProviderError("eltdx bridge candidate must be an object")
    bars = [_bar_from_dict(bar) for bar in _as_list(item.get("bars"))]
    return CandidateStockRawData(
        code=str(item.get("code") or ""),
        name=str(item.get("name") or item.get("code") or ""),
        sector=localize_sector_name(item.get("sector")),
        bars=bars,
        fund_flow=_optional_float(item.get("fund_flow")),
        turnover_rate=float(item.get("turnover_rate", 0.0)),
        amount=float(item.get("amount", 0.0)),
        pe_ttm=_optional_float(item.get("pe_ttm")),
        price_reliable=_bars_have_explicit_dates(bars),
    )


def _bars_have_explicit_dates(bars: list[DailyBar]) -> bool:
    if len(bars) < 2:
        return False
    for bar in bars[-2:]:
        date = bar.date.strip()
        if date.startswith("latest") or len(date) < 10:
            return False
    return True


def _as_list(value: object) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def _optional_float(value: object) -> float | None:
    if value in {None, ""}:
        return None
    return float(value)
