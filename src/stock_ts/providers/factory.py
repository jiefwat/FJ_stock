from __future__ import annotations

import os

from stock_ts.providers.akshare_provider import AkshareProvider
from stock_ts.providers.base import StockDataProvider
from stock_ts.providers.eltdx_provider import EltdxProvider, is_eltdx_bridge_available
from stock_ts.providers.sample import SampleDataProvider
from stock_ts.providers.tdx_snapshot_provider import TdxSnapshotProvider
from stock_ts.providers.tencent_provider import TencentProvider
from stock_ts.providers.tushare_provider import TushareProvider


def create_provider(name: str) -> StockDataProvider:
    normalized = name.strip().lower()
    if normalized == "sample":
        return SampleDataProvider()
    if normalized == "eltdx":
        return EltdxProvider()
    if normalized == "tencent":
        return TencentProvider()
    if normalized == "auto":
        if _prefer_eltdx_auto() and is_eltdx_bridge_available():
            return EltdxProvider(request_timeout=2.0)
        return TencentProvider(request_timeout=1.5)
    if normalized == "tdx-snapshot":
        return TdxSnapshotProvider()
    if normalized == "tushare":
        return TushareProvider()
    if normalized == "akshare":
        return AkshareProvider()
    raise ValueError(f"Unknown provider: {name}")


def _prefer_eltdx_auto() -> bool:
    return os.getenv("STOCK_TS_AUTO_PREFER_ELTDX", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
