from __future__ import annotations

import importlib.util
import json
from datetime import date, timedelta
from pathlib import Path


def _load_refresh_module():
    spec = importlib.util.spec_from_file_location(
        "refresh_tdx_snapshot", Path("scripts/refresh_tdx_snapshot.py")
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _market_payload(
    trade_date: str,
    *,
    advancing: int = 2200,
    declining: int = 2500,
) -> dict[str, object]:
    return {
        "trade_date": trade_date,
        "indices": [
            {
                "code": "000001",
                "name": "上证指数",
                "close": 3500,
                "pct_chg": 0.5,
                "amount": 5000,
            }
        ],
        "advancing": advancing,
        "declining": declining,
        "limit_up": 60,
        "limit_down": 12,
        "top_sectors": [],
    }


def test_refresh_snapshot_accumulates_market_history(tmp_path: Path) -> None:
    module = _load_refresh_module()
    output = tmp_path / "snapshot.json"
    output.write_text(
        json.dumps({"market": _market_payload("2026-07-09")}),
        encoding="utf-8",
    )

    def runner(operation: str, payload: dict[str, object], python_executable: str):
        if operation == "market":
            return _market_payload("2026-07-10", advancing=2700, declining=2100)
        if operation == "sectors":
            return {"sectors": []}
        if operation == "candidate_universe":
            return {"scanned_count": 0, "items": []}
        raise AssertionError(operation)

    module.refresh_snapshot(output, runner=runner, python_executable="python")

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert [row["trade_date"] for row in payload["market_history"]] == [
        "2026-07-09",
        "2026-07-10",
    ]
    assert payload["market_history"][-1]["breadth_ratio"] == 1.2857
    assert payload["market_history"][-1]["amount"] == 5000.0


def test_market_history_deduplicates_bad_rows_and_keeps_latest_60() -> None:
    module = _load_refresh_module()
    start = date(2026, 4, 1)
    rows = [
        _market_payload((start + timedelta(days=offset)).isoformat())
        for offset in range(70)
    ]
    latest_date = str(rows[-1]["trade_date"])
    rows.extend(
        [
            _market_payload(latest_date, advancing=3000, declining=1000),
            {"trade_date": "bad-date"},
            {"trade_date": "2026-07-11", "advancing": 1, "declining": "bad"},
        ]
    )

    result = module._merge_market_history(rows, limit=60)

    assert len(result) == 60
    assert result[-1]["trade_date"] == latest_date
    assert result[-1]["advancing"] == 3000
    assert result[-1]["breadth_ratio"] == 3.0


def test_refresh_tdx_snapshot_merges_full_market_candidate_metadata(tmp_path: Path) -> None:
    module = _load_refresh_module()
    output = tmp_path / "tdx.json"
    output.write_text(
        json.dumps(
            {
                "stocks": {
                    "600519": {
                        "name": "贵州茅台",
                        "bars": [
                            {
                                "date": "2026-06-18",
                                "open": 100,
                                "high": 101,
                                "low": 99,
                                "close": 100,
                                "volume": 1000,
                            }
                        ],
                    }
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    def fake_runner(operation: str, payload: dict[str, object], python_executable: str):
        if operation == "market":
            return {
                "trade_date": "2026-06-20",
                "indices": [],
                "advancing": 3000,
                "declining": 1900,
                "limit_up": 80,
                "limit_down": 8,
                "top_sectors": [],
            }
        if operation == "sectors":
            return {"trade_date": "2026-06-20", "sectors": []}
        if operation == "candidate_universe":
            return {
                "trade_date": "2026-06-20",
                "scope": "all_a_share",
                "scanned_count": 5128,
                "prefiltered_count": 1200,
                "returned_count": 2,
                "selection_method": "全市场行情分页扫描后预筛候选",
                "items": [
                    {
                        "code": "300001",
                        "name": "测试一",
                        "sector": "机器人",
                        "bars": [
                            {
                                "date": "2026-06-19",
                                "open": 10,
                                "high": 11,
                                "low": 9,
                                "close": 10,
                                "volume": 1000,
                            },
                            {
                                "date": "2026-06-20",
                                "open": 10,
                                "high": 12,
                                "low": 10,
                                "close": 12,
                                "volume": 2000,
                            },
                        ],
                    }
                ],
            }
        raise AssertionError(operation)

    summary = module.refresh_snapshot(
        output,
        python_executable="python3.11",
        candidate_limit=2,
        bar_count=2,
        timeout=8,
        runner=fake_runner,
    )

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["source"] == "tdx-mcp-eltdx-bridge"
    assert data["candidate_universe"]["scanned_count"] == 5128
    assert data["candidate_universe"]["returned_count"] == 2
    assert data["stocks"]["600519"]["name"] == "贵州茅台"
    assert summary["scanned_count"] == 5128
    assert summary["candidate_count"] == 1


def test_bridge_process_timeout_allows_full_market_scan() -> None:
    module = _load_refresh_module()

    assert module.bridge_process_timeout(30) >= 120


def test_refresh_tdx_snapshot_enriches_existing_candidate_snapshot(tmp_path: Path) -> None:
    module = _load_refresh_module()
    output = tmp_path / "tdx.json"
    output.write_text(
        json.dumps(
            {
                "source": "tdx-mcp-eltdx-bridge",
                "candidate_universe": {
                    "scope": "all_a_share",
                    "scanned_count": 5532,
                    "returned_count": 2,
                    "selection_method": "全市场行情分页扫描后预筛候选",
                    "items": [
                        {
                            "code": "300001",
                            "name": "测试一",
                            "sector": "未识别主题",
                            "bars": [
                                {
                                    "date": "2026-06-20-pre",
                                    "open": 10,
                                    "high": 10,
                                    "low": 10,
                                    "close": 10,
                                    "volume": 0,
                                },
                                {
                                    "date": "2026-06-20",
                                    "open": 10,
                                    "high": 12,
                                    "low": 10,
                                    "close": 12,
                                    "volume": 2000,
                                },
                            ],
                            "price_reliable": True,
                        },
                        {
                            "code": "300002",
                            "name": "测试二",
                            "sector": "未识别主题",
                            "bars": [
                                {
                                    "date": "2026-06-20-pre",
                                    "open": 20,
                                    "high": 20,
                                    "low": 20,
                                    "close": 20,
                                    "volume": 0,
                                },
                                {
                                    "date": "2026-06-20",
                                    "open": 20,
                                    "high": 21,
                                    "low": 19,
                                    "close": 21,
                                    "volume": 3000,
                                },
                            ],
                            "price_reliable": True,
                        },
                    ],
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    calls: list[tuple[str, dict[str, object]]] = []

    def fake_runner(operation: str, payload: dict[str, object], python_executable: str):
        calls.append((operation, payload))
        assert operation == "candidate_enrichment"
        assert payload["bar_count"] == 20
        items = payload["items"]
        assert isinstance(items, list)
        assert [item["code"] for item in items] == ["300001"]
        return {
            "items": [
                {
                    "code": "300001",
                    "name": "测试一",
                    "sector": "机器人",
                    "bar_source": "tdx_daily",
                    "price_reliable": True,
                    "bars": [
                        {
                            "date": "2026-06-19",
                            "open": 9,
                            "high": 10,
                            "low": 8.8,
                            "close": 9.5,
                            "volume": 1000,
                        },
                        {
                            "date": "2026-06-20",
                            "open": 10,
                            "high": 12,
                            "low": 10,
                            "close": 12,
                            "volume": 2000,
                        },
                    ],
                }
            ]
        }

    summary = module.enrich_existing_snapshot(
        output,
        python_executable="python3.11",
        enrich_limit=1,
        enrich_start=0,
        bar_count=20,
        timeout=8,
        runner=fake_runner,
    )

    data = json.loads(output.read_text(encoding="utf-8"))
    universe = data["candidate_universe"]
    assert calls and calls[0][0] == "candidate_enrichment"
    assert universe["items"][0]["sector"] == "机器人"
    assert universe["items"][0]["bar_source"] == "tdx_daily"
    assert universe["items"][1]["sector"] == "未识别主题"
    assert universe["returned_count"] == 2
    assert universe["enriched_count"] == 1
    assert universe["enrichment_status"] == "partial"
    assert "真实日线" in universe["enrichment_method"]
    assert summary["enriched_count"] == 1
