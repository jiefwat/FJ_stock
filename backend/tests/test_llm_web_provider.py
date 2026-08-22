import json
from datetime import UTC, datetime

import httpx
import pytest

from marketdesk.config import Settings
from marketdesk.models import AskStockConversationMessage
from marketdesk.providers.base import ProviderUnavailable
from marketdesk.providers.llm_web import LLMWebAskContext, LLMWebAskProvider


def test_financial_llm_prompts_require_plain_language() -> None:
    provider = LLMWebAskProvider(
        settings=Settings(llm_web_api_key="test-key")
    )

    assert "日常中文" in provider._system_prompt()
    assert "为什么值得看" in provider._system_prompt()
    assert "不要堆砌K线" in provider._system_prompt()
    assert "紧接着解释" in provider._stream_system_prompt()
    assert "主要担心" in provider._user_prompt(
        LLMWebAskContext(question="这只股票怎么看")
    )


@pytest.mark.asyncio
async def test_financial_llm_uses_openai_chat_completions_with_local_context() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content.decode())
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "answer": "结论：等待回踩确认。",
                                    "evidence": ["本地趋势评分为 68。"],
                                    "risks": ["短线波动偏高。"],
                                    "next_actions": ["观察支撑位。"],
                                    "intent": "action",
                                },
                                ensure_ascii=False,
                            )
                        }
                    }
                ]
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = LLMWebAskProvider(
            settings=Settings(
                llm_web_api_key="test-key",
                llm_web_base_url="https://finance-model.example/v1",
                llm_web_model="finance-model",
                llm_web_api_style="chat_completions",
                llm_web_search_enabled=False,
            ),
            client=client,
        )
        result = await provider.ask_stock(
            LLMWebAskContext(
                question="结合我的持仓，现在应该怎么处理",
                conversation=(
                    AskStockConversationMessage(role="user", content="贵州茅台趋势怎么样"),
                    AskStockConversationMessage(role="assistant", content="趋势仍需确认。"),
                ),
                stock={"symbol": "SH.600519", "name": "贵州茅台", "price": 1500},
                holdings=("贵州茅台(SH.600519) 数量100 成本1450 状态holding",),
                market_notes=("上证指数 -0.50%",),
                analysis_notes=("确定性结论：偏多观察；趋势评分 68；支撑位 1460",),
            )
        )

    assert result.kind == "llm_answer"
    assert result.answer == "结论：等待回踩确认。"
    assert seen["url"] == "https://finance-model.example/v1/chat/completions"
    body = seen["body"]
    assert isinstance(body, dict)
    assert "tools" not in body
    assert "enable_search" not in body
    prompt = body["messages"][1]["content"]
    assert "确定性分析上下文" in prompt
    assert "趋势评分 68" in prompt
    assert "当前账号持仓上下文" in prompt
    assert "最近对话" in prompt


