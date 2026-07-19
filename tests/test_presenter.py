from pathlib import Path

from aster_market.models import MarketSnapshot
from aster_market.presenter import build_view
from aster_market.snapshot import load_snapshot

FIXTURE = Path(__file__).parent / "fixtures" / "market_snapshot.json"


def _snapshot(**overrides: int) -> MarketSnapshot:
    loaded = load_snapshot(FIXTURE).snapshot
    assert loaded is not None
    values = {
        field: getattr(loaded, field) for field in MarketSnapshot.__dataclass_fields__
    }
    values.update(overrides)
    return MarketSnapshot(**values)


def test_build_view_derives_rotation_and_orders_strength() -> None:
    view = build_view(_snapshot())

    assert view["regime"] == "轮动"
    assert view["risk_level"] == "可控"
    assert view["breadth_ratio"] == 0.571
    assert view["sectors"][0]["name"] == "机器人"
    assert "horizon_points" not in view
    assert "candidates" not in view
    assert "news" not in view
    assert view["market_analysis"]["evidence"][0]["key"] == "index_direction"
    assert view["opportunities"][0]["theme"] == "机器人"


def test_build_view_derives_expansion_and_contraction() -> None:
    expansion = build_view(_snapshot(advancing=3400, declining=1600, limit_down=6))
    contraction = build_view(_snapshot(advancing=1600, declining=3400, limit_down=28))

    assert expansion["regime"] == "扩张"
    assert contraction["regime"] == "收缩"
    assert contraction["risk_level"] == "升高"


def test_build_view_exposes_decision_chain() -> None:
    view = build_view(_snapshot())

    assert view["decision_brief"]["permission"]["label"] == "结构确认"
    assert [step["key"] for step in view["decision_brief"]["chain"]] == [
        "environment",
        "permission",
        "mainline",
        "validation",
        "trigger",
    ]
