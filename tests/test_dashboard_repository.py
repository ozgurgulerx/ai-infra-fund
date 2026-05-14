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

from ai_infra_fund_api.repositories.dashboard import DashboardRepository  # noqa: E402


NOW = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)
LATER = datetime(2026, 5, 14, 13, 0, tzinfo=timezone.utc)

SUMMARY_COLUMNS = (
    "total_items",
    "total_chunks",
    "total_claims",
    "items_by_data_class",
    "latest_ingested_at",
    "latest_created_at",
)

RECOMMENDATION_COLUMNS = (
    "total_recommendations",
    "total_audits",
    "schema_valid_audits",
    "schema_invalid_audits",
    "latest_created_at",
)

MODEL_RUN_COLUMNS = (
    "total_model_runs",
    "runs_by_status",
    "latest_created_at",
)

EVALUATION_COLUMNS = (
    "total_backtest_runs",
    "backtest_runs_by_status",
    "total_run_artifacts",
    "run_artifacts_by_status",
    "latest_created_at",
)

DATA_QUALITY_COLUMNS = (
    "total_checks",
    "checks_by_status",
    "checks_by_severity",
    "latest_checked_at",
    "latest_created_at",
)

INCIDENT_COLUMNS = (
    "total_incidents",
    "incidents_by_severity",
    "incidents_by_freeze_status",
    "open_incidents",
    "latest_created_at",
)


