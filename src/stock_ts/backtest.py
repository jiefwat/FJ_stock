from __future__ import annotations

from dataclasses import dataclass

from .indicators import sma
from .models import DailyBar
from .report import DISCLAIMER


@dataclass(frozen=True)
class BacktestTrade:
    date: str
    side: str
    price: float
    shares: float
    reason: str


@dataclass(frozen=True)
class BacktestReport:
    code: str
    name: str
    start_date: str
    end_date: str
    strategy: str
    initial_cash: float
    final_value: float
    total_return_pct: float
    buy_and_hold_return_pct: float
    max_drawdown_pct: float
    trade_count: int
    win_rate_pct: float
    exposure_pct: float
    trades: list[BacktestTrade]
    notes: list[str]


def backtest_moving_average(
    code: str,
    name: str,
    bars: list[DailyBar],
    *,
    fast_window: int = 5,
    slow_window: int = 20,
    initial_cash: float = 100000.0,
) -> BacktestReport:
    if not bars:
        raise ValueError("bars cannot be empty")
    if fast_window <= 0 or slow_window <= 0:
        raise ValueError("windows must be positive")
    if fast_window >= slow_window:
        raise ValueError("fast_window must be smaller than slow_window")
    if initial_cash <= 0:
        raise ValueError("initial_cash must be positive")

    closes = [bar.close for bar in bars]
    cash = float(initial_cash)
    shares = 0.0
    entry_price = 0.0
    entry_values: list[float] = []
    closed_returns: list[float] = []
    equity_curve: list[float] = []
    exposure_days = 0
    trades: list[BacktestTrade] = []

    for index, bar in enumerate(bars):
        fast = sma(closes[: index + 1], fast_window)
        slow = sma(closes[: index + 1], slow_window)
        if fast is not None and slow is not None:
            if shares == 0 and fast > slow:
                shares = cash / bar.close
                cash = 0.0
                entry_price = bar.close
                entry_values.append(entry_price)
                trades.append(
                    BacktestTrade(
                        date=bar.date,
                        side="buy",
                        price=bar.close,
                        shares=shares,
                        reason=f"MA{fast_window} 上穿或站上 MA{slow_window}",
                    )
                )
            elif shares > 0 and fast < slow:
                cash = shares * bar.close
                closed_returns.append((bar.close - entry_price) / entry_price * 100)
                trades.append(
                    BacktestTrade(
                        date=bar.date,
                        side="sell",
                        price=bar.close,
                        shares=shares,
                        reason=f"MA{fast_window} 跌破 MA{slow_window}",
                    )
                )
                shares = 0.0
        if shares > 0:
            exposure_days += 1
        equity_curve.append(cash + shares * bar.close)

    final_value = equity_curve[-1]
    total_return = (final_value - initial_cash) / initial_cash * 100
    buy_and_hold = (bars[-1].close - bars[0].close) / bars[0].close * 100 if bars[0].close else 0
    drawdown = _max_drawdown(equity_curve)
    wins = sum(1 for item in closed_returns if item > 0)
    win_rate = wins / len(closed_returns) * 100 if closed_returns else 0.0
    notes = [
        "该回测为轻量研究工具，不含滑点、手续费、停牌、涨跌停无法成交等真实交易约束。",
        "信号使用收盘价计算，适合做策略 sanity check，不可视为实盘收益预测。",
        "建议与持仓分析、市场环境和板块强弱一起使用。",
    ]
    return BacktestReport(
        code=code,
        name=name,
        start_date=bars[0].date,
        end_date=bars[-1].date,
        strategy=f"MA{fast_window}/MA{slow_window} 均线趋势",
        initial_cash=initial_cash,
        final_value=final_value,
        total_return_pct=total_return,
        buy_and_hold_return_pct=buy_and_hold,
        max_drawdown_pct=drawdown,
        trade_count=len(trades),
        win_rate_pct=win_rate,
        exposure_pct=exposure_days / len(bars) * 100,
        trades=trades,
        notes=notes,
    )


def render_backtest_markdown(report: BacktestReport) -> str:
    lines = [
        f"# 轻量均线回测：{report.name}（{report.code}）",
        "",
        DISCLAIMER,
        "",
        "## 回测概览",
        f"- 区间：{report.start_date} 至 {report.end_date}",
        f"- 策略：{report.strategy}",
        f"- 初始资金：{report.initial_cash:.2f}",
        f"- 期末权益：{report.final_value:.2f}",
        f"- 策略收益：{report.total_return_pct:.2f}%",
        f"- 买入持有收益：{report.buy_and_hold_return_pct:.2f}%",
        f"- 最大回撤：{report.max_drawdown_pct:.2f}%",
        f"- 交易次数：{report.trade_count}",
        f"- 已平仓胜率：{report.win_rate_pct:.2f}%",
        f"- 持仓暴露：{report.exposure_pct:.2f}%",
        "",
        "## 交易明细",
    ]
    if not report.trades:
        lines.append("- 未触发交易信号")
    for trade in report.trades:
        lines.append(
            f"- {trade.date} {trade.side.upper()} {trade.shares:.2f} 股，"
            f"价格 {trade.price:.2f}，原因：{trade.reason}"
        )
    lines.extend(["", "## 使用限制"])
    lines.extend(f"- {item}" for item in report.notes)
    lines.extend(["", "---", DISCLAIMER])
    return "\n".join(lines).strip() + "\n"


def _max_drawdown(values: list[float]) -> float:
    peak = values[0]
    max_dd = 0.0
    for value in values:
        peak = max(peak, value)
        if peak:
            max_dd = min(max_dd, (value - peak) / peak * 100)
    return max_dd
