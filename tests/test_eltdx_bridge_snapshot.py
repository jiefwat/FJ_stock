from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path


class FakeHelpers:
    def quote_table(self, codes: list[str]) -> dict[str, object]:
        return {
            "rows": [
                {
                    "code": "300001",
                    "full_code": "300001",
                    "name": "测试一",
                    "last_price": 12.0,
                    "pre_close_price": 10.0,
                    "amount": 200000000,
                    "board": "创业板",
                },
                {
                    "code": "600001",
                    "full_code": "600001",
                    "name": "测试二",
                    "last_price": 9.0,
                    "pre_close_price": 10.0,
                    "amount": 100000000,
                    "board": "主板",
                },
            ]
        }

    def stock_profile_table(
        self,
        codes: list[str],
        *,
        include_security: bool = True,
        include_finance: bool = True,
    ) -> dict[str, object]:
        return {
            "rows": [
                {"code": "300001", "name": "测试一", "turnover_rate": 3.2},
                {"code": "600001", "name": "测试二", "turnover_rate": 1.1},
            ]
        }

    def stock_topics(self, code: str) -> dict[str, object]:
        return {"topics": [{"topic_name": f"主题{code}"}]}


class FakeClient:
    def __init__(self) -> None:
        self.helpers = FakeHelpers()

    def get_a_share_codes_all(self) -> list[str]:
        return ["300001", "600001"]

    def get_kline(
        self, code: str, period: str, *, count: int, kind: str = "stock"
    ) -> dict[str, object]:
        return {
            "bars": [
                {
                    "time": "2026-06-17 15:00:00",
                    "open": 10.0,
                    "high": 11.0,
                    "low": 9.8,
                    "close": 10.8,
                    "volume": 10000,
                },
                {
                    "time": "2026-06-18 15:00:00",
                    "open": 10.9,
                    "high": 12.2,
                    "low": 10.7,
                    "close": 12.0,
                    "volume": 18000,
                },
            ]
        }


class FailingTopicHelpers(FakeHelpers):
    def stock_topics(self, code: str) -> dict[str, object]:
        return {"topics": []}


class FailingTopicClient(FakeClient):
    def __init__(self) -> None:
        self.helpers = FailingTopicHelpers()


class NoisyTopicHelpers(FakeHelpers):
    def stock_topics(self, code: str) -> dict[str, object]:
        return {
            "topics": [
                {
                    "topic_name": "近期强势",
                    "relation_level": 5.0,
                    "selected_date": 20260618,
                    "category_raw": 4,
                },
                {
                    "topic_name": "通达信88",
                    "relation_level": 5.0,
                    "selected_date": 20260618,
                    "category_raw": 4,
                },
                {
                    "topic_name": "含可转债",
                    "relation_level": 5.0,
                    "selected_date": 20260618,
                    "category_raw": 2,
                },
                {
                    "topic_name": "次新股",
                    "relation_level": 5.0,
                    "selected_date": 20260618,
                    "category_raw": 2,
                },
                {
                    "topic_name": "商业航天",
                    "relation_level": 3.0,
                    "selected_date": 20250601,
                    "category_raw": 2,
                },
            ]
        }


class NoisyTopicClient(FakeClient):
    def __init__(self) -> None:
        self.helpers = NoisyTopicHelpers()


class CountingProfileHelpers(FakeHelpers):
    def __init__(self) -> None:
        self.calls: list[tuple[list[str], bool]] = []

    def stock_profile_table(
        self,
        codes: list[str],
        *,
        include_security: bool = True,
        include_finance: bool = True,
    ) -> dict[str, object]:
        self.calls.append((list(codes), include_finance))
        return {"rows": [{"code": code, "name": code, "turnover_rate": 1.0} for code in codes]}


class CountingProfileClient(FakeClient):
    def __init__(self) -> None:
        self.helpers = CountingProfileHelpers()


class BrokenProfileHelpers(FakeHelpers):
    def stock_profile_table(
        self,
        codes: list[str],
        *,
        include_security: bool = True,
        include_finance: bool = True,
    ) -> dict[str, object]:
        raise RuntimeError("profile unavailable")


