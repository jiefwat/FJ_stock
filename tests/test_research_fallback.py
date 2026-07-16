import json
from dataclasses import replace
from datetime import date, timedelta

from stock_ts.models import CandidateStockRawData, DailyBar, NewsItem, StockRawData
from stock_ts.providers.sample import SampleDataProvider
from stock_ts.research_engine import ResearchContext, ResearchTarget
from stock_ts.research_fallback import build_local_research
from stock_ts.workflows import build_market_report


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


def _candidate_bars(closes: list[float], *, end: date) -> list[DailyBar]:
    start = end - timedelta(days=len(closes) - 1)
    return [
        DailyBar(
            date=(start + timedelta(days=index)).isoformat(),
            open=close * 0.995,
            high=close * 1.01,
            low=close * 0.99,
            close=close,
            volume=1_000_000 + index * 15_000,
        )
        for index, close in enumerate(closes)
    ]


class MultiDayCandidateProvider(LocalFixtureProvider):
    def fetch_market(self):
        return replace(super().fetch_market(), trade_date="2026-07-15")

    def fetch_candidate_universe(self):
        return [
            CandidateStockRawData(
                code="600001",
                name="稳步上行",
                sector="半导体",
                bars=_candidate_bars(
                    [100 + index * 0.8 for index in range(25)],
                    end=date(2026, 7, 15),
                ),
                fund_flow=2.0,
            ),
            CandidateStockRawData(
                code="600002",
                name="单日脉冲",
                sector="半导体",
                bars=_candidate_bars(
                    [100.0] * 24 + [106.0],
                    end=date(2026, 7, 15),
                ),
            ),
            CandidateStockRawData(
                code="600003",
                name="陈旧行情",
                sector="半导体",
                bars=_candidate_bars(
                    [100 + index * 0.7 for index in range(25)],
                    end=date(2026, 7, 14),
                ),
            ),
        ]


class MultiThemeCandidateProvider(MultiDayCandidateProvider):
    def fetch_candidate_universe(self):
        items = super().fetch_candidate_universe()
        return [
            replace(items[0], code="600011", name="机器人趋势", sector="机器人"),
            replace(items[0], code="600012", name="半导体趋势", sector="半导体"),
            *items[1:],
        ]


class UnknownThemeCandidateProvider(MultiDayCandidateProvider):
    def fetch_candidate_universe(self):
        trend = super().fetch_candidate_universe()[0]
        return [
            replace(
                trend,
                code="600021",
                name="未知主题趋势",
                sector="未识别主题",
            ),
            replace(
                trend,
                code="600022",
                name="机器人趋势",
                sector="机器人",
            ),
        ]


class CandidateThemeOutsideSectorRankProvider(MultiDayCandidateProvider):
    def fetch_candidate_universe(self):
        trend = super().fetch_candidate_universe()[0]
        return [
            replace(
                trend,
                code="600031",
                name="旅游趋势",
                sector="旅游概念",
            )
        ]


class ExpandedCandidateProvider(MultiDayCandidateProvider):
    def fetch_candidate_universe(self):
        trend = super().fetch_candidate_universe()[0]
        rebound_closes = [120 - index for index in range(19)] + [102, 103, 104, 105, 106, 107]
        rebounds = [
            CandidateStockRawData(
                code=f"6001{index:02d}",
                name=f"反弹观察{index}",
                sector=f"主题{index}",
                bars=_candidate_bars(rebound_closes, end=date(2026, 7, 15)),
                fund_flow=1.0,
            )
            for index in range(1, 10)
        ]
        return [trend, *rebounds]


class StrongBreadthProvider(LocalFixtureProvider):
    def fetch_candidate_universe(self):
        candidates = super().fetch_candidate_universe()
        boosted = []
        for candidate in candidates[:4]:
            bars = list(candidate.bars)
            bars[-1] = replace(bars[-1], close=bars[-2].close * 1.04)
            boosted.append(replace(candidate, sector="半导体", bars=bars))
        return [*boosted, *candidates[4:]]


class MissingCandidateProvider(LocalFixtureProvider):
    def __init__(self):
        self.candidate_calls = 0

    def fetch_candidate_universe(self):
        self.candidate_calls += 1
        if self.candidate_calls == 1:
            raise ValueError("candidate scan unavailable")
        return super().fetch_candidate_universe()


