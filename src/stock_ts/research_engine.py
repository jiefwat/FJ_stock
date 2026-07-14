from __future__ import annotations

import re
import time
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any

from .iwencai import SKILLS, IwencaiSkillClient
from .research_evidence import normalize_capability_rows, raw_rows

WORKSPACE_CAPABILITIES = {
    "market": ("index", "macro", "sector_selector", "news"),
    "portfolio": ("event", "consensus", "market"),
    "stock": (
        "finance",
        "business",
        "consensus",
        "event",
        "market",
        "industry",
        "announcement",
        "report",
    ),
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
    "industry": "行业位置",
    "report": "研报观点",
}

FINDING_TITLES = {
    "index": "指数状态",
    "macro": "宏观变量",
    "sector_selector": "主线强度",
    "news": "市场事件",
    "event": "最新事件",
    "announcement": "公告事项",
    "consensus": "机构预期",
    "market": "价格与成交",
    "finance": "财务方向",
    "business": "经营与竞争",
    "astock_selector": "候选线索",
    "industry": "行业位置",
    "report": "研报观点",
}

FRONT_PRIORITY = {
    "market": {"index": 0, "sector_selector": 1, "news": 2, "macro": 3},
    "stock": {"event": 0, "finance": 1, "consensus": 2, "business": 3},
    "opportunity": {
        "sector_selector": 0,
        "astock_selector": 1,
        "event": 2,
        "news": 3,
    },
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
    evidence_key: tuple[tuple[str, str], ...] = ()

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
class ResearchModuleItem:
    kind: str
    code: str = ""
    name: str = ""
    label: str = ""
    summary: str = ""
    risk: str = ""
    status: str = "ready"
    facts: tuple[ResearchFact, ...] = ()

    def to_public_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "code": self.code,
            "name": self.name,
            "label": self.label,
            "summary": self.summary,
            "risk": self.risk,
            "status": self.status,
            "facts": [fact.to_public_dict() for fact in self.facts],
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
    subject_count: int = 0
    coverage_ready: int = 0
    coverage_total: int = 0
    delivery: str = "live"
    as_of: str = ""
    module_items: tuple[ResearchModuleItem, ...] = ()

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
            "subject_count": self.subject_count,
            "coverage": {
                "ready": self.coverage_ready,
                "total": self.coverage_total,
            },
            "delivery": self.delivery,
            "as_of": self.as_of or self.generated_at,
            "module_items": [item.to_public_dict() for item in self.module_items],
        }


