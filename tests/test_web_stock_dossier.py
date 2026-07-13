from __future__ import annotations

from stock_ts.research.evidence import EvidenceItem, EvidenceStatus
from stock_ts.research.stock_dossier_models import (
    DecisionStep,
    DiagnosticBlock,
    DossierScenario,
    DossierVerdict,
    PositionGuidance,
    ProfessionalStockDossier,
    RiskItem,
)
from stock_ts.webapp.stock_workspace import render_stock_workspace


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
                ("当前状态", "current", "风险规避", "不新开仓"),
                ("转强触发", "upgrade", "站稳 10.80", "重新评估"),
                ("加仓确认", "confirm", "回踩不破", "小仓验证"),
                ("降级触发", "downgrade", "跌破 9.50", "降低风险"),
                ("失效退出", "invalid", "跌破 9.40", "终止论点"),
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
    )


def test_workspace_leads_with_one_decision_and_five_step_rail() -> None:
    html = render_stock_workspace(_dossier())

    assert html.index("投委会结论") < html.index("诊断底稿")
    assert html.count('data-primary-stock-verdict="true"') == 1
    assert html.count('class="decision-rail-step') == 5
    assert "当前状态" in html
    assert "转强触发" in html
    assert "加仓确认" in html
    assert "降级触发" in html
    assert "失效退出" in html


def test_workspace_places_risk_before_scenarios_and_labels_confidence() -> None:
    html = render_stock_workspace(_dossier())

    assert html.index("风险登记表") < html.index("三种情景")
    assert "证据完整度" in html
    assert "上涨概率" not in html
    assert "仓位上限" in html
    assert "禁止动作" in html