class BrokenProfileClient(FakeClient):
    def __init__(self) -> None:
        self.helpers = BrokenProfileHelpers()


def _load_bridge_module():
    fake_eltdx = types.ModuleType("eltdx")
    fake_eltdx.TdxClient = object
    fake_eltdx.to_jsonable = lambda value: value
    sys.modules.setdefault("eltdx", fake_eltdx)
    spec = importlib.util.spec_from_file_location("eltdx_bridge", Path("scripts/eltdx_bridge.py"))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_candidate_universe_bridge_exports_real_dated_bars() -> None:
    bridge = _load_bridge_module()

    payload = bridge.build_candidate_universe(
        FakeClient(),
        {"limit": 1, "bar_count": 2, "topic_limit": 1},
    )

    bars = payload["items"][0]["bars"]
    assert [bar["date"] for bar in bars] == ["2026-06-17", "2026-06-18"]
    assert not bars[-1]["date"].startswith("latest")


def test_candidate_universe_bridge_records_full_market_scan_metadata() -> None:
    bridge = _load_bridge_module()

    payload = bridge.build_candidate_universe(
        FakeClient(),
        {"limit": 1, "bar_count": 2, "topic_limit": 1},
    )

    assert payload["scanned_count"] == 2
    assert payload["returned_count"] == 1
    assert payload["scope"] == "all_a_share"
    assert "全市场" in payload["selection_method"]


def test_candidate_universe_bridge_batches_profile_without_finance_payload() -> None:
    bridge = _load_bridge_module()
    client = CountingProfileClient()

    result = bridge._single_profile(client, [f"300{i:03d}" for i in range(7)], batch_size=3)

    assert len(result["rows"]) == 7
    assert [len(codes) for codes, _ in client.helpers.calls] == [3, 3, 1]
    assert all(include_finance is False for _, include_finance in client.helpers.calls)


def test_candidate_universe_bridge_quote_only_uses_full_market_rows_without_profile_calls() -> None:
    bridge = _load_bridge_module()
    client = CountingProfileClient()

    payload = bridge.build_candidate_universe(
        client,
        {"limit": 2, "quote_only": True},
    )

    assert payload["scanned_count"] == 2
    assert payload["returned_count"] == 2
    assert payload["bar_source"] == "tdx_quote_preclose"
    assert client.helpers.calls == []
    assert payload["items"][0]["price_reliable"] is True
    assert len(payload["items"][0]["bars"]) == 2
    assert "行情截面" in payload["selection_method"]


def test_candidate_enrichment_bridge_adds_daily_bars_and_topic_without_quote_scan() -> None:
    bridge = _load_bridge_module()
    client = CountingProfileClient()

    payload = bridge.build_candidate_enrichment(
        client,
        {
            "bar_count": 2,
            "items": [
                {
                    "code": "300001",
                    "name": "测试一",
                    "sector": "未识别主题",
                    "bars": [],
                }
            ],
        },
    )

    assert payload["enriched_count"] == 1
    assert client.helpers.calls == [(["300001"], False)]
    assert payload["items"][0]["bar_source"] == "tdx_daily"
    assert payload["items"][0]["price_reliable"] is True
    assert payload["items"][0]["sector"] == "主题300001"
    assert [bar["date"] for bar in payload["items"][0]["bars"]] == [
        "2026-06-17",
        "2026-06-18",
    ]


def test_candidate_enrichment_bridge_keeps_working_when_profile_batch_fails() -> None:
    bridge = _load_bridge_module()

    payload = bridge.build_candidate_enrichment(
        BrokenProfileClient(),
        {
            "bar_count": 2,
            "items": [{"code": "920083", "name": "北交所样本", "sector": "未识别主题"}],
        },
    )

    assert payload["enriched_count"] == 1
    assert payload["items"][0]["name"] == "北交所样本"
    assert payload["items"][0]["bar_source"] == "tdx_daily"


