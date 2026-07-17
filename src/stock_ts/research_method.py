from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, replace
from typing import Any

RESEARCH_CONTRACT_VERSION = "2026-07-17.multi-lens.v1"

_EVIDENCE_ALIASES = {
    "财务质量": ("finance",),
    "经营结构": ("business",),
    "机构预期": ("consensus",),
    "事件风险": ("event",),
    "行情资金": ("market",),
    "行业位置": ("industry",),
    "公告事项": ("announcement",),
    "研报观点": ("report",),
    "技术趋势": ("market",),
    "量价结构": ("market",),
    "资金行为": ("market",),
    "估值基本面": ("finance",),
    "消息事件": ("event", "announcement", "news"),
}


@dataclass(frozen=True)
class ResearchMethodDimension:
    key: str
    title: str
    evidence_keys: tuple[str, ...]
    analysis_task: str
    comparison_basis: str
    recovery: str
    required_all: tuple[str, ...] = ()
    required_any: tuple[str, ...] = ()


@dataclass(frozen=True)
class ResearchMethod:
    module: str
    title: str
    dimensions: tuple[ResearchMethodDimension, ...]
    required_outputs: tuple[str, ...]


def _dimension(
    key: str,
    title: str,
    evidence_keys: tuple[str, ...],
    analysis_task: str,
    comparison_basis: str,
    recovery: str,
    *,
    required_all: tuple[str, ...] = (),
    required_any: tuple[str, ...] = (),
) -> ResearchMethodDimension:
    return ResearchMethodDimension(
        key=key,
        title=title,
        evidence_keys=evidence_keys,
        analysis_task=analysis_task,
        comparison_basis=comparison_basis,
        recovery=recovery,
        required_all=required_all,
        required_any=required_any,
    )


