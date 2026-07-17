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
from .research_method import attach_method_section

WORKSPACE_CAPABILITIES = {
    "market": (
        "index",
        "breadth",
        "sector_selector",
        "hot_stock",
        "macro",
        "news",
    ),
    "portfolio": ("event", "consensus", "market", "industry"),
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
    "breadth": "涨跌分布",
    "hot_stock": "热门股票",
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
    "breadth": "涨跌分布",
    "hot_stock": "热门股票",
    "industry": "行业位置",
    "report": "研报观点",
}

FRONT_PRIORITY = {
    "market": {
        "index": 0,
        "sector_selector": 1,
        "news": 2,
        "breadth": 3,
        "hot_stock": 4,
        "macro": 5,
    },
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
        "risk": "当前只分析研究证据，资金暴露需由账户侧另行约束。",
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
    "Skill": "能力",
    "SKILL": "能力",
    "skill": "能力",
}
PUBLIC_BRAND_TERMS = ("问财", "iwencai", "同花顺")

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
        if _is_identity_fact_label(self.label):
            public_value = _public_identity_text(self.value, 500)
        elif _is_classification_label(self.label):
            public_value = _public_classification_value(self.value, 500)
        else:
            public_value = _public_free_text(self.value, 500)
        return {
            "label": (
                _public_classification_label(self.label, 64)
                if _is_classification_label(self.label)
                else _public_free_text(self.label, 64)
            ),
            "value": public_value,
        }


@dataclass(frozen=True)
class ResearchFinding:
    title: str
    summary: str
    target: str = ""
    facts: tuple[ResearchFact, ...] = ()
    evidence_key: tuple[tuple[str, str], ...] = ()

    def to_public_dict(self) -> dict[str, object]:
        return {
            "title": _public_free_text(self.title, 120),
            "summary": _public_free_text(self.summary, 500, (self.target,)),
            "target": _public_identity_text(self.target, 120),
            "facts": _public_fact_dicts(self.facts),
        }


@dataclass(frozen=True)
class ResearchDetail:
    section: str
    target: str
    status: str
    findings: tuple[ResearchFinding, ...] = ()

    def to_public_dict(self) -> dict[str, object]:
        return {
            "section": _public_free_text(self.section, 120),
            "target": _public_identity_text(self.target, 120),
            "status": self.status,
            "findings": [item.to_public_dict() for item in self.findings],
        }


@dataclass(frozen=True)
class ResearchModuleItem:
    kind: str
    key: str = ""
    code: str = ""
    name: str = ""
    label: str = ""
    summary: str = ""
    risk: str = ""
    status: str = "ready"
    score: float | None = None
    recovery: str = ""
    facts: tuple[ResearchFact, ...] = ()

    def to_public_dict(self) -> dict[str, object]:
        classification_kinds = {
            "candidate",
            "hot_stock",
            "portfolio_theme",
            "theme",
            "theme_divergence",
        }
        public_label = _public_classification_value(self.label, 120)
        if self.kind not in classification_kinds:
            public_label = _public_free_text(self.label, 120)
        elif not public_label:
            public_label = "主题待确认"
        classification_name_kinds = {"portfolio_theme", "theme", "theme_divergence"}
        public_name = (
            _public_classification_value(self.name, 120)
            if self.kind in classification_name_kinds
            else _public_identity_text(self.name, 120)
        )
        if self.kind in classification_name_kinds and not public_name:
            public_name = "主题待确认"
        identities = (self.name,) if self.kind not in classification_name_kinds else ()
        payload = {
            "kind": self.kind,
            "code": _public_identity_text(self.code, 64),
            "name": public_name,
            "label": public_label,
            "summary": _public_free_text(self.summary, 500, identities),
            "risk": _public_free_text(self.risk, 500),
            "status": self.status,
            "facts": _public_fact_dicts(self.facts),
        }
        if self.kind in {"method_dimension", "method_output"}:
            payload.update(
                key=self.key,
                score=self.score,
                recovery=_public_free_text(self.recovery, 500),
            )
        return payload


