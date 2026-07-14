from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from stock_ts.iwencai import SKILLS
from stock_ts.research_engine import (
    ResearchContext,
    ResearchModuleItem,
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
        "macro",
        "sector_selector",
        "news",
    )
    assert workspace_capabilities("portfolio") == (
        "event",
        "consensus",
        "market",
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

    assert len(requests) == 6
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

    assert len(requests) == 15
    assert "股票4" in " ".join(item.query for item in requests)


def test_portfolio_builds_three_capabilities_for_all_twenty_holdings() -> None:
    holdings = tuple(
        ResearchTarget(code=f"600{index:03d}", name=f"持仓{index}")
        for index in range(25)
    )

    requests = build_workspace_queries("portfolio", ResearchContext(holdings=holdings))

    assert len(requests) == 20 * 3
    assert {request.capability for request in requests} == {
        "event",
        "consensus",
        "market",
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


def test_opportunity_selector_query_contains_parseable_conditions() -> None:
    requests = build_workspace_queries(
        "opportunity", ResearchContext(sector="机器人")
    )
    query_by_capability = {item.capability: item.query for item in requests}

    assert "机器人概念" in query_by_capability["sector_selector"]
    assert "净利润同比增长" in query_by_capability["astock_selector"]
    assert "成交额" in query_by_capability["astock_selector"]
    assert "前10" in query_by_capability["astock_selector"]
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

    assert len(client.calls) == 24


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
