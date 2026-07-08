from __future__ import annotations

import argparse
from pathlib import Path

from .announcements import fetch_cninfo_announcements, render_announcement_markdown
from .backtest import backtest_moving_average, render_backtest_markdown
from .config import get_settings
from .deep_report import render_batch_markdown, render_deep_stock_markdown
from .html_report import render_batch_html, render_daily_deep_html, render_deep_stock_html
from .imports import load_price_bars_csv
from .llm import generate_stock_ai_insight
from .news import analyze_news
from .news_fetcher import fetch_akshare_stock_news
from .notification import dispatch_report
from .output import write_optional_text
from .professional_research import (
    build_event_radar,
    build_technical_profile,
    render_professional_appendix,
)
from .providers import create_provider
from .providers.akshare_provider import AkshareProvider
from .report import render_news_markdown
from .symbols import resolve_stock_query
from .trade_plan import build_trade_plan, render_trade_plan_markdown
from .watchlist import build_watchlist_report, render_watchlist_markdown
from .workflows import (
    build_batch_report,
    build_candidate_markdown,
    build_daily_deep_report,
    build_daily_report,
    build_deep_stock_report,
    build_imported_stock_markdown,
    build_market_markdown,
    build_news_markdown,
    build_portfolio_markdown,
    build_sector_markdown,
    build_stock_markdown,
    run_doctor,
)

