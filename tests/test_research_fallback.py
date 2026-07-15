from dataclasses import replace
from datetime import date, timedelta

from stock_ts.models import DailyBar, NewsItem, StockRawData
from stock_ts.providers.sample import SampleDataProvider
from stock_ts.research_engine import ResearchContext, ResearchTarget
from stock_ts.research_fallback import build_local_research


class LocalFixtureProvider(SampleDataProvider):
    def fetch_stock(self, code: str):
        raw = super().fetch_stock(code)
        return replace(
            raw,
            fundamental_metrics={"roe": 12.4, "revenue_yoy": 8.6, "net_profit_yoy": -3.2},
            valuation={"pe_ttm": raw.pe_ttm, "pb": 2.4},
            fund_flow_detail={"main_net_inflow": raw.fund_flow},
            news_items=[
                NewsItem(
                    date="2026-07-15",
                    source="公开新闻",
                    title="公司披露经营进展",
                    summary="收入保持增长，利润仍待修复。",
                )
            ],
            announcements=[{"title": "2026年半年度业绩预告", "date": "2026-07-15"}],
        )


class CandidateOnlyProvider(SampleDataProvider):
    def fetch_stock(self, code: str):
        raise ValueError(f"stock detail unavailable: {code}")


class StalePriceOnlyProvider(SampleDataProvider):
    def fetch_market(self):
        return replace(super().fetch_market(), trade_date="2026-07-15")

    def fetch_stock(self, code: str):
        bars = [
            DailyBar(
                date=(date(2026, 6, 20) + timedelta(days=index)).isoformat(),
                open=30 + index * 0.4,
                high=31 + index * 0.4,
                low=29 + index * 0.4,
                close=30 + index * 0.4,
                volume=1_000_000 + index * 20_000,
            )
            for index in range(25)
        ]
        return StockRawData(code=code, name="药石科技", bars=bars)


def test_local_stock_blocks_direction_when_price_is_stale_and_evidence_is_missing() -> None:
    result = build_local_research(
        "stock",
        ResearchContext(code="300725", name="药石科技"),
        provider=StalePriceOnlyProvider(),
    )

    assert result.decision_label == "数据不足"
    assert "谨慎进攻" not in result.verdict
    assert [section.key for section in result.module_sections[:2]] == [
        "stock-data-gate",
        "stock-multi-horizon",
    ]
    assert [item.label for item in result.module_items] == ["行情资金", "关键缺口"]
    assert result.module_items[-1].status == "missing"
    assert "行情日期" in result.module_sections[0].conclusion


def test_local_stock_fallback_keeps_available_dimensions_and_marks_gaps() -> None:
    result = build_local_research(
        "stock",
        ResearchContext(code="603278", name="大业股份"),
        provider=LocalFixtureProvider(),
    )

    payload = result.to_public_dict()
    assert payload["status"] == "partial"
    assert payload["delivery"] == "local_fallback"
    assert payload["data_label"] == "本地证据"
    assert payload["verdict"]
    assert len(payload["findings"]) >= 2
    assert len(payload["module_items"]) == 8
    assert {item["label"] for item in payload["module_items"]} >= {
        "财务质量",
        "行情资金",
        "公告事项",
    }
    assert "机构预期" in payload["missing_sections"]


def test_local_stock_fallback_uses_candidate_bars_when_stock_detail_is_missing() -> None:
    provider = CandidateOnlyProvider()
    candidate = provider.fetch_candidate_universe()[0]

    result = build_local_research(
        "stock",
        ResearchContext(code=candidate.code, name=candidate.name),
        provider=provider,
    )

    payload = result.to_public_dict()
    assert payload["delivery"] == "local_fallback"
    assert candidate.name in payload["verdict"]
    assert [item["label"] for item in payload["module_items"]] == [
        "行情资金",
        "关键缺口",
    ]
    assert len(payload["findings"]) == 3


def test_local_stock_fallback_uses_opportunity_snapshot_when_provider_has_no_stock() -> None:
    result = build_local_research(
        "stock",
        ResearchContext(code="002384.SZ", name="东山精密"),
        provider=CandidateOnlyProvider(),
        opportunity_snapshot={
            "as_of": "2026-07-15",
            "module_items": [
                {
                    "code": "002384.SZ",
                    "name": "东山精密",
                    "label": "今日候选",
                    "summary": "归母净利润同比增长，成交保持活跃。",
                    "risk": "主题退潮或成交萎缩时移出观察。",
                    "status": "ready",
                }
            ],
            "module_sections": [
                {
                    "key": "opportunity-candidates",
                    "items": [
                        {
                            "code": "002384.SZ",
                            "name": "东山精密",
                            "label": "共封装光学(CPO)",
                            "summary": "主题与成交同时确认。",
                            "risk": "主题退潮时移出观察。",
                        }
                    ],
                }
            ],
        },
    )

    payload = result.to_public_dict()
    assert payload["delivery"] == "local_fallback"
    assert "东山精密" in payload["verdict"]
    assert len(payload["module_items"]) == 8
    assert len(payload["findings"]) == 3
    assert payload["coverage"] == {"ready": 2, "total": 8}
    assert "CPO" in payload["module_items"][5]["summary"]