RESEARCH_METHODS = {
    "market": ResearchMethod(
        module="market",
        title="市场事实与状态识别",
        dimensions=(
            _dimension(
                "macro",
                "宏观与政策",
                ("macro",),
                "识别风险偏好变量及其变化方向。",
                "最新值、前值与政策预期",
                "宏观数据和政策日期",
            ),
            _dimension(
                "index",
                "指数趋势",
                ("index", "market-index"),
                "比较主要指数短中期趋势与波动。",
                "当日、5日、20日和60日",
                "主要指数多周期行情",
            ),
            _dimension(
                "breadth",
                "市场宽度",
                ("breadth", "market-breadth", "market-pulse"),
                "判断上涨是否扩散到足够多股票。",
                "上涨占比、涨跌比与近20日分位",
                "全市场涨跌家数",
            ),
            _dimension(
                "liquidity",
                "成交与流动性",
                ("breadth", "market-pulse", "hot_stock"),
                "识别增量成交、缩量和流动性压力。",
                "当日成交与5/20日均值",
                "全市场成交额和换手",
            ),
            _dimension(
                "style",
                "市场风格",
                ("index", "sector_selector", "market-themes"),
                "区分大小盘、价值成长与周期防御。",
                "风格指数相对收益",
                "风格指数或代表行业",
            ),
            _dimension(
                "rotation",
                "行业轮动",
                ("sector_selector", "market-themes"),
                "验证主线的强度、扩散和持续时间。",
                "1/5/20日行业相对强度",
                "行业热度、宽度和持续性",
            ),
            _dimension(
                "sentiment",
                "情绪与拥挤",
                ("news", "hot_stock", "market-movers"),
                "识别涨跌停压力、极端波动和拥挤。",
                "涨跌停、异动数量与历史分位",
                "情绪和异动数据",
            ),
            _dimension(
                "calendar",
                "事件日历",
                ("news", "macro"),
                "标记未来一周可能改变风险偏好的事件。",
                "当前状态与事件发生时间",
                "宏观、政策和市场事件日期",
            ),
        ),
        required_outputs=("市场阶段", "主要驱动", "核心矛盾", "风险状态"),
    ),
    "portfolio": ResearchMethod(
        module="portfolio",
        title="组合相对风险与处理顺序",
        dimensions=(
            _dimension(
                "thesis",
                "持仓论点",
                ("finance", "business", "portfolio-holdings"),
                "检查原始持仓理由是否仍成立。",
                "建仓假设与最新事实",
                "持仓研究假设和关键事实",
            ),
            _dimension(
                "earnings",
                "盈利与预期",
                ("finance", "consensus", "event"),
                "识别盈利趋势和机构预期变化。",
                "历史实际值与最新预测",
                "财务、预期和业绩事件",
            ),
            _dimension(
                "price",
                "价格与资金",
                ("market", "portfolio-holdings"),
                "识别趋势、资金和波动恶化。",
                "5/20/60日和持仓成本",
                "多周期行情和资金",
            ),
            _dimension(
                "concentration",
                "行业集中",
                ("industry", "portfolio-themes"),
                "识别行业与主题集中风险。",
                "组合权重与风险上限",
                "行业和主题暴露",
            ),
            _dimension(
                "correlation",
                "共同风险",
                ("portfolio-themes", "industry"),
                "识别持仓之间的共同驱动。",
                "行业、主题和价格相关性",
                "持仓相关性或共同主题",
            ),
            _dimension(
                "drawdown",
                "回撤贡献",
                ("market", "portfolio-holdings"),
                "排序单股对组合回撤的贡献。",
                "个股回撤与组合回撤",
                "持仓市值和多周期回撤",
            ),
            _dimension(
                "catalyst",
                "事件与催化",
                ("event", "announcement", "consensus"),
                "标记需要优先处理的事件窗口。",
                "事件前后论点变化",
                "公告、预告和复核日期",
            ),
            _dimension(
                "market_fit",
                "市场适配",
                ("market", "industry", "portfolio-themes"),
                "判断持仓与当前市场风格是否匹配。",
                "个股相对行业和指数",
                "市场状态与行业相对表现",
            ),
        ),
        required_outputs=("处理顺序", "继续持有条件", "减风险条件", "禁止动作", "复核事件"),
    ),
    "stock": ResearchMethod(
        module="stock",
        title="公司研究备忘录",
        dimensions=(
            _dimension(
                "identity",
                "公司身份",
                ("basicinfo",),
                "确认公司边界、上市时间和主体属性。",
                "公司自身历史与可比主体",
                "公司基本资料",
            ),
            _dimension(
                "business",
                "商业模式",
                ("business",),
                "拆解收入来源、客户供应商和竞争优势。",
                "业务结构变化与主要同行",
                "主营、客户、供应商和合同",
            ),
            _dimension(
                "earnings",
                "盈利趋势",
                ("finance",),
                "比较收入、利润、毛利率和ROE趋势。",
                "三年与四季度同比环比",
                "多期利润表指标",
            ),
            _dimension(
                "cashflow",
                "现金流质量",
                ("finance",),
                "检查利润与经营现金流是否匹配。",
                "现金利润比与资本开支趋势",
                "现金流和资产负债表",
            ),
            _dimension(
                "valuation",
                "估值匹配",
                ("finance", "industry"),
                "比较估值、盈利增速和质量。",
                "历史分位与同行分位",
                "估值和同行数据",
            ),
            _dimension(
                "industry",
                "行业位置",
                ("industry", "business"),
                "判断行业景气、排名和竞争位置。",
                "行业、同行和产业链",
                "行业盈利、行情和排名",
            ),
            _dimension(
                "consensus",
                "机构预期",
                ("consensus", "report"),
                "识别盈利修正、评级变化和观点分歧。",
                "近三个月预测变化",
                "一致预期、评级和研报",
            ),
            _dimension(
                "governance",
                "股东治理",
                ("management", "event"),
                "核查股东户数、质押和实控人变化。",
                "最近一期与历史变化",
                "股东股本和治理事件",
            ),
            _dimension(
                "price",
                "资金与技术",
                ("market",),
                "验证价格、成交和资金是否确认研究假设。",
                "5/20/60日和行业相对收益",
                "多周期行情、资金和波动",
            ),
            _dimension(
                "catalyst",
                "公告与催化",
                ("event", "announcement", "news", "report"),
                "识别催化、负面事件和复核日期。",
                "事件发生前后事实",
                "公告、新闻、事件和研报",
            ),
            _dimension(
                "expectation_gap",
                "预期差与失效",
                ("finance", "consensus", "industry", "event"),
                "合成市场预期、事实变化与主要反证。",
                "市场预期与实际变化",
                "盈利修正、同行和事件反证",
            ),
        ),
        required_outputs=("研究假设", "最强支持", "最大反证", "预期差", "确认条件", "失效条件"),
    ),
    "opportunity": ResearchMethod(
        module="opportunity",
        title="条件预测与风险排除",
        dimensions=(
            _dimension(
                "theme_gate",
                "主题持续",
                ("sector_selector", "opportunity-themes"),
                "验证启动时间、强度和多日持续性。",
                "1/5/20日主题相对强度",
                "主题历史和启动日期",
                required_all=("sector_selector",),
            ),
            _dimension(
                "breadth_gate",
                "扩散宽度",
                ("sector_selector", "opportunity-themes"),
                "检查上涨是否扩散到足够多成分股。",
                "上涨占比和前排集中度",
                "板块成分涨跌分布",
            ),
            _dimension(
                "industry_gate",
                "景气与估值",
                ("sector_selector", "industry"),
                "比较行业盈利、景气和估值位置。",
                "历史与同行行业分位",
                "行业盈利和估值",
            ),
            _dimension(
                "flow_gate",
                "资金与拥挤",
                ("astock_selector", "market"),
                "区分增量资金和高位拥挤。",
                "成交、换手和资金历史分位",
                "成交和资金流",
            ),
            _dimension(
                "market_fit",
                "市场适配",
                ("sector_selector", "news"),
                "判断主题与指数风格是否同向。",
                "主题相对指数和风格",
                "指数、风格和主题收益",
            ),
            _dimension(
                "company_gate",
                "公司质量",
                ("astock_selector", "finance", "business"),
                "排除盈利和经营质量不达标的股票。",
                "候选同行和财务底线",
                "候选财务与经营事实",
                required_all=("astock_selector",),
                required_any=("finance", "business"),
            ),
            _dimension(
                "expectation_gate",
                "预期变化",
                ("event", "consensus", "news"),
                "识别可验证的预期差和催化。",
                "事件前后预期变化",
                "预期、新闻和事件",
            ),
            _dimension(
                "event_gate",
                "事件催化",
                ("event", "news"),
                "确认催化日期、来源和持续窗口。",
                "事件发生时间和价格反应",
                "公告、新闻和事件日期",
            ),
            _dimension(
                "price_gate",
                "价格确认",
                ("astock_selector", "market", "opportunity-candidates"),
                "验证趋势、量能和回撤边界。",
                "5/10/20日及最大回撤",
                "候选多周期行情",
                required_all=("astock_selector",),
                required_any=("market", "opportunity-candidates"),
            ),
            _dimension(
                "risk_gate",
                "风险排除",
                ("event", "news", "opportunity-candidates"),
                "排除事件、基本面和高位回撤风险。",
                "最大反证与失效条件",
                "风险事件和回撤数据",
                required_all=("astock_selector",),
                required_any=("event", "news"),
            ),
        ),
        required_outputs=("主题门", "公司门", "价格门", "风险门", "T+1/T+3/T+5条件"),
    ),
}


