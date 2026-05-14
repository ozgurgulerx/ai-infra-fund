from pathlib import Path
import re
import stat
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_PHASE0_FILES = [
    "AGENTS.md",
    "docs/specs/0001-product-vision.md",
    "docs/specs/0002-trading-policy.md",
    "docs/specs/0003-data-contracts.md",
    "docs/specs/0004-agent-contracts.md",
    "docs/specs/0005-ui-acceptance.md",
    "docs/specs/0006-forward-indicators.md",
    "docs/specs/0007-situational-awareness-thesis-map.md",
    "docs/specs/0008-model-routing-and-audit.md",
    "docs/specs/0009-evaluation-harness.md",
    "docs/specs/0010-repo-patterns-architecture.md",
    "docs/specs/0011-implementation-roadmap.md",
    "docs/specs/0012-data-architecture.md",
    "docs/specs/0013-llm-routing-and-governance.md",
    "docs/specs/0014-risk-monitoring-and-incidents.md",
    "docs/specs/0015-containerized-deployment.md",
    "config/model_profiles.yaml",
    "docker-compose.yml",
    "docker-compose.prod.example.yml",
    ".env.example",
    ".dockerignore",
    "apps/web/Dockerfile",
    "apps/web/package-lock.json",
    "services/api/Dockerfile",
    "services/worker/Dockerfile",
    "services/api/migrations/0001_phase2_data_spine.sql",
    "scripts/compose_smoke.sh",
]

NON_NEGOTIABLE_PHRASES = [
    "advisory-only",
    "No live order placement",
    "Deterministic code owns scores",
    "config/model_profiles.yaml",
    "PostgreSQL + pgvector",
    "Docker Compose",
    "TargetWeights",
    "evidence IDs",
]

MODEL_PROFILE_REQUIRED_ROLES = [
    "source_classification",
    "evidence_summary",
    "orchestration_validation",
    "adversarial_review",
    "local_fallback",
    "embeddings",
]

COMPOSE_REQUIRED_SERVICES = ["web", "api", "worker", "postgres", "migrate"]

GENERATED_PATHS_THAT_MUST_BE_IGNORED = [
    "apps/web/.next/cache/example",
    "apps/web/node_modules/example",
    "packages/core/src/ai_infra_fund_core/__pycache__/example.pyc",
    "services/api/src/ai_infra_fund_api/__pycache__/example.pyc",
    "services/worker/src/ai_infra_fund_worker/__pycache__/example.pyc",
    "tests/__pycache__/example.pyc",
    ".pytest_cache/example",
    "data/raw/example.csv",
]

DEPRECATED_STORAGE_PATTERNS = [
    "DuckDB/Parquet cache",
    "DuckDB owns",
    "AI_INFRA_FUND_DUCKDB_PATH",
    "SQLite",
    "LanceDB",
    "sqlite-vec",
]

FORBIDDEN_PRODUCTION_PATTERNS = [
    r"\bplace_order\b",
    r"\bsubmit_order\b",
    r"\bbroker_client\b",
    r"\blive_order\b",
    r"\border_execution\b",
    r"\bexecute_order\b",
    r"\bbrokerage\b",
]


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def existing_text_files(*roots: str) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        base = ROOT / root
        if base.exists():
            files.extend(path for path in base.rglob("*") if path.is_file())
    return files


