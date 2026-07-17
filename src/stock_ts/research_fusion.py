from __future__ import annotations

from dataclasses import replace

from .research_engine import (
    ResearchFact,
    ResearchFinding,
    ResearchModuleItem,
    ResearchModuleSection,
    ResearchWorkspaceResult,
)
from .research_method import attach_method_section

_INTERNAL_TERMS = (
    "问财",
    "iwencai",
    "同花顺",
    "skill",
    "trace_id",
    "api_key",
    "gateway",
)

_STOCK_EVIDENCE_MAP = {
    "财务质量": "估值基本面",
    "经营结构": "估值基本面",
    "机构预期": "估值基本面",
    "行业位置": "估值基本面",
    "研报观点": "估值基本面",
    "事件风险": "消息事件",
    "公告事项": "消息事件",
    "行情资金": "资金行为",
}


def fuse_research_results(
    local: ResearchWorkspaceResult,
    enriched: ResearchWorkspaceResult,
) -> ResearchWorkspaceResult:
    if local.module != enriched.module:
        raise ValueError("研究模块不一致，不能融合。")
    if not enriched.ok:
        return local

    enriched_items = tuple(_safe_external_item(item) for item in enriched.module_items)
    merged_items = _merge_module_items(local.module_items, enriched_items)
    base_sections = tuple(
        section
        for section in local.module_sections
        if section.key != "professional-method"
    )
    merged_sections = _merge_sections(base_sections, enriched_items)
    merged_findings = _merge_findings(local.findings, enriched.findings)
    ready = sum(item.status == "ready" for item in merged_items)
    total = max(local.coverage_total, len(merged_items))
    filled_labels = {item.label for item in merged_items if item.status == "ready"}
    missing = tuple(label for label in local.missing_sections if label not in filled_labels)

    fused = replace(
        local,
        status="complete" if total and ready == total else "partial",
        findings=merged_findings,
        details=local.details + enriched.details,
        missing_sections=missing,
        coverage_ready=ready,
        coverage_total=total,
        delivery="hybrid",
        data_label="综合证据",
        fallback_reason="",
        module_items=merged_items,
        module_sections=merged_sections,
    )
    return attach_method_section(fused)


def _merge_module_items(
    local_items: tuple[ResearchModuleItem, ...],
    enriched_items: tuple[ResearchModuleItem, ...],
) -> tuple[ResearchModuleItem, ...]:
    enriched_by_label = {
        _item_key(item): item for item in enriched_items if item.status == "ready"
    }
    merged: list[ResearchModuleItem] = []
    local_keys = {_item_key(item) for item in local_items}
    for local_item in local_items:
        enriched_item = enriched_by_label.get(_item_key(local_item))
        if enriched_item is None or local_item.status == "ready":
            merged.append(local_item)
            continue
        merged.append(
            replace(
                local_item,
                summary=enriched_item.summary or local_item.summary,
                risk=enriched_item.risk or local_item.risk,
                status="ready",
                facts=_merge_facts(local_item.facts, enriched_item.facts),
            )
        )
    additions = [
        item
        for item in enriched_items
        if item.status == "ready" and _item_key(item) not in local_keys
    ]
    if additions and any(item.kind == "stock_missing_evidence" for item in merged):
        filled = {item.label for item in additions}
        compacted: list[ResearchModuleItem] = []
        for item in merged:
            if item.kind != "stock_missing_evidence":
                compacted.append(item)
                continue
            remaining = [
                label.strip()
                for label in item.summary.split("、")
                if label.strip() and label.strip() not in filled
            ]
            compacted.extend(additions)
            if remaining:
                compacted.append(replace(item, summary="、".join(remaining)))
        merged = compacted
    return tuple(merged)


def _merge_sections(
    sections: tuple[ResearchModuleSection, ...],
    enriched_items: tuple[ResearchModuleItem, ...],
) -> tuple[ResearchModuleSection, ...]:
    evidence_by_dimension: dict[str, list[ResearchModuleItem]] = {}
    for item in enriched_items:
        dimension = _STOCK_EVIDENCE_MAP.get(item.label)
        if dimension and item.status == "ready":
            evidence_by_dimension.setdefault(dimension, []).append(item)

    merged_sections = []
    for section in sections:
        if section.key != "stock-evidence":
            merged_sections.append(section)
            continue
        merged_items = []
        for item in section.items:
            additions = evidence_by_dimension.get(item.label, [])
            facts = item.facts + tuple(
                ResearchFact(label="补充证据", value=addition.summary)
                for addition in additions
                if addition.summary and not _contains_internal_term(addition.summary)
            )
            merged_items.append(replace(item, facts=_dedupe_facts(facts)))
        merged_sections.append(replace(section, items=tuple(merged_items)))
    return tuple(merged_sections)


def _merge_findings(
    local: tuple[ResearchFinding, ...],
    enriched: tuple[ResearchFinding, ...],
) -> tuple[ResearchFinding, ...]:
    merged: list[ResearchFinding] = list(local)
    seen = {(item.title, item.summary) for item in local}
    for item in enriched:
        key = (item.title, item.summary)
        if key in seen or _contains_internal_term(" ".join(key)):
            continue
        merged.append(replace(item, facts=_safe_facts(item.facts)))
        seen.add(key)
        if len(merged) >= 3:
            break
    return tuple(merged[:3])


def _safe_external_item(item: ResearchModuleItem) -> ResearchModuleItem:
    return replace(item, facts=_safe_facts(item.facts))


def _safe_facts(facts: tuple[ResearchFact, ...]) -> tuple[ResearchFact, ...]:
    return tuple(
        fact
        for fact in facts
        if not _contains_internal_term(f"{fact.label} {fact.value}")
    )


def _merge_facts(
    local: tuple[ResearchFact, ...],
    enriched: tuple[ResearchFact, ...],
) -> tuple[ResearchFact, ...]:
    return _dedupe_facts(local + _safe_facts(enriched))


def _dedupe_facts(facts: tuple[ResearchFact, ...]) -> tuple[ResearchFact, ...]:
    result: list[ResearchFact] = []
    seen: set[tuple[str, str]] = set()
    for fact in facts:
        key = (fact.label, fact.value)
        if key in seen:
            continue
        seen.add(key)
        result.append(fact)
    return tuple(result)


def _item_key(item: ResearchModuleItem) -> str:
    return (item.label or item.name or item.code).strip().casefold()


def _contains_internal_term(value: str) -> bool:
    normalized = value.casefold()
    return any(term.casefold() in normalized for term in _INTERNAL_TERMS)
