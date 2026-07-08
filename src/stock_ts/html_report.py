from __future__ import annotations

from html import escape

from .deep_models import BatchAnalysisReport, DailyDeepReport, DeepStockReport


def render_deep_stock_html(report: DeepStockReport) -> str:
    return _page(
        "StockTS 深度分析",
        [
            _hero(
                f"{report.name}（{report.code}）",
                report.final_conclusion,
                [
                    ("未来上涨潜力", f"{report.upside.score}/100"),
                    ("趋势", report.trend),
                    ("风险", report.risk_level),
                    ("日期", report.trade_date),
                ],
            ),
            _angle_grid(report),
            _section(
                "多轮对抗",
                "\n".join(
                    _debate_card(item.role, item.thesis, item.evidence, item.rebuttal)
                    for item in report.debate_rounds
                ),
            ),
            _list_section("风险与失效条件", report.invalid_conditions),
            _list_section("跟踪计划", report.action_plan),
            _section("免责声明", f"<p>{escape(report.disclaimer)}</p>"),
        ],
    )


def render_batch_html(report: BatchAnalysisReport) -> str:
    rows = []
    for index, stock in enumerate(report.stocks, start=1):
        rows.append(
            "<tr>"
            f"<td>{index}</td>"
            f"<td>{escape(stock.name)}<br><small>{escape(stock.code)}</small></td>"
            f"<td><strong>{stock.upside.score}</strong><br><small>{escape(stock.upside.label)}</small></td>"
            f"<td>{escape(stock.trend)}</td>"
            f"<td>{escape(stock.risk_level)}</td>"
            f"<td>{escape(stock.final_conclusion)}</td>"
            "</tr>"
        )
    return _page(
        "StockTS 批量深度分析",
        [
            _hero(
                "批量个股深度对比",
                report.market_summary,
                [
                    ("股票数", str(len(report.stocks))),
                    ("市场主线", "、".join(report.sector_mainline) or "未识别"),
                    ("日期", report.trade_date),
                ],
            ),
            _section(
                "排名对比",
                "<table><thead><tr><th>#</th><th>股票</th><th>潜力分</th><th>趋势</th><th>风险</th><th>结论</th></tr></thead>"
                f"<tbody>{''.join(rows)}</tbody></table>",
            ),
            _list_section("使用说明", report.comparison_notes),
        ],
    )


def render_daily_deep_html(report: DailyDeepReport) -> str:
    stock_cards = "\n".join(
        '<article class="stock-card">'
        f"<strong>{escape(stock.name)}（{escape(stock.code)}）</strong>"
        f"<span>{stock.upside.score}/100</span><p>{escape(stock.final_conclusion)}</p></article>"
        for stock in report.stocks
    )
    portfolio_note = "未提供持仓"
    if report.portfolio is not None:
        portfolio_note = (
            f"健康度 {report.portfolio.health_score}/100，浮动盈亏 {report.portfolio.total_pnl:.2f}"
        )
    news_note = report.news.summary if report.news is not None else "未提供新闻舆情"
    return _page(
        "StockTS 每日深度复盘",
        [
            _hero(
                "StockTS 每日深度复盘",
                report.market.summary,
                [
                    ("市场热度", f"{report.market.heat_score}/100"),
                    ("板块主线", "、".join(report.sectors.market_mainline)),
                    ("持仓", portfolio_note),
                    ("日期", report.trade_date),
                ],
            ),
            _section("新闻舆情", f"<p>{escape(news_note)}</p>"),
            _section("个股深度观察", f'<div class="stock-grid">{stock_cards}</div>'),
            _section(
                "候选股票池",
                "<ol>"
                + "".join(
                    f"<li>{escape(item.name)}（{escape(item.code)}）：{item.score}/100</li>"
                    for item in report.candidates.candidates[:10]
                )
                + "</ol>",
            ),
            _section("免责声明", f"<p>{escape(report.disclaimer)}</p>"),
        ],
    )


