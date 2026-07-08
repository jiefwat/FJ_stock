from stock_ts.news_fetcher import fetch_akshare_stock_news


class MiniFrame:
    empty = False

    def iterrows(self):
        yield (
            0,
            {
                "新闻标题": "公司遭监管处罚",
                "新闻内容": "业绩下滑风险",
                "发布时间": "2026-07-08 09:00:00",
                "文章来源": "东方财富",
            },
        )


class Ak:
    def stock_news_em(self, symbol: str):
        return MiniFrame()


def test_fetch_akshare_stock_news_classifies_sentiment() -> None:
    items = fetch_akshare_stock_news(Ak(), symbol="600519")

    assert items[0].sentiment == "negative"
