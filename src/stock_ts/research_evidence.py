from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class EvidenceFact:
    label: str
    value: str


@dataclass(frozen=True)
class CapabilitySchema:
    include_groups: tuple[tuple[str, ...], ...]
    context_groups: tuple[tuple[str, ...], ...] = ()
    minimum_facts: int = 1


CAPABILITY_SCHEMAS = {
    "finance": CapabilitySchema(
        (
            ("营业收入", "营收"),
            ("归母净利润", "净利润"),
            ("经营现金流", "经营活动产生的现金流"),
            ("roe", "净资产收益率"),
            ("毛利率",),
            ("负债",),
        )
    ),
    "consensus": CapabilitySchema(
        (
            ("预测", "一致预期"),
            ("评级",),
            ("目标价",),
            ("上调", "下修"),
        )
    ),
    "business": CapabilitySchema(
        (
            ("主营产品", "主营业务", "主要产品"),
            ("业务范围", "经营范围"),
            ("竞争对手", "竞争格局", "同行"),
            ("客户",),
            ("供应商",),
            ("市场地位", "市占率"),
        )
    ),
    "event": CapabilitySchema(
        (
            ("业绩预告", "业绩快报"),
            ("营业收入", "营收"),
            ("归母净利润", "净利润"),
            ("同比", "环比"),
            ("公告日期", "发生日期", "报告期"),
            ("解禁",),
            ("质押",),
            ("监管",),
            ("诉讼",),
            ("增持", "减持"),
        )
    ),
    "index": CapabilitySchema(
        (
            ("最新价", "最新点位", "收盘"),
            ("涨跌幅", "涨跌"),
            ("成交额", "成交量"),
            ("日期", "时间"),
        ),
        context_groups=(("指数名称", "指数简称", "指数代码"),),
    ),
    "macro": CapabilitySchema(
        (
            ("指标值", "最新值", "公布值", "今值"),
            ("前值", "预测值"),
            ("同比", "环比"),
            ("日期", "时间", "报告期"),
            ("政策", "利率", "汇率", "cpi", "ppi", "gdp", "社融", "m2"),
        ),
        context_groups=(("指标名称", "宏观指标", "事件名称"),),
    ),
    "sector_selector": CapabilitySchema(
        (
            ("热度", "排名", "强度"),
            ("成交额", "成交量"),
            ("涨跌幅", "涨幅"),
            ("持续", "入选理由", "筛选理由"),
            ("板块类型", "领域"),
        ),
        context_groups=(("板块名称", "行业名称", "概念名称"),),
    ),
    "astock_selector": CapabilitySchema(
        (
            ("净利润", "营业收入", "营收", "roe", "毛利率"),
            ("成交额", "成交量", "换手率"),
            ("排名", "评分"),
            ("入选理由", "筛选理由"),
        ),
        context_groups=(("股票代码", "证券代码"), ("股票简称", "证券简称", "股票名称")),
    ),
    "market": CapabilitySchema(
        (
            ("收盘价", "最新价", "开盘价", "最高价", "最低价"),
            ("成交量", "成交额", "换手率"),
            ("主力资金", "资金流"),
            ("涨跌幅", "涨跌"),
            ("日期", "时间"),
        ),
        context_groups=(("股票代码", "证券代码"), ("股票简称", "证券简称", "股票名称")),
    ),
    "announcement": CapabilitySchema(
        (
            ("标题", "公告名称"),
            ("摘要", "内容"),
            ("日期", "时间"),
            ("类型",),
            ("url", "链接"),
        )
    ),
    "news": CapabilitySchema(
        (
            ("标题", "title"),
            ("摘要", "内容", "summary", "content"),
            ("日期", "时间", "publish"),
            ("类型", "category"),
            ("url", "链接"),
        )
    ),
}

IDENTITY_FIELD_TOKENS = (
    "股票代码",
    "证券代码",
    "股票简称",
    "证券简称",
    "股票名称",
    "证券名称",
    "最新价",
    "现价",
    "涨跌幅",
    "交易所",
)

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

MONEY_FIELD_TOKENS = (
    "营业收入",
    "营收",
    "净利润",
    "现金流",
    "总资产",
    "净资产",
    "负债",
    "成交额",
    "市值",
    "目标价",
)

PERCENT_FIELD_TOKENS = (
    "率",
    "占比",
    "比例",
    "涨跌幅",
    "涨幅",
    "跌幅",
    "换手",
)