def test_candidate_universe_bridge_prefers_topic_for_every_selected_candidate() -> None:
    bridge = _load_bridge_module()

    payload = bridge.build_candidate_universe(
        FakeClient(),
        {"limit": 2, "bar_count": 2, "topic_limit": 0},
    )

    assert [item["sector"] for item in payload["items"]] == ["主题300001", "主题600001"]


def test_candidate_universe_bridge_does_not_use_exchange_board_as_theme() -> None:
    bridge = _load_bridge_module()

    payload = bridge.build_candidate_universe(
        FailingTopicClient(),
        {"limit": 2, "bar_count": 2},
    )

    assert [item["sector"] for item in payload["items"]] == ["未识别主题", "未识别主题"]


def test_sector_aggregation_skips_exchange_board_fallback_topics() -> None:
    bridge = _load_bridge_module()

    rows = FailingTopicClient().helpers.quote_table(["300001", "600001"])["rows"]
    aggregated = bridge._aggregate_sector_rows(FailingTopicClient(), rows, sector_limit=10)

    assert aggregated == []


def test_candidate_universe_bridge_filters_status_topics_before_theme() -> None:
    bridge = _load_bridge_module()

    payload = bridge.build_candidate_universe(
        NoisyTopicClient(),
        {"limit": 1, "bar_count": 2},
    )

    assert payload["items"][0]["sector"] == "商业航天"


def test_sector_aggregation_uses_clean_theme_not_status_topic() -> None:
    bridge = _load_bridge_module()

    rows = NoisyTopicClient().helpers.quote_table(["300001"])["rows"][:1]
    aggregated = bridge._aggregate_sector_rows(NoisyTopicClient(), rows, sector_limit=10)

    assert aggregated[0][0] == "商业航天"


class AbnormalPctHelpers(FakeHelpers):
    def quote_table(self, codes: list[str]) -> dict[str, object]:
        return {
            "rows": [
                {
                    "code": "300888",
                    "full_code": "300888",
                    "name": "异常样本",
                    "last_price": 311.65,
                    "pre_close_price": 100.0,
                    "amount": 100000000,
                    "board": "创业板",
                }
            ]
        }

    def stock_topics(self, code: str) -> dict[str, object]:
        return {"topics": [{"topic_name": "医疗器械概念", "relation_level": 5.0}]}


class AbnormalPctClient(FakeClient):
    def __init__(self) -> None:
        self.helpers = AbnormalPctHelpers()


def test_sector_aggregation_does_not_export_abnormal_pct_as_sector_move() -> None:
    bridge = _load_bridge_module()

    rows = AbnormalPctClient().helpers.quote_table(["300888"])["rows"]
    aggregated = bridge._aggregate_sector_rows(AbnormalPctClient(), rows, sector_limit=10)

    assert aggregated[0][0] == "医疗器械概念"
    assert aggregated[0][1] == 0.0
    assert aggregated[0][5] is True


class ZeroPriceHelpers(FakeHelpers):
    def quote_table(self, codes: list[str]) -> dict[str, object]:
        return {
            "rows": [
                {
                    "code": "600000",
                    "full_code": "600000",
                    "name": "停牌无价",
                    "last_price": 0.0,
                    "pre_close_price": 10.0,
                    "amount": 0,
                    "board": "主板",
                },
                {
                    "code": "600001",
                    "full_code": "600001",
                    "name": "真实跌停",
                    "last_price": 9.0,
                    "pre_close_price": 10.0,
                    "amount": 100000000,
                    "board": "主板",
                },
            ]
        }


class ZeroPriceClient(FakeClient):
    def __init__(self) -> None:
        self.helpers = ZeroPriceHelpers()

    def get_a_share_codes_all(self) -> list[str]:
        return ["600000", "600001"]


def test_market_bridge_ignores_zero_price_when_counting_limit_down() -> None:
    bridge = _load_bridge_module()

    payload = bridge.build_market_snapshot(ZeroPriceClient(), {"limit_down_detail_limit": 10})

    assert payload["limit_down"] == 1
    assert [item["code"] for item in payload["limit_down_details"]] == ["600001"]
