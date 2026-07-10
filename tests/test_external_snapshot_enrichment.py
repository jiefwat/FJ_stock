from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from stock_ts.providers.tdx_snapshot_provider import TdxSnapshotProvider
from stock_ts.web import render_page


class MiniSeries(dict):
    def __getitem__(self, key: str):
        return dict.__getitem__(self, key)

    def get(self, key: str, default=None):
        return dict.get(self, key, default)


class MiniFrame:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows
        self.empty = not rows
        self.columns = set(rows[0].keys()) if rows else set()

    def __len__(self) -> int:
        return len(self._rows)

    def iterrows(self):
        for index, row in enumerate(self._rows):
            yield index, MiniSeries(row)

    def tail(self, count: int) -> MiniFrame:
        return MiniFrame(self._rows[-count:])

    def head(self, count: int) -> MiniFrame:
        return MiniFrame(self._rows[:count])

    def to_dict(self, orient: str):
        assert orient == "records"
        return [dict(row) for row in self._rows]


class RichAk:
    def stock_zh_a_hist(self, symbol: str, period: str = "daily", adjust: str = "qfq") -> MiniFrame:
        return MiniFrame(
            [
                {
                    "日期": "2026-06-17",
                    "开盘": 10,
                    "最高": 11,
                    "最低": 9,
                    "收盘": 10.5,
                    "成交量": 1000,
                },
                {
                    "日期": "2026-06-18",
                    "开盘": 10.5,
                    "最高": 12,
                    "最低": 10.2,
                    "收盘": 11.8,
                    "成交量": 2200,
                },
            ]
        )

    def stock_value_em(self, symbol: str) -> MiniFrame:
        return MiniFrame(
            [
                {
                    "数据日期": "2026-06-18",
                    "PE(TTM)": 36.5,
                    "市净率": 4.2,
                    "市销率": 8.1,
                    "总市值": 12345678900,
                }
            ]
        )

    def stock_individual_fund_flow(self, stock: str, market: str) -> MiniFrame:
        return MiniFrame(
            [
                {
                    "日期": "2026-06-18",
                    "主力净流入-净额": 230000000,
                    "主力净流入-净占比": 7.5,
                    "超大单净流入-净额": 120000000,
                    "大单净流入-净额": 80000000,
                    "小单净流入-净额": -40000000,
                }
            ]
        )

    def stock_news_em(self, symbol: str) -> MiniFrame:
        return MiniFrame(
            [
                {
                    "新闻标题": "公司产品放量",
                    "新闻内容": "核心产品订单增长",
                    "发布时间": "2026-06-18 09:30:00",
                    "文章来源": "东方财富",
                    "新闻链接": "https://example.com/news",
                }
            ]
        )

    def stock_info_global_em(self) -> MiniFrame:
        return MiniFrame(
            [
                {
                    "标题": "市场主线活跃",
                    "摘要": "科技方向成交活跃",
                    "发布时间": "2026-06-18 15:30:00",
                    "链接": "https://example.com/market",
                }
            ]
        )


class PartialAk(RichAk):
    def stock_zh_a_hist(self, symbol: str, period: str = "daily", adjust: str = "qfq") -> MiniFrame:
        raise RuntimeError("kline unavailable")

    def stock_individual_fund_flow(self, stock: str, market: str) -> MiniFrame:
        raise RuntimeError("fund unavailable")


class TushareOnlyAk(PartialAk):
    def stock_value_em(self, symbol: str) -> MiniFrame:
        raise RuntimeError("ak valuation unavailable")

    def stock_news_em(self, symbol: str) -> MiniFrame:
        raise RuntimeError("ak news unavailable")


class RichItick:
    def fetch_daily_bars(self, code: str, *, limit: int = 120):
        from stock_ts.models import DailyBar

        assert code == "688362"
        assert limit == 120
        return [
            DailyBar("2026-06-17", 20, 21, 19, 20.5, 3000),
            DailyBar("2026-06-18", 20.5, 22, 20.2, 21.8, 4200),
        ]

    def fetch_tick(self, code: str):
        assert code == "688362"
        return {"source": "itick.stock_tick", "latest_price": 21.8, "volume": 4200}


