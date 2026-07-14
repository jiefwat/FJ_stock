from __future__ import annotations

from stock_ts.providers.sample import SampleDataProvider
from stock_ts.web import render_page
from stock_ts.webapp.research_console import (
    ResearchContextOption,
    render_iwencai_research_console,
)
from stock_ts.webapp.shell import app_script
from stock_ts.webapp.styles import CSS


def _workspace(html: str, key: str) -> str:
    start = html.index(f'id="{key}"')
    next_workspace = html.find('<section class="workspace-pane', start + 1)
    return html[start:] if next_workspace == -1 else html[start:next_workspace]


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


def test_context_modules_disable_queries_when_no_target_exists() -> None:
    portfolio = render_iwencai_research_console(module="portfolio", status="configured")
    opportunity = render_iwencai_research_console(module="opportunity", status="configured")

    assert "暂无持仓可核查" in portfolio
    assert "先录入持仓" in portfolio
    assert portfolio.count(" disabled") == 6
    assert "暂无板块或候选" in opportunity
    assert "先刷新候选" in opportunity
    assert opportunity.count(" disabled") == 6


def test_four_workspaces_each_render_one_research_console_in_decision_order() -> None:
    html = render_page(
        stock_code="600519",
        provider_name="sample",
        provider=SampleDataProvider(),
        holdings_path="data/portfolio/holdings.csv",
    )
    workspaces = {
        key: _workspace(html, key)
        for key in ("market", "portfolio", "stock", "opportunity")
    }

    assert all(
        section.count('data-iwencai-research="true"') == 1
        for section in workspaces.values()
    )
    assert workspaces["market"].index("五步风险决策轨道") < workspaces["market"].index(
        "问财外部核查"
    ) < workspaces["market"].index("三情景推演")
    assert workspaces["portfolio"].index("处置队列") < workspaces["portfolio"].index(
        "问财外部核查"
    ) < workspaces["portfolio"].index("持仓证据")
    assert workspaces["stock"].index("关键证据") < workspaces["stock"].index(
        "问财研究追问"
    )
    assert workspaces["opportunity"].index("证据漏斗") < workspaces["opportunity"].index(
        "问财外部核查"
    ) < workspaces["opportunity"].index("研究候选")


def test_portfolio_and_opportunity_consoles_only_expose_minimum_context() -> None:
    html = render_page(
        stock_code="600519",
        provider_name="sample",
        provider=SampleDataProvider(),
        holdings_path="data/portfolio/holdings.csv",
    )
    for key in ("portfolio", "opportunity"):
        workspace = _workspace(html, key)
        console = workspace.split('data-iwencai-research="true"', 1)[1].split("</section>", 1)[0]
        assert "data-code=" in console or "data-sector=" in console
        for private_field in ("data-shares", "data-cost", "data-weight", "cost_price"):
            assert private_field not in console


def test_opportunity_context_selector_caps_visible_choices() -> None:
    html = render_page(
        stock_code="600519",
        provider_name="sample",
        provider=SampleDataProvider(),
        holdings_path="data/portfolio/holdings.csv",
    )
    workspace = _workspace(html, "opportunity")
    console = workspace.split('data-iwencai-research="true"', 1)[1].split("</section>", 1)[0]

    assert console.count("<option") <= 14


def test_shared_script_posts_module_and_selected_allowlisted_context() -> None:
    script = app_script()

    for fragment in (
        "consoleElement.dataset.iwencaiModule",
        "querySelector('[data-iwencai-context]')",
        "selectedOption.dataset.code",
        "selectedOption.dataset.name",
        "selectedOption.dataset.sector",
        "context:",
    ):
        assert fragment in script
    assert "researchResult.replaceChildren" in script
    assert ".textContent =" in script
    assert "researchResult.innerHTML" not in script


def test_context_selector_is_compact_and_stacks_on_mobile() -> None:
    assert ".iwencai-context-select" in CSS
    mobile = CSS.split("@media (max-width: 760px)", 1)[1]
    assert ".iwencai-context-select" in mobile
    assert "grid-template-columns: 1fr" in mobile
