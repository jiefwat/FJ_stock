import json
from datetime import UTC, datetime
from types import SimpleNamespace

import httpx
import pytest

from marketdesk.providers.public_market import PublicMarketProvider, _market_observed_at


def test_public_provider_does_not_read_shell_proxy_environment(monkeypatch) -> None:
    created_clients: list[dict[str, object]] = []

    class FakeClient:
        def __init__(self, **kwargs: object) -> None:
            created_clients.append(kwargs)

    monkeypatch.setattr("marketdesk.providers.public_market.httpx.AsyncClient", FakeClient)

    PublicMarketProvider()

    assert created_clients[0]["trust_env"] is False


def test_sina_equities_normalize_market_cap_units() -> None:
    rows = [
        {
            "symbol": "sh600519",
            "code": "600519",
            "name": "贵州茅台",
            "trade": "1500.50",
            "changepercent": 1.25,
            "amount": 2_000_000_000,
            "turnoverratio": 0.63,
            "per": 22.4,
            "pb": 7.4,
            "mktcap": 1_900_000_00,
        }
    ]

    dataset = PublicMarketProvider().normalize_equities(rows)

    assert dataset.items[0].symbol == "SH.600519"
    assert dataset.items[0].market_cap == 1_900_000_000_000
    assert dataset.meta.coverage == 1


def test_sina_industry_payload_normalizes_sector_change() -> None:
    text = 'var S_Finance_bankuai_sinaindustry = {"new_dlhy":"new_dlhy,电力行业,62,8.266,0.1201,1.4751,5596,44585,sh600236,10.05,10.62,0.97,桂冠电力"};'

    sectors = PublicMarketProvider().normalize_sectors(text)

    assert sectors[0].name == "电力行业"
    assert sectors[0].change_pct == 1.4751


def test_eastmoney_board_constituents_normalize_to_quotes() -> None:
    payload = {
        "data": {
            "diff": [
                {
                    "f12": "600236",
                    "f14": "桂冠电力",
                    "f2": 10.62,
                    "f3": 10.05,
                    "f6": 387_794_582,
                    "f8": 0.47,
                    "f9": 24.36,
                    "f10": 2.38,
                    "f20": 83_710_852_257,
                    "f23": 4.87,
                    "f62": 87_265_482,
                    "f100": "电力",
                }
            ]
        }
    }

    quotes = PublicMarketProvider.normalize_eastmoney_board_constituents(payload)

    assert quotes[0].symbol == "SH.600236"
    assert quotes[0].net_flow == 87_265_482
    assert quotes[0].sector == "电力"


def test_eastmoney_financial_periods_normalize_and_deduplicate_reports() -> None:
    payload = {
        "result": {
            "data": [
                {
                    "REPORT_DATE": "2026-06-30 00:00:00",
                    "REPORT_DATE_NAME": "2026中报",
                    "REPORT_TYPE": "中报",
                    "TOTALOPERATEREVE": "90703000000",
                    "TOTALOPERATEREVETZ": "1.47",
                    "PARENTNETPROFIT": "44517000000",
                    "PARENTNETPROFITTZ": "-1.95",
                    "ROEJQ": "18.2",
                    "XSMLL": "91.3",
                    "MGJYXJJE": "16.8",
                    "JYXJLYYSR": "0.984",
                    "ZCFZL": "13.1",
                },
                {
                    "REPORT_DATE": "2026-06-30 00:00:00",
                    "REPORT_DATE_NAME": "重复中报",
                    "REPORT_TYPE": "中报",
                },
                {
                    "REPORT_DATE": "2026-03-31 00:00:00",
                    "REPORT_DATE_NAME": "2026一季报",
                    "REPORT_TYPE": "一季报",
                    "TOTALOPERATEREVE": "--",
                    "PARENTNETPROFIT": "",
                },
            ]
        }
    }

    periods = PublicMarketProvider.normalize_financial_periods(payload)

    assert [item.report_label for item in periods] == ["2026中报", "2026一季报"]
    assert periods[0].revenue_yoy == 1.47
    assert periods[0].net_profit_yoy == -1.95
    assert periods[0].cash_receipts_to_revenue == 98.4
    assert periods[1].revenue is None
    assert periods[1].net_profit is None


