from dataclasses import replace
from pathlib import Path

from aster_market.analysis import (
    analyze_stock,
    build_decision_brief,
    build_market_analysis,
    build_opportunities,
    find_stock,
    search_stocks,
)
from aster_market.snapshot import load_snapshot

FIXTURE = Path(__file__).parent / "fixtures" / "market_snapshot.json"


def _snapshot():
    snapshot = load_snapshot(FIXTURE).snapshot
    assert snapshot is not None
    return snapshot


def test_market_analysis_exposes_four_evidence_dimensions() -> None:
    analysis = build_market_analysis(_snapshot())

    assert analysis["regime"] == "轮动"
    assert analysis["risk_level"] == "可控"
    assert [item["key"] for item in analysis["evidence"]] == [
        "index_direction",
        "participation",
        "limit_pressure",
        "concentration",
    ]
    assert analysis["next_check"]


def test_opportunities_classify_spread_and_divergence() -> None:
    opportunities = build_opportunities(_snapshot())

    assert opportunities[0]["theme"] == "机器人"
    assert opportunities[0]["stage"] == "扩散"
    assert opportunities[0]["invalidation"] == "上涨占比跌破 50% 或分歧升高"
    assert opportunities[0]["candidates"][0]["code"] == "300100"
    assert opportunities[1]["stage"] == "分歧"


def test_stock_analysis_derives_trend_momentum_and_volatility() -> None:
    stock = find_stock(_snapshot(), "300100")
    assert stock is not None

    detail = analyze_stock(stock)

    assert detail["code"] == "300100"
    assert detail["trend"]["label"] == "强"
    assert detail["trend"]["average_20d"] is None
    assert detail["momentum"]["return_5d"] == 7.1
    assert detail["momentum"]["return_20d"] is None
    assert detail["volatility"]["range_10d"] is not None
    assert detail["valuation"]["pe_ttm"] == 28.4
    assert detail["flow"]["order_balance"] == 10.0


def test_stock_analysis_marks_short_history_as_insufficient() -> None:
    stock = find_stock(_snapshot(), "688981")
    assert stock is not None

    detail = analyze_stock(stock)

    assert detail["trend"]["label"] == "样本不足"
    assert detail["momentum"]["return_5d"] is None
    assert detail["valuation"]["pb"] is None


def test_stock_search_matches_code_name_and_sector() -> None:
    snapshot = _snapshot()

    assert search_stocks(snapshot, "300100")[0]["code"] == "300100"
    assert search_stocks(snapshot, "双林")[0]["name"] == "双林股份"
    assert search_stocks(snapshot, "机器人")[0]["sector"] == "机器人"
    assert len(search_stocks(snapshot, "")) <= 20


def test_decision_brief_downgrades_strength_in_contracting_market() -> None:
    snapshot = replace(_snapshot(), advancing=400, declining=4600, limit_down=80)

    brief = build_decision_brief(snapshot)

    assert brief["permission"]["label"] == "防守等待"
    assert brief["mainline"]["status"] == "countertrend"
    assert brief["mainline"]["label"] == "逆势异动"
    assert "尚未形成可确认主线" in brief["summary"]


def test_decision_brief_confirms_mainline_in_expansion() -> None:
    snapshot = replace(_snapshot(), advancing=3400, declining=1600, limit_down=6)

    brief = build_decision_brief(snapshot)

    assert brief["permission"]["label"] == "主动跟踪"
    assert brief["mainline"]["status"] == "confirmed"
    assert brief["mainline"]["theme"] == "机器人"


def test_decision_brief_keeps_rotation_as_candidate() -> None:
    brief = build_decision_brief(_snapshot())

    assert brief["permission"]["label"] == "结构确认"
    assert brief["mainline"]["status"] == "candidate"


def test_decision_brief_handles_empty_sectors() -> None:
    brief = build_decision_brief(replace(_snapshot(), sectors=(), candidates=()))

    assert brief["mainline"]["status"] == "none"
    assert brief["mainline"]["theme"] is None