def _page(title: str, blocks: list[str]) -> str:
    css = "\n".join(
        [
            ":root{--ink:#17211b;--muted:#66736d;--paper:#f5f0e7;",
            "--card:#fffaf1;--accent:#0f766e;--risk:#b45309;--line:#d8cbbb;}",
            "*{box-sizing:border-box}",
            "body{margin:0;font-family:Georgia,'Noto Serif SC',serif;color:var(--ink);",
            "background:radial-gradient(circle at top left,#d9f2e8,transparent 32%),",
            "linear-gradient(135deg,#f9f4e8,#eef6f1);}",
            "main{max-width:1180px;margin:0 auto;padding:40px 20px 64px}",
            ".hero{border:1px solid var(--line);border-radius:28px;padding:34px;",
            "background:linear-gradient(135deg,#fffdf6,#e6f3ee);",
            "box-shadow:0 24px 80px #38544922;}",
            "h1{margin:0 0 12px;font-size:clamp(30px,5vw,58px);",
            "letter-spacing:-.04em}",
            ".lead{font-size:18px;color:var(--muted);line-height:1.7;max-width:850px}",
            ".kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));",
            "gap:14px;margin-top:24px}",
            ".kpi{background:#ffffffaa;border:1px solid var(--line);",
            "border-radius:18px;padding:16px}",
            ".kpi b{display:block;font-size:24px}.kpi span{color:var(--muted);",
            "font-size:13px}",
            "section{margin-top:22px;border:1px solid var(--line);border-radius:24px;",
            "padding:24px;background:var(--card)}",
            "h2{margin:0 0 16px;font-size:24px}",
            ".angle-grid,.stock-grid{display:grid;",
            "grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}",
            ".angle,.stock-card,.debate-card{border:1px solid var(--line);",
            "border-radius:18px;background:#fffefa;padding:16px}",
            ".score{font-size:28px;font-weight:800;color:var(--accent)}",
            ".stance{display:inline-block;margin-top:8px;padding:4px 10px;",
            "border-radius:999px;background:#dff3ec;color:#075e55}",
            ".debate-card{margin-bottom:14px}.debate-card h3{margin:0 0 8px}",
            ".debate-card ul{padding-left:20px;color:var(--muted)}",
            "table{width:100%;border-collapse:collapse}",
            "th,td{padding:12px;border-bottom:1px solid var(--line);",
            "text-align:left;vertical-align:top}",
            "small{color:var(--muted)}ol,ul{line-height:1.8}",
            ".stock-card span{float:right;color:var(--accent);font-weight:800}",
            "@media(max-width:640px){main{padding:24px 12px}",
            ".hero,section{border-radius:18px;padding:18px}table{font-size:13px}}",
        ]
    )
    return (
        "<!doctype html>\n"
        '<html lang="zh-CN">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{escape(title)}</title>\n"
        "<style>\n"
        f"{css}\n"
        "</style>\n"
        "</head>\n"
        f"<body><main>{''.join(blocks)}</main></body>\n"
        "</html>\n"
    )


def _hero(title: str, lead: str, kpis: list[tuple[str, str]]) -> str:
    cards = "".join(
        f'<div class="kpi"><span>{escape(label)}</span><b>{escape(value)}</b></div>'
        for label, value in kpis
    )
    return (
        '<header class="hero">'
        f"<h1>{escape(title)}</h1>"
        f'<p class="lead">{escape(lead)}</p>'
        f'<div class="kpis">{cards}</div>'
        "</header>"
    )


def _angle_grid(report: DeepStockReport) -> str:
    cards = "".join(
        '<article class="angle">'
        f"<h3>{escape(angle.name)}</h3>"
        f'<div class="score">{angle.score}</div>'
        f'<span class="stance">{escape(angle.stance)}</span>'
        f"<p>{escape(angle.evidence)}</p>"
        "</article>"
        for angle in report.angles
    )
    return _section("多角度评分", f'<div class="angle-grid">{cards}</div>')


def _debate_card(role: str, thesis: str, evidence: list[str], rebuttal: str) -> str:
    items = "".join(f"<li>{escape(item)}</li>" for item in evidence)
    return (
        '<article class="debate-card">'
        f"<h3>{escape(role)}</h3>"
        f"<p>{escape(thesis)}</p>"
        f"<ul>{items}</ul>"
        f"<p><strong>约束：</strong>{escape(rebuttal)}</p>"
        "</article>"
    )


def _section(title: str, body: str) -> str:
    return f"<section><h2>{escape(title)}</h2>{body}</section>"


def _list_section(title: str, items: list[str]) -> str:
    body = "<ul>" + "".join(f"<li>{escape(item)}</li>" for item in items) + "</ul>"
    return _section(title, body)
