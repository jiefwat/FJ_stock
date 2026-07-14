from __future__ import annotations

import io
import json
import urllib.error

import pytest

from stock_ts import iwencai
from stock_ts.iwencai import (
    IwencaiConfigurationError,
    IwencaiGatewayError,
    IwencaiSkillClient,
    build_stock_research_response,
    iwencai_config_summary,
    route_stock_research_skill,
)


class FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self, _limit: int = -1) -> bytes:
        return json.dumps(self.payload, ensure_ascii=False).encode("utf-8")


class RawResponse:
    def __init__(self, body: bytes) -> None:
        self.body = body

    def __enter__(self) -> RawResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self, _limit: int = -1) -> bytes:
        return self.body


def test_trusted_ssl_context_uses_certifi_ca_bundle(monkeypatch) -> None:
    captured: dict[str, object] = {}
    expected_context = object()

    monkeypatch.setattr(iwencai.certifi, "where", lambda: "/trusted/cacert.pem")

    def create_default_context(*, cafile: str) -> object:
        captured["cafile"] = cafile
        return expected_context

    monkeypatch.setattr(iwencai.ssl, "create_default_context", create_default_context)

    context = iwencai._trusted_ssl_context()

    assert context is expected_context
    assert captured["cafile"] == "/trusted/cacert.pem"


def test_default_transport_passes_trusted_ssl_context(monkeypatch) -> None:
    captured: dict[str, object] = {}
    expected_context = object()

    monkeypatch.setattr(iwencai, "_trusted_ssl_context", lambda: expected_context)

    def urlopen(request: object, *, timeout: float, context: object) -> FakeResponse:
        captured.update(request=request, timeout=timeout, context=context)
        return FakeResponse({"datas": [{"股票简称": "贵州茅台"}], "code_count": 1})

    monkeypatch.setattr(iwencai.urllib.request, "urlopen", urlopen)
    client = IwencaiSkillClient(
        api_key="iwc-secret-value",
        timeout=9,
        trace_id_factory=lambda: "a" * 64,
    )

    result = client.query(route_stock_research_skill("净利润"), "贵州茅台 净利润")

    assert captured["timeout"] == 9
    assert captured["context"] is expected_context
    assert result["datas"][0]["股票简称"] == "贵州茅台"


@pytest.mark.parametrize(
    ("question", "skill_id"),
    [
        ("未来两年盈利预期和券商评级如何", "hithink-insresearch-query"),
        ("现金流和净利润质量怎么样", "hithink-finance-query"),
        ("行业估值处于什么位置", "hithink-industry-query"),
        ("最近有没有解禁、质押或监管函", "hithink-event-query"),
        ("主营业务和主要客户是什么", "hithink-business-query"),
        ("股东户数和实控人是否变化", "hithink-management-query"),
        ("主力资金和技术指标怎么样", "hithink-market-query"),
        ("最近的公司公告有哪些", "announcement-search"),
        ("最近机构研报的核心观点", "report-search"),
        ("近期有哪些重要新闻", "news-search"),
    ],
)
def test_route_stock_research_skill(question: str, skill_id: str) -> None:
    assert route_stock_research_skill(question).skill_id == skill_id


def test_unknown_question_defaults_to_finance_research() -> None:
    skill = route_stock_research_skill("这家公司值得继续研究吗")

    assert skill.skill_id == "hithink-finance-query"
    assert skill.label == "财务质量"


def test_config_summary_never_exposes_api_key() -> None:
    summary = iwencai_config_summary({"IWENCAI_API_KEY": "iwc-secret-value"})

    assert summary == {"status": "configured", "provider": "同花顺问财"}
    assert "iwc-secret-value" not in str(summary)


def test_client_builds_official_gateway_request_without_leaking_key() -> None:
    captured: dict[str, object] = {}

    def transport(request: object, timeout: float) -> FakeResponse:
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeResponse(
            {
                "datas": [{"股票简称": "贵州茅台", "净利润": "862.3亿"}],
                "code_count": 1,
                "chunks_info": {"query": "贵州茅台 净利润"},
            }
        )

    client = IwencaiSkillClient(
        api_key="iwc-secret-value",
        transport=transport,
        timeout=7,
        trace_id_factory=lambda: "a" * 64,
    )
    skill = route_stock_research_skill("净利润质量怎么样")

    result = client.query(skill, "贵州茅台 600519 净利润质量怎么样")

    request = captured["request"]
    assert request.full_url == "https://openapi.iwencai.com/v1/query2data"
    assert request.method == "POST"
    assert request.headers["Authorization"] == "Bearer iwc-secret-value"
    assert request.headers["X-claw-skill-id"] == "hithink-finance-query"
    assert request.headers["X-claw-skill-version"] == "1.0.0"
    assert request.headers["X-claw-trace-id"] == "a" * 64
    assert json.loads(request.data)["query"] == "贵州茅台 600519 净利润质量怎么样"
    assert captured["timeout"] == 7
    assert result["trace_id"] == "a" * 64
    assert result["datas"][0]["净利润"] == "862.3亿"
    assert "iwc-secret-value" not in str(result)


