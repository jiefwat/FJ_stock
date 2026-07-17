from __future__ import annotations

import re
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any, Callable

from .iwencai import (
    SKILLS,
    IwencaiConfigurationError,
    IwencaiError,
    IwencaiGatewayError,
    IwencaiSkillClient,
    build_module_research_query,
    route_stock_research_skill,
)
from .research_engine import ResearchContext, build_workspace_queries
from .research_evidence import normalize_capability_rows

DEEP_RESEARCH_GROUPS = {
    "company": ("公司与经营", ("basicinfo", "business", "management")),
    "finance": ("财务与估值", ("finance",)),
    "industry": ("行业与同行", ("industry",)),
    "consensus": ("机构与预期", ("consensus", "report")),
    "market": ("资金与技术", ("market",)),
    "event": ("公告与事件", ("event", "announcement", "news")),
}

CAPABILITY_GROUPS = {
    capability: group
    for group, (_title, capabilities) in DEEP_RESEARCH_GROUPS.items()
    for capability in capabilities
}

MAX_CACHE_ENTRIES = 128
_ACCOUNT_POSSESSIVE_PATTERN = re.compile(
    r"(?:我的|本人的|个人的)[^，。！？!?]{0,16}"
    r"(?:账户|持仓|仓位|买入价|盈亏|持股|股数|成本价|成本|均价)"
)
_ACCOUNT_CONTEXT_PATTERN = re.compile(r"账户|账号|组合列表")
_PERSONAL_OWNERSHIP_PATTERN = re.compile(
    r"(?:我|本人|个人)[^，。！？!?]*(?:持有|持股|有)"
    r"[^，。！？!?]{0,16}(?:\d[\d,.]*|[一二三四五六七八九十百千万两]+)(?:股|手)"
)
_STRONG_PUBLIC_SUBJECT_PATTERN = re.compile(
    r"大股东|控股股东|实际控制人|实控人|前十大股东|机构|基金|董监高|员工持股"
)
_GENERIC_PUBLIC_RESEARCH_PATTERN = re.compile(
    r"(?:公司|企业|产品|原材料|经营)[^，。！？!?]{0,24}(?:成本|盈亏)"
)
_SUBJECTLESS_PRIVATE_PATTERN = re.compile(
    r"持股(?:的)?(?:(?:平均)?成本|数量|均价)|"
    r"(?:当前|累计)(?:的)?(?:总)?盈亏|"
    r"持仓|仓位|浮盈|浮亏|成本价|买入价|买入成本|建仓(?:价|成本)"
)
_ENGLISH_ACCOUNT_POSSESSIVE_PATTERN = re.compile(
    r"\bmy\s+(?:stake|position|holdings|shares|(?:average\s+)?cost|pnl|p\s*&\s*l)\b|"
    r"\baccount\s+(?:weight|cost|position|holdings|pnl)\b|\bcookie\b",
    re.IGNORECASE,
)
_ENGLISH_PERSONAL_OWNERSHIP_PATTERN = re.compile(
    r"\bi\s+(?:hold|own|bought|have)\s+\d[\d,.]*\s+shares?\b",
    re.IGNORECASE,
)
_ENGLISH_STRONG_PUBLIC_SUBJECT_PATTERN = re.compile(
    r"\b(?:institutional|major\s+shareholder|controlling\s+shareholder)\b",
    re.IGNORECASE,
)
_ENGLISH_SUBJECTLESS_PRIVATE_PATTERN = re.compile(
    r"\bposition\s+size\b|\bentry\s+price\b",
    re.IGNORECASE,
)
_SENSITIVE_PUBLIC_FACT = re.compile(
    r"问财|同花顺|iwencai|skill[\s_-]*id|trace|gateway|provider|api[\s_-]*key|"
    r"authorization|secret",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class DeepResearchFact:
    label: str
    value: str

    def to_public_dict(self) -> dict[str, str]:
        return {
            "label": _safe_public_fact_text(self.label, fallback="研究事实", limit=80),
            "value": _safe_public_fact_text(
                self.value,
                fallback="内容已做安全处理",
                limit=500,
            ),
        }


@dataclass(frozen=True)
class DeepResearchGroup:
    key: str
    title: str
    status: str
    facts: tuple[DeepResearchFact, ...] = ()
    recovery: str = ""

    def to_public_dict(self) -> dict[str, object]:
        return {
            "key": self.key,
            "title": self.title,
            "status": self.status,
            "facts": [fact.to_public_dict() for fact in self.facts],
            "recovery": self.recovery,
        }


@dataclass(frozen=True)
class StockDeepResearchResult:
    ok: bool
    status: str
    code: str
    name: str
    focus: str
    groups: tuple[DeepResearchGroup, ...]
    coverage_ready: int
    coverage_total: int
    cached: bool
    as_of: str
    recovery: str = ""

    def to_public_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "status": self.status,
            "code": self.code,
            "name": self.name,
            "focus": self.focus,
            "groups": [group.to_public_dict() for group in self.groups],
            "coverage": {
                "ready": self.coverage_ready,
                "total": self.coverage_total,
            },
            "cached": self.cached,
            "as_of": self.as_of,
            "recovery": self.recovery,
        }


