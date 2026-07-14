from __future__ import annotations

import inspect

from stock_ts import web
from stock_ts.providers.sample import SampleDataProvider
from stock_ts.research.evidence import EvidenceItem, EvidenceStatus
from stock_ts.research.stock_dossier_models import (
    DecisionStep,
    DiagnosticBlock,
    DossierScenario,
    DossierVerdict,
    PositionGuidance,
    ProfessionalStockDossier,
    RiskItem,
    ThesisFramework,
    WeightedEvidence,
)
from stock_ts.webapp.stock_workspace import render_stock_workspace
from stock_ts.webapp.styles import CSS


def _dossier() -> ProfessionalStockDossier:
    return ProfessionalStockDossier(
        code="603278",
        name="大业股份",
        trade_date="2026-07-10",
        latest_close=10.05,
        verdict=DossierVerdict(
            stance="风险规避",
            action="不新开仓",
            evidence_grade="B",
            confidence=80,
            horizon="5-20 个交易日",
            thesis="亏损与高质押风险压制当前风险收益比。",
            strongest_evidence="反弹尝试，尚未修复中期趋势。",
            strongest_counter_evidence="累计质押占其持股65.72%",
            next_review="下一交易日收盘或重大公告后复核。",
        ),
        decision_steps=tuple(
            DecisionStep(label, state, condition, consequence)
            for label, state, condition, consequence in (
                ("当前判断", "current", "风险规避", "不新开仓"),
                ("研究转强", "upgrade", "盈利修复且质押解除", "进入价格确认"),
                ("价格确认", "confirm", "站稳 10.80", "小仓验证"),
                ("降级条件", "downgrade", "跌破 9.50", "降低风险"),
                ("论点失效", "invalid", "跌破 9.40", "终止论点"),
            )
        ),
        diagnostics=(
            DiagnosticBlock(
                "财务质量",
                "degraded",
                "净利润为负，当前处于亏损状态。",
                ("净利润 -24557.60",),
                ("盈利为负",),
                "仅有财务截面。",
            ),
            DiagnosticBlock(
                "估值",
                "degraded",
                "PE 失去解释力；PB 口径冲突。",
                ("来源 PB 0.18x", "反算 PB 1.77x"),
                ("口径冲突",),
                "不得使用低估结论。",
            ),
        ),
        risks=(
            RiskItem(
                "high",
                "股权质押",
                "累计质押占其持股65.72%",
                "限制新开仓",
                "复核平仓风险",
            ),
        ),
        position=PositionGuidance(
            audience="未持仓",
            current_action="等待风险解除",
            position_cap="0%",
            risk_budget="不分配新增风险",
            entry_trigger="站稳 10.80",
            add_trigger="回踩不破",
            reduce_trigger="跌破 9.50",
            invalidation="跌破 9.40",
            prohibited_action="禁止追反弹、摊低成本",
        ),
        scenarios=tuple(
            DossierScenario(name, premise, confirmation, action, invalidation, "fixture")
            for name, premise, confirmation, action, invalidation in (
                ("改善", "亏损收窄", "站稳压力", "小仓验证", "重新走弱"),
                ("基准", "亏损延续", "区间运行", "继续观察", "风险升级"),
                ("恶化", "质押风险发酵", "跌破失效", "继续规避", "风险解除"),
            )
        ),
        evidence=(
            EvidenceItem(
                "估值",
                "tdx.profile.finance",
                "2026-05-18",
                EvidenceStatus.DEGRADED,
                "PB 口径冲突",
            ),
        ),
        thesis=ThesisFramework(
            headline="投资假设尚未成立：盈利修复与质押风险解除必须同时发生",
            core_conflict="盈利修复能否覆盖股权质押造成的风险折价。",
            causal_chain=(
                "事实：净利润为负，存在高比例质押",
                "推断：只有盈利修复且风险解除，估值锚才可能恢复",
                "验证：站稳 10.80；跌破 9.40 论点失效",
            ),
            expectation_gap="未接入一致预期，预期差不可量化。",
            valuation_fit="亏损阶段 PE 失效，PB 口径仍需核对。",
            catalyst_window="下一份财报或重大公告",
            key_unknown="质押影响范围与盈利修复节奏",
            falsifier="质押风险升级、盈利恶化或跌破 9.40。",
        ),
        weighted_evidence=tuple(
            WeightedEvidence(dimension, importance, direction, fact, inference, unknown)
            for dimension, importance, direction, fact, inference, unknown in (
                ("盈利质量", "高", "反证", "净利润为负", "盈利压低风险预算", "下一财报"),
                ("估值与预期差", "高", "未知", "PE 失效", "不能判断低估", "一致预期"),
                ("事件与治理", "高", "反证", "高比例质押", "约束新风险", "公告原文"),
                ("行业位置", "中", "未知", "排名缺失", "不自动加分", "同业比较"),
                ("资金与价格", "中", "中性", "反弹未反转", "只确认时点", "持续资金"),
            )
        ),
    )


