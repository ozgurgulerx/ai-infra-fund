from __future__ import annotations

from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
API_SRC = ROOT / "services" / "api" / "src"
WORKER_SRC = ROOT / "services" / "worker" / "src"

for path in (CORE_SRC, API_SRC, WORKER_SRC):
    sys.path.insert(0, str(path))


class MigrationReadinessTests(unittest.TestCase):
    def test_versioned_sql_migration_files_exist_in_order(self) -> None:
        migrations_dir = ROOT / "services" / "api" / "migrations"
        migrations = sorted(migrations_dir.glob("*.sql"))

        self.assertTrue(migrations, "expected versioned SQL migration files")
        self.assertEqual(
            [path.name for path in migrations],
            sorted(path.name for path in migrations),
        )
        self.assertTrue(migrations[0].name.startswith("0001_"))

    def test_initial_schema_migration_contains_phase2_foundations(self) -> None:
        migration_path = ROOT / "services" / "api" / "migrations" / "0001_phase2_data_spine.sql"
        sql = migration_path.read_text(encoding="utf-8")

        required_snippets = [
            "CREATE EXTENSION IF NOT EXISTS vector",
            "CREATE EXTENSION IF NOT EXISTS pgcrypto",
            "CREATE SCHEMA IF NOT EXISTS core",
            "CREATE SCHEMA IF NOT EXISTS evidence",
            "CREATE SCHEMA IF NOT EXISTS audit",
            "CREATE SCHEMA IF NOT EXISTS signals",
            "CREATE SCHEMA IF NOT EXISTS recommendations",
            "CREATE SCHEMA IF NOT EXISTS governance",
            "CREATE TABLE IF NOT EXISTS core.positions",
            "CREATE TABLE IF NOT EXISTS core.trade_entries",
            "CREATE TABLE IF NOT EXISTS evidence.evidence_chunks",
            "embedding vector(1024)",
            "CREATE TABLE IF NOT EXISTS core.portfolio_snapshots",
            "CREATE TABLE IF NOT EXISTS core.portfolio_snapshot_positions",
            "CREATE TABLE IF NOT EXISTS signals.market_snapshots",
            "CREATE TABLE IF NOT EXISTS signals.factor_rows",
            "advisory_label = 'advisory_only'",
            "array_length(evidence_ids, 1) > 0",
            "array_length(model_run_ids, 1) > 0",
        ]

        missing = [snippet for snippet in required_snippets if snippet not in sql]
        self.assertEqual([], missing)

    def test_migration_runner_applies_sql_files_in_order(self) -> None:
        from ai_infra_fund_api import migrate

        applied: list[str] = []

        class FakeCursor:
            def execute(self, statement: str, params: tuple[object, ...] | None = None) -> None:
                if statement.strip().startswith("INSERT INTO audit.schema_migrations"):
                    applied.append(str(params[0]) if params else "")

            def fetchone(self) -> tuple[bool]:
                return (False,)

            def __enter__(self) -> "FakeCursor":
                return self

            def __exit__(self, *_exc: object) -> None:
                return None

        class FakeConnection:
            def cursor(self) -> FakeCursor:
                return FakeCursor()

            def commit(self) -> None:
                return None

        migration_files = [
            migrate.Migration("0002_second.sql", "SELECT 2;"),
            migrate.Migration("0001_first.sql", "SELECT 1;"),
        ]

        migrate.apply_migrations(FakeConnection(), migration_files)

        self.assertEqual(["0001_first.sql", "0002_second.sql"], applied)


class ApiReadinessTests(unittest.TestCase):
    def test_health_endpoint_uses_response_envelope_without_database(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api.main import app

        response = TestClient(app).get("/health")

        self.assertEqual(200, response.status_code)
        self.assertEqual(
            {
                "data": {
                    "service": "api",
                    "status": "ok",
                }
            },
            response.json(),
        )

    def test_version_endpoint_returns_service_metadata(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api.main import app

        payload = TestClient(app).get("/version").json()["data"]

        self.assertEqual("api", payload["service"])
        self.assertEqual("ai-infra-fund", payload["project"])
        self.assertIn("version", payload)

    def test_ready_endpoint_reports_unavailable_database(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        app = main.create_app(connection_check=lambda _settings: False)

        response = TestClient(app).get("/ready")

        self.assertEqual(503, response.status_code)
        self.assertEqual("readiness_failed", response.json()["error"]["code"])

    def test_ready_endpoint_reports_available_database(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        app = main.create_app(connection_check=lambda _settings: True)

        response = TestClient(app).get("/ready")

        self.assertEqual(200, response.status_code)
        self.assertEqual("ready", response.json()["data"]["status"])


class WorkerReadinessTests(unittest.TestCase):
    def test_worker_requires_database_url_and_model_profile_path(self) -> None:
        from ai_infra_fund_worker import main

        with self.assertRaises(SystemExit) as context:
            main.load_worker_settings({})

        self.assertNotEqual(0, context.exception.code)

    def test_worker_startup_checks_database_and_stubs_jobs(self) -> None:
        from ai_infra_fund_core.runtime.config import RuntimeSettings
        from ai_infra_fund_worker import main

        settings = RuntimeSettings(
            database_url="postgresql://user:pass@postgres:5432/ai_infra_fund",
            data_dir="/app/data",
            model_profiles_path="config/model_profiles.yaml",
            environment="local",
        )

        self.assertEqual(0, main.run_once(settings, connection_check=lambda _settings: True))
        self.assertEqual(2, main.run_once(settings, connection_check=lambda _settings: False))


class ComposeSmokeScriptTests(unittest.TestCase):
    def test_compose_smoke_script_exists_and_checks_expected_steps(self) -> None:
        script_path = ROOT / "scripts" / "compose_smoke.sh"
        text = script_path.read_text(encoding="utf-8")

        required_snippets = [
            "set -euo pipefail",
            "docker compose config",
            "docker compose build api worker web",
            "docker compose up -d postgres",
            "docker compose run --rm migrate",
            "docker compose up -d api worker web",
            "http://localhost:8000/health",
            "http://localhost:8000/ready",
            "docker compose ps",
            "docker compose logs --no-color --tail=100",
        ]
        missing = [snippet for snippet in required_snippets if snippet not in text]
        self.assertEqual([], missing)


if __name__ == "__main__":
    unittest.main()
