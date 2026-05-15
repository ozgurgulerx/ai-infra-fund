from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
API_SRC = ROOT / "services" / "api" / "src"
WORKER_SRC = ROOT / "services" / "worker" / "src"
for path in (CORE_SRC, API_SRC, WORKER_SRC):
    sys.path.insert(0, str(path))


NOW = datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc)


def _request_record() -> dict[str, Any]:
    return {
        "request_id": "backtest-req-abcd1234",
        "strategy_id": "strategy-ai-infra-v1",
        "dataset_snapshot_ids": ["dataset-snapshot-2026q1"],
        "validation_protocol": "walk_forward_v1",
        "cost_assumptions": {"spread_bps": "5"},
        "pipeline_inputs": _pipeline_inputs_payload(),
        "formula_version": "v1",
        "model_run_id": "model-run-shadow-001",
        "git_sha": "abc1234",
        "as_of": NOW.isoformat(),
        "status": "queued",
    }


def _pipeline_inputs_payload() -> dict[str, Any]:
    return {
        "production_recommendation_id": "recommendation-demo-001",
        "benchmark_id": "benchmark-spx",
        "benchmark_version": "v1",
        "features": [
            {
                "feature_id": "f-momentum-30d",
                "available_at": "2026-03-25T00:00:00+00:00",
            }
        ],
        "predictions": [
            {
                "prediction_id": "p-1",
                "as_of": "2026-03-27T00:00:00+00:00",
                "feature_ids": ["f-momentum-30d"],
            }
        ],
        "strategy_values": ["100", "102", "104"],
        "benchmark_values": ["100", "101", "103"],
        "monte_carlo_returns": ["0.01", "-0.005"],
        "monte_carlo_simulations": 4,
        "monte_carlo_horizon_periods": 2,
        "monte_carlo_seed": 11,
        "model_run_id": "model-run-shadow-001",
        "shadow_output_id": "shadow-output-001",
        "run_artifact_ids": ["run-artifact-001"],
        "available_at": NOW.isoformat(),
        "created_at": NOW.isoformat(),
    }


class FakeBacktestRequestRepository:
    def __init__(self, request: dict[str, Any] | None) -> None:
        self.request = request
        self.lease_calls = 0
        self.running_calls = 0
        self.succeeded_calls: list[tuple[str, str]] = []
        self.failed_calls: list[tuple[str, str]] = []

    def lease_next(self, *, leased_by: str, ttl_seconds: int = 300):
        self.lease_calls += 1
        if self.request is None:
            return None
        return self.request

    def mark_running(self, *, request_id: str) -> None:
        self.running_calls += 1

    def mark_succeeded(self, *, request_id: str, backtest_run_id: str) -> None:
        self.succeeded_calls.append((request_id, backtest_run_id))

    def mark_failed(self, *, request_id: str, error_summary: str) -> None:
        self.failed_calls.append((request_id, error_summary))


class FakeEvaluationPersistenceRepository:
    def __init__(self) -> None:
        self.backtest_runs: list[object] = []
        self.run_artifacts: list[object] = []

    def save_backtest_run(self, run: object) -> object:
        self.backtest_runs.append(run)
        return run

    def save_run_artifact(self, artifact: object) -> object:
        self.run_artifacts.append(artifact)
        return artifact


class FakeEventSink:
    def __init__(self) -> None:
        self.events: list[object] = []

    def __call__(self, event: object) -> None:
        self.events.append(event)


