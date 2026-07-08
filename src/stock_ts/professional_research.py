from __future__ import annotations

from dataclasses import dataclass

from .announcements import AnnouncementReport
from .indicators import macd, rsi, sma
from .models import DailyBar, StockRawData


@dataclass(frozen=True)
class TechnicalProfile:
    support: float
    resistance: float
    invalid_line: float
    ma5: float | None
    ma10: float | None
    ma20: float | None
    rsi14: float | None
    macd_status: str
    volume_ratio: float
    structure: str
    checkpoints: list[str]


@dataclass(frozen=True)
class EventRadar:
    source: str
    total: int
    returned: int
    risk_score: int
    gate: str
    key_events: list[str]
    review_actions: list[str]


def render_professional_appendix(
    technical: TechnicalProfile,
    event_radar: EventRadar,
    announcements: AnnouncementReport | None,
) -> str:
    lines = [
        "## 专业研究附录：盘口技术结构",
        f"- 支撑观察：{technical.support:.2f}",
        f"- 压力观察：{technical.resistance:.2f}",
        f"- 失效线：{technical.invalid_line:.2f}",
        f"- MA5/MA10/MA20：{_fmt(technical.ma5)} / {_fmt(technical.ma10)} / {_fmt(technical.ma20)}",
        f"- RSI14：{_fmt(technical.rsi14)}",
        f"- MACD：{technical.macd_status}",
        f"- 量能比：{technical.volume_ratio:.2f}",
        f"- 结构判断：{technical.structure}",
        "",
        "### 技术复核清单",
    ]
    lines.extend(f"- {item}" for item in technical.checkpoints)
    lines.extend(
        [
            "",
            "## 专业研究附录：公告事件雷达",
            f"- 数据源：{event_radar.source}",
            f"- 风险闸门：{event_radar.gate}",
            f"- 事件风险分：{event_radar.risk_score}/100",
            f"- 返回/总数：{event_radar.returned}/{event_radar.total}",
            "",
            "### 关键事件",
        ]
    )
    lines.extend(f"- {item}" for item in event_radar.key_events)
    lines.extend(["", "### 复核动作"])
    lines.extend(f"- {item}" for item in event_radar.review_actions)
    lines.extend(["", "### 最新公告"])
    if announcements is None or not announcements.items:
        lines.append("- 未拉取到公告数据。")
    else:
        for item in announcements.items[:5]:
            flags = f"（{','.join(item.risk_flags)}）" if item.risk_flags else ""
            lines.append(f"- {item.date} {item.title}{flags} {item.url}")
    return "\n".join(lines).strip() + "\n"


def build_technical_profile(raw: StockRawData) -> TechnicalProfile:
    if not raw.bars:
        raise ValueError("stock bars cannot be empty")

    bars = raw.bars
    latest = bars[-1]
    closes = [bar.close for bar in bars]
    volumes = [bar.volume for bar in bars]
    lookback = bars[-20:] if len(bars) >= 20 else bars
    support = min(bar.low for bar in lookback)
    resistance = max(bar.high for bar in lookback)
    invalid_line = min(latest.close * 0.95, support * 0.99)
    ma5 = sma(closes, min(5, len(closes)))
    ma10 = sma(closes, 10) if len(closes) >= 10 else None
    ma20 = sma(closes, 20) if len(closes) >= 20 else None
    rsi_values = rsi(closes, 14)
    rsi14 = next((value for value in reversed(rsi_values) if value is not None), None)
    macd_status = _macd_status(closes)
    volume_ratio = _volume_ratio(volumes)
    structure = _structure(latest, support, resistance, ma5, ma20, volume_ratio)
    return TechnicalProfile(
        support=round(support, 2),
        resistance=round(resistance, 2),
        invalid_line=round(invalid_line, 2),
        ma5=round(ma5, 2) if ma5 is not None else None,
        ma10=round(ma10, 2) if ma10 is not None else None,
        ma20=round(ma20, 2) if ma20 is not None else None,
        rsi14=round(rsi14, 1) if rsi14 is not None else None,
        macd_status=macd_status,
        volume_ratio=round(volume_ratio, 2),
        structure=structure,
        checkpoints=_checkpoints(latest, support, resistance, volume_ratio),
    )


