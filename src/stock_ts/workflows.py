from __future__ import annotations

from dataclasses import dataclass
from importlib.util import find_spec
from pathlib import Path

from .analysis import (
    analyze_candidates,
    analyze_market,
    analyze_portfolio,
    analyze_sectors,
    analyze_stock,
)
from .cache import JsonCacheStore
from .config import get_settings
from .deep_analysis import (
    analyze_batch_stocks,
    analyze_deep_stock,
)
from .deep_models import (
    BatchAnalysisReport,
    DailyDeepReport,
    DeepStockReport,
)
from .deep_report import (
    render_batch_markdown,
    render_daily_deep_markdown,
    render_deep_stock_markdown,
)
from .imports import load_news_csv, load_price_bars_csv
from .models import (
    CandidatePoolReport,
    MarketSnapshot,
    NewsItem,
    NewsSentimentReport,
    PortfolioAnalysisReport,
    SectorAnalysisReport,
    StockAnalysisReport,
    StockRawData,
)
from .news import analyze_news
from .portfolio import load_portfolio_source
from .portfolio_advice import build_portfolio_advice, render_portfolio_advice_markdown
from .providers.base import StockDataProvider
from .providers.eltdx_provider import is_eltdx_bridge_available
from .report import (
    render_candidate_pool_markdown,
    render_daily_markdown,
    render_market_markdown,
    render_news_markdown,
    render_portfolio_markdown,
    render_sector_markdown,
    render_stock_markdown,
)
from .symbols import resolve_stock_query


@dataclass(frozen=True)
class MarkdownReport:
    title: str
    markdown: str


@dataclass(frozen=True)
class DailyWorkflowResult:
    market: MarketSnapshot
    sectors: SectorAnalysisReport
    portfolio: PortfolioAnalysisReport | None
    candidates: CandidatePoolReport
    markdown: str
    news: NewsSentimentReport | None = None
    cache_hit: bool = False


@dataclass(frozen=True)
class DoctorItem:
    name: str
    ok: bool
    detail: str


@dataclass(frozen=True)
class DoctorReport:
    ok: bool
    items: list[DoctorItem]
    markdown: str


def build_market_report(provider: StockDataProvider) -> MarketSnapshot:
    return analyze_market(provider.fetch_market())


def build_market_markdown(provider: StockDataProvider) -> MarkdownReport:
    market = build_market_report(provider)
    return MarkdownReport(title="每日大盘分析", markdown=render_market_markdown(market))


def build_sector_report(
    provider: StockDataProvider,
    *,
    market: MarketSnapshot | None = None,
) -> SectorAnalysisReport:
    market = market or build_market_report(provider)
    return analyze_sectors(provider.fetch_sectors(), trade_date=market.trade_date)


def build_sector_markdown(provider: StockDataProvider) -> MarkdownReport:
    market = build_market_report(provider)
    sectors = build_sector_report(provider, market=market)
    return MarkdownReport(title="每日板块情况", markdown=render_sector_markdown(sectors))


def build_candidate_report(
    provider: StockDataProvider,
    *,
    market: MarketSnapshot | None = None,
    sectors: SectorAnalysisReport | None = None,
    limit: int = 20,
) -> CandidatePoolReport:
    market = market or build_market_report(provider)
    sectors = sectors or build_sector_report(provider, market=market)
    return analyze_candidates(provider.fetch_candidate_universe(), sectors, market, limit=limit)


def build_candidate_markdown(provider: StockDataProvider, *, limit: int = 20) -> MarkdownReport:
    market = build_market_report(provider)
    sectors = build_sector_report(provider, market=market)
    candidates = build_candidate_report(provider, market=market, sectors=sectors, limit=limit)
    return MarkdownReport(
        title="候选股票池",
        markdown=render_candidate_pool_markdown(candidates),
    )


def build_stock_report(provider: StockDataProvider, code: str) -> StockAnalysisReport:
    resolved = resolve_stock_query(code)
    return analyze_stock(provider.fetch_stock(resolved.code))