class BacktestOrchestratorTests(unittest.TestCase):
    def test_orchestrator_processes_queued_request_and_persists_artifacts(self) -> None:
        from ai_infra_fund_worker.backtest_orchestrator import process_next_backtest

        repo = FakeBacktestRequestRepository(_request_record())
        eval_repo = FakeEvaluationPersistenceRepository()
        sink = FakeEventSink()

        outcome = process_next_backtest(
            request_repository=repo,
            evaluation_repository=eval_repo,
            event_sink=sink,
            worker_id="worker-test-1",
            now=lambda: NOW,
        )

        self.assertEqual("succeeded", outcome.status)
        self.assertEqual(1, repo.running_calls)
        self.assertEqual(1, len(repo.succeeded_calls))
        self.assertEqual([], repo.failed_calls)
        self.assertEqual(1, len(eval_repo.backtest_runs))
        self.assertEqual(1, len(eval_repo.run_artifacts))
        kinds = [event.kind for event in sink.events]  # type: ignore[attr-defined]
        self.assertEqual(
            ["backtest_started", "shadow_comparison_recorded", "backtest_completed"],
            kinds,
        )

    def test_orchestrator_returns_idle_when_queue_empty(self) -> None:
        from ai_infra_fund_worker.backtest_orchestrator import process_next_backtest

        repo = FakeBacktestRequestRepository(None)
        eval_repo = FakeEvaluationPersistenceRepository()
        sink = FakeEventSink()

        outcome = process_next_backtest(
            request_repository=repo,
            evaluation_repository=eval_repo,
            event_sink=sink,
            worker_id="worker-test-1",
            now=lambda: NOW,
        )

        self.assertEqual("idle", outcome.status)
        self.assertEqual([], sink.events)
        self.assertEqual([], eval_repo.backtest_runs)

    def test_orchestrator_marks_failure_when_pipeline_raises(self) -> None:
        from ai_infra_fund_worker.backtest_orchestrator import process_next_backtest

        bad_request = _request_record()
        # Drop required pipeline field to force ValueError in input reconstruction.
        bad_request["pipeline_inputs"] = {"missing": "everything"}

        repo = FakeBacktestRequestRepository(bad_request)
        eval_repo = FakeEvaluationPersistenceRepository()
        sink = FakeEventSink()

        outcome = process_next_backtest(
            request_repository=repo,
            evaluation_repository=eval_repo,
            event_sink=sink,
            worker_id="worker-test-1",
            now=lambda: NOW,
        )

        self.assertEqual("failed", outcome.status)
        self.assertEqual(1, len(repo.failed_calls))
        self.assertEqual([], eval_repo.backtest_runs)
        kinds = [event.kind for event in sink.events]  # type: ignore[attr-defined]
        self.assertIn("backtest_started", kinds)

    def test_orchestrator_rejects_lookahead_available_at_after_as_of(self) -> None:
        from ai_infra_fund_worker.backtest_orchestrator import process_next_backtest

        leaky_request = _request_record()
        # available_at is one day AFTER as_of — forbidden by the lookahead invariant.
        leaky_request["pipeline_inputs"]["available_at"] = datetime(
            2026, 4, 2, 12, 0, tzinfo=timezone.utc
        ).isoformat()

        repo = FakeBacktestRequestRepository(leaky_request)
        eval_repo = FakeEvaluationPersistenceRepository()
        sink = FakeEventSink()

        outcome = process_next_backtest(
            request_repository=repo,
            evaluation_repository=eval_repo,
            event_sink=sink,
            worker_id="worker-test-1",
            now=lambda: NOW,
        )

        self.assertEqual("failed", outcome.status)
        self.assertEqual([], repo.succeeded_calls)
        self.assertEqual(1, len(repo.failed_calls))
        self.assertIn("LookaheadViolationError", repo.failed_calls[0][1])
        self.assertEqual([], eval_repo.backtest_runs)
        self.assertEqual([], eval_repo.run_artifacts)

    def test_orchestrator_fails_when_as_of_missing(self) -> None:
        from ai_infra_fund_worker.backtest_orchestrator import process_next_backtest

        request = _request_record()
        del request["as_of"]

        repo = FakeBacktestRequestRepository(request)
        eval_repo = FakeEvaluationPersistenceRepository()
        sink = FakeEventSink()

        outcome = process_next_backtest(
            request_repository=repo,
            evaluation_repository=eval_repo,
            event_sink=sink,
            worker_id="worker-test-1",
            now=lambda: NOW,
        )

        self.assertEqual("failed", outcome.status)
        self.assertIn("as_of", repo.failed_calls[0][1])
        self.assertEqual([], eval_repo.backtest_runs)

    def test_orchestrator_rejects_request_when_bias_check_fails(self) -> None:
        from ai_infra_fund_worker.backtest_orchestrator import process_next_backtest

        leaky_request = _request_record()
        # Feature's available_at AFTER the prediction's as_of — bias check must fail.
        leaky_request["pipeline_inputs"]["features"] = [
            {
                "feature_id": "f-momentum-30d",
                "available_at": "2026-03-30T00:00:00+00:00",
            }
        ]

        repo = FakeBacktestRequestRepository(leaky_request)
        eval_repo = FakeEvaluationPersistenceRepository()
        sink = FakeEventSink()

        outcome = process_next_backtest(
            request_repository=repo,
            evaluation_repository=eval_repo,
            event_sink=sink,
            worker_id="worker-test-1",
            now=lambda: NOW,
        )

        self.assertEqual("failed", outcome.status)
        self.assertEqual([], repo.succeeded_calls)
        self.assertEqual(1, len(repo.failed_calls))
        self.assertIn("BiasCheckFailedError", repo.failed_calls[0][1])
        self.assertEqual([], eval_repo.backtest_runs)
        self.assertEqual([], eval_repo.run_artifacts)


def _decimal(value: str) -> Decimal:
    return Decimal(value)


if __name__ == "__main__":
    unittest.main()
