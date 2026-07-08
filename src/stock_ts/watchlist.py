from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .deep_analysis import analyze_batch_stocks
from .deep_models import BatchAnalysisReport, DeepStockReport
from .providers.base import StockDataProvider
from .report import DISCLAIMER
from .workflows import build_deep_stock_report, build_market_report, build_sector_report


@dataclass(frozen=True)
class WatchlistItem:
    code: str
    name: str = ""
    sector: str = ""
    tags: list[str] | None = None
    thesis: str = ""
    alert_price_below: float | None = None
    alert_price_above: float | None = None
    alert_score_below: int | None = None


@dataclass(frozen=True)
class Watchlist:
    stocks: list[WatchlistItem]


@dataclass(frozen=True)
class WatchlistAlert:
    code: str
    name: str
    level: str
    message: str


@dataclass(frozen=True)
class WatchlistReport:
    trade_date: str
    watchlist: Watchlist
    deep_reports: list[DeepStockReport]
    batch: BatchAnalysisReport
    alerts: list[WatchlistAlert]
    notes: list[str]
    disclaimer: str = DISCLAIMER


def load_watchlist(path: str | Path) -> Watchlist:
    text = Path(path).read_text(encoding="utf-8")
    stocks: list[WatchlistItem] = []
    current: dict[str, str] | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line == "stocks:":
            continue
        if line.startswith("- "):
            if current:
                stocks.append(_item_from_dict(current))
            current = {}
            line = line[2:].strip()
            if line:
                key, value = _split_key_value(line)
                current[key] = value
            continue
        if current is None:
            continue
        key, value = _split_key_value(line)
        current[key] = value
    if current:
        stocks.append(_item_from_dict(current))
    if not stocks:
        raise ValueError("watchlist must contain at least one stock")
    return Watchlist(stocks=stocks)


def build_watchlist_report(
    provider: StockDataProvider,
    path: str | Path,
) -> WatchlistReport:
    watchlist = load_watchlist(path)
    market = build_market_report(provider)
    sectors = build_sector_report(provider, market=market)
    deep_reports = [
        build_deep_stock_report(provider, item.code, market=market, sectors=sectors)
        for item in watchlist.stocks
    ]
    batch = analyze_batch_stocks(deep_reports, market=market, sectors=sectors)
    alerts = _build_alerts(watchlist.stocks, deep_reports)
    return WatchlistReport(
        trade_date=market.trade_date,
        watchlist=watchlist,
        deep_reports=deep_reports,
        batch=batch,
        alerts=alerts,
        notes=[
            "自选股工作台用于沉淀研究假设、标签和提醒条件，避免每天从零开始筛选。",
            "观察分下降或价格触发阈值只提示复盘，不代表自动买卖。",
            "建议配合 daily-deep 和 backtest 使用，形成研究、验证、跟踪闭环。",
        ],
    )


def render_watchlist_markdown(report: WatchlistReport) -> str:
    by_code = {item.code: item for item in report.deep_reports}
    lines = [
        f"# 自选股研究工作台（{report.trade_date}）",
        "",
        report.disclaimer,
        "",
        "## 自选股清单",
    ]
    for item in report.watchlist.stocks:
        deep = by_code.get(item.code)
        tags = "、".join(item.tags or []) or "未标注"
        score = f"{deep.upside.score}/100" if deep else "未分析"
        lines.append(
            f"- {item.name or item.code}（{item.code}，{item.sector or '未分类'}）："
            f"标签 {tags}，观察分 {score}"
        )
        if item.thesis:
            lines.append(f"  - 研究假设：{item.thesis}")
    lines.extend(["", "## 批量深度排序"])
    for index, stock in enumerate(report.batch.stocks, start=1):
        lines.append(
            f"{index}. {stock.name}（{stock.code}）："
            f"{stock.upside.score}/100，{stock.final_conclusion}"
        )
    lines.extend(["", "## 提醒检查"])
    if not report.alerts:
        lines.append("- 当前没有触发自选股提醒条件")
    for alert in report.alerts:
        lines.append(f"- [{alert.level}] {alert.name}（{alert.code}）：{alert.message}")
    lines.extend(["", "## 工作台说明"])
    lines.extend(f"- {item}" for item in report.notes)
    lines.extend(["", "---", report.disclaimer])
    return "\n".join(lines).strip() + "\n"


def _build_alerts(
    items: list[WatchlistItem],
    deep_reports: list[DeepStockReport],
) -> list[WatchlistAlert]:
    by_code = {report.code: report for report in deep_reports}
    alerts: list[WatchlistAlert] = []
    for item in items:
        report = by_code.get(item.code)
        if report is None:
            continue
        if item.alert_price_below is not None and report.latest_close <= item.alert_price_below:
            alerts.append(
                WatchlistAlert(
                    item.code,
                    report.name,
                    "price",
                    f"最新价 {report.latest_close:.2f} 低于 {item.alert_price_below:.2f}",
                )
            )
        if item.alert_price_above is not None and report.latest_close >= item.alert_price_above:
            alerts.append(
                WatchlistAlert(
                    item.code,
                    report.name,
                    "price",
                    f"最新价 {report.latest_close:.2f} 高于 {item.alert_price_above:.2f}",
                )
            )
        if item.alert_score_below is not None and report.upside.score < item.alert_score_below:
            alerts.append(
                WatchlistAlert(
                    item.code,
                    report.name,
                    "score",
                    f"观察分 {report.upside.score}/100 低于 {item.alert_score_below}/100",
                )
            )
    return alerts


def _item_from_dict(data: dict[str, str]) -> WatchlistItem:
    code = data.get("code", "").strip().strip("'\"")
    if not code:
        raise ValueError("watchlist stock code is required")
    tags = _split_tags(data.get("tags", ""))
    return WatchlistItem(
        code=code,
        name=data.get("name", "").strip().strip("'\""),
        sector=data.get("sector", "").strip().strip("'\""),
        tags=tags,
        thesis=data.get("thesis", "").strip().strip("'\""),
        alert_price_below=_float_or_none(data.get("alert_price_below")),
        alert_price_above=_float_or_none(data.get("alert_price_above")),
        alert_score_below=_int_or_none(data.get("alert_score_below")),
    )


def _split_key_value(line: str) -> tuple[str, str]:
    if ":" not in line:
        raise ValueError(f"invalid watchlist line: {line}")
    key, value = line.split(":", 1)
    return key.strip(), value.strip().strip("'\"")


def _split_tags(value: str) -> list[str]:
    value = value.strip().strip("[]")
    if not value:
        return []
    return [item.strip().strip("'\"") for item in value.split(",") if item.strip()]


def _float_or_none(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _int_or_none(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    return int(float(value))
