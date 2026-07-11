import json
from pathlib import Path

import pytest

from stock_ts.data_sources import build_data_source_matrix
from stock_ts.providers.base import DataProviderError
from stock_ts.providers.tdx_snapshot_provider import TdxSnapshotProvider

EXCHANGE_BOARD_THEME_LABELS = {
    "sse_star_market",
    "szse_chinext",
    "sse_main_board",
    "szse_main_board",
    "bse_listed_stock",
    "科创板",
    "创业板",
    "沪市主板",
    "深市主板",
    "主板",
    "北交所",
    "沪深A股",
    "近期强势",
    "近期弱势",
    "最近情绪指数",
    "昨日上榜",
    "昨日首板",
    "昨日涨停",
    "通达信88",
    "密集调研",
    "拟减持",
    "含可转债",
    "次新股",
}


def test_data_source_matrix_mentions_skills_and_mcp() -> None:
    matrix = build_data_source_matrix(
        active_provider="tdx-snapshot",
        provider_class="TdxSnapshotProvider",
        has_tdx_snapshot=True,
    )

    names = {item.name for item in matrix}
    assert {
        "Tencent 行情",
        "eltdx MCP / 桥接",
        "Tushare Pro",
        "iTick",
        "AKShare",
        "TDX MCP 快照",
        "Longbridge MCP",
        "CNInfo skill",
        "AgentReach skill",
    } <= names
    assert next(item for item in matrix if item.name == "TDX MCP 快照").status == "active"
    assert "市场新闻" in next(item for item in matrix if item.name == "Longbridge MCP").coverage


