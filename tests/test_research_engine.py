from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from stock_ts.iwencai import SKILLS
from stock_ts.research_engine import (
    ResearchContext,
    ResearchDetail,
    ResearchFact,
    ResearchFinding,
    ResearchModuleItem,
    ResearchModuleSection,
    ResearchTarget,
    ResearchWorkspaceResult,
    ResearchWorkspaceService,
    build_workspace_queries,
    workspace_capabilities,
)


def test_workspace_result_exposes_complete_product_contract() -> None:
    result = ResearchWorkspaceResult(
        ok=True,
        status="complete",
        module="market",
        generated_at="2026-07-15T07:20:00+08:00",
        verdict="趋势偏强",
        action="保持风险预算",
        primary_risk="成交缩量",
        subject_count=3,
        coverage_ready=3,
        coverage_total=4,
        module_items=(
            ResearchModuleItem(
                kind="index",
                code="000001.SH",
                name="上证指数",
                label="短中期趋势",
                summary="5日上行，20日待确认",
                risk="跌破20日趋势则失效",
            ),
        ),
    )

    payload = result.to_public_dict()

    assert payload["subject_count"] == 3
    assert payload["coverage"] == {"ready": 3, "total": 4}
    assert payload["delivery"] == "live"
    assert payload["as_of"] == "2026-07-15T07:20:00+08:00"
    assert payload["module_items"][0]["kind"] == "index"


def test_workspace_result_exposes_decision_label_and_sections() -> None:
    result = ResearchWorkspaceResult(
        ok=True,
        status="complete",
        module="market",
        generated_at="2026-07-15T09:30:00+08:00",
        verdict="指数修复，但短周期仍有分化。",
        action="关注主线持续性。",
        primary_risk="修复未扩散。",
        decision_label="修复中",
        module_sections=(
            ResearchModuleSection(
                key="market-themes",
                title="当前主题",
                conclusion="制造与创新药靠前。",
            ),
        ),
    )

    payload = result.to_public_dict()

    assert payload["decision_label"] == "修复中"
    assert payload["module_sections"][0]["key"] == "market-themes"


