from pathlib import Path

from aster_market.presenter import build_view
from aster_market.snapshot import load_snapshot
from aster_market.ui import asset_text, render_app

FIXTURE = Path(__file__).parent / "fixtures" / "market_snapshot.json"


def _sample_view() -> dict[str, object]:
    snapshot = load_snapshot(FIXTURE).snapshot
    assert snapshot is not None
    return build_view(snapshot)


def test_ui_uses_market_horizon_and_no_inherited_patterns() -> None:
    html = render_app(_sample_view())

    assert 'data-aster-app="market-horizon"' in html
    assert "data-market-horizon" in html
    assert "市场地平线" in html
    assert "观察，不是买点" in html
    assert "StockTS" not in html
    assert "desktop-sidebar" not in html
    assert 'name="viewport"' not in html
    assert "@media (max-width" not in html


def test_ui_escapes_external_content() -> None:
    view = _sample_view()
    view["news"] = [
        {
            "published_at": "15:00",
            "source": "<source>",
            "title": "<script>alert(1)</script>",
            "summary": "A & B",
        }
    ]

    html = render_app(view)

    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "A &amp; B" in html


def test_assets_enforce_desktop_visual_contract() -> None:
    css = asset_text("app.css")
    javascript = asset_text("app.js")

    assert "min-width: 1180px" in css
    assert "#1346d8" in css.lower()
    assert "@media (max-width" not in css
    assert "desktop-sidebar" not in css
    assert "420ms" in css
    assert "location.reload()" in javascript
    assert "candidate-search" in javascript


def test_ui_explains_unavailable_data_without_fake_prices() -> None:
    html = render_app({"status": "unavailable", "message": "快照暂不可用"})

    assert "数据暂不可用" in html
    assert "快照暂不可用" in html
    assert "等待下一份有效行情快照" in html


def test_ui_marks_missing_candidate_change_as_unavailable() -> None:
    view = _sample_view()
    candidates = view["candidates"]
    assert isinstance(candidates, list)
    candidates[0]["pct_change"] = None

    html = render_app(view)

    assert '<span class="delta unavailable">—</span>' in html


def test_ui_contains_four_analysis_decks() -> None:
    html = render_app(_sample_view())

    for module in ("market", "opportunities", "stock", "portfolio"):
        assert f'data-module-deck="{module}"' in html
    assert "大盘分析" in html
    assert "市场机会" in html
    assert "股票分析" in html
    assert "我的持仓" in html
    assert "持仓只保存在当前浏览器" in html
    assert "card-grid" not in html


def test_module_assets_keep_the_desktop_only_contract() -> None:
    css = asset_text("modules.css")

    assert "analysis-deck" in css
    assert "min-width: 1180px" in css
    assert "@media (max-width" not in css
    assert "border-radius: 16px" not in css