def test_tdx_snapshot_provider_exposes_mcp_market_news_refresh_metadata(tmp_path: Path) -> None:
    snapshot = tmp_path / "tdx.json"
    snapshot.write_text(
        json.dumps(
            {
                "mcp_market_news_refresh": {
                    "source": "longbridge.mcp",
                    "generated_at": "2026-07-11T01:00:00Z",
                    "imported_count": 4,
                    "skipped_count": 1,
                    "total_market_news_count": 12,
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    metadata = TdxSnapshotProvider(snapshot).fetch_candidate_universe_metadata()

    assert metadata["mcp_market_news_refresh_source"] == "longbridge.mcp"
    assert metadata["mcp_market_news_refresh_generated_at"] == "2026-07-11T01:00:00Z"
    assert metadata["mcp_market_news_refresh_imported_count"] == "4"
    assert metadata["mcp_market_news_refresh_total_market_news_count"] == "12"


def test_tdx_snapshot_provider_reads_local_mcp_export(tmp_path: Path) -> None:
    snapshot = tmp_path / "tdx.json"
    snapshot.write_text(
        json.dumps(
            {
                "stocks": {
                    "603278": {
                        "name": "大业股份",
                        "bars": [
                            {
                                "date": "2026-06-11",
                                "open": 12.50,
                                "high": 12.77,
                                "low": 11.90,
                                "close": 12.06,
                                "volume": 407561,
                            },
                            {
                                "date": "2026-06-12",
                                "open": 12.18,
                                "high": 12.36,
                                "low": 11.62,
                                "close": 11.83,
                                "volume": 349275,
                            },
                        ],
                        "fund_flow": -0.43,
                        "pe_ttm": 42.0,
                    }
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    stock = TdxSnapshotProvider(snapshot).fetch_stock("603278")

    assert stock.name == "大业股份"
    assert stock.bars[-1].date == "2026-06-12"
    assert stock.bars[-1].close == 11.83
    assert stock.fund_flow == -0.43


def test_bundled_tdx_snapshot_uses_thematic_sector_labels() -> None:
    provider = TdxSnapshotProvider("data/imports/tdx_snapshots.json")

    market_theme_names = {name for name, _ in provider.fetch_market().top_sectors}
    sector_theme_names = {sector.name for sector in provider.fetch_sectors()}
    candidate_theme_names = {candidate.sector for candidate in provider.fetch_candidate_universe()}
    all_theme_names = market_theme_names | sector_theme_names | candidate_theme_names

    assert all_theme_names.isdisjoint(EXCHANGE_BOARD_THEME_LABELS)
    assert {"AI营销", "机器人概念", "芯片"} & all_theme_names


def test_tdx_snapshot_provider_uses_candidate_bars_when_stock_detail_missing(
    tmp_path: Path,
) -> None:
    snapshot = tmp_path / "tdx.json"
    snapshot.write_text(
        json.dumps(
            {
                "stocks": {},
                "candidate_universe": {
                    "scope": "all_a_share",
                    "scanned_count": 5100,
                    "returned_count": 1,
                    "bar_source": "tdx_quote_preclose",
                    "enriched_count": 1,
                    "enrichment_status": "partial",
                    "enrichment_method": "前排候选已补真实日线和主题",
                    "enriched_at": "2026-06-20T13:00:00+00:00",
                    "selection_method": "全市场行情分页扫描后预筛候选",
                    "items": [
                        {
                            "code": "002674",
                            "name": "兴业科技",
                            "sector": "深市主板",
                            "bars": [
                                {
                                    "date": "2026-06-17",
                                    "open": 9.8,
                                    "high": 10.1,
                                    "low": 9.7,
                                    "close": 10.0,
                                    "volume": 300000,
                                },
                                {
                                    "date": "2026-06-18",
                                    "open": 10.2,
                                    "high": 11.0,
                                    "low": 10.1,
                                    "close": 10.8,
                                    "volume": 520000,
                                },
                            ],
                            "fund_flow": 1.2,
                            "pe_ttm": 18.6,
                        }
                    ],
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    stock = TdxSnapshotProvider(snapshot).fetch_stock("002674")

    assert stock.name == "兴业科技"
    assert stock.bars[-1].date == "2026-06-18"
    assert stock.bars[-1].close == 10.8
    assert stock.fund_flow == 1.2
    assert stock.pe_ttm == 18.6


def test_tdx_snapshot_provider_reads_market_sectors_and_candidates(tmp_path: Path) -> None:
    snapshot = tmp_path / "tdx.json"
    snapshot.write_text(
        json.dumps(
            {
                "market": {
                    "trade_date": "2026-06-18",
                    "indices": [
                        {
                            "code": "000001",
                            "name": "上证指数",
                            "close": 3280.12,
                            "pct_chg": 0.62,
                            "amount": 5123.4,
                        }
                    ],
                    "advancing": 3210,
                    "declining": 1450,
                    "limit_up": 63,
                    "limit_down": 7,
                    "top_sectors": [["机器人", 2.8], ["算力", 1.9]],
                    "northbound_net_inflow": 12.5,
                },
                "sectors": [
                    {
                        "name": "机器人",
                        "pct_chg": 2.8,
                        "advancing_ratio": 0.72,
                        "amount_change": 16.4,
                        "fund_flow": 8.2,
                        "consecutive_days": 2,
                        "limit_up_count": 9,
                        "high_divergence": False,
                    }
                ],
                "candidate_universe": {
                    "scope": "all_a_share",
                    "scanned_count": 5100,
                    "returned_count": 1,
                    "bar_source": "tdx_quote_preclose",
                    "enriched_count": 1,
                    "enrichment_status": "partial",
                    "enrichment_method": "前排候选已补真实日线和主题",
                    "enriched_at": "2026-06-20T13:00:00+00:00",
                    "selection_method": "全市场行情分页扫描后预筛候选",
                    "items": [
                        {
                            "code": "603278",
                            "name": "大业股份",
                            "sector": "机器人",
                            "bars": [
                                {
                                    "date": "2026-06-17",
                                    "open": 11.9,
                                    "high": 12.2,
                                    "low": 11.8,
                                    "close": 12.0,
                                    "volume": 480000,
                                },
                                {
                                    "date": "2026-06-18",
                                    "open": 12.1,
                                    "high": 12.9,
                                    "low": 12.0,
                                    "close": 12.8,
                                    "volume": 510000,
                                },
                            ],
                            "turnover_rate": 7.2,
                            "amount": 4.6,
                        }
                    ],
                },
                "stocks": {
                    "603278": {
                        "name": "大业股份",
                        "bars": [
                            {
                                "date": "2026-06-18",
                                "open": 12.1,
                                "high": 12.9,
                                "low": 12.0,
                                "close": 12.8,
                                "volume": 510000,
                            }
                        ],
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    provider = TdxSnapshotProvider(snapshot)

    market = provider.fetch_market()
    sectors = provider.fetch_sectors()
    candidates = provider.fetch_candidate_universe()
    metadata = provider.fetch_candidate_universe_metadata()

    assert market.trade_date == "2026-06-18"
    assert market.limit_up == 63
    assert market.limit_down == 7
    assert market.indices[0].name == "上证指数"
    assert sectors[0].name == "机器人"
    assert sectors[0].limit_up_count == 9
    assert candidates[0].code == "603278"
    assert candidates[0].sector == "机器人"
    assert candidates[0].price_reliable is True
    assert metadata["scope"] == "all_a_share"
    assert metadata["scanned_count"] == "5100"
    assert metadata["returned_count"] == "1"
    assert metadata["bar_source"] == "tdx_quote_preclose"
    assert metadata["enriched_count"] == "1"
    assert metadata["enrichment_status"] == "partial"
    assert metadata["enriched_at"] == "2026-06-20T13:00:00+00:00"
    assert "全市场" in metadata["selection_method"]


def test_tdx_snapshot_provider_derives_unchanged_count_from_scan_total(
    tmp_path: Path,
) -> None:
    snapshot = tmp_path / "tdx.json"
    snapshot.write_text(
        json.dumps(
            {
                "market": {
                    "trade_date": "2026-06-26",
                    "indices": [],
                    "advancing": 3000,
                    "declining": 2000,
                    "limit_up": 50,
                    "limit_down": 10,
                    "top_sectors": [],
                },
                "candidate_universe": {
                    "scanned_count": 5534,
                    "items": [],
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    market = TdxSnapshotProvider(snapshot).fetch_market()

    assert market.unchanged == 534


def test_tdx_snapshot_provider_prefers_explicit_unchanged_count(
    tmp_path: Path,
) -> None:
    snapshot = tmp_path / "tdx.json"
    snapshot.write_text(
        json.dumps(
            {
                "market": {
                    "trade_date": "2026-06-26",
                    "indices": [],
                    "advancing": 3000,
                    "declining": 2000,
                    "unchanged": 321,
                    "limit_up": 50,
                    "limit_down": 10,
                    "top_sectors": [],
                },
                "candidate_universe": {
                    "scanned_count": 5534,
                    "items": [],
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    market = TdxSnapshotProvider(snapshot).fetch_market()

    assert market.unchanged == 321


def test_tdx_snapshot_provider_reuses_payload_within_instance(
    tmp_path: Path,
    monkeypatch,
) -> None:
    snapshot = tmp_path / "tdx.json"
    snapshot.write_text(
        json.dumps(
            {
                "market": {
                    "trade_date": "2026-06-26",
                    "indices": [],
                    "advancing": 1,
                    "declining": 1,
                    "limit_up": 0,
                    "limit_down": 0,
                    "top_sectors": [],
                },
                "candidate_universe": {"items": []},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    original_read_text = Path.read_text
    calls = 0

    def counting_read_text(self: Path, *args, **kwargs):
        nonlocal calls
        if self == snapshot:
            calls += 1
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", counting_read_text)
    provider = TdxSnapshotProvider(snapshot)

    provider.fetch_market()
    provider.fetch_market()

    assert calls == 1


def test_tdx_snapshot_provider_does_not_expose_exchange_boards_as_themes(
    tmp_path: Path,
) -> None:
    snapshot = tmp_path / "tdx.json"
    snapshot.write_text(
        json.dumps(
            {
                "market": {
                    "trade_date": "2026-06-18",
                    "indices": [],
                    "advancing": 1,
                    "declining": 1,
                    "limit_up": 0,
                    "limit_down": 0,
                    "top_sectors": [["sse_star_market", 1.6], ["szse_chinext", -0.1]],
                },
                "sectors": [
                    {
                        "name": "sse_star_market",
                        "pct_chg": 1.6,
                        "advancing_ratio": 0.7,
                        "amount_change": 2.0,
                    }
                ],
                "candidate_universe": {
                    "items": [
                        {
                            "code": "688001",
                            "name": "华兴源创",
                            "sector": "sse_star_market",
                            "bars": [
                                {
                                    "date": "2026-06-17",
                                    "open": 10,
                                    "high": 11,
                                    "low": 9,
                                    "close": 10,
                                },
                                {
                                    "date": "2026-06-18",
                                    "open": 10,
                                    "high": 12,
                                    "low": 10,
                                    "close": 11,
                                },
                            ],
                        }
                    ]
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    provider = TdxSnapshotProvider(snapshot)

    assert provider.fetch_market().top_sectors[0][0] == "未识别主题"
    assert provider.fetch_sectors()[0].name == "未识别主题"
    assert provider.fetch_candidate_universe()[0].sector == "未识别主题"


def test_tdx_snapshot_provider_filters_non_theme_labels(tmp_path: Path) -> None:
    snapshot = tmp_path / "tdx.json"
    snapshot.write_text(
        json.dumps(
            {
                "candidate_universe": {
                    "items": [
                        {
                            "code": "300001",
                            "name": "测试股",
                            "sector": "通达信88",
                            "bars": [
                                {
                                    "date": "2026-06-17",
                                    "open": 10,
                                    "high": 11,
                                    "low": 9,
                                    "close": 10,
                                },
                                {
                                    "date": "2026-06-18",
                                    "open": 10,
                                    "high": 12,
                                    "low": 10,
                                    "close": 11,
                                },
                            ],
                        }
                    ]
                },
                "sectors": [
                    {
                        "name": "含可转债",
                        "pct_chg": 1.0,
                        "advancing_ratio": 0.6,
                        "amount_change": 2.0,
                    }
                ],
                "market": {
                    "trade_date": "2026-06-18",
                    "indices": [],
                    "advancing": 1,
                    "declining": 1,
                    "limit_up": 0,
                    "limit_down": 0,
                    "top_sectors": [["次新股", 1.0]],
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    provider = TdxSnapshotProvider(snapshot)

    assert provider.fetch_candidate_universe()[0].sector == "未识别主题"
    assert provider.fetch_sectors()[0].name == "未识别主题"
    assert provider.fetch_market().top_sectors[0][0] == "未识别主题"


def test_tdx_snapshot_provider_marks_synthetic_candidate_bars_unreliable(
    tmp_path: Path,
) -> None:
    snapshot = tmp_path / "tdx.json"
    snapshot.write_text(
        json.dumps(
            {
                "candidate_universe": {
                    "items": [
                        {
                            "code": "603278",
                            "name": "大业股份",
                            "sector": "机器人",
                            "bars": [
                                {
                                    "date": "latest-1",
                                    "open": 11.9,
                                    "high": 12.1,
                                    "low": 11.8,
                                    "close": 12.0,
                                    "volume": 1000,
                                },
                                {
                                    "date": "latest-0",
                                    "open": 12.1,
                                    "high": 12.9,
                                    "low": 12.0,
                                    "close": 12.8,
                                    "volume": 1100,
                                },
                            ],
                        }
                    ]
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    candidates = TdxSnapshotProvider(snapshot).fetch_candidate_universe()

    assert candidates[0].price_reliable is False


def test_tdx_snapshot_provider_does_not_fallback_to_sample_market(tmp_path: Path) -> None:
    snapshot = tmp_path / "tdx.json"
    snapshot.write_text(json.dumps({"stocks": {}}, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(DataProviderError, match="missing market"):
        TdxSnapshotProvider(snapshot).fetch_market()


def test_tdx_snapshot_provider_computes_limit_down_details_from_bars(
    tmp_path: Path,
) -> None:
    def bars(previous: float, latest: float) -> list[dict]:
        return [
            {
                "date": "2026-06-25",
                "open": previous,
                "high": previous,
                "low": previous,
                "close": previous,
                "volume": 1000,
            },
            {
                "date": "2026-06-26",
                "open": latest,
                "high": latest,
                "low": latest,
                "close": latest,
                "volume": 1000,
            },
        ]

    snapshot = tmp_path / "tdx.json"
    snapshot.write_text(
        json.dumps(
            {
                "market": {
                    "trade_date": "2026-06-26",
                    "indices": [],
                    "advancing": 10,
                    "declining": 90,
                    "limit_up": 1,
                    "limit_down": 0,
                    "top_sectors": [],
                },
                "candidate_universe": {
                    "items": [
                        {
                            "code": "600001",
                            "name": "十厘米跌停",
                            "sector": "地产链",
                            "bars": bars(10.0, 9.0),
                        },
                        {
                            "code": "300002",
                            "name": "二十厘米跌停",
                            "sector": "机器人",
                            "bars": bars(10.0, 8.0),
                        },
                        {
                            "code": "600003",
                            "name": "普通下跌",
                            "sector": "白酒",
                            "bars": bars(10.0, 9.2),
                        },
                    ]
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    market = TdxSnapshotProvider(snapshot).fetch_market()

    assert market.limit_down == 2
    assert [item.code for item in market.limit_down_details] == ["300002", "600001"]
    assert market.limit_down_details[0].pct_chg == -20.0
    assert market.limit_down_details[0].reason == "20cm 跌停或极端下跌"
    assert market.limit_down_details[1].reason == "10cm 跌停或大幅下跌"


def test_tdx_snapshot_provider_does_not_count_zero_close_as_limit_down(
    tmp_path: Path,
) -> None:
    snapshot = tmp_path / "tdx.json"
    snapshot.write_text(
        json.dumps(
            {
                "market": {
                    "trade_date": "2026-06-26",
                    "indices": [],
                    "advancing": 10,
                    "declining": 90,
                    "limit_up": 1,
                    "limit_down": 0,
                    "top_sectors": [],
                },
                "candidate_universe": {
                    "items": [
                        {
                            "code": "600000",
                            "name": "停牌无价",
                            "sector": "银行",
                            "bars": [
                                {
                                    "date": "2026-06-25",
                                    "open": 10,
                                    "high": 10,
                                    "low": 10,
                                    "close": 10,
                                    "volume": 1000,
                                },
                                {
                                    "date": "2026-06-26",
                                    "open": 0,
                                    "high": 0,
                                    "low": 0,
                                    "close": 0,
                                    "volume": 0,
                                },
                            ],
                        }
                    ]
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    market = TdxSnapshotProvider(snapshot).fetch_market()

    assert market.limit_down == 0
    assert market.limit_down_details == []


def test_tdx_snapshot_provider_filters_zero_price_explicit_limit_down_details(
    tmp_path: Path,
) -> None:
    snapshot = tmp_path / "tdx.json"
    snapshot.write_text(
        json.dumps(
            {
                "market": {
                    "trade_date": "2026-06-26",
                    "indices": [],
                    "advancing": 10,
                    "declining": 90,
                    "limit_up": 1,
                    "limit_down": 88,
                    "top_sectors": [],
                    "limit_down_details": [
                        {
                            "code": "600000",
                            "name": "停牌无价",
                            "sector": "银行",
                            "latest_close": 0,
                            "pct_chg": -100,
                            "reason": "坏行情",
                        },
                        {
                            "code": "600001",
                            "name": "真实跌停",
                            "sector": "银行",
                            "latest_close": 9,
                            "pct_chg": -10,
                            "reason": "10cm 跌停",
                        },
                    ],
                },
                "candidate_universe": {"items": []},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    market = TdxSnapshotProvider(snapshot).fetch_market()

    assert market.limit_down == 1
    assert [item.code for item in market.limit_down_details] == ["600001"]