def build_stock_markdown(provider: StockDataProvider, code: str) -> MarkdownReport:
    stock = build_stock_report(provider, code)
    return MarkdownReport(title=f"个股分析：{stock.name}", markdown=render_stock_markdown(stock))


def build_deep_stock_report(
    provider: StockDataProvider,
    code: str,
    *,
    market: MarketSnapshot | None = None,
    sectors: SectorAnalysisReport | None = None,
    news: NewsSentimentReport | None = None,
    portfolio: PortfolioAnalysisReport | None = None,
    stock: StockAnalysisReport | None = None,
) -> DeepStockReport:
    market = market or build_market_report(provider)
    sectors = sectors or build_sector_report(provider, market=market)
    raw: StockRawData | None = None
    if stock is None or news is None:
        resolved = resolve_stock_query(code)
        raw = provider.fetch_stock(resolved.code)
    if stock is None:
        if raw is None:
            raise RuntimeError("stock raw data is required for latest stock analysis")
        stock = analyze_stock(raw)
    if news is None and raw is not None and raw.news_items:
        news = analyze_news(raw.news_items, trade_date=market.trade_date)
    return analyze_deep_stock(
        stock,
        market=market,
        sectors=sectors,
        news=news,
        portfolio=portfolio,
    )


def build_deep_stock_markdown(
    provider: StockDataProvider,
    code: str,
) -> MarkdownReport:
    report = build_deep_stock_report(provider, code)
    return MarkdownReport(
        title=f"深度个股分析：{report.name}",
        markdown=render_deep_stock_markdown(report),
    )


def build_batch_report(
    provider: StockDataProvider,
    codes: list[str],
) -> BatchAnalysisReport:
    if not codes:
        raise ValueError("codes cannot be empty")
    market = build_market_report(provider)
    sectors = build_sector_report(provider, market=market)
    reports = [
        build_deep_stock_report(provider, code, market=market, sectors=sectors) for code in codes
    ]
    return analyze_batch_stocks(reports, market=market, sectors=sectors)


def build_batch_markdown(provider: StockDataProvider, codes: list[str]) -> MarkdownReport:
    report = build_batch_report(provider, codes)
    return MarkdownReport(title="批量个股深度对比", markdown=render_batch_markdown(report))


def build_imported_stock_markdown(
    price_path: str | Path,
    *,
    code: str,
    name: str | None = None,
) -> MarkdownReport:
    bars = load_price_bars_csv(price_path)
    stock = analyze_stock(StockRawData(code=code, name=name or code, bars=bars))
    return MarkdownReport(
        title=f"导入行情分析：{stock.name}",
        markdown=render_stock_markdown(stock),
    )


def build_news_report(
    news_path: str | Path,
    *,
    trade_date: str | None = None,
) -> NewsSentimentReport:
    return analyze_news(load_news_csv(news_path), trade_date=trade_date)


def _provider_news_report(
    provider: StockDataProvider, *, trade_date: str
) -> NewsSentimentReport | None:
    fetcher = getattr(provider, "fetch_market_news", None)
    if not callable(fetcher):
        return None
    try:
        items = [item for item in fetcher() if isinstance(item, NewsItem) and item.title]
    except Exception:
        return None
    if not items:
        return None
    return analyze_news(items, trade_date=trade_date)


def build_news_markdown(news_path: str | Path, *, trade_date: str | None = None) -> MarkdownReport:
    news = build_news_report(news_path, trade_date=trade_date)
    return MarkdownReport(title="新闻舆情摘要", markdown=render_news_markdown(news))


def build_portfolio_report(
    provider: StockDataProvider,
    *,
    holdings_path: str | Path | None = None,
    transactions_path: str | Path | None = None,
    market: MarketSnapshot | None = None,
    allow_empty: bool = False,
) -> PortfolioAnalysisReport:
    market = market or build_market_report(provider)
    holdings = load_portfolio_source(
        holdings_path=holdings_path,
        transactions_path=transactions_path,
        allow_empty=allow_empty,
    )
    return analyze_portfolio(holdings, provider, market)