def test_workspace_reads_as_thesis_conditions_execution_evidence_and_scenarios() -> None:
    html = render_stock_workspace(_dossier())
    labels = [
        "投资判断",
        "核心矛盾",
        "决策条件",
        "执行边界",
        "论点链",
        "关键证据",
        "风险反证",
        "三情景",
        "证据账本",
    ]

    assert all(label in html for label in labels)
    assert [html.index(label) for label in labels] == sorted(
        html.index(label) for label in labels
    )
    assert "诊断底稿" not in html.split("证据账本", 1)[0]
    assert "多角色分析方法" not in html
    assert html.count('data-primary-stock-verdict="true"') == 1


def test_workspace_leads_with_one_decision_and_five_step_rail() -> None:
    html = render_stock_workspace(_dossier())

    assert html.index("投资判断") < html.index("关键证据")
    assert html.count('data-primary-stock-verdict="true"') == 1
    assert html.count('class="decision-rail-step') == 5
    assert "当前判断" in html
    assert "研究转强" in html
    assert "价格确认" in html
    assert "降级条件" in html
    assert "论点失效" in html


def test_workspace_places_risk_before_scenarios_and_labels_confidence() -> None:
    html = render_stock_workspace(_dossier())

    assert html.index("风险反证") < html.index("三情景")
    assert "完整度" in html
    assert "上涨概率" not in html
    assert "仓位 / 风险预算" in html
    assert "禁止动作" in html
    assert html.count('class="stock-evidence essence-evidence"') == 1
    assert "RISK FIRST" not in html
    assert "RESEARCH FILE" not in html


def test_real_stock_orchestration_builds_one_dossier() -> None:
    source = inspect.getsource(web._render_compact_stock_module)

    assert "build_professional_stock_dossier" in source
    assert source.count("render_stock_workspace(") == 1
    assert "legacy_trade_plan =" not in source


def test_stock_page_has_no_duplicate_primary_trade_conclusion() -> None:
    html = web.render_page(
        stock_code="603278",
        provider_name="sample",
        provider=SampleDataProvider(),
        holdings_path="data/portfolio/holdings.csv",
    )

    assert html.count('data-primary-stock-verdict="true"') == 1
    assert html.count("投资判断") == 1
    assert "多角色分析方法" not in html


def test_dossier_styles_define_desktop_mobile_and_reduced_motion() -> None:
    assert ".stock-dossier-grid" in CSS
    assert ".decision-rail-step" in CSS
    assert ".risk-register" in CSS
    assert "font-variant-numeric: tabular-nums" in CSS
    assert "@media (max-width: 760px)" in CSS
    assert "prefers-reduced-motion" in CSS
    mobile_css = CSS.split("@media (max-width:680px)", 1)[1]
    assert ".stock-identity-strip" in mobile_css
    assert "grid-template-columns:minmax(0,1.4fr)" in mobile_css


def test_v2_styles_define_thesis_spine_evidence_directions_and_mobile_stack() -> None:
    assert ".thesis-spine" in CSS
    assert ".weighted-evidence-row" in CSS
    assert '[data-direction="反证"]' in CSS
    assert '[data-direction="未知"]' in CSS
    assert ".stock-evidence summary:focus-visible" in CSS
    mobile = CSS.split("@media (max-width: 760px)", 1)[1]
    assert ".thesis-spine" in mobile
    assert "grid-template-columns:1fr" in mobile
    assert "prefers-reduced-motion" in CSS


def test_mobile_stock_header_removes_duplicate_height_before_verdict() -> None:
    mobile = CSS.split("@media (max-width:680px)", 1)[1]

    assert '.workspace-pane[data-workspace="stock"] .module-header' in mobile
    assert "display:none" in mobile
    assert ".stock-identity-strip" in mobile
    assert "grid-template-columns:minmax(0,1.4fr) minmax(0,.7fr) minmax(0,1fr) auto" in mobile
    assert ".stock-identity-strip .module-refresh-tools > span" in mobile


def test_mobile_data_quality_summary_uses_readable_grid() -> None:
    mobile_css = CSS.split("@media (max-width: 680px)", 1)[1]

    assert ".data-center-summary" in mobile_css
    assert "grid-template-columns:minmax(0,1fr) auto" in mobile_css
    assert ".data-center-summary > strong" in mobile_css
