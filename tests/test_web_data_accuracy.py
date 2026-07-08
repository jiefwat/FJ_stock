import json
from pathlib import Path

from stock_ts.providers.tdx_snapshot_provider import TdxSnapshotProvider
from stock_ts.web import _safe_fetch_announcements, render_page


def test_web_default_does_not_block_on_live_announcement_fetch(monkeypatch) -> None:
    called = False

    def fake_live_fetcher(*_args, **_kwargs):
        nonlocal called
        called = True
        raise AssertionError("live announcement fetcher should not be called by default")

    monkeypatch.delenv("STOCK_TS_WEB_LIVE_ANNOUNCEMENTS", raising=False)
    monkeypatch.setattr("stock_ts.web.fetch_cninfo_announcements", fake_live_fetcher)

    assert _safe_fetch_announcements("002487", announcement_fetcher=None) is None
    assert called is False


def test_web_uses_injected_announcement_fetcher_even_when_live_fetch_is_off() -> None:
    report = object()

    assert (
        _safe_fetch_announcements(
            "002487",
            announcement_fetcher=lambda query, limit=5: report,
        )
        is report
    )


def test_web_pauses_candidate_ranking_when_tdx_snapshot_uses_synthetic_bars(
    tmp_path: Path,
) -> None:
    holdings = tmp_path / "holdings.csv"
    holdings.write_text(
        "code,name,shares,cost_price,sector,note\n600519,贵州茅台,10,1500,白酒,核心\n",
        encoding="utf-8",
    )
    snapshot = tmp_path / "tdx.json"
    bar = {
        "date": "2026-06-18",
        "open": 1500,
        "high": 1515,
        "low": 1490,
        "close": 1510,
        "volume": 10000,
    }
    snapshot.write_text(
        json.dumps(
            {
                "market": {
                    "trade_date": "2026-06-18",
                    "indices": [
                        {
                            "code": "000001",
                            "name": "上证指数",
                            "close": 4090.48,
                            "pct_chg": -0.43,
                            "amount": 5123.4,
                        }
                    ],
                    "advancing": 2023,
                    "declining": 3407,
                    "limit_up": 134,
                    "limit_down": 35,
                    "top_sectors": [["白酒", 1.2]],
                },
                "sectors": [
                    {
                        "name": "白酒",
                        "pct_chg": 1.2,
                        "advancing_ratio": 0.7,
                        "amount_change": 10.0,
                    }
                ],
                "stocks": {
                    "600519": {
                        "name": "贵州茅台",
                        "bars": [bar | {"date": "2026-06-17"}, bar],
                    }
                },
                "candidate_universe": {
                    "items": [
                        {
                            "code": "600519",
                            "name": "贵州茅台",
                            "sector": "白酒",
                            "bars": [
                                bar | {"date": "latest-1", "close": 1500},
                                bar | {"date": "latest-0", "close": 1510},
                            ],
                        }
                    ]
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    html = render_page(
        stock_code="600519",
        provider_name="tdx-snapshot",
        provider=TdxSnapshotProvider(snapshot),
        holdings_path=str(holdings),
    )

    assert "涨停 / 跌停" in html
    assert "134 / 35" in html
    assert "候选池缺少真实日线，已暂停排序、评分和涨跌幅展示" in html
    assert "数据闸门" in html
    assert "候选价格" in html
    assert "排序暂停" in html
    assert "候选</span><strong>排序暂停</strong>" in html
    assert "最强上涨" not in html
    assert "最弱下跌" not in html


def test_web_quality_gate_marks_candidate_prices_available_when_dates_are_real(
    tmp_path: Path,
) -> None:
    holdings = tmp_path / "holdings.csv"
    holdings.write_text(
        "code,name,shares,cost_price,sector,note\n600519,贵州茅台,10,1500,白酒,核心\n",
        encoding="utf-8",
    )
    snapshot = tmp_path / "tdx.json"
    bar = {
        "date": "2026-06-18",
        "open": 1500,
        "high": 1515,
        "low": 1490,
        "close": 1510,
        "volume": 10000,
    }
    snapshot.write_text(
        json.dumps(
            {
                "market": {
                    "trade_date": "2026-06-18",
                    "indices": [
                        {
                            "code": "000001",
                            "name": "上证指数",
                            "close": 4090.48,
                            "pct_chg": -0.43,
                            "amount": 5123.4,
                        }
                    ],
                    "advancing": 2023,
                    "declining": 3407,
                    "limit_up": 134,
                    "limit_down": 35,
                    "top_sectors": [["白酒", 1.2]],
                },
                "sectors": [
                    {
                        "name": "白酒",
                        "pct_chg": 1.2,
                        "advancing_ratio": 0.7,
                        "amount_change": 10.0,
                    }
                ],
                "stocks": {
                    "600519": {
                        "name": "贵州茅台",
                        "bars": [bar | {"date": "2026-06-17"}, bar],
                    }
                },
                "candidate_universe": {
                    "items": [
                        {
                            "code": "600519",
                            "name": "贵州茅台",
                            "sector": "白酒",
                            "bars": [
                                bar | {"date": "2026-06-17", "close": 1500},
                                bar,
                            ],
                        }
                    ]
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    html = render_page(
        stock_code="600519",
        provider_name="tdx-snapshot",
        provider=TdxSnapshotProvider(snapshot),
        holdings_path=str(holdings),
    )

    assert "数据闸门" in html
    assert "候选价格</span><strong>可用</strong>" in html
    assert "候选</span><strong>1 只</strong>" in html
    assert "排序暂停" not in html


def test_web_quality_gate_warns_when_market_snapshot_is_older_than_stock_kline(
    tmp_path: Path,
) -> None:
    holdings = tmp_path / "holdings.csv"
    holdings.write_text(
        "code,name,shares,cost_price,sector,note\n600519,贵州茅台,10,1500,白酒,核心\n",
        encoding="utf-8",
    )
    snapshot = tmp_path / "tdx.json"
    old_bar = {
        "date": "2026-06-25",
        "open": 1500,
        "high": 1515,
        "low": 1490,
        "close": 1510,
        "volume": 10000,
    }
    latest_bar = old_bar | {"date": "2026-06-26", "close": 1520}
    snapshot.write_text(
        json.dumps(
            {
                "market": {
                    "trade_date": "2026-06-23",
                    "indices": [
                        {
                            "code": "000001",
                            "name": "上证指数",
                            "close": 4090.48,
                            "pct_chg": -0.43,
                            "amount": 5123.4,
                        }
                    ],
                    "advancing": 2023,
                    "declining": 3407,
                    "limit_up": 134,
                    "limit_down": 35,
                    "top_sectors": [["白酒", 1.2]],
                },
                "sectors": [
                    {
                        "name": "白酒",
                        "pct_chg": 1.2,
                        "advancing_ratio": 0.7,
                        "amount_change": 10.0,
                    }
                ],
                "stocks": {
                    "600519": {
                        "name": "贵州茅台",
                        "bars": [old_bar, latest_bar],
                    }
                },
                "candidate_universe": {
                    "items": [
                        {
                            "code": "600519",
                            "name": "贵州茅台",
                            "sector": "白酒",
                            "bars": [old_bar, latest_bar],
                        }
                    ]
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    html = render_page(
        stock_code="600519",
        provider_name="tdx-snapshot",
        provider=TdxSnapshotProvider(snapshot),
        holdings_path=str(holdings),
    )

    assert "大盘日期需刷新：大盘 2026-06-23，个股 2026-06-26。" in html
    assert "需要人工确认" in html


def test_web_opens_candidate_stock_when_tdx_stock_detail_is_missing(
    tmp_path: Path,
) -> None:
    holdings = tmp_path / "holdings.csv"
    holdings.write_text(
        "code,name,shares,cost_price,sector,note\n600519,贵州茅台,10,1500,白酒,核心\n",
        encoding="utf-8",
    )
    snapshot = tmp_path / "tdx.json"
    base_bar = {
        "date": "2026-06-18",
        "open": 1500,
        "high": 1515,
        "low": 1490,
        "close": 1510,
        "volume": 10000,
    }
    candidate_bars = [
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
    ]
    snapshot.write_text(
        json.dumps(
            {
                "market": {
                    "trade_date": "2026-06-18",
                    "indices": [
                        {
                            "code": "000001",
                            "name": "上证指数",
                            "close": 4090.48,
                            "pct_chg": -0.43,
                            "amount": 5123.4,
                        }
                    ],
                    "advancing": 2023,
                    "declining": 3407,
                    "limit_up": 134,
                    "limit_down": 35,
                    "top_sectors": [["深市主板", 1.2]],
                },
                "sectors": [
                    {
                        "name": "深市主板",
                        "pct_chg": 1.2,
                        "advancing_ratio": 0.7,
                        "amount_change": 10.0,
                    }
                ],
                "stocks": {
                    "600519": {
                        "name": "贵州茅台",
                        "bars": [base_bar | {"date": "2026-06-17"}, base_bar],
                    }
                },
                "candidate_universe": {
                    "items": [
                        {
                            "code": "002674",
                            "name": "兴业科技",
                            "sector": "深市主板",
                            "bars": candidate_bars,
                            "fund_flow": 1.2,
                            "pe_ttm": 18.6,
                        }
                    ]
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    html = render_page(
        stock_code="002674",
        provider_name="tdx-snapshot",
        provider=TdxSnapshotProvider(snapshot),
        holdings_path=str(holdings),
    )

    assert "系统暂时无法生成复盘" not in html
    assert "兴业科技" in html
    assert "个股分析" in html
    assert "6 维判断" in html