def method_for(module: str) -> ResearchMethod:
    try:
        return RESEARCH_METHODS[module.strip().lower()]
    except KeyError as exc:
        raise ValueError("不支持的研究模块。") from exc


def _dimension_status(
    dimension: ResearchMethodDimension,
    ready: set[str],
    missing: set[str],
) -> str:
    if dimension.required_all or dimension.required_any:
        required_all = set(dimension.required_all)
        required_any = set(dimension.required_any)
        all_ready = required_all <= ready
        any_ready = not required_any or bool(required_any & ready)
        if all_ready and any_ready:
            return "ready"
        if (required_all | required_any) & ready:
            return "partial"
        return "unknown"

    evidence = set(dimension.evidence_keys)
    matched_ready = evidence & ready
    matched_missing = evidence & missing
    if matched_ready and matched_missing:
        return "partial"
    if matched_ready:
        return "ready"
    return "unknown"


def _fact_direction(label: str, value: str) -> int:
    combined = f"{label} {value}"
    for resolved in ("承压缓解", "压力缓解", "下调风险解除", "下修风险解除", "风险解除"):
        combined = combined.replace(resolved, "")
    negative_terms = (
        "预亏",
        "下修",
        "下调",
        "净流出",
        "减持",
        "下降",
        "恶化",
        "亏损",
        "承压",
    )
    if any(term in combined for term in negative_terms):
        return -1

    numeric_value = re.sub(
        r"(?<=\d)%?\s*[-~—至]\s*(?=\d)",
        " ",
        value.replace(",", ""),
    )
    numbers = [
        float(number)
        for number in re.findall(r"(?<![\d.])[-+]?\d+(?:\.\d+)?", numeric_value)
    ]
    if any(number < 0 for number in numbers):
        return -1

    positive_terms = ("预增", "上调", "净流入", "增持", "改善", "修复")
    if any(term in combined for term in positive_terms):
        return 1
    directional_labels = ("增长", "涨跌", "变动", "净流", "收益")
    if numbers and any(term in label for term in directional_labels):
        if any(number > 0 for number in numbers):
            return 1
    return 0


