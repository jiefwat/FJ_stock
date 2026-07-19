from marketdesk.models import MarketAnalysis, MarketFactor, MarketSnapshot


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))


def analyse_market(snapshot: MarketSnapshot) -> MarketAnalysis:
    changes = [item.change_pct for item in snapshot.equities if item.change_pct is not None]
    advancing = sum(value > 0 for value in changes)
    declining = sum(value < 0 for value in changes)
    unchanged = len(changes) - advancing - declining
    breadth = 100 * advancing / len(changes) if changes else None
    index_changes = [item.change_pct for item in snapshot.indices if item.change_pct is not None]
    index_score = (
        _clamp(50 + (sum(index_changes) / len(index_changes)) * 12) if index_changes else None
    )
    volume_ratios = [
        item.volume_ratio for item in snapshot.equities if item.volume_ratio is not None
    ]
    liquidity = _clamp((sum(volume_ratios) / len(volume_ratios)) * 50) if volume_ratios else None
    sector_changes = [item.change_pct for item in snapshot.sectors if item.change_pct is not None]
    sector_participation = (
        100 * sum(value > 0 for value in sector_changes) / len(sector_changes)
        if sector_changes
        else None
    )
    flows = [item.net_flow for item in snapshot.equities if item.net_flow is not None]
    capital = 100 * sum(value > 0 for value in flows) / len(flows) if flows else None
    raw = [
        ("breadth", "涨跌广度", breadth, 0.30),
        ("index", "指数趋势", index_score, 0.25),
        ("liquidity", "流动性", liquidity, 0.15),
        ("sector", "板块参与度", sector_participation, 0.15),
        ("capital", "资金确认", capital, 0.10),
        ("external", "外部风险", None, 0.05),
    ]
    evidence = {
        "breadth": f"上涨 {advancing} / 下跌 {declining} / 平盘 {unchanged}",
        "index": f"{len(index_changes)} 个核心指数参与评分" if index_changes else "指数数据暂缺",
        "liquidity": f"{len(volume_ratios)} 只股票具备量比" if volume_ratios else "量比数据暂缺",
        "sector": f"{sum(value > 0 for value in sector_changes)} / {len(sector_changes)} 个板块上涨" if sector_changes else "板块数据暂缺",
        "capital": f"{sum(value > 0 for value in flows)} / {len(flows)} 只股票资金净流入" if flows else "资金流数据暂缺",
        "external": "外部风险数据暂缺",
    }
    available_weight = sum(weight for _, _, score, weight in raw if score is not None)
    factors = [
        MarketFactor(
            key=key,
            label=label,
            score=round(score, 2) if score is not None else None,
            weight=weight / available_weight if score is not None and available_weight else 0,
            available=score is not None,
            evidence=evidence[key] if score is not None else f"{evidence[key]}，未计入总分",
        )
        for key, label, score, weight in raw
    ]
    total = sum((factor.score or 0) * factor.weight for factor in factors)
    regime = (
        "risk_off"
        if total < 35
        else "cautious"
        if total < 50
        else "balanced"
        if total < 65
        else "risk_on"
    )
    confidence = available_weight / sum(weight for *_, weight in raw)
    return MarketAnalysis(
        score=round(total, 2),
        regime=regime,
        confidence=round(confidence, 2),
        factors=factors,
        advancing=advancing,
        declining=declining,
        unchanged=unchanged,
    )
