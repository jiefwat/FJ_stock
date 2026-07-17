import json

from stock_ts.iwencai import SKILLS
from stock_ts.providers.sample import SampleDataProvider
from stock_ts.research_engine import (
    ResearchContext,
    ResearchWorkspaceResult,
    ResearchWorkspaceService,
)
from stock_ts.research_fallback import build_local_research
from stock_ts.research_method import (
    RESEARCH_CONTRACT_VERSION,
    attach_method_section,
    build_method_section,
    method_for,
)


class CompleteStockClient:
    def __init__(self, *, negative: bool = False) -> None:
        self.negative = negative

    def query(self, skill: object, _query: str) -> dict[str, object]:
        capability = next(key for key, value in SKILLS.items() if value == skill)
        growth = "-25%" if self.negative else "18%"
        rating = "减持" if self.negative else "增持"
        event_type = "预亏" if self.negative else "预增"
        price_change = "-4.5%" if self.negative else "2.5%"
        revision_key = "盈利预测下修" if self.negative else "盈利预测上调"
        revision_value = "-20%" if self.negative else "12%"
        flow_key = "主力资金净流出" if self.negative else "主力资金净流入"
        rows = {
            "finance": {
                "营业收入[2025]": 5_100_000_000,
                "归母净利润[2025]": 162_000_000,
                "归母净利润同比增长率[2025]": growth,
            },
            "business": {"主营产品": "核心产品", "竞争对手": "主要同行"},
            "consensus": {
                "预测净利润[2027]": 320_000_000,
                "机构评级": rating,
                revision_key: revision_value,
            },
            "event": {"业绩预告类型": event_type, "公告日期": "20260714"},
            "market": {
                "收盘价": 18.6,
                "涨跌幅[20260714]": price_change,
                "成交量": 86_000_000,
                "交易日期": "20260714",
                flow_key: 20_000_000,
            },
            "industry": {"行业名称": "金属制品", "行业排名": 8, "行业市盈率": 24.6},
            "announcement": {"公告标题": "季度经营数据公告", "公告日期": "20260714"},
            "report": {
                "title": "盈利修复仍需观察",
                "summary": "关注成本和海外需求",
                "publish_date": "20260715",
            },
        }
        return {"datas": [rows[capability]]}


class BoundaryStockClient(CompleteStockClient):
    def query(self, skill: object, query: str) -> dict[str, object]:
        capability = next(key for key, value in SKILLS.items() if value == skill)
        payload = super().query(skill, query)
        row = payload["datas"][0]
        if capability == "finance":
            row["归母净利润同比增长率[2025]"] = "10%-20%"
        elif capability == "business":
            row["主营产品"] = "成本承压缓解"
        elif capability == "consensus":
            row["盈利预测下修风险解除"] = "风险已解除"
        return payload


def _method_section(payload: dict[str, object]) -> dict[str, object]:
    return next(
        section for section in payload["module_sections"] if section["key"] == "professional-method"
    )


def _local_stock_payload() -> dict[str, object]:
    return build_local_research(
        "stock",
        ResearchContext(code="600519", name="贵州茅台"),
        provider=SampleDataProvider(),
    ).to_public_dict()