PROVIDER_CHOICES = ["sample", "tencent", "eltdx", "auto", "akshare", "tushare", "tdx-snapshot"]
NOTIFICATION_STYLE_CHOICES = ["auto", "full", "digest", "action"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="stock-ts", description="A-share market and stock analysis"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    market = subparsers.add_parser("market", help="Generate daily market analysis")
    market.add_argument("--provider", default="sample", choices=PROVIDER_CHOICES)
    market.add_argument("--output", help="Write markdown report to this path")

    stock = subparsers.add_parser("stock", help="Generate single stock analysis")
    stock.add_argument("code", help="A-share code, e.g. 600519")
    stock.add_argument("--provider", default="sample", choices=PROVIDER_CHOICES)
    stock.add_argument("--output", help="Write markdown report to this path")

    stock_deep = subparsers.add_parser(
        "stock-deep",
        help="Generate multi-angle single stock deep analysis with debate",
    )
    stock_deep.add_argument("code", help="A-share code, e.g. 600519")
    stock_deep.add_argument("--provider", default="sample", choices=PROVIDER_CHOICES)
    stock_deep.add_argument("--html", help="Write standalone HTML conclusion report")
    stock_deep.add_argument("--output", help="Write markdown report to this path")

    research = subparsers.add_parser(
        "research",
        help="Generate professional single-stock pack with technical levels and CNInfo events",
    )
    research.add_argument("code", help="A-share code or name, e.g. 大业股份")
    research.add_argument("--provider", default="auto", choices=PROVIDER_CHOICES)
    research.add_argument("--announcements", type=int, default=5)
    research.add_argument("--output", help="Write markdown report to this path")

    ai_insight = subparsers.add_parser(
        "ai-insight",
        help="Generate optional LLM-enhanced stock insight",
    )
    ai_insight.add_argument("code", help="A-share code, e.g. 600519")
    ai_insight.add_argument("--provider", default="sample", choices=PROVIDER_CHOICES)
    ai_insight.add_argument("--output", help="Write markdown report to this path")

    batch = subparsers.add_parser("batch", help="Generate batch deep comparison")
    batch.add_argument("codes", help="Comma separated codes, e.g. 600519,000001,300750")
    batch.add_argument("--provider", default="sample", choices=PROVIDER_CHOICES)
    batch.add_argument("--html", help="Write standalone HTML comparison report")
    batch.add_argument("--output", help="Write markdown report to this path")

    watchlist = subparsers.add_parser(
        "watchlist",
        help="Generate watchlist research workspace",
    )
    watchlist.add_argument("input", help="YAML-like watchlist file")
    watchlist.add_argument("--provider", default="sample", choices=PROVIDER_CHOICES)
    watchlist.add_argument("--output", help="Write markdown report to this path")

    backtest = subparsers.add_parser(
        "backtest",
        help="Run a lightweight moving-average backtest from local price CSV",
    )
    backtest.add_argument("input", help="CSV with date,open,high,low,close,volume columns")
    backtest.add_argument("--code", required=True)
    backtest.add_argument("--name", help="Stock name for report display")
    backtest.add_argument("--fast", type=int, default=5)
    backtest.add_argument("--slow", type=int, default=20)
    backtest.add_argument("--initial-cash", type=float, default=100000.0)
    backtest.add_argument("--output", help="Write markdown report to this path")

    imported = subparsers.add_parser("import-prices", help="Analyze locally imported price CSV")
    imported.add_argument("input", help="CSV with date,open,high,low,close,volume columns")
    imported.add_argument("--code", required=True, help="Stock code for the imported bars")
    imported.add_argument("--name", help="Stock name for report display")
    imported.add_argument("--output", help="Write markdown report to this path")

    news = subparsers.add_parser("news", help="Render locally imported news/sentiment CSV")
    news.add_argument("input", help="CSV with date,source,title,summary,url,sentiment columns")
    news.add_argument("--output", help="Write markdown report to this path")

    fetch_news = subparsers.add_parser(
        "fetch-news",
        help="Fetch stock news and render sentiment summary",
    )
    fetch_news.add_argument("symbol", help="Stock code or keyword, e.g. 600519")
    fetch_news.add_argument("--provider", default="akshare", choices=["akshare"])
    fetch_news.add_argument("--limit", type=int, default=20)
    fetch_news.add_argument("--output", help="Write markdown report to this path")

    announcements = subparsers.add_parser(
        "announcements",
        help="Fetch CNInfo announcements and render event/risk summary",
    )
    announcements.add_argument("symbol", help="Stock code or name, e.g. 603278")
    announcements.add_argument("--limit", type=int, default=10)
    announcements.add_argument("--output", help="Write markdown report to this path")

    sectors = subparsers.add_parser("sectors", help="Generate daily sector analysis")
    sectors.add_argument("--provider", default="sample", choices=PROVIDER_CHOICES)
    sectors.add_argument("--output", help="Write markdown report to this path")

    candidates = subparsers.add_parser("candidates", help="Generate next-day watch candidates")
    candidates.add_argument("--provider", default="sample", choices=PROVIDER_CHOICES)
    candidates.add_argument("--limit", type=int, default=20)
    candidates.add_argument("--output", help="Write markdown report to this path")

    doctor = subparsers.add_parser("doctor", help="Run local StockTS health checks")
    doctor.add_argument("--provider", default="sample", choices=PROVIDER_CHOICES)
    doctor.add_argument("--output", help="Write markdown report to this path")

    portfolio = subparsers.add_parser("portfolio", help="Generate daily portfolio analysis")
    portfolio.add_argument("--provider", default="sample", choices=PROVIDER_CHOICES)
    portfolio.add_argument("--holdings", default="data/portfolio/holdings.csv")
    portfolio.add_argument("--transactions", help="Build holdings from transaction ledger CSV")
    portfolio.add_argument("--output", help="Write markdown report to this path")

    daily = subparsers.add_parser("daily", help="Generate full daily report")
    daily.add_argument("--provider", default="sample", choices=PROVIDER_CHOICES)
    daily.add_argument("--holdings", default="data/portfolio/holdings.csv")
    daily.add_argument("--transactions", help="Build holdings from transaction ledger CSV")
    daily.add_argument("--news", help="Optional local news/sentiment CSV")
    daily.add_argument("--candidate-limit", type=int, default=20)
    daily.add_argument("--cache-dir", help="Cache daily markdown under this directory")
    daily.add_argument("--refresh", action="store_true", help="Ignore cached daily markdown")
    daily.add_argument("--output", help="Write markdown report to this path")

    daily_deep = subparsers.add_parser(
        "daily-deep",
        help="Generate daily deep market/sector/portfolio/news report",
    )
    daily_deep.add_argument("--provider", default="sample", choices=PROVIDER_CHOICES)
    daily_deep.add_argument("--holdings", default="data/portfolio/holdings.csv")
    daily_deep.add_argument("--transactions", help="Build holdings from transaction ledger CSV")
    daily_deep.add_argument("--news", help="Optional local news/sentiment CSV")
    daily_deep.add_argument("--candidate-limit", type=int, default=20)
    daily_deep.add_argument("--focus", help="Optional comma separated stock codes for deep section")
    daily_deep.add_argument("--html", help="Write standalone HTML conclusion report")
    daily_deep.add_argument("--output", help="Write markdown report to this path")

    send_daily = subparsers.add_parser("send-daily", help="Generate daily report and send it")
    send_daily.add_argument("--provider", default="sample", choices=PROVIDER_CHOICES)
    send_daily.add_argument("--holdings", default="data/portfolio/holdings.csv")
    send_daily.add_argument("--transactions", help="Build holdings from transaction ledger CSV")
    send_daily.add_argument("--news", help="Optional local news/sentiment CSV")
    send_daily.add_argument("--candidate-limit", type=int, default=20)
    send_daily.add_argument(
        "--channels",
        default="",
        help="Comma separated channels; empty uses NOTIFICATION_REPORT_CHANNELS",
    )
    send_daily.add_argument("--style", default="auto", choices=NOTIFICATION_STYLE_CHOICES)
    send_daily.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned sends without sending",
    )
    send_daily.add_argument("--output", help="Write generated markdown report to this path")

    test_notify = subparsers.add_parser("test-notify", help="Send a notification test message")
    test_notify.add_argument("--channel", required=True)
    test_notify.add_argument("--subject", default="StockTS 通知测试")
    test_notify.add_argument("--content", default="这是一条测试消息，用于验证渠道配置是否可用。")
    test_notify.add_argument("--style", default="auto", choices=NOTIFICATION_STYLE_CHOICES)
    test_notify.add_argument("--dry-run", action="store_true")
    return parser


