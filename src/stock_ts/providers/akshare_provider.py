from __future__ import annotations

import warnings

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


class AkshareProvider(StockDataProvider):
    """AKShare provider kept behind an adapter so core analysis stays mockable."""

    def __init__(self) -> None:
        try:
            import akshare as ak  # type: ignore[import-not-found]
        except ImportError as exc:
            raise DataProviderError("AKShare is not installed. Run: pip install akshare") from exc
        self._ak = ak

    def fetch_market(self) -> MarketRawData:
        index_map = {
            "000001": "上证指数",
            "399001": "深证成指",
            "399006": "创业板指",
        }
        indices = []
        for code, name in index_map.items():
            try:
                frame = self._ak.stock_zh_index_daily_em(symbol=code)
            except Exception as exc:
                warnings.warn(
                    f"AKShare index {code} unavailable: {exc}",
                    RuntimeWarning,
                    stacklevel=2,
                )
                continue
            if frame.empty:
                continue
            latest = frame.iloc[-1]
            previous = frame.iloc[-2] if len(frame) >= 2 else latest
            pct = (
                0.0
                if previous["close"] == 0
                else (latest["close"] - previous["close"]) / previous["close"] * 100
            )
            indices.append(
                IndexQuote(
                    code=code,
                    name=name,
                    close=float(latest["close"]),
                    pct_chg=float(pct),
                    amount=float(latest.get("amount", 0.0)) / 100000000,
                )
            )

        advancing = 0
        declining = 0
        limit_up = 0
        limit_down = 0
        trade_date = ""
        try:
            spot = self._ak.stock_zh_a_spot_em()
            pct_col = "涨跌幅"
            advancing = int((spot[pct_col] > 0).sum()) if pct_col in spot else 0
            declining = int((spot[pct_col] < 0).sum()) if pct_col in spot else 0
            limit_up = int((spot[pct_col] >= 9.8).sum()) if pct_col in spot else 0
            limit_down = int((spot[pct_col] <= -9.8).sum()) if pct_col in spot else 0
            trade_date = str(spot.iloc[0].get("数据日期", "")) if not spot.empty else ""
        except Exception as exc:
            warnings.warn(
                f"AKShare spot data unavailable, falling back to index-only market: {exc}",
                RuntimeWarning,
                stacklevel=2,
            )

        return MarketRawData(
            trade_date=trade_date or "latest",
            indices=indices,
            advancing=advancing,
            declining=declining,
            limit_up=limit_up,
            limit_down=limit_down,
            top_sectors=[],
            northbound_net_inflow=None,
        )

    def fetch_stock(self, code: str) -> StockRawData:
        symbol = code.strip()
        try:
            frame = self._ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust="qfq")
        except Exception as exc:
            warnings.warn(
                f"AKShare stock {symbol} unavailable, falling back to sample: {exc}",
                RuntimeWarning,
                stacklevel=2,
            )
            return SampleDataProvider().fetch_stock(symbol)
        if frame.empty:
            warnings.warn(
                f"AKShare stock {symbol} returned no history, falling back to sample",
                RuntimeWarning,
                stacklevel=2,
            )
            return SampleDataProvider().fetch_stock(symbol)
        bars = [
            DailyBar(
                date=str(row["日期"]),
                open=float(row["开盘"]),
                high=float(row["最高"]),
                low=float(row["最低"]),
                close=float(row["收盘"]),
                volume=float(row["成交量"]),
            )
            for _, row in frame.tail(80).iterrows()
        ]
        name = symbol
        if "股票名称" in frame.columns:
            name = str(frame.iloc[-1]["股票名称"])
        return StockRawData(code=symbol, name=name, bars=bars)

    def fetch_sectors(self) -> list[SectorRawData]:
        try:
            frame = self._ak.stock_board_industry_name_em()
        except Exception as exc:
            warnings.warn(
                f"AKShare industry board unavailable, falling back to sample sectors: {exc}",
                RuntimeWarning,
                stacklevel=2,
            )
            return SampleDataProvider().fetch_sectors()
        sectors: list[SectorRawData] = []
        for _index, row in frame.iterrows():
            name = _row_text(row, "板块名称", "行业名称", "name")
            if not name:
                continue
            up_count = _row_float(row, "上涨家数", default=0.0)
            down_count = _row_float(row, "下跌家数", default=0.0)
            total = up_count + down_count
            advancing_ratio = up_count / total if total else 0.5
            pct_chg = _row_float(row, "涨跌幅", "涨幅", default=0.0)
            sectors.append(
                SectorRawData(
                    name=name,
                    pct_chg=pct_chg,
                    advancing_ratio=advancing_ratio,
                    amount_change=_row_float(row, "换手率", "成交额", default=0.0),
                    fund_flow=None,
                    consecutive_days=1,
                    limit_up_count=int(_row_float(row, "涨停家数", default=0.0)),
                    high_divergence=pct_chg >= 6,
                )
            )
        if not sectors:
            warnings.warn(
                "AKShare industry board returned no rows, falling back to sample sectors",
                RuntimeWarning,
                stacklevel=2,
            )
            return SampleDataProvider().fetch_sectors()
        return sectors

    def fetch_candidate_universe(self) -> list[CandidateStockRawData]:
        try:
            return self._candidate_universe_from_spot()
        except Exception as spot_exc:
            warnings.warn(
                "AKShare spot candidate universe unavailable, "
                f"falling back to industry boards: {spot_exc}",
                RuntimeWarning,
                stacklevel=2,
            )
        candidates: list[CandidateStockRawData] = []
        errors: list[str] = []
        for sector in self.fetch_sectors()[:8]:
            try:
                frame = self._ak.stock_board_industry_cons_em(symbol=sector.name)
            except Exception as exc:
                errors.append(f"{sector.name}: {exc}")
                continue
            for _index, row in frame.iterrows():
                candidate = _candidate_from_row(row, sector=sector.name)
                if candidate is not None:
                    candidates.append(candidate)
                if len(candidates) >= 120:
                    return candidates
        if not candidates:
            detail = "; ".join(errors[:3]) if errors else "no constituents returned"
            warnings.warn(
                f"AKShare candidate universe unavailable, falling back to sample: {detail}",
                RuntimeWarning,
                stacklevel=2,
            )
            return SampleDataProvider().fetch_candidate_universe()
        return candidates

    def _candidate_universe_from_spot(self) -> list[CandidateStockRawData]:
        frame = self._ak.stock_zh_a_spot_em()
        candidates: list[CandidateStockRawData] = []
        for _index, row in frame.iterrows():
            candidate = _candidate_from_row(row, sector=_row_text(row, "所属行业") or "未分类")
            if candidate is not None:
                candidates.append(candidate)
            if len(candidates) >= 300:
                break
        if not candidates:
            raise DataProviderError("AKShare spot returned no candidate rows")
        return candidates