def build_portfolio_markdown(
    provider: StockDataProvider,
    *,
    holdings_path: str | Path | None = None,
    transactions_path: str | Path | None = None,
) -> MarkdownReport:
    market = build_market_report(provider)
    portfolio = build_portfolio_report(
        provider,
        holdings_path=holdings_path,
        transactions_path=transactions_path,
        market=market,
    )
    advice = build_portfolio_advice(
        portfolio,
        market=market,
        holdings_path=str(holdings_path or "data/portfolio/holdings.csv"),
        transactions_path=str(transactions_path or "data/portfolio/transactions.csv"),
    )
    markdown = (
        render_portfolio_markdown(portfolio).strip()
        + "\n\n"
        + render_portfolio_advice_markdown(advice)
    )
    return MarkdownReport(title="每日持仓分析", markdown=markdown)


def build_daily_report(
    provider: StockDataProvider,
    *,
    holdings_path: str | Path | None = None,
    transactions_path: str | Path | None = None,
    news_path: str | Path | None = None,
    candidate_limit: int = 20,
    cache_dir: str | Path | None = None,
    refresh: bool = False,
    provider_name: str = "sample",
    allow_empty_portfolio: bool = False,
) -> DailyWorkflowResult:
    market = build_market_report(provider)
    sectors = build_sector_report(provider, market=market)
    candidates = build_candidate_report(
        provider, market=market, sectors=sectors, limit=candidate_limit
    )
    portfolio = None
    if holdings_path is not None or transactions_path is not None:
        portfolio = build_portfolio_report(
            provider,
            holdings_path=holdings_path,
            transactions_path=transactions_path,
            market=market,
            allow_empty=allow_empty_portfolio,
        )
    news = None
    if news_path is not None:
        news = build_news_report(news_path, trade_date=market.trade_date)
    else:
        news = _provider_news_report(provider, trade_date=market.trade_date)

    cache = JsonCacheStore(cache_dir) if cache_dir is not None else None
    cache_key = f"reports/daily-{provider_name}-{market.trade_date}"
    if cache is not None and not refresh:
        cached = cache.read_json(cache_key)
        cached_markdown = cached.payload.get("markdown") if cached else None
        if isinstance(cached_markdown, str):
            return DailyWorkflowResult(
                market=market,
                sectors=sectors,
                portfolio=portfolio,
                candidates=candidates,
                markdown=cached_markdown,
                news=news,
                cache_hit=True,
            )

    markdown = render_daily_markdown(
        market,
        portfolio,
        sectors=sectors,
        candidates=candidates,
        news=news,
    )
    if cache is not None:
        cache.write_json(
            cache_key,
            {"markdown": markdown},
            source=provider_name,
            trade_date=market.trade_date,
        )
    return DailyWorkflowResult(
        market=market,
        sectors=sectors,
        portfolio=portfolio,
        candidates=candidates,
        markdown=markdown,
        news=news,
        cache_hit=False,
    )


def build_daily_deep_report(
    provider: StockDataProvider,
    *,
    holdings_path: str | Path | None = None,
    transactions_path: str | Path | None = None,
    news_path: str | Path | None = None,
    candidate_limit: int = 20,
    focus_codes: list[str] | None = None,
    provider_name: str = "sample",
) -> DailyDeepReport:
    daily = build_daily_report(
        provider,
        holdings_path=holdings_path,
        transactions_path=transactions_path,
        news_path=news_path,
        candidate_limit=candidate_limit,
        provider_name=provider_name,
    )
    codes = focus_codes or []
    if not codes and daily.portfolio is not None:
        codes = [position.holding.code for position in daily.portfolio.positions[:5]]
    if not codes:
        codes = [
            candidate.code for candidate in daily.candidates.candidates[: min(5, candidate_limit)]
        ]
    stocks = [
        build_deep_stock_report(
            provider,
            code,
            market=daily.market,
            sectors=daily.sectors,
            news=daily.news,
            portfolio=daily.portfolio,
        )
        for code in codes
    ]
    report = DailyDeepReport(
        trade_date=daily.market.trade_date,
        market=daily.market,
        sectors=daily.sectors,
        candidates=daily.candidates,
        stocks=stocks,
        portfolio=daily.portfolio,
        news=daily.news,
        markdown=daily.markdown,
    )
    return DailyDeepReport(
        trade_date=report.trade_date,
        market=report.market,
        sectors=report.sectors,
        candidates=report.candidates,
        stocks=report.stocks,
        portfolio=report.portfolio,
        news=report.news,
        markdown=render_daily_deep_markdown(report),
    )


