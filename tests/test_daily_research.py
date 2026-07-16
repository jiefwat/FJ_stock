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


def test_daily_research_timer_runs_after_each_data_checkpoint() -> None:
    timer = Path("deploy/systemd/stock-ts-daily-research.timer").read_text()

    for checkpoint in ("07:30:00", "09:30:00", "13:30:00", "15:30:00"):
        assert checkpoint in timer
    assert timer.count("OnCalendar=") == 4
    assert "Persistent=true" in timer

    service = Path("deploy/systemd/stock-ts-daily-research.service").read_text()
    assert "After=network-online.target stock-ts-daily-analysis.service" in service


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
                            code="600001.SH",
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
            as_of="2026-07-16T07:20:00+08:00",
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
            status="complete",
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
                ResearchModuleSection(
                    key="opportunity-candidates",
                    title="候选",
                    conclusion="候选与主题不一致",
                    items=(
                        ResearchModuleItem(
                            kind="candidate",
                            code="600002.SH",
                            name="错配候选",
                            label="另一个主题",
                        ),
                    ),
                ),
            ),
        )


def test_daily_research_fuses_local_market_facts_before_saving_snapshot(
    tmp_path, monkeypatch
) -> None:
    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text(
        json.dumps(
            {
                "snapshot_version": "published-v1",
                "market": {"trade_date": "2026-07-15"},
            }
        ),
        encoding="utf-8",
    )

    def local_research(module, *_args, **_kwargs):
        return ResearchWorkspaceResult(
            ok=True,
            status="complete",
            module=module,
            generated_at=NOW.isoformat(timespec="seconds"),
            verdict=f"{module} 本地事实结论",
            action="使用本地行情作为判断底座",
            primary_risk="本地数据缺口",
            subject_count=1,
            delivery="local_fallback",
        )

    monkeypatch.setattr(daily_research_module, "build_local_research", local_research)

    result = run_daily_research(
        output_dir=tmp_path / "research",
        service=FakeDailyService(),
        now=NOW,
        snapshot_path=snapshot,
        prediction_db=tmp_path / "predictions.sqlite3",
    )

    assert result.ok is True
    market = json.loads(
        (tmp_path / "research/market/latest.json").read_text(encoding="utf-8")
    )
    assert market["verdict"] == "market 本地事实结论"
    assert market["delivery"] == "snapshot"
    assert market["evidence_delivery"] == "hybrid"
    assert market["source_snapshot_fingerprint"]
    assert market["source_snapshot_version"] == "published-v1"


def test_daily_research_saves_local_facts_when_enrichment_fails(
    tmp_path, monkeypatch
) -> None:
    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text(
        json.dumps({"market": {"trade_date": "2026-07-15"}}),
        encoding="utf-8",
    )

    def local_research(module, *_args, **_kwargs):
        return ResearchWorkspaceResult(
            ok=True,
            status="complete",
            module=module,
            generated_at=NOW.isoformat(timespec="seconds"),
            verdict=f"{module} 本地可用",
            action="继续使用最后完整行情",
            primary_risk="外部补强暂不可用",
            subject_count=1,
            delivery="local_fallback",
        )

    class ExplodingDailyService:
        def research(self, *_args, **_kwargs):
            raise TimeoutError("external enrichment timed out")

    monkeypatch.setattr(daily_research_module, "build_local_research", local_research)

    result = run_daily_research(
        output_dir=tmp_path / "research",
        service=ExplodingDailyService(),
        now=NOW,
        snapshot_path=snapshot,
        prediction_db=tmp_path / "predictions.sqlite3",
    )

    assert result.ok is True
    status = json.loads(result.status_path.read_text(encoding="utf-8"))
    assert status["status"] == "partial"
    assert status["modules"] == {"market": "complete", "opportunity": "complete"}
    market = json.loads(
        (tmp_path / "research/market/latest.json").read_text(encoding="utf-8")
    )
    assert market["verdict"] == "market 本地可用"
    assert market["evidence_delivery"] == "local_fallback"


def test_daily_research_does_not_publish_when_pipeline_version_changes(
    tmp_path, monkeypatch
) -> None:
    snapshot = tmp_path / "snapshot.json"
    pipeline_status = tmp_path / "pipeline.status"
    snapshot.write_text(
        json.dumps(
            {
                "snapshot_version": "published-v1",
                "market": {"trade_date": "2026-07-15"},
            }
        ),
        encoding="utf-8",
    )
    pipeline_status.write_text(
        "status=ok\nsnapshot_version=published-v1\n", encoding="utf-8"
    )

    class VersionChangingService(FakeDailyService):
        def research(self, module, context, *, refresh=False):
            pipeline_status.write_text(
                "status=ok\nsnapshot_version=published-v2\n", encoding="utf-8"
            )
            return super().research(module, context, refresh=refresh)

    monkeypatch.setattr(
        daily_research_module,
        "build_local_research",
        lambda module, *_args, **_kwargs: FakeDailyService().research(
            module, None, refresh=True
        ),
    )

    result = run_daily_research(
        output_dir=tmp_path / "research",
        service=VersionChangingService(),
        now=NOW,
        snapshot_path=snapshot,
        prediction_db=tmp_path / "predictions.sqlite3",
        pipeline_status_path=pipeline_status,
    )

    assert result.ok is False
    assert not (tmp_path / "research/market/latest.json").exists()


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
    assert feedback["conclusion"] == "暂无可回评样本"
    rendered_feedback = json.dumps(feedback, ensure_ascii=False)
    assert "3日命中率" not in rendered_feedback
    assert "平均超额" not in rendered_feedback
    assert "平均MAE" not in rendered_feedback
    assert "0.0%" not in rendered_feedback
