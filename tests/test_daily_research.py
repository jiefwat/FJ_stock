from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import scripts.run_daily_research as daily_research_module
from scripts.run_daily_research import run_daily_research
from stock_ts.prediction_feedback import PredictionStore
from stock_ts.research_engine import (
    ResearchFact,
    ResearchModuleItem,
    ResearchModuleSection,
    ResearchWorkspaceResult,
)

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
        prediction_db=tmp_path / "predictions.sqlite3",
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


class ForecastDailyService:
    def research(self, module, _context, *, refresh=False):
        sections = ()
        if module == "opportunity":
            sections = (
                ResearchModuleSection(
                    key="opportunity-candidates",
                    title="前瞻候选",
                    conclusion="只保留通过闸门的股票。",
                    items=(
                        ResearchModuleItem(
                            kind="candidate",
                            code="600001",
                            name="稳步上行",
                            label="半导体",
                            summary="可进入投资候选",
                            risk="波动仍高",
                            facts=(
                                ResearchFact("阶段判断", "可进入投资候选"),
                                ResearchFact("持续性评分", "82/100"),
                                ResearchFact("入选原因", "多周期趋势同向"),
                                ResearchFact("确认条件", "量能保持"),
                                ResearchFact("失效条件", "跌破十日线"),
                            ),
                        ),
                    ),
                ),
            )
        return ResearchWorkspaceResult(
            ok=True,
            status="complete",
            module=module,
            generated_at=NOW.isoformat(timespec="seconds"),
            verdict=f"{module} 已更新",
            action="继续核查",
            primary_risk="证据变化",
            as_of="2026-07-15",
            subject_count=1,
            module_sections=sections,
        )


class PartialThemeOnlyDailyService(FakeDailyService):
    def research(self, module, _context, *, refresh=False):
        result = super().research(module, _context, refresh=refresh)
        if module != "opportunity":
            return result
        return ResearchWorkspaceResult(
            ok=True,
            status="partial",
            module=module,
            generated_at=NOW.isoformat(timespec="seconds"),
            verdict="主题已出现，但候选证据不足。",
            action="继续核查",
            primary_risk="候选为空",
            module_sections=(
                ResearchModuleSection(
                    key="opportunity-themes",
                    title="主题",
                    conclusion="主题待验证",
                    items=(
                        ResearchModuleItem(
                            kind="theme",
                            name="主题但无股票",
                            label="主题",
                        ),
                    ),
                ),
            ),
        )


def test_daily_research_uses_local_gate_when_remote_has_themes_without_stocks(
    tmp_path, monkeypatch
) -> None:
    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text(
        json.dumps(
            {
                "market": {"trade_date": "2026-07-15"},
                "stocks": {
                    "600001": {
                        "name": "稳步上行",
                        "bars": [
                            {
                                "date": "2026-07-15",
                                "open": 100,
                                "high": 102,
                                "low": 99,
                                "close": 101,
                                "volume": 1000000,
                            }
                        ],
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    local_result = ForecastDailyService().research(
        "opportunity", None, refresh=True
    )
    monkeypatch.setattr(
        daily_research_module,
        "build_local_research",
        lambda *_args, **_kwargs: local_result,
    )

    prediction_db = tmp_path / "predictions.sqlite3"
    result = run_daily_research(
        output_dir=tmp_path / "research",
        service=PartialThemeOnlyDailyService(),
        now=NOW,
        snapshot_path=snapshot,
        prediction_db=prediction_db,
    )

    assert result.ok is True
    assert PredictionStore(prediction_db).count() == 1
    opportunity = json.loads(
        (tmp_path / "research/opportunity/latest.json").read_text(encoding="utf-8")
    )
    candidates = next(
        section["items"]
        for section in opportunity["module_sections"]
        if section["key"] == "opportunity-candidates"
    )
    assert [item["name"] for item in candidates] == ["稳步上行"]


def test_daily_research_records_predictions_and_writes_feedback(tmp_path) -> None:
    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text(
        json.dumps(
            {
                "market": {"trade_date": "2026-07-15"},
                "stocks": {
                    "600001": {
                        "name": "稳步上行",
                        "bars": [
                            {
                                "date": "2026-07-15",
                                "open": 100,
                                "high": 102,
                                "low": 99,
                                "close": 101,
                                "volume": 1000000,
                            }
                        ],
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    prediction_db = tmp_path / "predictions.sqlite3"
    feedback_summary = tmp_path / "research" / "feedback_summary.json"

    result = run_daily_research(
        output_dir=tmp_path / "research",
        service=ForecastDailyService(),
        now=NOW,
        snapshot_path=snapshot,
        prediction_db=prediction_db,
        feedback_summary_path=feedback_summary,
    )

    assert result.ok is True
    assert PredictionStore(prediction_db).count() == 1
    summary = json.loads(feedback_summary.read_text(encoding="utf-8"))
    assert summary["horizon"] == 3
    assert summary["sample_state"] == "暂无到期样本"
    opportunity = json.loads(
        (tmp_path / "research/opportunity/latest.json").read_text(encoding="utf-8")
    )
    feedback = next(
        section
        for section in opportunity["module_sections"]
        if section["key"] == "opportunity-feedback"
    )
    assert feedback["conclusion"] == "暂无到期样本"
