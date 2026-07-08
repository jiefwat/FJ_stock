from __future__ import annotations

import pytest

from stock_ts.providers.base import DataProviderError
from stock_ts.providers.itick_provider import ItickClient, to_itick_region_code


class FakeResponse:
    def __init__(self, payload: dict[str, object], status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code
        self.text = str(payload)

    def json(self) -> dict[str, object]:
        return self._payload


class FakeSession:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.calls: list[dict[str, object]] = []

    def get(
        self,
        url: str,
        *,
        params: dict[str, object],
        headers: dict[str, str],
        timeout: float,
    ) -> FakeResponse:
        self.calls.append({"url": url, "params": params, "headers": headers, "timeout": timeout})
        return self.response


def test_itick_maps_a_share_codes_to_region_and_exchange_suffix() -> None:
    assert to_itick_region_code("688362") == ("CN", "688362.SH")
    assert to_itick_region_code("000001") == ("CN", "000001.SZ")
    assert to_itick_region_code("430047") == ("CN", "430047.BJ")
    assert to_itick_region_code("600519.SH") == ("CN", "600519.SH")


def test_itick_client_fetches_daily_bars_with_token_header() -> None:
    session = FakeSession(
        FakeResponse(
            {
                "code": 0,
                "msg": None,
                "data": [
                    {
                        "t": 1729090560000,
                        "o": 10.0,
                        "h": 11.0,
                        "l": 9.8,
                        "c": 10.8,
                        "v": 10000,
                        "tu": 123456,
                    }
                ],
            }
        )
    )
    client = ItickClient(api_key="secret-token", session=session, timeout=3.5)

    bars = client.fetch_daily_bars("688362", limit=20)

    assert len(bars) == 1
    assert bars[0].date == "2024-10-16"
    assert bars[0].open == 10.0
    assert bars[0].close == 10.8
    assert bars[0].volume == 10000
    assert session.calls[0]["url"] == "https://api.itick.org/stock/kline"
    assert session.calls[0]["params"] == {"region": "CN", "code": "688362.SH", "kType": "8"}
    assert session.calls[0]["headers"] == {"accept": "application/json", "token": "secret-token"}
    assert session.calls[0]["timeout"] == 3.5


def test_itick_client_rejects_missing_token() -> None:
    with pytest.raises(DataProviderError, match="ITICK_API_KEY"):
        ItickClient(api_key="")


def test_itick_client_raises_readable_error_for_api_failure() -> None:
    session = FakeSession(FakeResponse({"code": 10001, "msg": "bad symbol", "data": []}))
    client = ItickClient(api_key="secret-token", session=session)

    with pytest.raises(DataProviderError, match="bad symbol"):
        client.fetch_daily_bars("688362")
