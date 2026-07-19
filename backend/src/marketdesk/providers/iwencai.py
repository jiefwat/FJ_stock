from __future__ import annotations

from typing import Any, cast

import httpx

from marketdesk.config import Settings
from marketdesk.providers.base import ProviderUnavailable


class IwencaiProvider:
    def __init__(
        self,
        endpoint: str | None = None,
        api_key: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        settings = Settings()
        self.endpoint = endpoint or settings.iwencai_endpoint
        self.api_key = api_key or settings.iwencai_api_key
        self.client = client or httpx.AsyncClient(timeout=15, follow_redirects=True)

    @property
    def configured(self) -> bool:
        return bool(self.endpoint and self.api_key)

    async def fetch_research_evidence(
        self, symbol: str, name: str, sector: str | None = None
    ) -> list[str]:
        if not self.configured:
            return []
        assert self.endpoint is not None
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        query = f"{name} {symbol} 最近公告 研报 投资者问答 风险提示"
        if sector:
            query += f" 所属行业 {sector}"
        try:
            response = await self.client.post(
                self.endpoint,
                json={"query": query, "symbol": symbol, "name": name, "sector": sector},
                headers=headers,
            )
            response.raise_for_status()
            return normalize_research_evidence(cast(dict[str, Any], response.json()))
        except (httpx.HTTPError, ValueError) as error:
            raise ProviderUnavailable(f"semantic research request failed: {error}") from error


def normalize_research_evidence(payload: dict[str, Any], limit: int = 5) -> list[str]:
    candidates: list[str] = []
    for key in ("research_evidence", "summary", "announcements", "reports", "risks"):
        value = payload.get(key)
        if isinstance(value, str):
            candidates.append(value)
        elif isinstance(value, list):
            candidates.extend(_extract_text(item) for item in value)
    data = payload.get("data")
    if isinstance(data, dict):
        candidates.extend(normalize_research_evidence(data, limit=limit))
    elif isinstance(data, list):
        candidates.extend(_extract_text(item) for item in data)
    cleaned = []
    for item in candidates:
        text = " ".join(str(item).split())
        if text and text not in cleaned:
            cleaned.append(text)
    return cleaned[:limit]


def _extract_text(item: object) -> str:
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        for key in ("summary", "title", "content", "text", "name"):
            value = item.get(key)
            if value:
                return str(value)
    return ""
