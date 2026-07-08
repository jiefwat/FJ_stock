from __future__ import annotations

from pathlib import Path

import pytest

from stock_ts.portfolio import build_holdings_from_transactions, load_transactions_csv
from stock_ts.providers.akshare_provider import AkshareProvider
from stock_ts.workflows import build_daily_report, build_portfolio_report


class MiniSeries(dict):
    def __getitem__(self, key: str):
        return dict.__getitem__(self, key)

    def get(self, key: str, default=None):
        return dict.get(self, key, default)


class MiniILoc:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows

    def __getitem__(self, index: int) -> MiniSeries:
        return MiniSeries(self._rows[index])


class MiniFrame:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows
        self.empty = not rows
        self.iloc = MiniILoc(rows)

    def __len__(self) -> int:
        return len(self._rows)


class FailingSpotAk:
    def stock_zh_index_daily_em(self, symbol: str) -> MiniFrame:
        return MiniFrame(
            [
                {"close": 100.0, "amount": 1_000_000_000},
                {"close": 102.0, "amount": 1_200_000_000},
            ]
        )

    def stock_zh_a_spot_em(self) -> MiniFrame:
        raise RuntimeError("remote spot unavailable")


class FailingStockAk(FailingSpotAk):
    def stock_zh_a_hist(self, symbol: str, period: str, adjust: str) -> MiniFrame:
        raise RuntimeError("remote stock history unavailable")


def write_transactions(path: Path) -> None:
    path.write_text(
        "date,code,name,side,shares,price,fee,tax,sector,note\n"
        "2026-06-01,600519,贵州茅台,buy,100,1500,5,0,白酒,建仓\n"
        "2026-06-02,600519,贵州茅台,buy,50,1600,3,0,白酒,加仓\n"
        "2026-06-03,600519,贵州茅台,sell,20,1700,2,1,白酒,减仓\n"
        "2026-06-04,000001,平安银行,buy,1000,10.5,1,0,银行,低估值\n",
        encoding="utf-8",
    )


def test_transactions_csv_can_build_weighted_holdings(tmp_path: Path) -> None:
    tx_file = tmp_path / "transactions.csv"
    write_transactions(tx_file)

    transactions = load_transactions_csv(tx_file)
    holdings = build_holdings_from_transactions(transactions)

    assert len(transactions) == 4
    assert [(item.code, item.shares) for item in holdings] == [("600519", 130), ("000001", 1000)]
    maotai = holdings[0]
    assert maotai.name == "贵州茅台"
    assert maotai.sector == "白酒"
    assert maotai.cost_price == pytest.approx((100 * 1500 + 50 * 1600) / 150)


def test_portfolio_workflow_accepts_transactions_path(tmp_path: Path) -> None:
    tx_file = tmp_path / "transactions.csv"
    write_transactions(tx_file)

    from stock_ts.providers.sample import SampleDataProvider

    provider = SampleDataProvider()
    report = build_portfolio_report(provider, transactions_path=tx_file)
    daily = build_daily_report(provider, transactions_path=tx_file, candidate_limit=3)

    assert report.total_market_value > 0
    assert "600519" in [position.holding.code for position in report.positions]
    assert daily.portfolio is not None
    assert "每日持仓分析" in daily.markdown


def test_akshare_market_falls_back_to_index_only_when_spot_fails() -> None:
    provider = AkshareProvider.__new__(AkshareProvider)
    provider._ak = FailingSpotAk()

    market = provider.fetch_market()

    assert market.trade_date == "latest"
    assert len(market.indices) == 3
    assert market.advancing == 0
    assert market.declining == 0
    assert market.top_sectors == []


def test_akshare_stock_falls_back_to_sample_when_history_fails() -> None:
    provider = AkshareProvider.__new__(AkshareProvider)
    provider._ak = FailingStockAk()

    with pytest.warns(RuntimeWarning, match="AKShare stock 600519 unavailable"):
        stock = provider.fetch_stock("600519")

    assert stock.code == "600519"
    assert stock.name == "贵州茅台"
    assert stock.bars
