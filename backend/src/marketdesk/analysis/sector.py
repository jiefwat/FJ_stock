from __future__ import annotations

from marketdesk.models import EquityQuote, SectorDossier, SectorSnapshot


def _format_yi(value: float) -> str:
    return f"{value / 100_000_000:.2f} 亿"


def _temperature(change_pct: float | None, net_flow: float | None) -> str:
    score = 0
    if change_pct is not None:
        score += 1 if change_pct > 1 else -1 if change_pct < -1 else 0
    if net_flow is not None:
        score += 1 if net_flow > 0 else -1 if net_flow < 0 else 0
    if score >= 2:
        return "偏强"
    if score <= -2:
        return "偏弱"
    return "中性"


def analyse_sector(
    sector: SectorSnapshot, constituents: list[EquityQuote], limit: int = 30
) -> SectorDossier:
    ranked = sorted(
        constituents,
        key=lambda quote: (
            quote.net_flow is not None,
            quote.net_flow or 0,
            quote.change_pct or -999,
            quote.amount or 0,
        ),
        reverse=True,
    )[:limit]
    missing: list[str] = []
    present = 0
    required = 3
    if sector.change_pct is not None:
        present += 1
    else:
        missing.append("板块涨跌幅")
    if sector.net_flow is not None:
        present += 1
    else:
        missing.append("板块资金流")
    if ranked:
        present += 1
    else:
        missing.append("成分股列表")
    if ranked and any(item.net_flow is None for item in ranked):
        missing.append("成分股资金流")

    tone = _temperature(sector.change_pct, sector.net_flow)
    summary: list[str] = []
    if sector.net_flow is not None:
        direction = "净流入" if sector.net_flow >= 0 else "净流出"
        summary.append(f"主力{direction} {_format_yi(abs(sector.net_flow))}，板块热度{tone}。")
    elif sector.change_pct is not None:
        summary.append(f"板块涨跌 {sector.change_pct:.2f}%，热度{tone}，资金流仍待增强源确认。")
    else:
        summary.append("板块价格和资金证据不足，先作为观察入口，不做强弱判断。")
    if ranked:
        rising = sum((item.change_pct or 0) > 0 for item in ranked)
        summary.append(f"成分股样本 {len(ranked)} 只，上涨 {rising} 只，先核对前排个股的证据链。")

    return SectorDossier(
        sector=sector,
        summary=summary,
        evidence_coverage=present / required,
        missing_evidence=missing,
        constituents=ranked,
    )
