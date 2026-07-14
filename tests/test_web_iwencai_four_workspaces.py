from __future__ import annotations

from stock_ts.webapp.research_console import (
    ResearchContextOption,
    render_iwencai_research_console,
)


def test_shared_research_console_has_four_module_presets() -> None:
    for module in ("market", "portfolio", "stock", "opportunity"):
        html = render_iwencai_research_console(
            module=module,
            status="configured",
            code="600519" if module in {"portfolio", "stock"} else "",
            name="贵州茅台" if module in {"portfolio", "stock"} else "",
            sector="白酒" if module == "opportunity" else "",
            local_as_of="2026-07-14",
        )

        assert f'data-iwencai-module="{module}"' in html
        assert html.count("data-iwencai-question=") == 4
        assert ("问财研究追问" if module == "stock" else "问财外部核查") in html
        assert "已连接" in html


def test_portfolio_context_options_never_render_private_position_data() -> None:
    html = render_iwencai_research_console(
        module="portfolio",
        status="configured",
        context_options=(
            ResearchContextOption(code="600519", name="贵州茅台", label="贵州茅台 · 600519"),
            ResearchContextOption(code="300750", name="宁德时代", label="宁德时代 · 300750"),
        ),
    )

    assert 'data-iwencai-context' in html
    assert 'data-code="600519"' in html
    assert 'data-name="贵州茅台"' in html
    assert "贵州茅台 · 600519" in html
    for private_field in ("shares", "cost_price", "weight", "股数", "成本", "仓位"):
        assert private_field not in html


def test_research_console_escapes_context_and_disables_when_login_is_unavailable() -> None:
    html = render_iwencai_research_console(
        module="opportunity",
        status="requires_login",
        context_options=(
            ResearchContextOption(
                sector='机器人"><script>alert(1)</script>',
                label='机器人"><script>alert(1)</script>',
            ),
        ),
    )

    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "需启用登录" in html
    assert html.count(" disabled") == 7
