from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


class MiniFrame:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows
        self.empty = not rows

    def to_dict(self, orient: str):
        assert orient == "records"
        return list(self._rows)


class FakeTushareClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int]] = []

    def daily(self, ts_code: str, limit: int):
        self.calls.append((ts_code, limit))
        return MiniFrame(
            [
                {
                    "trade_date": "20260625",
                    "open": 11.56,
                    "high": 11.67,
                    "low": 11.15,
                    "close": 11.18,
                    "vol": 176918,
                },
                {
                    "trade_date": "20260626",
                    "open": 11.13,
                    "high": 11.17,
                    "low": 10.77,
                    "close": 10.81,
                    "vol": 147381,
                },
            ]
        )


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "refresh_a_share_kline", Path("scripts/refresh_a_share_kline.py")
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["refresh_a_share_kline"] = module
    spec.loader.exec_module(module)
    return module


def test_refresh_a_share_kline_writes_tushare_bars_to_stocks_and_candidates(tmp_path: Path) -> None:
    module = _load_module()
    snapshot = tmp_path / "tdx_snapshots.json"
    holdings = tmp_path / "holdings.csv"
    holdings.write_text(
        "code,name,shares,cost_price,sector,note\n"
        "603278,大业股份,100,10,高端装备,测试\n"
        "06088,FIT HON TENG,100,6,港股电子,测试\n",
        encoding="utf-8",
    )
    snapshot.write_text(
        json.dumps(
            {
                "stocks": {"603278": {"name": "大业股份"}},
                "candidate_universe": {
                    "items": [
                        {"code": "603278", "name": "大业股份"},
                        {"code": "688362", "name": "甬矽电子"},
                        {"code": "920363", "name": "北交所样本"},
                    ]
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    client = FakeTushareClient()

    result = module.refresh_a_share_kline_snapshot(
        snapshot,
        holdings_path=holdings,
        codes=None,
        candidate_limit=3,
        bar_count=120,
        tushare_client=client,
    )

    payload = json.loads(snapshot.read_text(encoding="utf-8"))
    stock = payload["stocks"]["603278"]
    candidate = payload["candidate_universe"]["items"][0]
    assert result["updated_count"] == 3
    assert result["skipped_count"] == 1
    assert stock["bar_source"] == "tushare.daily"
    assert stock["bars"][-1]["date"] == "2026-06-26"
    assert stock["bars"][-1]["close"] == 10.81
    assert candidate["bar_source"] == "tushare.daily"
    assert payload["kline_refresh"]["source"] == "tushare.daily"
    assert ("06088.SZ", 120) not in client.calls
    assert ("603278.SH", 120) in client.calls
    assert ("688362.SH", 120) in client.calls
    assert ("920363.BJ", 120) in client.calls


class RateLimitThenSuccessClient:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def daily(self, ts_code: str, limit: int):
        self.calls.append(ts_code)
        if ts_code == "688362.SH":
            raise RuntimeError("抱歉，您访问接口(daily)频率超限(50次/分钟)")
        return MiniFrame(
            [
                {
                    "trade_date": "20260703",
                    "open": 10.0,
                    "high": 11.0,
                    "low": 9.8,
                    "close": 10.5,
                    "vol": 1000,
                }
            ]
        )


def test_refresh_a_share_kline_treats_rate_limited_subset_as_partial_success(
    tmp_path: Path,
) -> None:
    module = _load_module()
    snapshot = tmp_path / "tdx_snapshots.json"
    snapshot.write_text(
        json.dumps(
            {
                "stocks": {},
                "candidate_universe": {
                    "items": [
                        {"code": "603278", "name": "大业股份"},
                        {"code": "688362", "name": "甬矽电子"},
                    ]
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    client = RateLimitThenSuccessClient()

    result = module.refresh_a_share_kline_snapshot(
        snapshot,
        holdings_path=None,
        codes=None,
        candidate_limit=2,
        bar_count=120,
        tushare_client=client,
    )

    assert result["updated_count"] == 1
    assert result["failed_count"] == 1
    assert result["status"] == "partial"
    assert result["rate_limited_count"] == 1
    assert result["usable"] is True
    payload = json.loads(snapshot.read_text(encoding="utf-8"))
    assert payload["kline_refresh"]["status"] == "partial"
    assert payload["stocks"]["603278"]["bar_source"] == "tushare.daily"


class StaleTushareClient:
    def daily(self, ts_code: str, limit: int):
        return MiniFrame(
            [
                {
                    "trade_date": "20260714",
                    "open": 39.0,
                    "high": 41.2,
                    "low": 38.8,
                    "close": 41.0,
                    "vol": 180000,
                }
            ]
        )


def test_refresh_marks_bars_stale_when_they_lag_market_trade_date(tmp_path: Path) -> None:
    module = _load_module()
    snapshot = tmp_path / "tdx_snapshots.json"
    snapshot.write_text(
        json.dumps(
            {
                "market": {"trade_date": "2026-07-15"},
                "stocks": {"300725": {"name": "药石科技"}},
                "candidate_universe": {
                    "items": [{"code": "300725", "name": "药石科技"}]
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = module.refresh_a_share_kline_snapshot(
        snapshot,
        holdings_path=None,
        codes=["300725"],
        bar_count=120,
        tushare_client=StaleTushareClient(),
    )

    payload = json.loads(snapshot.read_text(encoding="utf-8"))
    assert result["status"] == "stale"
    assert result["stale_count"] == 1
    assert result["stale_codes"] == ["300725"]
    assert payload["stocks"]["300725"]["price_reliable"] is False
    assert payload["candidate_universe"]["items"][0]["price_reliable"] is False


def test_refresh_before_daily_publication_cutoff_accepts_previous_close(
    tmp_path: Path,
) -> None:
    module = _load_module()
    snapshot = tmp_path / "tdx_snapshots.json"
    snapshot.write_text(
        json.dumps(
            {
                "market": {"trade_date": "2026-07-16"},
                "stocks": {"300725": {"name": "药石科技"}},
                "candidate_universe": {
                    "items": [{"code": "300725", "name": "药石科技"}]
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    class PreviousCloseClient:
        def daily(self, ts_code: str, limit: int):
            return MiniFrame(
                [
                    {
                        "trade_date": "20260715",
                        "open": 39.0,
                        "high": 41.2,
                        "low": 38.8,
                        "close": 41.0,
                        "vol": 180000,
                    }
                ]
            )

    result = module.refresh_a_share_kline_snapshot(
        snapshot,
        holdings_path=None,
        codes=["300725"],
        tushare_client=PreviousCloseClient(),
        now=datetime(2026, 7, 16, 16, 0, tzinfo=ZoneInfo("Asia/Shanghai")),
    )

    payload = json.loads(snapshot.read_text(encoding="utf-8"))
    assert result["status"] == "ok"
    assert result["stale_count"] == 0
    assert result["expected_trade_date"] == "2026-07-15"
    assert payload["stocks"]["300725"]["price_reliable"] is True


def test_refresh_uses_exchange_calendar_for_holiday(tmp_path: Path) -> None:
    module = _load_module()
    snapshot = tmp_path / "tdx_snapshots.json"
    snapshot.write_text(
        json.dumps(
            {
                "market": {"trade_date": "2026-10-08"},
                "stocks": {"300725": {"name": "药石科技"}},
                "candidate_universe": {
                    "items": [{"code": "300725", "name": "药石科技"}]
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    class HolidayCalendarClient:
        def trade_cal(self, **_kwargs):
            return MiniFrame(
                [
                    {"cal_date": "20260930", "is_open": 1},
                    {"cal_date": "20261001", "is_open": 0},
                    {"cal_date": "20261008", "is_open": 1},
                ]
            )

        def daily(self, ts_code: str, limit: int):
            return MiniFrame(
                [
                    {
                        "trade_date": "20260930",
                        "open": 39.0,
                        "high": 41.2,
                        "low": 38.8,
                        "close": 41.0,
                        "vol": 180000,
                    }
                ]
            )

    result = module.refresh_a_share_kline_snapshot(
        snapshot,
        holdings_path=None,
        codes=["300725"],
        tushare_client=HolidayCalendarClient(),
        now=datetime(2026, 10, 8, 13, 0, tzinfo=ZoneInfo("Asia/Shanghai")),
    )

    assert result["expected_trade_date"] == "2026-09-30"
    assert result["stale_count"] == 0


def test_stale_response_does_not_overwrite_newer_snapshot_bars(tmp_path: Path) -> None:
    module = _load_module()
    snapshot = tmp_path / "tdx_snapshots.json"
    current_bar = {
        "date": "2026-07-15",
        "open": 41.0,
        "high": 42.0,
        "low": 40.5,
        "close": 41.5,
        "volume": 200000,
    }
    snapshot.write_text(
        json.dumps(
            {
                "market": {"trade_date": "2026-07-15"},
                "stocks": {
                    "300725": {
                        "name": "药石科技",
                        "bars": [current_bar],
                        "price_reliable": True,
                    }
                },
                "candidate_universe": {
                    "items": [
                        {
                            "code": "300725",
                            "name": "药石科技",
                            "bars": [current_bar],
                            "price_reliable": True,
                        }
                    ]
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = module.refresh_a_share_kline_snapshot(
        snapshot,
        holdings_path=None,
        codes=["300725"],
        tushare_client=StaleTushareClient(),
    )

    payload = json.loads(snapshot.read_text(encoding="utf-8"))
    assert result["preserved_newer_count"] == 1
    assert result["preserved_newer_codes"] == ["300725"]
    assert payload["stocks"]["300725"]["bars"][-1]["date"] == "2026-07-15"
    assert payload["stocks"]["300725"]["price_reliable"] is True
    assert payload["candidate_universe"]["items"][0]["bars"][-1]["date"] == "2026-07-15"
