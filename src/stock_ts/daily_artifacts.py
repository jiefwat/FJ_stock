from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from html import escape
from pathlib import Path
from traceback import format_exception_only

from .daily_decisions import write_decision_artifact
from .html_report import render_daily_deep_html
from .providers import create_provider
from .workflows import build_daily_deep_report


@dataclass(frozen=True)
class DailyArtifactConfig:
    provider_name: str = "tdx-snapshot"
    holdings_path: str | Path = "data/portfolio/holdings.csv"
    transactions_path: str | Path | None = None
    news_path: str | Path | None = None
    output_dir: str | Path = "reports/daily"
    html_dir: str | Path = "reports/html"
    candidate_limit: int = 20
    focus_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class DailyArtifactResult:
    ok: bool
    trade_date: str
    status_path: Path
    markdown_latest: Path | None = None
    markdown_dated: Path | None = None
    decisions_latest: Path | None = None
    decisions_dated: Path | None = None
    html_latest: Path | None = None
    html_dated: Path | None = None
    error: str = ""


def run_daily_artifact_job(config: DailyArtifactConfig) -> DailyArtifactResult:
    output_dir = Path(config.output_dir)
    html_dir = Path(config.html_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    html_dir.mkdir(parents=True, exist_ok=True)
    status_path = output_dir / "latest.status"

    try:
        provider = create_provider(config.provider_name)
        report = build_daily_deep_report(
            provider,
            holdings_path=None if config.transactions_path else config.holdings_path,
            transactions_path=config.transactions_path,
            news_path=config.news_path,
            candidate_limit=config.candidate_limit,
            focus_codes=list(config.focus_codes) or None,
            provider_name=config.provider_name,
        )
        trade_date = _safe_date_name(report.trade_date)
        caveat_markdown = _holding_data_caveat_markdown(config.holdings_path)
        markdown = report.markdown
        if caveat_markdown:
            markdown = markdown.rstrip() + "\n\n" + caveat_markdown + "\n"
        markdown_latest = output_dir / "latest.md"
        markdown_dated = output_dir / f"{trade_date}.md"
        decisions_latest = output_dir / "latest_decisions.json"
        decisions_dated = output_dir / f"{trade_date}_decisions.json"
        html_latest = html_dir / "latest.html"
        html_dated = html_dir / f"{trade_date}.html"
        html = _append_caveat_html(render_daily_deep_html(report), caveat_markdown)

        markdown_latest.write_text(markdown, encoding="utf-8")
        markdown_dated.write_text(markdown, encoding="utf-8")
        write_decision_artifact(markdown, decisions_latest)
        write_decision_artifact(markdown, decisions_dated)
        html_latest.write_text(html, encoding="utf-8")
        html_dated.write_text(html, encoding="utf-8")
        _write_status(
            status_path,
            [
                "status=ok",
                f"provider={config.provider_name}",
                f"trade_date={report.trade_date}",
                f"generated_at={datetime.now().isoformat(timespec='seconds')}",
                f"markdown={markdown_latest}",
                f"decisions={decisions_latest}",
                f"html={html_latest}",
            ],
        )
        return DailyArtifactResult(
            ok=True,
            trade_date=trade_date,
            status_path=status_path,
            markdown_latest=markdown_latest,
            markdown_dated=markdown_dated,
            decisions_latest=decisions_latest,
            decisions_dated=decisions_dated,
            html_latest=html_latest,
            html_dated=html_dated,
        )
    except Exception as exc:
        error = "".join(format_exception_only(type(exc), exc)).strip()
        _write_status(
            status_path,
            [
                "status=failed",
                f"provider={config.provider_name}",
                f"generated_at={datetime.now().isoformat(timespec='seconds')}",
                f"error={error}",
            ],
        )
        return DailyArtifactResult(
            ok=False,
            trade_date="",
            status_path=status_path,
            error=error,
        )


def _safe_date_name(value: str) -> str:
    cleaned = "".join(ch for ch in value.strip() if ch.isdigit() or ch == "-")
    return cleaned or datetime.now().date().isoformat()


def _write_status(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _holding_data_caveat_markdown(holdings_path: str | Path) -> str:
    path = Path(holdings_path)
    if not path.exists():
        return ""
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    hk_codes = []
    for line in lines[1:]:
        columns = [item.strip() for item in line.split(",")]
        if not columns:
            continue
        code = columns[0]
        if code.startswith("0") and len(code) == 5:
            hk_codes.append(code)
    if not hk_codes:
        return ""
    codes = "、".join(sorted(set(hk_codes)))
    return (
        "## 数据边界\n"
        f"- 港股 {codes} 不在 A 股 TDX 全市场刷新范围内，价格和技术结论必须单独用港股数据源复核；"
        "若页面显示旧价，不可当作当日实时数据。"
    )


def _append_caveat_html(html: str, caveat_markdown: str) -> str:
    if not caveat_markdown:
        return html
    body = "".join(
        f"<p>{escape(line.removeprefix('- ').strip())}</p>"
        for line in caveat_markdown.splitlines()
        if line.startswith("- ")
    )
    section = f"<section><h2>数据边界</h2>{body}</section>"
    return html.replace("</main>", f"{section}</main>")