class ArchitecturePolicyTests(unittest.TestCase):
    def test_phase0_required_files_exist(self) -> None:
        missing = [
            relative_path
            for relative_path in REQUIRED_PHASE0_FILES
            if not (ROOT / relative_path).is_file()
        ]
        self.assertEqual([], missing)

    def test_agents_md_contains_non_negotiable_rules(self) -> None:
        text = read_text("AGENTS.md")
        missing = [phrase for phrase in NON_NEGOTIABLE_PHRASES if phrase not in text]
        self.assertEqual([], missing)

    def test_specs_agree_on_postgresql_only_v1_storage(self) -> None:
        required_files = [
            "docs/plans/data_plan.md",
            "docs/plans/database_design.md",
            "docs/plans/deployment_harness.md",
            "docs/specs/0012-data-architecture.md",
            "docs/specs/0015-containerized-deployment.md",
            "AGENTS.md",
        ]
        for relative_path in required_files:
            text = read_text(relative_path)
            self.assertIn("PostgreSQL + pgvector", text, relative_path)
            self.assertIn("not a v1 dependency", text, relative_path)

    def test_deprecated_v1_storage_references_are_absent(self) -> None:
        offenders: list[str] = []
        for path in existing_text_files("docs/plans", "docs/specs", "AGENTS.md"):
            text = path.read_text(encoding="utf-8")
            for pattern in DEPRECATED_STORAGE_PATTERNS:
                if pattern in text:
                    offenders.append(f"{path.relative_to(ROOT)} contains {pattern}")
        self.assertEqual([], offenders)

    def test_model_profiles_define_required_roles(self) -> None:
        text = read_text("config/model_profiles.yaml")
        missing = [role for role in MODEL_PROFILE_REQUIRED_ROLES if role not in text]
        self.assertEqual([], missing)
        self.assertIn("fallback_chain", text)
        self.assertIn("allowed_data_classes", text)

    def test_container_scaffold_defines_required_services(self) -> None:
        text = read_text("docker-compose.yml")
        missing = [
            service
            for service in COMPOSE_REQUIRED_SERVICES
            if not re.search(rf"^  {re.escape(service)}:\s*$", text, re.MULTILINE)
        ]
        self.assertEqual([], missing)
        self.assertIn("postgres_data:", text)
        self.assertIn("./data:/app/data", text)

    def test_web_container_does_not_receive_database_url(self) -> None:
        text = read_text("docker-compose.yml")
        match = re.search(r"^  web:\s*\n(?P<body>.*?)(?=^  [a-zA-Z0-9_-]+:\s*$|\Z)", text, re.MULTILINE | re.DOTALL)
        self.assertIsNotNone(match)
        web_body = match.group("body") if match else ""
        self.assertNotIn("AI_INFRA_FUND_DATABASE_URL", web_body)
        self.assertNotIn("AZURE_AI_FOUNDRY_API_KEY", web_body)

    def test_migrate_service_owns_schema_migrations(self) -> None:
        text = read_text("docker-compose.yml")
        migrate_match = re.search(r"^  migrate:\s*\n(?P<body>.*?)(?=^  [a-zA-Z0-9_-]+:\s*$|\Z)", text, re.MULTILINE | re.DOTALL)
        self.assertIsNotNone(migrate_match)
        migrate_body = migrate_match.group("body") if migrate_match else ""
        self.assertIn("ai_infra_fund_api.migrate", migrate_body)

        for service in ("api", "worker", "web"):
            match = re.search(rf"^  {service}:\s*\n(?P<body>.*?)(?=^  [a-zA-Z0-9_-]+:\s*$|\Z)", text, re.MULTILINE | re.DOTALL)
            self.assertIsNotNone(match)
            body = match.group("body") if match else ""
            self.assertNotIn("ai_infra_fund_api.migrate", body, service)

    def test_frontend_uses_lockfile_and_reproducible_install(self) -> None:
        dockerfile = read_text("apps/web/Dockerfile")
        self.assertIn("package-lock.json", dockerfile)
        self.assertIn("npm ci", dockerfile)
        self.assertNotIn("npm install", dockerfile)

    def test_generated_directories_are_gitignored(self) -> None:
        result = subprocess.run(
            ["git", "check-ignore", *GENERATED_PATHS_THAT_MUST_BE_IGNORED],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        ignored = set(result.stdout.splitlines())
        missing = [
            path
            for path in GENERATED_PATHS_THAT_MUST_BE_IGNORED
            if path not in ignored
        ]
        self.assertEqual([], missing, result.stderr)

    def test_compose_smoke_script_is_executable(self) -> None:
        script_path = ROOT / "scripts" / "compose_smoke.sh"
        mode = script_path.stat().st_mode
        self.assertTrue(mode & stat.S_IXUSR)

    def test_production_overlay_hardens_postgres_and_preserves_boundaries(self) -> None:
        text = read_text("docker-compose.prod.example.yml")
        for service in COMPOSE_REQUIRED_SERVICES:
            self.assertIsNotNone(
                re.search(rf"^  {re.escape(service)}:\s*$", text, re.MULTILINE),
                service,
            )
        self.assertIn("POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD", text)
        self.assertIn("ports: !reset []", text)
        self.assertNotIn("ai_infra_fund:ai_infra_fund@", text)
        self.assertNotRegex(text, r"sk-[A-Za-z0-9_-]+")

    def test_docs_distinguish_local_and_production_readiness(self) -> None:
        deployment_plan = read_text("docs/plans/deployment_readiness_plan.md")
        container_plan = read_text("docs/plans/containerization_plan.md")
        combined = f"{deployment_plan}\n{container_plan}"
        required = [
            "local/dev",
            "production-ready",
            "product-feature-complete",
            "docker-compose.prod.example.yml",
            "TLS/reverse proxy",
            "backup/restore",
            "monitoring",
            "CI/CD",
            "docker compose down",
        ]
        missing = [phrase for phrase in required if phrase not in combined]
        self.assertEqual([], missing)

    def test_env_example_contains_no_real_secret_values(self) -> None:
        text = read_text(".env.example")
        self.assertNotIn("sk-", text)
        self.assertNotRegex(text, r"(?i)(api_key|token|secret)=\S+")

    def test_no_live_order_execution_surface_exists(self) -> None:
        offenders: list[str] = []
        for path in existing_text_files("apps", "services", "packages"):
            text = path.read_text(encoding="utf-8", errors="ignore")
            for pattern in FORBIDDEN_PRODUCTION_PATTERNS:
                if re.search(pattern, text, re.IGNORECASE):
                    offenders.append(f"{path.relative_to(ROOT)} matches {pattern}")
        self.assertEqual([], offenders)


if __name__ == "__main__":
    unittest.main()
