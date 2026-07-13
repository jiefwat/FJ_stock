import inspect
import json
from pathlib import Path
from typing import get_type_hints

from stock_ts.providers.tdx_snapshot_provider import TdxSnapshotProvider
from stock_ts.research.evidence import EvidenceStatus
from stock_ts.web import (
    DataQualityView,
    _assess_data_quality,
    _safe_fetch_announcements,
    render_page,
)


def test_data_quality_exposes_typed_research_quote_status() -> None:
    assert get_type_hints(DataQualityView)["quote_status"] is EvidenceStatus
    source = inspect.getsource(_assess_data_quality)
    assert "quote_freshness_warnings" in source
    assert "quote_status=" in source


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

    assert "股票涨跌统计" in html
    assert "涨停" in html
    assert "跌停" in html
    assert "推荐股票" in html
    assert "待补数据" in html or "价格可靠" in html
    assert "最强上涨" not in html
    assert "最弱下跌" not in html


def test_web_quality_gate_marks_candidate_prices_available_when_dates_are_real(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("STOCK_TS_NOW", "2026-06-19T10:00:00+08:00")
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

    assert "推荐股票" in html
    assert "价格链路可靠" in html
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

    assert "数据状态" in html
    assert "热点机会" in html


def test_web_blocks_opportunity_ranking_when_snapshot_trade_date_is_stale(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("STOCK_TS_NOW", "2026-07-11T09:30:00+08:00")
    holdings = tmp_path / "holdings.csv"
    holdings.write_text(
        "code,name,shares,cost_price,sector,note\n600519,贵州茅台,10,1500,白酒,核心\n",
        encoding="utf-8",
    )
    snapshot = tmp_path / "tdx.json"
    old_bar = {
        "date": "2026-07-08",
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
                    "trade_date": "2026-07-08",
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
                        "bars": [old_bar | {"date": "2026-07-07"}, old_bar],
                        "fund_flow": 1.2,
                        "pe_ttm": 22.0,
                    }
                },
                "candidate_universe": {
                    "items": [
                        {
                            "code": "600519",
                            "name": "贵州茅台",
                            "sector": "白酒",
                            "bars": [old_bar | {"date": "2026-07-07"}, old_bar],
                            "fund_flow": 1.2,
                            "pe_ttm": 22.0,
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

    assert "数据已滞后：最近应为 2026-07-10" in html
    assert "不能按今天盘面执行" in html
    assert 'data-research-status="数据暂停"' in html
    assert "数据质量：已滞后，不能排到前列" in html
    assert "排序暂停" in html


def test_web_blocks_actions_when_pipeline_refresh_is_stale(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("STOCK_TS_NOW", "2026-07-10T10:00:00+08:00")
    report_dir = tmp_path / "daily"
    report_dir.mkdir()
    (report_dir / "pipeline.status").write_text(
        "\n".join(
            [
                "status=ok",
                "generated_at=2026-07-09T00:30:00",
                "refresh=ok",
                "tdx_enrich=ok",
                "external_enrich=ok",
                "announcements=ok",
                "report=ok",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("STOCK_TS_DAILY_REPORT_DIR", str(report_dir))
    holdings = tmp_path / "holdings.csv"
    holdings.write_text(
        "code,name,shares,cost_price,sector,note\n600519,贵州茅台,10,1500,白酒,核心\n",
        encoding="utf-8",
    )
    snapshot = tmp_path / "tdx.json"
    latest_bar = {
        "date": "2026-07-09",
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
                    "trade_date": "2026-07-09",
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
                        "bars": [latest_bar | {"date": "2026-07-08"}, latest_bar],
                        "fund_flow": 1.2,
                        "pe_ttm": 22.0,
                    }
                },
                "candidate_universe": {
                    "items": [
                        {
                            "code": "600519",
                            "name": "贵州茅台",
                            "sector": "白酒",
                            "bars": [latest_bar | {"date": "2026-07-08"}, latest_bar],
                            "fund_flow": 1.2,
                            "pe_ttm": 22.0,
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

    assert "自动更新已滞后：超过 8 小时" in html
    assert "先刷新数据流水线" in html
    assert "排序暂停" in html


def test_web_blocks_when_kline_bars_are_stale_even_if_dates_are_real(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("STOCK_TS_NOW", "2026-07-11T09:30:00+08:00")
    holdings = tmp_path / "holdings.csv"
    holdings.write_text(
        "code,name,shares,cost_price,sector,note\n603278,大业股份,10,10,高端装备,核心\n",
        encoding="utf-8",
    )
    snapshot = tmp_path / "tdx.json"
    stock_bar = {
        "date": "2026-06-26",
        "open": 10,
        "high": 10.5,
        "low": 9.8,
        "close": 10.2,
        "volume": 10000,
    }
    candidate_bar = stock_bar | {"date": "2026-06-23", "close": 9.8}
    snapshot.write_text(
        json.dumps(
            {
                "market": {
                    "trade_date": "2026-07-10",
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
                    "top_sectors": [["高端装备", 1.2]],
                },
                "sectors": [
                    {
                        "name": "高端装备",
                        "pct_chg": 1.2,
                        "advancing_ratio": 0.7,
                        "amount_change": 10.0,
                    }
                ],
                "stocks": {
                    "603278": {
                        "name": "大业股份",
                        "bars": [stock_bar | {"date": "2026-06-25"}, stock_bar],
                    }
                },
                "candidate_universe": {
                    "items": [
                        {
                            "code": "603278",
                            "name": "大业股份",
                            "sector": "高端装备",
                            "bars": [candidate_bar | {"date": "2026-06-20"}, candidate_bar],
                        }
                    ]
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    html = render_page(
        stock_code="603278",
        provider_name="tdx-snapshot",
        provider=TdxSnapshotProvider(snapshot),
        holdings_path=str(holdings),
    )

    assert "K线已滞后：最近应为 2026-07-10" in html
    assert "个股K线最晚 2026-06-26" in html
    assert "候选池K线最晚 2026-06-23" in html
    assert "排序暂停" in html


def test_web_warns_when_multisource_context_is_missing_or_stale(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("STOCK_TS_NOW", "2026-07-11T09:30:00+08:00")
    holdings = tmp_path / "holdings.csv"
    holdings.write_text(
        "code,name,shares,cost_price,sector,note\n603278,大业股份,10,10,高端装备,核心\n",
        encoding="utf-8",
    )
    snapshot = tmp_path / "tdx.json"
    latest_bar = {
        "date": "2026-07-10",
        "open": 10,
        "high": 10.5,
        "low": 9.8,
        "close": 10.2,
        "volume": 10000,
    }
    snapshot.write_text(
        json.dumps(
            {
                "market": {
                    "trade_date": "2026-07-10",
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
                    "top_sectors": [["高端装备", 1.2]],
                },
                "market_news": [
                    {
                        "date": "2026-06-21 12:53:34",
                        "source": "东方财富财经",
                        "title": "旧市场新闻",
                        "summary": "旧新闻不能代表当天舆情",
                    }
                ],
                "sectors": [
                    {
                        "name": "高端装备",
                        "pct_chg": 1.2,
                        "advancing_ratio": 0.7,
                        "amount_change": 10.0,
                    }
                ],
                "stocks": {
                    "603278": {
                        "name": "大业股份",
                        "bars": [latest_bar | {"date": "2026-07-09"}, latest_bar],
                    }
                },
                "candidate_universe": {
                    "items": [
                        {
                            "code": "603278",
                            "name": "大业股份",
                            "sector": "高端装备",
                            "bars": [latest_bar | {"date": "2026-07-09"}, latest_bar],
                        }
                    ]
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    html = render_page(
        stock_code="603278",
        provider_name="tdx-snapshot",
        provider=TdxSnapshotProvider(snapshot),
        holdings_path=str(holdings),
    )

    assert "市场新闻已滞后：最近应为 2026-07-10，市场新闻最晚 2026-06-21" in html
    assert "多维数据缺口：资金面、消息面、公告、基本面缺失" in html
    assert "不能输出完整股票分析" in html
    assert "可用于专业复盘" not in html


def test_web_consumes_real_news_announcement_financial_and_sentiment_snapshot(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("STOCK_TS_NOW", "2026-07-10T10:00:00+08:00")
    holdings = tmp_path / "holdings.csv"
    holdings.write_text(
        "code,name,shares,cost_price,sector,note\n600519,贵州茅台,10,1500,白酒,核心\n",
        encoding="utf-8",
    )
    snapshot = tmp_path / "tdx.json"
    latest_bar = {
        "date": "2026-07-09",
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
                    "trade_date": "2026-07-09",
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
                "market_news": [
                    {
                        "date": "2026-07-09",
                        "source": "东方财富财经",
                        "title": "A股机器人板块涨停扩散",
                        "summary": "机器人、算力主线活跃",
                        "sentiment": "positive",
                    },
                    {
                        "date": "2026-07-09",
                        "source": "财联社",
                        "title": "多家公司提示减持风险",
                        "summary": "减持公告可能压制风险偏好",
                        "sentiment": "negative",
                    },
                ],
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
                        "bars": [latest_bar | {"date": "2026-07-08"}, latest_bar],
                        "fund_flow": 1.2,
                        "pe_ttm": 22.0,
                        "valuation": {
                            "source": "tushare.daily_basic",
                            "date": "2026-07-09",
                            "pb": 8.1,
                            "total_mv": 1850000000000,
                        },
                        "fundamental_metrics": {
                            "source": "tushare.fina_indicator",
                            "date": "2026-07-09",
                            "revenue_yoy": 15.2,
                            "net_profit_yoy": 18.4,
                            "roe": 29.6,
                            "gross_margin": 91.3,
                            "debt_to_assets": 18.5,
                            "ocf_to_profit": 1.18,
                        },
                        "fund_flow_detail": {
                            "source": "tushare.moneyflow",
                            "date": "2026-07-09",
                            "main_net_inflow": 1.2,
                            "main_net_pct": 3.4,
                        },
                        "news_items": [
                            {
                                "date": "2026-07-09",
                                "source": "东方财富",
                                "title": "贵州茅台发布经营稳健消息",
                                "summary": "营收增长，现金流稳定",
                                "sentiment": "positive",
                            }
                        ],
                        "announcements": [
                            {
                                "date": "2026-07-09",
                                "source": "cninfo",
                                "title": "贵州茅台2026年半年度业绩预告公告",
                                "url": "https://static.cninfo.com.cn/test.pdf",
                                "risk_flags": [],
                            }
                        ],
                        "data_sources": [
                            "tdx.kline",
                            "tushare.daily_basic",
                            "tushare.fina_indicator",
                            "tushare.moneyflow",
                            "akshare.stock_news_em",
                            "cninfo.announcement",
                        ],
                    }
                },
                "candidate_universe": {
                    "items": [
                        {
                            "code": "600519",
                            "name": "贵州茅台",
                            "sector": "白酒",
                            "bars": [latest_bar | {"date": "2026-07-08"}, latest_bar],
                            "fund_flow": 1.2,
                            "pe_ttm": 22.0,
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

    assert "异动事件" in html
    assert "机器人" in html
    assert "对应主题" in html
    assert "正面 1 / 负面 1" not in html
    assert "多家公司提示减持风险" not in html
    assert "贵州茅台2026年半年度业绩预告公告" in html
    assert "营收同比 15.2%" in html
    assert "净利同比 18.4%" in html
    assert "ROE 29.6%" in html
    assert "tushare.fina_indicator" in html
    assert "akshare.stock_news_em" in html
    assert "cninfo.announcement" in html


def test_web_displays_tdx_finance_metrics_as_basic_fundamental_evidence(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("STOCK_TS_NOW", "2026-07-11T09:30:00+08:00")
    holdings = tmp_path / "holdings.csv"
    holdings.write_text(
        "code,name,shares,cost_price,sector,note\n603278,大业股份,10,10,高端装备,核心\n",
        encoding="utf-8",
    )
    bar = {
        "date": "2026-07-10",
        "open": 10,
        "high": 10.5,
        "low": 9.8,
        "close": 10.2,
        "volume": 10000,
    }
    snapshot = tmp_path / "tdx.json"
    snapshot.write_text(
        json.dumps(
            {
                "market": {
                    "trade_date": "2026-07-10",
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
                    "top_sectors": [["高端装备", 1.2]],
                },
                "market_news": [
                    {
                        "date": "2026-07-10",
                        "source": "东方财富财经",
                        "title": "市场新闻",
                        "summary": "市场新闻",
                    }
                ],
                "sectors": [
                    {
                        "name": "高端装备",
                        "pct_chg": 1.2,
                        "advancing_ratio": 0.7,
                        "amount_change": 10.0,
                    }
                ],
                "stocks": {
                    "603278": {
                        "name": "大业股份",
                        "bars": [bar | {"date": "2026-07-09"}, bar],
                        "pe_ttm": 32.5,
                        "fund_flow_detail": {
                            "source": "tdx.quote.turnover",
                            "date": "2026-07-10",
                            "amount_yuan": 306457952.0,
                            "turnover_rate": 8.84,
                        },
                        "fundamental_metrics": {
                            "source": "tdx.profile.finance",
                            "date": "2026-05-18",
                            "eps": -0.07,
                            "net_asset_per_share": 5.66,
                            "operating_revenue": 1136418.25,
                            "net_profit": -24557.6,
                            "operating_cash_flow": 29811.0,
                        },
                        "news_items": [
                            {
                                "date": "2026-07-10",
                                "source": "东方财富",
                                "title": "大业股份新闻",
                                "summary": "经营更新",
                            }
                        ],
                        "announcements": [
                            {
                                "date": "2026-07-10",
                                "source": "cninfo",
                                "title": "大业股份公告",
                            }
                        ],
                        "data_sources": ["tdx.profile.finance"],
                    }
                },
                "candidate_universe": {
                    "items": [
                        {
                            "code": "603278",
                            "name": "大业股份",
                            "sector": "高端装备",
                            "bars": [bar | {"date": "2026-07-09"}, bar],
                        }
                    ]
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    html = render_page(
        stock_code="603278",
        provider_name="tdx-snapshot",
        provider=TdxSnapshotProvider(snapshot),
        holdings_path=str(holdings),
    )

    assert "EPS -0.07" in html
    assert "成交额 30645.80 万" in html
    assert "每股净资产 5.66" in html
    assert "营收 1136418.25" in html
    assert "净利润 -24557.60" in html


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
    assert "分析内容" in html
