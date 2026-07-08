from __future__ import annotations

from stock_ts.models import DailyBar
from stock_ts.providers.eltdx_provider import EltdxProvider


def test_eltdx_provider_translates_latest_market_stock_and_candidates() -> None:
    calls: list[tuple[str, dict[str, object], str]] = []

    def runner(
        operation: str,
        payload: dict[str, object],
        python_executable: str,
    ) -> dict[str, object]:
        calls.append((operation, payload, python_executable))
        if operation == "market":
            return {
                "trade_date": "2026-06-18",
                "indices": [
                    {
                        "code": "000001",
                        "name": "上证指数",
                        "close": 4090.48,
                        "pct_chg": -0.43,
                        "amount": 15604.7,
                    },
                    {
                        "code": "399001",
                        "name": "深证成指",
                        "close": 16030.7,
                        "pct_chg": 0.94,
                        "amount": 17496.3,
                    },
                ],
                "advancing": 3125,
                "declining": 1841,
                "limit_up": 86,
                "limit_down": 22,
                "top_sectors": [["半导体", 6.8], ["白酒", 4.2]],
            }
        if operation == "stock":
            return {
                "code": "600519",
                "name": "贵州茅台",
                "fund_flow": -0.43,
                "pe_ttm": 28.1,
                "bars": [
                    {
                        "date": "2026-06-17",
                        "open": 1258.0,
                        "high": 1259.77,
                        "low": 1238.56,
                        "close": 1240.0,
                        "volume": 44803.3,
                    },
                    {
                        "date": "2026-06-18",
                        "open": 1235.0,
                        "high": 1238.87,
                        "low": 1211.22,
                        "close": 1215.0,
                        "volume": 57471.73,
                    },
                ],
            }
        if operation == "candidate_universe":
            return {
                "trade_date": "2026-06-18",
                "items": [
                    {
                        "code": "600519",
                        "name": "贵州茅台",
                        "sector": "白酒概念",
                        "fund_flow": -0.43,
                        "turnover_rate": 0.46,
                        "amount": 701.67,
                        "pe_ttm": 28.1,
                        "bars": [
                            {
                                "date": "2026-06-17",
                                "open": 1258.0,
                                "high": 1259.77,
                                "low": 1238.56,
                                "close": 1240.0,
                                "volume": 44803.3,
                            },
                            {
                                "date": "2026-06-18",
                                "open": 1235.0,
                                "high": 1238.87,
                                "low": 1211.22,
                                "close": 1215.0,
                                "volume": 57471.73,
                            },
                        ],
                    },
                    {
                        "code": "300750",
                        "name": "宁德时代",
                        "sector": "新能源",
                        "fund_flow": 1.2,
                        "turnover_rate": 1.05,
                        "amount": 812.34,
                        "pe_ttm": 34.7,
                        "bars": [
                            {
                                "date": "2026-06-17",
                                "open": 250.0,
                                "high": 255.0,
                                "low": 247.0,
                                "close": 253.0,
                                "volume": 12000.0,
                            },
                            {
                                "date": "2026-06-18",
                                "open": 253.0,
                                "high": 258.0,
                                "low": 251.0,
                                "close": 257.0,
                                "volume": 15000.0,
                            },
                        ],
                    },
                ],
            }
        raise AssertionError(operation)

    provider = EltdxProvider(runner=runner, python_executable="python3.11")

    market = provider.fetch_market()
    stock = provider.fetch_stock("600519")
    candidates = provider.fetch_candidate_universe()

    assert market.trade_date == "2026-06-18"
    assert market.indices[0].name == "上证指数"
    assert market.advancing == 3125
    assert stock.name == "贵州茅台"
    assert stock.bars[-1] == DailyBar(
        date="2026-06-18",
        open=1235.0,
        high=1238.87,
        low=1211.22,
        close=1215.0,
        volume=57471.73,
    )
    assert [item.code for item in candidates] == ["600519", "300750"]
    assert candidates[0].sector == "白酒概念"
    assert candidates[0].bars[-1].date == "2026-06-18"
    assert [op for op, _payload, _exe in calls] == [
        "market",
        "stock",
        "candidate_universe",
    ]