def normalize_capability_rows(
    capability: str,
    raw: Mapping[str, object],
    *,
    max_rows: int = 3,
    max_facts: int = 6,
) -> tuple[tuple[EvidenceFact, ...], ...]:
    schema = CAPABILITY_SCHEMAS[capability]
    normalized: list[tuple[EvidenceFact, ...]] = []
    seen: set[tuple[tuple[str, str], ...]] = set()
    for row in _raw_rows(raw):
        facts, evidence_count = _extract_ranked_facts(schema, row)
        facts = facts[:max_facts]
        fingerprint = tuple((fact.label, fact.value) for fact in facts)
        if evidence_count < schema.minimum_facts or fingerprint in seen:
            continue
        normalized.append(tuple(facts))
        seen.add(fingerprint)
        if len(normalized) == max_rows:
            break
    return tuple(normalized)


def raw_rows(raw: Mapping[str, object]) -> tuple[Mapping[str, object], ...]:
    return tuple(_raw_rows(raw))


def _raw_rows(raw: Mapping[str, object]) -> list[Mapping[str, object]]:
    rows = raw.get("datas")
    if not isinstance(rows, list):
        rows = raw.get("data")
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, Mapping)]


def _extract_ranked_facts(
    schema: CapabilitySchema,
    row: Mapping[str, object],
) -> tuple[list[EvidenceFact], int]:
    ranked: list[tuple[int, int, EvidenceFact]] = []
    evidence_count = 0
    for source_index, (key, value) in enumerate(row.items()):
        label = _clean_text(str(key), 64)
        normalized_label = label.lower()
        if not label:
            continue
        context_index = _matching_groups(schema.context_groups, normalized_label)
        evidence_index = _matching_groups(schema.include_groups, normalized_label)
        if context_index is None and (
            evidence_index is None or _is_excluded_field(normalized_label)
        ):
            continue
        rendered = _render_value(label, value)
        if rendered:
            if context_index is not None:
                rank = context_index
            else:
                rank = len(schema.context_groups) + int(evidence_index)
                evidence_count += 1
            ranked.append(
                (rank, source_index, EvidenceFact(label=label, value=rendered))
            )
    ranked.sort(key=lambda item: (item[0], item[1]))
    return [item[2] for item in ranked], evidence_count


def _matching_groups(groups: tuple[tuple[str, ...], ...], label: str) -> int | None:
    for index, tokens in enumerate(groups):
        if any(token in label for token in tokens):
            return index
    return None


def _is_excluded_field(label: str) -> bool:
    return any(token in label for token in IDENTITY_FIELD_TOKENS + INTERNAL_FIELD_TOKENS)


def _render_value(label: str, value: object) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, bool):
        return "是" if value else "否"
    if isinstance(value, (int, float)):
        if any(token in label.lower() for token in MONEY_FIELD_TOKENS):
            return _format_amount(float(value))
        if any(token in label.lower() for token in PERCENT_FIELD_TOKENS):
            percentage = float(value) * 100 if abs(float(value)) <= 1 else float(value)
            return f"{percentage:.2f}%"
        return f"{value:g}"
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return ""
        if _looks_like_date(stripped):
            return _format_date(stripped)
        return _clean_text(stripped, 180)
    if isinstance(value, list):
        return _clean_text("、".join(str(item) for item in value[:3]), 180)
    if isinstance(value, Mapping):
        pairs = [f"{key}:{item}" for key, item in list(value.items())[:3]]
        return _clean_text("；".join(pairs), 180)
    return ""


def _format_amount(value: float) -> str:
    absolute = abs(value)
    if absolute >= 100_000_000:
        return f"{value / 100_000_000:.2f} 亿"
    if absolute >= 10_000:
        return f"{value / 10_000:.2f} 万"
    return f"{value:g} 元"


def _looks_like_date(value: str) -> bool:
    return len(value) == 8 and value.isdigit() and value.startswith(("19", "20"))


def _format_date(value: str) -> str:
    try:
        return datetime.strptime(value, "%Y%m%d").strftime("%Y-%m-%d")
    except ValueError:
        return value


def _clean_text(value: str, limit: int) -> str:
    cleaned = "".join(character if character.isprintable() else " " for character in value)
    return " ".join(cleaned.split())[:limit]
