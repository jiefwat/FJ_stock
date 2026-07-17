from __future__ import annotations

import json
import os
import secrets
import ssl
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import certifi

IWENCAI_BASE_URL = "https://openapi.iwencai.com"
IWENCAI_SOURCE_URL = "https://www.iwencai.com/unifiedwap/chat"
MAX_RESPONSE_BYTES = 1024 * 1024


def _trusted_ssl_context() -> ssl.SSLContext:
    return ssl.create_default_context(cafile=certifi.where())


def _default_transport(request: object, timeout: float) -> object:
    return urllib.request.urlopen(
        request,
        timeout=timeout,
        context=_trusted_ssl_context(),
    )


class IwencaiError(RuntimeError):
    pass


class IwencaiConfigurationError(IwencaiError):
    pass


class IwencaiGatewayError(IwencaiError):
    pass


@dataclass(frozen=True)
class IwencaiSkill:
    skill_id: str
    label: str
    version: str = "1.0.0"
    endpoint: str = "/v1/query2data"
    channel: str = ""


SKILLS = {
    "basicinfo": IwencaiSkill("hithink-basicinfo-query", "公司身份"),
    "finance": IwencaiSkill("hithink-finance-query", "财务质量"),
    "consensus": IwencaiSkill("hithink-insresearch-query", "机构预期"),
    "industry": IwencaiSkill("hithink-industry-query", "行业位置"),
    "event": IwencaiSkill("hithink-event-query", "事件风险"),
    "business": IwencaiSkill("hithink-business-query", "经营结构"),
    "management": IwencaiSkill("hithink-management-query", "股东治理"),
    "market": IwencaiSkill("hithink-market-query", "行情资金"),
    "announcement": IwencaiSkill(
        "announcement-search",
        "公告核查",
        endpoint="/v1/comprehensive/search",
        channel="announcement",
    ),
    "report": IwencaiSkill(
        "report-search",
        "研报观点",
        endpoint="/v1/comprehensive/search",
        channel="report",
    ),
    "news": IwencaiSkill(
        "news-search",
        "新闻催化",
        endpoint="/v1/comprehensive/search",
        channel="news",
    ),
    "index": IwencaiSkill("hithink-zhishu-query", "指数结构"),
    "macro": IwencaiSkill("hithink-macro-query", "宏观变量"),
    "sector_selector": IwencaiSkill("hithink-sector-selector", "板块筛选"),
    "astock_selector": IwencaiSkill("hithink-astock-selector", "A股筛选"),
    "breadth": IwencaiSkill("hithink-astock-selector", "市场涨跌分布"),
    "hot_stock": IwencaiSkill("hithink-astock-selector", "市场热门股票"),
}

ROUTING_RULES = (
    ("basicinfo", ("公司身份", "公司属性", "成立", "上市日期", "经营边界")),
    ("announcement", ("公告", "年报", "季报", "招股书")),
    ("report", ("研报", "目标价", "研究报告")),
    ("news", ("新闻", "消息", "舆情", "媒体")),
    ("event", ("解禁", "质押", "监管函", "调研", "业绩预告", "增发", "事件")),
    ("management", ("股东", "股本", "实控人", "持有人", "治理")),
    ("business", ("主营", "客户", "供应商", "合同", "参控股", "业务")),
    ("consensus", ("预期", "评级", "预测", "券商", "一致预期", "分析师")),
    ("industry", ("行业", "板块排名", "同行", "行业估值")),
    ("market", ("资金流", "主力资金", "技术指标", "成交量", "行情", "价格")),
    (
        "finance",
        ("财务", "利润", "营收", "收入", "现金流", "roe", "毛利率", "负债", "估值"),
    ),
)

MODULE_ROUTING_RULES = {
    "market": (
        (
            ("news", ("新闻", "风险", "舆情", "消息")),
            ("macro", ("宏观", "政策", "利率", "通胀", "汇率", "经济")),
            ("sector_selector", ("板块", "行业", "主线", "方向", "筛选")),
            ("index", ("指数", "上证", "沪深", "创业板", "科创")),
        ),
        "index",
    ),
    "portfolio": (
        (
            ("announcement", ("公告", "年报", "季报")),
            ("report", ("研报", "目标价", "研究报告")),
            ("event", ("业绩风险", "事件", "解禁", "质押", "监管", "预告")),
            ("consensus", ("机构", "预期", "评级", "预测", "下修")),
            ("market", ("资金", "行情", "技术", "成交", "异动")),
            ("finance", ("财务", "利润", "营收", "现金流", "roe", "负债")),
        ),
        "event",
    ),
    "opportunity": (
        (
            ("astock_selector", ("a股", "选股", "股票筛选", "筛选股票")),
            ("sector_selector", ("板块", "行业", "主线", "持续性", "方向")),
            ("event", ("事件", "催化", "预告", "解禁", "质押", "监管")),
            ("news", ("新闻", "消息", "舆情", "风险排除")),
        ),
        "sector_selector",
    ),
}