class RichTushare:
    def daily(self, ts_code: str, limit: int):
        return MiniFrame(
            [
                {
                    "trade_date": "20260617",
                    "open": 10,
                    "high": 11,
                    "low": 9,
                    "close": 10.5,
                    "vol": 10,
                },
                {
                    "trade_date": "20260618",
                    "open": 10.5,
                    "high": 12,
                    "low": 10.2,
                    "close": 11.8,
                    "vol": 22,
                },
            ]
        )

    def daily_basic(self, ts_code: str, limit: int, fields: str):
        return MiniFrame(
            [
                {
                    "trade_date": "20260618",
                    "pe_ttm": 40.2,
                    "pb": 5.1,
                    "ps": 8.8,
                    "total_mv": 1234.5,
                    "turnover_rate": 6.5,
                }
            ]
        )

    def moneyflow(self, ts_code: str, limit: int):
        return MiniFrame([{"trade_date": "20260618", "net_mf_amount": 12345}])


def _load_enrichment_module():
    spec = importlib.util.spec_from_file_location(
        "enrich_tdx_snapshot", Path("scripts/enrich_tdx_snapshot.py")
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_snapshot(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "market": {
                    "trade_date": "2026-06-18",
                    "indices": [],
                    "advancing": 1,
                    "declining": 1,
                    "limit_up": 0,
                    "limit_down": 0,
                },
                "sectors": [
                    {"name": "芯片", "pct_chg": 1.2, "advancing_ratio": 0.6, "amount_change": 2.0}
                ],
                "stocks": {
                    "688362": {
                        "name": "甬矽电子",
                        "bars": [
                            {
                                "date": "2026-06-18",
                                "open": 10,
                                "high": 11,
                                "low": 9,
                                "close": 10.5,
                                "volume": 1000,
                            }
                        ],
                    }
                },
                "candidate_universe": {
                    "scope": "all_a_share",
                    "items": [
                        {
                            "code": "688362",
                            "name": "甬矽电子",
                            "sector": "芯片",
                            "bars": [
                                {
                                    "date": "2026-06-17",
                                    "open": 10,
                                    "high": 11,
                                    "low": 9,
                                    "close": 10.0,
                                    "volume": 1000,
                                },
                                {
                                    "date": "2026-06-18",
                                    "open": 10,
                                    "high": 11,
                                    "low": 9,
                                    "close": 10.5,
                                    "volume": 1000,
                                },
                            ],
                        }
                    ],
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_enrich_tdx_snapshot_writes_kline_valuation_fund_and_news(tmp_path: Path) -> None:
    module = _load_enrichment_module()
    snapshot = tmp_path / "tdx.json"
    _write_snapshot(snapshot)

    summary = module.enrich_snapshot(snapshot, codes=["688362"], ak=RichAk(), market_news_limit=1)

    data = json.loads(snapshot.read_text(encoding="utf-8"))
    stock = data["stocks"]["688362"]
    assert summary["enriched_stock_count"] == 1
    assert len(stock["bars"]) == 2
    assert stock["pe_ttm"] == 36.5
    assert stock["fund_flow"] == 2.3
    assert stock["valuation"]["pb"] == 4.2
    assert stock["fund_flow_detail"]["main_net_pct"] == 7.5
    assert stock["news_items"][0]["title"] == "公司产品放量"
    assert data["market_news"][0]["title"] == "市场主线活跃"


def test_enrich_tdx_snapshot_keeps_partial_fields_when_some_interfaces_fail(tmp_path: Path) -> None:
    module = _load_enrichment_module()
    snapshot = tmp_path / "tdx.json"
    _write_snapshot(snapshot)

    summary = module.enrich_snapshot(
        snapshot, codes=["688362"], ak=PartialAk(), market_news_limit=1
    )

    stock = json.loads(snapshot.read_text(encoding="utf-8"))["stocks"]["688362"]
    assert summary["enriched_stock_count"] == 1
    assert stock["pe_ttm"] == 36.5
    assert stock["news_items"][0]["title"] == "公司产品放量"
    assert stock["enrichment_errors"]["daily_bars"] == "kline unavailable"
    assert stock["enrichment_errors"]["fund_flow"] == "fund unavailable"



def test_enrich_tdx_snapshot_flushes_each_stock_before_next_request(tmp_path: Path) -> None:
    module = _load_enrichment_module()
    snapshot = tmp_path / "tdx.json"
    _write_snapshot(snapshot)
    data = json.loads(snapshot.read_text(encoding="utf-8"))
    data["stocks"]["600481"] = {"name": "双良节能", "bars": data["stocks"]["688362"]["bars"]}
    data["candidate_universe"]["items"].append(
        {
            "code": "600481",
            "name": "双良节能",
            "sector": "光伏",
            "bars": data["stocks"]["688362"]["bars"],
        }
    )
    snapshot.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    seen_flushed = {"value": False}

    class InspectingAk(RichAk):
        def stock_zh_a_hist(
            self, symbol: str, period: str = "daily", adjust: str = "qfq"
        ) -> MiniFrame:
            if symbol == "600481":
                current = json.loads(snapshot.read_text(encoding="utf-8"))
                seen_flushed["value"] = bool(current["stocks"]["688362"].get("news_items"))
            return super().stock_zh_a_hist(symbol, period=period, adjust=adjust)

    summary = module.enrich_snapshot(
        snapshot, codes=["688362", "600481"], ak=InspectingAk(), market_news_limit=0
    )

    assert summary["enriched_stock_count"] == 2
    assert seen_flushed["value"] is True

def test_enrich_tdx_snapshot_uses_tushare_for_kline_and_valuation(tmp_path: Path) -> None:
    module = _load_enrichment_module()
    snapshot = tmp_path / "tdx.json"
    _write_snapshot(snapshot)

    module.enrich_snapshot(
        snapshot,
        codes=["688362"],
        ak=TushareOnlyAk(),
        tushare_client=RichTushare(),
        market_news_limit=0,
    )

    stock = json.loads(snapshot.read_text(encoding="utf-8"))["stocks"]["688362"]
    assert stock["bar_source"] == "tushare.daily"
    assert stock["bars"][-1]["date"] == "2026-06-18"
    assert stock["pe_ttm"] == 40.2
    assert stock["valuation"]["source"] == "tushare.daily_basic"
    assert stock["valuation"]["pb"] == 5.1


def test_tdx_provider_and_web_use_enriched_stock_fields(tmp_path: Path) -> None:
    module = _load_enrichment_module()
    snapshot = tmp_path / "tdx.json"
    _write_snapshot(snapshot)
    module.enrich_snapshot(snapshot, codes=["688362"], ak=RichAk(), market_news_limit=1)

    provider = TdxSnapshotProvider(snapshot)
    stock = provider.fetch_stock("688362")
    assert stock.pe_ttm == 36.5
    assert stock.fund_flow == 2.3
    assert stock.valuation["pb"] == 4.2
    assert stock.news_items[0].title == "公司产品放量"
    holdings = tmp_path / "holdings.csv"
    holdings.write_text(
        "code,name,shares,cost_price,sector,note\n688362,甬矽电子,100,10.0,芯片,测试\n",
        encoding="utf-8",
    )

    html = render_page(
        stock_code="688362",
        provider_name="tdx-snapshot",
        provider=provider,
        holdings_path=str(holdings),
    )
    stock_start = html.index('id="stock"')
    next_workspace = html.find('<section class="workspace-pane', stock_start + 1)
    stock_html = html[stock_start:] if next_workspace == -1 else html[stock_start:next_workspace]
    assert "PE(TTM) 36.5" in stock_html
    assert "主力净流入 2.30 亿" in stock_html
    assert "公司产品放量" in stock_html
    assert "估值未接入" not in stock_html
    assert "资金明细未接入" not in stock_html


def test_enrich_tdx_snapshot_uses_itick_as_kline_fallback(tmp_path: Path, monkeypatch) -> None:
    module = _load_enrichment_module()
    snapshot = tmp_path / "tdx.json"
    _write_snapshot(snapshot)
    monkeypatch.chdir(tmp_path)

    module.enrich_snapshot(
        snapshot,
        codes=["688362"],
        ak=PartialAk(),
        itick_client=RichItick(),
        market_news_limit=0,
    )

    data = json.loads(snapshot.read_text(encoding="utf-8"))
    stock = data["stocks"]["688362"]
    candidate = data["candidate_universe"]["items"][0]
    assert stock["bar_source"] == "itick.stock_kline"
    assert stock["bars"][-1]["close"] == 21.8
    assert stock["latest_quote"]["source"] == "itick.stock_tick"
    assert "itick" in stock["data_sources"]
    assert candidate["bar_source"] == "itick.stock_kline"
    assert candidate["bars"][-1]["close"] == 21.8
    assert "itick" in data["external_enrichment"]["sources"]


def test_enrich_tdx_snapshot_classifies_news_and_records_quality(tmp_path: Path) -> None:
    module = _load_enrichment_module()
    snapshot = tmp_path / "tdx.json"
    _write_snapshot(snapshot)

    module.enrich_snapshot(snapshot, codes=["688362"], ak=RichAk(), market_news_limit=1)

    data = json.loads(snapshot.read_text(encoding="utf-8"))
    stock = data["stocks"]["688362"]
    assert stock["data_quality"]["data_quality"] == "good"
    assert stock["data_quality"]["primary_source"] in {"akshare.stock_zh_a_hist", "multi-source"}
    assert stock["news_items"][0]["sentiment"] == "positive"
    assert "订单" in stock["news_items"][0]["catalyst_tags"]


def test_enrich_tdx_snapshot_accepts_fail_open_external_intelligence_urls(tmp_path: Path) -> None:
    module = _load_enrichment_module()
    snapshot = tmp_path / "tdx.json"
    _write_snapshot(snapshot)

    def opener(url: str, timeout: float) -> bytes:
        if "bad" in url:
            raise TimeoutError("bad source")
        payload = {
            "items": [
                {"title": "机器人订单增长", "summary": "AI算力方向活跃", "url": "https://n/robot"}
            ]
        }
        return json.dumps(payload, ensure_ascii=False).encode()

    module.enrich_snapshot(
        snapshot,
        codes=["688362"],
        ak=RichAk(),
        market_news_limit=1,
        intelligence_urls=["https://bad.example/news", "https://good.example/news"],
        intelligence_opener=opener,
    )

    data = json.loads(snapshot.read_text(encoding="utf-8"))
    assert any(item["title"] == "机器人订单增长" for item in data["market_news"])
    assert data["external_enrichment"]["intelligence_statuses"]["env-1"].startswith("failed:")
    assert data["external_enrichment"]["intelligence_statuses"]["env-2"] == "ok:1"


def test_daily_report_uses_snapshot_market_news_when_no_news_csv(tmp_path: Path) -> None:
    from stock_ts.workflows import build_daily_report

    snapshot = tmp_path / "tdx.json"
    _write_snapshot(snapshot)
    data = json.loads(snapshot.read_text(encoding="utf-8"))
    data["market_news"] = [
        {
            "date": "2026-06-18",
            "source": "财联社",
            "title": "商业航天订单增长",
            "summary": "机器人方向活跃",
            "sentiment": "positive",
        }
    ]
    snapshot.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    report = build_daily_report(TdxSnapshotProvider(snapshot), candidate_limit=1)

    assert report.news is not None
    assert report.news.positive_count == 1
    assert "商业航天订单增长" in report.markdown


def test_enrich_tdx_snapshot_times_out_slow_market_news(tmp_path: Path) -> None:
    import time

    class SlowMarketNewsAk(RichAk):
        def stock_info_global_em(self) -> MiniFrame:
            time.sleep(2)
            return MiniFrame([])

    module = _load_enrichment_module()
    snapshot = tmp_path / "tdx.json"
    _write_snapshot(snapshot)

    summary = module.enrich_snapshot(
        snapshot,
        codes=[],
        limit=0,
        ak=SlowMarketNewsAk(),
        field_timeout=1,
        market_news_limit=20,
    )

    assert summary["market_news_count"] == 0
    data = json.loads(snapshot.read_text(encoding="utf-8"))
    assert data["external_enrichment"]["intelligence_statuses"]["akshare-global"].startswith(
        "failed:"
    )


def test_select_codes_respects_zero_limit_for_market_news_only(tmp_path: Path) -> None:
    module = _load_enrichment_module()
    snapshot = tmp_path / "tdx.json"
    _write_snapshot(snapshot)
    payload = json.loads(snapshot.read_text(encoding="utf-8"))

    assert module._select_codes(payload, explicit_codes=None, limit=0) == []


def test_stock_data_quality_ignores_skipped_optional_fields() -> None:
    module = _load_enrichment_module()
    quality = module._stock_data_quality_payload(
        {
            "bar_source": "tushare.daily",
            "data_sources": ["tushare"],
            "bars": [{"close": 10}],
            "valuation": {"pe_ttm": 20},
            "fund_flow_detail": {"main_net_inflow": 1.2},
            "news_items": [{"title": "订单增长"}],
        },
        {"tushare_moneyflow": "skipped"},
    )

    assert quality["data_quality"] == "good"
    assert quality["fallback_from"] == []
    assert quality["attempts"][0]["ok"] is True


def test_market_intelligence_filters_builtin_akshare_noise_without_external_sources() -> None:
    module = _load_enrichment_module()

    class NoisyMarketAk(RichAk):
        def stock_info_global_em(self) -> MiniFrame:
            return MiniFrame(
                [
                    {"标题": "特朗普重要票仓利益受损：数据中心推高美国能源成本"},
                    {"标题": "韩国交易所对KOSPI指数启动熔断机制"},
                    {"标题": "科创50指数半日涨超3% 半导体产业链走强"},
                ]
            )

    result = module._fetch_market_intelligence(
        NoisyMarketAk(),
        limit=20,
        urls=None,
        opener=None,
        timeout=1,
        field_timeout=1,
    )

    titles = [item["title"] for item in result["items"]]
    assert titles == ["科创50指数半日涨超3% 半导体产业链走强"]
