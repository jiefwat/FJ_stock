import json

import httpx
import pytest

from marketdesk.models import SemanticScreenResult
from marketdesk.providers.iwencai import (
    IwencaiProvider,
    normalize_research_evidence,
    normalize_stock_screen,
)
from marketdesk.providers.public_market import PublicMarketProvider


def test_normalize_research_evidence_accepts_common_payload_shapes() -> None:
    payload = {
        "summary": "近三十日有分红相关公告",
        "reports": [{"title": "研报关注现金流与渠道库存"}],
        "data": {"risks": ["食品安全风险仍需跟踪"]},
    }

    evidence = normalize_research_evidence(payload)

    assert evidence == ["近三十日有分红相关公告", "研报关注现金流与渠道库存", "食品安全风险仍需跟踪"]


def test_normalize_stock_screen_prioritizes_identity_columns() -> None:
    payload = {
        "data": [
            {
                "市盈率": 23.1,
                "股票简称": " 贵州 茅台 ",
                "股票代码": "600519",
                "详情": {"unsafe": "nested"},
            }
        ]
    }

    result = normalize_stock_screen(payload)

    assert result.columns == ["股票代码", "股票简称", "市盈率"]
    assert result.rows == [{"股票代码": "600519", "股票简称": "贵州 茅台", "市盈率": 23.1}]


def test_normalize_stock_screen_bounds_rows_columns_and_strings() -> None:
    rows = [
        {f"字段{column}": "  一段   很长的值  " * 50 for column in range(15)}
        for _ in range(25)
    ]

    result = normalize_stock_screen({"data": rows})

    assert len(result.columns) == 12
    assert len(result.rows) == 20
    assert all(len(str(value)) <= 300 for row in result.rows for value in row.values())


@pytest.mark.asyncio
async def test_query_stocks_posts_bounded_semantic_request() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "data": [
                    {"股票代码": f"{index:06d}", "股票简称": f"测试股票{index}"}
                    for index in range(1, 101)
                ]
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = IwencaiProvider(
            endpoint="https://semantic.example.test/query",
            api_key="test-key",
            client=client,
        )
        result = await provider.query_stocks("低估值白酒股", limit=100)

    assert result.rows[0]["股票代码"] == "000001"
    assert len(result.rows) == 100
    assert requests[0].headers["Authorization"] == "Bearer test-key"
    assert json.loads(requests[0].content) == {
        "query": "低估值白酒股",
        "query_type": "stock",
        "limit": 100,
    }


@pytest.mark.asyncio
async def test_public_provider_delegates_semantic_stock_screen() -> None:
    class SemanticFixture:
        configured = True

        async def query_stocks(self, question: str, limit: int = 20) -> SemanticScreenResult:
            assert question == "低估值白酒股"
            assert limit == 20
            return SemanticScreenResult(
                columns=["股票代码", "股票简称"],
                rows=[{"股票代码": "600519", "股票简称": "贵州茅台"}],
            )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(500))
    ) as client:
        provider = PublicMarketProvider(client=client)
        provider.research_provider = SemanticFixture()  # type: ignore[assignment]
        result = await provider.query_stock_screen("低估值白酒股")

    assert result.rows[0]["股票简称"] == "贵州茅台"
    assert provider.provider_status()["semantic_research"]["status"] == "ready"
