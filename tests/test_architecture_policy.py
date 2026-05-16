from pathlib import Path
import re
import stat
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_PHASE0_FILES = [
    "AGENTS.md",
    "docs/PRODUCT.md",
    "docs/ALPHA_ANALYST_PRINCIPLES.md",
    "docs/ARCHITECTURE.md",
    "docs/CURRENT_TASK.md",
    "docs/HARNESS.md",
    "docs/SPEC_ROUTER.md",
    "docs/BUILD_LOG.md",
    "docs/DECISIONS.md",
    "docs/plans/active/current-plan.md",
    "docs/plans/archive/deployment_harness.md",
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
    "docs/specs/0016-equity-intelligence-crawler.md",
    "docs/specs/0017-crawl-pipeline-runtime.md",
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
    "Advisory-only system",
    "no live order placement",
    "Deterministic code owns scores",
    "config/model_profiles.yaml",
    "PostgreSQL + pgvector",
    "DuckDB/Parquet is future optional only",
    "target weights",
    "evidence IDs",
    "ModelRun",
    ".env.example",
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
    ".venv/example",
    "venv/example",
    "ai_infra_fund.egg-info/example",
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
    ignored_parts = {
        ".next",
        ".pytest_cache",
        "__pycache__",
        "build",
        "coverage",
        "dist",
        "node_modules",
    }
    for root in roots:
        base = ROOT / root
        if base.exists():
            files.extend(
                path
                for path in base.rglob("*")
                if path.is_file() and not ignored_parts.intersection(path.parts)
            )
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
            "docs/ARCHITECTURE.md",
            "docs/DECISIONS.md",
            "docs/specs/0012-data-architecture.md",
            "docs/specs/0015-containerized-deployment.md",
            "AGENTS.md",
        ]
        for relative_path in required_files:
            text = read_text(relative_path)
            self.assertIn("PostgreSQL + pgvector", text, relative_path)
            self.assertRegex(
                text,
                r"DuckDB(/|\s*\+\s*)Parquet.*future optional",
                relative_path,
            )

    def test_deprecated_v1_storage_references_are_absent(self) -> None:
        offenders: list[str] = []
        for path in existing_text_files("docs/specs", "AGENTS.md"):
            text = path.read_text(encoding="utf-8")
            for pattern in DEPRECATED_STORAGE_PATTERNS:
                if pattern in text:
                    offenders.append(f"{path.relative_to(ROOT)} contains {pattern}")
        for relative_path in (
            "docs/PRODUCT.md",
            "docs/ARCHITECTURE.md",
            "docs/HARNESS.md",
            "docs/DECISIONS.md",
            "docs/SPEC_ROUTER.md",
        ):
            text = read_text(relative_path)
            for pattern in DEPRECATED_STORAGE_PATTERNS:
                if pattern in text:
                    offenders.append(f"{relative_path} contains {pattern}")
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
        self.assertIn("AI_INFRA_FUND_INTERNAL_API_BASE_URL", web_body)
        self.assertIn("http://api:8000", web_body)

    def test_trade_journal_proxy_uses_container_internal_api_url(self) -> None:
        route = read_text("apps/web/app/api/trade-journal/entries/route.ts")
        self.assertIn("AI_INFRA_FUND_INTERNAL_API_BASE_URL", route)
        self.assertIn("AI_INFRA_FUND_INTERNAL_TOKEN", route)
        self.assertIn("X-Internal-Token", route)
        self.assertIn("NEXT_PUBLIC_API_BASE_URL", route)
        self.assertIn("/internal/trade-journal/entries", route)

    def test_read_only_backend_proxy_forwards_internal_token_server_side(self) -> None:
        route = read_text("apps/web/app/api/backend/[...path]/route.ts")
        client = read_text("apps/web/lib/api.ts")
        self.assertIn("AI_INFRA_FUND_INTERNAL_TOKEN", route)
        self.assertIn("X-Internal-Token", route)
        self.assertNotIn("AI_INFRA_FUND_INTERNAL_TOKEN", client)
        self.assertIn("/api/backend", client)
        self.assertNotRegex(client, r"\$\{apiBaseUrl\(\)\}/internal")

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
        self.assertIn("AI_INFRA_FUND_INTERNAL_TOKEN:?Set AI_INFRA_FUND_INTERNAL_TOKEN", text)
        self.assertIn("ports: !reset []", text)
        self.assertNotIn("ai_infra_fund:ai_infra_fund@", text)
        self.assertNotRegex(text, r"sk-[A-Za-z0-9_-]+")

    def test_aks_manifest_wires_internal_token_from_secret(self) -> None:
        text = read_text("deploy/aks-ai-infra-fund.yaml")
        self.assertIn("AI_INFRA_FUND_INTERNAL_TOKEN", text)
        self.assertIn("secretKeyRef:", text)

    def test_docs_distinguish_local_and_production_readiness(self) -> None:
        deployment_plan = read_text("docs/plans/archive/deployment_readiness_plan.md")
        container_plan = read_text("docs/plans/archive/containerization_plan.md")
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

    def test_harness_consolidation_routes_specs_and_archives_old_plans(self) -> None:
        agents = read_text("AGENTS.md")
        current_task = read_text("docs/CURRENT_TASK.md")
        router = read_text("docs/SPEC_ROUTER.md")
        build_log = read_text("docs/BUILD_LOG.md")

        for required in (
            "docs/PRODUCT.md",
            "docs/ARCHITECTURE.md",
            "docs/CURRENT_TASK.md",
            "docs/SPEC_ROUTER.md",
        ):
            self.assertIn(required, agents)
        self.assertIn("## Governing Specs", current_task)
        self.assertIn("## Product Objective", current_task)
        self.assertIn("## Definition Of Done", current_task)
        self.assertIn("specs/0016-equity-intelligence-crawler.md", router)
        self.assertIn("Duplicate content found", build_log)

        self.assertFalse((ROOT / "docs" / "plans" / "deployment_harness.md").exists())
        self.assertTrue(
            (ROOT / "docs" / "plans" / "archive" / "deployment_harness.md").is_file()
        )

    def test_alpha_analyst_principles_keep_product_catalyst_driven(self) -> None:
        principles = read_text("docs/ALPHA_ANALYST_PRINCIPLES.md")
        product = read_text("docs/PRODUCT.md")

        required = [
            "Detect catalyst",
            "second-order beneficiaries",
            "typed `MarketEvent`",
            "deterministic signals",
            "advisory-only recommendation artifact",
            "daily high-alpha AI infrastructure brief",
            "catalyst detection",
            "analyst brief usefulness",
        ]
        missing = [phrase for phrase in required if phrase not in principles]
        self.assertEqual([], missing)
        self.assertIn("docs/ALPHA_ANALYST_PRINCIPLES.md", product)

    def test_market_events_require_provenance_before_signal_use(self) -> None:
        contract = read_text("packages/core/src/ai_infra_fund_core/contracts/events.py")
        data_contract = read_text("docs/specs/0003-data-contracts.md")

        self.assertIn("source_evidence_ids", contract)
        self.assertIn("require_non_empty_tuple", contract)
        self.assertIn("Events without provenance cannot influence `SignalBundle`", data_contract)

        offenders: list[str] = []
        for path in existing_text_files("packages/core/src/ai_infra_fund_core/signals"):
            text = path.read_text(encoding="utf-8", errors="ignore")
            if "MarketEvent" in text and "source_evidence_ids" not in text:
                offenders.append(str(path.relative_to(ROOT)))
        self.assertEqual([], offenders)

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

    def test_frontend_does_not_import_database_or_backend_internals(self) -> None:
        forbidden_patterns = [
            r"AI_INFRA_FUND_DATABASE_URL",
            r"\bpsycopg\b",
            r"services/api",
            r"ai_infra_fund_api",
            r"postgresql://",
        ]
        offenders: list[str] = []
        for path in existing_text_files("apps/web"):
            if "node_modules" in path.parts or ".next" in path.parts:
                continue
            if path.suffix not in {".css", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".json"}:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for pattern in forbidden_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    offenders.append(f"{path.relative_to(ROOT)} matches {pattern}")
        self.assertEqual([], offenders)

    def test_frontend_has_no_order_or_broker_execution_controls(self) -> None:
        forbidden_label_patterns = [
            r">\s*Place\s+Order\s*<",
            r">\s*Submit\s+Order\s*<",
            r">\s*Execute\s+Order\s*<",
            r">\s*Connect\s+Broker\s*<",
            r">\s*Start\s+Live\s+Trading\s*<",
        ]
        offenders: list[str] = []
        for path in existing_text_files("apps/web"):
            if "node_modules" in path.parts or ".next" in path.parts:
                continue
            if path.suffix not in {".css", ".ts", ".tsx"}:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for pattern in forbidden_label_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    offenders.append(f"{path.relative_to(ROOT)} matches {pattern}")
        self.assertEqual([], offenders)


if __name__ == "__main__":
    unittest.main()