@dataclass(frozen=True)
class _CapabilityResult:
    capability: str
    facts: tuple[DeepResearchFact, ...] = ()
    succeeded: bool = False
    error: Exception | None = None


class StockDeepResearchService:
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
        self._cache: OrderedDict[
            tuple[str, str, str, str], tuple[float, StockDeepResearchResult]
        ] = OrderedDict()
        self._cache_lock = Lock()

    def research(
        self,
        *,
        code: str,
        name: str,
        focus: str = "all",
        question: str = "",
        refresh: bool = False,
    ) -> StockDeepResearchResult:
        code = _clean_input(code, 32)
        name = _clean_input(name, 64)
        focus = _clean_input(focus, 32).lower() or "all"
        question = _clean_input(question)
        if not code and not name:
            raise ValueError("请输入股票代码或名称。")
        if focus != "all" and focus not in DEEP_RESEARCH_GROUPS:
            raise ValueError("研究范围不支持，请选择六个业务组之一。")
        if len(question) > 200:
            raise ValueError("研究问题不能超过 200 个字符。")
        if _contains_private_context(question):
            raise ValueError("研究问题不能包含账户或持仓信息。")

        cache_key = (code, name, focus, question)
        if not refresh:
            cached = self._cached(cache_key)
            if cached is not None:
                return cached

        requests = _requests_for(code=code, name=name, focus=focus, question=question)
        client = self.client_factory()
        results = _execute_requests(client, requests)
        ready = sum(result.succeeded for result in results)
        _raise_if_zero_success(results, ready=ready)
        groups = _build_groups(results, focus=focus, question=question)
        total = len(results)
        status = "complete" if ready == total else "partial"
        result = StockDeepResearchResult(
            ok=True,
            status=status,
            code=code,
            name=name,
            focus=focus,
            groups=groups,
            coverage_ready=ready,
            coverage_total=total,
            cached=False,
            as_of=datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds"),
            recovery="",
        )
        if self.cache_ttl > 0:
            self._store_cached(cache_key, result)
        return result

    def _cached(
        self,
        cache_key: tuple[str, str, str, str],
    ) -> StockDeepResearchResult | None:
        with self._cache_lock:
            self._prune_expired_locked(self.clock())
            cached = self._cache.get(cache_key)
            if cached is None:
                return None
            _expires_at, result = cached
            self._cache.move_to_end(cache_key)
            return replace(result, cached=True)

    def _store_cached(
        self,
        cache_key: tuple[str, str, str, str],
        result: StockDeepResearchResult,
    ) -> None:
        with self._cache_lock:
            now = self.clock()
            self._prune_expired_locked(now)
            self._cache[cache_key] = (now + self.cache_ttl, result)
            self._cache.move_to_end(cache_key)
            while len(self._cache) > MAX_CACHE_ENTRIES:
                self._cache.popitem(last=False)

    def _prune_expired_locked(self, now: float) -> None:
        expired = [
            key
            for key, (expires_at, _result) in self._cache.items()
            if expires_at <= now
        ]
        for key in expired:
            self._cache.pop(key, None)


def _requests_for(
    *,
    code: str,
    name: str,
    focus: str,
    question: str,
) -> tuple[tuple[str, str], ...]:
    if question:
        skill = route_stock_research_skill(question)
        capability = next(key for key, value in SKILLS.items() if value == skill)
        query = build_module_research_query(
            "stock",
            question,
            code=code,
            name=name,
        )
        return ((capability, query),)

    request_by_capability = {
        request.capability: request.query
        for request in build_workspace_queries(
            "stock",
            ResearchContext(code=code, name=name),
        )
    }
    capabilities = (
        tuple(CAPABILITY_GROUPS)
        if focus == "all"
        else DEEP_RESEARCH_GROUPS[focus][1]
    )
    return tuple((capability, request_by_capability[capability]) for capability in capabilities)


