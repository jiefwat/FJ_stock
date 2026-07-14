from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any

from .iwencai import SKILLS, IwencaiSkillClient

WORKSPACE_CAPABILITIES = {
    "market": ("index", "macro", "sector_selector", "news"),
    "portfolio": ("event", "announcement", "consensus", "market"),
    "stock": ("finance", "business", "consensus", "event"),
    "opportunity": ("sector_selector", "astock_selector", "event", "news"),
}

CAPABILITY_LABELS = {
    "index": "指数状态",
    "macro": "宏观环境",
    "sector_selector": "行业方向",
    "news": "市场事件",
    "event": "事件风险",
    "announcement": "公告事项",
    "consensus": "机构预期",
    "market": "行情资金",
    "finance": "财务质量",
    "business": "经营结构",
    "astock_selector": "候选筛选",
}

MODULE_COPY = {
    "market": {
        "complete": "市场关键证据已更新，进入风险与主线确认。",
        "partial": "部分市场证据已更新，当前判断按谨慎级别处理。",
        "action": "先确认指数、宏观与主线是否同向，再决定风险暴露。",
        "risk": "市场证据可能不同步，避免只按单一热点行动。",
    },
    "portfolio": {
        "complete": "重点持仓风险证据已更新，进入逐只复核。",
        "partial": "部分持仓证据缺失，当前只处理已确认的风险。",
        "action": "先处理事件与预期恶化的持仓，再检查价格和资金确认。",
        "risk": "持仓数量、成本和权重未参与研究，仓位动作需由账户侧另行约束。",
    },
    "stock": {
        "complete": "公司经营、财务、预期与事件证据已更新。",
        "partial": "公司研究证据不完整，当前结论只作条件复核。",
        "action": "先核对关键变化与反证，再进入价格和仓位验证。",
        "risk": "单一数据变化不能独立构成买卖依据。",
    },
    "opportunity": {
        "complete": "行业、候选与事件线索已更新，进入风险排除。",
        "partial": "机会线索不完整，当前只保留可核查候选。",
        "action": "先确认方向持续性，再逐只排除事件与基本风险。",
        "risk": "热点强度可能快速衰减，候选不等于交易信号。",
    },
}

PUBLIC_REPLACEMENTS = {
    "问财": "研究服务",
    "iWencai": "研究服务",
    "IWENCAI": "研究服务",
    "iwencai": "研究服务",
    "同花顺": "数据服务",
    "Skill": "能力",
    "SKILL": "能力",
    "skill": "能力",
}

INTERNAL_FIELD_TOKENS = (
    "trace",
    "skill",
    "provider",
    "authorization",
    "api_key",
    "apikey",
    "source_url",
    "gateway",
    "channel",
)


@dataclass(frozen=True)
class ResearchTarget:
    code: str = ""
    name: str = ""
    sector: str = ""


@dataclass(frozen=True)
class ResearchContext:
    code: str = ""
    name: str = ""
    sector: str = ""
    holdings: tuple[ResearchTarget, ...] = ()


@dataclass(frozen=True)
class CapabilityRequest:
    capability: str
    query: str
    target: ResearchTarget = ResearchTarget()


@dataclass(frozen=True)
class ResearchFact:
    label: str
    value: str

    def to_public_dict(self) -> dict[str, str]:
        return {"label": self.label, "value": self.value}


@dataclass(frozen=True)
class ResearchFinding:
    title: str
    summary: str
    target: str = ""
    facts: tuple[ResearchFact, ...] = ()

    def to_public_dict(self) -> dict[str, object]:
        return {
            "title": self.title,
            "summary": self.summary,
            "target": self.target,
            "facts": [item.to_public_dict() for item in self.facts],
        }


@dataclass(frozen=True)
class ResearchDetail:
    section: str
    target: str
    status: str
    findings: tuple[ResearchFinding, ...] = ()

    def to_public_dict(self) -> dict[str, object]:
        return {
            "section": self.section,
            "target": self.target,
            "status": self.status,
            "findings": [item.to_public_dict() for item in self.findings],
        }