def route_stock_research_skill(question: str) -> IwencaiSkill:
    normalized = question.strip().lower()
    for skill_key, keywords in ROUTING_RULES:
        if any(keyword in normalized for keyword in keywords):
            return SKILLS[skill_key]
    return SKILLS["finance"]


def route_module_research_skill(module: str, question: str) -> IwencaiSkill:
    normalized_module = module.strip().lower()
    if normalized_module == "stock":
        return route_stock_research_skill(question)
    if normalized_module not in MODULE_ROUTING_RULES:
        raise ValueError("不支持的研究模块。")
    rules, fallback = MODULE_ROUTING_RULES[normalized_module]
    normalized_question = question.strip().lower()
    for skill_key, keywords in rules:
        if any(keyword in normalized_question for keyword in keywords):
            return SKILLS[skill_key]
    return SKILLS[fallback]


def build_module_research_query(
    module: str,
    question: str,
    *,
    code: str = "",
    name: str = "",
    sector: str = "",
) -> str:
    normalized_module = module.strip().lower()
    if normalized_module not in {"market", "portfolio", "stock", "opportunity"}:
        raise ValueError("不支持的研究模块。")
    cleaned_question = _clean_query_part(question, 200)
    if normalized_module == "market":
        values = (cleaned_question,)
    elif normalized_module == "opportunity":
        values = (
            _clean_query_part(sector, 64),
            _clean_query_part(name, 64),
            _clean_query_part(code, 32),
            cleaned_question,
        )
    else:
        values = (
            _clean_query_part(name, 64),
            _clean_query_part(code, 32),
            cleaned_question,
        )
    return " ".join(value for value in values if value)


def iwencai_config_summary(env: Mapping[str, str] | None = None) -> dict[str, str]:
    values = os.environ if env is None else env
    return {
        "status": "configured" if values.get("IWENCAI_API_KEY", "").strip() else "missing",
        "provider": "同花顺问财",
    }


class IwencaiSkillClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str = IWENCAI_BASE_URL,
        timeout: float = 12,
        transport: Callable[..., Any] | None = None,
        trace_id_factory: Callable[[], str] | None = None,
    ) -> None:
        parsed = urlparse(base_url)
        if parsed.scheme != "https" or parsed.netloc != "openapi.iwencai.com":
            raise ValueError("问财 OpenAPI 地址必须使用官方 HTTPS 域名")
        self.api_key = (
            api_key if api_key is not None else os.getenv("IWENCAI_API_KEY", "")
        ).strip()
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.transport = transport or _default_transport
        self.trace_id_factory = trace_id_factory or (lambda: secrets.token_hex(32))

    def query(self, skill: IwencaiSkill, query: str) -> dict[str, Any]:
        if not self.api_key:
            raise IwencaiConfigurationError(
                "服务器未配置 IWENCAI_API_KEY，请先在问财 SkillHub 获取并写入服务器环境变量。"
            )
        trace_id = self.trace_id_factory()
        if len(trace_id) != 64:
            raise ValueError("问财 trace id 必须是 64 个字符")
        payload = self._build_payload(skill, query)
        request = urllib.request.Request(
            f"{self.base_url}{skill.endpoint}",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "X-Claw-Call-Type": "normal",
                "X-Claw-Skill-Id": skill.skill_id,
                "X-Claw-Skill-Version": skill.version,
                "X-Claw-Plugin-Id": "none",
                "X-Claw-Plugin-Version": "none",
                "X-Claw-Trace-Id": trace_id,
            },
            method="POST",
        )
        try:
            with self.transport(request, timeout=self.timeout) as response:
                body = response.read(MAX_RESPONSE_BYTES + 1)
        except urllib.error.HTTPError as exc:
            detail = _safe_error_detail(
                exc.read(512).decode("utf-8", errors="replace"),
                secret=self.api_key,
            )
            raise IwencaiGatewayError(f"问财网关返回 HTTP {exc.code}：{detail}") from exc
        except urllib.error.URLError as exc:
            reason = _safe_error_detail(str(exc.reason), secret=self.api_key)
            raise IwencaiGatewayError(f"问财连接失败：{reason}") from exc
        except TimeoutError as exc:
            raise IwencaiGatewayError("问财请求超时，请稍后重试。") from exc
        if len(body) > MAX_RESPONSE_BYTES:
            raise IwencaiGatewayError("问财响应超过安全大小限制。")
        try:
            result = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise IwencaiGatewayError("问财返回了无法解析的数据。") from exc
        if not isinstance(result, dict):
            raise IwencaiGatewayError("问财返回格式不符合预期。")
        business_status = result.get("status_code", result.get("code"))
        if business_status is not None and not _is_success_business_status(business_status):
            detail = result.get("message", result.get("error", "网关业务错误"))
            safe_detail = _safe_error_detail(str(detail), secret=self.api_key)
            safe_status = _safe_error_detail(str(business_status), secret=self.api_key)
            raise IwencaiGatewayError(f"问财网关业务错误 {safe_status}：{safe_detail}")
        result = _redact_secret(result, self.api_key)
        result["trace_id"] = trace_id
        return result

    @staticmethod
    def _build_payload(skill: IwencaiSkill, query: str) -> dict[str, Any]:
        if skill.channel:
            return {
                "query": query,
                "channels": [skill.channel],
                "app_id": "AIME_SKILL",
                "size": 10,
            }
        return {
            "query": query,
            "page": "1",
            "limit": "10",
            "is_cache": "1",
            "expand_index": "true",
        }


