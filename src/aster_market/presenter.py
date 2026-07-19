from __future__ import annotations

from .models import Candidate, MarketSnapshot, SectorPulse


def _sector_score(sector: SectorPulse) -> float:
    divergence_penalty = 0.7 if sector.high_divergence else 0.0
    return (
        sector.pct_change
        + sector.advancing_ratio * 2
        + sector.amount_change * 0.03
        + sector.consecutive_days * 0.2
        - divergence_penalty
    )


def _sector_view(sector: SectorPulse) -> dict[str, object]:
    return {
        "name": sector.name,
        "pct_change": round(sector.pct_change, 2),
        "advancing_ratio": round(sector.advancing_ratio, 3),
        "amount_change": round(sector.amount_change, 2),
        "consecutive_days": sector.consecutive_days,
        "high_divergence": sector.high_divergence,
        "strength": round(_sector_score(sector), 2),
    }


def _candidate_view(candidate: Candidate) -> dict[str, object]:
    return {
        "code": candidate.code,
        "name": candidate.name,
        "sector": candidate.sector,
        "pct_change": round(candidate.pct_change, 2) if candidate.pct_change is not None else None,
        "latest_price": round(candidate.latest_price, 2),
        "reason": candidate.reason,
        "risk": candidate.risk,
    }


def _horizon_points(breadth: float, limit_down: int, peak_strength: float) -> list[int]:
    breadth_lift = round((breadth - 0.5) * 36)
    risk_drop = min(limit_down, 40)
    strength_lift = min(round(max(peak_strength, 0) * 2), 24)
    return [58, 52 - breadth_lift, 48 - strength_lift, 50 + risk_drop, 44, 54]


def build_view(snapshot: MarketSnapshot) -> dict[str, object]:
    total = snapshot.advancing + snapshot.declining
    breadth = snapshot.advancing / total if total else 0.0
    if breadth >= 0.58 and snapshot.limit_down <= 10:
        regime = "扩张"
    elif breadth <= 0.42 or snapshot.limit_down >= 25:
        regime = "收缩"
    else:
        regime = "轮动"

    if snapshot.limit_down >= 25:
        risk_level = "升高"
    elif snapshot.limit_down >= 10:
        risk_level = "留意"
    else:
        risk_level = "可控"

    ordered_sectors = sorted(snapshot.sectors, key=_sector_score, reverse=True)
    ordered_candidates = sorted(
        snapshot.candidates,
        key=lambda item: item.pct_change if item.pct_change is not None else float("-inf"),
        reverse=True,
    )
    peak_strength = _sector_score(ordered_sectors[0]) if ordered_sectors else 0.0

    return {
        "status": "ready",
        "trade_date": snapshot.trade_date,
        "generated_at": snapshot.generated_at,
        "source": snapshot.source,
        "regime": regime,
        "risk_level": risk_level,
        "breadth_ratio": round(breadth, 3),
        "advancing": snapshot.advancing,
        "declining": snapshot.declining,
        "limit_up": snapshot.limit_up,
        "limit_down": snapshot.limit_down,
        "northbound_net_inflow": (
            round(snapshot.northbound_net_inflow, 2)
            if snapshot.northbound_net_inflow is not None
            else None
        ),
        "indices": [
            {
                "name": quote.name,
                "code": quote.code,
                "value": round(quote.value, 2),
                "pct_change": round(quote.pct_change, 2),
            }
            for quote in snapshot.indices
        ],
        "sectors": [_sector_view(sector) for sector in ordered_sectors],
        "candidates": [_candidate_view(candidate) for candidate in ordered_candidates],
        "news": [
            {
                "published_at": item.published_at,
                "source": item.source,
                "title": item.title,
                "summary": item.summary,
            }
            for item in snapshot.news
        ],
        "horizon_points": _horizon_points(breadth, snapshot.limit_down, peak_strength),
    }