def run_doctor(provider: StockDataProvider, *, provider_name: str = "sample") -> DoctorReport:
    settings = get_settings()
    eltdx_ready = is_eltdx_bridge_available()
    items: list[DoctorItem] = [
        DoctorItem(
            "settings_provider",
            settings.provider == provider_name,
            f"settings={settings.provider}, active={provider_name}",
        ),
        DoctorItem("holdings_file", Path(settings.holdings_path).exists(), settings.holdings_path),
        DoctorItem("cache_dir", True, settings.cache_dir),
        DoctorItem(
            "Tushare token", settings.has_tushare_token, settings.safe_summary()["tushare_token"]
        ),
        DoctorItem(
            "iTick API Key",
            settings.has_itick_api_key,
            settings.safe_summary()["itick"],
        ),
        DoctorItem(
            "akshare_dependency",
            find_spec("akshare") is not None,
            "installed" if find_spec("akshare") else "missing",
        ),
        DoctorItem(
            "tushare_dependency",
            find_spec("tushare") is not None,
            "installed" if find_spec("tushare") else "missing",
        ),
        DoctorItem(
            "eltdx_bridge",
            eltdx_ready,
            "python3.11 bridge ready" if eltdx_ready else "python3.11 eltdx bridge missing",
        ),
        DoctorItem(
            "email_channel",
            bool(settings.email_sender and settings.email_password),
            settings.safe_summary()["email"],
        ),
        DoctorItem(
            "wechat_channel",
            bool(settings.wechat_webhook_url),
            settings.safe_summary()["wechat"],
        ),
        DoctorItem(
            "feishu_channel",
            bool(settings.feishu_webhook_url),
            settings.safe_summary()["feishu"],
        ),
        DoctorItem(
            "notification_report",
            bool(settings.notification_report_channels),
            (
                f"channels={','.join(settings.notification_report_channels or [])}; "
                f"style={settings.notification_report_style}"
            ),
        ),
        DoctorItem(
            "llm_channel",
            settings.has_llm_api_key,
            (f"{settings.safe_summary()['llm']} ({settings.llm_provider}/{settings.llm_model})"),
        ),
    ]
    try:
        daily = build_daily_report(
            provider,
            holdings_path=settings.holdings_path,
            candidate_limit=20,
            provider_name=provider_name,
        )
        items.append(DoctorItem("sample_daily_flow", True, f"trade_date={daily.market.trade_date}"))
    except Exception as exc:
        items.append(DoctorItem("sample_daily_flow", False, str(exc)))

    ok = all(item.ok for item in items if item.name in {"holdings_file", "sample_daily_flow"})
    lines = [
        "# StockTS 运行体检",
        "",
        "免责声明：本报告仅用于研究与复盘，不构成投资建议。",
        "",
        "## 检查结果",
    ]
    for item in items:
        mark = "OK" if item.ok else "WARN"
        lines.append(f"- {mark} {item.name}: {item.detail}")
    lines.extend(
        [
            "",
            "## 建议",
            "- sample_daily_flow 必须保持 OK，这是离线可用性的底线。",
            "- AKShare/Tushare 缺依赖不影响 sample 流程；真实数据源使用前再安装 data 依赖。",
            "- Tushare token 和 iTick API Key 只显示 configured/missing，不输出真实值。",
            "- LLM Key 只显示 configured/missing，不输出真实值；无 Key 时 AI 增强自动降级。",
        ]
    )
    return DoctorReport(ok=ok, items=items, markdown="\n".join(lines) + "\n")
