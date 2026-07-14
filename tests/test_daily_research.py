from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.run_daily_research import run_daily_research
from stock_ts.research_engine import ResearchWorkspaceResult

TZ = timezone(timedelta(hours=8))
NOW = datetime(2026, 7, 15, 7, 20, tzinfo=TZ)


class FakeDailyService:
    def research(self, module, _context, *, refresh=False):
        return ResearchWorkspaceResult(
            ok=True,
            status="complete",
            module=module,
            generated_at=NOW.isoformat(timespec="seconds"),
            verdict=f"{module} 已更新",
            action="继续核查",
            primary_risk="证据变化",
            subject_count=5,
        )


def test_daily_research_writes_market_opportunity_and_status(tmp_path) -> None:
    result = run_daily_research(
        output_dir=tmp_path,
        service=FakeDailyService(),
        now=NOW,
    )

    assert result.ok is True
    assert (tmp_path / "market/latest.json").exists()
    assert (tmp_path / "opportunity/latest.json").exists()
    status = json.loads((tmp_path / "daily.status.json").read_text())
    assert status["status"] == "complete"
    assert status["modules"] == {
        "market": "complete",
        "opportunity": "complete",
    }


def test_daily_research_timer_has_three_persistent_checkpoints() -> None:
    timer = Path("deploy/systemd/stock-ts-daily-research.timer").read_text()

    for checkpoint in ("07:20:00", "12:10:00", "18:30:00"):
        assert checkpoint in timer
    assert "Persistent=true" in timer