def _evidence_direction(
    summary: str,
    facts: Iterable[tuple[str, str]],
) -> int:
    directions = [_fact_direction(label, value) for label, value in facts]
    summary_direction = _fact_direction("", summary)
    if -1 in directions or summary_direction == -1:
        return -1
    if 1 in directions or summary_direction == 1:
        return 1
    return 0


def _stock_result_context(result: Any | None) -> dict[str, Any]:
    context: dict[str, Any] = {
        "verdict": "",
        "action": "",
        "risk": "",
        "evidence": [],
        "support": "",
        "counter": "",
        "expectation": "",
        "price": "",
    }
    if result is None:
        return context

    payload = result.to_public_dict()
    context.update(
        verdict=str(payload.get("verdict") or ""),
        action=str(payload.get("action") or ""),
        risk=str(payload.get("primary_risk") or ""),
    )
    evidence: list[tuple[str, str, int]] = []
    seen: set[str] = set()

    def add_evidence(
        section: str,
        summary: str,
        facts: Iterable[dict[str, object]],
    ) -> None:
        fact_pairs = tuple(
            (str(fact.get("label")), str(fact.get("value")))
            for fact in facts
            if fact.get("label") and fact.get("value")
        )
        fact_text = "；".join(
            f"{label}：{value}" for label, value in fact_pairs
        )
        body = summary.strip()
        if fact_text and fact_text not in body:
            body = f"{body}（{fact_text}）" if body else fact_text
        text = f"{section}：{body}" if section and body else body
        if text and text not in seen:
            seen.add(text)
            evidence.append(
                (section, text, _evidence_direction(summary, fact_pairs))
            )

    for finding in payload.get("findings", []):
        add_evidence(
            str(finding.get("title") or "研究事实"),
            str(finding.get("summary") or ""),
            finding.get("facts", []),
        )
    for detail in payload.get("details", []):
        section = str(detail.get("section") or "研究事实")
        for finding in detail.get("findings", []):
            add_evidence(
                section,
                str(finding.get("summary") or ""),
                finding.get("facts", []),
            )
    for item in payload.get("module_items", []):
        add_evidence(
            str(item.get("label") or item.get("name") or "研究事实"),
            str(item.get("summary") or ""),
            item.get("facts", []),
        )

    evidence_texts = [text for _, text, _direction in evidence]
    context["evidence"] = evidence_texts
    context["support"] = next(
        (text for _section, text, direction in evidence if direction == 1),
        "",
    )
    context["counter"] = next(
        (text for _section, text, direction in evidence if direction == -1),
        context["risk"] if _fact_direction("", context["risk"]) == -1 else "",
    )
    context["expectation"] = next(
        (
            text
            for section, text, _direction in evidence
            if any(term in section for term in ("机构预期", "研报"))
        ),
        "",
    )
    context["price"] = next(
        (
            text
            for section, text, _direction in evidence
            if any(term in section for term in ("行情", "价格", "资金"))
        ),
        "",
    )
    return context