def write_or_print(markdown: str, output: str | None) -> None:
    path = write_optional_text(markdown, output)
    if path is not None:
        print(str(path))
        return
    print(markdown, end="")


def write_html(html: str, output: str | None) -> None:
    write_optional_text(html, output)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    provider = (
        create_provider(args.provider)
        if hasattr(args, "provider") and args.command != "fetch-news"
        else None
    )

    if args.command == "market":
        assert provider is not None
        write_or_print(build_market_markdown(provider).markdown, args.output)
        return 0
    if args.command == "stock":
        assert provider is not None
        write_or_print(build_stock_markdown(provider, args.code).markdown, args.output)
        return 0
    if args.command == "stock-deep":
        assert provider is not None
        report = build_deep_stock_report(provider, args.code)
        write_html(render_deep_stock_html(report), args.html)
        write_or_print(render_deep_stock_markdown(report), args.output)
        return 0
    if args.command == "research":
        assert provider is not None
        resolved = resolve_stock_query(args.code)
        raw = provider.fetch_stock(resolved.code)
        technical = build_technical_profile(raw)
        try:
            announcements = fetch_cninfo_announcements(resolved.code, limit=args.announcements)
        except Exception:
            announcements = None
        event_radar = build_event_radar(announcements)
        report = build_deep_stock_report(provider, resolved.code)
        plan = build_trade_plan(
            stock_name=report.name,
            latest_close=report.latest_close,
            upside_score=report.upside.score,
            risk_level=report.risk_level,
            trend=report.trend,
            technical=technical,
            event_radar=event_radar,
            data_quality_warnings=[],
        )
        markdown = (
            render_deep_stock_markdown(report).strip()
            + "\n\n"
            + render_trade_plan_markdown(plan).strip()
            + "\n\n"
            + render_professional_appendix(technical, event_radar, announcements)
        )
        write_or_print(markdown, args.output)
        return 0
    if args.command == "ai-insight":
        assert provider is not None
        report = build_deep_stock_report(provider, args.code)
        insight = generate_stock_ai_insight(report)
        write_or_print(insight.markdown, args.output)
        return 0
    if args.command == "batch":
        assert provider is not None
        codes = [item.strip() for item in args.codes.split(",") if item.strip()]
        report = build_batch_report(provider, codes)
        write_html(render_batch_html(report), args.html)
        write_or_print(render_batch_markdown(report), args.output)
        return 0
    if args.command == "watchlist":
        assert provider is not None
        report = build_watchlist_report(provider, args.input)
        write_or_print(render_watchlist_markdown(report), args.output)
        return 0
    if args.command == "backtest":
        report = backtest_moving_average(
            args.code,
            args.name or args.code,
            load_price_bars_csv(args.input),
            fast_window=args.fast,
            slow_window=args.slow,
            initial_cash=args.initial_cash,
        )
        write_or_print(render_backtest_markdown(report), args.output)
        return 0
    if args.command == "import-prices":
        write_or_print(
            build_imported_stock_markdown(args.input, code=args.code, name=args.name).markdown,
            args.output,
        )
        return 0
    if args.command == "news":
        write_or_print(build_news_markdown(args.input).markdown, args.output)
        return 0
    if args.command == "fetch-news":
        ak_provider = AkshareProvider()
        items = fetch_akshare_stock_news(ak_provider._ak, symbol=args.symbol, limit=args.limit)
        markdown = render_news_markdown(analyze_news(items))
        write_or_print(markdown, args.output)
        return 0
    if args.command == "announcements":
        report = fetch_cninfo_announcements(args.symbol, limit=args.limit)
        write_or_print(render_announcement_markdown(report), args.output)
        return 0
    if args.command == "sectors":
        assert provider is not None
        write_or_print(build_sector_markdown(provider).markdown, args.output)
        return 0
    if args.command == "candidates":
        assert provider is not None
        write_or_print(build_candidate_markdown(provider, limit=args.limit).markdown, args.output)
        return 0
    if args.command == "doctor":
        assert provider is not None
        write_or_print(run_doctor(provider, provider_name=args.provider).markdown, args.output)
        return 0
    if args.command == "portfolio":
        assert provider is not None
        write_or_print(
            build_portfolio_markdown(
                provider,
                holdings_path=None if args.transactions else args.holdings,
                transactions_path=args.transactions,
            ).markdown,
            args.output,
        )
        return 0
    if args.command == "daily":
        assert provider is not None
        daily = build_daily_report(
            provider,
            holdings_path=None if args.transactions else args.holdings,
            transactions_path=args.transactions,
            news_path=args.news,
            candidate_limit=args.candidate_limit,
            cache_dir=args.cache_dir,
            refresh=args.refresh,
            provider_name=args.provider,
        )
        write_or_print(daily.markdown, args.output)
        return 0
    if args.command == "daily-deep":
        assert provider is not None
        focus_codes = (
            [item.strip() for item in args.focus.split(",") if item.strip()] if args.focus else None
        )
        daily = build_daily_deep_report(
            provider,
            holdings_path=None if args.transactions else args.holdings,
            transactions_path=args.transactions,
            news_path=args.news,
            candidate_limit=args.candidate_limit,
            focus_codes=focus_codes,
            provider_name=args.provider,
        )
        write_html(render_daily_deep_html(daily), args.html)
        write_or_print(daily.markdown, args.output)
        return 0
    if args.command == "send-daily":
        assert provider is not None
        daily = build_daily_report(
            provider,
            holdings_path=None if args.transactions else args.holdings,
            transactions_path=args.transactions,
            news_path=args.news,
            candidate_limit=args.candidate_limit,
            provider_name=args.provider,
        )
        if args.output:
            Path(args.output).parent.mkdir(parents=True, exist_ok=True)
            Path(args.output).write_text(daily.markdown, encoding="utf-8")
        settings = get_settings()
        configured_channels = settings.notification_report_channels or ["email", "wechat"]
        channels = (
            [item.strip() for item in args.channels.split(",") if item.strip()]
            if args.channels.strip()
            else configured_channels
        )
        result = dispatch_report(
            daily.markdown,
            channels=channels,
            subject=f"StockTS 早间复盘与机会（{daily.market.trade_date}）",
            dry_run=args.dry_run,
            style=args.style,
        )
        print(result.markdown, end="")
        return 0 if result.ok else 2
    if args.command == "test-notify":
        result = dispatch_report(
            args.content,
            channels=[args.channel],
            subject=args.subject,
            dry_run=args.dry_run,
            style=args.style,
        )
        print(result.markdown, end="")
        return 0 if result.ok else 2
    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
