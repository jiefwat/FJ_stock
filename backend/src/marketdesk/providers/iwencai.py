from __future__ import annotations

import math
from typing import Any, cast

import httpx

from marketdesk.config import Settings
from marketdesk.models import JsonScalar, SemanticScreenResult
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


    async def query_stocks(self, question: str, limit: int = 20) -> SemanticScreenResult:
        if not self.configured:
            raise ProviderUnavailable("semantic stock screening is not configured")
        assert self.endpoint is not None
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        bounded_limit = min(max(limit, 1), 20)
        try:
            response = await self.client.post(
                self.endpoint,
                json={"query": question, "query_type": "stock", "limit": bounded_limit},
                headers=headers,
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("response must be a JSON object")
            result = normalize_stock_screen(
                cast(dict[str, Any], payload), row_limit=bounded_limit
            )
            if not result.rows:
                raise ValueError("response contains no usable stock rows")
            return result
        except (httpx.HTTPError, ValueError) as error:
            raise ProviderUnavailable(f"semantic stock screening failed: {error}") from error


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


def normalize_stock_screen(
    payload: dict[str, Any], row_limit: int = 20, column_limit: int = 12
) -> SemanticScreenResult:
    raw_rows = _extract_rows(payload)
    normalized_rows: list[dict[str, JsonScalar]] = []
    discovered_columns: list[str] = []
    for raw_row in raw_rows[: min(max(row_limit, 0), 20)]:
        row: dict[str, JsonScalar] = {}
        for raw_key, raw_value in raw_row.items():
            key = " ".join(str(raw_key).split())[:80]
            value = _normalize_scalar(raw_value)
            if not key or value is _UNUSABLE:
                continue
            row[key] = cast(JsonScalar, value)
            if key not in discovered_columns:
                discovered_columns.append(key)
        if row:
            normalized_rows.append(row)

    columns = sorted(discovered_columns, key=_column_priority)[: min(max(column_limit, 0), 12)]
    rows = [{column: row[column] for column in columns if column in row} for row in normalized_rows]
    return SemanticScreenResult(columns=columns, rows=rows)


def _extract_text(item: object) -> str:
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        for key in ("summary", "title", "content", "text", "name"):
            value = item.get(key)
            if value:
                return str(value)
    return ""


_UNUSABLE = object()


def _extract_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data: object = payload.get("data", payload.get("rows", payload.get("items", [])))
    if isinstance(data, dict):
        data = data.get("rows", data.get("items", data.get("data", [])))
    if not isinstance(data, list):
        return []
    return [cast(dict[str, Any], item) for item in data if isinstance(item, dict)]


def _normalize_scalar(value: object) -> JsonScalar | object:
    if value is None or isinstance(value, bool | int):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, str):
        return " ".join(value.split())[:300]
    return _UNUSABLE


def _column_priority(column: str) -> tuple[int, int]:
    normalized = column.casefold()
    if any(token in normalized for token in ("股票代码", "证券代码", "symbol", "code")):
        return (0, 0)
    if any(token in normalized for token in ("股票简称", "股票名称", "证券简称", "name")):
        return (1, 0)
    return (2, 0)
