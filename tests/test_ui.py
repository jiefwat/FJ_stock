from dataclasses import replace
from pathlib import Path

from aster_market.presenter import build_view
from aster_market.snapshot import load_snapshot
from aster_market.ui import asset_text, render_app

FIXTURE = Path(__file__).parent / "fixtures" / "market_snapshot.json"


def _sample_view() -> dict[str, object]:
    snapshot = load_snapshot(FIXTURE).snapshot
    assert snapshot is not None
    return build_view(snapshot)


def test_ui_uses_decision_chain_and_no_inherited_patterns() -> None:
    html = render_app(_sample_view())

    assert 'data-aster-app="decision-chain"' in html
    assert "data-decision-chain" in html
    assert "不构成投资建议" in html
    assert "StockTS" not in html
    assert "desktop-sidebar" not in html
    assert 'name="viewport"' not in html
    assert "@media (max-width" not in html


def test_ui_escapes_external_content() -> None:
    view = _sample_view()
    decision_brief = view["decision_brief"]
    assert isinstance(decision_brief, dict)
    decision_brief["summary"] = "<script>alert(1)</script> A & B"

    html = render_app(view)

    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "A &amp; B" in html


def test_assets_enforce_desktop_visual_contract() -> None:
    css = asset_text("app.css")
    javascript = asset_text("app.js")

    assert "min-width: 1180px" in css
    assert "#1648d8" in css.lower()
    assert "@media (max-width" not in css
    assert "desktop-sidebar" not in css
    assert "180ms" in css
    assert "location.reload()" in javascript
    assert "candidate-search" in javascript


def test_ui_explains_unavailable_data_without_fake_prices() -> None:
    html = render_app({"status": "unavailable", "message": "快照暂不可用"})

    assert "数据暂不可用" in html
    assert "快照暂不可用" in html
    assert "等待下一份有效行情快照" in html


def test_ui_marks_missing_candidate_change_as_unavailable() -> None:
    view = _sample_view()
    opportunities = view["opportunities"]
    assert isinstance(opportunities, list)
    candidates = opportunities[0]["candidates"]
    assert isinstance(candidates, list)
    candidates[0]["pct_change"] = None

    html = render_app(view)

    assert "300100 · —" in html


def test_ui_contains_four_analysis_decks() -> None:
    html = render_app(_sample_view())

    for module in ("market", "opportunities", "stock", "portfolio"):
        assert f'data-module-deck="{module}"' in html
    assert "今日研判" in html
    assert "主线扫描" in html
    assert "个股验证" in html
    assert "持仓检查" in html
    assert "代码、成本和数量仅保存在 localStorage" in html
    assert "card-grid" not in html
    assert "/assets/app.css?v=decision-v1" in html
    assert "/assets/modules.css?v=decision-v1" in html
    assert "/assets/app.js?v=decision-v1" in html
    assert "/assets/portfolio.js?v=decision-v1" in html


def test_module_assets_keep_the_desktop_only_contract() -> None:
    css = asset_text("modules.css")

    assert "analysis-deck" in css
    assert "min-width: 1180px" in css
    assert "@media (max-width" not in css
    assert "border-radius: 16px" not in css
    assert "[data-stock-empty][hidden]" in css
    assert "[data-portfolio-empty][hidden]" in css


def test_interaction_assets_keep_holdings_private_to_the_browser() -> None:
    app_javascript = asset_text("app.js")
    portfolio_javascript = asset_text("portfolio.js")

    assert "data-module-switch" in app_javascript
    assert "/api/stocks?query=" in app_javascript
    assert "/api/stocks/" in app_javascript
    assert "aster.portfolio.v1" in portfolio_javascript
    assert "localStorage" in portfolio_javascript
    assert "/api/stocks/" in portfolio_javascript
    assert "body:" not in portfolio_javascript
    assert "method:" not in portfolio_javascript
    assert "innerHTML" not in app_javascript
    assert "innerHTML" not in portfolio_javascript
    missing_guard = 'value === null || value === undefined || value === ""'
    assert missing_guard in app_javascript
    assert missing_guard in portfolio_javascript


def test_ui_exposes_comfort_workbench_contract() -> None:
    html = render_app(_sample_view())
    css = asset_text("app.css") + asset_text("modules.css")

    assert 'data-keyboard-hint="1-4"' in html
    assert "data-toast" in html
    assert "stock-loading-skeleton" in html
    assert "decision-v1" in html
    assert ".command-band" in css
    assert "min-height: 64px" in css
    assert ".deck-heading" in css
    assert "min-height: 84px" in css


def test_interaction_assets_include_smooth_workbench_controls() -> None:
    app_javascript = asset_text("app.js")
    portfolio_javascript = asset_text("portfolio.js")
    app_css = asset_text("app.css")

    assert "AbortController" in app_javascript
    assert "moduleScrollPositions" in app_javascript
    assert 'event.key === "/"' in app_javascript
    assert 'event.key === "Escape"' in app_javascript
    assert "dismissToast" in app_javascript
    assert "AsterStockCache" in app_javascript
    assert "aster:toast" in app_javascript
    assert "AsterStockCache" in portfolio_javascript
    assert app_javascript.count("if (requestId !== stockRequestSequence) return;") >= 2
    assert "portfolioRenderSequence" in portfolio_javascript
    assert "holdingSnapshot" in portfolio_javascript
    assert "completeQuotes" in portfolio_javascript
    assert "部分行情不可用，组合汇总暂不计算" in portfolio_javascript
    assert "scroll-behavior: smooth" not in app_css


def test_ui_exposes_analyst_decision_chain() -> None:
    html = render_app(_sample_view())
    css = asset_text("app.css")

    assert "data-decision-chain" in html
    assert 'data-decision-status="candidate"' in html
    assert "今日研判" in html
    assert "主线扫描" in html
    assert "个股验证" in html
    assert "持仓检查" in html
    assert "参与许可" in html
    assert "主线梯队" in html
    assert ".decision-chain" in css
    assert ".thesis-stage" in css
    assert "decision-v1" in html


def test_ui_downgrades_strong_themes_in_contracting_market() -> None:
    snapshot = load_snapshot(FIXTURE).snapshot
    assert snapshot is not None
    view = build_view(replace(snapshot, advancing=400, declining=4600, limit_down=80))

    html = render_app(view)

    assert 'data-decision-status="countertrend"' in html
    assert "防守等待" in html
    assert "逆势异动" in html
    assert "尚未形成可确认主线" in html
    assert "确认主线：机器人" not in html
    assert 'data-opportunity-stage="扩散"' not in html
    assert html.count('data-opportunity-stage="逆势异动"') == len(view["opportunities"])


def test_ui_keeps_only_decision_essentials() -> None:
    html = render_app(_sample_view())
    css = asset_text("app.css") + asset_text("modules.css")

    assert "thesis-evidence" in html
    assert "升级条件" in html
    assert "decision-followup" not in html
    assert "data-market-horizon" not in html
    assert "TODAY'S THESIS" not in html
    assert "为什么这样判断" not in html
    assert "什么时候升级判断" not in html
    assert "影响判断的事件" not in html
    assert "candidate-row" not in html
    assert "event-row" not in html
    assert "market-evidence" not in css
    assert "horizon-draw" not in css