class NegativeEventCandidateProvider(MultiDayCandidateProvider):
    def fetch_candidate_universe(self):
        trend = replace(
            super().fetch_candidate_universe()[0],
            code="600041",
            name="无事件趋势",
            fund_flow=None,
            pe_ttm=None,
        )
        negative = replace(
            trend,
            code="600042",
            name="负面事件趋势",
            news_items=[
                NewsItem(
                    date="2026-07-15",
                    source="公开新闻",
                    title="公司遭监管问询",
                    summary="监管要求公司说明相关风险。",
                    sentiment="negative",
                )
            ],
            announcements=[{"title": "股东减持公告", "date": "2026-07-15"}],
        )
        return [trend, negative]


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
    decision_section = next(
        section for section in result.module_sections if section.key == "stock-decision"
    )
    evidence_section = next(
        section for section in result.module_sections if section.key == "stock-evidence"
    )
    assert "数据闸门未解除" in decision_section.conclusion
    assert "谨慎进攻" not in decision_section.conclusion
    assert "不形成方向性结论" in evidence_section.conclusion


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
        assert facts["阶段判断"]
        assert facts["5日表现"]
        assert facts["10日表现"]
        assert facts["20日表现"]


def test_local_global_fallback_returns_market_and_opportunity_content() -> None:
    market = build_local_research("market", ResearchContext(), provider=LocalFixtureProvider())
    opportunity = build_local_research(
        "opportunity", ResearchContext(), provider=LocalFixtureProvider()
    )

    assert market.module_sections
    assert opportunity.module_sections
    assert market.module_items
    assert opportunity.module_items


def test_market_contains_facts_but_no_forecast_watchlist() -> None:
    provider = MultiDayCandidateProvider()
    market = build_local_research("market", ResearchContext(), provider=provider)
    section_keys = {section.key for section in market.module_sections}
    movers = next(
        section for section in market.module_sections if section.key == "market-movers"
    )

    assert {"market-pulse", "market-breadth", "market-themes", "market-movers"} <= (
        section_keys
    )
    assert "market-continuation" not in section_keys
    assert "单日脉冲" in {item.name for item in movers.items}
    assert "未来" not in market.action
    assert "候选" not in market.action
    visible_text = json.dumps(market.to_public_dict(), ensure_ascii=False)
    for forbidden in ("风险预算", "仓位", "可投资", "候选", "买入", "卖出", "明日上涨"):
        assert forbidden not in visible_text
    for item in movers.items:
        fact_labels = {fact.label for fact in item.facts}
        assert "确认条件" not in fact_labels
        assert "失效条件" not in fact_labels


def test_market_mover_public_text_uses_observation_only_risks() -> None:
    cases = (
        (
            MultiDayCandidateProvider(),
            "上涨异动",
            "单日涨幅较大，不代表趋势已经形成。",
        ),
        (
            LocalFixtureProvider(),
            "下跌异动",
            "单日跌幅较大，反映当日波动风险。",
        ),
    )
    for provider, direction, expected_risk in cases:
        payload = build_local_research(
            "market",
            ResearchContext(),
            provider=provider,
        ).to_public_dict()
        movers = next(
            section
            for section in payload["module_sections"]
            if section["key"] == "market-movers"
        )
        item = next(row for row in movers["items"] if direction in row["summary"])
        facts = {fact["label"]: fact["value"] for fact in item["facts"]}
        visible_text = json.dumps(
            {
                "summary": item["summary"],
                "risk": item["risk"],
                "facts": item["facts"],
            },
            ensure_ascii=False,
        )

        assert item["risk"] == expected_risk
        assert facts["风险"] == expected_risk
        for forbidden in ("开盘", "承接", "确认", "追高", "等待", "次日"):
            assert forbidden not in visible_text


def test_opportunity_top10_keeps_strict_candidates_and_ranked_rebound_watchlist() -> None:
    opportunity = build_local_research(
        "opportunity",
        ResearchContext(),
        provider=ExpandedCandidateProvider(),
    )

    candidates = next(
        section
        for section in opportunity.module_sections
        if section.key == "opportunity-candidates"
    )
    assert len(candidates.items) == 10
    assert candidates.items[0].name == "稳步上行"
    item = candidates.items[0]
    assert {fact.label for fact in item.facts} >= {
        "阶段判断",
        "持续性评分",
        "5日表现",
        "10日表现",
        "20日表现",
        "上涨天数",
        "最大回撤",
        "入选原因",
        "确认条件",
        "失效条件",
    }
    stages = {
        next(fact.value for fact in candidate.facts if fact.label == "阶段判断")
        for candidate in candidates.items
    }
    assert stages <= {"价格延续观察", "等待确认", "反弹观察"}
    assert candidates.items[0].facts[0].value == "价格延续观察"
    assert "反弹观察" in stages
    assert all(candidate.status == "ready" for candidate in candidates.items)


def test_opportunity_selected_theme_only_returns_matching_candidates() -> None:
    result = build_local_research(
        "opportunity",
        ResearchContext(sector="机器人"),
        provider=MultiThemeCandidateProvider(),
    )

    themes = next(
        section for section in result.module_sections if section.key == "opportunity-themes"
    )
    candidates = next(
        section for section in result.module_sections if section.key == "opportunity-candidates"
    )

    assert [item.name for item in themes.items] == ["机器人"]
    assert [item.name for item in candidates.items] == ["机器人趋势"]
    assert "机器人" in result.verdict