def build_method_section(
    module: str,
    *,
    ready_keys: Iterable[str] = (),
    missing_keys: Iterable[str] = (),
    result: Any | None = None,
) -> Any:
    from .research_engine import ResearchFact, ResearchModuleItem, ResearchModuleSection

    method = method_for(module)
    ready = {str(item) for item in ready_keys}
    missing = {str(item) for item in missing_keys}
    items = []
    dimension_statuses: dict[str, str] = {}
    ready_count = 0
    for dimension in method.dimensions:
        status = _dimension_status(dimension, ready, missing)
        dimension_statuses[dimension.key] = status
        label = {
            "ready": "已确认",
            "partial": "部分证据",
            "unknown": "待补数据",
        }[status]
        if status == "ready":
            ready_count += 1
        recovery = "" if status == "ready" else dimension.recovery
        risk = (
            "继续寻找反证，不能只按这一维度行动。"
            if status == "ready"
            else f"待补：{dimension.recovery}"
        )
        items.append(
            ResearchModuleItem(
                kind="method_dimension",
                key=dimension.key,
                name=dimension.title,
                label=label,
                summary=dimension.analysis_task,
                risk=risk,
                status=status,
                score={"ready": 1.0, "partial": 0.5}.get(status),
                recovery=recovery,
                facts=(
                    ResearchFact(label="证据状态", value=label),
                    ResearchFact(label="比较基准", value=dimension.comparison_basis),
                    ResearchFact(label="分析任务", value=dimension.analysis_task),
                ),
            )
        )
    if module == "stock":
        gap_titles = [
            dimension.title
            for dimension in method.dimensions
            if dimension_statuses[dimension.key] != "ready"
        ]
        gap_text = "、".join(gap_titles) or "后续事实变化"
        context = _stock_result_context(result)
        verdict = context["verdict"]
        action = context["action"]
        risk = context["risk"]
        evidence = context["evidence"]
        support = context["support"]
        counter = context["counter"]
        expectation = context["expectation"]
        price = context["price"]
        first_evidence = evidence[0] if evidence else ""
        hypothesis_status = "partial" if verdict or action else "unknown"
        support_status = "partial" if support else "unknown"
        counter_status = "partial" if counter else "unknown"
        expectation_status = "partial" if expectation else "unknown"
        confirmation_status = "partial" if action else "unknown"
        invalidation_status = "partial" if risk or price else "unknown"
        output_specs = (
            (
                "research_hypothesis",
                "研究假设",
                (
                    f"{verdict}；下一步：{action}"
                    if verdict or action
                    else "当前没有足够公开事实形成研究假设。"
                ),
                hypothesis_status,
                f"补齐{gap_text}后形成可证伪假设。",
                (("当前判断", verdict), ("下一步动作", action), ("公开证据", first_evidence)),
            ),
            (
                "strongest_support",
                "最强支持",
                support or "现有公开事实未识别出方向性支持。",
                support_status,
                "从已确认事实中提取与研究假设直接相关的支持证据。",
                (("支持证据", support),),
            ),
            (
                "counter_evidence",
                "最大反证",
                counter or f"当前未识别结构化反证；需优先核对{gap_text}。",
                counter_status,
                "核对负面事实、预期下修、治理风险和价格失效信号。",
                (("反证或风险", counter),),
            ),
            (
                "expectation_gap",
                "预期差",
                expectation or "缺少机构预期或研报事实，不推断预期差。",
                expectation_status,
                "补齐盈利预测修正、同行比较和事件后的实际变化。",
                (("预期证据", expectation),),
            ),
            (
                "confirmation_condition",
                "确认条件",
                (
                    f"按实际动作复核：{action}；价格证据：{price or '待补'}。"
                    if action
                    else "缺少实际动作，确认条件未知。"
                ),
                confirmation_status,
                "定义下一次可观察、带日期且可复核的确认条件。",
                (("实际动作", action), ("价格证据", price)),
            ),
            (
                "invalidation_condition",
                "失效条件",
                (
                    f"实际风险：{risk or '待补'}；价格证据：{price or '待补'}。"
                    if risk or price
                    else "缺少实际风险和价格事实，失效条件未知。"
                ),
                invalidation_status,
                "根据最大反证、事件变化和价格结构定义明确失效条件。",
                (("主要风险", risk), ("价格证据", price)),
            ),
        )
        items.extend(
            ResearchModuleItem(
                kind="method_output",
                key=key,
                name=name,
                label="待验证" if status == "partial" else "待补数据",
                summary=summary,
                risk=recovery,
                status=status,
                score=None,
                recovery=recovery,
                facts=tuple(
                    ResearchFact(label=label, value=value)
                    for label, value in facts
                    if value
                ),
            )
            for key, name, summary, status, recovery, facts in output_specs
        )
    return ResearchModuleSection(
        key="professional-method",
        title=method.title,
        conclusion=(
            f"已覆盖 {ready_count}/{len(method.dimensions)} 个专业维度；"
            f"最终输出必须包含{'、'.join(method.required_outputs)}。"
        ),
        tone="neutral" if ready_count else "caution",
        items=tuple(items),
    )


