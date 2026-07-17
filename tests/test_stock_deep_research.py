from __future__ import annotations

import json

import pytest

import stock_ts.stock_deep_research as deep_research_module
from stock_ts.iwencai import (
    SKILLS,
    IwencaiConfigurationError,
    IwencaiError,
    IwencaiGatewayError,
)
from stock_ts.stock_deep_research import DeepResearchFact, StockDeepResearchService


def _row_for(capability: str) -> dict[str, object]:
    return {
        "basicinfo": {"公司名称": "贵州茅台股份有限公司", "公司类型": "国有企业"},
        "business": {"主营产品": "白酒", "竞争对手": "主要同行"},
        "management": {"股东户数[2026Q2]": 120000, "质押比例": "0.2%"},
        "finance": {"营业收入[2025]": 180_000_000_000, "归母净利润[2025]": 86_000_000_000},
        "industry": {"行业名称": "白酒", "行业排名": 1, "行业市盈率": 24.6},
        "consensus": {"预测净利润[2027]": 95_000_000_000, "机构评级": "增持"},
        "report": {"title": "盈利质量稳定", "summary": "关注需求变化", "publish_date": "20260716"},
        "market": {"收盘价": 1480.0, "成交量": 8_600_000, "交易日期": "20260716"},
        "event": {"业绩预告类型": "预增", "公告日期": "20260716"},
        "announcement": {
            "title": "经营数据公告",
            "summary": "收入保持增长",
            "publish_date": "20260716",
        },
        "news": {
            "title": "渠道库存改善",
            "summary": "仍需跟踪终端需求",
            "publish_date": "20260716",
        },
    }[capability]


class FakeClient:
    def __init__(
        self,
        *,
        failures: set[str] | None = None,
        rows: dict[str, dict[str, object]] | None = None,
    ) -> None:
        self.failures = failures or set()
        self.rows = rows or {}
        self.calls: list[tuple[str, str]] = []

    def query(self, skill: object, query: str) -> dict[str, object]:
        capability = next(key for key, value in SKILLS.items() if value == skill)
        self.calls.append((capability, query))
        if capability in self.failures:
            raise RuntimeError("gateway trace_id secret failure")
        return {
            "datas": [self.rows.get(capability, _row_for(capability))],
            "trace_id": "secret-trace",
            "provider": "internal-provider",
        }


class AlwaysFailingClient:
    def __init__(self, error_type: type[IwencaiError]) -> None:
        self.error_type = error_type

    def query(self, _skill: object, _query: str) -> dict[str, object]:
        raise self.error_type("gateway trace secret /private/path")


def test_all_focus_returns_six_supplier_neutral_product_groups() -> None:
    client = FakeClient()
    service = StockDeepResearchService(client_factory=lambda: client)

    result = service.research(
        code="600519",
        name="贵州茅台",
        focus="all",
        question="",
        refresh=False,
    )
    payload = result.to_public_dict()

    assert [group["key"] for group in payload["groups"]] == [
        "company",
        "finance",
        "industry",
        "consensus",
        "market",
        "event",
    ]
    assert payload["status"] == "complete"
    assert payload["coverage"] == {"ready": 11, "total": 11}
    assert len(client.calls) == 11
    serialized = json.dumps(payload, ensure_ascii=False)
    for forbidden in (
        "问财",
        "同花顺",
        "skill_id",
        "trace",
        "gateway",
        "api_key",
        "Cookie",
        "成本",
        "权重",
        "持仓",
        "账号",
    ):
        assert forbidden.casefold() not in serialized.casefold()
    assert all(
        forbidden not in query
        for _capability, query in client.calls
        for forbidden in ("持仓", "成本", "权重", "账号", "Cookie")
    )