def test_eastmoney_stock_news_jsonp_normalizes_clean_articles() -> None:
    payload = "stockts(" + json.dumps(
        {
            "code": 0,
            "result": {
                "cmsArticleWebOld": [
                    {
                        "date": "2026-08-15 09:30:00",
                        "code": "202608151234",
                        "title": "<em>贵州茅台</em>半年报",
                        "content": "营业收入增长，<b>净利润</b>小幅下降。",
                        "mediaName": "证券时报",
                        "url": "https://finance.eastmoney.com/a/202608151234.html",
                    }
                ]
            },
        },
        ensure_ascii=False,
    ) + ")"

    items = PublicMarketProvider.normalize_stock_news(payload)

    assert items[0].id == "eastmoney-news:202608151234"
    assert items[0].title == "贵州茅台半年报"
    assert items[0].summary == "营业收入增长，净利润小幅下降。"
    assert items[0].media == "证券时报"
    assert items[0].published_at.tzinfo is not None


@pytest.mark.asyncio
async def test_eastmoney_financial_and_stock_news_fetch_contracts() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if "datacenter-web" in request.url.host:
            return httpx.Response(
                200,
                json={
                    "result": {
                        "data": [
                            {
                                "REPORT_DATE": "2026-06-30 00:00:00",
                                "REPORT_DATE_NAME": "2026中报",
                                "REPORT_TYPE": "中报",
                            }
                        ]
                    }
                },
            )
        return httpx.Response(
            200,
            text='stockts({"code":0,"result":{"cmsArticleWebOld":[]}})',
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = PublicMarketProvider(client)
        periods = await provider.fetch_financial_periods("SH.600519", 5)
        news = await provider.fetch_stock_news("SH.600519", "贵州茅台", 20)

    assert periods[0].report_label == "2026中报"
    assert news == []
    assert requests[0].url.params["reportName"] == "RPT_F10_FINANCE_MAINFINADATA"
    assert requests[0].url.params["filter"] == '(SECUCODE="600519.SH")'
    assert '"keyword":"贵州茅台"' in requests[1].url.params["param"]


@pytest.mark.asyncio
async def test_eastmoney_returns_bounded_ten_day_equity_ranking() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "data": {
                    "diff": [
                        {
                            "f12": "300862",
                            "f14": "蓝盾光电",
                            "f2": 47.29,
                            "f3": 19.99,
                            "f160": 148.76,
                        },
                        {
                            "f12": "300615",
                            "f14": "欣天科技",
                            "f2": 17.62,
                            "f3": 1.85,
                            "f160": 102.76,
                        },
                    ]
                }
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await PublicMarketProvider(client).fetch_equity_period_ranking(10, 100)

    assert result.columns == ["股票代码", "股票简称", "近10日涨跌幅", "最新价", "今日涨跌幅"]
    assert result.rows[0] == {
        "股票代码": "300862",
        "股票简称": "蓝盾光电",
        "近10日涨跌幅": 148.76,
        "最新价": 47.29,
        "今日涨跌幅": 19.99,
    }
    assert requests[0].url.params["fid"] == "f160"
    assert requests[0].url.params["pz"] == "100"
    assert "f160" in requests[0].url.params["fields"]


@pytest.mark.asyncio
async def test_eastmoney_json_falls_back_to_curl_when_httpx_disconnects(monkeypatch) -> None:
    class BrokenClient:
        async def get(self, *args, **kwargs):
            raise httpx.RemoteProtocolError("Server disconnected without sending a response.")

    def fake_run(*args, **kwargs):
        return SimpleNamespace(
            stdout='{"data":{"diff":[{"f12":"BK1380","f14":"水力发电","f3":3.28,"f62":161979008.0}]}}'
        )

    monkeypatch.setattr("marketdesk.providers.public_market.subprocess.run", fake_run)

    payload = await PublicMarketProvider(BrokenClient())._get_eastmoney_json({"pn": 1})

    assert payload["data"]["diff"][0]["f14"] == "水力发电"


def test_tencent_quotes_and_kline_normalize() -> None:
    quotes = 'v_sh000001="1~上证指数~000001~3764.15~3882.41~3865.32~650450984~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~~20260717161402~-118.26~-3.05~3869.21~3745.17~3764.15/650450984/1246445452836";'
    kline = {
        "data": {"sh600519": {"qfqday": [["2026-07-17", "1180", "1190", "1200", "1170", "50000"]]}}
    }

    provider = PublicMarketProvider()
    indices = provider.normalize_indices(quotes)
    bars = provider.normalize_kline(kline, "SH.600519")

    assert indices[0].symbol == "SH.000001"
    assert indices[0].change_pct == -3.05
    assert bars[0].close == 1190


def test_weekend_observation_uses_previous_market_close() -> None:
    sunday = datetime(2026, 7, 19, 8, tzinfo=UTC)

    observed = _market_observed_at(sunday)

    assert observed == datetime(2026, 7, 17, 7, tzinfo=UTC)


@pytest.mark.asyncio
async def test_market_events_fall_back_to_cls_when_eastmoney_is_unavailable() -> None:
    class BrokenEastmoneyClient:
        async def get(self, *args, **kwargs):
            raise httpx.ConnectError("eastmoney unavailable")

    class ClsFallback:
        async def fetch_cls_events(self, limit: int):
            from marketdesk.models import MarketEventRaw

            return [
                MarketEventRaw(
                    id="cls:1",
                    title="财联社备源事件",
                    summary="主源不可用时仍保留独立事件来源。",
                    source="财联社电报",
                    url="https://www.cls.cn/detail/1",
                    published_at=datetime.now(UTC),
                )
            ][:limit]

        def provider_status(self):
            return {"cls_fast_news": {"status": "ready", "required": False}}

    provider = PublicMarketProvider(BrokenEastmoneyClient())
    provider.evidence_provider = ClsFallback()

    events = await provider.fetch_market_events(10)

    assert events[0].source == "财联社电报"
    assert provider.provider_status()["eastmoney_fast_news"]["status"] == "partial"
    assert provider.provider_status()["cls_fast_news"]["status"] == "ready"


def test_global_provider_normalizes_tencent_search_quote_and_kline() -> None:
    from marketdesk.providers.global_market import GlobalMarketProvider

    provider = GlobalMarketProvider()
    search_text = 'v_hint="hk~00700~腾讯控股~txkg~GP^us~aapl.oq~苹果~pg~GP^jj~007005~基金~jj~KJ"'
    quote_text = 'v_hk00700="100~腾讯控股~00700~485.800~490.400~491.000~22450645.0~0~0~485.800~0~0~0~0~0~0~0~0~0~485.800~0~0~0~0~0~0~0~0~0~22450645.0~2026/08/04 15:39:08~-4.600~-0.94~494.800~480.800~485.800~22450645.0~10916258976.780~0~17.74~~0~0~2.85~44171.4441~44171.4441~TENCENT";'
    kline = {
        "data": {
            "hk00700": {
                "qfqday": [["2026-08-04", "491.0", "485.8", "494.8", "480.8", "22450645", {}, "0.25", "1091625.9"]]
            }
        }
    }
    us_text = '/*<script>location.href=\'//sina.com\';</script>*/\nvar _([{"d":"2026-08-03","o":"309.58","h":"311.80","l":"302.56","c":"303.42","v":"75051951","a":"0"}]);'

    assert provider.normalize_tencent_search(search_text) == ["HK.00700", "US.AAPL"]
    quote = provider.normalize_tencent_quote(quote_text, "HK.700")
    assert quote.symbol == "HK.00700"
    assert quote.name == "腾讯控股"
    assert quote.price == 485.8
    assert quote.change_pct == -0.94
    assert quote.sector == "港股/HKD"
    assert provider.normalize_tencent_kline(kline, "hk00700")[0].close == 485.8
    assert provider.normalize_sina_us_kline(us_text)[0].close == 303.42
