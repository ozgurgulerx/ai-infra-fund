from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
API_SRC = ROOT / "services" / "api" / "src"
for path in (CORE_SRC, API_SRC):
    sys.path.insert(0, str(path))

from ai_infra_fund_api.repositories.model_runs import ModelRunRepository  # noqa: E402
from ai_infra_fund_core.contracts.common import DataClass, ModelRunStatus  # noqa: E402
from ai_infra_fund_core.contracts.model_runs import ModelRun  # noqa: E402


NOW = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)


class ModelRunRepositoryTests(unittest.TestCase):
    def test_persists_successful_model_run_with_parameterized_insert(self) -> None:
        connection = FakeConnection()
        run = model_run(status=ModelRunStatus.SUCCESS, schema_valid=True)

        saved = ModelRunRepository(connection).save(run)

        self.assertEqual(run, saved)
        self.assertEqual(1, connection.commit_count)
        statement, params = connection.cursor_instance.executions[0]
        self.assertIn("INSERT INTO audit.model_runs", statement)
        self.assertNotIn(run.model_id, statement)
        self.assertIn(ModelRunStatus.SUCCESS.value, params)
        self.assertIn([DataClass.PUBLIC_EVIDENCE.value], params)

    def test_persists_failed_model_run_with_error_summary(self) -> None:
        connection = FakeConnection()
        run = model_run(
            model_run_id="model-run-failure",
            status=ModelRunStatus.FAILURE,
            output_hash=None,
            schema_valid=False,
            retry_count=2,
            error_summary="schema validation failed",
        )

        ModelRunRepository(connection).save(run)

        _statement, params = connection.cursor_instance.executions[0]
        self.assertIn(ModelRunStatus.FAILURE.value, params)
        self.assertIn("schema validation failed", params)

    def test_persists_retry_model_run_with_schema_invalid_state(self) -> None:
        connection = FakeConnection()
        run = model_run(
            model_run_id="model-run-retry",
            status=ModelRunStatus.RETRY,
            output_hash=None,
            schema_valid=False,
            retry_count=1,
            error_summary="retrying after invalid schema",
        )

        ModelRunRepository(connection).save(run)

        _statement, params = connection.cursor_instance.executions[0]
        self.assertIn(ModelRunStatus.RETRY.value, params)
        self.assertIn(False, params)
        self.assertIn(1, params)

    def test_persists_denied_model_run_for_policy_blocks(self) -> None:
        connection = FakeConnection()
        run = model_run(
            model_run_id="model-run-denied",
            status=ModelRunStatus.DENIED,
            output_hash=None,
            schema_valid=False,
            data_classes=(DataClass.PRIVATE_RESEARCH,),
            error_summary="data-class policy denied cloud route",
        )

        ModelRunRepository(connection).save(run)

        _statement, params = connection.cursor_instance.executions[0]
        self.assertIn(ModelRunStatus.DENIED.value, params)
        self.assertIn([DataClass.PRIVATE_RESEARCH.value], params)
        self.assertIn("data-class policy denied cloud route", params)


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


def model_run(**overrides: object) -> ModelRun:
    data = {
        "model_run_id": "model-run-success",
        "task_role": "evidence_summary",
        "model_id": "configured-model",
        "deployment": "configured-deployment",
        "provider": "configured-provider",
        "prompt_version": "prompt-v1",
        "input_hash": "a" * 64,
        "output_hash": "b" * 64,
        "latency_ms": 125,
        "token_estimate_input": 1000,
        "token_estimate_output": 200,
        "schema_valid": True,
        "retry_count": 0,
        "data_classes": (DataClass.PUBLIC_EVIDENCE,),
        "status": ModelRunStatus.SUCCESS,
        "error_summary": None,
        "created_at": NOW,
    }
    data.update(overrides)
    return ModelRun(**data)


if __name__ == "__main__":
    unittest.main()
