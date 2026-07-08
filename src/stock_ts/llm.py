from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol

from .config import Settings, get_settings
from .deep_models import DeepStockReport
from .report import DISCLAIMER


class ChatClient(Protocol):
    def complete(self, messages: list[dict[str, str]], *, settings: Settings) -> str:
        raise NotImplementedError


@dataclass(frozen=True)
class AiInsightResult:
    enabled: bool
    provider: str
    model: str
    markdown: str
    error: str = ""


@dataclass(frozen=True)
class StaticChatClient:
    response: str

    def complete(self, messages: list[dict[str, str]], *, settings: Settings) -> str:
        return self.response


class OpenAICompatibleChatClient:
    def complete(self, messages: list[dict[str, str]], *, settings: Settings) -> str:
        endpoint = settings.llm_base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": settings.llm_model,
            "messages": messages,
            "temperature": settings.llm_temperature,
            "max_tokens": 1200,
        }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            endpoint,
            data=data,
            headers={
                "Authorization": f"Bearer {settings.llm_api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=settings.llm_timeout) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")[:300]
            raise RuntimeError(f"LLM HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"LLM request failed: {exc.reason}") from exc
        parsed = json.loads(body)
        choices = parsed.get("choices") or []
        if not choices:
            raise RuntimeError("LLM response has no choices")
        message = choices[0].get("message") or {}
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("LLM response content is empty")
        return content.strip()


def generate_stock_ai_insight(
    report: DeepStockReport,
    *,
    settings: Settings | None = None,
    client: ChatClient | None = None,
) -> AiInsightResult:
    settings = settings or get_settings()
    if not settings.has_llm_api_key:
        return AiInsightResult(
            enabled=False,
            provider=settings.llm_provider,
            model=settings.llm_model,
            markdown=_disabled_markdown(report, settings),
        )
    client = client or OpenAICompatibleChatClient()
    messages = [
        {
            "role": "system",
            "content": (
                "你是谨慎的股票复盘助手。只基于用户提供的结构化数据分析，"
                "不得承诺收益，不得输出确定性买卖建议，必须包含风险和失效条件。"
            ),
        },
        {"role": "user", "content": _prompt(report)},
    ]
    try:
        content = client.complete(messages, settings=settings)
    except Exception as exc:
        return AiInsightResult(
            enabled=False,
            provider=settings.llm_provider,
            model=settings.llm_model,
            markdown=_failed_markdown(report, settings, str(exc)),
            error=str(exc),
        )
    markdown = "\n".join(
        [
            f"# AI 增强研报：{report.name}（{report.code}）",
            "",
            DISCLAIMER,
            "",
            f"- 模型：{settings.llm_provider} / {settings.llm_model}",
            "- 说明：以下内容由大模型基于 StockTS 结构化分析生成，必须人工复核。",
            "",
            "## AI 观点",
            content.strip(),
            "",
            "---",
            DISCLAIMER,
        ]
    )
    return AiInsightResult(
        enabled=True,
        provider=settings.llm_provider,
        model=settings.llm_model,
        markdown=markdown.strip() + "\n",
    )


def _prompt(report: DeepStockReport) -> str:
    angle_lines = "\n".join(
        f"- {angle.name}: {angle.score}/100, {angle.stance}, {angle.evidence}"
        for angle in report.angles
    )
    debate_lines = "\n".join(
        f"- {item.role}: {item.thesis}; 证据={'；'.join(item.evidence)}; 约束={item.rebuttal}"
        for item in report.debate_rounds
    )
    risks = "\n".join(f"- {item}" for item in report.risks)
    invalid = "\n".join(f"- {item}" for item in report.invalid_conditions)
    return f"""
请基于以下 StockTS 结构化分析，生成一份中文增强研报。

股票：{report.name}（{report.code}）
日期：{report.trade_date}
最新价：{report.latest_close:.2f}
趋势：{report.trend}
风险等级：{report.risk_level}
规则结论：{report.final_conclusion}
综合机会评分：{report.upside.score}/100（{report.upside.label}）

多角度评分：
{angle_lines}

多轮对抗：
{debate_lines}

风险：
{risks}

失效条件：
{invalid}

输出要求：
1. 用“观察、情景、风险、失效条件”表述。
2. 不得承诺上涨，不得输出“买入/卖出/必涨”。
3. 给出 3 条后续跟踪清单。
""".strip()


def _disabled_markdown(report: DeepStockReport, settings: Settings) -> str:
    return (
        "\n".join(
            [
                f"# AI 增强研报：{report.name}（{report.code}）",
                "",
                DISCLAIMER,
                "",
                "AI 增强未启用：未检测到 `STOCK_TS_LLM_API_KEY` 或 `DASHSCOPE_API_KEY`。",
                f"当前规则结论：{report.final_conclusion}",
                "",
                "## 如何启用",
                "- 将真实 Key 放入本机 `.env`，不要提交到仓库。",
                f"- 当前模型配置：{settings.llm_provider} / {settings.llm_model}",
                "- 配置后重新运行 `ai-insight`。",
                "",
                "---",
                DISCLAIMER,
            ]
        ).strip()
        + "\n"
    )


def _failed_markdown(report: DeepStockReport, settings: Settings, error: str) -> str:
    safe_error = (
        error.replace(settings.llm_api_key, "[redacted]") if settings.llm_api_key else error
    )
    return (
        "\n".join(
            [
                f"# AI 增强研报：{report.name}（{report.code}）",
                "",
                DISCLAIMER,
                "",
                "AI 增强调用失败，已降级为规则结论。",
                f"- 模型：{settings.llm_provider} / {settings.llm_model}",
                f"- 错误：{safe_error}",
                f"- 当前规则结论：{report.final_conclusion}",
                "",
                "---",
                DISCLAIMER,
            ]
        ).strip()
        + "\n"
    )