@pytest.mark.asyncio
async def test_financial_llm_streams_generic_chat_completions() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content.decode())
        return httpx.Response(
            200,
            content=(
                'data: {"choices":[{"delta":{"content":"结论：等待确认。"}}]}\n\n'
                "data: [DONE]\n\n"
            ),
            headers={"content-type": "text/event-stream"},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = LLMWebAskProvider(
            settings=Settings(
                llm_web_api_key="test-key",
                llm_web_base_url="https://finance-model.example/v1",
                llm_web_model="finance-model",
                llm_web_api_style="chat_completions",
                llm_web_search_enabled=False,
            ),
            client=client,
        )
        chunks = [
            chunk
            async for chunk in provider.stream_answer_text(
                LLMWebAskContext(question="贵州茅台怎么看")
            )
        ]

    assert chunks == ["结论：等待确认。"]
    assert seen["url"] == "https://finance-model.example/v1/chat/completions"
    body = seen["body"]
    assert isinstance(body, dict)
    assert body["stream"] is True
    assert "messages" in body
    assert "tools" not in body


@pytest.mark.asyncio
async def test_llm_web_provider_calls_responses_api_with_web_search_context() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        seen["body"] = json.loads(request.content.decode())
        return httpx.Response(
            200,
            json={
                "output_text": json.dumps(
                    {
                        "answer": "结论：先看最新公告和行业消息。",
                        "evidence": ["检索到近期公告线索。"],
                        "risks": ["信息可能滞后。"],
                        "next_actions": ["回到个股研究页复核。"],
                        "intent": "catalyst",
                        "symbol": "SH.600519",
                        "name": "贵州茅台",
                    },
                    ensure_ascii=False,
                )
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = LLMWebAskProvider(
            settings=Settings(
                llm_web_api_key="test-key",
                llm_web_base_url="https://llm.example/v1",
                llm_web_model="test-model",
                llm_web_search_enabled=True,
            ),
            client=client,
        )
        result = await provider.ask_stock(
            LLMWebAskContext(
                question="它最新有什么催化",
                conversation=(
                    AskStockConversationMessage(role="user", content="贵州茅台风险是什么"),
                    AskStockConversationMessage(role="assistant", content="估值和需求是关键。"),
                ),
                stock={"symbol": "SH.600519", "name": "贵州茅台", "price": 1500},
                observed_at=datetime.now(UTC),
                market_notes=("上证指数 -0.50%",),
            )
        )

    assert result.kind == "llm_answer"
    assert result.intent == "catalyst"
    assert result.source == "金融分析 Skill + 本地证据"
    assert result.confidence is not None
    assert result.evidence == ["核对到近期公告线索。"]
    assert seen["url"] == "https://llm.example/v1/responses"
    assert seen["auth"] == "Bearer test-key"
    body = seen["body"]
    assert isinstance(body, dict)
    assert body["model"] == "test-model"
    assert body["tools"] == [{"type": "web_search_preview"}]
    assert "最近对话" in body["input"][1]["content"]
    assert "贵州茅台" in body["input"][1]["content"]
    assert "不得把观察股票写成用户持仓" in body["input"][1]["content"]


@pytest.mark.asyncio
async def test_llm_web_provider_requires_api_key() -> None:
    provider = LLMWebAskProvider(settings=Settings(llm_web_api_key=None))

    with pytest.raises(ProviderUnavailable):
        await provider.ask_stock(LLMWebAskContext(question="贵州茅台怎么样"))


@pytest.mark.asyncio
async def test_llm_web_provider_supports_dashscope_openai_compatible_search() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content.decode())
        return httpx.Response(
            200,
            json={
                "output_text": json.dumps(
                    {"answer": "结论：先复核最新公告。", "intent": "catalyst"},
                    ensure_ascii=False,
                )
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = LLMWebAskProvider(
            settings=Settings(
                llm_web_api_key="test-key",
                llm_web_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                llm_web_model="qwen3.7-plus",
                llm_web_search_enabled=True,
            ),
            client=client,
        )
        await provider.ask_stock(LLMWebAskContext(question="贵州茅台最新催化是什么"))

    assert seen["url"] == "https://dashscope.aliyuncs.com/compatible-mode/v1/responses"
    body = seen["body"]
    assert isinstance(body, dict)
    assert body["tools"] == [{"type": "web_search"}]


@pytest.mark.asyncio
async def test_llm_web_provider_streams_responses_api_text() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content.decode())
        return httpx.Response(
            200,
            content=(
                'data: {"choices":[{"delta":{"content":"结论：先看公告。\\n"}}]}\n\n'
                'data: {"choices":[{"delta":{"content":"依据：近期公告需要核对。"}}]}\n\n'
                "data: [DONE]\n\n"
            ),
            headers={"content-type": "text/event-stream"},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = LLMWebAskProvider(
            settings=Settings(
                llm_web_api_key="test-key",
                llm_web_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                llm_web_model="qwen3.7-plus",
                llm_web_search_enabled=True,
            ),
            client=client,
        )
        context = LLMWebAskContext(
            question="贵州茅台现在主要风险是什么",
            stock={"symbol": "SH.600519", "name": "贵州茅台"},
            observed_at=datetime.now(UTC),
        )
        chunks = [chunk async for chunk in provider.stream_answer_text(context)]
        result = provider.streamed_response(context, "".join(chunks))

    assert chunks == ["结论：先看公告。\n", "依据：近期公告需要核对。"]
    assert result.answer == "先看公告。"
    assert result.evidence == ["近期公告需要核对。"]
    assert seen["url"] == "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    body = seen["body"]
    assert isinstance(body, dict)
    assert body["stream"] is True
    assert body["enable_search"] is True
    assert body["enable_thinking"] is False


def test_streamed_response_parses_json_fenced_dashscope_text() -> None:
    provider = LLMWebAskProvider(
        settings=Settings(
            llm_web_api_key="test-key",
            llm_web_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            llm_web_model="qwen3.7-plus",
        )
    )
    context = LLMWebAskContext(
        question="贵州茅台怎么看",
        stock={"symbol": "SH.600519", "name": "贵州茅台"},
        observed_at=datetime.now(UTC),
    )
    text = """```json
{
  "answer": "干净结论：先看量能和公告确认。",
  "evidence": ["依据 1"],
  "risks": ["公开信息可能滞后"],
  "next_actions": ["打开个股页复核"],
  "intent": "movement",
  "symbol": "SH.600519",
  "name": "贵州茅台"
}
```"""

    result = provider.streamed_response(context, text)

    assert result.answer == "干净结论：先看量能和公告确认。"
    assert result.evidence == ["依据 1"]
    assert result.risks == ["公开信息可能滞后"]
    assert result.next_actions == ["打开个股页复核"]
    assert "```" not in result.answer


def test_settings_accepts_dashscope_api_key_alias(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("MARKETDESK_LLM_WEB_API_KEY", raising=False)
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("DASHSCOPE_API_KEY=test-dashscope-key\n", encoding="utf-8")

    settings = Settings(_env_file=env_file)

    assert settings.llm_web_api_key == "test-dashscope-key"


def test_settings_accepts_financial_llm_configuration(tmp_path, monkeypatch) -> None:
    for key in (
        "MARKETDESK_LLM_WEB_API_KEY",
        "DASHSCOPE_API_KEY",
        "MARKETDESK_FINANCIAL_LLM_API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            (
                "MARKETDESK_FINANCIAL_LLM_API_KEY=finance-key",
                "MARKETDESK_FINANCIAL_LLM_BASE_URL=https://finance.example/v1",
                "MARKETDESK_FINANCIAL_LLM_MODEL=finance-model",
                "MARKETDESK_FINANCIAL_LLM_API_STYLE=chat_completions",
                "MARKETDESK_FINANCIAL_LLM_WEB_SEARCH_ENABLED=false",
            )
        )
        + "\n",
        encoding="utf-8",
    )

    settings = Settings(_env_file=env_file)

    assert settings.llm_web_api_key == "finance-key"
    assert settings.llm_web_base_url == "https://finance.example/v1"
    assert settings.llm_web_model == "finance-model"
    assert settings.llm_web_api_style == "chat_completions"
    assert settings.llm_web_search_enabled is False
