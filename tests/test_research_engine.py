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
        return self.results.get(capability, default_capability_result(capability))


def default_capability_result(capability: str) -> dict[str, object]:
    rows = {
        "index": {"指数简称": "上证指数", "最新点位": 3520.1, "涨跌幅": "0.6%"},
        "macro": {"指标名称": "制造业PMI", "最新值": 50.4, "公布日期": "20260701"},
        "sector_selector": {"板块名称": "机器人概念", "热度排名": 2, "成交额": 98_600_000_000},
        "news": {"标题": "市场风险偏好改善", "发布日期": "20260714"},
        "event": {"业绩预告类型": "预增", "公告日期": "20260714"},
        "announcement": {"公告标题": "季度经营数据公告", "公告日期": "20260714"},
        "consensus": {"预测净利润[2027]": 320_000_000, "机构评级": "增持"},
        "market": {"收盘价": 18.6, "成交量": 86_000_000, "交易日期": "20260714"},
        "finance": {"营业收入[2025]": 5_100_000_000, "归母净利润[2025]": 162_000_000},
        "business": {"主营产品": "核心产品", "竞争对手": "主要同行"},
        "astock_selector": {
            "股票代码": "603278",
            "股票简称": "大业股份",
            "净利润同比增长率": "18.6%",
        },
    }
    return {"datas": [rows[capability]]}


def stock_research_fixture() -> dict[str, dict[str, object]]:
    return {
        "finance": {
            "datas": [
                {
                    "股票代码": "603278",
                    "股票简称": "大业股份",
                    "最新价": 8.61,
                    "涨跌幅": "1.06%",
                    "营业收入[2025]": 5_100_000_000,
                    "营业收入[2024]": 4_700_000_000,
                    "归母净利润[2025]": 162_000_000,
                    "经营现金流[2025]": 91_000_000,
                    "净资产收益率ROE[2025]": "7.8%",
                }
            ]
        },
        "business": {
            "datas": [
                {
                    "股票代码": "603278",
                    "主营产品": "胎圈钢丝、钢帘线",
                    "业务范围": "橡胶骨架材料研发与制造",
                    "竞争对手": "江苏兴达、贝卡尔特",
                }
            ]
        },
        "consensus": {
            "datas": [
                {
                    "股票代码": "603278",
                    "预测净利润中值[2026]": 265_000_000,
                    "预测净利润中值[2027]": 338_000_000,
                }
            ]
        },
        "event": {
            "datas": [
                {
                    "股票代码": "603278",
                    "营业收入同比增长率[2026一季]": "12.4%",
                    "归母净利润同比增长率[2026一季]": "-8.7%",
                    "公告日期": "20260428",
                }
            ]
        },
    }


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
    fixture = stock_research_fixture()
    service = ResearchWorkspaceService(
        client_factory=lambda: FakeClient(
            results=fixture
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


def test_identity_only_capability_is_reported_insufficient() -> None:
    service = ResearchWorkspaceService(
        client_factory=lambda: FakeClient(
            results={
                "consensus": {
                    "datas": [
                        {
                            "股票代码": "603278",
                            "股票简称": "大业股份",
                            "最新价": 8.61,
                        }
                    ]
                }
            }
        )
    )

    result = service.research(
        "stock", ResearchContext(code="603278", name="大业股份")
    )

    consensus = next(item for item in result.details if item.section == "机构预期")
    assert consensus.status == "insufficient"
    assert "大业股份 · 机构预期" in result.missing_sections


def test_stock_findings_use_distinct_research_evidence() -> None:
    service = ResearchWorkspaceService(
        client_factory=lambda: FakeClient(results=stock_research_fixture())
    )

    result = service.research(
        "stock", ResearchContext(code="603278", name="大业股份")
    )

    payload = result.to_public_dict()
    serialized = json.dumps(payload, ensure_ascii=False)
    assert "营业收入" in serialized
    assert "主营产品" in serialized
    assert "2027" in serialized
    assert len({item.summary for item in result.findings}) == len(result.findings)
    for finding in result.findings:
        assert not finding.summary.startswith("股票代码")


def test_stock_front_page_prioritizes_risk_and_uses_decision_titles() -> None:
    service = ResearchWorkspaceService(
        client_factory=lambda: FakeClient(results=stock_research_fixture())
    )

    result = service.research(
        "stock", ResearchContext(code="603278", name="大业股份")
    )

    assert [item.title for item in result.findings] == [
        "最新事件",
        "财务方向",
        "机构预期",
    ]
    assert "净利润同比" in result.findings[0].summary
    assert "-8.7%" in result.findings[0].summary
    assert "收入" in result.findings[1].summary
    assert "增长轨道" in result.findings[2].summary
    assert result.verdict.startswith("大业股份：")
    assert "-8.7%" in result.primary_risk


def test_front_page_deduplicates_identical_fact_fingerprints() -> None:
    duplicate = {"datas": [{"公告日期": "20260428"}]}
    service = ResearchWorkspaceService(
        client_factory=lambda: FakeClient(
            results={
                "sector_selector": {
                    "datas": [{"板块名称": "机器人概念", "热度排名": 1}]
                },
                "astock_selector": {"datas": []},
                "event": duplicate,
                "news": duplicate,
            }
        )
    )

    result = service.research("opportunity", ResearchContext(sector="机器人"))

    fingerprints = [
        tuple((fact.label, fact.value) for fact in item.facts)
        for item in result.findings
    ]
    assert len(fingerprints) == len(set(fingerprints))