def _candidate_from_row(row: object, *, sector: str) -> CandidateStockRawData | None:
    code = _row_text(row, "代码", "code")
    name = _row_text(row, "名称", "股票名称", "name") or code
    latest_close = _row_float(row, "最新价", "最新", "close", default=0.0)
    if not code or latest_close <= 0:
        return None
    pct = _row_float(row, "涨跌幅", "pct_chg", default=0.0)
    return CandidateStockRawData(
        code=code,
        name=name,
        sector=sector or "未分类",
        bars=_synthetic_bars(latest_close, pct),
        fund_flow=None,
        turnover_rate=_row_float(row, "换手率", default=0.0),
        amount=_row_float(row, "成交额", default=0.0) / 100000000,
        pe_ttm=_row_float(row, "市盈率-动态", "市盈率", "PE", default=0.0) or None,
        price_reliable=False,
    )


def _synthetic_bars(latest_close: float, pct_change: float) -> list[DailyBar]:
    previous = latest_close / (1 + pct_change / 100) if pct_change != -100 else latest_close
    bars = []
    for index in range(10):
        weight = index / 9
        close = previous * (1 - weight) + latest_close * weight
        bars.append(
            DailyBar(
                date=f"latest-{9 - index}",
                open=close * 0.995,
                high=close * 1.012,
                low=close * 0.988,
                close=close,
                volume=1000 + index * 100,
            )
        )
    return bars


def _row_text(row: object, *keys: str) -> str:
    for key in keys:
        value = row.get(key, "")  # type: ignore[attr-defined]
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _row_float(row: object, *keys: str, default: float = 0.0) -> float:
    for key in keys:
        value = row.get(key, None)  # type: ignore[attr-defined]
        if value in (None, ""):
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return default