@dataclass(frozen=True)
class _CapabilityOutcome:
    request: CapabilityRequest
    rows: tuple[tuple[ResearchFact, ...], ...] = ()
    failed: bool = False
    insufficient: bool = False


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
        with ThreadPoolExecutor(max_workers=min(8, len(requests))) as executor:
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
            for target in context.holdings[:20]
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
        return tuple(
            CapabilityRequest(
                capability=capability,
                query=_opportunity_query(capability, context.sector),
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
        ("market", "index"): (
            "上证指数、深证成指、创业板指 最新点位 涨跌幅 成交额 "
            "近5日涨跌幅 近20日涨跌幅 5日均线 20日均线"
        ),
        ("market", "macro"): "近期影响A股风险偏好的宏观指标与政策变化",
        ("market", "sector_selector"): (
            "行业板块 排除融资融券 按成交额和热度排序 前5"
        ),
        ("market", "news"): "近期影响A股风险偏好的重要新闻与风险事件",
        ("portfolio", "event"): "近期业绩预告、解禁、质押、监管和经营风险",
        ("portfolio", "announcement"): "近期公告中需要持有人重点复核的事项",
        ("portfolio", "consensus"): "机构盈利预期、评级及其上调或下修变化",
        ("portfolio", "market"): "近期价格、成交量和资金异动",
        ("stock", "finance"): "收入、利润、现金流、ROE和负债质量变化",
        ("stock", "business"): "主营结构、竞争位置、客户供应链与经营变化",
        ("stock", "consensus"): "未来两年盈利预期、评级和预期变化",
        ("stock", "event"): "近期业绩、解禁、质押、监管和事件风险",
        ("stock", "market"): "近期价格、成交量、成交额、换手率和资金变化",
        ("stock", "industry"): "行业位置、行业排名、同行估值和竞争参照",
        ("stock", "announcement"): "近期公告中需要重点核查的事项",
        ("stock", "report"): "近期研报观点、盈利预测、评级和主要分歧",
        ("opportunity", "sector_selector"): "筛选强度、成交和持续性靠前的行业方向",
        ("opportunity", "astock_selector"): "筛选盈利改善、成交活跃且风险可核查的股票",
        ("opportunity", "event"): "近期可核查的业绩、公告和事件催化",
        ("opportunity", "news"): "近期市场主线新闻及需要排除的风险",
    }
    return prompts[(module, capability)]


def _opportunity_query(capability: str, sector: str) -> str:
    cleaned_sector = _clean_text(sector, 64)
    if cleaned_sector and not cleaned_sector.endswith(("概念", "行业", "板块")):
        theme = f"{cleaned_sector}概念"
    else:
        theme = cleaned_sector
    scope = theme or "A股"
    stock_scope = f"{theme} " if theme else ""
    sector_query = (
        f"{theme}板块 按成交额和热度排序 前5"
        if theme
        else "概念板块 排除融资融券 按板块热度排序 前5"
    )
    prompts = {
        "sector_selector": sector_query,
        "astock_selector": (
            f"{stock_scope}A股 净利润同比增长 成交额大于5亿 按成交额排序 前10"
        ),
        "event": f"{scope} 近期业绩预告、公告和事件催化",
        "news": f"{scope} 近期市场主线新闻及需要排除的风险",
    }
    return prompts[capability]


def _clean_text(value: str, limit: int) -> str:
    cleaned = "".join(character if character.isprintable() else " " for character in value)
    return " ".join(cleaned.split())[:limit]


def _execute_capability(client: Any, request: CapabilityRequest) -> _CapabilityOutcome:
    raw = client.query(SKILLS[request.capability], request.query)
    row_limits = {
        "astock_selector": 10,
        "sector_selector": 5,
        "news": 5,
        "announcement": 5,
        "report": 5,
    }
    evidence_rows = normalize_capability_rows(
        request.capability,
        raw,
        max_rows=row_limits.get(request.capability, 3),
    )
    rows = tuple(
        tuple(ResearchFact(label=fact.label, value=fact.value) for fact in row)
        for row in evidence_rows
    )
    return _CapabilityOutcome(
        request=request,
        rows=rows,
        insufficient=bool(raw_rows(raw)) and not rows,
    )


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
        if module == "stock":
            status = "complete" if len(successful) >= 6 else "partial"
        else:
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
        verdict = _workspace_verdict(module, successful, findings, copy[status])
        action = copy["action"]
    missing_sections = tuple(
        _detail_label(outcome.request)
        for outcome in failed
    )
    module_items = _build_module_items(module, outcomes)
    subject_count = _subject_count(module, outcomes, module_items)
    return ResearchWorkspaceResult(
        ok=bool(successful),
        status=status,
        module=module,
        generated_at=datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds"),
        verdict=verdict,
        action=action,
        primary_risk=_primary_risk(module, successful, copy["risk"]),
        findings=findings,
        details=details,
        missing_sections=missing_sections,
        subject_count=subject_count,
        coverage_ready=len(successful),
        coverage_total=len(outcomes),
        as_of=datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds"),
        module_items=module_items,
    )


def _build_module_items(
    module: str,
    outcomes: tuple[_CapabilityOutcome, ...],
) -> tuple[ResearchModuleItem, ...]:
    if module == "market":
        index = next((item for item in outcomes if item.request.capability == "index"), None)
        return tuple(_market_module_item(row) for row in (index.rows if index else ())[:3])
    if module == "portfolio":
        return _portfolio_module_items(outcomes)
    if module == "stock":
        return tuple(_stock_module_item(outcome) for outcome in outcomes)
    candidates = next(
        (item for item in outcomes if item.request.capability == "astock_selector"),
        None,
    )
    return tuple(
        item
        for row in (candidates.rows if candidates else ())[:10]
        if (item := _candidate_module_item(row)) is not None
    )


def _market_module_item(row: tuple[ResearchFact, ...]) -> ResearchModuleItem:
    return ResearchModuleItem(
        kind="index",
        code=_row_value(row, ("指数代码",)),
        name=_row_value(row, ("指数简称", "指数名称")),
        label="短中期趋势",
        summary=_index_summary(row),
        risk="5日与20日趋势转弱时降低风险暴露",
        facts=_display_facts("index", row),
    )


def _portfolio_module_items(
    outcomes: tuple[_CapabilityOutcome, ...],
) -> tuple[ResearchModuleItem, ...]:
    grouped: dict[tuple[str, str], list[_CapabilityOutcome]] = {}
    for outcome in outcomes:
        target = outcome.request.target
        grouped.setdefault((target.code, target.name), []).append(outcome)
    items: list[ResearchModuleItem] = []
    priority = {"event": 0, "consensus": 1, "market": 2}
    for (code, name), target_outcomes in grouped.items():
        ready = [outcome for outcome in target_outcomes if outcome.rows]
        ready.sort(key=lambda outcome: priority.get(outcome.request.capability, 99))
        chosen = ready[0] if ready else None
        finding = _outcome_findings(chosen)[0] if chosen else None
        label = (
            FINDING_TITLES.get(chosen.request.capability, "证据不足")
            if chosen
            else "证据不足"
        )
        risk = (
            finding.summary
            if finding and _finding_has_negative_signal(finding)
            else "未发现高优先风险，仍需结合成本与仓位复核"
        )
        items.append(
            ResearchModuleItem(
                kind="holding",
                code=code,
                name=name,
                label=label,
                summary=finding.summary if finding else "本次未返回可用研究证据",
                risk=risk,
                status="ready" if chosen else "missing",
                facts=finding.facts if finding else (),
            )
        )
    return tuple(items)


def _stock_module_item(outcome: _CapabilityOutcome) -> ResearchModuleItem:
    findings = _outcome_findings(outcome)
    status = "ready" if outcome.rows else "failed" if outcome.failed else "missing"
    return ResearchModuleItem(
        kind="dimension",
        code=outcome.request.target.code,
        name=outcome.request.target.name,
        label=CAPABILITY_LABELS[outcome.request.capability],
        summary=findings[0].summary if findings else "本维度证据待补",
        risk="证据不足时不提高结论置信度" if not findings else "关键事实变化时重新评估",
        status=status,
        facts=findings[0].facts if findings else (),
    )


def _candidate_module_item(
    row: tuple[ResearchFact, ...],
) -> ResearchModuleItem | None:
    code = _row_value(row, ("股票代码", "证券代码"))
    name = _row_value(row, ("股票简称", "证券简称", "股票名称"))
    if not code or not name:
        return None
    return ResearchModuleItem(
        kind="candidate",
        code=code,
        name=name,
        label="今日候选",
        summary=_candidate_summary(row),
        risk="板块退潮、成交萎缩或业绩证据转弱时移出清单",
        facts=_display_facts("astock_selector", row),
    )


def _row_value(row: tuple[ResearchFact, ...], terms: tuple[str, ...]) -> str:
    fact = _fact_matching(row, terms)
    return fact.value if fact else ""


def _finding_has_negative_signal(finding: ResearchFinding) -> bool:
    text = " ".join([finding.summary, *(fact.value for fact in finding.facts)])
    return any(term in text for term in ("预亏", "下降", "承压", "监管", "质押", "解禁", "负"))


def _subject_count(
    module: str,
    outcomes: tuple[_CapabilityOutcome, ...],
    module_items: tuple[ResearchModuleItem, ...],
) -> int:
    if module == "stock":
        return 1
    if module == "portfolio":
        return len({(item.request.target.code, item.request.target.name) for item in outcomes})
    return len(module_items)


def _front_findings(
    module: str,
    successful: list[_CapabilityOutcome],
) -> tuple[ResearchFinding, ...]:
    if module != "portfolio":
        candidates = [
            (outcome, finding)
            for outcome in successful
            for finding in _outcome_findings(outcome)[:1]
        ]
        priority = FRONT_PRIORITY.get(module, {})
        candidates.sort(
            key=lambda item: priority.get(item[0].request.capability, 99)
        )
        return _deduplicate_findings(item[1] for item in candidates)[:3]
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
    return _deduplicate_findings(findings)


def _outcome_detail(outcome: _CapabilityOutcome) -> ResearchDetail:
    if outcome.rows:
        status = "ready"
    elif outcome.failed:
        status = "failed"
    elif outcome.insufficient:
        status = "insufficient"
    else:
        status = "missing"
    return ResearchDetail(
        section=CAPABILITY_LABELS[outcome.request.capability],
        target=_target_label(outcome.request.target),
        status=status,
        findings=_outcome_findings(outcome),
    )


def _outcome_findings(outcome: _CapabilityOutcome) -> tuple[ResearchFinding, ...]:
    capability = outcome.request.capability
    title = FINDING_TITLES[capability]
    target = _target_label(outcome.request.target)
    return tuple(
        ResearchFinding(
            title=title,
            summary=_finding_summary(capability, row),
            target=target,
            facts=_display_facts(capability, row),
            evidence_key=tuple((fact.label, fact.value) for fact in row),
        )
        for row in outcome.rows
    )


def _finding_summary(
    capability: str,
    row: tuple[ResearchFact, ...],
) -> str:
    if capability == "finance":
        return _finance_summary(row)
    if capability == "business":
        return _business_summary(row)
    if capability == "consensus":
        return _consensus_summary(row)
    if capability == "event":
        return _event_summary(row)
    if capability == "index":
        return _index_summary(row)
    if capability == "sector_selector":
        return _sector_summary(row)
    if capability == "astock_selector":
        return _candidate_summary(row)
    if capability in {"news", "announcement"}:
        return _document_summary(row)
    if capability == "market":
        return _market_summary(row)
    if capability == "industry":
        return _industry_summary(row)
    if capability == "report":
        return _document_summary(row)
    return "；".join(f"{fact.label}：{fact.value}" for fact in row[:2])


def _finance_summary(row: tuple[ResearchFact, ...]) -> str:
    revenues = [
        fact
        for fact in row
        if any(key in fact.label for key in ("营业收入", "营收"))
        and not any(change in fact.label for change in ("同比", "环比"))
    ]
    parts: list[str] = []
    if len(revenues) >= 2:
        latest = _numeric_value(revenues[0].value)
        previous = _numeric_value(revenues[1].value)
        if latest is not None and previous is not None:
            direction = "改善" if latest > previous else "回落" if latest < previous else "持平"
            parts.append(
                f"收入较上一期{direction}（{revenues[0].value} / {revenues[1].value}）"
            )
    elif revenues:
        parts.append(f"收入为{revenues[0].value}，仅单期数据，趋势待确认")

    profit = next((fact for fact in row if "净利润" in fact.label), None)
    cash_flow = next(
        (
            fact
            for fact in row
            if "经营现金流" in fact.label or "经营活动产生的现金流" in fact.label
        ),
        None,
    )
    if profit and cash_flow:
        profit_value = _numeric_value(profit.value)
        cash_value = _numeric_value(cash_flow.value)
        if profit_value is not None and cash_value is not None:
            if profit_value <= 0 and cash_value < 0:
                quality = "利润与经营现金流均为负，增长质量承压"
            elif profit_value <= 0 <= cash_value:
                quality = "利润为负但经营现金流为正，需区分非现金损益"
            elif profit_value > 0 > cash_value:
                quality = "利润为正但经营现金流为负，含金量偏弱"
            elif cash_value >= profit_value:
                quality = "现金流覆盖利润"
            else:
                quality = "现金流低于利润，含金量需复核"
            parts.append(quality)
    return "；".join(parts) or _compact_facts(row)


def _business_summary(row: tuple[ResearchFact, ...]) -> str:
    product = next((fact for fact in row if "主营" in fact.label or "产品" in fact.label), None)
    competitor = next((fact for fact in row if "竞争" in fact.label or "同行" in fact.label), None)
    if product and competitor:
        return f"主营围绕{product.value}；竞争参照为{competitor.value}"
    if product:
        return f"主营围绕{product.value}，竞争位置仍需补充验证"
    return _compact_facts(row)


def _consensus_summary(row: tuple[ResearchFact, ...]) -> str:
    forecasts = [fact for fact in row if "预测" in fact.label or "一致预期" in fact.label]
    if len(forecasts) >= 2:
        first = _numeric_value(forecasts[0].value)
        second = _numeric_value(forecasts[1].value)
        first_year = _label_year(forecasts[0].label)
        second_year = _label_year(forecasts[1].label)
        if first is not None and second is not None:
            if second > first:
                return f"{second_year}年预测高于{first_year}年，机构预期仍在增长轨道"
            if second < first:
                return f"{second_year}年预测低于{first_year}年，机构预期出现回落"
            return f"{first_year}至{second_year}年预测基本持平，预期缺少上修动能"
    if forecasts:
        return f"仅有{_label_year(forecasts[0].label)}年预测，趋势待更多期间确认"
    return _compact_facts(row)


def _event_summary(row: tuple[ResearchFact, ...]) -> str:
    negative = next((fact for fact in row if _fact_is_negative(fact)), None)
    if negative:
        return f"{_short_metric(negative.label)}为{negative.value}，最新变化承压"
    positive = next(
        (
            fact
            for fact in row
            if any(term in fact.label for term in ("同比", "环比", "增长率"))
            and _numeric_value(fact.value) is not None
        ),
        None,
    )
    if positive:
        return f"{_short_metric(positive.label)}为{positive.value}，最新变化改善"
    return _compact_facts(row)


def _index_summary(row: tuple[ResearchFact, ...]) -> str:
    name = _fact_matching(row, ("指数简称", "指数名称"))
    price = _fact_matching(row, ("最新点位", "收盘价", "最新价"))
    change = _fact_matching(row, ("涨跌幅", "涨跌"))
    metrics = [
        f"{_short_metric(fact.label)} {fact.value}"
        for fact in (price, change)
        if fact is not None
    ]
    if name and metrics:
        return f"{name.value} {'，'.join(metrics)}"
    return _compact_facts(row)


def _sector_summary(row: tuple[ResearchFact, ...]) -> str:
    name = _fact_matching(row, ("板块名称", "行业名称", "概念名称", "指数简称"))
    heat = _fact_matching(row, ("热度", "排名", "强度"))
    amount = _fact_matching(row, ("成交额", "成交量"))
    metrics = [
        f"{_short_metric(fact.label)} {fact.value}"
        for fact in (heat, amount)
        if fact is not None
    ]
    if name and metrics:
        return f"{name.value} {'，'.join(metrics)}"
    return _compact_facts(row)


def _candidate_summary(row: tuple[ResearchFact, ...]) -> str:
    name = _fact_matching(row, ("股票简称", "证券简称", "股票名称"))
    growth = _fact_matching(row, ("净利润同比", "营业收入同比", "营收同比"))
    amount = _fact_matching(row, ("成交额", "成交量", "换手率"))
    metrics = [
        f"{_short_metric(fact.label)} {fact.value}"
        for fact in (growth, amount)
        if fact is not None
    ]
    if name and metrics:
        return f"{name.value}：{'，'.join(metrics)}"
    return _compact_facts(row)


def _document_summary(row: tuple[ResearchFact, ...]) -> str:
    title = _fact_matching(row, ("标题", "title", "公告名称"))
    summary = _fact_matching(row, ("摘要", "summary", "内容"))
    if title and summary:
        summary_text = summary.value
        if summary_text.startswith(title.value):
            summary_text = summary_text[len(title.value) :].lstrip(" ：:，,。")
        return _public_text(f"{title.value}：{summary_text}", 80)
    if title:
        return _public_text(title.value, 180)
    return _compact_facts(row)


def _market_summary(row: tuple[ResearchFact, ...]) -> str:
    price = _fact_matching(row, ("收盘价", "最新价"))
    volume = _fact_matching(row, ("成交量", "成交额", "换手率"))
    if price and volume:
        return (
            f"{_short_metric(price.label)} {price.value}，"
            f"{_short_metric(volume.label)} {volume.value}"
        )
    return _compact_facts(row)


def _industry_summary(row: tuple[ResearchFact, ...]) -> str:
    industry = _fact_matching(row, ("行业名称", "所属行业"))
    ranking = _fact_matching(row, ("行业排名", "排名"))
    valuation = _fact_matching(row, ("市盈率", "估值"))
    parts = [fact.value for fact in (industry, ranking, valuation) if fact]
    return "，".join(parts) if parts else _compact_facts(row)


def _display_facts(
    capability: str,
    row: tuple[ResearchFact, ...],
) -> tuple[ResearchFact, ...]:
    excluded_terms = {
        "index": ("指数代码", "指数简称", "指数名称", "最新价", "最新点位", "收盘价", "涨跌幅"),
        "sector_selector": (
            "指数代码",
            "指数简称",
            "板块名称",
            "行业名称",
            "概念名称",
            "热度",
            "排名",
            "成交额",
            "成交量",
            "涨跌幅",
        ),
        "astock_selector": (
            "股票代码",
            "证券代码",
            "股票简称",
            "证券简称",
            "股票名称",
            "净利润同比",
            "营业收入同比",
            "营收同比",
            "成交额",
            "成交量",
            "换手率",
        ),
        "news": (
            "title",
            "标题",
            "summary",
            "摘要",
            "内容",
            "url",
            "链接",
            "publish_time",
            "发布时间",
        ),
        "announcement": (
            "title",
            "标题",
            "公告名称",
            "summary",
            "摘要",
            "内容",
            "url",
            "链接",
            "publish_time",
            "发布时间",
        ),
    }
    terms = excluded_terms.get(capability, ())
    return tuple(
        fact
        for fact in row
        if not any(term.lower() in fact.label.lower() for term in terms)
    )[:4]


def _workspace_verdict(
    module: str,
    successful: list[_CapabilityOutcome],
    findings: tuple[ResearchFinding, ...],
    fallback: str,
) -> str:
    if not findings:
        return fallback
    summary = findings[0].summary
    if module == "stock":
        target = _target_label(successful[0].request.target)
        return _public_text(f"{target}：{summary}" if target else summary, 180)
    prefixes = {
        "market": "市场证据显示：",
        "portfolio": "重点持仓需要先看：",
        "opportunity": "当前可核查线索：",
    }
    return _public_text(f"{prefixes.get(module, '')}{summary}", 180)


def _deduplicate_findings(
    findings: Iterable[ResearchFinding],
) -> tuple[ResearchFinding, ...]:
    unique: list[ResearchFinding] = []
    seen: set[tuple[tuple[str, str], ...]] = set()
    for finding in findings:
        fingerprint = (("target", finding.target),) + finding.evidence_key
        if not fingerprint or fingerprint in seen:
            continue
        unique.append(finding)
        seen.add(fingerprint)
    return tuple(unique)


def _compact_facts(row: tuple[ResearchFact, ...]) -> str:
    return "；".join(f"{fact.label}：{fact.value}" for fact in row[:2])


def _numeric_value(value: str) -> float | None:
    match = re.search(r"-?\d+(?:\.\d+)?", value.replace(",", ""))
    if not match:
        return None
    number = float(match.group())
    if "亿" in value:
        return number * 100_000_000
    if "万" in value:
        return number * 10_000
    return number


def _label_year(label: str) -> str:
    match = re.search(r"20\d{2}", label)
    return match.group() if match else "当前"


def _short_metric(label: str) -> str:
    cleaned = re.sub(r"\[[^]]+]", "", label)
    cleaned = cleaned.replace(":前复权", "").replace("_前复权", "")
    cleaned = cleaned.replace("增长率", "")
    if cleaned == "最新涨跌幅":
        return "涨跌幅"
    if cleaned == "最新价":
        return "点位"
    return cleaned


def _fact_matching(
    row: tuple[ResearchFact, ...],
    terms: tuple[str, ...],
) -> ResearchFact | None:
    return next(
        (fact for fact in row if any(term.lower() in fact.label.lower() for term in terms)),
        None,
    )


def _fact_is_negative(fact: ResearchFact) -> bool:
    value = _numeric_value(fact.value)
    return value is not None and value < 0 and any(
        term in fact.label for term in ("同比", "环比", "利润", "收入", "增长", "涨跌")
    )


def _primary_risk(
    module: str,
    successful: list[_CapabilityOutcome],
    fallback: str,
) -> str:
    risk_terms = (
        "风险事件",
        "下修",
        "减持",
        "监管",
        "亏损",
        "解禁",
        "质押",
        "下降",
        "恶化",
        "诉讼",
        "预减",
    )
    priority = FRONT_PRIORITY.get(module, {})
    ordered = sorted(
        successful,
        key=lambda outcome: priority.get(outcome.request.capability, 99),
    )
    for outcome in ordered:
        for row in outcome.rows:
            negative = next((fact for fact in row if _fact_is_negative(fact)), None)
            if negative:
                if outcome.request.capability in {"index", "sector_selector"}:
                    name = _fact_matching(
                        row,
                        (
                            "指数简称",
                            "指数名称",
                            "板块名称",
                            "行业名称",
                            "概念名称",
                        ),
                    )
                    if name:
                        return _public_text(
                            f"{name.value} · {_short_metric(negative.label)}：{negative.value}",
                            180,
                        )
                description = f"{negative.label}：{negative.value}"
                target = _target_label(outcome.request.target)
                if module == "portfolio" and target:
                    description = f"{target} · {description}"
                return _public_text(description, 180)
            risk_fact = next(
                (
                    fact
                    for fact in row
                    if any(term in f"{fact.label} {fact.value}" for term in risk_terms)
                ),
                None,
            )
            if risk_fact:
                if outcome.request.capability in {"news", "announcement"}:
                    description = _finding_summary(outcome.request.capability, row)
                else:
                    description = f"{_short_metric(risk_fact.label)}：{risk_fact.value}"
                target = _target_label(outcome.request.target)
                if module == "portfolio" and target:
                    description = f"{target} · {description}"
                return _public_text(description, 180)
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
