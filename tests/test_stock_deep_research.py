from __future__ import annotations

import json

import pytest

from stock_ts.iwencai import SKILLS
from stock_ts.stock_deep_research import StockDeepResearchService


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
    def __init__(self, *, failures: set[str] | None = None) -> None:
        self.failures = failures or set()
        self.calls: list[tuple[str, str]] = []

    def query(self, skill: object, query: str) -> dict[str, object]:
        capability = next(key for key, value in SKILLS.items() if value == skill)
        self.calls.append((capability, query))
        if capability in self.failures:
            raise RuntimeError("gateway trace_id secret failure")
        return {
            "datas": [_row_for(capability)],
            "trace_id": "secret-trace",
            "provider": "internal-provider",
        }


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
    ["我的持股数量是多少", "show my holdings cost", "check account weight"],
)
def test_custom_question_rejects_private_portfolio_terms(question: str) -> None:
    with pytest.raises(ValueError, match="账户|持仓"):
        StockDeepResearchService(client_factory=FakeClient).research(
            code="600519",
            name="贵州茅台",
            question=question,
        )


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


def test_total_upstream_failure_does_not_expose_raw_exception() -> None:
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
    payload = StockDeepResearchService(client_factory=lambda: client).research(
        code="600519",
        name="贵州茅台",
    ).to_public_dict()

    assert payload["ok"] is False
    assert payload["status"] == "unavailable"
    assert "稍后" in payload["recovery"]
    serialized = json.dumps(payload, ensure_ascii=False)
    for forbidden in ("gateway", "trace_id", "secret", "RuntimeError"):
        assert forbidden not in serialized