def test_client_requires_server_side_api_key() -> None:
    client = IwencaiSkillClient(api_key="")

    with pytest.raises(IwencaiConfigurationError, match="IWENCAI_API_KEY"):
        client.query(route_stock_research_skill("净利润"), "贵州茅台 净利润")


def test_search_skills_use_comprehensive_search_contract() -> None:
    captured: dict[str, object] = {}

    def transport(request: object, timeout: float) -> FakeResponse:
        captured["request"] = request
        return FakeResponse(
            {
                "status_code": 0,
                "data": [{"title": "年度报告", "publish_time": 1770000000}],
            }
        )

    client = IwencaiSkillClient(
        api_key="iwc-secret-value",
        transport=transport,
        trace_id_factory=lambda: "d" * 64,
    )
    skill = route_stock_research_skill("最近公司公告")

    result = client.query(skill, "贵州茅台 600519 最近公司公告")

    request = captured["request"]
    assert request.full_url == "https://openapi.iwencai.com/v1/comprehensive/search"
    assert request.headers["X-claw-skill-version"] == "1.0.0"
    assert json.loads(request.data) == {
        "query": "贵州茅台 600519 最近公司公告",
        "channels": ["announcement"],
        "app_id": "AIME_SKILL",
        "size": 10,
    }
    assert result["data"][0]["title"] == "年度报告"


def test_gateway_error_redacts_api_key_from_response_detail() -> None:
    secret = "iwc-error-secret"

    def transport(_request: object, timeout: float) -> FakeResponse:
        raise urllib.error.HTTPError(
            "https://openapi.iwencai.com/v1/query2data",
            401,
            "Unauthorized",
            {},
            io.BytesIO(f'{{"message":"invalid {secret}"}}'.encode()),
        )

    client = IwencaiSkillClient(api_key=secret, transport=transport)

    with pytest.raises(IwencaiGatewayError) as caught:
        client.query(route_stock_research_skill("净利润"), "贵州茅台 净利润")

    assert secret not in str(caught.value)
    assert "[redacted]" in str(caught.value)


@pytest.mark.parametrize(
    ("failure", "message"),
    [
        (urllib.error.URLError("network down"), "连接失败"),
        (TimeoutError("slow gateway"), "请求超时"),
    ],
)
def test_client_converts_network_failures_to_safe_gateway_errors(
    failure: Exception,
    message: str,
) -> None:
    def transport(_request: object, timeout: float) -> FakeResponse:
        raise failure

    client = IwencaiSkillClient(api_key="iwc-secret", transport=transport)

    with pytest.raises(IwencaiGatewayError, match=message):
        client.query(route_stock_research_skill("净利润"), "贵州茅台 净利润")


def test_network_failure_redacts_api_key_from_reason() -> None:
    secret = "iwc-network-secret"

    def transport(_request: object, timeout: float) -> FakeResponse:
        raise urllib.error.URLError(f"connection rejected for {secret}")

    client = IwencaiSkillClient(api_key=secret, transport=transport)

    with pytest.raises(IwencaiGatewayError) as caught:
        client.query(route_stock_research_skill("净利润"), "贵州茅台 净利润")

    assert secret not in str(caught.value)


def test_client_rejects_response_over_one_megabyte() -> None:
    client = IwencaiSkillClient(
        api_key="iwc-secret",
        transport=lambda _request, timeout: RawResponse(b"x" * (1024 * 1024 + 1)),
    )

    with pytest.raises(IwencaiGatewayError, match="安全大小限制"):
        client.query(route_stock_research_skill("净利润"), "贵州茅台 净利润")


def test_client_rejects_http_200_gateway_business_error_without_leaking_key() -> None:
    secret = "iwc-business-secret"
    client = IwencaiSkillClient(
        api_key=secret,
        transport=lambda _request, timeout: FakeResponse(
            {"status_code": 429, "message": f"quota exceeded for {secret}"}
        ),
    )

    with pytest.raises(IwencaiGatewayError) as caught:
        client.query(route_stock_research_skill("最近新闻"), "贵州茅台 最近新闻")

    assert secret not in str(caught.value)
    assert "quota exceeded" in str(caught.value)


