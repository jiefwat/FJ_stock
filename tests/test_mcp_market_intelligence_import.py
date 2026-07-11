from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_import_module():
    spec = importlib.util.spec_from_file_location(
        "import_mcp_market_intelligence", Path("scripts/import_mcp_market_intelligence.py")
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_import_mcp_market_intelligence_converts_longbridge_outputs(tmp_path: Path) -> None:
    module = _load_import_module()
    snapshot = tmp_path / "tdx.json"
    snapshot.write_text(json.dumps({"source": "tdx-mcp", "market_news": []}), encoding="utf-8")
    raw = tmp_path / "longbridge.json"
    raw.write_text(
        json.dumps(
            [
                {
                    "type": "text",
                    "text": json.dumps(
                        [
                            {
                                "title": "A-shares staged a V-shaped reversal, STAR 50 surged",
                                "description": (
                                    "Semiconductor sector exploded; turnover increased "
                                    "and incremental funds entered the market."
                                ),
                                "url": "https://longbridge.com/news/1",
                                "published_at": "2026-07-09T12:00:02Z",
                            },
                            {"title": "", "description": "blank titles must be skipped"},
                        ]
                    ),
                },
                {
                    "events": [
                        {
                            "stock": {
                                "symbol": "981.HK",
                                "name": "中芯国际",
                                "market": "HK",
                                "change": "-0.0562",
                                "labels": ["半导体厂商"],
                            },
                            "timestamp": "2026-07-10T07:47:14Z",
                            "alert_reason": "波动超 20 日均值",
                        }
                    ],
                    "updated_at": "2026-07-10T19:49:59Z",
                },
                {
                    "temperature": 70,
                    "description": "Temp Warm & Gradually Rising",
                    "valuation": 86,
                    "sentiment": 54,
                    "timestamp": "2026-07-10T13:20:05Z",
                    "market": "CN",
                },
                {
                    "list": [
                        {
                            "date": "2026-07-14",
                            "infos": [
                                {
                                    "market": "CN",
                                    "content": "中国 (大陆), GDP",
                                    "datetime": "2026-07-15T02:00:00Z",
                                    "star": 3,
                                    "data_kv": [
                                        {"key": "前值", "value": "5"},
                                        {"key": "预测", "value": "--"},
                                    ],
                                }
                            ],
                        }
                    ]
                },
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    summary = module.import_market_intelligence(
        snapshot,
        [raw],
        source="longbridge.mcp",
        fetched_at="2026-07-11T01:00:00Z",
        limit=10,
    )

    data = json.loads(snapshot.read_text(encoding="utf-8"))
    titles = [item["title"] for item in data["market_news"]]
    assert "A-shares staged a V-shaped reversal, STAR 50 surged" in titles
    assert "中芯国际异动：波动超 20 日均值" in titles
    assert "Longbridge CN市场温度 70：Temp Warm & Gradually Rising" in titles
    assert "宏观日历：中国 (大陆), GDP" in titles
    assert all(item.get("fetched_at") == "2026-07-11T01:00:00Z" for item in data["market_news"])
    smic_event = next(
        item for item in data["market_news"] if item["title"].startswith("中芯国际")
    )
    assert smic_event["symbols"] == ["981.HK"]
    assert data["mcp_market_news_refresh"]["source"] == "longbridge.mcp"
    assert data["mcp_market_news_refresh"]["imported_count"] == 4
    assert summary["imported_count"] == 4


def test_import_mcp_market_intelligence_dedupes_against_existing_snapshot(tmp_path: Path) -> None:
    module = _load_import_module()
    snapshot = tmp_path / "tdx.json"
    snapshot.write_text(
        json.dumps(
            {
                "market_news": [
                    {
                        "date": "2026-07-09",
                        "source": "old",
                        "title": "A股半导体板块走强",
                        "url": "https://longbridge.com/news/2",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    raw = tmp_path / "news.json"
    raw.write_text(
        json.dumps(
            [
                {
                    "title": "A股半导体板块走强",
                    "description": "重复 URL 不应再导入",
                    "url": "https://longbridge.com/news/2",
                    "published_at": "2026-07-10T01:00:00Z",
                },
                {
                    "title": "机器人订单增长",
                    "description": "A股机器人概念活跃",
                    "url": "https://longbridge.com/news/3",
                    "published_at": "2026-07-10T02:00:00Z",
                },
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    summary = module.import_market_intelligence(
        snapshot,
        [raw],
        source="longbridge.mcp",
        fetched_at="2026-07-11T01:00:00Z",
    )

    data = json.loads(snapshot.read_text(encoding="utf-8"))
    assert [item["title"] for item in data["market_news"]].count("A股半导体板块走强") == 1
    assert any(item["title"] == "机器人订单增长" for item in data["market_news"])
    assert summary["imported_count"] == 1
    assert data["mcp_market_news_refresh"]["skipped_count"] == 1
