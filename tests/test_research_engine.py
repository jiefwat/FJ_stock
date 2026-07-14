from __future__ import annotations

import json

from stock_ts.iwencai import SKILLS
from stock_ts.research_engine import (
    ResearchContext,
    ResearchTarget,
    ResearchWorkspaceService,
    build_workspace_queries,
    workspace_capabilities,
)


class FakeClient:
    def __init__(
        self,
        *,
        results: dict[str, dict[str, object]] | None = None,
        failures: set[str] | None = None,
    ) -> None:
        self.results = results or {}
        self.failures = failures or set()
        self.calls: list[tuple[str, str]] = []

    def query(self, skill: object, query: str) -> dict[str, object]:
        capability = next(key for key, value in SKILLS.items() if value == skill)
        self.calls.append((capability, query))
        if capability in self.failures:
            raise RuntimeError("upstream failed")
        return self.results.get(
            capability,
            {"datas": [{"结论": f"{capability}数据可用", "状态": "已更新"}]},
        )


def test_each_workspace_has_a_fixed_capability_bundle() -> None:
    assert workspace_capabilities("market") == (
        "index",
        "macro",
        "sector_selector",
        "news",
    )
    assert workspace_capabilities("portfolio") == (
        "event",
        "announcement",
        "consensus",
        "market",
    )
    assert workspace_capabilities("stock") == (
        "finance",
        "business",
        "consensus",
        "event",
    )
    assert workspace_capabilities("opportunity") == (
        "sector_selector",
        "astock_selector",
        "event",
        "news",
    )


def test_unknown_workspace_is_rejected() -> None:
    try:
        workspace_capabilities("unknown")
    except ValueError as exc:
        assert str(exc) == "不支持的研究模块。"
    else:
        raise AssertionError("unknown workspace should be rejected")


def test_portfolio_queries_only_include_target_identity() -> None:
    context = ResearchContext(
        holdings=(
            ResearchTarget(code="600519", name="贵州茅台"),
            ResearchTarget(code="000001", name="平安银行"),
        ),
    )

    requests = build_workspace_queries("portfolio", context)

    assert len(requests) == 8
    query_text = " ".join(item.query for item in requests)
    assert "贵州茅台" in query_text
    assert "600519" in query_text
    for private_term in ("股数", "成本", "权重", "账户", "Cookie"):
        assert private_term not in query_text


def test_portfolio_research_is_capped_to_three_holdings() -> None:
    context = ResearchContext(
        holdings=tuple(
            ResearchTarget(code=f"60000{index}", name=f"股票{index}")
            for index in range(5)
        )
    )

    requests = build_workspace_queries("portfolio", context)

    assert len(requests) == 12
    assert "股票3" not in " ".join(item.query for item in requests)


def test_stock_queries_require_a_stock_identity() -> None:
    try:
        build_workspace_queries("stock", ResearchContext())
    except ValueError as exc:
        assert str(exc) == "请输入股票代码或名称。"
    else:
        raise AssertionError("stock workspace should require an identity")


def test_service_returns_supplier_neutral_partial_result() -> None:
    client = FakeClient(
        results={"finance": {"datas": [{"收入": "同比增长", "现金流": "改善"}]}},
        failures={"event"},
    )
    service = ResearchWorkspaceService(client_factory=lambda: client)

    result = service.research(
        "stock",
        ResearchContext(code="600519", name="贵州茅台"),
    )
    payload = result.to_public_dict()

    assert payload["ok"] is True
    assert payload["status"] == "partial"
    assert payload["findings"]
    serialized = json.dumps(payload, ensure_ascii=False)
    for forbidden in ("event", "skill", "问财", "iWencai", "同花顺", "trace_id"):
        assert forbidden not in serialized


def test_service_marks_all_failed_bundle_unavailable() -> None:
    service = ResearchWorkspaceService(
        client_factory=lambda: FakeClient(
            failures={"index", "macro", "sector_selector", "news"}
        )
    )

    result = service.research("market", ResearchContext())

    assert result.status == "unavailable"
    assert result.ok is False
    assert result.findings == ()
    assert result.action == "稍后重新分析；当前不沿用旧结论。"


def test_service_reuses_unexpired_result() -> None:
    client = FakeClient()
    service = ResearchWorkspaceService(client_factory=lambda: client, cache_ttl=300)

    first = service.research("market", ResearchContext())
    second = service.research("market", ResearchContext())

    assert second is first
    assert len(client.calls) == 4


def test_refresh_bypasses_workspace_cache() -> None:
    client = FakeClient()
    service = ResearchWorkspaceService(client_factory=lambda: client, cache_ttl=300)

    first = service.research("market", ResearchContext())
    second = service.research("market", ResearchContext(), refresh=True)

    assert second is not first
    assert len(client.calls) == 8


def test_public_result_caps_findings_and_fact_fields() -> None:
    rows = [
        {f"字段{column}": f"第{row}行" for column in range(8)}
        for row in range(8)
    ]
    service = ResearchWorkspaceService(
        client_factory=lambda: FakeClient(
            results={
                "finance": {"datas": rows},
                "business": {"datas": rows},
                "consensus": {"datas": rows},
                "event": {"datas": rows},
            }
        )
    )

    payload = service.research(
        "stock", ResearchContext(code="600519", name="贵州茅台")
    ).to_public_dict()

    assert len(payload["findings"]) == 3
    assert all(len(item["facts"]) <= 4 for item in payload["findings"])


def test_public_result_drops_internal_metadata_from_dynamic_rows() -> None:
    service = ResearchWorkspaceService(
        client_factory=lambda: FakeClient(
            results={
                "finance": {
                    "datas": [
                        {
                            "股票简称": "贵州茅台",
                            "trace_id": "internal-trace",
                            "skill_id": "internal-capability",
                            "provider": "internal-provider",
                            "Authorization": "Bearer secret",
                            "来源": "IWENCAI",
                        }
                    ]
                }
            }
        )
    )

    payload = service.research(
        "stock", ResearchContext(code="600519", name="贵州茅台")
    ).to_public_dict()
    serialized = json.dumps(payload, ensure_ascii=False).lower()

    for forbidden in (
        "trace_id",
        "internal-trace",
        "skill_id",
        "internal-capability",
        "provider",
        "authorization",
        "bearer secret",
        "iwencai",
    ):
        assert forbidden not in serialized


def test_portfolio_front_page_represents_each_capped_holding() -> None:
    service = ResearchWorkspaceService(client_factory=lambda: FakeClient())
    context = ResearchContext(
        holdings=(
            ResearchTarget(code="600519", name="贵州茅台"),
            ResearchTarget(code="000001", name="平安银行"),
            ResearchTarget(code="300750", name="宁德时代"),
        )
    )

    payload = service.research("portfolio", context).to_public_dict()

    assert [item["target"] for item in payload["findings"]] == [
        "贵州茅台",
        "平安银行",
        "宁德时代",
    ]
