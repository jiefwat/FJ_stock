import json
from pathlib import Path

from aster_market.snapshot import load_snapshot

FIXTURE = Path(__file__).parent / "fixtures" / "market_snapshot.json"


def test_load_snapshot_maps_market_and_candidates() -> None:
    result = load_snapshot(FIXTURE)

    assert result.status == "ready"
    assert result.snapshot is not None
    assert result.snapshot.trade_date == "2026-07-18"
    assert result.snapshot.indices[0].value == 3501.26
    assert result.snapshot.candidates[0].code == "300100"
    assert result.snapshot.candidates[0].latest_price == 32.45
    assert result.snapshot.news[0].published_at == "2026-07-18 14:35:00"


def test_missing_snapshot_is_explicitly_unavailable(tmp_path: Path) -> None:
    result = load_snapshot(tmp_path / "missing.json")

    assert result.status == "unavailable"
    assert result.snapshot is None
    assert "不存在" in result.message


def test_malformed_snapshot_is_explicitly_unavailable(tmp_path: Path) -> None:
    path = tmp_path / "broken.json"
    path.write_text('{"market": []}', encoding="utf-8")

    result = load_snapshot(path)

    assert result.status == "unavailable"
    assert result.snapshot is None
    assert "格式" in result.message


def test_missing_market_values_are_not_invented_as_zero(tmp_path: Path) -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    payload["market"]["northbound_net_inflow"] = None
    payload["candidate_universe"]["items"][0]["bars"] = [
        {"date": "2026-07-18", "close": 32.45}
    ]
    payload["candidate_universe"]["items"][1]["bars"] = []
    payload["stocks"]["688981"]["bars"] = []
    path = tmp_path / "partial.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    result = load_snapshot(path)

    assert result.snapshot is not None
    assert result.snapshot.northbound_net_inflow is None
    assert result.snapshot.candidates[0].pct_change is None
    assert [item.code for item in result.snapshot.candidates] == ["300100"]