def test_public_facts_remove_sensitive_supplier_content_from_labels_and_values() -> None:
    class LeakyFactClient:
        def query(self, _skill: object, _query: str) -> dict[str, object]:
            return {
                "datas": [
                    {
                        "营业收入[2025]": (
                            "问财 同花顺 iWencai skill id trace gateway secret /private/path"
                        )
                    }
                ]
            }

    payload = StockDeepResearchService(client_factory=LeakyFactClient).research(
        code="600519",
        name="贵州茅台",
        focus="finance",
    ).to_public_dict()
    sensitive_label = DeepResearchFact(
        label="iWencai skill_id trace gateway",
        value="正常事实",
    ).to_public_dict()
    serialized = json.dumps({"payload": payload, "label": sensitive_label}, ensure_ascii=False)

    for forbidden in (
        "问财",
        "同花顺",
        "iwencai",
        "skill id",
        "skill_id",
        "trace",
        "gateway",
        "secret",
        "/private/path",
    ):
        assert forbidden.casefold() not in serialized.casefold()
    assert "安全处理" in serialized


def test_focus_allowlist_runs_only_the_requested_group() -> None:
    client = FakeClient()
    result = StockDeepResearchService(client_factory=lambda: client).research(
        code="600519",
        name="贵州茅台",
        focus="company",
    )

    assert [group.key for group in result.groups] == ["company"]
    assert {capability for capability, _query in client.calls} == {
        "basicinfo",
        "business",
        "management",
    }


def test_custom_question_routes_to_one_capability_without_private_context() -> None:
    client = FakeClient()
    result = StockDeepResearchService(client_factory=lambda: client).research(
        code="600519",
        name="贵州茅台",
        focus="all",
        question="股东户数变化如何",
    )

    assert [capability for capability, _query in client.calls] == ["management"]
    assert [group.key for group in result.groups] == ["company"]
    assert "股东户数变化如何" in client.calls[0][1]


@pytest.mark.parametrize(
    "question",
    [
        "我的持股数量是多少",
        "show my holdings cost",
        "check account weight",
        "我的仓位30%",
        "我的买入价1500",
        "当前浮亏20%",
        "浮盈",
        "持仓成本",
        "position size",
        "entry price",
        "my average cost",
        "my PnL",
        "持股成本1500元",
        "持股数量100股",
        "累计盈亏20%",
        "成本价1500元",
        "我持有100股",
        "本人持有100股",
        "账户盈亏20%",
        "当前盈亏20%",
        "持仓均价1500元",
        "买入成本1500元",
        "持股的成本",
        "持股的数量",
        "持股均价",
        "我现在持有100股",
        "本人现持有100股",
        "当前总盈亏20%",
        "累计总盈亏20%",
        "我的公司持仓",
        "个人持股100股",
        "个人持有100股",
        "我在公司有100股",
        "本人在公司有100股",
        "当前的盈亏20%",
        "当前的总盈亏20%",
        "持股的平均成本",
        "持股平均成本",
        "I hold 100 shares",
        "I own 100 shares",
        "I have 100 shares",
        "I bought 100 shares",
        "my stake is 30%",
        "我持有贵州茅台，怎么看",
        "本人持有这只股票",
        "我在这家公司持股",
        "I own shares in this company",
        "I hold shares of this stock",
    ],
)
def test_custom_question_rejects_private_portfolio_terms(question: str) -> None:
    client = FakeClient()
    with pytest.raises(ValueError, match="账户|持仓"):
        StockDeepResearchService(client_factory=lambda: client).research(
            code="600519",
            name="贵州茅台",
            question=question,
        )
    assert client.calls == []


