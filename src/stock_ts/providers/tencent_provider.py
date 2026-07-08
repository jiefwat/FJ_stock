from __future__ import annotations

import json
import re
import time
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import RLock
from urllib.parse import urlencode
from urllib.request import Request, urlopen

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
from stock_ts.symbols import stock_name_for_code

_QUOTE_URL = "https://qt.gtimg.cn/q={symbol}"
_KLINE_URL = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
_USER_AGENT = "Mozilla/5.0 StockTS/0.1"
_DEFAULT_TIMEOUT = 10.0
_CACHE_TTL_SECONDS = 90.0
_CACHE_LOCK = RLock()
_MARKET_CACHE: dict[tuple[float], tuple[float, MarketRawData]] = {}
_STOCK_CACHE: dict[tuple[str, float], tuple[float, StockRawData]] = {}


class TencentProvider(StockDataProvider):
    """No-dependency Tencent quote provider for fresher A-share stock bars."""

    def __init__(self, *, request_timeout: float = _DEFAULT_TIMEOUT) -> None:
        self.request_timeout = request_timeout

    def fetch_market(self) -> MarketRawData:
        cache_key = (self.request_timeout,)
        cached = _load_cache(_MARKET_CACHE, cache_key)
        if cached is not None:
            return cached

        indices: list[IndexQuote] = []
        trade_date = ""
        index_map = {
            "sh000001": "上证指数",
            "sz399001": "深证成指",
            "sz399006": "创业板指",
        }
        with ThreadPoolExecutor(max_workers=len(index_map)) as executor:
            future_map = {
                executor.submit(_fetch_quote, symbol, timeout=self.request_timeout): (
                    symbol,
                    name,
                )
                for symbol, name in index_map.items()
            }
            for future in as_completed(future_map):
                symbol, name = future_map[future]
                try:
                    quote = future.result()
                except Exception as exc:
                    warnings.warn(
                        f"Tencent index {symbol} unavailable: {exc}",
                        RuntimeWarning,
                        stacklevel=2,
                    )
                    continue
                fields = quote.fields
                indices.append(
                    IndexQuote(
                        code=fields[2],
                        name=name or fields[1],
                        close=_float_at(fields, 3),
                        pct_chg=_float_at(fields, 32),
                        amount=_float_at(fields, 37) / 10000,
                    )
                )
                trade_date = trade_date or _quote_date(fields)

        if not indices:
            warnings.warn(
                "Tencent index data unavailable, falling back to sample market",
                RuntimeWarning,
                stacklevel=2,
            )
            return SampleDataProvider().fetch_market()

        result = MarketRawData(
            trade_date=trade_date or "latest",
            indices=indices,
            advancing=1,
            declining=1,
            limit_up=0,
            limit_down=0,
            top_sectors=[],
            northbound_net_inflow=None,
        )
        _store_cache(_MARKET_CACHE, cache_key, result)
        return result

    def fetch_stock(self, code: str) -> StockRawData:
        normalized_code = code.strip()
        cache_key = (normalized_code, self.request_timeout)
        cached = _load_cache(_STOCK_CACHE, cache_key)
        if cached is not None:
            return cached

        symbol = _market_symbol(code)
        try:
            with ThreadPoolExecutor(max_workers=2) as executor:
                quote_future = executor.submit(_fetch_quote, symbol, timeout=self.request_timeout)
                bars_future = executor.submit(
                    _fetch_kline,
                    symbol,
                    count=80,
                    timeout=self.request_timeout,
                )
                quote = quote_future.result()
                bars = bars_future.result()
        except Exception as exc:
            warnings.warn(
                f"Tencent stock {code} unavailable, falling back to sample: {exc}",
                RuntimeWarning,
                stacklevel=2,
            )
            return SampleDataProvider().fetch_stock(normalized_code)

        fields = quote.fields
        name = (
            fields[1]
            if len(fields) > 1 and fields[1]
            else stock_name_for_code(normalized_code) or normalized_code
        )
        if bars:
            result = StockRawData(code=normalized_code, name=name, bars=bars)
            _store_cache(_STOCK_CACHE, cache_key, result)
            return result

        latest = DailyBar(
            date=_quote_date(fields),
            open=_float_at(fields, 5),
            high=_float_at(fields, 33),
            low=_float_at(fields, 34),
            close=_float_at(fields, 3),
            volume=_float_at(fields, 6),
        )
        result = StockRawData(code=normalized_code, name=name, bars=[latest])
        _store_cache(_STOCK_CACHE, cache_key, result)
        return result

    def fetch_sectors(self) -> list[SectorRawData]:
        warnings.warn(
            "Tencent provider has no sector endpoint yet, using sample sectors",
            RuntimeWarning,
            stacklevel=2,
        )
        return SampleDataProvider().fetch_sectors()

    def fetch_candidate_universe(self) -> list[CandidateStockRawData]:
        warnings.warn(
            "Tencent provider has no candidate universe yet, using sample candidates",
            RuntimeWarning,
            stacklevel=2,
        )
        return SampleDataProvider().fetch_candidate_universe()


