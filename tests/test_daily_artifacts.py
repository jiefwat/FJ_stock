from pathlib import Path

from stock_ts.daily_artifacts import DailyArtifactConfig, run_daily_artifact_job


def test_daily_artifact_job_writes_latest_and_dated_reports(tmp_path: Path) -> None:
    result = run_daily_artifact_job(
        DailyArtifactConfig(
            provider_name="sample",
            holdings_path="data/portfolio/holdings.csv",
            output_dir=tmp_path / "daily",
            html_dir=tmp_path / "html",
            candidate_limit=5,
        )
    )

    assert result.ok is True
    assert result.trade_date
    assert result.markdown_latest == tmp_path / "daily" / "latest.md"
    assert result.html_latest == tmp_path / "html" / "latest.html"
    assert result.markdown_dated == tmp_path / "daily" / f"{result.trade_date}.md"
    assert result.html_dated == tmp_path / "html" / f"{result.trade_date}.html"
    assert result.markdown_latest.exists()
    assert result.markdown_dated.exists()
    assert result.html_latest.exists()
    assert result.html_dated.exists()
    markdown = result.markdown_latest.read_text(encoding="utf-8")
    assert "StockTS 每日深度复盘" in markdown
    assert "港股 06088" in markdown
    assert "港股 06088" in result.html_latest.read_text(encoding="utf-8")
    assert "provider=sample" in result.status_path.read_text(encoding="utf-8")


def test_daily_artifact_job_writes_failure_status(tmp_path: Path) -> None:
    result = run_daily_artifact_job(
        DailyArtifactConfig(
            provider_name="sample",
            holdings_path=str(tmp_path / "missing-holdings.csv"),
            output_dir=tmp_path / "daily",
            html_dir=tmp_path / "html",
        )
    )

    assert result.ok is False
    assert result.markdown_latest is None
    assert result.status_path.exists()
    status = result.status_path.read_text(encoding="utf-8")
    assert "status=failed" in status
    assert "missing-holdings.csv" in status
