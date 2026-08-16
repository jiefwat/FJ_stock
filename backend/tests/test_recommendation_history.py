import sqlite3
from datetime import UTC, date, datetime, timedelta

from marketdesk.analysis.recommendation_history import analyse_recommendation_history
from marketdesk.models import (
    RecommendationObservation,
    RecommendationSnapshot,
    RecommendationSnapshotPick,
)
from marketdesk.store import Store


def recommendation_run() -> RecommendationSnapshot:
    return RecommendationSnapshot(
        preset="trend",
        trading_date=date(2026, 7, 1),
        observed_at=datetime(2026, 7, 1, 7, tzinfo=UTC),
        available=True,
        summary="趋势候选已冻结",
        benchmark_symbol="SH.000001",
        benchmark_name="上证指数",
        benchmark_price=1000,
        picks=[
            RecommendationSnapshotPick(
                rank=1,
                symbol="SH.600001",
                name="示例科技",
                sector="半导体",
                entry_price=100,
                score=82,
                evidence_coverage=0.8,
                thesis="趋势与资金同步改善",
                risk_flags=[],
            )
        ],
    )


def test_recommendation_history_uses_fixed_trading_session_horizons() -> None:
    run = recommendation_run()
    observations = [
        RecommendationObservation(
            trading_date=run.trading_date + timedelta(days=index),
            observed_at=run.observed_at + timedelta(days=index),
            benchmark_price=1000 + index,
            prices={"SH.600001": 100 + index},
        )
        for index in range(21)
    ]

    result = analyse_recommendation_history(
        "trend", [(run, observations)], datetime(2026, 7, 21, 8, tzinfo=UTC)
    )

    pick = result.days[0].picks[0]
    assert pick.return_1d == 1
    assert pick.return_5d == 5
    assert pick.return_20d == 20
    assert pick.benchmark_20d_return == 2
    assert pick.excess_20d_return == 18
    assert pick.status == "evaluated"
    assert result.summary.evaluated_count == 1
    assert result.summary.hit_rate_20d == 1
    assert result.summary.benchmark_win_rate_20d == 1


def test_recommendation_store_keeps_daily_run_immutable_and_updates_observation(
    tmp_path,
) -> None:
    store = Store(tmp_path / "recommendations.db")
    original = recommendation_run()
    record = store.save_recommendation_run(original)
    changed = original.model_copy(update={"summary": "不应覆盖", "picks": []})

    same_record = store.save_recommendation_run(changed)
    store.save_recommendation_observation(
        record.id,
        RecommendationObservation(
            trading_date=original.trading_date,
            observed_at=original.observed_at,
            benchmark_price=1000,
            prices={"SH.600001": 100},
        ),
    )
    store.save_recommendation_observation(
        record.id,
        RecommendationObservation(
            trading_date=original.trading_date,
            observed_at=original.observed_at + timedelta(hours=1),
            benchmark_price=1010,
            prices={"SH.600001": 103},
        ),
    )

    assert same_record.id == record.id
    assert store.list_recommendation_runs("trend")[0].snapshot.summary == "趋势候选已冻结"
    observations = store.list_recommendation_observations([record.id])[record.id]
    assert len(observations) == 1
    assert observations[0].prices["SH.600001"] == 103


def test_recommendation_store_keeps_algorithm_versions_separate(tmp_path) -> None:
    store = Store(tmp_path / "recommendation-versions.db")
    legacy = recommendation_run()
    current = legacy.model_copy(
        update={
            "algorithm_version": "strategy-profiles-v2",
            "summary": "策略专属评分已冻结",
        }
    )

    legacy_record = store.save_recommendation_run(legacy)
    current_record = store.save_recommendation_run(current)
    store.save_recommendation_run(current.model_copy(update={"summary": "不应覆盖新算法快照"}))

    assert legacy_record.id != current_record.id
    assert (
        store.list_recommendation_runs("trend", algorithm_version="v1")[0].snapshot.summary
        == "趋势候选已冻结"
    )
    assert (
        store.list_recommendation_runs("trend", algorithm_version="strategy-profiles-v2")[
            0
        ].snapshot.summary
        == "策略专属评分已冻结"
    )


def test_recommendation_store_migrates_legacy_runs_without_rewriting_them(
    tmp_path,
) -> None:
    path = tmp_path / "legacy-recommendations.db"
    legacy = recommendation_run()
    observation = RecommendationObservation(
        trading_date=legacy.trading_date,
        observed_at=legacy.observed_at,
        benchmark_price=1000,
        prices={"SH.600001": 100},
    )
    with sqlite3.connect(path) as connection:
        connection.executescript("""
            CREATE TABLE recommendation_runs (
                id INTEGER PRIMARY KEY,
                preset TEXT NOT NULL,
                trading_date TEXT NOT NULL,
                observed_at TEXT NOT NULL,
                payload TEXT NOT NULL,
                UNIQUE(preset, trading_date)
            );
            CREATE TABLE recommendation_observations (
                id INTEGER PRIMARY KEY,
                run_id INTEGER NOT NULL,
                trading_date TEXT NOT NULL,
                observed_at TEXT NOT NULL,
                payload TEXT NOT NULL,
                UNIQUE(run_id, trading_date),
                FOREIGN KEY(run_id) REFERENCES recommendation_runs(id)
                    ON DELETE CASCADE
            );
        """)
        connection.execute(
            """
            INSERT INTO recommendation_runs(
                id,preset,trading_date,observed_at,payload
            ) VALUES(1,?,?,?,?)
            """,
            (
                legacy.preset,
                legacy.trading_date.isoformat(),
                legacy.observed_at.isoformat(),
                legacy.model_dump_json(exclude={"algorithm_version"}),
            ),
        )
        connection.execute(
            """
            INSERT INTO recommendation_observations(
                id,run_id,trading_date,observed_at,payload
            ) VALUES(1,1,?,?,?)
            """,
            (
                observation.trading_date.isoformat(),
                observation.observed_at.isoformat(),
                observation.model_dump_json(),
            ),
        )

    store = Store(path)
    migrated = store.list_recommendation_runs("trend")[0]
    current = legacy.model_copy(update={"algorithm_version": "strategy-profiles-v2"})
    current_record = store.save_recommendation_run(current)

    assert migrated.id == 1
    assert migrated.snapshot.algorithm_version == "v1"
    assert store.list_recommendation_observations([migrated.id])[migrated.id][0].prices == {
        "SH.600001": 100
    }
    assert current_record.id != migrated.id
    with sqlite3.connect(path) as connection:
        foreign_key = connection.execute(
            "PRAGMA foreign_key_list(recommendation_observations)"
        ).fetchone()
    assert foreign_key is not None
    assert foreign_key[2] == "recommendation_runs"
