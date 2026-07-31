import json
from datetime import UTC, datetime

import httpx
import pytest

from marketdesk.config import Settings
from marketdesk.models import AskStockConversationMessage
from marketdesk.providers.base import ProviderUnavailable
from marketdesk.providers.llm_web import LLMWebAskContext, LLMWebAskProvider


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
                        "answer": "联网结论：先看最新公告和行业消息。",
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
    assert result.source == "联网大模型问答"
    assert seen["url"] == "https://llm.example/v1/responses"
    assert seen["auth"] == "Bearer test-key"
    body = seen["body"]
    assert isinstance(body, dict)
    assert body["model"] == "test-model"
    assert body["tools"] == [{"type": "web_search_preview"}]
    assert "最近对话" in body["input"][1]["content"]
    assert "贵州茅台" in body["input"][1]["content"]


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
            ),
            client=client,
        )
        await provider.ask_stock(LLMWebAskContext(question="贵州茅台最新催化是什么"))

    assert seen["url"] == "https://dashscope.aliyuncs.com/compatible-mode/v1/responses"
    body = seen["body"]
    assert isinstance(body, dict)
    assert body["tools"] == [{"type": "web_search"}]


def test_settings_accepts_dashscope_api_key_alias(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("MARKETDESK_LLM_WEB_API_KEY", raising=False)
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("DASHSCOPE_API_KEY=test-dashscope-key\n", encoding="utf-8")

    settings = Settings(_env_file=env_file)

    assert settings.llm_web_api_key == "test-dashscope-key"
