from __future__ import annotations

from .analysis import (
    build_decision_brief,
    build_market_analysis,
    build_opportunities,
    sector_score,
)
from .models import MarketSnapshot, SectorPulse


def _sector_view(sector: SectorPulse) -> dict[str, object]:
    return {
        "name": sector.name,
        "pct_change": round(sector.pct_change, 2),
        "advancing_ratio": (
            round(sector.advancing_ratio, 3)
            if sector.advancing_ratio is not None
            else None
        ),
        "amount_change": round(sector.amount_change, 2),
        "consecutive_days": sector.consecutive_days,
        "high_divergence": sector.high_divergence,
        "strength": round(sector_score(sector), 2),
    }


def build_view(snapshot: MarketSnapshot) -> dict[str, object]:
    market_analysis = build_market_analysis(snapshot)
    regime = market_analysis["regime"]
    risk_level = market_analysis["risk_level"]
    total = snapshot.advancing + snapshot.declining
    breadth = snapshot.advancing / total if total else 0.0

    ordered_sectors = sorted(snapshot.sectors, key=sector_score, reverse=True)
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
        "market_analysis": market_analysis,
        "opportunities": build_opportunities(snapshot),
        "decision_brief": build_decision_brief(snapshot),
    }
