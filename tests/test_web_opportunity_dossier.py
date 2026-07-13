from __future__ import annotations

import inspect
from dataclasses import replace

from stock_ts.providers.sample import SampleDataProvider
from stock_ts.research.evidence import EvidenceStatus
from stock_ts.research.opportunity_dossier_models import (
    CandidateDecision,
    FunnelStage,
    OpportunityDossier,
    OpportunityGate,
    OpportunityRisk,
)
from stock_ts.web import _render_hot_opportunity_module, render_page
from stock_ts.webapp.opportunity_workspace import render_opportunity_workspace


def _dossier(*, state: str = "开放验证") -> OpportunityDossier:
    gate = OpportunityGate(
        state=state,
        action="仅验证 1 只证据较完整候选" if state != "数据暂停" else "停止排序，只保留证据审计",
        risk_budget="50%-70%" if state != "数据暂停" else "0%",
        data_status="complete" if state != "数据暂停" else "stale",
        scanned_count=5200,
        evidence_ready_count=2,
        eligible_count=1 if state != "数据暂停" else 0,
        thesis="候选只获得进入个股档案复核的资格。",
        next_step="逐只进入个股档案确认失效条件。",
    )
    funnel = tuple(
        FunnelStage(name, count, status, note)
        for name, count, status, note in (
            ("扫描范围", 5200, "audit", "全市场候选源"),
            ("证据就绪", 2, "evidence", "价格与证据可审计"),
            ("风险排除", 1, "excluded", "明确风险先剔除"),
            ("只观察", 1, "watch", "等待确认"),
            ("可验证", 1 if state != "数据暂停" else 0, "eligible", "进入个股档案"),
        )
    )
    candidates = (
        CandidateDecision(
            code="600001",
            name="研究股份",
            sector="机器人",
            state="可验证" if state != "数据暂停" else "待补数据",
            strategy="主线强势与资金承接",
            evidence=("机器人强度靠前", "收盘位于短期均线上方"),
            counter_evidence=("短线涨幅较大",),
            data_date="2026-07-13",
            data_status=(EvidenceStatus.COMPLETE if state != "数据暂停" else EvidenceStatus.STALE),
            next_verification="进入个股档案复核财务、估值、事件风险与价格触发",
            exclusion_reason="",
        ),
    )
    return OpportunityDossier(
        gate=gate,
        funnel=funnel,
        candidates=candidates,
        risks=(OpportunityRisk("市场闸门", "high", "情绪分歧", "限制验证范围"),),
        source_notes=("按趋势、量价、板块、资金和风险扣分排序",),
    )


def test_opportunity_workspace_is_gate_first_and_not_buy_first() -> None:
    html = render_opportunity_workspace(
        _dossier(),
        provider_name="sample",
        holdings_path="data/portfolio/holdings.csv",
    )

    assert html.count('data-primary-opportunity-verdict="true"') == 1
    assert html.index("机会总闸门") < html.index("研究候选")
    assert "支持证据" in html
    assert "最大反证" in html
    assert "进入个股分析" in html
    assert "推荐买入" not in html
    assert "推荐股票" not in html
    assert "买入建议" not in html


def test_stale_workspace_exposes_zero_eligible_candidates() -> None:
    html = render_opportunity_workspace(
        _dossier(state="数据暂停"),
        provider_name="sample",
        holdings_path="data/portfolio/holdings.csv",
    )

    assert "数据暂停" in html
    assert "可验证" in html
    assert "待补数据" in html
    assert "0%" in html
    assert "推荐" not in html


def test_web_opportunity_module_builds_and_renders_one_dossier() -> None:
    source = inspect.getsource(_render_hot_opportunity_module)

    assert source.count("build_opportunity_dossier(") == 1
    assert source.count("render_opportunity_workspace(") == 1
    assert "_render_opportunity_buy_sell_guidance(" not in source


def test_stale_web_page_has_no_recommendation_surface() -> None:
    html = render_page(
        stock_code="600519",
        provider_name="sample",
        provider=SampleDataProvider(),
        holdings_path="data/portfolio/holdings.csv",
    )
    start = html.index('id="module-opportunity"')
    opportunity_html = html[start:]

    assert "数据暂停" in opportunity_html
    assert "待补数据" in opportunity_html
    assert "推荐买入" not in opportunity_html
    assert "推荐股票" not in opportunity_html


def test_opportunity_workspace_keeps_six_front_candidates_and_all_records() -> None:
    dossier = _dossier()
    seed = dossier.candidates[0]
    candidates = tuple(
        replace(seed, code=f"6000{index:02d}", name=f"候选{index:02d}")
        for index in range(1, 9)
    )
    html = render_opportunity_workspace(
        replace(dossier, candidates=candidates),
        provider_name="sample",
        holdings_path="data/portfolio/holdings.csv",
    )

    assert html.count("data-opportunity-stock-row") == 8
    front = html.split('class="candidate-overflow', 1)[0]
    assert front.count("data-opportunity-stock-row") == 6
    assert "查看其余 2 只候选" in html
    assert html.count("进入个股分析") == 8
