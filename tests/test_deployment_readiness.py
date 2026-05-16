from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import tomllib
import unittest
from unittest.mock import patch


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
        migration_path = (
            ROOT / "services" / "api" / "migrations" / "0001_phase2_data_spine.sql"
        )
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
            def execute(
                self, statement: str, params: tuple[object, ...] | None = None
            ) -> None:
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

    def test_compose_smoke_fails_when_worker_logs_errors(self) -> None:
        smoke_script = (ROOT / "scripts" / "compose_smoke.sh").read_text(
            encoding="utf-8"
        )

        self.assertIn("worker_logs=", smoke_script)
        self.assertIn("worker logs contain errors", smoke_script)
        self.assertIn("grep -Eq", smoke_script)


class PythonPackagingReadinessTests(unittest.TestCase):
    def test_pyproject_supports_editable_install_for_all_python_packages(self) -> None:
        pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

        self.assertEqual(
            "setuptools.build_meta", pyproject["build-system"]["build-backend"]
        )
        find_config = pyproject["tool"]["setuptools"]["packages"]["find"]
        self.assertEqual(
            ["packages/core/src", "services/api/src", "services/worker/src"],
            find_config["where"],
        )
        self.assertEqual(
            ["ai_infra_fund_core*", "ai_infra_fund_api*", "ai_infra_fund_worker*"],
            find_config["include"],
        )
        self.assertIn(
            "pytest==9.0.3", pyproject["project"]["optional-dependencies"]["dev"]
        )
        self.assertIn(
            "httpx==0.28.1", pyproject["project"]["optional-dependencies"]["dev"]
        )

    def test_generated_python_virtualenvs_are_ignored_by_git_and_docker_contexts(
        self,
    ) -> None:
        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")

        for ignored_path in (".venv/", "venv/", "*.egg-info/"):
            self.assertIn(ignored_path, gitignore)
            self.assertIn(ignored_path, dockerignore)


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
        self.assertEqual("ok", response.json()["data"]["checks"]["database"])
        self.assertIn("runtime_checks", response.json()["data"])

    def test_ready_endpoint_returns_runtime_ops_without_secret_values(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main
        from ai_infra_fund_core.runtime.config import RuntimeSettings

        with tempfile.TemporaryDirectory() as tmp:
            profiles = Path(tmp) / "model_profiles.yaml"
            profiles.write_text("profiles: []\n", encoding="utf-8")
            settings = RuntimeSettings(
                database_url="postgresql://user:super-secret@postgres:5432/fund",
                data_dir=tmp,
                model_profiles_path=str(profiles),
                environment="production",
            )
            app = main.create_app(
                connection_check=lambda _settings: True,
                settings_provider=lambda: settings,
                internal_token="internal-secret-token",
            )

            response = TestClient(app).get("/ready")

        self.assertEqual(200, response.status_code)
        payload = response.json()["data"]
        self.assertEqual("ready", payload["status"])
        self.assertTrue(payload["advisory_boundary"]["advisory_only"])
        self.assertTrue(payload["advisory_boundary"]["manual_journal_only"])
        self.assertEqual("forbidden", payload["advisory_boundary"]["broker_integration"])
        self.assertEqual("ok", payload["checks"]["production_internal_token"])
        serialized = json.dumps(payload)
        self.assertNotIn("super-secret", serialized)
        self.assertNotIn("internal-secret-token", serialized)

    def test_local_web_origin_can_read_health_endpoint(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        app = main.create_app(connection_check=lambda _settings: True)
        response = TestClient(app).options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual(
            "http://localhost:3000", response.headers.get("access-control-allow-origin")
        )

    def test_configured_web_origin_can_read_health_endpoint(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        app = main.create_app(
            connection_check=lambda _settings: True,
            web_origins=("https://fundrag-frontend.azurewebsites.net",),
        )
        response = TestClient(app).options(
            "/health",
            headers={
                "Origin": "https://fundrag-frontend.azurewebsites.net",
                "Access-Control-Request-Method": "GET",
            },
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual(
            "https://fundrag-frontend.azurewebsites.net",
            response.headers.get("access-control-allow-origin"),
        )

    def test_api_cors_origins_are_configurable_for_deployed_frontend(self) -> None:
        api_source = (
            ROOT / "services" / "api" / "src" / "ai_infra_fund_api" / "main.py"
        ).read_text(encoding="utf-8")
        self.assertIn("AI_INFRA_FUND_CORS_ORIGINS", api_source)
        self.assertIn("web_origins", api_source)
        self.assertIn("configured_web_origins", api_source)

    def test_local_web_origin_is_not_granted_cross_origin_post(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        app = main.create_app(connection_check=lambda _settings: True)
        response = TestClient(app).options(
            "/internal/recommendations",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )

        self.assertNotEqual(200, response.status_code)


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

        self.assertEqual(
            0, main.run_once(settings, connection_check=lambda _settings: True)
        )
        self.assertEqual(
            2, main.run_once(settings, connection_check=lambda _settings: False)
        )

    def test_production_worker_startup_uses_configured_internal_token(self) -> None:
        from ai_infra_fund_core.runtime.config import RuntimeSettings
        from ai_infra_fund_worker import main

        with tempfile.TemporaryDirectory() as tmp:
            profiles = Path(tmp) / "model_profiles.yaml"
            profiles.write_text("profiles: []\n", encoding="utf-8")
            settings = RuntimeSettings(
                database_url="postgresql://user:pass@postgres:5432/ai_infra_fund",
                data_dir=tmp,
                model_profiles_path=str(profiles),
                environment="production",
            )

            with patch.dict(
                os.environ,
                {"AI_INFRA_FUND_INTERNAL_TOKEN": "configured-token"},
                clear=True,
            ):
                self.assertEqual(
                    0,
                    main.run_once(settings, connection_check=lambda _settings: True),
                )

            with patch.dict(os.environ, {}, clear=True):
                self.assertEqual(
                    2,
                    main.run_once(settings, connection_check=lambda _settings: True),
                )


class RuntimeOpsPreflightTests(unittest.TestCase):
    def test_runtime_preflight_blocks_missing_crawl_user_agent_when_required(self) -> None:
        from ai_infra_fund_core.runtime.config import RuntimeSettings
        from ai_infra_fund_core.runtime.ops import build_runtime_preflight

        with tempfile.TemporaryDirectory() as tmp:
            profiles = Path(tmp) / "model_profiles.yaml"
            profiles.write_text("profiles: []\n", encoding="utf-8")
            settings = RuntimeSettings(
                database_url="postgresql://user:pass@postgres:5432/fund",
                data_dir=tmp,
                model_profiles_path=str(profiles),
                environment="production",
            )
            report = build_runtime_preflight(
                settings,
                service="worker",
                database_available=True,
                internal_token_configured=True,
                require_internal_token=True,
                require_crawl_user_agent=True,
                env={},
            )

        payload = report.to_dict()
        self.assertEqual("not_ready", payload["status"])
        self.assertEqual("failed", payload["checks"]["crawl_user_agent"])
        self.assertIn("SEC_EDGAR_USER_AGENT", json.dumps(payload))

    def test_runtime_preflight_accepts_contactable_crawl_user_agent(self) -> None:
        from ai_infra_fund_core.runtime.config import RuntimeSettings
        from ai_infra_fund_core.runtime.ops import build_runtime_preflight

        with tempfile.TemporaryDirectory() as tmp:
            profiles = Path(tmp) / "model_profiles.yaml"
            profiles.write_text("profiles: []\n", encoding="utf-8")
            settings = RuntimeSettings(
                database_url="postgresql://user:pass@postgres:5432/fund",
                data_dir=tmp,
                model_profiles_path=str(profiles),
                environment="production",
            )
            report = build_runtime_preflight(
                settings,
                service="worker",
                database_available=True,
                internal_token_configured=True,
                require_internal_token=True,
                require_crawl_user_agent=True,
                env={"SEC_EDGAR_USER_AGENT": "AI Infra Fund Research <ops@example.com>"},
            )

        payload = report.to_dict()
        self.assertEqual("ready", payload["status"])
        self.assertEqual("ok", payload["checks"]["crawl_user_agent"])
        self.assertNotIn("postgresql://user:pass", json.dumps(payload))


class ComposeSmokeScriptTests(unittest.TestCase):
    def test_api_dockerfile_has_runtime_and_test_targets(self) -> None:
        dockerfile = (ROOT / "services" / "api" / "Dockerfile").read_text(
            encoding="utf-8"
        )

        required_snippets = [
            "FROM python:3.12-slim AS runtime",
            "COPY pyproject.toml /app/pyproject.toml",
            "COPY packages/core /app/packages/core",
            "COPY services/api /app/services/api",
            "COPY services/worker /app/services/worker",
            'RUN pip install --no-cache-dir -e "."',
            "FROM runtime AS test",
            'RUN pip install --no-cache-dir -e ".[dev]"',
            'CMD ["python", "-m", "pytest", "tests/test_deployment_readiness.py"]',
        ]

        missing = [
            snippet for snippet in required_snippets if snippet not in dockerfile
        ]
        self.assertEqual([], missing)

    def test_worker_dockerfile_uses_editable_project_install(self) -> None:
        dockerfile = (ROOT / "services" / "worker" / "Dockerfile").read_text(
            encoding="utf-8"
        )

        required_snippets = [
            "FROM python:3.12-slim",
            "COPY pyproject.toml /app/pyproject.toml",
            "COPY packages/core /app/packages/core",
            "COPY services/api /app/services/api",
            "COPY services/worker /app/services/worker",
            'RUN pip install --no-cache-dir -e "."',
        ]

        missing = [
            snippet for snippet in required_snippets if snippet not in dockerfile
        ]
        self.assertEqual([], missing)

    def test_compose_exposes_containerized_python_test_target(self) -> None:
        compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

        required_snippets = [
            "  test:",
            "dockerfile: services/api/Dockerfile",
            "target: test",
            'command: ["python", "-m", "pytest", "tests/test_deployment_readiness.py"]',
        ]

        missing = [snippet for snippet in required_snippets if snippet not in compose]
        self.assertEqual([], missing)

    def test_compose_smoke_script_exists_and_checks_expected_steps(self) -> None:
        script_path = ROOT / "scripts" / "compose_smoke.sh"
        text = script_path.read_text(encoding="utf-8")

        required_snippets = [
            "set -euo pipefail",
            "docker compose config",
            "docker compose build api migrate worker web",
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
