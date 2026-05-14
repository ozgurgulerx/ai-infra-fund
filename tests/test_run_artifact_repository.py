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

from ai_infra_fund_api.repositories.run_artifacts import RunArtifactRepository  # noqa: E402
from ai_infra_fund_core.contracts.evaluation import RunArtifact  # noqa: E402


NOW = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)
LATER = datetime(2026, 5, 14, 12, 30, tzinfo=timezone.utc)
HASH_A = "a" * 64
HASH_B = "b" * 64

RUN_ARTIFACT_COLUMNS = (
    "run_id",
    "run_type",
    "started_at",
    "completed_at",
    "inputs_hash",
    "output_hash",
    "artifact_uri",
    "status",
    "error_summary",
    "created_at",
)


class RunArtifactRepositoryTests(unittest.TestCase):
    def test_upserts_run_artifact_with_parameterized_sql(self) -> None:
        connection = FakeConnection()
        artifact = run_artifact()

        saved = RunArtifactRepository(connection).save(artifact)

        self.assertEqual(artifact, saved)
        self.assertEqual(1, connection.commit_count)
        statement, params = connection.cursor_instance.executions[0]
        self.assertIn("INSERT INTO audit.run_artifacts", statement)
        self.assertIn("ON CONFLICT (run_id) DO UPDATE SET", statement)
        self.assertNotIn(artifact.run_id, statement)
        self.assertNotIn("recommendation-demo-nvda", statement)
        self.assertNotIn("audit-demo-nvda", statement)
        self.assertEqual(artifact.run_id, params[0])
        self.assertEqual("advisory_demo", params[1])
        self.assertEqual(HASH_A, params[4])
        self.assertEqual(HASH_B, params[5])
        self.assertEqual("succeeded", params[7])
        self.assertIsNone(params[8])

    def test_rejects_invalid_status_before_execute(self) -> None:
        connection = FakeConnection()
        invalid = artifact_record(status="complete")

        with self.assertRaisesRegex(ValueError, "status must be one of"):
            RunArtifactRepository(connection).save(invalid)

        self.assertEqual(0, connection.commit_count)
        self.assertEqual([], connection.cursor_instance.executions)

    def test_get_latest_defaults_to_advisory_demo_run_type(self) -> None:
        connection = FakeConnection(rows=[run_artifact_row()])

        found = RunArtifactRepository(connection).get_latest()

        statement, params = connection.cursor_instance.executions[0]
        self.assertIn("WHERE run_type = %s", statement)
        self.assertIn("ORDER BY started_at DESC, created_at DESC, run_id DESC", statement)
        self.assertNotIn("advisory_demo", statement)
        self.assertEqual(("advisory_demo",), params)
        self.assertEqual(expected_payload(), found)

    def test_get_latest_all_omits_run_type_filter(self) -> None:
        connection = FakeConnection(rows=[run_artifact_row(run_type="evaluation")])

        found = RunArtifactRepository(connection).get_latest("all")

        statement, params = connection.cursor_instance.executions[0]
        self.assertIn("FROM audit.run_artifacts", statement)
        self.assertNotIn("WHERE run_type = %s", statement)
        self.assertEqual((), params)
        self.assertEqual("evaluation", found["run_type"] if found else None)

    def test_get_by_id_returns_json_serializable_payload_with_traceability(self) -> None:
        connection = FakeConnection(rows=[run_artifact_row()])

        found = RunArtifactRepository(connection).get_by_id("run-advisory-demo")

        statement, params = connection.cursor_instance.executions[0]
        self.assertIn("WHERE run_id = %s", statement)
        self.assertNotIn("run-advisory-demo", statement)
        self.assertEqual(("run-advisory-demo",), params)
        self.assertEqual(expected_payload(), found)
        json.dumps(found)

    def test_returns_none_when_lookup_has_no_rows(self) -> None:
        connection = FakeConnection(rows=[])

        self.assertIsNone(RunArtifactRepository(connection).get_by_id("missing-run"))
        self.assertIsNone(RunArtifactRepository(connection).get_latest())


class FakeCursor:
    def __init__(self, rows: list[tuple[object, ...]], columns: tuple[str, ...]) -> None:
        self.executions: list[tuple[str, tuple[object, ...]]] = []
        self.rows = rows
        self.description = tuple((column,) for column in columns)

    def execute(self, statement: str, params: tuple[object, ...] | None = None) -> None:
        self.executions.append((statement, params or ()))

    def fetchone(self) -> tuple[object, ...] | None:
        return self.rows[0] if self.rows else None

    def __enter__(self) -> FakeCursor:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None


class FakeConnection:
    def __init__(
        self,
        *,
        rows: list[tuple[object, ...]] | None = None,
        columns: tuple[str, ...] = RUN_ARTIFACT_COLUMNS,
    ) -> None:
        self.cursor_instance = FakeCursor(rows or [], columns)
        self.commit_count = 0

    def cursor(self) -> FakeCursor:
        return self.cursor_instance

    def commit(self) -> None:
        self.commit_count += 1


def run_artifact(**overrides: object) -> RunArtifact:
    data = {
        "run_id": "run-advisory-demo",
        "run_type": "advisory_demo",
        "started_at": NOW,
        "completed_at": LATER,
        "inputs_hash": HASH_A,
        "output_hash": HASH_B,
        "artifact_uri": (
            "artifact://advisory/demo"
            "?recommendation_id=recommendation-demo-nvda"
            "&audit_id=audit-demo-nvda"
            "&evaluation_id=evaluation-demo-nvda"
            "&backtest_run_id=backtest-demo-nvda"
            "&advisory_label=advisory_only"
            "&ignored=value"
        ),
        "status": "succeeded",
        "error_summary": None,
        "created_at": NOW,
    }
    data.update(overrides)
    return RunArtifact(**data)


def artifact_record(**overrides: object) -> SimpleNamespace:
    artifact = run_artifact()
    data = {field: getattr(artifact, field) for field in RUN_ARTIFACT_COLUMNS}
    data.update(overrides)
    return SimpleNamespace(**data)


def run_artifact_row(**overrides: object) -> tuple[object, ...]:
    artifact = run_artifact(**overrides)
    return tuple(getattr(artifact, field) for field in RUN_ARTIFACT_COLUMNS)


def expected_payload(**overrides: object) -> dict[str, object]:
    artifact = run_artifact(**overrides)
    return {
        "run_id": artifact.run_id,
        "run_type": artifact.run_type,
        "started_at": artifact.started_at.isoformat(),
        "completed_at": artifact.completed_at.isoformat() if artifact.completed_at else None,
        "inputs_hash": artifact.inputs_hash,
        "output_hash": artifact.output_hash,
        "artifact_uri": artifact.artifact_uri,
        "status": artifact.status,
        "error_summary": artifact.error_summary,
        "created_at": artifact.created_at.isoformat(),
        "traceability": {
            "recommendation_id": "recommendation-demo-nvda",
            "audit_id": "audit-demo-nvda",
            "evaluation_id": "evaluation-demo-nvda",
            "backtest_run_id": "backtest-demo-nvda",
            "advisory_label": "advisory_only",
        },
    }


if __name__ == "__main__":
    unittest.main()
