from stock_ts.iwencai import SKILLS
from stock_ts.research_engine import (
    ResearchContext,
    ResearchWorkspaceResult,
    ResearchWorkspaceService,
)
from stock_ts.research_method import (
    RESEARCH_CONTRACT_VERSION,
    attach_method_section,
    build_method_section,
    method_for,
)


def test_four_workspaces_use_distinct_professional_methods() -> None:
    methods = {
        module: method_for(module) for module in ("market", "portfolio", "stock", "opportunity")
    }

    assert len({tuple(item.key for item in method.dimensions) for method in methods.values()}) == 4
    assert "breadth" in {item.key for item in methods["market"].dimensions}
    assert "correlation" in {item.key for item in methods["portfolio"].dimensions}
    assert "expectation_gap" in {item.key for item in methods["stock"].dimensions}
    assert {"theme_gate", "company_gate", "price_gate", "risk_gate"} <= {
        item.key for item in methods["opportunity"].dimensions
    }
    assert all(item.comparison_basis for method in methods.values() for item in method.dimensions)


def test_missing_method_dimensions_are_unknown_without_scores() -> None:
    section = build_method_section(
        "stock",
        ready_keys={"finance"},
        missing_keys={"industry", "consensus", "market"},
    )
    payload = section.to_public_dict()
    unknown = [item for item in payload["items"] if item["status"] == "unknown"]

    assert unknown
    assert all(fact["label"] != "评分" for item in unknown for fact in item["facts"])
    assert all("待补" in item["risk"] for item in unknown)


def test_stock_method_requires_support_counter_expectation_and_invalidation() -> None:
    method = method_for("stock")

    assert method.required_outputs == (
        "研究假设",
        "最强支持",
        "最大反证",
        "预期差",
        "确认条件",
        "失效条件",
    )


def test_method_section_attaches_once_and_exposes_contract_version() -> None:
    result = ResearchWorkspaceResult(
        ok=True,
        status="partial",
        module="market",
        generated_at="2026-07-17T07:00:00+08:00",
        verdict="市场事实待复核",
        action="只记录事实",
        primary_risk="宽度不足",
    )

    enriched = attach_method_section(result, ready_keys={"index", "breadth"})
    enriched_again = attach_method_section(enriched, ready_keys={"index", "breadth"})
    payload = enriched_again.to_public_dict()

    assert RESEARCH_CONTRACT_VERSION == "2026-07-17.multi-lens.v1"
    assert [section["key"] for section in payload["module_sections"]].count(
        "professional-method"
    ) == 1
    assert payload["research_contract_version"] == RESEARCH_CONTRACT_VERSION


def test_external_workspace_attaches_method_from_capability_outcomes() -> None:
    class PartialMarketClient:
        def query(self, skill: object, _query: str) -> dict[str, object]:
            capability = next(key for key, value in SKILLS.items() if value == skill)
            if capability != "index":
                raise RuntimeError("upstream failed")
            return {
                "datas": [
                    {
                        "指数简称": "上证指数",
                        "最新点位": 3520.1,
                        "涨跌幅": "0.6%",
                    }
                ]
            }

    result = ResearchWorkspaceService(
        client_factory=PartialMarketClient,
    ).research("market", ResearchContext())
    payload = result.to_public_dict()
    method_sections = [
        section for section in payload["module_sections"] if section["key"] == "professional-method"
    ]

    assert len(method_sections) == 1
    statuses = {item["name"]: item["status"] for item in method_sections[0]["items"]}
    assert statuses["指数趋势"] == "ready"
    assert statuses["宏观与政策"] == "unknown"
    assert payload["research_contract_version"] == RESEARCH_CONTRACT_VERSION


def test_external_failed_bundle_has_no_ready_method_dimensions() -> None:
    class FailedMarketClient:
        def query(self, _skill: object, _query: str) -> dict[str, object]:
            raise RuntimeError("upstream failed")

    result = ResearchWorkspaceService(
        client_factory=FailedMarketClient,
    ).research("market", ResearchContext())
    method_section = next(
        section
        for section in result.to_public_dict()["module_sections"]
        if section["key"] == "professional-method"
    )

    assert {item["status"] for item in method_section["items"]} == {"unknown"}