def test_local_portfolio_fallback_shows_all_positions_and_theme_sections(tmp_path) -> None:
    holdings = tmp_path / "holdings.csv"
    holdings.write_text(
        "code,name,shares,cost_price,sector,note\n"
        "600519,贵州茅台,10,1500,白酒,核心\n"
        "000001,平安银行,100,12,银行,观察\n"
        "300750,宁德时代,20,200,新能源车,观察\n",
        encoding="utf-8",
    )
    result = build_local_research(
        "portfolio",
        ResearchContext(
            holdings=(
                ResearchTarget(code="600519", name="贵州茅台"),
                ResearchTarget(code="000001", name="平安银行"),
                ResearchTarget(code="300750", name="宁德时代"),
            )
        ),
        provider=LocalFixtureProvider(),
        holdings_path=holdings,
    )

    payload = result.to_public_dict()
    assert payload["subject_count"] == 3
    assert len(payload["module_items"]) == 3
    assert {section["key"] for section in payload["module_sections"]} == {
        "portfolio-themes",
        "portfolio-divergence",
    }
    assert len(payload["findings"]) <= 3
    for item in payload["module_items"]:
        facts = {fact["label"]: fact["value"] for fact in item["facts"]}
        assert facts["当前动作"]
        assert facts["主要原因"]
        assert facts["确认条件"]
        assert facts["失效条件"]


def test_local_global_fallback_returns_market_and_opportunity_content() -> None:
    market = build_local_research("market", ResearchContext(), provider=LocalFixtureProvider())
    opportunity = build_local_research(
        "opportunity", ResearchContext(), provider=LocalFixtureProvider()
    )

    assert market.module_sections
    assert opportunity.module_sections
    assert market.module_items
    assert opportunity.module_items


def test_local_market_leads_with_professional_pulse_metrics() -> None:
    result = build_local_research(
        "market",
        ResearchContext(),
        provider=LocalFixtureProvider(),
    )

    assert result.module_sections[0].key == "market-pulse"
    pulse_items = result.module_sections[0].items
    assert len(pulse_items) == 6
    assert all(item.kind == "market_metric" for item in pulse_items)
    assert {item.label for item in pulse_items} >= {
        "上涨参与率",
        "涨跌宽度比",
        "涨跌停平衡",
        "扫描样本强弱差",
        "主题扩散",
        "证据覆盖",
    }
    assert "风险预算" in result.action
    assert result.decision_label in {
        "风险关闭",
        "防守",
        "均衡",
        "结构进攻",
        "风险开启",
    }
    breadth = next(
        section for section in result.module_sections if section.key == "market-breadth"
    )
    assert [item.name for item in breadth.items] == [
        "上涨家数",
        "下跌家数",
        "平盘家数",
        "涨停家数",
        "跌停家数",
    ]
    assert all(item.summary.isdigit() for item in breadth.items)
    movers = next(
        section for section in result.module_sections if section.key == "market-movers"
    )
    assert movers.items
    for item in movers.items:
        facts = {fact.label: fact.value for fact in item.facts}
        assert facts["涨跌幅"]
        assert facts["异动原因"]
        assert facts["确认条件"]
        assert facts["失效条件"]


def test_local_stock_exposes_eight_auditable_evidence_dimensions() -> None:
    result = build_local_research(
        "stock",
        ResearchContext(code="603278", name="大业股份"),
        provider=LocalFixtureProvider(),
    )

    evidence = next(
        section for section in result.module_sections if section.key == "stock-evidence"
    )
    assert [section.key for section in result.module_sections[:4]] == [
        "stock-data-gate",
        "stock-multi-horizon",
        "stock-decision",
        "stock-evidence",
    ]
    decision = result.module_sections[2]
    assert [item.label for item in decision.items] == [
        "当前动作",
        "最强支持",
        "主要反证",
        "执行边界",
    ]
    assert len(evidence.items) == 8
    assert all(item.kind == "stock_evidence" for item in evidence.items)
    for item in evidence.items:
        facts = {fact.label: fact.value for fact in item.facts}
        assert facts["评分"]
        assert facts["可信度"] in {"高", "中", "低", "阻断"}
        assert facts["转强条件"]
        assert facts["失效条件"]
        assert item.summary
        assert item.risk


def test_local_opportunity_candidates_have_reasoned_list_facts_without_candidate_findings() -> None:
    result = build_local_research(
        "opportunity",
        ResearchContext(),
        provider=LocalFixtureProvider(),
    )

    payload = result.to_public_dict()
    candidates = next(
        section
        for section in payload["module_sections"]
        if section["key"] == "opportunity-candidates"
    )
    assert candidates["items"]
    for item in candidates["items"]:
        facts = {fact["label"]: fact["value"] for fact in item["facts"]}
        assert facts["观察分"]
        assert facts["涨跌幅"]
        assert facts["入选原因"]
        assert facts["确认条件"]
        assert facts["失效条件"]
    assert all(not finding["title"].startswith("候选：") for finding in payload["findings"])
