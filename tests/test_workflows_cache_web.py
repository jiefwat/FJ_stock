from pathlib import Path

from stock_ts.cache import JsonCacheStore
from stock_ts.providers.base import DataProviderError
from stock_ts.providers.sample import SampleDataProvider
from stock_ts.web import render_error_page, render_page
from stock_ts.workflows import (
    build_candidate_report,
    build_daily_report,
    build_market_report,
    build_portfolio_report,
    build_sector_report,
    build_stock_report,
)


class FailingProvider(SampleDataProvider):
    def fetch_market(self):  # type: ignore[no-untyped-def]
        raise DataProviderError("sample failure for page")


def test_workflows_build_core_reports_from_same_provider() -> None:
    provider = SampleDataProvider()

    market = build_market_report(provider)
    sectors = build_sector_report(provider, market=market)
    candidates = build_candidate_report(provider, market=market, sectors=sectors, limit=20)
    portfolio = build_portfolio_report(
        provider,
        holdings_path="data/portfolio/holdings.csv",
        market=market,
    )
    stock = build_stock_report(provider, "600519")
    daily = build_daily_report(
        provider,
        holdings_path="data/portfolio/holdings.csv",
        candidate_limit=20,
    )

    assert market.heat_score > 0
    assert sectors.sectors
    assert len(candidates.candidates) == 20
    assert portfolio.total_market_value > 0
    assert stock.code == "600519"
    assert daily.market.trade_date == market.trade_date
    assert daily.markdown.startswith("# StockTS 每日复盘")
    assert "最需要关注的 3 件事" in daily.markdown


def test_render_page_handles_provider_error_with_readable_error_page() -> None:
    html = render_page(provider=FailingProvider())

    assert "系统暂时无法生成复盘" in html
    assert "sample failure for page" in html
    assert "Web 页面固定使用 TDX MCP 快照" in html
    assert "不构成投资建议" in html


def test_render_page_accepts_provider_and_holdings_query_values() -> None:
    html = render_page(
        stock_code="000001", provider_name="sample", holdings_path="data/portfolio/holdings.csv"
    )

    assert "数据源" in html
    assert "TDX MCP" in html
    assert "请求数据源" not in html
    assert "000001" in html
    assert 'id="workspace-market"' in html
    assert 'id="module-market"' in html


def test_render_page_accepts_empty_holdings_file(tmp_path: Path) -> None:
    holdings_path = tmp_path / "holdings.csv"
    holdings_path.write_text("code,name,shares,cost_price,sector,note\n", encoding="utf-8")

    html = render_page(
        stock_code="600519",
        provider_name="sample",
        provider=SampleDataProvider(),
        holdings_path=str(holdings_path),
    )

    assert "系统暂时无法生成复盘" not in html
    assert "持仓 0 只" in html
    assert "还没有持仓" in html
    assert "添加持仓" in html


def test_json_cache_store_roundtrips_payload_with_metadata(tmp_path: Path) -> None:
    cache = JsonCacheStore(tmp_path)
    payload = {"code": "600519", "close": 1586.0}

    cache.write_json("stock/600519", payload, source="sample", trade_date="2026-06-05")
    entry = cache.read_json("stock/600519")

    assert entry is not None
    assert entry.payload == payload
    assert entry.metadata["source"] == "sample"
    assert entry.metadata["trade_date"] == "2026-06-05"
    assert (tmp_path / "stock" / "600519.json").exists()


def test_render_error_page_contains_next_steps() -> None:
    html = render_error_page("AKShare 缺少依赖", provider_name="akshare")

    assert "AKShare 缺少依赖" in html
    assert "data/imports/tdx_snapshots.json" in html
    assert "TDX MCP" in html
