import json

from stock_ts.research_engine import (
    ResearchFact,
    ResearchFinding,
    ResearchModuleItem,
    ResearchWorkspaceResult,
)
from stock_ts.research_fusion import fuse_research_results


def _result(
    *,
    ok: bool = True,
    verdict: str,
    action: str,
    risk: str,
    decision_label: str,
    items: tuple[ResearchModuleItem, ...],
    delivery: str,
) -> ResearchWorkspaceResult:
    return ResearchWorkspaceResult(
        ok=ok,
        status="partial" if ok else "unavailable",
        module="stock",
        generated_at="2026-07-15T20:00:00+08:00",
        verdict=verdict,
        action=action,
        primary_risk=risk,
        findings=(ResearchFinding(title="本地价格", summary="趋势证据已确认。"),),
        coverage_ready=sum(item.status == "ready" for item in items),
        coverage_total=len(items),
        delivery=delivery,
        data_label="本地分析" if delivery == "local_fallback" else "实时研究",
        module_items=items,
        decision_label=decision_label,
    )


def test_fusion_preserves_local_decision_and_fills_missing_evidence() -> None:
    local = _result(
        verdict="本地判断：防守观察",
        action="不加仓；等待价格和资金确认。",
        risk="跌破失效线时降低风险。",
        decision_label="防守观察",
        delivery="local_fallback",
        items=(
            ResearchModuleItem(
                kind="stock_dimension",
                label="财务质量",
                summary="财务证据待补。",
                risk="证据待补。",
                status="missing",
            ),
            ResearchModuleItem(
                kind="stock_dimension",
                label="行情资金",
                summary="价格趋势已确认。",
                risk="跌破均线则失效。",
                status="ready",
            ),
        ),
    )
    enriched = _result(
        verdict="外部结论不应接管",
        action="外部动作不应接管",
        risk="外部风险不应覆盖",
        decision_label="谨慎进攻",
        delivery="live",
        items=(
            ResearchModuleItem(
                kind="stock_dimension",
                label="财务质量",
                summary="营收和利润同比改善。",
                risk="现金流仍需复核。",
                status="ready",
                facts=(ResearchFact(label="来源", value="同花顺问财 skill trace_id"),),
            ),
        ),
    )

    fused = fuse_research_results(local, enriched)

    assert fused.verdict == local.verdict
    assert fused.action == local.action
    assert fused.primary_risk == local.primary_risk
    assert fused.decision_label == local.decision_label
    assert fused.delivery == "hybrid"
    assert fused.data_label == "综合证据"
    assert fused.coverage_ready > local.coverage_ready
    financial = next(item for item in fused.module_items if item.label == "财务质量")
    assert financial.status == "ready"
    assert "营收和利润" in financial.summary

    public_text = json.dumps(fused.to_public_dict(), ensure_ascii=False)
    for forbidden in ("问财", "iWencai", "同花顺", "skill", "trace_id", "api_key"):
        assert forbidden.casefold() not in public_text.casefold()


def test_unavailable_enrichment_returns_local_result_without_decision_changes() -> None:
    local = _result(
        verdict="本地判断",
        action="本地动作",
        risk="本地风险",
        decision_label="均衡",
        delivery="local_fallback",
        items=(
            ResearchModuleItem(
                kind="market_metric",
                label="证据覆盖",
                summary="67%",
                risk="主题数据待补。",
                status="ready",
            ),
        ),
    )
    unavailable = _result(
        ok=False,
        verdict="服务不可用",
        action="稍后重试",
        risk="服务失败",
        decision_label="待确认",
        delivery="unavailable",
        items=(),
    )

    fused = fuse_research_results(local, unavailable)

    assert fused == local