def test_opportunity_themes_only_link_to_gated_classified_candidates() -> None:
    result = build_local_research(
        "opportunity",
        ResearchContext(),
        provider=UnknownThemeCandidateProvider(),
    )

    themes = next(
        section for section in result.module_sections if section.key == "opportunity-themes"
    )
    candidates = next(
        section for section in result.module_sections if section.key == "opportunity-candidates"
    )

    assert [item.name for item in themes.items] == ["机器人"]
    assert [item.name for item in candidates.items] == ["机器人趋势", "未知主题趋势"]
    assert all(item.label != "未识别主题" for item in candidates.items)
    assert candidates.items[1].label == "独立个股"


def test_opportunity_builds_theme_card_when_candidate_theme_is_outside_sector_rank() -> None:
    result = build_local_research(
        "opportunity",
        ResearchContext(),
        provider=CandidateThemeOutsideSectorRankProvider(),
    )

    themes = next(
        section for section in result.module_sections if section.key == "opportunity-themes"
    )
    candidates = next(
        section for section in result.module_sections if section.key == "opportunity-candidates"
    )

    assert [item.name for item in themes.items] == ["旅游概念"]
    assert [item.name for item in candidates.items] == ["旅游趋势"]
    assert "旅游概念" in result.verdict
    assert themes.conclusion == "旅游概念"
    assert result.findings[0].summary == "旅游概念"
    assert "旅游概念" in result.primary_risk
    assert "旅游概念" in result.findings[2].summary
    candidate_score = next(
        fact.value for fact in candidates.items[0].facts if fact.label == "持续性评分"
    )
    assert candidate_score in result.findings[1].summary


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
    assert result.action == "这里只记录已发生的市场事实；条件研究请进入热门机会。"
    assert result.decision_label == "宽度均衡"
    assert "宽度均衡" in result.verdict
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
        assert "确认条件" not in facts
        assert "失效条件" not in facts


def test_missing_market_scan_uses_neutral_public_wording() -> None:
    result = build_local_research(
        "market",
        ResearchContext(),
        provider=MissingCandidateProvider(),
    )
    pulse = next(
        section for section in result.module_sections if section.key == "market-pulse"
    )
    scan = next(item for item in pulse.items if item.label == "扫描样本强弱差")

    assert scan.summary == "待补"
    assert scan.risk == "扫描样本未返回"
    assert "候选扫描样本" not in json.dumps(result.to_public_dict(), ensure_ascii=False)


def test_market_risk_keeps_observed_fact_without_account_action(monkeypatch) -> None:
    provider = LocalFixtureProvider()
    market = replace(
        build_market_report(provider),
        risks=["北向大额净流出", "建议降低仓位"],
    )
    monkeypatch.setattr(
        "stock_ts.research_fallback.build_market_report",
        lambda _provider: market,
    )

    result = build_local_research("market", ResearchContext(), provider=provider)
    risk_finding = next(item for item in result.findings if item.title == "当日风险事实")

    assert risk_finding.summary == "北向大额净流出"
    assert result.primary_risk == "北向大额净流出"
    assert "仓位" not in json.dumps(result.to_public_dict(), ensure_ascii=False)
    assert "建议" not in risk_finding.summary


def test_market_risk_merges_and_deduplicates_hard_gate_with_observed_fact(
    monkeypatch,
) -> None:
    provider = LocalFixtureProvider()
    market = replace(
        build_market_report(provider),
        limit_down_count=50,
        risks=["跌停压力进入高风险区", "北向大额净流出", "建议降低仓位"],
    )
    monkeypatch.setattr(
        "stock_ts.research_fallback.build_market_report",
        lambda _provider: market,
    )

    result = build_local_research("market", ResearchContext(), provider=provider)
    risk_finding = next(item for item in result.findings if item.title == "当日风险事实")

    assert risk_finding.summary == "跌停压力进入高风险区；北向大额净流出"
    assert risk_finding.summary.count("跌停压力进入高风险区") == 1
    assert result.primary_risk == risk_finding.summary
    assert "仓位" not in json.dumps(result.to_public_dict(), ensure_ascii=False)


def test_strong_market_breadth_remains_descriptive() -> None:
    result = build_local_research(
        "market",
        ResearchContext(),
        provider=StrongBreadthProvider(),
    )

    assert result.decision_label == "宽度偏强"
    assert "宽度偏强" in result.verdict


def test_negative_events_do_not_increase_positive_candidate_evidence() -> None:
    result = build_local_research(
        "opportunity",
        ResearchContext(),
        provider=NegativeEventCandidateProvider(),
    )
    candidates = next(
        section
        for section in result.module_sections
        if section.key == "opportunity-candidates"
    )
    scores = {
        item.name: next(
            fact.value for fact in item.facts if fact.label == "持续性评分"
        )
        for item in candidates.items
    }

    assert scores["无事件趋势"] == scores["负面事件趋势"]


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