def attach_method_section(
    result: Any,
    *,
    ready_keys: Iterable[str] | None = None,
    missing_keys: Iterable[str] | None = None,
) -> Any:
    observed_ready = set(ready_keys or _ready_keys_from_result(result))
    observed_missing = set(missing_keys or _missing_keys_from_result(result))
    sections = tuple(
        section for section in result.module_sections if section.key != "professional-method"
    )
    return replace(
        result,
        research_contract_version=RESEARCH_CONTRACT_VERSION,
        module_sections=(
            *sections,
            build_method_section(
                result.module,
                ready_keys=observed_ready,
                missing_keys=observed_missing,
                result=result,
            ),
        ),
    )


def _evidence_aliases(value: str) -> set[str]:
    return {
        alias
        for label, aliases in _EVIDENCE_ALIASES.items()
        if label in value
        for alias in aliases
    }


def _ready_keys_from_result(result: Any) -> set[str]:
    keys: set[str] = set()
    for detail in result.details:
        if detail.status == "ready":
            keys.add(detail.section)
            keys.update(_evidence_aliases(detail.section))
    for section in result.module_sections:
        keys.update((section.key, section.title))
    for item in result.module_items:
        if item.status == "ready":
            keys.update((item.kind, item.name, item.label))
            keys.update(_evidence_aliases(f"{item.name} {item.label}"))
    return {key for key in keys if key}


def _missing_keys_from_result(result: Any) -> set[str]:
    values = [detail.section for detail in result.details if detail.status != "ready"]
    values.extend(result.missing_sections)
    values.extend(
        f"{item.name} {item.label}"
        for item in result.module_items
        if item.status != "ready"
    )
    keys = {value for value in values if value}
    for value in values:
        keys.update(_evidence_aliases(value))
    return {key for key in keys if key}