class _TencentQuote:
    def __init__(self, symbol: str, fields: list[str]) -> None:
        self.symbol = symbol
        self.fields = fields


def _fetch_quote(symbol: str, *, timeout: float = _DEFAULT_TIMEOUT) -> _TencentQuote:
    text = _read_text(_QUOTE_URL.format(symbol=symbol), encoding="gbk", timeout=timeout)
    match = re.search(r'v_([^=]+)="(.*)";?', text)
    if not match:
        raise DataProviderError(f"invalid Tencent quote response for {symbol}")
    fields = match.group(2).split("~")
    if len(fields) < 40:
        raise DataProviderError(f"incomplete Tencent quote response for {symbol}")
    return _TencentQuote(symbol=match.group(1), fields=fields)


def _fetch_kline(symbol: str, *, count: int, timeout: float = _DEFAULT_TIMEOUT) -> list[DailyBar]:
    params = urlencode({"param": f"{symbol},day,,,{count},qfq"})
    payload = json.loads(_read_text(f"{_KLINE_URL}?{params}", encoding="utf-8", timeout=timeout))
    stock_data = payload.get("data", {}).get(symbol, {})
    rows = stock_data.get("qfqday") or stock_data.get("day") or []
    bars: list[DailyBar] = []
    for row in rows:
        if len(row) < 6:
            continue
        bars.append(
            DailyBar(
                date=str(row[0]),
                open=float(row[1]),
                close=float(row[2]),
                high=float(row[3]),
                low=float(row[4]),
                volume=float(row[5]),
            )
        )
    if not bars:
        raise DataProviderError(f"empty Tencent kline response for {symbol}")
    return bars


def _read_text(url: str, *, encoding: str, timeout: float = _DEFAULT_TIMEOUT) -> str:
    request = Request(url, headers={"User-Agent": _USER_AGENT, "Referer": "https://gu.qq.com/"})
    with urlopen(request, timeout=timeout) as response:
        return response.read().decode(encoding, errors="replace")


def _market_symbol(code: str) -> str:
    normalized = code.strip().lower()
    if normalized.startswith(("sh", "sz")):
        return normalized
    if normalized.startswith(("5", "6", "9")):
        return f"sh{normalized}"
    return f"sz{normalized}"


def _float_at(fields: list[str], index: int, default: float = 0.0) -> float:
    try:
        return float(fields[index])
    except (IndexError, TypeError, ValueError):
        return default


def _quote_date(fields: list[str]) -> str:
    raw = fields[30] if len(fields) > 30 else ""
    if len(raw) >= 8 and raw[:8].isdigit():
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"
    return "latest"


def _load_cache(cache: dict[tuple[object, ...], tuple[float, object]], key: tuple[object, ...]):
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
    cache: dict[tuple[object, ...], tuple[float, object]],
    key: tuple[object, ...],
    value: object,
) -> None:
    with _CACHE_LOCK:
        cache[key] = (time.monotonic(), value)