def test_public_contract_is_field_aware_about_provider_brands() -> None:
    result = ResearchWorkspaceResult(
        ok=True,
        status="complete",
        module="stock",
        generated_at="2026-07-15T09:30:00+08:00",
        verdict="来自问财的结论",
        action="使用同花顺数据复核",
        primary_risk="iWencai服务暂不可用",
        missing_sections=("问财能力待补",),
        decision_label="同花顺数据判断",
        module_items=(
            ResearchModuleItem(
                kind="holding",
                code="300033",
                name="同花顺",
                label="重点持仓",
                summary="同花顺：公司经营证据已更新",
                facts=(
                    ResearchFact(label="股票简称", value="同花顺"),
                    ResearchFact(
                        label="所属概念", value="CPO、同花顺特色分类"
                    ),
                ),
            ),
            ResearchModuleItem(
                kind="candidate",
                name="示例股",
                label="同花顺特色分类",
            ),
            ResearchModuleItem(
                kind="theme",
                name="研究服务",
                label="数据服务",
            ),
        ),
        details=(
            ResearchDetail(
                section="公司研究",
                target="同花顺",
                status="ready",
                findings=(
                    ResearchFinding(
                        title="公司结论",
                        summary="同花顺：公司基本面稳定",
                        target="同花顺",
                        facts=(
                            ResearchFact(label="股票简称", value="同花顺"),
                            ResearchFact(
                                label="所属行业", value="软件、问财特色分类"
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )

    payload = result.to_public_dict()
    serialized = json.dumps(payload, ensure_ascii=False)

    assert payload["module_items"][0]["name"] == "同花顺"
    assert payload["module_items"][0]["summary"].startswith("同花顺：")
    assert payload["module_items"][0]["facts"][0]["value"] == "同花顺"
    assert payload["module_items"][0]["facts"][1]["value"] == "CPO"
    assert payload["module_items"][1]["label"] == "主题待确认"
    assert payload["module_items"][2]["name"] == "研究服务"
    assert payload["module_items"][2]["label"] == "数据服务"
    assert payload["details"][0]["target"] == "同花顺"
    assert payload["details"][0]["findings"][0]["facts"][1]["value"] == "软件"
    for metadata in ("来自问财", "同花顺数据", "iWencai服务", "问财特色分类"):
        assert metadata not in serialized


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


class PortfolioThemeClient(FakeClient):
    def query(self, skill: object, query: str) -> dict[str, object]:
        capability = next(key for key, value in SKILLS.items() if value == skill)
        self.calls.append((capability, query))
        if capability == "industry":
            return {
                "datas": [
                    {
                        "行业名称": "半导体",
                        "行业排名": 3,
                        "同行公司": "行业样本",
                    }
                ]
            }
        if capability == "market":
            change = 5.2 if "芯片强" in query else -3.4
            return {
                "datas": [
                    {
                        "收盘价": 18.6,
                        "涨跌幅[20260715]": change,
                        "成交额[20260715]": 1_200_000_000,
                    }
                ]
            }
        return default_capability_result(capability)


class PortfolioMultiThemeClient(FakeClient):
    def query(self, skill: object, query: str) -> dict[str, object]:
        capability = next(key for key, value in SKILLS.items() if value == skill)
        self.calls.append((capability, query))
        if capability == "industry":
            concepts = (
                [
                    "CPO",
                    "CPO概念",
                    "cpo",
                    "PCB概念",
                    "5G",
                    "同花顺特色分类",
                ]
                if "主题甲" in query
                else ["CPO", "光模块", "算力"]
            )
            return {"datas": [{"所属概念": concepts}]}
        if capability == "market":
            change = 5.0 if "主题甲" in query else -3.0
            return {
                "datas": [
                    {
                        "收盘价": 18.6,
                        "涨跌幅[20260715]": change,
                        "成交额[20260715]": 1_200_000_000,
                    }
                ]
            }
        return default_capability_result(capability)


class PortfolioEssenceClient(FakeClient):
    def query(self, skill: object, query: str) -> dict[str, object]:
        capability = next(key for key, value in SKILLS.items() if value == skill)
        self.calls.append((capability, query))
        if capability == "industry":
            name = query.split()[0]
            theme = "CPO" if name.startswith("共享") else name.replace("持仓", "主题")
            return {"datas": [{"所属概念": [theme]}]}
        if capability == "market":
            change = 5.0 if "共享强" in query else -3.0 if "共享弱" in query else 0.2
            return {
                "datas": [
                    {
                        "收盘价": 18.6,
                        "涨跌幅[20260715]": change,
                        "成交额[20260715]": 1_200_000_000,
                    }
                ]
            }
        return default_capability_result(capability)


def default_capability_result(capability: str) -> dict[str, object]:
    rows = {
        "index": {"指数简称": "上证指数", "最新点位": 3520.1, "涨跌幅": "0.6%"},
        "breadth": {"上涨家数": 3200, "下跌家数": 2100, "平盘家数": 100},
        "macro": {"指标名称": "制造业PMI", "最新值": 50.4, "公布日期": "20260701"},
        "sector_selector": {"板块名称": "机器人概念", "热度排名": 2, "成交额": 98_600_000_000},
        "hot_stock": {
            "股票代码": "603278",
            "股票简称": "大业股份",
            "涨跌幅": "1.06%",
            "成交额": 1_000_000_000,
            "所属概念": ["机器人概念"],
        },
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
        "industry": {"行业名称": "金属制品", "行业排名": 8, "行业市盈率": 24.6},
        "report": {
            "title": "盈利修复仍需观察",
            "summary": "关注成本和海外需求",
            "publish_date": "20260715",
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
                    "营业收入同比增长率[2025]": "8.5%",
                    "归母净利润[2025]": 162_000_000,
                    "归母净利润同比增长率[2025]": "18.6%",
                    "经营现金流[2025]": 91_000_000,
                    "净资产收益率ROE[2025]": "7.8%",
                    "资产负债率[2025]": "58.2%",
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
        "breadth",
        "sector_selector",
        "hot_stock",
        "macro",
        "news",
    )
    assert workspace_capabilities("portfolio") == (
        "event",
        "consensus",
        "market",
        "industry",
    )
    assert workspace_capabilities("stock") == (
        "finance",
        "business",
        "consensus",
        "event",
        "market",
        "industry",
        "announcement",
        "report",
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


def test_portfolio_research_covers_holdings_within_twenty_limit() -> None:
    context = ResearchContext(
        holdings=tuple(
            ResearchTarget(code=f"60000{index}", name=f"股票{index}")
            for index in range(5)
        )
    )

    requests = build_workspace_queries("portfolio", context)

    assert len(requests) == 20
    assert "股票4" in " ".join(item.query for item in requests)


def test_portfolio_builds_four_capabilities_for_all_twenty_holdings() -> None:
    holdings = tuple(
        ResearchTarget(code=f"600{index:03d}", name=f"持仓{index}")
        for index in range(25)
    )

    requests = build_workspace_queries("portfolio", ResearchContext(holdings=holdings))

    assert len(requests) == 20 * 4
    assert {request.capability for request in requests} == {
        "event",
        "consensus",
        "market",
        "industry",
    }
    assert "持仓19" in " ".join(item.query for item in requests)
    assert "持仓20" not in " ".join(item.query for item in requests)


def test_stock_research_uses_eight_dimensions() -> None:
    requests = build_workspace_queries(
        "stock", ResearchContext(code="603278", name="大业股份")
    )

    assert [request.capability for request in requests] == [
        "finance",
        "business",
        "consensus",
        "event",
        "market",
        "industry",
        "announcement",
        "report",
    ]


def test_opportunity_keeps_ten_candidate_module_items() -> None:
    rows = [
        {
            "股票代码": f"60{index:04d}",
            "股票简称": f"候选{index}",
            "净利润同比增长率": f"{index + 10}%",
            "成交额": 1_000_000_000 + index,
        }
        for index in range(10)
    ]
    client = FakeClient(results={"astock_selector": {"datas": rows}})

    result = ResearchWorkspaceService(client_factory=lambda: client).research(
        "opportunity", ResearchContext(), refresh=True
    )

    candidates = [item for item in result.module_items if item.kind == "candidate"]
    assert len(candidates) == 10
    assert candidates[0].code == "600000"
    assert candidates[0].name == "候选0"
    assert candidates[0].risk


def test_stock_queries_require_a_stock_identity() -> None:
    try:
        build_workspace_queries("stock", ResearchContext())
    except ValueError as exc:
        assert str(exc) == "请输入股票代码或名称。"
    else:
        raise AssertionError("stock workspace should require an identity")


def test_market_queries_use_explicit_index_and_sector_shapes() -> None:
    requests = build_workspace_queries("market", ResearchContext())
    query_by_capability = {item.capability: item.query for item in requests}

    assert "上证指数" in query_by_capability["index"]
    assert "创业板指" in query_by_capability["index"]
    assert "前5" in query_by_capability["sector_selector"]
    assert "排序" in query_by_capability["sector_selector"]
    assert "排除融资融券" in query_by_capability["sector_selector"]
    assert "上涨家数" in query_by_capability["breadth"]
    assert "按成交额从高到低排序" in query_by_capability["hot_stock"]


def test_opportunity_selector_query_contains_parseable_conditions() -> None:
    requests = build_workspace_queries(
        "opportunity", ResearchContext(sector="机器人")
    )
    query_by_capability = {item.capability: item.query for item in requests}

    assert "机器人概念" in query_by_capability["sector_selector"]
    assert "净利润同比增长" in query_by_capability["astock_selector"]
    assert "成交额" in query_by_capability["astock_selector"]
    assert "前10" in query_by_capability["astock_selector"]
    assert "所属概念" in query_by_capability["astock_selector"]
    assert "所属行业" in query_by_capability["astock_selector"]
    default_requests = build_workspace_queries("opportunity", ResearchContext())
    default_astock = next(
        item.query for item in default_requests if item.capability == "astock_selector"
    )
    default_sector = next(
        item.query for item in default_requests if item.capability == "sector_selector"
    )
    assert "A股 A股" not in default_astock
    assert "概念板块" in default_sector
    assert "排除融资融券" in default_sector


def test_stock_service_is_complete_with_seven_of_eight_dimensions() -> None:
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
    assert payload["status"] == "complete"
    assert payload["findings"]
    serialized = json.dumps(payload, ensure_ascii=False)
    for forbidden in ("event", "skill", "问财", "iWencai", "同花顺", "trace_id"):
        assert forbidden not in serialized


def test_service_marks_all_failed_bundle_unavailable() -> None:
    service = ResearchWorkspaceService(
        client_factory=lambda: FakeClient(
            failures={
                "index",
                "breadth",
                "sector_selector",
                "hot_stock",
                "macro",
                "news",
            }
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
    assert len(client.calls) == 6


def test_refresh_bypasses_workspace_cache() -> None:
    client = FakeClient()
    service = ResearchWorkspaceService(client_factory=lambda: client, cache_ttl=300)

    first = service.research("market", ResearchContext())
    second = service.research("market", ResearchContext(), refresh=True)

    assert second is not first
    assert len(client.calls) == 12


def test_portfolio_cache_key_includes_every_analyzed_holding() -> None:
    client = FakeClient()
    service = ResearchWorkspaceService(client_factory=lambda: client, cache_ttl=300)
    shared = (
        ResearchTarget(code="600001", name="持仓一"),
        ResearchTarget(code="600002", name="持仓二"),
        ResearchTarget(code="600003", name="持仓三"),
    )

    service.research(
        "portfolio",
        ResearchContext(
            holdings=shared + (ResearchTarget(code="600004", name="持仓四"),)
        ),
    )
    service.research(
        "portfolio",
        ResearchContext(
            holdings=shared + (ResearchTarget(code="600005", name="持仓五"),)
        ),
    )

    assert len(client.calls) == 32


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
    assert "47.00 亿" in result.findings[1].summary
    assert "元" not in result.findings[1].summary
    assert "增长轨道" in result.findings[2].summary
    assert result.verdict.startswith("大业股份：")
    assert "-8.7%" in result.primary_risk


def test_front_page_deduplicates_identical_fact_fingerprints() -> None:
    duplicate = {
        "datas": [{"标题": "同一风险事件", "公告日期": "20260428"}]
    }
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


def test_market_and_opportunity_summaries_lead_with_decision_evidence() -> None:
    service = ResearchWorkspaceService(client_factory=lambda: FakeClient())

    market = service.research("market", ResearchContext())
    opportunity = service.research("opportunity", ResearchContext())

    assert market.findings[0].summary.startswith("上证指数")
    assert "最新点位" in market.findings[0].summary
    assert market.findings[1].summary.startswith("机器人概念")
    assert "热度排名" in market.findings[1].summary
    assert market.findings[2].summary.startswith("市场风险偏好改善")
    candidate = next(
        item for item in opportunity.findings if item.title == "候选线索"
    )
    assert candidate.summary.startswith("大业股份")
    assert "净利润同比" in candidate.summary
    assert not candidate.summary.startswith("股票代码")


def test_stock_primary_risk_prefers_latest_event_over_old_finance_period() -> None:
    fixture = stock_research_fixture()
    fixture["finance"] = {
        "datas": [
            {
                "归母净利润[20251231]": -134_712_000,
                "营业收入[20251231]": 5_026_000_000,
            }
        ]
    }
    service = ResearchWorkspaceService(
        client_factory=lambda: FakeClient(results=fixture)
    )

    result = service.research(
        "stock", ResearchContext(code="603278", name="大业股份")
    )

    assert "2026一季" in result.primary_risk
    assert "-8.7%" in result.primary_risk


def test_positive_risk_preference_news_does_not_become_primary_risk() -> None:
    client = FakeClient(
        results={
            "news": {
                "datas": [
                    {
                        "title": "政策预期改善市场风险偏好",
                        "summary": "成交仍需继续确认。",
                    }
                ]
            }
        }
    )

    result = ResearchWorkspaceService(client_factory=lambda: client).research(
        "market", ResearchContext()
    )

    assert result.primary_risk == "市场证据可能不同步，避免只按单一热点行动。"


def test_index_risk_names_the_affected_index() -> None:
    client = FakeClient(
        results={
            "index": {
                "datas": [
                    {
                        "指数简称": "深证成指",
                        "最新价": 12_860.1,
                        "最新涨跌幅:前复权": -0.3301,
                    }
                ]
            }
        }
    )

    result = ResearchWorkspaceService(client_factory=lambda: client).research(
        "market", ResearchContext()
    )

    assert result.primary_risk == "深证成指 · 涨跌幅：-0.33%"


def test_index_risk_keeps_the_date_range_for_period_change() -> None:
    client = FakeClient(
        results={
            "index": {
                "datas": [
                    {
                        "指数简称": "上证指数",
                        "最新价": 3967.13,
                        "最新涨跌幅:前复权": 1.36,
                        "涨跌幅[20260708-20260714]": -0.58,
                    }
                ]
            }
        }
    )

    result = ResearchWorkspaceService(client_factory=lambda: client).research(
        "market", ResearchContext()
    )

    assert result.primary_risk == "上证指数 · 涨跌幅（07-08至07-14）：-0.58%"


def test_market_index_card_shows_daily_and_period_trend() -> None:
    client = FakeClient(
        results={
            "index": {
                "datas": [
                    {
                        "指数代码": "000001.SH",
                        "指数简称": "上证指数",
                        "最新价": 3967.13,
                        "最新涨跌幅:前复权": 1.36,
                        "涨跌幅[20260708-20260714]": -0.58,
                    }
                ]
            }
        }
    )

    result = ResearchWorkspaceService(client_factory=lambda: client).research(
        "market", ResearchContext()
    )

    assert result.module_items[0].summary == (
        "上证指数 点位 3967.13，涨跌幅 1.36%，涨跌幅（07-08至07-14） -0.58%"
    )


def test_market_builds_theme_breadth_and_hot_stock_sections() -> None:
    client = FakeClient(
        results={
            "index": {
                "datas": [
                    {
                        "指数代码": "000001.SH",
                        "指数简称": "上证指数",
                        "最新价": 3967.13,
                        "最新涨跌幅:前复权": 1.36,
                        "涨跌幅[20260708-20260714]": -0.58,
                    }
                ]
            },
            "breadth": {
                "datas": [
                    {
                        "指数简称": "同花顺全A(沪深京)",
                        "上涨家数[20260715]": 3681,
                        "下跌家数[20260715]": 1771,
                        "平盘家数[20260715]": 71,
                        "涨停家数[20260715]": 63,
                        "跌停家数[20260715]": 16,
                    }
                ]
            },
            "sector_selector": {
                "datas": [
                    {"板块名称": "创新药", "板块热度": 980, "涨跌幅": "2.8%"}
                ]
            },
            "hot_stock": {
                "datas": [
                    {
                        "股票代码": "002384.SZ",
                        "股票简称": "东山精密",
                        "涨跌幅[20260715]": 2.68,
                        "成交额[20260715]": 29_117_831_192,
                        "所属概念": ["CPO", "PCB概念"],
                    }
                ]
            },
        }
    )

    payload = ResearchWorkspaceService(client_factory=lambda: client).research(
        "market", ResearchContext()
    ).to_public_dict()

    assert [item["key"] for item in payload["module_sections"]] == [
        "market-themes",
        "market-breadth",
        "market-hot",
        "professional-method",
    ]
    assert payload["decision_label"] == "修复中"


def test_branded_theme_classification_never_leaks_derived_fragments() -> None:
    results = {
        "sector_selector": {
            "datas": [
                {"板块名称": "同花顺果指数", "板块热度": 980, "涨跌幅": "2.8%"}
            ]
        },
        "astock_selector": {
            "datas": [
                {
                    "股票代码": "600001.SH",
                    "股票简称": "候选一",
                    "净利润同比增长率": "28%",
                    "成交额": 2_000_000_000,
                    "所属概念": ["同花顺果指数"],
                }
            ]
        },
    }
    service = ResearchWorkspaceService(
        client_factory=lambda: FakeClient(results=results)
    )

    payloads = (
        service.research("market", ResearchContext()).to_public_dict(),
        service.research("opportunity", ResearchContext()).to_public_dict(),
    )

    for payload in payloads:
        serialized = json.dumps(payload, ensure_ascii=False)
        assert "同花顺" not in serialized
        assert "果指数" not in serialized
        assert "主题分类待确认" in serialized


def test_market_positive_breadth_with_falling_core_indexes_is_structural_divergence() -> None:
    index_rows = [
        {
            "指数简称": name,
            "最新涨跌幅:前复权": daily,
            "涨跌幅[20260708-20260714]": period,
        }
        for name, daily, period in (
            ("上证指数", -0.6, -1.2),
            ("深证成指", -0.8, -2.0),
            ("创业板指", -1.1, -3.0),
        )
    ]
    service = ResearchWorkspaceService(
        client_factory=lambda: FakeClient(
            results={
                "index": {"datas": index_rows},
                "breadth": {"datas": [{"上涨家数": 3238, "下跌家数": 2195}]},
            }
        )
    )

    result = service.research("market", ResearchContext())

    assert result.decision_label == "结构分化"
    assert "上涨家数占优" in result.verdict
    assert "核心指数回落" in result.verdict


def test_market_positive_breadth_with_rising_core_indexes_stays_strong() -> None:
    index_rows = [
        {"指数简称": "上证指数", "最新涨跌幅:前复权": 0.6},
        {"指数简称": "深证成指", "最新涨跌幅:前复权": 0.8},
        {"指数简称": "创业板指", "最新涨跌幅:前复权": -0.2},
    ]
    service = ResearchWorkspaceService(
        client_factory=lambda: FakeClient(
            results={
                "index": {"datas": index_rows},
                "breadth": {"datas": [{"上涨家数": 3238, "下跌家数": 2195}]},
            }
        )
    )

    result = service.research("market", ResearchContext())

    assert result.decision_label == "偏强"


def test_market_negative_sector_is_not_presented_as_a_strong_theme() -> None:
    service = ResearchWorkspaceService(
        client_factory=lambda: FakeClient(
            results={
                "sector_selector": {
                    "datas": [
                        {
                            "板块名称": "下跌高成交板块",
                            "成交额": 20_000_000_000,
                            "涨跌幅": -3.2,
                        }
                    ]
                }
            }
        )
    )

    result = service.research("market", ResearchContext())
    section = result.module_sections[0]

    assert section.tone == "neutral"
    assert "强势主题待确认" in section.conclusion
    assert section.items[0].status == "partial"
    assert section.items[0].label != "当前强势主题"


def test_market_numeric_heat_threshold_vetoes_low_strength() -> None:
    def section_for(heat: float) -> ResearchModuleSection:
        result = ResearchWorkspaceService(
            client_factory=lambda: FakeClient(
                results={
                    "sector_selector": {
                        "datas": [
                            {
                                "板块名称": "高成交测试板块",
                                "板块热度": heat,
                                "成交额": 20_000_000_000,
                                "涨跌幅": 0.2,
                            }
                        ]
                    }
                }
            )
        ).research("market", ResearchContext())
        return result.module_sections[0]

    low_heat = section_for(10)
    threshold_heat = section_for(50)

    assert low_heat.tone == "neutral"
    assert low_heat.items[0].status == "partial"
    assert low_heat.items[0].label == "高关注待确认"
    assert threshold_heat.tone == "positive"
    assert threshold_heat.items[0].status == "ready"


def test_portfolio_groups_holdings_by_theme_and_explains_divergence() -> None:
    service = ResearchWorkspaceService(client_factory=PortfolioThemeClient)
    context = ResearchContext(
        holdings=(
            ResearchTarget(code="600001", name="芯片强"),
            ResearchTarget(code="600002", name="芯片弱"),
        )
    )

    payload = service.research("portfolio", context).to_public_dict()
    themes = next(
        item for item in payload["module_sections"] if item["key"] == "portfolio-themes"
    )
    divergence = next(
        item
        for item in payload["module_sections"]
        if item["key"] == "portfolio-divergence"
    )

    assert themes["items"][0]["name"] == "半导体"
    assert "相对强" in divergence["items"][0]["summary"]
    assert "相对弱" in divergence["items"][0]["summary"]


def test_portfolio_splits_multi_concepts_into_shared_theme_groups() -> None:
    result = ResearchWorkspaceService(client_factory=PortfolioMultiThemeClient).research(
        "portfolio",
        ResearchContext(
            holdings=(
                ResearchTarget(code="600001", name="主题甲"),
                ResearchTarget(code="600002", name="主题乙"),
            )
        ),
    )
    themes = next(
        section
        for section in result.module_sections
        if section.key == "portfolio-themes"
    )
    divergence = next(
        section
        for section in result.module_sections
        if section.key == "portfolio-divergence"
    )
    theme_by_name = {item.name: item for item in themes.items}
    divergence_by_name = {item.name: item for item in divergence.items}

    assert theme_by_name["CPO"].label == "2只持仓"
    assert "相对强：主题甲" in divergence_by_name["CPO"].summary
    assert "相对弱：主题乙" in divergence_by_name["CPO"].summary
    assert all("、" not in item.name for item in themes.items)
    assert all("同花顺" not in item.name for item in themes.items)
    assert all("数据服务" not in item.name for item in themes.items)
    assert "CPO概念" not in theme_by_name
    assert "cpo" not in theme_by_name
    serialized = json.dumps(themes.to_public_dict(), ensure_ascii=False)
    assert all(term not in serialized for term in ("股数", "成本", "权重"))


def test_portfolio_sections_keep_top_themes_and_only_comparable_divergence() -> None:
    holdings = (
        ResearchTarget(code="600001", name="共享强"),
        ResearchTarget(code="600002", name="共享弱"),
        *(
            ResearchTarget(code=f"601{index:03d}", name=f"持仓{index}")
            for index in range(12)
        ),
    )
    result = ResearchWorkspaceService(client_factory=PortfolioEssenceClient).research(
        "portfolio", ResearchContext(holdings=holdings)
    )
    themes = next(
        section
        for section in result.module_sections
        if section.key == "portfolio-themes"
    )
    divergence = next(
        section
        for section in result.module_sections
        if section.key == "portfolio-divergence"
    )

    assert len(themes.items) <= 8
    assert themes.items[0].name == "CPO"
    assert "主要主题" in themes.conclusion
    assert [item.name for item in divergence.items] == ["CPO"]
    assert "相对强" in divergence.items[0].summary
    assert "相对弱" in divergence.items[0].summary


def test_portfolio_missing_industry_is_counted_as_theme_pending() -> None:
    service = ResearchWorkspaceService(
        client_factory=lambda: FakeClient(failures={"industry"})
    )
    result = service.research(
        "portfolio",
        ResearchContext(
            holdings=(ResearchTarget(code="600001", name="主题缺失股"),)
        ),
    )
    themes = next(
        section
        for section in result.module_sections
        if section.key == "portfolio-themes"
    )

    assert themes.items[0].name == "主题待补"
    assert "1只持仓" in themes.items[0].summary
    assert "待补" in themes.conclusion


def test_portfolio_negative_event_takes_priority_over_theme_conclusion() -> None:
    service = ResearchWorkspaceService(
        client_factory=lambda: FakeClient(
            results={
                "event": {
                    "datas": [
                        {
                            "净利润增长率上限[20260630]": -180,
                            "变动类型[20260630]": "预亏",
                        }
                    ]
                }
            }
        )
    )
    result = service.research(
        "portfolio",
        ResearchContext(holdings=(ResearchTarget(code="600001", name="风险股"),)),
    )

    assert result.decision_label == "先处理风险"
    assert "先处理" in result.verdict
    assert any(section.key == "portfolio-themes" for section in result.module_sections)


def test_portfolio_large_single_holding_drop_takes_priority_over_missing_theme() -> None:
    def result_for(change: float) -> ResearchWorkspaceResult:
        return ResearchWorkspaceService(
            client_factory=lambda: FakeClient(
                results={
                    "market": {
                        "datas": [
                            {
                                "收盘价": 18.6,
                                "涨跌幅[20260715]": change,
                                "成交额[20260715]": 1_200_000_000,
                            }
                        ]
                    }
                },
                failures={"industry"},
            )
        ).research(
            "portfolio",
            ResearchContext(
                holdings=(ResearchTarget(code="600001", name="主题缺失股"),)
            ),
        )

    large_drop = result_for(-6.23)
    boundary_safe = result_for(-4.9)

    assert large_drop.decision_label == "先处理风险"
    assert "主题缺失股" in large_drop.verdict
    assert "-6.23%" in large_drop.verdict
    assert any(
        section.key == "portfolio-themes"
        for section in large_drop.module_sections
    )
    assert boundary_safe.decision_label == "主题待补"


def test_portfolio_final_recovery_states_override_historical_risk_words() -> None:
    recovered_rows = (
        ("event", {"标题": "监管处罚决定书撤销"}),
        ("event", {"标题": "诉讼案件已撤诉"}),
        ("event", {"标题": "减持计划期限届满未实施"}),
        ("consensus", {"机构评级": "由减持上调至中性"}),
    )

    for capability, row in recovered_rows:
        service = ResearchWorkspaceService(
            client_factory=lambda capability=capability, row=row: FakeClient(
                results={capability: {"datas": [row]}}
            )
        )
        result = service.research(
            "portfolio",
            ResearchContext(holdings=(ResearchTarget(code="600001", name="恢复股"),)),
        )

        assert result.decision_label != "先处理风险", row


def test_portfolio_final_negative_states_remain_priority_risks() -> None:
    negative_rows = (
        ("event", {"标题": "监管处罚决定书下达"}),
        ("event", {"标题": "监管处罚决定书维持"}),
        ("event", {"标题": "终止上市风险提示"}),
        ("consensus", {"机构评级": "由中性下调至减持"}),
    )

    for capability, row in negative_rows:
        service = ResearchWorkspaceService(
            client_factory=lambda capability=capability, row=row: FakeClient(
                results={capability: {"datas": [row]}}
            )
        )
        result = service.research(
            "portfolio",
            ResearchContext(holdings=(ResearchTarget(code="600001", name="风险股"),)),
        )

        assert result.decision_label == "先处理风险", row


def test_stock_verdict_is_plain_language_status_reason_and_next_step() -> None:
    service = ResearchWorkspaceService(
        client_factory=lambda: FakeClient(
            results={
                "finance": {
                    "datas": [
                        {
                            "营业收入[2025]": 5_100_000_000,
                            "归母净利润[2025]": -162_000_000,
                            "经营现金流[2025]": -91_000_000,
                        }
                    ]
                },
                "event": {
                    "datas": [
                        {
                            "净利润增长率上限[20260630]": -241.5,
                            "变动类型[20260630]": "预亏",
                        }
                    ]
                },
            }
        )
    )

    result = service.research(
        "stock", ResearchContext(code="603278", name="大业股份")
    )

    assert result.decision_label == "基本面承压"
    assert "先等" in result.verdict


def test_stock_finance_only_pressure_does_not_continue_tracking() -> None:
    service = ResearchWorkspaceService(
        client_factory=lambda: FakeClient(
            results={
                "finance": {
                    "datas": [
                        {
                            "归母净利润[2025]": -162_000_000,
                            "经营现金流[2025]": -91_000_000,
                        }
                    ]
                }
            }
        )
    )

    result = service.research(
        "stock", ResearchContext(code="603278", name="财务承压股")
    )

    assert result.decision_label == "基本面承压"
    assert "先" in result.verdict


def test_stock_event_only_pressure_does_not_continue_tracking() -> None:
    service = ResearchWorkspaceService(
        client_factory=lambda: FakeClient(
            results={
                "event": {
                    "datas": [
                        {
                            "净利润增长率上限[20260630]": -120,
                            "变动类型[20260630]": "预减",
                        }
                    ]
                }
            }
        )
    )

    result = service.research(
        "stock", ResearchContext(code="600001", name="事件承压股")
    )

    assert result.decision_label == "基本面承压"
    assert "先" in result.verdict


def test_stock_with_six_non_negative_dimensions_but_no_market_waits() -> None:
    service = ResearchWorkspaceService(
        client_factory=lambda: FakeClient(failures={"market", "announcement"})
    )

    result = service.research(
        "stock", ResearchContext(code="600001", name="待确认股")
    )

    assert result.decision_label == "等待确认"
    assert "先等" in result.verdict
    assert "价格" in result.verdict


def test_stock_with_complete_core_and_confirmation_can_continue() -> None:
    result = ResearchWorkspaceService(client_factory=lambda: FakeClient()).research(
        "stock", ResearchContext(code="600001", name="证据完整股")
    )

    assert result.decision_label == "可继续跟踪"


def test_stock_positive_event_with_historical_loss_is_not_downgraded() -> None:
    service = ResearchWorkspaceService(
        client_factory=lambda: FakeClient(
            results={
                "event": {
                    "datas": [
                        {
                            "净利润增长率上限[20260630]": 800,
                            "变动类型[20260630]": "预增",
                            "变动原因[20260630]": "上年同期亏损，本期订单恢复。",
                        }
                    ]
                }
            }
        )
    )

    result = service.research(
        "stock", ResearchContext(code="600001", name="业绩修复股")
    )

    assert result.decision_label == "可继续跟踪"


def test_stock_recovery_events_are_not_misclassified_as_negative() -> None:
    recovery_titles = (
        "股东提前终止减持计划",
        "监管措施解除",
        "处罚撤销",
        "诉讼撤诉",
    )

    for title in recovery_titles:
        service = ResearchWorkspaceService(
            client_factory=lambda title=title: FakeClient(
                results={"event": {"datas": [{"标题": title}]}}
            )
        )
        result = service.research(
            "stock", ResearchContext(code="600001", name="事件恢复股")
        )

        assert result.decision_label == "可继续跟踪", title


def test_stock_delisting_and_regulatory_penalty_remain_negative() -> None:
    for title in ("终止上市风险提示", "监管处罚决定"):
        service = ResearchWorkspaceService(
            client_factory=lambda title=title: FakeClient(
                results={"event": {"datas": [{"标题": title}]}}
            )
        )
        result = service.research(
            "stock", ResearchContext(code="600001", name="事件风险股")
        )

        assert result.decision_label == "基本面承压", title


def test_opportunity_sections_put_themes_before_candidates() -> None:
    service = ResearchWorkspaceService(
        client_factory=lambda: FakeClient(
            results={
                "sector_selector": {
                    "datas": [
                        {"板块名称": "创新药", "板块热度": 980, "涨跌幅": "2.8%"}
                    ]
                },
                "astock_selector": {
                    "datas": [
                        {
                            "股票代码": "600001.SH",
                            "股票简称": "候选一",
                            "净利润同比增长率": "28%",
                            "成交额": 2_000_000_000,
                            "所属概念": ["创新药"],
                        }
                    ]
                },
            }
        )
    )

    result = service.research("opportunity", ResearchContext())

    assert [section.key for section in result.module_sections][:2] == [
        "opportunity-themes",
        "opportunity-candidates",
    ]
    assert result.decision_label == "有主线"
    assert result.module_sections[1].items[0].label == "创新药"


def test_opportunity_candidate_labels_use_first_matching_primary_theme() -> None:
    service = ResearchWorkspaceService(
        client_factory=lambda: FakeClient(
            results={
                "sector_selector": {
                    "datas": [
                        {"板块名称": "CPO", "板块热度": 1000},
                        {"板块名称": "PCB概念", "板块热度": 900},
                    ]
                },
                "astock_selector": {
                    "datas": [
                        {
                            "股票代码": "600001.SH",
                            "股票简称": "候选甲",
                            "净利润同比增长率": "28%",
                            "成交额": 2_000_000_000,
                            "所属概念": ["CPO", "PCB概念", "5G"],
                        },
                        {
                            "股票代码": "600002.SH",
                            "股票简称": "候选乙",
                            "净利润同比增长率": "25%",
                            "成交额": 1_800_000_000,
                            "所属概念": ["CPO", "光模块", "算力"],
                        },
                    ]
                },
            }
        )
    )

    result = service.research("opportunity", ResearchContext())
    candidates = result.module_sections[1].items

    assert [item.label for item in candidates] == ["CPO", "CPO"]
    assert any("PCB概念" in fact.value for fact in candidates[0].facts)
    assert any("光模块" in fact.value for fact in candidates[1].facts)


def test_opportunity_theme_matching_is_case_insensitive() -> None:
    service = ResearchWorkspaceService(
        client_factory=lambda: FakeClient(
            results={
                "sector_selector": {
                    "datas": [{"板块名称": "CPO", "板块热度": 980}]
                },
                "astock_selector": {
                    "datas": [
                        {
                            "股票代码": "600001.SH",
                            "股票简称": "候选一",
                            "净利润同比增长率": "28%",
                            "成交额": 2_000_000_000,
                            "所属概念": ["cpo概念"],
                        }
                    ]
                },
            }
        )
    )

    result = service.research("opportunity", ResearchContext())

    assert result.decision_label == "有主线"
    assert result.module_sections[1].items[0].label == "CPO"


def test_opportunity_without_candidate_theme_does_not_claim_a_mainline() -> None:
    service = ResearchWorkspaceService(
        client_factory=lambda: FakeClient(
            results={
                "sector_selector": {
                    "datas": [
                        {"板块名称": "创新药", "板块热度": 980, "涨跌幅": "2.8%"}
                    ]
                },
                "astock_selector": {
                    "datas": [
                        {
                            "股票代码": "600001.SH",
                            "股票简称": "主题待确认股",
                            "净利润同比增长率": "28%",
                            "成交额": 2_000_000_000,
                        }
                    ]
                },
            }
        )
    )

    result = service.research("opportunity", ResearchContext())
    candidate = result.module_sections[1].items[0]

    assert candidate.label == "主题待确认"
    assert candidate.status == "missing"
    assert result.decision_label == "主线待确认"


def test_opportunity_weak_theme_does_not_claim_a_mainline() -> None:
    service = ResearchWorkspaceService(
        client_factory=lambda: FakeClient(
            results={
                "sector_selector": {
                    "datas": [{"板块名称": "创新药", "涨跌幅": "-1.8%"}]
                },
                "astock_selector": {
                    "datas": [
                        {
                            "股票代码": "600001.SH",
                            "股票简称": "候选一",
                            "净利润同比增长率": "28%",
                            "成交额": 2_000_000_000,
                            "所属概念": ["创新药"],
                        }
                    ]
                },
            }
        )
    )

    result = service.research("opportunity", ResearchContext())

    assert result.decision_label == "主线待确认"
    assert result.module_sections[1].items[0].status == "partial"


def test_opportunity_text_heat_distinguishes_weak_and_strong_themes() -> None:
    def result_for(heat: str) -> object:
        return ResearchWorkspaceService(
            client_factory=lambda: FakeClient(
                results={
                    "sector_selector": {
                        "datas": [{"板块名称": "创新药", "板块热度": heat}]
                    },
                    "astock_selector": {
                        "datas": [
                            {
                                "股票代码": "600001.SH",
                                "股票简称": "候选一",
                                "净利润同比增长率": "28%",
                                "成交额": 2_000_000_000,
                                "所属概念": ["创新药"],
                            }
                        ]
                    },
                }
            )
        ).research("opportunity", ResearchContext())

    for heat in ("低迷", "弱", "降温", "萎缩"):
        assert result_for(heat).decision_label == "主线待确认", heat
    for heat in ("高", "强", "活跃", "放量"):
        assert result_for(heat).decision_label == "有主线", heat


def test_opportunity_context_names_never_count_as_strength() -> None:
    def result_for(name: str, heat: str = "") -> object:
        sector_row = {"板块名称": name, "板块类型": "概念"}
        if heat:
            sector_row["板块热度"] = heat
        return ResearchWorkspaceService(
            client_factory=lambda: FakeClient(
                results={
                    "sector_selector": {"datas": [sector_row]},
                    "astock_selector": {
                        "datas": [
                            {
                                "股票代码": "600001.SH",
                                "股票简称": "候选一",
                                "净利润同比增长率": "28%",
                                "成交额": 2_000_000_000,
                                "所属概念": [name],
                            }
                        ]
                    },
                }
            )
        ).research("opportunity", ResearchContext())

    for name in ("高端装备", "强周期"):
        assert result_for(name).decision_label == "主线待确认", name
    for heat in ("高", "活跃"):
        assert result_for("高端装备", heat).decision_label == "有主线", heat


def test_opportunity_negative_event_downgrades_all_candidates() -> None:
    service = ResearchWorkspaceService(
        client_factory=lambda: FakeClient(
            results={
                "sector_selector": {
                    "datas": [
                        {"板块名称": "创新药", "板块热度": 980, "涨跌幅": "2.8%"}
                    ]
                },
                "astock_selector": {
                    "datas": [
                        {
                            "股票代码": "600001.SH",
                            "股票简称": "候选一",
                            "净利润同比增长率": "28%",
                            "成交额": 2_000_000_000,
                            "所属概念": ["创新药"],
                        }
                    ]
                },
                "event": {
                    "datas": [
                        {
                            "净利润增长率上限[20260630]": -200,
                            "变动类型[20260630]": "预亏",
                        }
                    ]
                },
            }
        )
    )

    result = service.research("opportunity", ResearchContext())

    assert result.decision_label == "主线待确认"
    assert result.module_sections[1].items[0].status == "partial"
    assert "不利" in result.module_sections[1].conclusion


def test_positive_breadth_is_not_overridden_by_isolated_limit_downs() -> None:
    service = ResearchWorkspaceService(
        client_factory=lambda: FakeClient(
            results={
                "breadth": {
                    "datas": [
                        {
                            "上涨家数": 4000,
                            "下跌家数": 1000,
                            "涨停家数": 2,
                            "跌停家数": 3,
                        }
                    ]
                }
            }
        )
    )

    result = service.research("market", ResearchContext())

    assert result.decision_label == "偏强"


def test_market_repair_requires_same_index_and_cannot_override_negative_breadth() -> None:
    service = ResearchWorkspaceService(
        client_factory=lambda: FakeClient(
            results={
                "index": {
                    "datas": [
                        {
                            "指数简称": "上证指数",
                            "最新涨跌幅:前复权": 0.1,
                            "涨跌幅[20260708-20260714]": 1.2,
                        },
                        {
                            "指数简称": "深证成指",
                            "最新涨跌幅:前复权": -2.0,
                            "涨跌幅[20260708-20260714]": -4.0,
                        },
                    ]
                },
                "breadth": {
                    "datas": [{"上涨家数": 1000, "下跌家数": 4000}]
                },
            }
        )
    )

    result = service.research("market", ResearchContext())

    assert result.decision_label == "偏弱"


def test_public_payload_replaces_provider_names_inside_facts() -> None:
    service = ResearchWorkspaceService(
        client_factory=lambda: FakeClient(
            results={
                "breadth": {
                    "datas": [
                        {
                            "指数简称": "同花顺全A(沪深京)",
                            "上涨家数[20260715]": 3681,
                            "下跌家数[20260715]": 1771,
                        }
                    ]
                }
            }
        )
    )

    payload = service.research("market", ResearchContext()).to_public_dict()

    assert "同花顺" not in json.dumps(payload, ensure_ascii=False)


def test_public_hot_stock_drops_branded_classification_instead_of_renaming_it() -> None:
    payload = ResearchModuleItem(
        kind="hot_stock",
        code="300033",
        name="示例股票",
        label="同花顺果指数",
        summary="成交活跃",
        facts=(ResearchFact(label="所属概念", value="同花顺果指数"),),
    ).to_public_dict()
    serialized = json.dumps(payload, ensure_ascii=False)

    assert payload["label"] == "主题待确认"
    assert payload["facts"] == []
    assert "同花顺" not in serialized
    assert "数据服务果指数" not in serialized


def test_sector_risk_names_the_affected_sector() -> None:
    client = FakeClient(
        results={
            "sector_selector": {
                "datas": [
                    {
                        "指数简称": "通信设备",
                        "板块热度": 860,
                        "最新涨跌幅:前复权": -0.3301,
                    }
                ]
            }
        }
    )

    result = ResearchWorkspaceService(client_factory=lambda: client).research(
        "market", ResearchContext()
    )

    assert result.primary_risk == "通信设备 · 涨跌幅：-0.33%"


def test_portfolio_primary_risk_names_the_holding() -> None:
    service = ResearchWorkspaceService(
        client_factory=lambda: FakeClient(
            results={
                "event": {
                    "datas": [
                        {
                            "净利润增长率上限[20260630]": -241.516,
                            "变动类型[20260630]": "预减",
                        }
                    ]
                }
            }
        )
    )
    context = ResearchContext(
        holdings=(ResearchTarget(code="600519", name="贵州茅台"),)
    )

    result = service.research("portfolio", context)

    assert result.primary_risk.startswith("贵州茅台 · 净利润增长率上限")


def test_positive_event_summary_is_not_presented_as_primary_risk() -> None:
    service = ResearchWorkspaceService(
        client_factory=lambda: FakeClient(
            results={
                "event": {
                    "datas": [
                        {
                            "净利润增长率上限[20260630]": 800,
                            "变动类型[20260630]": "预增",
                            "变动原因[20260630]": "上年同期亏损，本期订单恢复。",
                        }
                    ]
                }
            }
        )
    )

    result = service.research("opportunity", ResearchContext())

    assert "最新变化改善" not in result.primary_risk
    assert result.primary_risk.startswith("变动原因")


def test_document_summary_is_capped_and_does_not_repeat_title() -> None:
    title = "重要政策推动风险偏好改善"
    service = ResearchWorkspaceService(
        client_factory=lambda: FakeClient(
            results={
                "news": {
                    "datas": [
                        {
                            "title": title,
                            "summary": f"{title}{'成交确认仍需观察。' * 40}",
                            "publish_date": datetime.now(
                                timezone(timedelta(hours=8))
                            ).strftime("%Y%m%d"),
                        }
                    ]
                }
            }
        )
    )

    result = service.research("market", ResearchContext())
    news = next(item for item in result.findings if item.title == "市场事件")

    assert len(news.summary) <= 80
    assert news.summary.count(title) == 1


def test_documents_older_than_thirty_days_stay_out_of_front_judgment() -> None:
    old_date = (
        datetime.now(timezone(timedelta(hours=8))) - timedelta(days=31)
    ).strftime("%Y%m%d")
    title = "重大风险事件仍在发酵"
    service = ResearchWorkspaceService(
        client_factory=lambda: FakeClient(
            results={
                "news": {
                    "datas": [
                        {
                            "title": title,
                            "summary": "风险影响仍需核查。",
                            "publish_date": old_date,
                        }
                    ]
                }
            }
        )
    )

    result = service.research("market", ResearchContext())
    news_detail = next(item for item in result.details if item.section == "市场事件")

    assert news_detail.findings
    assert all(item.title != "市场事件" for item in result.findings)
    assert title not in result.verdict
    assert title not in result.primary_risk


def test_summary_backed_findings_drop_repeated_identity_and_text_facts() -> None:
    service = ResearchWorkspaceService(client_factory=lambda: FakeClient())

    market = service.research("market", ResearchContext())
    opportunity = service.research("opportunity", ResearchContext())

    index = next(item for item in market.findings if item.title == "指数状态")
    news = next(item for item in market.findings if item.title == "市场事件")
    candidate = next(
        item for item in opportunity.findings if item.title == "候选线索"
    )
    assert all("指数" not in fact.label for fact in index.facts)
    assert all(
        fact.label.lower() not in {"title", "summary", "url"}
        for fact in news.facts
    )
    assert all("股票" not in fact.label for fact in candidate.facts)


def test_finance_summary_handles_negative_profit_and_cash_flow() -> None:
    fixture = stock_research_fixture()
    fixture["finance"] = {
        "datas": [
            {
                "营业收入[20251231]": 5_026_000_000,
                "营业收入[20241231]": 5_097_000_000,
                "归母净利润[20251231]": -13_471_200,
                "经营活动产生的现金流量净额[20251231]": -184_000_000,
            }
        ]
    }
    service = ResearchWorkspaceService(
        client_factory=lambda: FakeClient(results=fixture)
    )

    result = service.research(
        "stock", ResearchContext(code="603278", name="大业股份")
    )
    finance = next(item for item in result.findings if item.title == "财务方向")

    assert "利润与经营现金流均为负" in finance.summary


def test_positive_event_growth_is_summarized_as_improvement() -> None:
    fixture = stock_research_fixture()
    fixture["event"] = {
        "datas": [
            {
                "净利润增长率上限[20260630]": 800,
                "净利润增长率下限[20260630]": 700,
                "变动类型[20260630]": "预增",
            }
        ]
    }
    service = ResearchWorkspaceService(
        client_factory=lambda: FakeClient(results=fixture)
    )

    result = service.research(
        "stock", ResearchContext(code="603278", name="大业股份")
    )

    assert result.findings[0].summary == "净利润上限为800.00%，最新变化改善"
