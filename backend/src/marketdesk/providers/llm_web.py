from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal, cast

import httpx

from marketdesk.config import Settings
from marketdesk.models import (
    AskStockConversationMessage,
    AskStockMetric,
    AskStockResponse,
    AskStockSourceContext,
)
from marketdesk.providers.base import ProviderUnavailable

LLMIntent = Literal[
    "risk",
    "trend",
    "valuation",
    "fundamental",
    "catalyst",
    "action",
    "movement",
    "overview",
    "screening",
    "portfolio",
]

_INTENTS: set[str] = {
    "risk",
    "trend",
    "valuation",
    "fundamental",
    "catalyst",
    "action",
    "movement",
    "overview",
    "screening",
    "portfolio",
}


@dataclass(frozen=True)
class LLMWebAskContext:
    question: str
    conversation: tuple[AskStockConversationMessage, ...] = ()
    source_context: AskStockSourceContext | None = None
    stock: dict[str, str | int | float | None] | None = None
    holdings: tuple[str, ...] = ()
    observed_at: datetime | None = None
    market_notes: tuple[str, ...] = field(default_factory=tuple)
    analysis_notes: tuple[str, ...] = field(default_factory=tuple)


class LLMWebAskProvider:
    def __init__(
        self,
        settings: Settings | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.settings = settings or Settings()
        self.client = client or httpx.AsyncClient(timeout=45, follow_redirects=True, trust_env=False)

    @property
    def configured(self) -> bool:
        return bool(self.settings.llm_web_api_key)

    def provider_status(self) -> dict[str, dict[str, Any]]:
        return {
            "llm_web_answer": {
                "status": "configured" if self.configured else "not_configured",
                "required": False,
                "description": "金融大模型问股",
                "model": self.settings.llm_web_model,
                "api_style": self.settings.llm_web_api_style,
                "web_search": self.settings.llm_web_search_enabled,
            }
        }

    async def ask_stock(self, context: LLMWebAskContext) -> AskStockResponse:
        if not self.configured:
            raise ProviderUnavailable("llm web answer is not configured")

        api_style = self._api_style(stream=False)
        if api_style == "chat_completions":
            url = f"{self.settings.llm_web_base_url.rstrip('/')}/chat/completions"
            payload: dict[str, Any] = {
                "model": self.settings.llm_web_model,
                "messages": [
                    {"role": "system", "content": self._system_prompt()},
                    {"role": "user", "content": self._user_prompt(context)},
                ],
                "max_tokens": 1200,
            }
            if self._uses_dashscope() and self.settings.llm_web_search_enabled:
                payload["enable_search"] = True
                payload["enable_thinking"] = False
        else:
            url = f"{self.settings.llm_web_base_url.rstrip('/')}/responses"
            payload = {
                "model": self.settings.llm_web_model,
                "max_output_tokens": 1200,
                "input": [
                    {"role": "system", "content": self._system_prompt()},
                    {"role": "user", "content": self._user_prompt(context)},
                ],
            }
            if self.settings.llm_web_search_enabled:
                payload["tools"] = [self._web_search_tool()]
        try:
            response = await self.client.post(
                url,
                headers={
                    "Authorization": f"Bearer {self.settings.llm_web_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            data = cast(dict[str, Any], response.json())
        except (httpx.HTTPError, ValueError) as error:
            raise ProviderUnavailable(f"llm web answer failed: {error}") from error

        parsed = self._parse_answer(self._output_text(data))
        return AskStockResponse(
            kind="llm_answer",
            question=context.question,
            intent=self._intent(parsed),
            symbol=self._string_or_none(parsed.get("symbol")) or self._context_symbol(context),
            name=self._string_or_none(parsed.get("name")) or self._context_name(context),
            answer=self._clean_display_text(self._answer_text(parsed)),
            evidence=self._clean_display_list(
                self._string_list(
                    parsed.get("evidence"),
                    fallback="公开信息核对未返回可结构化依据。",
                )
            ),
            risks=self._clean_display_list(
                self._string_list(
                    parsed.get("risks"),
                    fallback="公开信息可能滞后，需复核公告、行情和成交。",
                )
            ),
            next_actions=self._clean_display_list(
                self._string_list(
                    parsed.get("next_actions"),
                    fallback="打开个股研究页核对本地证据，再决定是否行动。",
                )
            ),
            metrics=[
                AskStockMetric(label="回答模式", value="智能分析", tone="neutral"),
                AskStockMetric(
                    label="上下文",
                    value="已带入" if context.conversation or context.stock else "仅本轮",
                    tone="neutral",
                ),
            ],
            observed_at=context.observed_at,
            source="智能分析",
            disclaimer="研究辅助信息，不构成投资建议；交易前请复核公告、行情和账户风险。",
        )

    async def stream_answer_text(self, context: LLMWebAskContext) -> AsyncIterator[str]:
        if not self.configured:
            raise ProviderUnavailable("llm web answer is not configured")

        if self._api_style(stream=True) == "chat_completions":
            url = f"{self.settings.llm_web_base_url.rstrip('/')}/chat/completions"
            payload: dict[str, Any] = {
                "model": self.settings.llm_web_model,
                "messages": [
                    {"role": "system", "content": self._stream_system_prompt()},
                    {"role": "user", "content": self._user_prompt(context)},
                ],
                "max_tokens": 900,
                "stream": True,
            }
            if self._uses_dashscope() and self.settings.llm_web_search_enabled:
                payload["enable_search"] = True
                payload["enable_thinking"] = False
        else:
            url = f"{self.settings.llm_web_base_url.rstrip('/')}/responses"
            payload = {
                "model": self.settings.llm_web_model,
                "max_output_tokens": 900,
                "stream": True,
                "input": [
                    {"role": "system", "content": self._stream_system_prompt()},
                    {"role": "user", "content": self._user_prompt(context)},
                ],
            }
            if self.settings.llm_web_search_enabled:
                payload["tools"] = [self._web_search_tool()]
        try:
            async with self.client.stream(
                "POST",
                url,
                headers={
                    "Authorization": f"Bearer {self.settings.llm_web_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    chunk = self._stream_delta(line)
                    if chunk:
                        yield chunk
        except httpx.HTTPError as error:
            raise ProviderUnavailable(f"llm web answer failed: {error}") from error

    def streamed_response(self, context: LLMWebAskContext, text: str) -> AskStockResponse:
        parsed = self._parse_answer(text)
        if not self._has_structured_answer(parsed):
            parsed = self._parse_stream_sections(text)
        return AskStockResponse(
            kind="llm_answer",
            question=context.question,
            intent=self._intent(parsed),
            symbol=self._string_or_none(parsed.get("symbol")) or self._context_symbol(context),
            name=self._string_or_none(parsed.get("name")) or self._context_name(context),
            answer=self._clean_display_text(self._answer_text(parsed)),
            evidence=self._clean_display_list(
                self._string_list(
                    parsed.get("evidence"),
                    fallback="公开信息核对未返回可结构化依据。",
                )
            ),
            risks=self._clean_display_list(
                self._string_list(
                    parsed.get("risks"),
                    fallback="公开信息可能滞后，需复核公告、行情和成交。",
                )
            ),
            next_actions=self._clean_display_list(
                self._string_list(
                    parsed.get("next_actions"),
                    fallback="打开个股研究页核对本地证据，再决定是否行动。",
                )
            ),
            metrics=[
                AskStockMetric(label="回答模式", value="智能分析", tone="neutral"),
                AskStockMetric(
                    label="上下文",
                    value="已带入" if context.conversation or context.stock else "仅本轮",
                    tone="neutral",
                ),
            ],
            observed_at=context.observed_at,
            source="智能分析",
            disclaimer="研究辅助信息，不构成投资建议；交易前请复核公告、行情和账户风险。",
        )

    def _web_search_tool(self) -> dict[str, str]:
        tool_type = "web_search" if self._uses_dashscope() else "web_search_preview"
        return {"type": tool_type}

    def _uses_dashscope(self) -> bool:
        return "dashscope" in self.settings.llm_web_base_url.lower()

    def _api_style(self, *, stream: bool) -> Literal["responses", "chat_completions"]:
        configured = self.settings.llm_web_api_style
        if configured != "auto":
            return configured
        if stream and self._uses_dashscope():
            return "chat_completions"
        return "responses"

    def _system_prompt(self) -> str:
        return (
            "你是金融投研问答助手。必须优先使用系统提供的本地行情、确定性分析、持仓和对话上下文，"
            "只有上下文不足时才使用公开信息补充，回答要短、结论先行。"
            "必须使用普通投资者能直接听懂的日常中文，围绕为什么值得看、主要担心什么、下一步做什么来回答。"
            "不要堆砌K线、MA、MACD、RSI、ATR、波动率等术语；必须使用时，要紧接着用一句白话解释它代表什么。"
            "不要写成说明书，不要复述系统能力，不要编造数据或承诺收益。"
            "如果公开信息不足，明确说哪些点未确认。"
            "输出必须是 JSON，字段：answer, evidence, risks, next_actions, intent, symbol, name。"
        )

    def _stream_system_prompt(self) -> str:
        return (
            "你是金融投研问答助手。必须优先使用系统提供的本地行情、确定性分析、持仓和对话上下文，"
            "只有上下文不足时才使用公开信息补充，直接输出中文短回答。"
            "必须使用普通投资者能直接听懂的日常中文，不堆砌K线、MA、MACD、RSI、ATR、波动率等术语；"
            "必须使用时，要紧接着解释它代表什么。先讲为什么值得看或不值得看，再讲主要担心和下一步。"
            "不要输出 JSON，不要写说明书，不要复述系统能力，不要承诺收益。"
            "格式固定为：结论：...\n依据：...\n风险：...\n下一步：..."
        )

    def _user_prompt(self, context: LLMWebAskContext) -> str:
        blocks = [
            f"当前日期：{datetime.now(UTC).date().isoformat()}",
            f"用户问题：{context.question}",
        ]
        if context.source_context is not None:
            source = context.source_context
            detail = f"{source.origin} / {source.label}"
            if source.detail:
                detail = f"{detail} / {source.detail}"
            blocks.append(f"页面来源上下文：{detail}")
        if context.stock is not None:
            blocks.append(f"股票上下文：{json.dumps(context.stock, ensure_ascii=False)}")
        if context.market_notes:
            blocks.append("本地市场摘要：" + "；".join(context.market_notes[:6]))
        if context.analysis_notes:
            blocks.append("确定性分析上下文：" + "；".join(context.analysis_notes[:12]))
        if context.holdings:
            blocks.append("当前账号持仓上下文：" + "；".join(context.holdings[:8]))
        if context.conversation:
            history = [
                f"{message.role}: {message.content}" for message in context.conversation[-8:]
            ]
            blocks.append("最近对话：\n" + "\n".join(history))
        blocks.append(
            "请直接用日常中文回答用户问题。answer 控制在 2-4 句；先说结论和原因，"
            "再分别给出主要担心与可执行的下一步；evidence/risks/next_actions 每项不超过 5 条。"
        )
        return "\n\n".join(blocks)

    def _output_text(self, data: dict[str, Any]) -> str:
        direct = data.get("output_text")
        if isinstance(direct, str) and direct.strip():
            return direct
        chunks: list[str] = []
        output = data.get("output")
        if isinstance(output, list):
            for item in output:
                if not isinstance(item, dict):
                    continue
                content = item.get("content")
                if not isinstance(content, list):
                    continue
                for part in content:
                    if isinstance(part, dict) and isinstance(part.get("text"), str):
                        chunks.append(cast(str, part["text"]))
        choices = data.get("choices")
        if isinstance(choices, list) and choices:
            first = choices[0]
            if isinstance(first, dict):
                message = first.get("message")
                if isinstance(message, dict) and isinstance(message.get("content"), str):
                    chunks.append(cast(str, message["content"]))
        return "\n".join(chunks).strip()

    def _stream_delta(self, line: str) -> str:
        if not line.startswith("data:"):
            return ""
        value = line.removeprefix("data:").strip()
        if not value or value == "[DONE]":
            return ""
        try:
            payload = json.loads(value)
        except ValueError:
            return ""
        if not isinstance(payload, dict):
            return ""
        if payload.get("type") == "response.output_text.delta":
            delta = payload.get("delta")
            return delta if isinstance(delta, str) else ""
        choices = payload.get("choices")
        if isinstance(choices, list) and choices:
            first = choices[0]
            if isinstance(first, dict):
                delta = first.get("delta")
                if isinstance(delta, dict) and isinstance(delta.get("content"), str):
                    return cast(str, delta["content"])
        return ""

    def _parse_answer(self, text: str) -> dict[str, Any]:
        if not text:
            return {}
        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else {}
        except ValueError:
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                try:
                    parsed = json.loads(text[start : end + 1])
                    return parsed if isinstance(parsed, dict) else {}
                except ValueError:
                    return {"answer": text}
            return {"answer": text}

    def _has_structured_answer(self, parsed: dict[str, Any]) -> bool:
        if "intent" in parsed and self._string_or_none(parsed.get("answer")):
            return True
        return any(
            key in parsed and parsed.get(key) not in (None, "", [])
            for key in ("evidence", "risks", "next_actions")
        )

    def _parse_stream_sections(self, text: str) -> dict[str, Any]:
        normalized = text.strip()
        if not normalized:
            return {}
        sections: dict[str, list[str]] = {"evidence": [], "risks": [], "next_actions": []}
        answer = normalized
        heading_pattern = re.compile(r"(?:^|\n)\s*(结论|依据|风险|下一步)[：:]\s*")
        matches = list(heading_pattern.finditer(normalized))
        if matches:
            answer = ""
            for index, match in enumerate(matches):
                label = match.group(1)
                start = match.end()
                end = matches[index + 1].start() if index + 1 < len(matches) else len(normalized)
                content = normalized[start:end].strip()
                if label == "结论":
                    answer = content
                elif label == "依据":
                    sections["evidence"] = self._section_items(content)
                elif label == "风险":
                    sections["risks"] = self._section_items(content)
                elif label == "下一步":
                    sections["next_actions"] = self._section_items(content)
        return {
            "answer": answer or normalized,
            "evidence": sections["evidence"],
            "risks": sections["risks"],
            "next_actions": sections["next_actions"],
            "intent": "overview",
        }

    def _section_items(self, content: str) -> list[str]:
        items = [
            re.sub(r"^[\-•\d.、\s]+", "", item).strip()
            for item in re.split(r"[\n；;]", content)
        ]
        return [item for item in items if item][:5]

    def _answer_text(self, parsed: dict[str, Any]) -> str:
        answer = self._string_or_none(parsed.get("answer"))
        if answer:
            return answer
        return "智能分析已返回，但没有形成可用结论；请换一种更具体的问法。"

    def _clean_display_text(self, value: str) -> str:
        return (
            value.replace("联网大模型问答", "智能分析")
            .replace("联网问答", "智能分析")
            .replace("联网检索", "资料核对")
            .replace("联网结论：", "结论：")
            .replace("联网结论:", "结论：")
            .replace("联网依据", "依据")
            .replace("联网研究", "研究")
            .replace("已检索", "已核对")
            .replace("检索", "核对")
            .replace("联网", "")
            .strip()
        )

    def _clean_display_list(self, values: list[str]) -> list[str]:
        return [item for item in (self._clean_display_text(value) for value in values) if item]

    def _intent(self, parsed: dict[str, Any]) -> LLMIntent:
        intent = self._string_or_none(parsed.get("intent"))
        if intent in _INTENTS:
            return cast(LLMIntent, intent)
        return "overview"

    def _string_list(self, value: object, *, fallback: str) -> list[str]:
        if isinstance(value, list):
            items = [
                item.strip()
                for item in value
                if isinstance(item, str) and item.strip()
            ][:5]
            if items:
                return items
        return [fallback]

    def _string_or_none(self, value: object) -> str | None:
        if not isinstance(value, str):
            return None
        normalized = " ".join(value.split())
        return normalized or None

    def _context_symbol(self, context: LLMWebAskContext) -> str | None:
        if context.stock is None:
            return None
        symbol = context.stock.get("symbol")
        return symbol if isinstance(symbol, str) and symbol else None

    def _context_name(self, context: LLMWebAskContext) -> str | None:
        if context.stock is None:
            return None
        name = context.stock.get("name")
        return name if isinstance(name, str) and name else None