@dataclass(frozen=True)
class ResearchWorkspaceResult:
    ok: bool
    status: str
    module: str
    generated_at: str
    verdict: str
    action: str
    primary_risk: str
    findings: tuple[ResearchFinding, ...] = ()
    details: tuple[ResearchDetail, ...] = ()
    missing_sections: tuple[str, ...] = ()

    def to_public_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "status": self.status,
            "module": self.module,
            "generated_at": self.generated_at,
            "verdict": self.verdict,
            "action": self.action,
            "primary_risk": self.primary_risk,
            "findings": [item.to_public_dict() for item in self.findings],
            "details": [item.to_public_dict() for item in self.details],
            "missing_sections": list(self.missing_sections),
        }


@dataclass(frozen=True)
class _CapabilityOutcome:
    request: CapabilityRequest
    rows: tuple[tuple[ResearchFact, ...], ...] = ()
    failed: bool = False


class ResearchWorkspaceService:
    def __init__(
        self,
        *,
        client_factory: Callable[[], Any] = IwencaiSkillClient,
        cache_ttl: float = 300,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.client_factory = client_factory
        self.cache_ttl = max(cache_ttl, 0)
        self.clock = clock
        self._cache: dict[
            tuple[object, ...], tuple[float, ResearchWorkspaceResult]
        ] = {}
        self._cache_lock = Lock()

    def research(
        self,
        module: str,
        context: ResearchContext,
        *,
        refresh: bool = False,
    ) -> ResearchWorkspaceResult:
        normalized = module.strip().lower()
        requests = build_workspace_queries(normalized, context)
        cache_key = _research_cache_key(normalized, context)
        if not refresh:
            cached = self._cached(cache_key)
            if cached is not None:
                return cached

        client = self.client_factory()
        outcomes = self._execute_bundle(client, requests)
        result = _build_workspace_result(normalized, outcomes)
        if result.ok and self.cache_ttl > 0:
            with self._cache_lock:
                self._cache[cache_key] = (self.clock() + self.cache_ttl, result)
        return result

    def _cached(self, cache_key: tuple[object, ...]) -> ResearchWorkspaceResult | None:
        with self._cache_lock:
            cached = self._cache.get(cache_key)
            if cached is None:
                return None
            expires_at, result = cached
            if expires_at <= self.clock():
                self._cache.pop(cache_key, None)
                return None
            return result

    @staticmethod
    def _execute_bundle(
        client: Any,
        requests: tuple[CapabilityRequest, ...],
    ) -> tuple[_CapabilityOutcome, ...]:
        if not requests:
            return ()
        outcomes_by_index: dict[int, _CapabilityOutcome] = {}
        with ThreadPoolExecutor(max_workers=min(4, len(requests))) as executor:
            futures = {
                executor.submit(_execute_capability, client, request): index
                for index, request in enumerate(requests)
            }
            for future in as_completed(futures):
                index = futures[future]
                try:
                    outcomes_by_index[index] = future.result()
                except Exception:
                    outcomes_by_index[index] = _CapabilityOutcome(
                        request=requests[index],
                        failed=True,
                    )
        return tuple(outcomes_by_index[index] for index in range(len(requests)))


def workspace_capabilities(module: str) -> tuple[str, ...]:
    normalized = module.strip().lower()
    try:
        return WORKSPACE_CAPABILITIES[normalized]
    except KeyError as exc:
        raise ValueError("不支持的研究模块。") from exc


def build_workspace_queries(
    module: str,
    context: ResearchContext,
) -> tuple[CapabilityRequest, ...]:
    capabilities = workspace_capabilities(module)
    if module == "portfolio":
        return tuple(
            CapabilityRequest(
                capability=capability,
                query=_target_query(target, _prompt_for(module, capability)),
                target=target,
            )
            for target in context.holdings[:3]
            for capability in capabilities
        )
    if module == "stock":
        target = ResearchTarget(code=context.code, name=context.name)
        if not target.code and not target.name:
            raise ValueError("请输入股票代码或名称。")
        return tuple(
            CapabilityRequest(
                capability=capability,
                query=_target_query(target, _prompt_for(module, capability)),
                target=target,
            )
            for capability in capabilities
        )
    if module == "opportunity":
        prefix = _clean_text(context.sector, 64) or "A股"
        return tuple(
            CapabilityRequest(
                capability=capability,
                query=f"{prefix} {_prompt_for(module, capability)}",
            )
            for capability in capabilities
        )
    return tuple(
        CapabilityRequest(
            capability=capability,
            query=_prompt_for(module, capability),
        )
        for capability in capabilities
    )


def _target_query(target: ResearchTarget, prompt: str) -> str:
    identity = " ".join(
        value
        for value in (
            _clean_text(target.name, 64),
            _clean_text(target.code, 32),
        )
        if value
    )
    return f"{identity} {prompt}".strip()


def _prompt_for(module: str, capability: str) -> str:
    prompts = {
        ("market", "index"): "主要指数最新趋势、强弱、成交和关键位置",
        ("market", "macro"): "近期影响A股风险偏好的宏观指标与政策变化",
        ("market", "sector_selector"): "当前强度、成交额和持续性靠前的行业板块",
        ("market", "news"): "近期影响A股风险偏好的重要新闻与风险事件",
        ("portfolio", "event"): "近期业绩预告、解禁、质押、监管和经营风险",
        ("portfolio", "announcement"): "近期公告中需要持有人重点复核的事项",
        ("portfolio", "consensus"): "机构盈利预期、评级及其上调或下修变化",
        ("portfolio", "market"): "近期价格、成交量和资金异动",
        ("stock", "finance"): "收入、利润、现金流、ROE和负债质量变化",
        ("stock", "business"): "主营结构、竞争位置、客户供应链与经营变化",
        ("stock", "consensus"): "未来两年盈利预期、评级和预期变化",
        ("stock", "event"): "近期业绩、解禁、质押、监管和事件风险",
        ("opportunity", "sector_selector"): "筛选强度、成交和持续性靠前的行业方向",
        ("opportunity", "astock_selector"): "筛选盈利改善、成交活跃且风险可核查的股票",
        ("opportunity", "event"): "近期可核查的业绩、公告和事件催化",
        ("opportunity", "news"): "近期市场主线新闻及需要排除的风险",
    }
    return prompts[(module, capability)]


def _clean_text(value: str, limit: int) -> str:
    cleaned = "".join(character if character.isprintable() else " " for character in value)
    return " ".join(cleaned.split())[:limit]


def _execute_capability(client: Any, request: CapabilityRequest) -> _CapabilityOutcome:
    raw = client.query(SKILLS[request.capability], request.query)
    return _CapabilityOutcome(request=request, rows=_normalize_rows(raw))


def _normalize_rows(raw: Mapping[str, object]) -> tuple[tuple[ResearchFact, ...], ...]:
    rows = raw.get("datas")
    if not isinstance(rows, list):
        rows = raw.get("data")
    if not isinstance(rows, list):
        return ()
    normalized: list[tuple[ResearchFact, ...]] = []
    for row in rows[:3]:
        if not isinstance(row, Mapping):
            continue
        facts: list[ResearchFact] = []
        for key, value in row.items():
            normalized_key = str(key).strip().lower()
            if any(token in normalized_key for token in INTERNAL_FIELD_TOKENS):
                continue
            if len(facts) >= 4:
                break
            label = _public_text(str(key), 40)
            rendered = _render_value(value)
            if not label or not rendered:
                continue
            facts.append(ResearchFact(label=label, value=rendered))
        if facts:
            normalized.append(tuple(facts))
    return tuple(normalized)


def _render_value(value: object) -> str:
    if isinstance(value, (str, int, float, bool)):
        return _public_text(str(value), 160)
    if isinstance(value, list):
        return _public_text("、".join(str(item) for item in value[:3]), 160)
    if isinstance(value, Mapping):
        pairs = [f"{key}:{item}" for key, item in list(value.items())[:3]]
        return _public_text("；".join(pairs), 160)
    return ""


def _public_text(value: str, limit: int) -> str:
    cleaned = _clean_text(value, limit)
    for source, replacement in PUBLIC_REPLACEMENTS.items():
        cleaned = cleaned.replace(source, replacement)
    return cleaned


def _build_workspace_result(
    module: str,
    outcomes: tuple[_CapabilityOutcome, ...],
) -> ResearchWorkspaceResult:
    successful = [outcome for outcome in outcomes if outcome.rows]
    failed = [outcome for outcome in outcomes if outcome.failed or not outcome.rows]
    if successful:
        status = "complete" if not failed else "partial"
    else:
        status = "unavailable" if any(item.failed for item in outcomes) else "empty"
    details = tuple(_outcome_detail(outcome) for outcome in outcomes)
    findings = _front_findings(module, successful)
    copy = MODULE_COPY[module]
    if status == "unavailable":
        verdict = "研究服务暂时不可用，当前没有可执行结论。"
        action = "稍后重新分析；当前不沿用旧结论。"
    elif status == "empty":
        verdict = "本次没有返回足够证据，当前判断暂停。"
        action = "调整研究对象或稍后重新分析。"
    else:
        verdict = copy[status]
        action = copy["action"]
    missing_sections = tuple(
        _detail_label(outcome.request)
        for outcome in failed
    )
    return ResearchWorkspaceResult(
        ok=bool(successful),
        status=status,
        module=module,
        generated_at=datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds"),
        verdict=verdict,
        action=action,
        primary_risk=_primary_risk(successful, copy["risk"]),
        findings=findings,
        details=details,
        missing_sections=missing_sections,
    )


def _front_findings(
    module: str,
    successful: list[_CapabilityOutcome],
) -> tuple[ResearchFinding, ...]:
    if module != "portfolio":
        return tuple(
            finding
            for outcome in successful
            for finding in _outcome_findings(outcome)[:1]
        )[:3]
    findings: list[ResearchFinding] = []
    seen_targets: set[str] = set()
    for outcome in successful:
        target = _target_label(outcome.request.target)
        if not target or target in seen_targets:
            continue
        findings.extend(_outcome_findings(outcome)[:1])
        seen_targets.add(target)
        if len(findings) == 3:
            break
    return tuple(findings)


def _outcome_detail(outcome: _CapabilityOutcome) -> ResearchDetail:
    return ResearchDetail(
        section=CAPABILITY_LABELS[outcome.request.capability],
        target=_target_label(outcome.request.target),
        status="ready" if outcome.rows else "missing",
        findings=_outcome_findings(outcome),
    )


def _outcome_findings(outcome: _CapabilityOutcome) -> tuple[ResearchFinding, ...]:
    label = CAPABILITY_LABELS[outcome.request.capability]
    target = _target_label(outcome.request.target)
    return tuple(
        ResearchFinding(
            title=f"{target} · {label}" if target else label,
            summary="；".join(
                f"{fact.label}：{fact.value}" for fact in row[:2]
            ),
            target=target,
            facts=row,
        )
        for row in outcome.rows
    )


def _primary_risk(
    successful: list[_CapabilityOutcome],
    fallback: str,
) -> str:
    risk_terms = ("风险", "下修", "减持", "监管", "亏损", "解禁", "质押", "下降", "恶化")
    for outcome in successful:
        for row in outcome.rows:
            text = "；".join(f"{fact.label}：{fact.value}" for fact in row)
            if any(term in text for term in risk_terms):
                return _public_text(text, 180)
    return fallback


def _detail_label(request: CapabilityRequest) -> str:
    label = CAPABILITY_LABELS[request.capability]
    target = _target_label(request.target)
    return f"{target} · {label}" if target else label


def _target_label(target: ResearchTarget) -> str:
    return _public_text(target.name or target.code, 64)


def _research_cache_key(
    module: str,
    context: ResearchContext,
) -> tuple[object, ...]:
    holdings = tuple(
        (_clean_text(item.code, 32), _clean_text(item.name, 64))
        for item in context.holdings[:3]
    )
    return (
        module,
        _clean_text(context.code, 32),
        _clean_text(context.name, 64),
        _clean_text(context.sector, 64),
        holdings,
    )