def test_client_accepts_float_zero_gateway_success_status() -> None:
    client = IwencaiSkillClient(
        api_key="iwc-secret",
        transport=lambda _request, timeout: FakeResponse(
            {
                "status_code": 0.0,
                "status_msg": "ok",
                "datas": [{"股票简称": "贵州茅台"}],
            }
        ),
    )

    result = client.query(route_stock_research_skill("净利润"), "贵州茅台 净利润")

    assert result["status_code"] == 0.0
    assert result["datas"][0]["股票简称"] == "贵州茅台"


def test_business_status_field_cannot_echo_api_key() -> None:
    secret = "iwc-status-secret"
    client = IwencaiSkillClient(
        api_key=secret,
        transport=lambda _request, timeout: FakeResponse(
            {"status_code": secret, "message": "denied"}
        ),
    )

    with pytest.raises(IwencaiGatewayError) as caught:
        client.query(route_stock_research_skill("最近新闻"), "贵州茅台 最近新闻")

    assert secret not in str(caught.value)
    assert "[redacted]" in str(caught.value)


def test_client_redacts_api_key_echoed_inside_success_payload() -> None:
    secret = "iwc-success-secret"
    client = IwencaiSkillClient(
        api_key=secret,
        transport=lambda _request, timeout: FakeResponse(
            {
                "datas": [
                    {
                        "股票简称": "贵州茅台",
                        "debug": f"Authorization: Bearer {secret}",
                        secret: "echoed in key",
                        "[redacted]": "existing redacted key",
                    }
                ],
                "code_count": 1,
            }
        ),
    )

    result = client.query(route_stock_research_skill("净利润"), "贵州茅台 净利润")

    assert secret not in json.dumps(result, ensure_ascii=False)
    assert "[redacted]" in result["datas"][0]["debug"]
    assert len(result["datas"][0]) == 4


def test_research_response_limits_rows_and_fields_and_keeps_audit_metadata() -> None:
    raw = {
        "datas": [
            {
                "股票代码": f"60051{index}.SH",
                "股票简称": f"样例{index}",
                "净利润": f"{index}亿",
                "营业收入": f"{index * 10}亿",
                "ROE": f"{index}%",
                "资产负债率": f"{index + 20}%",
                "多余字段": "不展示",
            }
            for index in range(8)
        ],
        "code_count": 8,
        "trace_id": "b" * 64,
    }
    skill = route_stock_research_skill("净利润和ROE怎么样")

    response = build_stock_research_response(
        raw,
        skill=skill,
        question="净利润和ROE怎么样",
        query="贵州茅台 600519 净利润和ROE怎么样",
        local_as_of="2026-07-13",
        queried_at="2026-07-14T10:30:00+08:00",
    )

    assert response["ok"] is True
    assert response["skill"]["id"] == "hithink-finance-query"
    assert len(response["facts"]) == 5
    assert all(len(item) <= 6 for item in response["facts"])
    assert response["source"]["name"] == "同花顺问财"
    assert response["source"]["trace"] == "bbbbbbbb"
    assert response["local_context"] == "StockTs 本地档案日期 2026-07-13"
    assert "不构成投资建议" in response["boundary"]


def test_research_response_marks_empty_gateway_result() -> None:
    skill = route_stock_research_skill("机构预期")

    response = build_stock_research_response(
        {"datas": [], "code_count": 0, "trace_id": "c" * 64},
        skill=skill,
        question="机构预期",
        query="贵州茅台 600519 机构预期",
        local_as_of="2026-07-13",
        queried_at="2026-07-14T10:30:00+08:00",
    )

    assert response["ok"] is False
    assert response["status"] == "empty"
    assert response["facts"] == []
    assert "未返回" in response["summary"]


def test_research_response_accepts_comprehensive_search_data_shape() -> None:
    skill = route_stock_research_skill("最近公司公告")

    response = build_stock_research_response(
        {
            "status_code": 0,
            "data": [
                {
                    "title": "2026 年半年度报告",
                    "summary": "披露经营情况",
                    "publish_time": 1770000000,
                    "url": "https://example.com/report",
                }
            ],
            "trace_id": "e" * 64,
        },
        skill=skill,
        question="最近公司公告",
        query="贵州茅台 600519 最近公司公告",
        local_as_of="2026-07-13",
        queried_at="2026-07-14T10:30:00+08:00",
    )

    assert response["ok"] is True
    assert response["facts"][0]["title"] == "2026 年半年度报告"
    assert response["source"]["trace"] == "eeeeeeee"
