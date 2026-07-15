from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from stock_ts.models import DailyBar
from stock_ts.prediction_feedback import PredictionInput, PredictionStore


def _bars(code_offset: float = 0.0) -> list[DailyBar]:
    closes = [100, 103, 101, 106, 108, 109, 110, 111, 112, 113, 114]
    return [
        DailyBar(
            date=f"2026-07-{15 + index:02d}",
            open=close - 0.5 + code_offset,
            high=close + 1.0 + code_offset,
            low=close - 2.0 + code_offset,
            close=close + code_offset,
            volume=1_000_000 + index * 10_000,
        )
        for index, close in enumerate(closes)
    ]


def _benchmark_bars() -> list[DailyBar]:
    closes = [100, 101, 101, 102, 103, 103, 104, 104, 105, 105, 106]
    return [
        DailyBar(
            date=f"2026-07-{15 + index:02d}",
            open=close,
            high=close + 0.5,
            low=close - 0.5,
            close=close,
            volume=10_000_000,
        )
        for index, close in enumerate(closes)
    ]


def _prediction(**overrides: object) -> PredictionInput:
    values: dict[str, object] = {
        "baseline_trade_date": "2026-07-15",
        "baseline_price": 100.0,
        "subject_code": "600001",
        "subject_name": "稳步上行",
        "theme": "半导体",
        "stage": "可进入投资候选",
        "score": 82,
        "confidence": "中",
        "support": "多周期趋势同向",
        "counter_evidence": "波动仍高",
        "confirmation": "收盘站上 102",
        "invalidation": "收盘跌破 98",
        "data_as_of": "2026-07-15",
        "evidence_as_of": "2026-07-15",
        "confirmation_price": 102.0,
        "invalidation_price": 98.0,
        "snapshot_fingerprint": "snapshot-a",
    }
    values.update(overrides)
    return PredictionInput(**values)


def test_prediction_is_idempotent_and_original_thesis_is_immutable(tmp_path: Path) -> None:
    store = PredictionStore(tmp_path / "predictions.sqlite3")
    prediction = _prediction()

    first = store.record(prediction)
    second = store.record(replace(prediction, support="事后改写"))

    assert first == second
    assert store.count() == 1
    assert store.get(first).support == "多周期趋势同向"


def test_evaluate_due_horizons_records_returns_mfe_mae_and_excess(tmp_path: Path) -> None:
    store = PredictionStore(tmp_path / "predictions.sqlite3")
    prediction_id = store.record(_prediction())

    evaluated = store.evaluate_prediction(
        prediction_id,
        stock_bars=_bars(),
        benchmark_bars=_benchmark_bars(),
        evaluated_at="2026-07-26T16:00:00+08:00",
    )

    assert {item.horizon for item in evaluated} == {1, 3, 5, 10}
    outcomes = {item.horizon: item for item in store.outcomes_for(prediction_id)}
    assert outcomes[1].absolute_return == 3.0
    assert outcomes[3].absolute_return == 6.0
    assert outcomes[3].benchmark_return == 2.0
    assert outcomes[3].excess_return == 4.0
    assert outcomes[5].mfe == 10.0
    assert outcomes[5].mae == -1.0
    assert outcomes[3].confirmation_triggered is True
    assert outcomes[3].invalidation_triggered is False
    assert outcomes[3].result == "命中"


def test_missing_future_bars_remain_pending_and_out_of_summary(tmp_path: Path) -> None:
    store = PredictionStore(tmp_path / "predictions.sqlite3")
    prediction_id = store.record(_prediction())

    evaluated = store.evaluate_prediction(
        prediction_id,
        stock_bars=_bars()[:3],
        benchmark_bars=_benchmark_bars()[:3],
    )
    summary = store.summary(horizon=3)

    assert {item.horizon for item in evaluated} == {1}
    assert summary.sample_count == 0
    assert summary.sample_state == "暂无到期样本"


def test_summary_marks_small_sample_and_reports_calibration(tmp_path: Path) -> None:
    store = PredictionStore(tmp_path / "predictions.sqlite3")
    for index in range(3):
        prediction_id = store.record(
            _prediction(
                subject_code=f"60000{index + 1}",
                subject_name=f"候选{index + 1}",
                snapshot_fingerprint=f"snapshot-{index}",
                confidence=("高" if index == 0 else "中"),
            )
        )
        store.evaluate_prediction(
            prediction_id,
            stock_bars=_bars(code_offset=float(index)),
            benchmark_bars=_benchmark_bars(),
        )

    summary = store.summary(horizon=3)

    assert summary.sample_count == 3
    assert summary.sample_state == "样本积累中"
    assert summary.hit_rate == 100.0
    assert summary.average_excess_return > 0
    assert summary.average_mae <= 0
    assert summary.calibration == {
        "中": {"count": 2, "hit_rate": 100.0},
        "高": {"count": 1, "hit_rate": 100.0},
    }


def test_user_feedback_is_account_isolated_and_does_not_change_score(tmp_path: Path) -> None:
    store = PredictionStore(tmp_path / "predictions.sqlite3")
    prediction_id = store.record(_prediction())

    store.record_user_feedback(
        prediction_id=prediction_id,
        user_id=1,
        usefulness="有用",
        reason_accuracy="原因正确",
        disposition="已关注",
    )
    store.record_user_feedback(
        prediction_id=prediction_id,
        user_id=2,
        usefulness="没用",
        reason_accuracy="原因错误",
        disposition="已忽略",
    )

    assert store.user_feedback(prediction_id, user_id=1).usefulness == "有用"
    assert store.user_feedback(prediction_id, user_id=2).usefulness == "没用"
    assert store.get(prediction_id).score == 82


def test_benchmark_closes_are_upserted_by_trade_date(tmp_path: Path) -> None:
    store = PredictionStore(tmp_path / "predictions.sqlite3")

    store.record_benchmark_close("000001", "2026-07-15", 3950.0)
    store.record_benchmark_close("000001", "2026-07-15", 3955.0)
    store.record_benchmark_close("000001", "2026-07-16", 3970.0)

    bars = store.benchmark_bars("000001")
    assert [(item.date, item.close) for item in bars] == [
        ("2026-07-15", 3955.0),
        ("2026-07-16", 3970.0),
    ]