def build_stock_research_response(
    raw: Mapping[str, Any],
    *,
    skill: IwencaiSkill,
    question: str,
    query: str,
    local_as_of: str,
    queried_at: str,
) -> dict[str, Any]:
    raw_rows = raw.get("datas")
    if not isinstance(raw_rows, list):
        raw_rows = raw.get("data")
    rows = raw_rows if isinstance(raw_rows, list) else []
    facts = [_compact_row(item) for item in rows[:5] if isinstance(item, Mapping)]
    facts = [item for item in facts if item]
    trace_id = str(raw.get("trace_id") or "")
    code_count = _safe_int(raw.get("code_count"), len(rows))
    is_empty = not facts
    return {
        "ok": not is_empty,
        "status": "empty" if is_empty else "complete",
        "question": question,
        "query": query,
        "skill": {"id": skill.skill_id, "label": skill.label, "version": skill.version},
        "summary": (
            "问财未返回可展示的数据，请简化问题或稍后重试。"
            if is_empty
            else f"问财返回 {code_count} 条匹配记录，当前展示前 {len(facts)} 条结构化事实。"
        ),
        "facts": facts,
        "relationship": "外部事实用于交叉验证，不会自动改写上方 StockTs 结论或仓位边界。",
        "unknowns": [
            "动态字段口径由问财查询解析决定，重要结论需复核公告或研报原文。",
            "若外部数据与本地档案日期不同，先按数据新鲜度和原始来源核对。",
        ],
        "source": {
            "name": "同花顺问财",
            "url": IWENCAI_SOURCE_URL,
            "queried_at": queried_at,
            "trace": trace_id[-8:] if trace_id else "",
        },
        "local_context": f"StockTs 本地档案日期 {local_as_of or '缺失'}",
        "boundary": "仅供研究参考，不构成投资建议；不自动交易。",
    }


def build_module_research_response(
    raw: Mapping[str, Any],
    *,
    module: str,
    skill: IwencaiSkill,
    question: str,
    query: str,
    context_label: str,
    local_as_of: str,
    queried_at: str,
) -> dict[str, Any]:
    result = build_stock_research_response(
        raw,
        skill=skill,
        question=question,
        query=query,
        local_as_of=local_as_of,
        queried_at=queried_at,
    )
    result.update(
        {
            "module": module,
            "context_label": context_label,
            "relationship": (
                "外部事实仅用于交叉验证，不自动改写 StockTs 本地结论、风险闸门、"
                "持仓动作或候选排序。"
            ),
            "local_context": f"StockTs 本地数据日期 {local_as_of or '缺失'}",
        }
    )
    return result


def _compact_row(row: Mapping[str, Any]) -> dict[str, str]:
    preferred = ("股票简称", "股票代码", "证券简称", "证券代码", "名称", "代码")
    keys = [key for key in preferred if key in row]
    keys.extend(str(key) for key in row if str(key) not in keys)
    result: dict[str, str] = {}
    for key in keys:
        if len(result) >= 6:
            break
        value = row.get(key)
        if value is None or value == "":
            continue
        result[key[:40]] = _display_value(value)
    return result


def _clean_query_part(value: str, limit: int) -> str:
    cleaned = "".join(character if character.isprintable() else " " for character in value)
    return " ".join(cleaned.split())[:limit]


def _display_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    else:
        text = str(value)
    return text.replace("\x00", "").strip()[:240]


def _safe_int(value: Any, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _is_success_business_status(value: Any) -> bool:
    try:
        return float(str(value).strip()) in {0.0, 200.0}
    except (TypeError, ValueError):
        return False


def _safe_error_detail(detail: str, *, secret: str = "") -> str:
    cleaned = " ".join(detail.replace("\x00", "").split())
    if secret:
        cleaned = cleaned.replace(secret, "[redacted]")
    return cleaned[:240] or "无错误详情"


def _redact_secret(value: Any, secret: str) -> Any:
    if not secret:
        return value
    if isinstance(value, str):
        return value.replace(secret, "[redacted]")
    if isinstance(value, list):
        return [_redact_secret(item, secret) for item in value]
    if isinstance(value, dict):
        redacted: dict[Any, Any] = {}
        for key, item in value.items():
            safe_key = key.replace(secret, "[redacted]") if isinstance(key, str) else key
            base_key = safe_key
            suffix = 2
            while safe_key in redacted:
                safe_key = f"{base_key}#{suffix}"
                suffix += 1
            redacted[safe_key] = _redact_secret(item, secret)
        return redacted
    return value