def _external_stock_payload(*, negative: bool = False) -> dict[str, object]:
    return (
        ResearchWorkspaceService(
            client_factory=lambda: CompleteStockClient(negative=negative)
        )
        .research(
            "stock",
            ResearchContext(code="600519", name="贵州茅台"),
        )
        .to_public_dict()
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
    unknown = [
        item
        for item in payload["items"]
        if item["kind"] == "method_dimension" and item["status"] == "unknown"
    ]

    assert unknown
    assert all(fact["label"] != "评分" for item in unknown for fact in item["facts"])
    assert all("待补" in item["risk"] for item in unknown)


def test_local_and_external_method_dimensions_expose_structured_public_fields() -> None:
    for payload in (_local_stock_payload(), _external_stock_payload()):
        dimensions = [
            item for item in _method_section(payload)["items"] if item["kind"] == "method_dimension"
        ]
        unknown = [item for item in dimensions if item["status"] == "unknown"]

        assert dimensions
        assert len({item["key"] for item in dimensions}) == len(dimensions)
        assert all("score" in item and "recovery" in item for item in dimensions)
        assert unknown
        assert all(item["score"] is None for item in unknown)
        assert all(item["recovery"] for item in unknown)


def test_local_stock_method_maps_only_observed_evidence_dimensions() -> None:
    dimensions = {
        item["key"]: item
        for item in _method_section(_local_stock_payload())["items"]
        if item["kind"] == "method_dimension"
    }

    assert any(item["status"] != "unknown" for item in dimensions.values())
    assert dimensions["price"]["status"] in {"ready", "partial"}
    assert dimensions["identity"]["status"] == "unknown"


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


def test_local_and_external_stock_methods_emit_six_structured_outputs() -> None:
    expected = ["研究假设", "最强支持", "最大反证", "预期差", "确认条件", "失效条件"]

    for payload in (_local_stock_payload(), _external_stock_payload()):
        outputs = [
            item for item in _method_section(payload)["items"] if item["kind"] == "method_output"
        ]

        assert [item["name"] for item in outputs] == expected
        assert all(item["summary"] for item in outputs)
        assert all(item["status"] in {"partial", "unknown"} for item in outputs)


def test_external_stock_outputs_change_with_opposite_public_facts() -> None:
    positive = _external_stock_payload()
    negative = _external_stock_payload(negative=True)
    positive_outputs = [
        item
        for item in _method_section(positive)["items"]
        if item["kind"] == "method_output"
    ]
    negative_outputs = [
        item
        for item in _method_section(negative)["items"]
        if item["kind"] == "method_output"
    ]
    positive_text = json.dumps(positive_outputs, ensure_ascii=False)
    negative_text = json.dumps(negative_outputs, ensure_ascii=False)
    positive_by_name = {item["name"]: item for item in positive_outputs}
    negative_by_name = {item["name"]: item for item in negative_outputs}
    positive_support = json.dumps(positive_by_name["最强支持"], ensure_ascii=False)
    negative_support = json.dumps(negative_by_name["最强支持"], ensure_ascii=False)
    negative_counter = json.dumps(negative_by_name["最大反证"], ensure_ascii=False)

    assert positive_outputs != negative_outputs
    assert "18%" in positive_text or "预增" in positive_text
    assert "-25%" in negative_text or "预亏" in negative_text
    assert any(term in positive_support for term in ("18%", "预增", "上调", "净流入"))
    assert all(
        term not in negative_support for term in ("-25%", "预亏", "下修", "净流出")
    )
    assert any(term in negative_counter for term in ("-25%", "预亏", "下修", "净流出"))
    support_facts = {
        (fact["label"], fact["value"])
        for fact in negative_by_name["最强支持"]["facts"]
    }
    counter_facts = {
        (fact["label"], fact["value"])
        for fact in negative_by_name["最大反证"]["facts"]
    }
    assert support_facts.isdisjoint(counter_facts)


def test_direction_classifier_does_not_treat_ranges_or_relief_as_negative() -> None:
    payload = (
        ResearchWorkspaceService(client_factory=BoundaryStockClient)
        .research("stock", ResearchContext(code="600519", name="贵州茅台"))
        .to_public_dict()
    )
    outputs = {
        item["name"]: item
        for item in _method_section(payload)["items"]
        if item["kind"] == "method_output"
    }
    counter_text = json.dumps(outputs["最大反证"], ensure_ascii=False)

    assert "10%-20%" not in counter_text
    assert "成本承压缓解" not in counter_text
    assert "下修风险解除" not in counter_text


def test_local_stock_outputs_anchor_actual_result_judgment_and_evidence() -> None:
    payload = _local_stock_payload()
    outputs = [
        item
        for item in _method_section(payload)["items"]
        if item["kind"] == "method_output"
    ]
    output_text = json.dumps(outputs, ensure_ascii=False)

    assert payload["verdict"] in output_text
    assert payload["action"] in output_text
    assert payload["primary_risk"] in output_text
    assert any(item["summary"] in output_text for item in payload["findings"])


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


def test_opportunity_selector_only_does_not_satisfy_company_or_price_gates() -> None:
    class SelectorOnlyClient:
        def query(self, skill: object, _query: str) -> dict[str, object]:
            capability = next(key for key, value in SKILLS.items() if value == skill)
            if capability != "astock_selector":
                raise RuntimeError("upstream failed")
            return {
                "datas": [
                    {
                        "股票代码": "600001",
                        "股票简称": "候选一",
                        "净利润同比增长率": "18%",
                    }
                ]
            }

    payload = (
        ResearchWorkspaceService(client_factory=SelectorOnlyClient)
        .research(
            "opportunity",
            ResearchContext(),
        )
        .to_public_dict()
    )
    dimensions = {
        item["name"]: item
        for item in _method_section(payload)["items"]
        if item["kind"] == "method_dimension"
    }

    assert dimensions["公司质量"]["status"] != "ready"
    assert dimensions["价格确认"]["status"] != "ready"