def build_event_radar(report: AnnouncementReport | None) -> EventRadar:
    if report is None:
        return EventRadar(
            source="cninfo",
            total=0,
            returned=0,
            risk_score=50,
            gate="公告待补充",
            key_events=["未拉取到公告数据，不能把事件风险视为已排除。"],
            review_actions=["补充 CNInfo 公告或本地公告 CSV 后再做事件确认。"],
        )

    flagged_items = [item for item in report.items if item.risk_flags]
    risk_score = min(100, 35 + len(flagged_items) * 30 + len(report.items) * 2)
    if flagged_items:
        gate = "事件需复核"
    elif report.items:
        gate = "未见标题级风险"
    else:
        gate = "公告待补充"
    key_events = [
        f"{item.date} {item.title}（{','.join(item.risk_flags) or '普通公告'}）"
        for item in (flagged_items or report.items[:3])
    ]
    if not key_events:
        key_events = ["本次未返回公告，需检查代码、名称或接口可用性。"]
    review_actions = [
        "打开公告 PDF 原文复核关键条款，标题规则不能替代人工判断。",
        "把减持、质押、监管、诉讼、业绩预告等事件纳入次日风险闸门。",
        "若公告与技术面冲突，以事件风险优先，降低观察等级。",
    ]
    return EventRadar(
        source=report.source,
        total=report.total,
        returned=len(report.items),
        risk_score=risk_score,
        gate=gate,
        key_events=key_events,
        review_actions=review_actions,
    )


def _fmt(value: float | None) -> str:
    return "-" if value is None else f"{value:.2f}"


def _macd_status(closes: list[float]) -> str:
    if len(closes) < 3:
        return "样本不足"
    values = macd(closes)
    latest = values["macd"][-1]
    previous = values["macd"][-2] if len(values["macd"]) >= 2 else latest
    if latest >= 0 and latest >= previous:
        return "红柱扩张，动能偏强"
    if latest >= 0:
        return "红柱收敛，动能放缓"
    if latest < previous:
        return "绿柱扩张，动能偏弱"
    return "绿柱收敛，等待修复"


def _volume_ratio(volumes: list[float]) -> float:
    if not volumes:
        return 0.0
    recent = sum(volumes[-3:]) / min(3, len(volumes))
    base = sum(volumes) / len(volumes)
    return recent / base if base else 0.0


def _structure(
    latest: DailyBar,
    support: float,
    resistance: float,
    ma5: float | None,
    ma20: float | None,
    volume_ratio: float,
) -> str:
    parts = [f"支撑 {support:.2f} / 压力 {resistance:.2f}"]
    if ma5 is not None:
        parts.append("站上 5 日线" if latest.close >= ma5 else "未站稳 5 日线")
    if ma20 is not None:
        parts.append("位于 20 日线上方" if latest.close >= ma20 else "位于 20 日线下方")
    parts.append("量能放大" if volume_ratio >= 1.2 else "量能未明显放大")
    return "，".join(parts)


def _checkpoints(
    latest: DailyBar,
    support: float,
    resistance: float,
    volume_ratio: float,
) -> list[str]:
    return [
        f"若回踩不破 {support:.2f} 且缩量，观察是否形成低吸承接。",
        f"若放量突破 {resistance:.2f}，再确认是否有板块和指数共振。",
        f"若跌破 {min(latest.close * 0.95, support * 0.99):.2f}，按失效处理，不用补仓摊低。",
        f"当前量能比 {volume_ratio:.2f}，低于 1.2 时不把突破视为充分确认。",
    ]