@pytest.mark.parametrize(
    "question",
    [
        "原材料成本",
        "经营成本",
        "成本承压缓解",
        "大股东持股比例",
        "大股东持股数量",
        "控股股东持股数量变化",
        "前十大股东持股",
        "机构持股均价",
        "公司产品成本价变化",
        "公司当前盈亏情况",
        "我想问大股东持股数量",
        "我想了解大股东持股数量",
        "我想知道大股东持股数量",
        "请问大股东持股数量",
        "我想请问大股东持股数量",
        "我想研究控股股东持股比例",
        "我想看看机构持股均价",
        "我有个问题：前十大股东持股变化",
        "I have a question about institutional shares",
        "I want to know the major shareholder holdings",
        "我想研究大股东持有多少",
        "I want to know what institutional investors hold",
    ],
)
def test_custom_question_allows_company_cost_and_shareholding_research(
    question: str,
) -> None:
    client = FakeClient()

    result = StockDeepResearchService(client_factory=lambda: client).research(
        code="600519",
        name="贵州茅台",
        question=question,
    )

    assert result.ok is True
    assert len(client.calls) == 1


def test_partial_success_preserves_available_facts_and_recovery_copy() -> None:
    client = FakeClient(failures={"report", "news"})
    result = StockDeepResearchService(client_factory=lambda: client).research(
        code="600519",
        name="贵州茅台",
        focus="all",
    )
    payload = result.to_public_dict()

    assert payload["ok"] is True
    assert payload["status"] == "partial"
    assert payload["coverage"] == {"ready": 9, "total": 11}
    assert any(group["status"] == "partial" for group in payload["groups"])
    assert all("gateway" not in group["recovery"].lower() for group in payload["groups"])


def test_public_evidence_contract_separates_support_from_explicit_conflicts() -> None:
    client = FakeClient(
        rows={
            "finance": {
                "营业收入同比[2025]": "8%",
                "归母净利润同比[2025]": "-10%",
            }
        }
    )
    payload = StockDeepResearchService(client_factory=lambda: client).research(
        code="600519",
        name="贵州茅台",
        focus="finance",
    ).to_public_dict()
    group = payload["groups"][0]

    assert group["support"] == [
        {"label": "营业收入同比[2025]", "value": "8%"},
    ]
    assert group["conflicts"] == [
        {"label": "归母净利润同比[2025]", "value": "-10%"},
    ]
    assert group["gaps"] == []


@pytest.mark.parametrize(
    ("focus", "capability", "row", "expected"),
    [
        ("event", "event", {"业绩预告类型": "预亏"}, "预亏"),
        ("consensus", "consensus", {"机构评级": "下修"}, "下修"),
        ("market", "market", {"主力资金流向": "净流出 2 亿元"}, "净流出"),
        ("finance", "finance", {"营业收入同比[2025]": "明显下降"}, "明显下降"),
    ],
)
def test_explicit_negative_language_is_published_only_as_conflict(
    focus: str,
    capability: str,
    row: dict[str, object],
    expected: str,
) -> None:
    client = FakeClient(rows={capability: row})
    payload = StockDeepResearchService(client_factory=lambda: client).research(
        code="600519",
        name="贵州茅台",
        focus=focus,
    ).to_public_dict()
    group = payload["groups"][0]

    assert any(expected in fact["value"] for fact in group["conflicts"])
    assert all(expected not in fact["value"] for fact in group["support"])


def test_neutral_dates_and_company_facts_are_not_forced_into_conflicts() -> None:
    client = FakeClient(
        rows={
            "basicinfo": {
                "公司类型": "国有企业",
                "成立日期": "19991120",
            }
        }
    )
    payload = StockDeepResearchService(client_factory=lambda: client).research(
        code="600519",
        name="贵州茅台",
        focus="company",
    ).to_public_dict()
    company = payload["groups"][0]

    assert {fact["label"] for fact in company["support"]} >= {"公司类型", "成立日期"}
    assert company["conflicts"] == []


def test_partial_group_exposes_only_product_gap_labels() -> None:
    client = FakeClient(failures={"report", "news"})
    payload = StockDeepResearchService(client_factory=lambda: client).research(
        code="600519",
        name="贵州茅台",
        focus="all",
    ).to_public_dict()
    groups = {group["key"]: group for group in payload["groups"]}

    assert groups["consensus"]["gaps"] == ["研究报告"]
    assert groups["event"]["gaps"] == ["新闻动态"]
    serialized = json.dumps(groups, ensure_ascii=False)
    for forbidden in ("report", "news", "gateway", "trace", "secret"):
        assert forbidden.casefold() not in serialized.casefold()


