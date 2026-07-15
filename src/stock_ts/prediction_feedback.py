from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median

from .models import DailyBar

MODEL_VERSION = "continuation-v1"
HORIZONS = (1, 3, 5, 10)
USEFULNESS_VALUES = {"有用", "没用"}
REASON_VALUES = {"原因正确", "原因错误"}
DISPOSITION_VALUES = {"已关注", "已忽略"}


@dataclass(frozen=True)
class PredictionInput:
    baseline_trade_date: str
    baseline_price: float
    subject_code: str
    subject_name: str
    theme: str
    stage: str
    score: int
    confidence: str
    support: str
    counter_evidence: str
    confirmation: str
    invalidation: str
    data_as_of: str
    evidence_as_of: str
    confirmation_price: float | None = None
    invalidation_price: float | None = None
    benchmark_code: str = "000001"
    model_version: str = MODEL_VERSION
    snapshot_fingerprint: str = ""
    created_at: str = ""


@dataclass(frozen=True)
class PredictionRecord(PredictionInput):
    prediction_id: str = ""


@dataclass(frozen=True)
class PredictionOutcome:
    prediction_id: str
    horizon: int
    evaluated_at: str
    target_trade_date: str
    absolute_return: float
    benchmark_return: float
    excess_return: float
    mfe: float
    mae: float
    confirmation_triggered: bool
    invalidation_triggered: bool
    result: str
    miss_reason: str


@dataclass(frozen=True)
class PredictionSummary:
    horizon: int
    sample_count: int
    sample_state: str
    hit_rate: float
    average_excess_return: float
    median_excess_return: float
    average_mae: float
    top_miss_reason: str
    calibration: dict[str, dict[str, float | int]]

    def to_public_dict(self) -> dict[str, object]:
        return {
            "horizon": self.horizon,
            "sample_count": self.sample_count,
            "sample_state": self.sample_state,
            "hit_rate": self.hit_rate,
            "average_excess_return": self.average_excess_return,
            "median_excess_return": self.median_excess_return,
            "average_mae": self.average_mae,
            "top_miss_reason": self.top_miss_reason,
            "calibration": self.calibration,
        }


@dataclass(frozen=True)
class UserPredictionFeedback:
    prediction_id: str
    user_id: int
    usefulness: str
    reason_accuracy: str
    disposition: str
    updated_at: str


class PredictionStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS predictions (
                    prediction_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    baseline_trade_date TEXT NOT NULL,
                    baseline_price REAL NOT NULL,
                    subject_code TEXT NOT NULL,
                    subject_name TEXT NOT NULL,
                    theme TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    confidence TEXT NOT NULL,
                    support TEXT NOT NULL,
                    counter_evidence TEXT NOT NULL,
                    confirmation TEXT NOT NULL,
                    invalidation TEXT NOT NULL,
                    confirmation_price REAL,
                    invalidation_price REAL,
                    benchmark_code TEXT NOT NULL,
                    data_as_of TEXT NOT NULL,
                    evidence_as_of TEXT NOT NULL,
                    model_version TEXT NOT NULL,
                    snapshot_fingerprint TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS prediction_outcomes (
                    prediction_id TEXT NOT NULL,
                    horizon INTEGER NOT NULL,
                    evaluated_at TEXT NOT NULL,
                    target_trade_date TEXT NOT NULL,
                    absolute_return REAL NOT NULL,
                    benchmark_return REAL NOT NULL,
                    excess_return REAL NOT NULL,
                    mfe REAL NOT NULL,
                    mae REAL NOT NULL,
                    confirmation_triggered INTEGER NOT NULL,
                    invalidation_triggered INTEGER NOT NULL,
                    result TEXT NOT NULL,
                    miss_reason TEXT NOT NULL,
                    PRIMARY KEY (prediction_id, horizon),
                    FOREIGN KEY (prediction_id) REFERENCES predictions(prediction_id)
                );
                CREATE TABLE IF NOT EXISTS prediction_user_feedback (
                    prediction_id TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    usefulness TEXT NOT NULL,
                    reason_accuracy TEXT NOT NULL,
                    disposition TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (prediction_id, user_id),
                    FOREIGN KEY (prediction_id) REFERENCES predictions(prediction_id)
                );
                CREATE TABLE IF NOT EXISTS benchmark_closes (
                    benchmark_code TEXT NOT NULL,
                    trade_date TEXT NOT NULL,
                    close REAL NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (benchmark_code, trade_date)
                );
                """
            )

    def record(self, prediction: PredictionInput) -> str:
        prediction_id = prediction_identifier(prediction)
        created_at = prediction.created_at or _now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO predictions (
                    prediction_id, created_at, baseline_trade_date, baseline_price,
                    subject_code, subject_name, theme, stage, score, confidence,
                    support, counter_evidence, confirmation, invalidation,
                    confirmation_price, invalidation_price, benchmark_code,
                    data_as_of, evidence_as_of, model_version, snapshot_fingerprint
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    prediction_id,
                    created_at,
                    prediction.baseline_trade_date,
                    prediction.baseline_price,
                    prediction.subject_code,
                    prediction.subject_name,
                    prediction.theme,
                    prediction.stage,
                    prediction.score,
                    prediction.confidence,
                    prediction.support,
                    prediction.counter_evidence,
                    prediction.confirmation,
                    prediction.invalidation,
                    prediction.confirmation_price,
                    prediction.invalidation_price,
                    prediction.benchmark_code,
                    prediction.data_as_of,
                    prediction.evidence_as_of,
                    prediction.model_version,
                    prediction.snapshot_fingerprint,
                ),
            )
        return prediction_id

    def count(self) -> int:
        with self._connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM predictions").fetchone()
        return int(row["count"] if row is not None else 0)

    def get(self, prediction_id: str) -> PredictionRecord:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM predictions WHERE prediction_id = ?", (prediction_id,)
            ).fetchone()
        if row is None:
            raise KeyError(prediction_id)
        return _prediction_record(row)

    def pending_predictions(self) -> tuple[PredictionRecord, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT p.* FROM predictions p
                WHERE (SELECT COUNT(*) FROM prediction_outcomes o
                       WHERE o.prediction_id = p.prediction_id) < ?
                ORDER BY p.baseline_trade_date, p.subject_code
                """,
                (len(HORIZONS),),
            ).fetchall()
        return tuple(_prediction_record(row) for row in rows)

    def evaluate_prediction(
        self,
        prediction_id: str,
        *,
        stock_bars: Iterable[DailyBar],
        benchmark_bars: Iterable[DailyBar],
        evaluated_at: str = "",
    ) -> tuple[PredictionOutcome, ...]:
        prediction = self.get(prediction_id)
        stock = sorted(stock_bars, key=lambda item: item.date)
        benchmark = sorted(benchmark_bars, key=lambda item: item.date)
        stock_start = _bar_index(stock, prediction.baseline_trade_date)
        benchmark_start = _bar_index(benchmark, prediction.baseline_trade_date)
        if stock_start is None or benchmark_start is None:
            return ()
        evaluation_time = evaluated_at or _now()
        outcomes: list[PredictionOutcome] = []
        for horizon in HORIZONS:
            stock_target = stock_start + horizon
            benchmark_target = benchmark_start + horizon
            if stock_target >= len(stock) or benchmark_target >= len(benchmark):
                continue
            window = stock[stock_start + 1 : stock_target + 1]
            target = stock[stock_target]
            benchmark_target_bar = benchmark[benchmark_target]
            benchmark_base = benchmark[benchmark_start].close
            absolute_return = _pct(prediction.baseline_price, target.close)
            benchmark_return = _pct(benchmark_base, benchmark_target_bar.close)
            confirmation_triggered = bool(
                prediction.confirmation_price is not None
                and any(item.high >= prediction.confirmation_price for item in window)
            )
            invalidation_triggered = bool(
                prediction.invalidation_price is not None
                and any(item.low <= prediction.invalidation_price for item in window)
            )
            excess_return = absolute_return - benchmark_return
            result, miss_reason = _outcome_result(
                excess_return=excess_return,
                confirmation_triggered=confirmation_triggered,
                invalidation_triggered=invalidation_triggered,
            )
            outcome = PredictionOutcome(
                prediction_id=prediction_id,
                horizon=horizon,
                evaluated_at=evaluation_time,
                target_trade_date=target.date,
                absolute_return=round(absolute_return, 4),
                benchmark_return=round(benchmark_return, 4),
                excess_return=round(excess_return, 4),
                mfe=round(_pct(prediction.baseline_price, max(item.high for item in window)), 4),
                mae=round(_pct(prediction.baseline_price, min(item.low for item in window)), 4),
                confirmation_triggered=confirmation_triggered,
                invalidation_triggered=invalidation_triggered,
                result=result,
                miss_reason=miss_reason,
            )
            self._save_outcome(outcome)
            outcomes.append(outcome)
        return tuple(outcomes)

    def _save_outcome(self, outcome: PredictionOutcome) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO prediction_outcomes (
                    prediction_id, horizon, evaluated_at, target_trade_date,
                    absolute_return, benchmark_return, excess_return, mfe, mae,
                    confirmation_triggered, invalidation_triggered, result, miss_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    outcome.prediction_id,
                    outcome.horizon,
                    outcome.evaluated_at,
                    outcome.target_trade_date,
                    outcome.absolute_return,
                    outcome.benchmark_return,
                    outcome.excess_return,
                    outcome.mfe,
                    outcome.mae,
                    int(outcome.confirmation_triggered),
                    int(outcome.invalidation_triggered),
                    outcome.result,
                    outcome.miss_reason,
                ),
            )

    def outcomes_for(self, prediction_id: str) -> tuple[PredictionOutcome, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM prediction_outcomes WHERE prediction_id = ? ORDER BY horizon",
                (prediction_id,),
            ).fetchall()
        return tuple(_prediction_outcome(row) for row in rows)

    def summary(self, *, horizon: int = 3, limit: int = 20) -> PredictionSummary:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT o.*, p.confidence FROM prediction_outcomes o
                JOIN predictions p ON p.prediction_id = o.prediction_id
                WHERE o.horizon = ?
                ORDER BY o.target_trade_date DESC, o.prediction_id
                LIMIT ?
                """,
                (horizon, limit),
            ).fetchall()
        if not rows:
            return PredictionSummary(
                horizon=horizon,
                sample_count=0,
                sample_state="暂无到期样本",
                hit_rate=0.0,
                average_excess_return=0.0,
                median_excess_return=0.0,
                average_mae=0.0,
                top_miss_reason="暂无",
                calibration={},
            )
        results = [str(row["result"]) for row in rows]
        excess = [float(row["excess_return"]) for row in rows]
        maes = [float(row["mae"]) for row in rows]
        calibration: dict[str, dict[str, float | int]] = {}
        for confidence in sorted({str(row["confidence"]) for row in rows}):
            bucket = [row for row in rows if str(row["confidence"]) == confidence]
            hits = sum(str(row["result"]) == "命中" for row in bucket)
            calibration[confidence] = {
                "count": len(bucket),
                "hit_rate": round(hits / len(bucket) * 100, 2),
            }
        miss_reasons = [str(row["miss_reason"]) for row in rows if row["miss_reason"]]
        top_miss_reason = max(set(miss_reasons), key=miss_reasons.count) if miss_reasons else "暂无"
        return PredictionSummary(
            horizon=horizon,
            sample_count=len(rows),
            sample_state="样本积累中" if len(rows) < 20 else "可校准",
            hit_rate=round(results.count("命中") / len(rows) * 100, 2),
            average_excess_return=round(mean(excess), 4),
            median_excess_return=round(median(excess), 4),
            average_mae=round(mean(maes), 4),
            top_miss_reason=top_miss_reason,
            calibration=calibration,
        )

    def record_user_feedback(
        self,
        *,
        prediction_id: str,
        user_id: int,
        usefulness: str,
        reason_accuracy: str,
        disposition: str,
    ) -> None:
        self.get(prediction_id)
        if usefulness not in USEFULNESS_VALUES:
            raise ValueError("usefulness 无效")
        if reason_accuracy not in REASON_VALUES:
            raise ValueError("reason_accuracy 无效")
        if disposition not in DISPOSITION_VALUES:
            raise ValueError("disposition 无效")
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO prediction_user_feedback (
                    prediction_id, user_id, usefulness, reason_accuracy,
                    disposition, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(prediction_id, user_id) DO UPDATE SET
                    usefulness=excluded.usefulness,
                    reason_accuracy=excluded.reason_accuracy,
                    disposition=excluded.disposition,
                    updated_at=excluded.updated_at
                """,
                (
                    prediction_id,
                    user_id,
                    usefulness,
                    reason_accuracy,
                    disposition,
                    _now(),
                ),
            )

    def user_feedback(self, prediction_id: str, *, user_id: int) -> UserPredictionFeedback:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM prediction_user_feedback
                WHERE prediction_id = ? AND user_id = ?
                """,
                (prediction_id, user_id),
            ).fetchone()
        if row is None:
            raise KeyError((prediction_id, user_id))
        return UserPredictionFeedback(
            prediction_id=str(row["prediction_id"]),
            user_id=int(row["user_id"]),
            usefulness=str(row["usefulness"]),
            reason_accuracy=str(row["reason_accuracy"]),
            disposition=str(row["disposition"]),
            updated_at=str(row["updated_at"]),
        )

    def record_benchmark_close(self, code: str, trade_date: str, close: float) -> None:
        if not code or not trade_date or close <= 0:
            return
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO benchmark_closes (
                    benchmark_code, trade_date, close, updated_at
                ) VALUES (?, ?, ?, ?)
                ON CONFLICT(benchmark_code, trade_date) DO UPDATE SET
                    close=excluded.close,
                    updated_at=excluded.updated_at
                """,
                (code, trade_date, close, _now()),
            )

    def benchmark_bars(self, code: str) -> tuple[DailyBar, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT trade_date, close FROM benchmark_closes
                WHERE benchmark_code = ? ORDER BY trade_date
                """,
                (code,),
            ).fetchall()
        return tuple(
            DailyBar(
                date=str(row["trade_date"]),
                open=float(row["close"]),
                high=float(row["close"]),
                low=float(row["close"]),
                close=float(row["close"]),
                volume=0.0,
            )
            for row in rows
        )


def prediction_identifier(prediction: PredictionInput) -> str:
    stable = {
        "baseline_trade_date": prediction.baseline_trade_date,
        "subject_code": prediction.subject_code,
        "model_version": prediction.model_version,
        "snapshot_fingerprint": prediction.snapshot_fingerprint,
    }
    raw = json.dumps(stable, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def build_feedback_section(summary: PredictionSummary) -> dict[str, object]:
    return {
        "key": "opportunity-feedback",
        "title": "历史预测反馈",
        "conclusion": summary.sample_state,
        "tone": "neutral",
        "items": [
            {
                "kind": "prediction_feedback",
                "code": "",
                "name": "3日窗口",
                "label": summary.sample_state,
                "summary": (
                    f"有效样本 {summary.sample_count}；命中率 {summary.hit_rate:.1f}%；"
                    f"平均超额 {summary.average_excess_return:+.2f}%。"
                ),
                "risk": (
                    f"平均 MAE {summary.average_mae:+.2f}%；"
                    f"主要误判：{summary.top_miss_reason}。"
                ),
                "status": "ready" if summary.sample_count else "missing",
                "facts": [
                    {"label": "样本量", "value": str(summary.sample_count)},
                    {"label": "3日命中率", "value": f"{summary.hit_rate:.1f}%"},
                    {
                        "label": "平均超额",
                        "value": f"{summary.average_excess_return:+.2f}%",
                    },
                    {"label": "平均MAE", "value": f"{summary.average_mae:+.2f}%"},
                ],
            }
        ],
    }


def _prediction_record(row: sqlite3.Row) -> PredictionRecord:
    return PredictionRecord(
        prediction_id=str(row["prediction_id"]),
        created_at=str(row["created_at"]),
        baseline_trade_date=str(row["baseline_trade_date"]),
        baseline_price=float(row["baseline_price"]),
        subject_code=str(row["subject_code"]),
        subject_name=str(row["subject_name"]),
        theme=str(row["theme"]),
        stage=str(row["stage"]),
        score=int(row["score"]),
        confidence=str(row["confidence"]),
        support=str(row["support"]),
        counter_evidence=str(row["counter_evidence"]),
        confirmation=str(row["confirmation"]),
        invalidation=str(row["invalidation"]),
        confirmation_price=(
            float(row["confirmation_price"])
            if row["confirmation_price"] is not None
            else None
        ),
        invalidation_price=(
            float(row["invalidation_price"])
            if row["invalidation_price"] is not None
            else None
        ),
        benchmark_code=str(row["benchmark_code"]),
        data_as_of=str(row["data_as_of"]),
        evidence_as_of=str(row["evidence_as_of"]),
        model_version=str(row["model_version"]),
        snapshot_fingerprint=str(row["snapshot_fingerprint"]),
    )


def _prediction_outcome(row: sqlite3.Row) -> PredictionOutcome:
    return PredictionOutcome(
        prediction_id=str(row["prediction_id"]),
        horizon=int(row["horizon"]),
        evaluated_at=str(row["evaluated_at"]),
        target_trade_date=str(row["target_trade_date"]),
        absolute_return=float(row["absolute_return"]),
        benchmark_return=float(row["benchmark_return"]),
        excess_return=float(row["excess_return"]),
        mfe=float(row["mfe"]),
        mae=float(row["mae"]),
        confirmation_triggered=bool(row["confirmation_triggered"]),
        invalidation_triggered=bool(row["invalidation_triggered"]),
        result=str(row["result"]),
        miss_reason=str(row["miss_reason"]),
    )


def _outcome_result(
    *,
    excess_return: float,
    confirmation_triggered: bool,
    invalidation_triggered: bool,
) -> tuple[str, str]:
    if invalidation_triggered:
        return "已失效", "触发失效条件"
    if confirmation_triggered and excess_return > 0:
        return "命中", ""
    if not confirmation_triggered:
        return "未命中", "确认条件未触发"
    return "未命中", "未取得正超额收益"


def _bar_index(bars: list[DailyBar], trade_date: str) -> int | None:
    return next((index for index, item in enumerate(bars) if item.date == trade_date), None)


def _pct(start: float, end: float) -> float:
    return (end / start - 1) * 100 if start else 0.0


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
