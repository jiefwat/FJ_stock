from __future__ import annotations

import inspect
from dataclasses import replace

from stock_ts.providers.sample import SampleDataProvider
from stock_ts.research.portfolio_dossier_models import (
    PortfolioBoundary,
    PortfolioDossier,
    PortfolioExposure,
    PortfolioMetric,
    PortfolioQueueItem,
    PortfolioVerdict,
)
from stock_ts.web import _render_compact_portfolio_module, render_page
from stock_ts.webapp.portfolio_workspace import render_portfolio_workspace


def _dossier(*, stale: bool = False) -> PortfolioDossier:
    verdict = PortfolioVerdict(
        state="数据暂停" if stale else "风险收缩",
        action="保留账本审计，价格动作待刷新" if stale else "先降集中度，再谈进攻",
        risk_budget="0%" if stale else "40%-60%",
        confidence=0 if stale else 61,
        thesis="成本、股数和暴露可审计；价格动作必须服从市场闸门。",
        primary_risk="单票与行业集中度偏高",
        next_review="刷新行情后重新生成处置队列。" if stale else "下一交易日收盘后复核。",
    )
    queue = (
        PortfolioQueueItem(
            priority=1,
            state="待补数据" if stale else "必须处理",
            code="600001",
            name="风险股份",
            current_weight=0.46,
            cost_context=(
                "成本 10.00 / 现价待刷新 / 盈亏待刷新"
                if stale
                else "成本 10.00 / 现价 8.20 / 盈亏 -18.0%"
            ),
            reason="下降趋势且集中度偏高",
            trigger="待刷新" if stale else "连续弱于指数时降低风险",
            invalidation="待刷新" if stale else "跌破 7.50",
        ),
    )
    boundaries = (
        PortfolioBoundary(
            code="600001",
            name="风险股份",
            current_action="价格动作待刷新" if stale else "降仓",
            target_range="待刷新" if stale else "0%-10%",
            reduce_trigger="待刷新" if stale else "连续弱于指数",
            invalidation="待刷新" if stale else "跌破 7.50",
            prohibited_action="禁止使用旧价格加仓、补仓或机械止损",
        ),
    )
    return PortfolioDossier(
        verdict=verdict,
        metrics=(PortfolioMetric("第一大仓位", "46.0%", "critical", "高集中风险"),),
        queue=queue,
        exposures=(
            PortfolioExposure("行业：机器人", 0.78, "critical", "停止新增同主题仓位"),
        ),
        boundaries=boundaries,
    )


def test_portfolio_workspace_leads_with_one_committee_verdict() -> None:
    html = render_portfolio_workspace(_dossier(), supporting_evidence_html="<p>持仓证据</p>")

    assert html.count('data-primary-portfolio-verdict="true"') == 1
    assert html.index("组合风控结论") < html.index("处置队列")
    assert html.index("处置队列") < html.index("持仓证据")
    assert "风险暴露登记表" in html
    assert "禁止动作" in html
    assert html.count('class="portfolio-evidence essence-evidence"') == 1
    assert "其余 0 项处置" not in html


def test_stale_portfolio_workspace_hides_numeric_price_actions() -> None:
    html = render_portfolio_workspace(_dossier(stale=True))
    primary = html.split("持仓证据", 1)[0]

    assert "数据暂停" in primary
    assert "价格动作待刷新" in primary
    assert "待刷新" in primary
    assert "跌破 7.50" not in primary
    assert "0%-10%" not in primary
    assert "现价 8.20" not in primary


def test_web_portfolio_module_builds_and_renders_one_dossier() -> None:
    source = inspect.getsource(_render_compact_portfolio_module)

    assert source.count("build_portfolio_dossier(") == 1
    assert source.count("render_portfolio_workspace(") == 1
    assert "_render_portfolio_buy_sell_guidance(" not in source


def test_stale_web_portfolio_page_pauses_price_actions() -> None:
    html = render_page(
        stock_code="600519",
        provider_name="sample",
        provider=SampleDataProvider(),
        holdings_path="data/portfolio/holdings.csv",
    )
    start = html.index('id="module-portfolio"')
    end = html.index('</section></div>\n</section>', start)
    portfolio_html = html[start:end]

    assert "数据暂停" in portfolio_html
    assert "价格动作待刷新" in portfolio_html
    assert "持仓证据" in portfolio_html
    assert "买入触发" not in portfolio_html


def test_portfolio_workspace_limits_front_row_to_three_without_losing_audit_records() -> None:
    dossier = _dossier()
    queue_seed = dossier.queue[0]
    boundary_seed = dossier.boundaries[0]
    queue = tuple(
        replace(queue_seed, code=f"6000{index:02d}", name=f"持仓{index:02d}")
        for index in range(1, 8)
    )
    boundaries = tuple(
        replace(boundary_seed, code=f"6000{index:02d}", name=f"持仓{index:02d}")
        for index in range(1, 7)
    )
    html = render_portfolio_workspace(
        replace(dossier, queue=queue, boundaries=boundaries)
    )

    assert html.count('class="portfolio-queue-item') == 7
    front_queue = html.split('class="portfolio-evidence', 1)[0]
    assert front_queue.count('class="portfolio-queue-item') == 3
    assert "其余 4 项处置" in html
    assert html.count('class="portfolio-boundary-card') == 6
    assert html.count('class="portfolio-evidence essence-evidence"') == 1