def test_cache_ttl_and_refresh_control_live_calls() -> None:
    now = [1000.0]
    client = FakeClient()
    service = StockDeepResearchService(
        client_factory=lambda: client,
        clock=lambda: now[0],
        cache_ttl=300,
    )

    first = service.research(code="600519", name="贵州茅台")
    call_count = len(client.calls)
    cached = service.research(code="600519", name="贵州茅台")
    refreshed = service.research(code="600519", name="贵州茅台", refresh=True)
    now[0] += 301
    expired = service.research(code="600519", name="贵州茅台")

    assert first.cached is False
    assert cached.cached is True
    assert len(client.calls) == call_count * 3
    assert refreshed.cached is False
    assert expired.cached is False


def test_cache_is_bounded_and_evicts_the_least_recently_used_key() -> None:
    client = FakeClient()
    service = StockDeepResearchService(client_factory=lambda: client)

    for index in range(128):
        service.research(
            code="600519",
            name="测试公司",
            question=f"营业收入趋势 {index}",
        )
    service.research(code="600519", name="测试公司", question="营业收入趋势 0")
    service.research(code="600519", name="测试公司", question="营业收入趋势 128")

    assert deep_research_module.MAX_CACHE_ENTRIES == 128
    assert len(service._cache) == deep_research_module.MAX_CACHE_ENTRIES
    assert ("600519", "测试公司", "all", "营业收入趋势 0") in service._cache
    assert ("600519", "测试公司", "all", "营业收入趋势 1") not in service._cache


def test_new_cache_key_prunes_all_expired_entries() -> None:
    now = [1000.0]
    client = FakeClient()
    service = StockDeepResearchService(
        client_factory=lambda: client,
        clock=lambda: now[0],
    )
    for code in ("000001", "000002", "000003"):
        service.research(code=code, name="测试公司", focus="finance")

    now[0] += 301
    service.research(code="000004", name="测试公司", focus="finance")

    assert list(service._cache) == [("000004", "测试公司", "finance", "")]


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"code": "", "name": ""}, "股票"),
        ({"code": "600519", "name": "贵州茅台", "focus": "unknown"}, "研究范围"),
        ({"code": "600519", "name": "贵州茅台", "question": "x" * 201}, "问题"),
    ],
)
def test_input_validation_uses_product_language(kwargs: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        StockDeepResearchService(client_factory=FakeClient).research(**kwargs)


def test_total_generic_failure_raises_sanitized_unavailable_error() -> None:
    client = FakeClient(failures={
        "basicinfo",
        "business",
        "management",
        "finance",
        "industry",
        "consensus",
        "report",
        "market",
        "event",
        "announcement",
        "news",
    })
    with pytest.raises(IwencaiError, match="暂时不可用") as caught:
        StockDeepResearchService(client_factory=lambda: client).research(
            code="600519",
            name="贵州茅台",
        )

    for forbidden in ("gateway", "trace_id", "secret", "RuntimeError"):
        assert forbidden not in str(caught.value)


@pytest.mark.parametrize(
    "error_type",
    [IwencaiConfigurationError, IwencaiGatewayError],
)
def test_zero_success_preserves_stable_upstream_error_type(
    error_type: type[IwencaiError],
) -> None:
    client = AlwaysFailingClient(error_type)

    with pytest.raises(error_type) as caught:
        StockDeepResearchService(client_factory=lambda: client).research(
            code="600519",
            name="贵州茅台",
        )

    for forbidden in ("gateway", "trace", "secret", "/private/path"):
        assert forbidden not in str(caught.value).casefold()