class DashboardRepositoryTests(unittest.TestCase):
    def test_returns_zero_default_summaries_on_empty_database(self) -> None:
        connection = FakeConnection(
            result_sets=[
                ResultSet([(0, 0, 0, {}, None, None)], SUMMARY_COLUMNS),
                ResultSet([(0, 0, 0, 0, None)], RECOMMENDATION_COLUMNS),
                ResultSet([(0, {}, None)], MODEL_RUN_COLUMNS),
                ResultSet([(0, {}, 0, {}, None)], EVALUATION_COLUMNS),
                ResultSet([(0, {}, {}, None, None)], DATA_QUALITY_COLUMNS),
                ResultSet([(0, {}, {}, 0, None)], INCIDENT_COLUMNS),
            ],
        )

        summary = DashboardRepository(connection).overview()

        self.assertEqual("empty", summary["status"])
        self.assertEqual(0, summary["evidence"]["total_items"])
        self.assertEqual(0, summary["evidence"]["total_chunks"])
        self.assertEqual(0, summary["evidence"]["total_claims"])
        self.assertEqual({}, summary["evidence"]["items_by_data_class"])
        self.assertIsNone(summary["evidence"]["latest_ingested_at"])
        self.assertIsNone(summary["evidence"]["latest_created_at"])
        self.assertEqual(0, summary["recommendations"]["total_recommendations"])
        self.assertEqual(0, summary["model_runs"]["total_model_runs"])
        self.assertEqual(0, summary["evaluations"]["total_backtest_runs"])
        self.assertEqual(0, summary["data_quality"]["total_checks"])
        self.assertEqual(0, summary["incidents"]["total_incidents"])
        self.assertEqual(0, connection.commit_count)
        self.assertEqual(6, len(connection.cursor_instance.executions))
        for statement, params in connection.cursor_instance.executions:
            self.assertIn("SELECT", statement.upper())
            self.assertNotIn("INSERT", statement.upper())
            self.assertNotIn("UPDATE", statement.upper())
            self.assertNotIn("DELETE", statement.upper())
            self.assertIsInstance(params, tuple)

    def test_route_adapter_methods_delegate_to_read_only_summaries(self) -> None:
        connection = FakeConnection(
            result_sets=[
                ResultSet([(1, 2, 3, {"public_evidence": 1}, NOW, LATER)], SUMMARY_COLUMNS),
                ResultSet([(4, 5, 5, 0, LATER)], RECOMMENDATION_COLUMNS),
                ResultSet([(6, {"success": 5, "denied": 1}, LATER)], MODEL_RUN_COLUMNS),
                ResultSet([(7, {"succeeded": 7}, 8, {"succeeded": 8}, LATER)], EVALUATION_COLUMNS),
                ResultSet([(9, {"pass": 9}, {"low": 9}, NOW, LATER)], DATA_QUALITY_COLUMNS),
                ResultSet([(10, {"low": 10}, {"resolved": 10}, 0, LATER)], INCIDENT_COLUMNS),
            ],
        )

        modules = DashboardRepository(connection).get_status_modules()

        self.assertEqual(6, len(connection.cursor_instance.executions))
        module_ids = [module["id"] for module in modules["modules"]]
        self.assertIn("data-plane", module_ids)
        self.assertIn("evidence-plane", module_ids)
        self.assertIn("recommendation-artifacts", module_ids)
        self.assertIn("model-router", module_ids)
        self.assertIn("evaluation-harness", module_ids)
        self.assertIn("data-quality", module_ids)
        self.assertIn("incidents", module_ids)
        for module in modules["modules"]:
            self.assertIn("status", module)
            self.assertIn("source_label", module)
            self.assertIn("detail", module)
            self.assertNotIn("chunk_text", str(module))
            self.assertNotIn("final_payload_json", str(module))

    def test_counts_evidence_items_chunks_claims_and_latest_timestamps(self) -> None:
        connection = FakeConnection(
            result_sets=[
                ResultSet(
                    [(3, 12, 7, {"public": 2, "restricted": 1}, NOW, LATER)],
                    SUMMARY_COLUMNS,
                ),
            ],
        )

        summary = DashboardRepository(connection).evidence_summary()

        statement, params = connection.cursor_instance.executions[0]
        self.assertIn("FROM evidence.evidence_items", statement)
        self.assertIn("FROM evidence.evidence_chunks", statement)
        self.assertIn("FROM evidence.evidence_claims", statement)
        self.assertNotIn("chunk_text", statement)
        self.assertEqual((), params)
        self.assertEqual(
            {
                "status": "available",
                "total_items": 3,
                "total_chunks": 12,
                "total_claims": 7,
                "items_by_data_class": {"public": 2, "restricted": 1},
                "latest_ingested_at": "2026-05-14T12:00:00+00:00",
                "latest_created_at": "2026-05-14T13:00:00+00:00",
            },
            summary,
        )

    def test_counts_recommendations_and_audits(self) -> None:
        connection = FakeConnection(
            result_sets=[ResultSet([(5, 4, 3, 1, LATER)], RECOMMENDATION_COLUMNS)],
        )

        summary = DashboardRepository(connection).recommendation_summary()

        statement, params = connection.cursor_instance.executions[0]
        self.assertIn("FROM recommendations.recommendation_artifacts", statement)
        self.assertIn("FROM recommendations.recommendation_audits", statement)
        self.assertNotIn("final_payload_json", statement)
        self.assertEqual((), params)
        self.assertEqual(5, summary["total_recommendations"])
        self.assertEqual(4, summary["total_audits"])
        self.assertEqual(3, summary["schema_valid_audits"])
        self.assertEqual(1, summary["schema_invalid_audits"])
        self.assertEqual("2026-05-14T13:00:00+00:00", summary["latest_created_at"])
        self.assertEqual("available", summary["status"])

    def test_counts_model_runs_by_status(self) -> None:
        connection = FakeConnection(
            result_sets=[
                ResultSet([(4, {"succeeded": 2, "failed": 1, "running": 1}, LATER)], MODEL_RUN_COLUMNS),
            ],
        )

        summary = DashboardRepository(connection).model_run_summary()

        statement, params = connection.cursor_instance.executions[0]
        self.assertIn("FROM audit.model_runs", statement)
        self.assertNotIn("model_id", statement)
        self.assertNotIn("deployment", statement)
        self.assertEqual((), params)
        self.assertEqual(4, summary["total_model_runs"])
        self.assertEqual({"succeeded": 2, "failed": 1, "running": 1}, summary["runs_by_status"])
        self.assertEqual("available", summary["status"])

    def test_counts_evaluation_backtest_and_run_artifact_records(self) -> None:
        connection = FakeConnection(
            result_sets=[
                ResultSet(
                    [(2, {"succeeded": 1, "failed": 1}, 3, {"succeeded": 2, "pending": 1}, LATER)],
                    EVALUATION_COLUMNS,
                ),
            ],
        )

        summary = DashboardRepository(connection).evaluation_summary()

        statement, params = connection.cursor_instance.executions[0]
        self.assertIn("FROM audit.backtest_runs", statement)
        self.assertIn("FROM audit.run_artifacts", statement)
        self.assertNotIn("artifact_uri", statement)
        self.assertEqual((), params)
        self.assertEqual(2, summary["total_backtest_runs"])
        self.assertEqual({"succeeded": 1, "failed": 1}, summary["backtest_runs_by_status"])
        self.assertEqual(3, summary["total_run_artifacts"])
        self.assertEqual({"succeeded": 2, "pending": 1}, summary["run_artifacts_by_status"])

    def test_counts_data_quality_checks_by_status_and_severity(self) -> None:
        connection = FakeConnection(
            result_sets=[
                ResultSet(
                    [(3, {"passed": 2, "failed": 1}, {"low": 1, "high": 2}, NOW, LATER)],
                    DATA_QUALITY_COLUMNS,
                ),
            ],
        )

        summary = DashboardRepository(connection).data_quality_summary()

        statement, params = connection.cursor_instance.executions[0]
        self.assertIn("FROM governance.data_quality_checks", statement)
        self.assertEqual((), params)
        self.assertEqual(3, summary["total_checks"])
        self.assertEqual({"passed": 2, "failed": 1}, summary["checks_by_status"])
        self.assertEqual({"low": 1, "high": 2}, summary["checks_by_severity"])
        self.assertEqual("available", summary["status"])

    def test_counts_incidents_by_severity_and_freeze_status(self) -> None:
        connection = FakeConnection(
            result_sets=[
                ResultSet(
                    [(4, {"critical": 1, "medium": 3}, {"frozen": 2, "none": 2}, 1, LATER)],
                    INCIDENT_COLUMNS,
                ),
            ],
        )

        summary = DashboardRepository(connection).incident_summary()

        statement, params = connection.cursor_instance.executions[0]
        self.assertIn("FROM governance.incident_records", statement)
        self.assertEqual((), params)
        self.assertEqual(4, summary["total_incidents"])
        self.assertEqual({"critical": 1, "medium": 3}, summary["incidents_by_severity"])
        self.assertEqual({"frozen": 2, "none": 2}, summary["incidents_by_freeze_status"])
        self.assertEqual(1, summary["open_incidents"])
        self.assertEqual("degraded", summary["status"])

    def test_get_status_overview_matches_overview_payload(self) -> None:
        connection = FakeConnection(
            result_sets=[
                ResultSet([(0, 0, 0, {}, None, None)], SUMMARY_COLUMNS),
                ResultSet([(0, 0, 0, 0, None)], RECOMMENDATION_COLUMNS),
                ResultSet([(0, {}, None)], MODEL_RUN_COLUMNS),
                ResultSet([(0, {}, 0, {}, None)], EVALUATION_COLUMNS),
                ResultSet([(0, {}, {}, None, None)], DATA_QUALITY_COLUMNS),
                ResultSet([(0, {}, {}, 0, None)], INCIDENT_COLUMNS),
            ],
        )

        summary = DashboardRepository(connection).get_status_overview()

        self.assertEqual("empty", summary["status"])
        self.assertEqual(0, summary["evidence"]["total_items"])
        self.assertEqual(0, summary["recommendations"]["total_recommendations"])


class ResultSet:
    def __init__(self, rows: list[tuple[object, ...]], columns: tuple[str, ...]) -> None:
        self.rows = rows
        self.columns = columns


class FakeCursor:
    def __init__(self, result_sets: list[ResultSet]) -> None:
        self._result_sets = result_sets
        self._index = 0
        self.executions: list[tuple[str, tuple[object, ...]]] = []
        self.description: tuple[tuple[str], ...] = ()
        self.rows: list[tuple[object, ...]] = []

    def execute(self, statement: str, params: tuple[object, ...] | None = None) -> None:
        self.executions.append((statement, params if params is not None else ()))
        result_set = self._result_sets[self._index]
        self._index += 1
        self.rows = result_set.rows
        self.description = tuple((column,) for column in result_set.columns)

    def fetchall(self) -> list[tuple[object, ...]]:
        return self.rows

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, *_exc: object) -> None:
        return None


class FakeConnection:
    def __init__(self, *, result_sets: list[ResultSet]) -> None:
        self.cursor_instance = FakeCursor(result_sets)
        self.commit_count = 0

    def cursor(self) -> FakeCursor:
        return self.cursor_instance

    def commit(self) -> None:
        self.commit_count += 1


if __name__ == "__main__":
    unittest.main()