@dataclass(frozen=True)
class ResearchModuleSection:
    key: str
    title: str
    conclusion: str
    tone: str = "neutral"
    items: tuple[ResearchModuleItem, ...] = ()

    def to_public_dict(self) -> dict[str, object]:
        return {
            "key": self.key,
            "title": _public_free_text(self.title, 120),
            "conclusion": _public_free_text(self.conclusion, 500),
            "tone": self.tone,
            "items": [item.to_public_dict() for item in self.items],
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
    data_label: str = ""
    fallback_reason: str = ""
    as_of: str = ""
    module_items: tuple[ResearchModuleItem, ...] = ()
    decision_label: str = "待确认"
    module_sections: tuple[ResearchModuleSection, ...] = ()
    research_contract_version: str = ""

    def to_public_dict(self) -> dict[str, object]:
        identities = tuple(
            item.name
            for item in self.module_items
            if item.kind not in {"portfolio_theme", "theme", "theme_divergence"}
        )
        return {
            "ok": self.ok,
            "status": self.status,
            "module": self.module,
            "generated_at": self.generated_at,
            "verdict": _public_free_text(self.verdict, 500, identities),
            "action": _public_free_text(self.action, 500),
            "primary_risk": _public_free_text(self.primary_risk, 500, identities),
            "findings": [item.to_public_dict() for item in self.findings],
            "details": [item.to_public_dict() for item in self.details],
            "missing_sections": [
                text
                for item in self.missing_sections
                if (text := _public_free_text(item, 200, identities))
            ],
            "subject_count": self.subject_count,
            "coverage": {
                "ready": self.coverage_ready,
                "total": self.coverage_total,
            },
            "delivery": self.delivery,
            "data_label": _public_free_text(self.data_label, 64),
            "fallback_reason": _public_free_text(self.fallback_reason, 200),
            "as_of": self.as_of or self.generated_at,
            "module_items": [item.to_public_dict() for item in self.module_items],
            "decision_label": _public_free_text(self.decision_label, 120),
            "module_sections": [item.to_public_dict() for item in self.module_sections],
            "research_contract_version": self.research_contract_version,
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
        ("market", "breadth"): "A股 今日上涨家数 下跌家数 平盘家数 涨停家数 跌停家数",
        ("market", "macro"): "近期影响A股风险偏好的宏观指标与政策变化",
        ("market", "sector_selector"): (
            "行业板块 排除融资融券 按成交额和热度排序 前5"
        ),
        ("market", "hot_stock"): (
            "A股 按成交额从高到低排序 前10 股票代码 股票简称 涨跌幅 "
            "成交额 所属概念板块 所属行业"
        ),
        ("market", "news"): "近期影响A股风险偏好的重要新闻与风险事件",
        ("portfolio", "event"): "近期业绩预告、解禁、质押、监管和经营风险",
        ("portfolio", "announcement"): "近期公告中需要持有人重点复核的事项",
        ("portfolio", "consensus"): "机构盈利预期、评级及其上调或下修变化",
        ("portfolio", "market"): "近期价格、成交量和资金异动",
        ("portfolio", "industry"): "所属行业、概念主题、行业排名和同行公司",
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
            f"{stock_scope}A股 净利润同比增长 成交额大于5亿 按成交额排序 "
            "前10 股票代码 股票简称 所属概念 所属行业"
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
        "breadth": 1,
        "hot_stock": 10,
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


def _base_public_text(value: str, limit: int) -> str:
    cleaned = _clean_text(value, limit)
    for source, replacement in PUBLIC_REPLACEMENTS.items():
        cleaned = cleaned.replace(source, replacement)
    return cleaned


def _public_identity_text(value: str, limit: int) -> str:
    return _clean_text(value, limit)


def _public_free_text(
    value: str,
    limit: int,
    identities: tuple[str, ...] = (),
) -> str:
    cleaned = _base_public_text(value, limit)
    placeholders: dict[str, str] = {}
    for index, identity in enumerate(sorted(set(identities), key=len, reverse=True)):
        identity = _clean_text(identity, limit)
        if not identity:
            continue
        placeholder = f"__identity_{index}__"
        pattern = re.compile(re.escape(identity) + r"(?=[:：·])")
        if pattern.search(cleaned):
            cleaned = pattern.sub(placeholder, cleaned)
            placeholders[placeholder] = identity
    for term in PUBLIC_BRAND_TERMS:
        cleaned = re.sub(re.escape(term), "", cleaned, flags=re.IGNORECASE)
    for placeholder, identity in placeholders.items():
        cleaned = cleaned.replace(placeholder, identity)
    return _clean_text(cleaned, limit)


def _is_identity_fact_label(label: str) -> bool:
    return any(
        term in label
        for term in ("股票简称", "证券简称", "股票名称", "证券名称", "公司名称")
    )


def _is_classification_label(label: str) -> bool:
    return label in {"概念", "行业", "分类"} or any(
        term in label
        for term in ("所属概念", "概念名称", "所属行业", "行业名称", "分类")
    )


def _public_classification_label(value: str, limit: int) -> str:
    cleaned = _base_public_text(value, limit)
    for term in PUBLIC_BRAND_TERMS:
        cleaned = re.sub(re.escape(term), "", cleaned, flags=re.IGNORECASE)
    return _clean_text(cleaned, limit)


def _public_classification_value(value: str, limit: int) -> str:
    tokens = []
    for raw_token in re.split(r"[、,，/；;]", _base_public_text(value, limit)):
        token = raw_token.strip()
        if not token or _contains_public_brand(token):
            continue
        tokens.append(token)
    return "、".join(tokens)[:limit]


def _contains_public_brand(value: str) -> bool:
    normalized = str(value or "").casefold()
    return any(term.casefold() in normalized for term in PUBLIC_BRAND_TERMS)


def _public_fact_dicts(
    facts: tuple[ResearchFact, ...],
) -> list[dict[str, str]]:
    public_facts = [fact.to_public_dict() for fact in facts]
    return [fact for fact in public_facts if fact["label"] and fact["value"]]


def _build_workspace_result(
    module: str,
    outcomes: tuple[_CapabilityOutcome, ...],
) -> ResearchWorkspaceResult:
    now = datetime.now(timezone(timedelta(hours=8)))
    successful = [outcome for outcome in outcomes if outcome.rows]
    front_successful = [
        outcome for outcome in successful if _is_front_evidence_current(outcome, now)
    ]
    failed = [outcome for outcome in outcomes if outcome.failed or not outcome.rows]
    if successful:
        if module == "stock":
            status = "complete" if len(successful) >= 6 else "partial"
        else:
            status = "complete" if not failed else "partial"
    else:
        status = "unavailable" if any(item.failed for item in outcomes) else "empty"
    details = tuple(_outcome_detail(outcome) for outcome in outcomes)
    findings = _front_findings(module, front_successful)
    copy = MODULE_COPY[module]
    if status == "unavailable":
        verdict = "研究服务暂时不可用，当前没有可执行结论。"
        action = "稍后重新分析；当前不沿用旧结论。"
    elif status == "empty":
        verdict = "本次没有返回足够证据，当前判断暂停。"
        action = "调整研究对象或稍后重新分析。"
    else:
        verdict = _workspace_verdict(module, front_successful, findings, copy[status])
        action = copy["action"]
    missing_sections = tuple(
        _detail_label(outcome.request)
        for outcome in failed
    )
    module_items = _build_module_items(module, outcomes)
    module_sections = _build_module_sections(module, outcomes, module_items)
    decision_label, decision_verdict = _module_decision(
        module,
        outcomes,
        module_items,
        verdict,
    )
    if status not in {"unavailable", "empty"}:
        verdict = decision_verdict
    else:
        decision_label = "待确认"
    subject_count = _subject_count(module, outcomes, module_items)
    return attach_method_section(
        ResearchWorkspaceResult(
            ok=bool(successful),
            status=status,
            module=module,
            generated_at=now.isoformat(timespec="seconds"),
            verdict=verdict,
            action=action,
            primary_risk=_primary_risk(module, front_successful, copy["risk"]),
            findings=findings,
            details=details,
            missing_sections=missing_sections,
            subject_count=subject_count,
            coverage_ready=len(successful),
            coverage_total=len(outcomes),
            as_of=now.isoformat(timespec="seconds"),
            module_items=module_items,
            decision_label=decision_label,
            module_sections=module_sections,
        ),
        ready_keys=(item.request.capability for item in successful),
        missing_keys=(item.request.capability for item in failed),
    )


def _is_front_evidence_current(
    outcome: _CapabilityOutcome,
    now: datetime,
) -> bool:
    if outcome.request.capability not in {"news", "announcement", "report"}:
        return True
    published = next(
        (
            parsed
            for row in outcome.rows
            for fact in row
            if any(term in fact.label for term in ("发布日期", "公告日期", "发布时间", "日期"))
            if (parsed := _parse_evidence_datetime(fact.value, now.tzinfo)) is not None
        ),
        None,
    )
    if published is None:
        return False
    age = now - published.astimezone(now.tzinfo)
    return timedelta(0) <= age <= timedelta(days=30)


def _parse_evidence_datetime(value: str, tzinfo: Any) -> datetime | None:
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        digits = re.sub(r"\D", "", normalized)
        if len(digits) != 8:
            return None
        try:
            parsed = datetime.strptime(digits, "%Y%m%d")
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=tzinfo)
    return parsed


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


def _build_module_sections(
    module: str,
    outcomes: tuple[_CapabilityOutcome, ...],
    module_items: tuple[ResearchModuleItem, ...],
) -> tuple[ResearchModuleSection, ...]:
    if module == "market":
        return _market_sections(outcomes)
    if module == "portfolio":
        return _portfolio_sections(outcomes)
    if module == "opportunity":
        return _opportunity_sections(outcomes, module_items)
    return ()


def _module_decision(
    module: str,
    outcomes: tuple[_CapabilityOutcome, ...],
    module_items: tuple[ResearchModuleItem, ...],
    fallback: str,
) -> tuple[str, str]:
    if module == "market":
        return _market_decision(outcomes)
    if module == "portfolio":
        return _portfolio_decision(outcomes, fallback)
    if module == "stock":
        return _stock_decision(outcomes, fallback)
    return _opportunity_decision(outcomes, module_items, fallback)


def _market_sections(
    outcomes: tuple[_CapabilityOutcome, ...],
) -> tuple[ResearchModuleSection, ...]:
    themes = _outcome_for(outcomes, "sector_selector")
    theme_items: list[ResearchModuleItem] = []
    for row in (themes.rows if themes else ())[:5]:
        name = _theme_name(row)
        if not name:
            continue
        strong = _sector_row_has_strength(row)
        theme_items.append(
            ResearchModuleItem(
                kind="theme",
                name=name,
                label="当前强势主题" if strong else "高关注待确认",
                summary=_sector_summary(row),
                risk="热度回落且涨跌幅转负时降级观察",
                status="ready" if strong else "partial",
                facts=_display_facts("sector_selector", row),
            )
        )
    theme_items_tuple = tuple(theme_items)
    breadth = _outcome_for(outcomes, "breadth")
    breadth_row = breadth.rows[0] if breadth and breadth.rows else ()
    breadth_items = tuple(
        ResearchModuleItem(
            kind="breadth",
            name=_short_metric(fact.label),
            label="市场分布",
            summary=fact.value,
            status="ready",
            facts=(fact,),
        )
        for fact in breadth_row
        if any(
            term in fact.label
            for term in ("上涨家数", "下跌家数", "平盘家数", "涨停家数", "跌停家数")
        )
    )
    hot = _outcome_for(outcomes, "hot_stock")
    hot_items = tuple(
        item
        for row in (hot.rows if hot else ())[:10]
        if (item := _hot_stock_item(row)) is not None
    )
    strong_theme_names = [
        name
        for item in theme_items_tuple
        if item.status == "ready"
        if (name := _public_classification_value(item.name, 120))
    ]
    theme_names = "、".join(strong_theme_names[:3])
    has_public_theme_name = any(
        _public_classification_value(item.name, 120) for item in theme_items_tuple
    )
    hot_names = "、".join(item.name for item in hot_items[:3])
    return (
        ResearchModuleSection(
            key="market-themes",
            title="当前主题",
            conclusion=(
                f"{theme_names}靠前，先看持续性与扩散。"
                if theme_names
                else "强势主题待确认。"
                if has_public_theme_name
                else "主题分类待确认，强度数据已返回。"
                if theme_items_tuple
                else "主题证据待补。"
            ),
            tone="positive" if theme_names else "neutral",
            items=theme_items_tuple,
        ),
        ResearchModuleSection(
            key="market-breadth",
            title="涨跌分布",
            conclusion=_breadth_summary(breadth_row) if breadth_row else "涨跌分布待补。",
            tone=_breadth_tone(breadth_row),
            items=breadth_items,
        ),
        ResearchModuleSection(
            key="market-hot",
            title="热门股票",
            conclusion=(
                f"成交活跃股集中在{hot_names}等标的，需结合所属主题判断。"
                if hot_names
                else "热门股票证据待补。"
            ),
            items=hot_items,
        ),
    )


def _portfolio_sections(
    outcomes: tuple[_CapabilityOutcome, ...],
) -> tuple[ResearchModuleSection, ...]:
    groups = _portfolio_theme_groups(outcomes)
    ordered_groups = sorted(groups.items(), key=lambda item: (-len(item[1]), item[0]))

    def theme_item(
        theme: str,
        members: list[tuple[ResearchTarget, float | None]],
    ) -> ResearchModuleItem:
        return ResearchModuleItem(
            kind="portfolio_theme",
            name=theme,
            label=f"{len(members)}只持仓",
            summary=(
                f"{len(members)}只持仓缺少主题证据，已计入待补。"
                if theme == "主题待补"
                else f"{theme}覆盖{len(members)}只持仓。"
            ),
            risk="仅按持仓数量统计，不代表资金暴露。",
            status="missing" if theme == "主题待补" else "ready",
            facts=(ResearchFact(label="持仓数量", value=str(len(members))),),
        )
    valid_groups = [(theme, members) for theme, members in ordered_groups if theme != "主题待补"]
    selected_groups = valid_groups[:8]
    pending_members = groups.get("主题待补", [])
    if pending_members:
        selected_groups = selected_groups[:7]
    theme_items = tuple(theme_item(theme, members) for theme, members in selected_groups)
    if pending_members:
        theme_items += (theme_item("主题待补", pending_members),)

    divergence_items = tuple(
        ResearchModuleItem(
            kind="theme_divergence",
            name=theme,
            label="主题内分化",
            summary=_theme_divergence_summary(members),
            risk="强弱切换或同步转弱时重新评估主题暴露。",
            status="ready",
        )
        for theme, members in valid_groups
        if len(members) >= 2
    )
    pending_count = len(pending_members)
    primary_names = "、".join(theme for theme, _members in selected_groups[:3])
    if primary_names:
        theme_conclusion = f"主要主题：{primary_names}。"
        if pending_count:
            theme_conclusion += f"{pending_count}只持仓主题待补。"
    elif pending_count:
        theme_conclusion = f"{pending_count}只持仓主题待补。"
    else:
        theme_conclusion = "持仓主题证据待补。"
    return (
        ResearchModuleSection(
            key="portfolio-themes",
            title="持仓主题",
            conclusion=theme_conclusion,
            items=theme_items,
        ),
        ResearchModuleSection(
            key="portfolio-divergence",
            title="主题内分化",
            conclusion=(
                "同一主题内强弱并存，优先处理相对弱势标的。"
                if any(
                    "相对强" in item.summary and "相对弱" in item.summary
                    for item in divergence_items
                )
                else "重叠主题行情待确认。"
                if divergence_items
                else "暂无可比重叠主题。"
            ),
            items=divergence_items,
        ),
    )


def _opportunity_sections(
    outcomes: tuple[_CapabilityOutcome, ...],
    module_items: tuple[ResearchModuleItem, ...],
) -> tuple[ResearchModuleSection, ...]:
    themes = _outcome_for(outcomes, "sector_selector")
    ordered_strong_themes = _ordered_strong_opportunity_themes(outcomes)
    strong_theme_names = {normalized for _name, normalized in ordered_strong_themes}
    negative_reason = _opportunity_negative_reason(outcomes)
    theme_items = tuple(
        ResearchModuleItem(
            kind="theme",
            name=_theme_name(row),
            label="机会主题",
            summary=_sector_summary(row),
            risk="主题热度回落且成交收缩时停止扩展候选。",
            status="ready" if _sector_row_has_strength(row) else "partial",
            facts=_display_facts("sector_selector", row),
        )
        for row in (themes.rows if themes else ())[:5]
        if _theme_name(row)
    )
    candidate_items: list[ResearchModuleItem] = []
    for item in module_items:
        if item.kind != "candidate":
            continue
        candidate_theme = _candidate_theme(item.facts)
        primary_theme = _candidate_primary_theme(item, ordered_strong_themes)
        matched = bool(primary_theme)
        if not candidate_theme:
            candidate_status = "missing"
        elif negative_reason or not matched:
            candidate_status = "partial"
        else:
            candidate_status = item.status
        candidate_risk = "失效条件：主题退潮、成交萎缩或基本证据转弱。"
        if negative_reason:
            candidate_risk = (
                f"模块级风险：{negative_reason}；未映射到单只候选，统一降级复核。"
            )
        candidate_items.append(
            ResearchModuleItem(
                kind=item.kind,
                code=item.code,
                name=item.name,
                label=primary_theme or _candidate_industry(item.facts) or "主题待确认",
                summary=f"入选依据：{item.summary}；确认条件：主题延续且成交保持活跃。",
                risk=candidate_risk,
                status=candidate_status,
                facts=item.facts,
            )
        )
    candidate_items_tuple = tuple(candidate_items)
    theme_names = "、".join(
        name
        for item in theme_items[:3]
        if _normalized_theme_name(item.name) in strong_theme_names
        if (name := _public_classification_value(item.name, 120))
    )
    all_theme_rows_strong = bool(theme_items) and all(
        _sector_row_has_strength(row) for row in (themes.rows if themes else ())
    )
    return (
        ResearchModuleSection(
            key="opportunity-themes",
            title="机会主题",
            conclusion=(
                f"{theme_names}具备强度证据，进入持续性确认。"
                if theme_names
                else "主题分类待确认，强度数据已返回。"
                if all_theme_rows_strong
                else "主题名称已返回，但强度证据不足。"
            ),
            tone="negative" if negative_reason else "positive" if theme_names else "neutral",
            items=theme_items,
        ),
        ResearchModuleSection(
            key="opportunity-candidates",
            title="主题候选",
            conclusion=(
                f"存在模块级不利证据：{negative_reason}，候选统一降级待确认。"
                if negative_reason
                else f"筛出{len(candidate_items_tuple)}只候选，均需满足确认条件。"
                if candidate_items_tuple
                else "暂无满足证据门槛的候选。"
            ),
            items=candidate_items_tuple,
        ),
    )


def _market_decision(
    outcomes: tuple[_CapabilityOutcome, ...],
) -> tuple[str, str]:
    index = _outcome_for(outcomes, "index")
    evaluated_indexes = 0
    repairing_indexes = 0
    daily_evaluated = 0
    daily_down = 0
    for row in index.rows if index else ():
        daily_changes: list[float] = []
        period_changes: list[float] = []
        for fact in row:
            if "涨跌幅" not in fact.label:
                continue
            value = _numeric_value(fact.value)
            if value is None:
                continue
            if "[" in fact.label and "-" in fact.label:
                period_changes.append(value)
            else:
                daily_changes.append(value)
        if daily_changes:
            daily_evaluated += 1
            daily_value = sum(daily_changes) / len(daily_changes)
            if daily_value < 0:
                daily_down += 1
        if daily_changes and period_changes:
            evaluated_indexes += 1
            if any(value > 0 for value in daily_changes) and any(
                value < 0 for value in period_changes
            ):
                repairing_indexes += 1
    breadth = _outcome_for(outcomes, "breadth")
    row = breadth.rows[0] if breadth and breadth.rows else ()
    tone = _breadth_tone(row)
    if tone == "negative":
        return "偏弱", "下跌家数占优，市场表现偏弱；先控制风险并等待扩散修复。"
    repair_majority = (
        evaluated_indexes > 0 and repairing_indexes >= evaluated_indexes // 2 + 1
    )
    if repair_majority:
        return (
            "修复中",
            "指数当日回升，但区间趋势仍弱；先看强势主题能否带动上涨家数持续扩散。",
        )
    if tone == "positive":
        if daily_evaluated and daily_down >= daily_evaluated // 2 + 1:
            return (
                "结构分化",
                "上涨家数占优，但核心指数回落居多；市场结构分化，先确认上涨能否向权重扩散。",
            )
        return "偏强", "上涨家数占优，市场表现偏强；继续确认主题持续性。"
    if row:
        return "分化中", "涨跌分布接近，市场仍在分化；只跟踪证据最完整的主题。"
    return "分布待补", "指数已有更新，但涨跌分布不足，暂不提高判断强度。"


def _portfolio_decision(
    outcomes: tuple[_CapabilityOutcome, ...],
    fallback: str,
) -> tuple[str, str]:
    priority_risk = _portfolio_priority_risk(outcomes)
    if priority_risk:
        return "先处理风险", f"{priority_risk}；先处理已确认风险，再看主题集中与分化。"
    groups = _portfolio_theme_groups(outcomes)
    if not groups:
        return "主题待补", fallback
    pending_count = len(groups.get("主题待补", ()))
    if pending_count:
        return (
            "主题待补",
            f"{pending_count}只持仓缺少主题证据；先补齐归属，再判断主题集中与分化。",
        )
    if any(
        "相对强" in _theme_divergence_summary(members)
        and "相对弱" in _theme_divergence_summary(members)
        for members in groups.values()
    ):
        return "分化明显", "同一主题内强弱分化明显，先复核相对弱势持仓及其基本证据。"
    if any(len(members) > 1 for members in groups.values()):
        return "主题集中", "持仓在少数主题内集中，先检查主题持续性和个股同步性。"
    return "主题分散", "持仓主题较分散，逐只按事件、预期和价格证据复核。"


def _stock_decision(
    outcomes: tuple[_CapabilityOutcome, ...],
    fallback: str,
) -> tuple[str, str]:
    target = next(
        (
            _target_label(outcome.request.target)
            for outcome in outcomes
            if _target_label(outcome.request.target)
        ),
        "",
    )
    prefix = f"{target}：" if target else ""
    finance = _outcome_for(outcomes, "finance")
    event = _outcome_for(outcomes, "event")
    finance_stressed = any(
        _finance_row_stressed(row) for row in (finance.rows if finance else ())
    )
    event_stressed = any(
        _event_row_negative(row)
        for row in (event.rows if event else ())
    )
    if finance_stressed:
        return (
            "基本面承压",
            f"{prefix}基本面承压，利润和经营现金流仍弱；先等业绩转正与价格确认。",
        )
    if event_stressed:
        return (
            "基本面承压",
            f"{prefix}基本面承压，已出现明确不利事件；先核查影响范围与解除条件。",
        )
    ready_capabilities = {
        outcome.request.capability for outcome in outcomes if outcome.rows
    }
    core_capabilities = {"finance", "business", "consensus", "event"}
    confirmation_capabilities = {"market", "report"}
    core_complete = core_capabilities <= ready_capabilities
    confirmation_complete = confirmation_capabilities <= ready_capabilities
    if (
        core_complete
        and confirmation_complete
        and len(ready_capabilities) >= 6
    ):
        return "可继续跟踪", fallback
    if len(ready_capabilities) >= 4:
        missing_confirmations: list[str] = []
        if "market" not in ready_capabilities:
            missing_confirmations.append("价格")
        if "report" not in ready_capabilities:
            missing_confirmations.append("研报")
        missing_core = core_capabilities - ready_capabilities
        if missing_core:
            missing_confirmations.append("核心研究")
        missing_text = "、".join(missing_confirmations) or "关键证据"
        return (
            "等待确认",
            f"{prefix}当前未见明确负面，但确认链不完整；先等{missing_text}等缺失确认。",
        )
    return "证据不足", fallback


def _opportunity_decision(
    outcomes: tuple[_CapabilityOutcome, ...],
    module_items: tuple[ResearchModuleItem, ...],
    fallback: str,
) -> tuple[str, str]:
    theme_names = _strong_opportunity_themes(outcomes)
    negative_reason = _opportunity_negative_reason(outcomes)
    has_candidate = any(item.kind == "candidate" for item in module_items)
    has_matched_candidate = any(
        _candidate_matches_themes(item, theme_names)
        for item in module_items
        if item.kind == "candidate"
    )
    if negative_reason:
        return "主线待确认", f"出现模块级不利证据：{negative_reason}；候选统一降级待确认。"
    if theme_names and has_matched_candidate:
        return "有主线", "主题与候选同时出现；先等持续性和成交确认，再保留通过失效检查的标的。"
    if theme_names and not has_candidate:
        return "有主题无候选", "主题方向已出现，但候选证据不足，暂不扩展清单。"
    if theme_names and has_candidate:
        return "主线待确认", "候选与当前主题尚未形成可核查关联，暂不判定主线。"
    return "主线待确认", fallback


def _outcome_for(
    outcomes: tuple[_CapabilityOutcome, ...], capability: str
) -> _CapabilityOutcome | None:
    return next(
        (outcome for outcome in outcomes if outcome.request.capability == capability),
        None,
    )


def _theme_name(row: tuple[ResearchFact, ...]) -> str:
    return _row_value(
        row,
        ("板块名称", "行业名称", "概念名称", "指数简称", "所属行业", "所属概念"),
    )


def _portfolio_theme_groups(
    outcomes: tuple[_CapabilityOutcome, ...],
) -> dict[str, list[tuple[ResearchTarget, float | None]]]:
    by_target: dict[tuple[str, str], list[_CapabilityOutcome]] = {}
    for outcome in outcomes:
        target = outcome.request.target
        by_target.setdefault((target.code, target.name), []).append(outcome)
    groups: dict[str, list[tuple[ResearchTarget, float | None]]] = {}
    for (code, name), target_outcomes in by_target.items():
        industry = next(
            (
                outcome
                for outcome in target_outcomes
                if outcome.request.capability == "industry" and outcome.rows
            ),
            None,
        )
        themes = _portfolio_theme_tokens(industry.rows if industry else ())
        if not themes:
            themes = ("主题待补",)
        market = next(
            (
                outcome
                for outcome in target_outcomes
                if outcome.request.capability == "market" and outcome.rows
            ),
            None,
        )
        change = _row_change(market.rows[0]) if market else None
        member = (ResearchTarget(code=code, name=name), change)
        for theme in themes:
            groups.setdefault(theme, []).append(member)
    return groups


def _portfolio_theme_tokens(
    rows: tuple[tuple[ResearchFact, ...], ...],
) -> tuple[str, ...]:
    themes: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for fact in row:
            label = fact.label
            is_classification = label in {"概念", "行业"} or any(
                term in label
                for term in ("所属概念", "概念名称", "所属行业", "行业名称")
            )
            if not is_classification:
                continue
            for value in re.split(r"[、,，/；;]", fact.value):
                theme = value.strip()
                fingerprint = _normalized_theme_name(theme).casefold()
                if not theme or not fingerprint or fingerprint in seen:
                    continue
                if _contains_public_brand(theme):
                    continue
                themes.append(theme)
                seen.add(fingerprint)
    return tuple(themes)


def _theme_divergence_summary(
    members: list[tuple[ResearchTarget, float | None]],
) -> str:
    comparable = [(target, change) for target, change in members if change is not None]
    if len(comparable) < 2:
        return "可比行情不足，主题内强弱待确认。"
    strongest = max(comparable, key=lambda item: item[1])
    weakest = min(comparable, key=lambda item: item[1])
    if strongest[1] == weakest[1]:
        return "主题内表现接近，暂未出现明显分化。"
    return (
        f"相对强：{_target_label(strongest[0])}（{strongest[1]:.2f}%）；"
        f"相对弱：{_target_label(weakest[0])}（{weakest[1]:.2f}%）。"
    )


def _row_change(row: tuple[ResearchFact, ...]) -> float | None:
    fact = _fact_matching(row, ("涨跌幅", "涨跌"))
    return _numeric_value(fact.value) if fact else None


def _finance_row_stressed(row: tuple[ResearchFact, ...]) -> bool:
    profit = _fact_matching(row, ("归母净利润", "净利润"))
    cash_flow = _fact_matching(row, ("经营现金流", "经营活动产生的现金流"))
    profit_value = _numeric_value(profit.value) if profit else None
    cash_value = _numeric_value(cash_flow.value) if cash_flow else None
    return (
        profit_value is not None
        and cash_value is not None
        and profit_value <= 0
        and cash_value < 0
    )


def _candidate_theme(facts: tuple[ResearchFact, ...]) -> str:
    return _row_value(facts, ("所属概念", "概念", "所属行业", "行业"))


def _candidate_industry(facts: tuple[ResearchFact, ...]) -> str:
    return _row_value(facts, ("所属行业", "行业"))


def _candidate_theme_tokens(facts: tuple[ResearchFact, ...]) -> set[str]:
    return {
        _normalized_theme_name(part)
        for fact in facts
        if any(term in fact.label for term in ("所属概念", "概念", "所属行业", "行业"))
        for part in re.split(r"[、,，/；;]", fact.value)
        if part.strip()
    }


def _candidate_matches_themes(
    item: ResearchModuleItem,
    theme_names: set[str],
) -> bool:
    return bool(_candidate_theme_tokens(item.facts) & theme_names)


def _candidate_primary_theme(
    item: ResearchModuleItem,
    ordered_themes: tuple[tuple[str, str], ...],
) -> str:
    candidate_themes = _candidate_theme_tokens(item.facts)
    return next(
        (name for name, normalized in ordered_themes if normalized in candidate_themes),
        "",
    )


def _normalized_theme_name(value: str) -> str:
    cleaned = re.sub(r"(?:概念|行业|板块)$", "", value.strip())
    return re.sub(r"\s+", "", cleaned).casefold()


def _sector_row_is_weak(row: tuple[ResearchFact, ...]) -> bool:
    weak_terms = ("低迷", "偏弱", "走弱", "降温", "萎缩", "缩量", "弱")
    for fact in row:
        if any(term in fact.label for term in ("涨跌", "涨幅")):
            value = _numeric_value(fact.value)
            if value is not None and value < 0:
                return True
        if any(term in fact.label for term in ("热度", "强度")):
            if any(term in fact.value for term in weak_terms):
                return True
            value = _numeric_value(fact.value)
            if value is not None and "排名" not in fact.label and value < 50:
                return True
    return False


def _sector_row_has_strength(row: tuple[ResearchFact, ...]) -> bool:
    if _sector_row_is_weak(row):
        return False
    weak_terms = ("低迷", "偏弱", "弱", "降温", "萎缩", "缩量", "低")
    strong_terms = ("高", "强", "活跃", "放量", "升温", "领先")
    for fact in row:
        label = fact.label
        if not any(
            term in label
            for term in (
                "热度",
                "强度",
                "成交",
                "排名",
                "涨跌",
                "涨幅",
                "量比",
                "换手",
                "持续",
            )
        ):
            continue
        value_text = fact.value.strip()
        if any(term in value_text for term in weak_terms):
            continue
        if any(term in value_text for term in strong_terms):
            return True
        value = _numeric_value(fact.value)
        if any(term in fact.label for term in ("强度", "热度")):
            if value is not None and value >= 50:
                return True
        if "排名" in fact.label:
            if value is not None and 0 < value <= 10:
                return True
        if "成交" in fact.label:
            if value is not None and value >= 100_000_000:
                return True
        if any(term in fact.label for term in ("量比", "换手")):
            if value is not None and value >= 1:
                return True
        if any(term in fact.label for term in ("涨跌", "涨幅")):
            if value is not None and value > 0:
                return True
    return False


def _strong_opportunity_themes(
    outcomes: tuple[_CapabilityOutcome, ...],
) -> set[str]:
    return {
        normalized
        for _name, normalized in _ordered_strong_opportunity_themes(outcomes)
    }


def _ordered_strong_opportunity_themes(
    outcomes: tuple[_CapabilityOutcome, ...],
) -> tuple[tuple[str, str], ...]:
    themes = _outcome_for(outcomes, "sector_selector")
    ordered: list[tuple[str, str]] = []
    seen: set[str] = set()
    for row in themes.rows if themes else ():
        name = _public_classification_value(_theme_name(row), 120)
        normalized = _normalized_theme_name(name)
        if not name or not normalized or normalized in seen:
            continue
        if not _sector_row_has_strength(row):
            continue
        ordered.append((name, normalized))
        seen.add(normalized)
    return tuple(ordered)


def _event_row_negative(row: tuple[ResearchFact, ...]) -> bool:
    if any(_fact_is_negative(fact) for fact in row):
        return True
    text = " ".join(f"{fact.label} {fact.value}" for fact in row)
    state_markers: list[tuple[int, int, bool]] = []
    for pattern in (
        r"撤销|撤诉|解除|未实施|不再实施|终止实施",
        r"终止.{0,12}减持计划|减持计划.{0,12}终止",
    ):
        state_markers.extend(
            (match.end(), 1, False) for match in re.finditer(pattern, text)
        )
    for pattern in (
        r"预亏|预减|下修|下调|监管|诉讼|处罚|立案|减持|终止上市",
    ):
        state_markers.extend(
            (match.end(), 0, True) for match in re.finditer(pattern, text)
        )
    return max(state_markers, default=(0, 0, False))[-1]


def _consensus_row_negative(row: tuple[ResearchFact, ...]) -> bool:
    ratings = [
        rating
        for fact in row
        if "评级" in fact.label
        for rating in re.findall(r"买入|增持|中性|减持|卖出", fact.value)
    ]
    if ratings and ratings[-1] in {"减持", "卖出"}:
        return True
    text = " ".join(
        f"{fact.label} {fact.value}" for fact in row if "评级" not in fact.label
    )
    if any(term in text for term in ("下修", "下调", "调低", "卖出", "减持")):
        return True
    if ratings:
        return False
    return "回落" in _consensus_summary(row)


def _portfolio_priority_risk(
    outcomes: tuple[_CapabilityOutcome, ...],
) -> str:
    for outcome in outcomes:
        capability = outcome.request.capability
        if capability not in {"event", "consensus"}:
            continue
        for row in outcome.rows:
            negative = (
                _event_row_negative(row)
                if capability == "event"
                else _consensus_row_negative(row)
            )
            if not negative:
                continue
            summary = _finding_summary(capability, row)
            target = _target_label(outcome.request.target)
            return f"{target}：{summary}" if target else summary
    for outcome in outcomes:
        if outcome.request.capability != "market":
            continue
        for row in outcome.rows:
            change = _row_change(row)
            if change is None or change > -5:
                continue
            change_fact = _fact_matching(row, ("涨跌幅", "涨跌"))
            target = _target_label(outcome.request.target)
            change_text = change_fact.value if change_fact else f"{change:.2f}%"
            description = f"{target}：跌幅{change_text}，已进入相对弱势"
            return description if target else f"跌幅{change_text}，已进入相对弱势"
    return ""


def _opportunity_negative_reason(
    outcomes: tuple[_CapabilityOutcome, ...],
) -> str:
    for outcome in outcomes:
        capability = outcome.request.capability
        for row in outcome.rows:
            if capability == "event" and _event_row_negative(row):
                return _finding_summary(capability, row)
            if capability == "news":
                text = " ".join(f"{fact.label} {fact.value}" for fact in row)
                if any(
                    term in text
                    for term in (
                        "重大风险",
                        "风险事件",
                        "风险上升",
                        "风险加剧",
                        "监管",
                        "诉讼",
                        "处罚",
                        "立案",
                        "减持",
                        "预亏",
                        "预减",
                        "下修",
                    )
                ):
                    return _finding_summary(capability, row)
    return ""


def _breadth_tone(row: tuple[ResearchFact, ...]) -> str:
    up = _numeric_fact(row, "上涨家数")
    down = _numeric_fact(row, "下跌家数")
    limit_up = _numeric_fact(row, "涨停家数")
    limit_down = _numeric_fact(row, "跌停家数")
    if up is None or down is None:
        return "neutral"
    limit_down_expanded = (
        limit_down is not None
        and limit_down >= 20
        and (limit_up is None or limit_down >= limit_up * 2)
    )
    if down > up * 1.2 or limit_down_expanded:
        return "negative"
    if up > down * 1.2:
        return "positive"
    return "neutral"


def _numeric_fact(row: tuple[ResearchFact, ...], term: str) -> float | None:
    fact = _fact_matching(row, (term,))
    return _numeric_value(fact.value) if fact else None


def _hot_stock_item(row: tuple[ResearchFact, ...]) -> ResearchModuleItem | None:
    code = _row_value(row, ("股票代码", "证券代码"))
    name = _row_value(row, ("股票简称", "证券简称", "股票名称"))
    if not code or not name:
        return None
    theme = _row_value(row, ("所属概念", "概念", "所属行业", "行业"))
    return ResearchModuleItem(
        kind="hot_stock",
        code=code,
        name=name,
        label=theme or "主题待确认",
        summary=_hot_stock_summary(row),
        risk="成交降温或所属主题转弱时停止追踪。",
        facts=_display_facts("hot_stock", row),
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
            else "未发现高优先风险，仍需结合账户边界复核"
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
    if capability == "breadth":
        return _breadth_summary(row)
    if capability == "hot_stock":
        return _hot_stock_summary(row)
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
    period_changes = [
        fact
        for fact in row
        if "涨跌幅[" in fact.label and "-" in fact.label
    ][:2]
    metrics = [
        f"{_short_metric(fact.label)} {fact.value}"
        for fact in (price, change, *period_changes)
        if fact is not None
    ]
    if name and metrics:
        return f"{name.value} {'，'.join(metrics)}"
    return _compact_facts(row)


def _sector_summary(row: tuple[ResearchFact, ...]) -> str:
    name = _fact_matching(row, ("板块名称", "行业名称", "概念名称", "指数简称"))
    public_name = _public_classification_value(name.value, 120) if name else ""
    if name and not public_name:
        return "主题分类待确认，强度数据已返回。"
    heat = _fact_matching(row, ("热度", "排名", "强度"))
    amount = _fact_matching(row, ("成交额", "成交量"))
    metrics = [
        f"{_short_metric(fact.label)} {fact.value}"
        for fact in (heat, amount)
        if fact is not None
    ]
    if public_name and metrics:
        return f"{public_name} {'，'.join(metrics)}"
    if public_name:
        return f"{public_name}，强度证据待补。"
    return _compact_facts(row)


def _breadth_summary(row: tuple[ResearchFact, ...]) -> str:
    if not row:
        return "涨跌分布待补。"
    values = [
        f"{_short_metric(fact.label)}{fact.value}"
        for fact in row
        if any(
            term in fact.label
            for term in ("上涨家数", "下跌家数", "平盘家数", "涨停家数", "跌停家数")
        )
    ]
    return "，".join(values) if values else _compact_facts(row)


def _hot_stock_summary(row: tuple[ResearchFact, ...]) -> str:
    name = _fact_matching(row, ("股票简称", "证券简称", "股票名称"))
    change = _fact_matching(row, ("涨跌幅", "涨跌"))
    amount = _fact_matching(row, ("成交额", "成交量", "换手率"))
    metrics = [
        f"{_short_metric(fact.label)} {fact.value}"
        for fact in (change, amount)
        if fact is not None
    ]
    if name and metrics:
        return f"{name.value}：{'，'.join(metrics)}"
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
        return _clean_text(f"{title.value}：{summary_text}", 80)
    if title:
        return _clean_text(title.value, 180)
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
        return _clean_text(f"{target}：{summary}" if target else summary, 180)
    prefixes = {
        "market": "市场证据显示：",
        "portfolio": "重点持仓需要先看：",
        "opportunity": "当前可核查线索：",
    }
    return _clean_text(f"{prefixes.get(module, '')}{summary}", 180)


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
    period = re.search(r"\[(20\d{6})-(20\d{6})]", label)
    cleaned = re.sub(r"\[[^]]+]", "", label)
    cleaned = cleaned.replace(":前复权", "").replace("_前复权", "")
    cleaned = cleaned.replace("增长率", "")
    if period:
        start, end = period.groups()
        cleaned += f"（{start[4:6]}-{start[6:]}至{end[4:6]}-{end[6:]}）"
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
                        return _clean_text(
                            f"{name.value} · {_short_metric(negative.label)}：{negative.value}",
                            180,
                        )
                description = f"{negative.label}：{negative.value}"
                target = _target_label(outcome.request.target)
                if module == "portfolio" and target:
                    description = f"{target} · {description}"
                return _clean_text(description, 180)
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
                return _clean_text(description, 180)
    return fallback


def _detail_label(request: CapabilityRequest) -> str:
    label = CAPABILITY_LABELS[request.capability]
    target = _target_label(request.target)
    return f"{target} · {label}" if target else label


def _target_label(target: ResearchTarget) -> str:
    return _public_identity_text(target.name or target.code, 64)


def _research_cache_key(
    module: str,
    context: ResearchContext,
) -> tuple[object, ...]:
    holdings = tuple(
        (_clean_text(item.code, 32), _clean_text(item.name, 64))
        for item in context.holdings[:20]
    )
    return (
        module,
        _clean_text(context.code, 32),
        _clean_text(context.name, 64),
        _clean_text(context.sector, 64),
        holdings,
    )