def _execute_requests(
    client: Any,
    requests: tuple[tuple[str, str], ...],
) -> tuple[_CapabilityResult, ...]:
    indexed: dict[int, _CapabilityResult] = {}
    with ThreadPoolExecutor(max_workers=min(8, len(requests))) as executor:
        futures = {
            executor.submit(_execute_request, client, capability, query): index
            for index, (capability, query) in enumerate(requests)
        }
        for future in as_completed(futures):
            index = futures[future]
            capability = requests[index][0]
            try:
                indexed[index] = future.result()
            except Exception as exc:
                indexed[index] = _CapabilityResult(capability=capability, error=exc)
    return tuple(indexed[index] for index in range(len(requests)))


def _raise_if_zero_success(
    results: tuple[_CapabilityResult, ...],
    *,
    ready: int,
) -> None:
    if ready:
        return
    errors = tuple(result.error for result in results if result.error is not None)
    if any(isinstance(error, IwencaiConfigurationError) for error in errors):
        raise IwencaiConfigurationError("深度研究服务尚未配置。")
    if any(isinstance(error, IwencaiGatewayError) for error in errors):
        raise IwencaiGatewayError("深度研究服务暂时不可用，请稍后重试。")
    raise IwencaiError("深度研究服务暂时不可用，请稍后重试。")


def _execute_request(client: Any, capability: str, query: str) -> _CapabilityResult:
    raw = client.query(SKILLS[capability], query)
    rows = normalize_capability_rows(capability, raw, max_rows=3)
    facts = _dedupe_facts(
        DeepResearchFact(label=fact.label, value=fact.value)
        for row in rows
        for fact in row
    )
    return _CapabilityResult(
        capability=capability,
        facts=facts,
        succeeded=bool(rows),
    )


def _build_groups(
    results: tuple[_CapabilityResult, ...],
    *,
    focus: str,
    question: str,
) -> tuple[DeepResearchGroup, ...]:
    requested = {result.capability for result in results}
    group_keys = (
        tuple(DEEP_RESEARCH_GROUPS)
        if focus == "all" and not question
        else tuple(
            group
            for group in DEEP_RESEARCH_GROUPS
            if requested & set(DEEP_RESEARCH_GROUPS[group][1])
        )
    )
    groups = []
    for key in group_keys:
        title, capabilities = DEEP_RESEARCH_GROUPS[key]
        group_results = [result for result in results if result.capability in capabilities]
        succeeded = sum(result.succeeded for result in group_results)
        facts = _dedupe_facts(
            fact for result in group_results if result.succeeded for fact in result.facts
        )
        status = (
            "ready"
            if group_results and succeeded == len(group_results)
            else "partial"
            if succeeded
            else "unavailable"
        )
        recovery = (
            ""
            if status == "ready"
            else "部分事实待补，请稍后重试。"
            if status == "partial"
            else "该组数据暂未返回，请稍后重试。"
        )
        groups.append(
            DeepResearchGroup(
                key=key,
                title=title,
                status=status,
                facts=facts,
                recovery=recovery,
            )
        )
    return tuple(groups)


def _dedupe_facts(facts: Any) -> tuple[DeepResearchFact, ...]:
    result = []
    seen: set[tuple[str, str]] = set()
    for fact in facts:
        key = (fact.label, fact.value)
        if key in seen:
            continue
        seen.add(key)
        result.append(fact)
    return tuple(result)


def _contains_private_context(question: str) -> bool:
    normalized = question.casefold()
    compact = re.sub(r"\s+", "", normalized)
    if (
        _ACCOUNT_POSSESSIVE_PATTERN.search(compact)
        or _ACCOUNT_CONTEXT_PATTERN.search(compact)
        or _ENGLISH_ACCOUNT_POSSESSIVE_PATTERN.search(normalized)
    ):
        return True
    if _PERSONAL_OWNERSHIP_PATTERN.search(
        compact
    ) or _ENGLISH_PERSONAL_OWNERSHIP_PATTERN.search(normalized):
        return True
    if _STRONG_PUBLIC_SUBJECT_PATTERN.search(
        compact
    ) or _ENGLISH_STRONG_PUBLIC_SUBJECT_PATTERN.search(normalized):
        return False
    if _GENERIC_PUBLIC_RESEARCH_PATTERN.search(compact):
        return False
    return bool(
        _SUBJECTLESS_PRIVATE_PATTERN.search(compact)
        or _ENGLISH_SUBJECTLESS_PRIVATE_PATTERN.search(normalized)
    )


def _safe_public_fact_text(value: object, *, fallback: str, limit: int) -> str:
    cleaned = _clean_input(value, limit)
    return fallback if _SENSITIVE_PUBLIC_FACT.search(cleaned) else cleaned


def _clean_input(value: object, limit: int | None = None) -> str:
    text = str(value or "")
    cleaned = "".join(character if character.isprintable() else " " for character in text)
    normalized = " ".join(cleaned.split())
    return normalized if limit is None else normalized[:limit]
