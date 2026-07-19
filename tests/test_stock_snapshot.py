import json
from pathlib import Path

from aster_market.snapshot import load_snapshot

FIXTURE = Path(__file__).parent / "fixtures" / "market_snapshot.json"


def test_snapshot_merges_stock_profiles_by_code() -> None:
    result = load_snapshot(FIXTURE)

    assert result.snapshot is not None
    stock = result.snapshot.stocks[0]
    assert stock.code == "300100"
    assert stock.sector == "机器人"
    assert stock.bars[-1].close == 32.45
    assert stock.valuation.pe_ttm == 28.4
    assert stock.flow.outside_volume == 99000
    assert stock.events[0].title == "双林股份披露业务进展"


def test_stock_profile_preserves_missing_optional_values() -> None:
    result = load_snapshot(FIXTURE)

    assert result.snapshot is not None
    stock = next(item for item in result.snapshot.stocks if item.code == "688981")
    assert stock.flow.inside_volume is None
    assert stock.valuation.pb is None
    assert stock.missing_fields == ("pb", "inside_dish_hand", "outer_disc_hand")
    assert stock.events[0].title == "中芯国际披露运营数据"


def test_candidate_enrichment_fills_missing_stock_profile_fields(tmp_path: Path) -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    payload["stocks"]["688981"]["valuation"]["pe_ttm"] = None
    payload["candidate_universe"]["items"][1]["pe_ttm"] = 41.8
    path = tmp_path / "candidate-enrichment.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    result = load_snapshot(path)

    assert result.snapshot is not None
    stock = next(item for item in result.snapshot.stocks if item.code == "688981")
    assert stock.valuation.pe_ttm == 41.8
