from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
API_SRC = ROOT / "services" / "api" / "src"
for path in (CORE_SRC, API_SRC):
    sys.path.insert(0, str(path))

from ai_infra_fund_api.repositories.evaluation import EvaluationRepository  # noqa: E402
from ai_infra_fund_core.contracts.evaluation import BacktestRun, RunArtifact  # noqa: E402


NOW = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)
LATER = datetime(2026, 5, 14, 12, 30, tzinfo=timezone.utc)
HASH_A = "a" * 64
HASH_B = "b" * 64

BACKTEST_FIELDS = (
    "backtest_run_id",
    "strategy_id",
    "dataset_snapshot_ids",
    "validation_protocol",
    "cost_assumptions",
    "metrics",
    "artifact_hash",
    "as_of",
    "available_at",
    "created_at",
)


class EvaluationRepositoryTests(unittest.TestCase):
    def test_persists_backtest_evaluation_with_parameterized_insert(self) -> None:
        connection = FakeConnection()
        run = backtest_run()

        saved = EvaluationRepository(connection).save_backtest_run(run)

        self.assertEqual(run, saved)
        self.assertEqual(1, connection.commit_count)
        statement, params = connection.cursor_instance.executions[0]
        self.assertIn("INSERT INTO audit.backtest_runs", statement)
        self.assertNotIn(run.backtest_run_id, statement)
        self.assertNotIn("dataset-snapshot-20260514-prices", statement)
        self.assertEqual(run.backtest_run_id, params[0])
        self.assertEqual(run.strategy_id, params[1])
        self.assertEqual(["dataset-snapshot-20260514-prices"], params[2])
        self.assertEqual(run.as_of, params[3])
        self.assertEqual(run.available_at, params[4])
        self.assertEqual("succeeded", params[8])
        self.assertIsNone(params[9])

        config = json.loads(params[5])
        metrics = json.loads(params[6])
        cost_model = json.loads(params[7])
        self.assertEqual("walk-forward-v1", config["validation_protocol"])
        self.assertEqual({"scores": "score-formula-v3"}, config["formula_versions"])
        self.assertEqual("nasdaq-100-total-return-v2", config["benchmark_version"])
        self.assertEqual(HASH_A, metrics["artifact_hash"])
        self.assertEqual("nasdaq-100-total-return-v2", metrics["benchmark_version"])
        self.assertEqual({"commission_bps": "1.0", "slippage_bps": "5.0"}, cost_model)

    def test_rejects_backtest_evaluation_without_required_lineage_before_execute(self) -> None:
        invalid_records = (
            (
                backtest_record(dataset_snapshot_ids=()),
                "dataset_snapshot_ids must not be empty",
            ),
            (
                backtest_record(metrics={"benchmark_version": "nasdaq-100-total-return-v2"}),
                "metrics.formula_versions is required",
            ),
            (
                backtest_record(metrics={"formula_versions": {"scores": "score-formula-v3"}}),
                "metrics.benchmark_version is required",
            ),
        )

        for invalid_record, error_message in invalid_records:
            with self.subTest(error_message=error_message):
                connection = FakeConnection()
                with self.assertRaisesRegex(ValueError, error_message):
                    EvaluationRepository(connection).save_backtest_run(invalid_record)

                self.assertEqual(0, connection.commit_count)
                self.assertEqual([], connection.cursor_instance.executions)

    def test_persists_run_artifact_with_parameterized_insert(self) -> None:
        connection = FakeConnection()
        artifact = run_artifact()

        saved = EvaluationRepository(connection).save_run_artifact(artifact)

        self.assertEqual(artifact, saved)
        self.assertEqual(1, connection.commit_count)
        statement, params = connection.cursor_instance.executions[0]
        self.assertIn("INSERT INTO audit.run_artifacts", statement)
        self.assertNotIn(artifact.run_id, statement)
        self.assertNotIn("artifact://evaluations/evaluation-20260514-baseline", statement)
        self.assertEqual(artifact.run_id, params[0])
        self.assertEqual("evaluation", params[1])
        self.assertEqual(HASH_A, params[4])
        self.assertEqual(HASH_B, params[5])
        self.assertEqual("succeeded", params[7])


class FakeCursor:
    def __init__(self) -> None:
        self.executions: list[tuple[str, tuple[object, ...]]] = []

    def execute(self, statement: str, params: tuple[object, ...] | None = None) -> None:
        self.executions.append((statement, params or ()))

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, *_exc: object) -> None:
        return None


class FakeConnection:
    def __init__(self) -> None:
        self.cursor_instance = FakeCursor()
        self.commit_count = 0

    def cursor(self) -> FakeCursor:
        return self.cursor_instance

    def commit(self) -> None:
        self.commit_count += 1


def backtest_run(**overrides: object) -> BacktestRun:
    data = {
        "backtest_run_id": "evaluation-20260514-baseline",
        "strategy_id": "strategy-baseline-weighted",
        "dataset_snapshot_ids": ("dataset-snapshot-20260514-prices",),
        "validation_protocol": "walk-forward-v1",
        "cost_assumptions": {"commission_bps": "1.0", "slippage_bps": "5.0"},
        "metrics": {
            "formula_versions": {"scores": "score-formula-v3"},
            "benchmark_version": "nasdaq-100-total-return-v2",
            "walk_forward": {"splits": 3, "mean_excess_return": "0.04"},
        },
        "artifact_hash": HASH_A,
        "as_of": NOW,
        "available_at": LATER,
        "created_at": NOW,
    }
    data.update(overrides)
    return BacktestRun(**data)


def backtest_record(**overrides: object) -> SimpleNamespace:
    run = backtest_run()
    data = {field: getattr(run, field) for field in BACKTEST_FIELDS}
    data.update(overrides)
    return SimpleNamespace(**data)


def run_artifact(**overrides: object) -> RunArtifact:
    data = {
        "run_id": "evaluation-20260514-baseline-artifact",
        "run_type": "evaluation",
        "started_at": NOW,
        "completed_at": LATER,
        "inputs_hash": HASH_A,
        "output_hash": HASH_B,
        "artifact_uri": "artifact://evaluations/evaluation-20260514-baseline",
        "status": "succeeded",
        "error_summary": None,
        "created_at": NOW,
    }
    data.update(overrides)
    return RunArtifact(**data)


if __name__ == "__main__":
    unittest.main()
