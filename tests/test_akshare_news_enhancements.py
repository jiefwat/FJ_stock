from __future__ import annotations

from stock_ts.news_fetcher import fetch_akshare_stock_news
from stock_ts.providers.akshare_provider import AkshareProvider


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
        self.columns = set(rows[0].keys()) if rows else set()

    def __len__(self) -> int:
        return len(self._rows)

    def __contains__(self, key: str) -> bool:
        return key in self.columns

    def iterrows(self):
        for index, row in enumerate(self._rows):
            yield index, MiniSeries(row)

    def head(self, count: int) -> MiniFrame:
        return MiniFrame(self._rows[:count])


class BoardAndNewsAk:
    def stock_board_industry_name_em(self) -> MiniFrame:
        return MiniFrame(
            [
                {
                    "板块名称": "半导体",
                    "涨跌幅": 3.2,
                    "上涨家数": 50,
                    "下跌家数": 10,
                    "换手率": 4.1,
                },
                {
                    "板块名称": "银行",
                    "涨跌幅": -0.8,
                    "上涨家数": 8,
                    "下跌家数": 30,
                    "换手率": 1.2,
                },
            ]
        )

    def stock_board_industry_cons_em(self, symbol: str) -> MiniFrame:
        return MiniFrame(
            [
                {
                    "代码": "688001",
                    "名称": f"{symbol}龙头",
                    "最新价": 22.5,
                    "涨跌幅": 2.1,
                    "成交额": 9.8,
                    "换手率": 5.2,
                    "市盈率-动态": 42,
                },
                {
                    "代码": "688002",
                    "名称": f"{symbol}二号",
                    "最新价": 18.2,
                    "涨跌幅": 1.1,
                    "成交额": 4.8,
                    "换手率": 3.1,
                    "市盈率-动态": 28,
                },
            ]
        )

    def stock_zh_a_spot_em(self) -> MiniFrame:
        raise RuntimeError("spot unavailable")

    def stock_news_em(self, symbol: str) -> MiniFrame:
        return MiniFrame(
            [
                {
                    "关键词": symbol,
                    "新闻标题": "公司订单增长",
                    "新闻内容": "订单增长带动业绩预期",
                    "发布时间": "2026-06-12 09:30:00",
                    "文章来源": "东方财富",
                    "新闻链接": "https://example.com/news",
                }
            ]
        )


class BrokenAk:
    def stock_zh_index_daily_em(self, symbol: str) -> MiniFrame:
        raise RuntimeError("index unavailable")

    def stock_zh_a_spot_em(self) -> MiniFrame:
        raise RuntimeError("spot unavailable")

    def stock_board_industry_name_em(self) -> MiniFrame:
        raise RuntimeError("board unavailable")

    def stock_news_em(self, symbol: str) -> MiniFrame:
        raise RuntimeError("news unavailable")


def provider_with_fake_ak() -> AkshareProvider:
    provider = AkshareProvider.__new__(AkshareProvider)
    provider._ak = BoardAndNewsAk()
    return provider


def test_akshare_fetch_sectors_from_industry_board() -> None:
    sectors = provider_with_fake_ak().fetch_sectors()

    assert sectors[0].name == "半导体"
    assert sectors[0].pct_chg == 3.2
    assert sectors[0].advancing_ratio == 50 / 60
    assert sectors[0].amount_change == 4.1


def test_akshare_candidate_universe_falls_back_to_industry_constituents() -> None:
    universe = provider_with_fake_ak().fetch_candidate_universe()

    assert universe
    assert universe[0].sector == "半导体"
    assert universe[0].code == "688001"
    assert universe[0].name == "半导体龙头"
    assert len(universe[0].bars) >= 6


def test_fetch_akshare_stock_news_normalizes_news_items() -> None:
    items = fetch_akshare_stock_news(BoardAndNewsAk(), symbol="600519")

    assert len(items) == 1
    assert items[0].title == "公司订单增长"
    assert items[0].source == "东方财富"
    assert items[0].sentiment == "positive"


def test_cli_fetch_news_writes_markdown(monkeypatch, tmp_path) -> None:
    from stock_ts import cli

    class FakeAkshareProvider:
        _ak = BoardAndNewsAk()

    monkeypatch.setattr(cli, "AkshareProvider", FakeAkshareProvider)
    output = tmp_path / "news.md"

    status = cli.main(["fetch-news", "600519", "--output", str(output)])

    assert status == 0
    text = output.read_text(encoding="utf-8")
    assert "新闻舆情摘要" in text
    assert "公司订单增长" in text


def test_akshare_external_failures_return_fallback_data() -> None:
    provider = AkshareProvider.__new__(AkshareProvider)
    provider._ak = BrokenAk()

    market = provider.fetch_market()
    sectors = provider.fetch_sectors()
    candidates = provider.fetch_candidate_universe()
    news_items = fetch_akshare_stock_news(BrokenAk(), symbol="600519")

    assert market.trade_date == "latest"
    assert sectors
    assert candidates
    assert news_items[0].title == "AKShare新闻接口不可用"
