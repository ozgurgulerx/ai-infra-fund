from pathlib import Path
import dataclasses
from datetime import datetime, timezone
import re
import stat
import subprocess
import sys
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
    "Deterministic code still owns numeric scores",
    "config/model_profiles.yaml",
    "PostgreSQL + pgvector",
    "DuckDB/Parquet is future optional only",
    "target weights",
    "evidence IDs",
    "ModelRun",
    ".env.example",
]

AGENTS_LLM_MEDIATED_DECISION_POLICY_PHRASES = [
    "Every analyst evaluation and decision point must be LLM-mediated",
    "evidence-linked, and auditable",
    "Deterministic code still owns numeric scores, risk math",
    "constraints, target weights, scenario values, entry/exit levels, PnL",
    "publication/suppression gates",
    "LLM review cannot bypass failed deterministic checks",
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

ADVISORY_WORKSTATION_CONTRACT_DOCS = [
    "docs/ANALYST_OBJECT_MODEL.md",
    "docs/specs/0003-data-contracts.md",
]

ADVISORY_WORKSTATION_CONTRACT_OBJECTS = [
    "SourceSignal",
    "FinancialSnapshot",
    "ValuationContext",
    "MacroRegimeSnapshot",
    "SegmentImpact",
    "EquityImpactAssessment",
    "RiskRegimeUpdate",
    "TradingAdvisory",
    "TradePlan",
    "PortfolioExposureSnapshot",
    "AnalystBrief",
    "AdvisoryUpdate",
    "OutcomeJournalEntry",
    "LLMAnalystNote",
]

FORBIDDEN_ADVISORY_CONTRACT_FIELD_TERMS = [
    "broker",
    "order",
    "route",
    "fill",
    "execution",
    "exchange",
    "auto_trade",
]

ADVISORY_CONTRACT_FIELD_TERM_ALLOWLIST = {
    ("SegmentImpact", "first_order_tickers", "order"),
    ("SegmentImpact", "second_order_tickers", "order"),
}

TRADING_ADVISORY_POLICY_PHRASES = [
    "`TradingAdvisory` is an advisory-only output",
    "`advisory_label` must be advisory-only",
    "Entry, add, trim, exit, and invalidation levels are planning guidance, not orders",
    "Target scenarios are scenarios, not predictions",
    "Deterministic code owns PnL, exposure, risk-limit checks, accounting, stale-data gates, and publication policy checks",
]

CRAWLER_BOUNDARY_PHRASES = [
    "crawling arbitrary internet sources without watchlist or source-registry configuration",
    "private documents, paid reports, broker/account documents, or licensed research",
    "broker, order, route, fill, execution, or automated trading outputs",
    "any live market action endpoint or UI control",
    "any execution/trading action",
    "using LLM output to produce deterministic scores, constraints, or target weights directly",
    "They must never contain broker, order, route, fill, execution, automated-trading, or live-market-action instructions",
]

CRAWL_RUNTIME_BOUNDARY_PHRASES = [
    "must not crawl arbitrary internet sources without watchlist or source-registry configuration",
    "must not crawl private documents, paid reports, broker/account documents, or licensed research",
    "Forbidden runtime outputs:",
    "broker records",
    "order records",
    "route records",
    "fill records",
    "execution state",
    "automated trading actions",
    "live-market-action UI state",
    "No extractor may emit broker/order/execution outputs, automated trading actions, trade instructions, or live-market-action UI state",
    "Never scores, weights, constraints, broker records, order records, execution records, or trade instructions",
]

DETERMINISTIC_OWNERSHIP_PHRASES = [
    "LLMs must not own final scores, risk, constraints, target weights, portfolio exposure, entry/exit levels, or PnL calculations",
    "Deterministic code owns scores, risk, constraints, target weights, correlation exposure, concentration checks, entry/exit levels, scenario values, PnL, exposure, risk-limit checks, and accounting",
    "UI consumers must render fields as provided. They must not compute scores, weights, PnL, target prices, entry/exit levels, or constraints",
    "Deterministic code owns PnL, exposure, risk-limit checks, and accounting",
]

LLM_EXTRACTION_FORBIDDEN_OUTPUT_NAME_TERMS = [
    "score",
    "scoring",
    "weight",
    "constraint",
    "order",
    "execution",
]

FORBIDDEN_ROUTE_PATH_TERMS = [
    "broker",
    "place-order",
    "submit-order",
    "execute-order",
    "order-execution",
    "execution",
    "fill",
    "fills",
    "route-order",
    "live-trading",
    "automated-trading",
]

ALLOWED_ROUTE_PATHS = {
    "/internal/trade-journal/entries",
}

FORBIDDEN_ROUTE_MODULE_STEMS = {
    "broker",
    "brokers",
    "order",
    "orders",
    "execution",
    "executions",
    "fills",
    "order_execution",
    "brokerage",
}

ALLOWED_ROUTE_MODULE_STEMS = {
    "trade_journal",
}

DETERMINISTIC_MODULE_ROOTS = [
    "packages/core/src/ai_infra_fund_core/signals",
    "packages/core/src/ai_infra_fund_core/portfolio",
    "packages/core/src/ai_infra_fund_core/evaluation",
    "packages/core/src/ai_infra_fund_core/recommendations",
    "packages/core/src/ai_infra_fund_core/contracts",
]

FORBIDDEN_MODEL_CLIENT_IMPORT_PATTERNS = [
    r"^\s*(?:from|import)\s+ai_infra_fund_core\.model_routing\b",
    r"^\s*(?:from|import)\s+openai\b",
    r"^\s*(?:from|import)\s+anthropic\b",
    r"^\s*(?:from|import)\s+azure\.ai\b",
    r"^\s*(?:from|import)\s+google\.generativeai\b",
    r"^\s*(?:from|import)\s+ollama\b",
    r"^\s*(?:from|import)\s+litellm\b",
    r"^\s*(?:from|import)\s+langchain\b",
]

FRONTEND_PUBLIC_ENV_ALLOWLIST = {
    "NEXT_PUBLIC_API_BASE_URL",
}

FORBIDDEN_V1_STORAGE_DEPENDENCIES = [
    "duckdb",
    "pyarrow",
    "polars",
    "parquetjs",
    "lancedb",
    "sqlite-vec",
]

FORBIDDEN_V1_STORAGE_IMPORT_PATTERNS = [
    r"^\s*(?:from|import)\s+duckdb\b",
    r"^\s*(?:from|import)\s+pyarrow\b",
    r"^\s*(?:from|import)\s+polars\b",
    r"^\s*(?:from|import)\s+lancedb\b",
    r"^\s*(?:from|import)\s+sqlite_vec\b",
]

TRACKED_SECRET_OR_PRIVATE_PATTERNS = [
    r"(^|/)\.env($|\.)",
    r"(^|/)private_research/",
    r"(^|/)raw_private/",
    r"(^|/)Downloads/",
    r"(?i)schwab.*\.pdf$",
    r"(?i)routing.*\.pdf$",
]

TRACKED_SECRET_ALLOWLIST = {
    ".env.example",
}

LLM_PROMPT_PACK_REQUIRED_BOUNDARY_PHRASES = [
    "Every analyst evaluation and decision point must be LLM-mediated",
    "config/model_profiles.yaml",
    "ModelRun",
    "private research is local-only by default",
    "data-class policy",
    "advisory-only",
    "LLMs must not generate final deterministic scores",
    "target weights",
    "constraints",
    "PnL",
    "executable trade instructions",
]

LLM_PROMPT_PACK_FORBIDDEN_TERMS = [
    "place an order",
    "submit an order",
    "execute a trade",
    "route to broker",
    "broker credentials",
    "order ticket",
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


def existing_python_files(*roots: str) -> list[Path]:
    return [path for path in existing_text_files(*roots) if path.suffix == ".py"]


def markdown_section(text: str, heading: str) -> str:
    match = re.search(
        rf"^## {re.escape(heading)}\n(?P<body>.*?)(?=^## |\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    return match.group("body") if match else ""


def contract_field_names(section_body: str) -> set[str]:
    fields_match = re.search(
        r"(?:### Fields|Required fields:)\n(?P<body>.*?)(?=^### |^## |\Z)",
        section_body,
        re.MULTILINE | re.DOTALL,
    )
    fields_body = fields_match.group("body") if fields_match else section_body
    names: set[str] = set()
    for line in fields_body.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- `"):
            continue
        names.add(stripped.removeprefix("- `").split("`", 1)[0])
    return names


def model_profile_terms() -> set[str]:
    text = read_text("config/model_profiles.yaml")
    terms = set(re.findall(r"^  ([A-Za-z0-9_]+):\s*$", text, re.MULTILINE))
    terms.update(
        value.strip().strip('"').strip("'")
        for value in re.findall(
            r"^\s+(?:model_id|deployment):\s+(.+?)\s*$",
            text,
            re.MULTILINE,
        )
    )
    return {term for term in terms if term}


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

    def test_agents_md_requires_llm_mediated_audited_decisions_with_deterministic_boundaries(self) -> None:
        text = read_text("AGENTS.md")
        missing = [
            phrase
            for phrase in AGENTS_LLM_MEDIATED_DECISION_POLICY_PHRASES
            if phrase not in text
        ]
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
        self.assertRegex(current_task, r"## Governing (Specs|Docs)")
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

    def test_no_broker_order_execution_routes_or_modules_exist(self) -> None:
        route_offenders: list[str] = []
        route_pattern = re.compile(
            r"@router\.(?:get|post|put|patch|delete)\(\s*['\"](?P<path>[^'\"]+)['\"]"
        )

        for path in existing_python_files("services/api/src/ai_infra_fund_api/routes"):
            stem = path.stem.lower()
            if stem not in ALLOWED_ROUTE_MODULE_STEMS:
                for forbidden in FORBIDDEN_ROUTE_MODULE_STEMS:
                    if forbidden == stem or forbidden in stem.split("_"):
                        route_offenders.append(
                            f"{path.relative_to(ROOT)} module name contains {forbidden}"
                        )
            text = path.read_text(encoding="utf-8", errors="ignore")
            for match in route_pattern.finditer(text):
                route_path = match.group("path").lower()
                if route_path in ALLOWED_ROUTE_PATHS:
                    continue
                for forbidden in FORBIDDEN_ROUTE_PATH_TERMS:
                    if forbidden in route_path:
                        route_offenders.append(
                            f"{path.relative_to(ROOT)} exposes {match.group('path')}"
                        )

        self.assertEqual([], route_offenders)

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

    def test_frontend_public_env_surface_exposes_no_database_or_model_secrets(self) -> None:
        public_env_references: set[str] = set()
        secret_like_references: list[str] = []
        for path in existing_text_files("apps/web"):
            if path.suffix not in {".js", ".jsx", ".ts", ".tsx", ".mjs", ".json"}:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            public_env_references.update(re.findall(r"\bNEXT_PUBLIC_[A-Z0-9_]+\b", text))
            for pattern in (
                r"\bNEXT_PUBLIC_[A-Z0-9_]*(?:DATABASE|SECRET|TOKEN|API_KEY|MODEL|AZURE|OPENAI|ANTHROPIC)[A-Z0-9_]*\b",
                r"\bAI_INFRA_FUND_DATABASE_URL\b",
                r"\bAZURE_AI_FOUNDRY_API_KEY\b",
                r"\bOPENAI_API_KEY\b",
                r"\bANTHROPIC_API_KEY\b",
            ):
                if re.search(pattern, text):
                    secret_like_references.append(
                        f"{path.relative_to(ROOT)} matches {pattern}"
                    )

        unexpected_public_env = sorted(
            public_env_references - FRONTEND_PUBLIC_ENV_ALLOWLIST
        )
        self.assertEqual([], unexpected_public_env)
        self.assertEqual([], secret_like_references)

    def test_trading_advisory_contract_is_advisory_only(self) -> None:
        data_contract = read_text("docs/specs/0003-data-contracts.md")
        object_model = read_text("docs/ANALYST_OBJECT_MODEL.md")
        trading_advisory = markdown_section(data_contract, "TradingAdvisory")
        combined = f"{object_model}\n{trading_advisory}"

        missing = [phrase for phrase in TRADING_ADVISORY_POLICY_PHRASES if phrase not in combined]
        self.assertEqual([], missing)

    def test_advisory_workstation_contract_fields_exclude_execution_surfaces(self) -> None:
        offenders: list[str] = []
        for relative_path in ADVISORY_WORKSTATION_CONTRACT_DOCS:
            text = read_text(relative_path)
            for object_name in ADVISORY_WORKSTATION_CONTRACT_OBJECTS:
                body = markdown_section(text, object_name)
                self.assertTrue(body, f"{relative_path} missing {object_name}")
                for field_name in contract_field_names(body):
                    lowered = field_name.lower()
                    for forbidden in FORBIDDEN_ADVISORY_CONTRACT_FIELD_TERMS:
                        if (object_name, field_name, forbidden) in ADVISORY_CONTRACT_FIELD_TERM_ALLOWLIST:
                            continue
                        if forbidden in lowered:
                            offenders.append(
                                f"{relative_path} {object_name}.{field_name} contains {forbidden}"
                            )

        self.assertEqual([], offenders)

    def test_core_contracts_exclude_executable_order_fields(self) -> None:
        offenders: list[str] = []
        for path in existing_python_files("packages/core/src/ai_infra_fund_core/contracts"):
            text = path.read_text(encoding="utf-8", errors="ignore")
            for field_name in re.findall(r"^\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*:", text, re.MULTILINE):
                lowered = field_name.lower()
                for forbidden in ("broker", "route", "exchange", "order_id", "execution_id", "auto_trade"):
                    if forbidden in lowered:
                        offenders.append(
                            f"{path.relative_to(ROOT)} field {field_name} contains {forbidden}"
                        )
        self.assertEqual([], offenders)

    def test_recommendation_artifact_requires_advisory_lineage(self) -> None:
        core_src = ROOT / "packages" / "core" / "src"
        sys.path.insert(0, str(core_src))

        from ai_infra_fund_core.contracts.common import RecommendationAction
        from ai_infra_fund_core.contracts.recommendations import RecommendationArtifact

        base = {
            "recommendation_id": "rec-1",
            "ticker_or_portfolio": "NVDA",
            "advisory_label": "advisory_only",
            "action": RecommendationAction.ACCUMULATE,
            "horizon": "2w",
            "score_breakdown": {"strategic": "0.72"},
            "target_weights_id": "tw-1",
            "evidence_ids": ("evidence-1",),
            "model_run_ids": ("model-run-1",),
            "signal_bundle_id": "signal-1",
            "risks": ("valuation",),
            "contradictions": (),
            "final_payload": {"advisory": "accumulate"},
            "created_at": datetime.now(timezone.utc),
        }

        RecommendationArtifact(**base)
        invalid_cases = {
            "advisory_label": "not_advisory",
            "target_weights_id": "",
            "evidence_ids": (),
            "model_run_ids": (),
            "signal_bundle_id": "",
        }
        for field_name, invalid_value in invalid_cases.items():
            payload = {**base, field_name: invalid_value}
            with self.subTest(field_name=field_name):
                with self.assertRaises(ValueError):
                    RecommendationArtifact(**payload)

    def test_crawler_specs_forbid_arbitrary_crawling_and_execution_outputs(self) -> None:
        crawler_spec = read_text("docs/specs/0016-equity-intelligence-crawler.md")
        runtime_spec = read_text("docs/specs/0017-crawl-pipeline-runtime.md")

        missing_crawler = [
            phrase for phrase in CRAWLER_BOUNDARY_PHRASES if phrase not in crawler_spec
        ]
        missing_runtime = [
            phrase for phrase in CRAWL_RUNTIME_BOUNDARY_PHRASES if phrase not in runtime_spec
        ]

        self.assertEqual([], missing_crawler, "0016 crawler policy gaps")
        self.assertEqual([], missing_runtime, "0017 runtime policy gaps")

    def test_deterministic_ownership_remains_protected(self) -> None:
        combined = "\n".join(
            read_text(relative_path)
            for relative_path in (
                "docs/ANALYST_OBJECT_MODEL.md",
                "docs/specs/0003-data-contracts.md",
                "docs/specs/0016-equity-intelligence-crawler.md",
                "docs/specs/0017-crawl-pipeline-runtime.md",
            )
        )

        missing = [
            phrase for phrase in DETERMINISTIC_OWNERSHIP_PHRASES if phrase not in combined
        ]
        self.assertEqual([], missing)

    def test_deterministic_analysis_modules_do_not_import_llm_or_router_clients(self) -> None:
        offenders: list[str] = []
        for root in DETERMINISTIC_MODULE_ROOTS:
            for path in existing_python_files(root):
                text = path.read_text(encoding="utf-8", errors="ignore")
                for pattern in FORBIDDEN_MODEL_CLIENT_IMPORT_PATTERNS:
                    if re.search(pattern, text, re.MULTILINE):
                        offenders.append(f"{path.relative_to(ROOT)} matches {pattern}")
        self.assertEqual([], offenders)

    def test_business_logic_does_not_hard_code_model_deployment_names(self) -> None:
        model_terms = model_profile_terms()
        offenders: list[str] = []
        for path in existing_text_files("apps", "packages", "services", "scripts"):
            if path.suffix not in {".py", ".js", ".mjs", ".ts", ".tsx", ".json", ".sh", ".yaml", ".yml"}:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for term in model_terms:
                if term in text:
                    offenders.append(f"{path.relative_to(ROOT)} contains {term}")
        self.assertEqual([], offenders)

    def test_private_research_routes_only_to_local_allowed_profiles(self) -> None:
        core_src = ROOT / "packages" / "core" / "src"
        sys.path.insert(0, str(core_src))

        from ai_infra_fund_core.contracts.common import DataClass
        from ai_infra_fund_core.model_routing.profiles import load_model_profiles
        from ai_infra_fund_core.model_routing.router import ModelRouteDenied, ModelRouter

        catalog = load_model_profiles(ROOT / "config" / "model_profiles.yaml")
        router = ModelRouter(catalog)
        for profile in catalog.profiles.values():
            if profile.endpoint_type != "local":
                with self.subTest(profile=profile.profile_id):
                    self.assertFalse(
                        router.is_allowed(
                            profile,
                            data_classes=(DataClass.PRIVATE_RESEARCH,),
                        )
                    )

        roles = sorted({role for profile in catalog.profiles.values() for role in profile.task_roles})
        for role in roles:
            with self.subTest(role=role):
                try:
                    route = router.resolve(role, data_classes=(DataClass.PRIVATE_RESEARCH,))
                except ModelRouteDenied:
                    continue
                self.assertEqual("local", route.profile.endpoint_type)
                unsafe_allowed_fallbacks = [
                    profile.profile_id
                    for profile in route.fallback_chain
                    if profile.endpoint_type != "local"
                    and router.is_allowed(
                        profile,
                        data_classes=(DataClass.PRIVATE_RESEARCH,),
                    )
                ]
                self.assertEqual([], unsafe_allowed_fallbacks)

    def test_v1_dependencies_and_imports_do_not_include_duckdb_or_parquet_store(self) -> None:
        dependency_files = [
            "pyproject.toml",
            "services/api/requirements.txt",
            "services/worker/requirements.txt",
            "apps/web/package.json",
            "apps/web/package-lock.json",
        ]
        offenders: list[str] = []
        for relative_path in dependency_files:
            text = read_text(relative_path).lower()
            for dependency in FORBIDDEN_V1_STORAGE_DEPENDENCIES:
                if re.search(rf"['\"]?{re.escape(dependency)}(?:==|>=|<=|~=|['\"]|:)", text):
                    offenders.append(f"{relative_path} declares {dependency}")

        for path in existing_python_files("apps", "packages", "services", "scripts"):
            text = path.read_text(encoding="utf-8", errors="ignore")
            for pattern in FORBIDDEN_V1_STORAGE_IMPORT_PATTERNS:
                if re.search(pattern, text, re.MULTILINE):
                    offenders.append(f"{path.relative_to(ROOT)} matches {pattern}")

        self.assertEqual([], offenders)

    def test_postgresql_pgvector_remains_canonical_fact_spine(self) -> None:
        architecture = read_text("docs/ARCHITECTURE.md")
        migration = read_text("services/api/migrations/0001_phase2_data_spine.sql")
        docker_compose = read_text("docker-compose.yml")

        self.assertIn("PostgreSQL + pgvector owns all v1 durable records", architecture)
        self.assertIn("CREATE EXTENSION IF NOT EXISTS vector", migration)
        self.assertIn("postgres:", docker_compose)
        self.assertIn("pgvector", docker_compose)

        bypass_offenders: list[str] = []
        for path in existing_python_files("packages", "services", "scripts"):
            text = path.read_text(encoding="utf-8", errors="ignore")
            for pattern in (
                r"^\s*(?:from|import)\s+sqlite3\b",
                r"^\s*(?:from|import)\s+sqlite_vec\b",
                r"^\s*(?:from|import)\s+lancedb\b",
            ):
                if re.search(pattern, text, re.MULTILINE):
                    bypass_offenders.append(f"{path.relative_to(ROOT)} matches {pattern}")
        self.assertEqual([], bypass_offenders)

    def test_raw_private_files_and_env_files_are_not_tracked(self) -> None:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
        offenders: list[str] = []
        for tracked_path in result.stdout.splitlines():
            if tracked_path in TRACKED_SECRET_ALLOWLIST:
                continue
            for pattern in TRACKED_SECRET_OR_PRIVATE_PATTERNS:
                if re.search(pattern, tracked_path):
                    offenders.append(tracked_path)
        self.assertEqual([], offenders)

    def test_market_event_without_evidence_cannot_reach_signal_policy(self) -> None:
        core_src = ROOT / "packages" / "core" / "src"
        sys.path.insert(0, str(core_src))

        from ai_infra_fund_core.contracts.events import MarketEvent

        with self.assertRaises(ValueError):
            MarketEvent(
                event_id="event-1",
                event_type="capex_signal",
                source_evidence_ids=(),
                tickers=("NVDA",),
                companies=("Nvidia",),
                themes=("accelerator demand",),
                catalyst="Hyperscaler capex raised.",
                ai_relevance="Higher AI infrastructure demand.",
                direction="positive",
                time_horizon="short_to_medium",
                confidence="0.7",
                occurred_at=datetime.now(timezone.utc),
                available_at=datetime.now(timezone.utc),
                content_hash="hash-1",
                extracted_by_model_run_id="model-run-1",
                review_status="usable",
            )

    def test_llm_prompt_pack_if_present_preserves_deterministic_boundary(self) -> None:
        prompt_pack = ROOT / "docs" / "LLM_ANALYST_PROMPT_PACK.md"
        if not prompt_pack.exists():
            return

        text = prompt_pack.read_text(encoding="utf-8")
        missing = [
            phrase for phrase in LLM_PROMPT_PACK_REQUIRED_BOUNDARY_PHRASES if phrase not in text
        ]
        forbidden_present = [
            phrase for phrase in LLM_PROMPT_PACK_FORBIDDEN_TERMS if phrase in text.lower()
        ]
        self.assertEqual([], missing)
        self.assertEqual([], forbidden_present)

    def test_research_extractor_result_names_exclude_deterministic_and_execution_outputs(self) -> None:
        import sys

        core_src = ROOT / "packages" / "core" / "src"
        sys.path.insert(0, str(core_src))

        from ai_infra_fund_core.equity_intelligence import research_extractor

        output_classes = [
            research_extractor.EvidenceClaimDraft,
            research_extractor.SourceSignalDraft,
            research_extractor.MarketEventDraft,
            research_extractor.ModelRunRecord,
            research_extractor.ResearchExtractionResult,
            research_extractor.SuppressedModelOutput,
        ]
        output_names = {
            class_.__name__
            for class_ in output_classes
        }
        for class_ in output_classes:
            output_names.update(field.name for field in dataclasses.fields(class_))

        offenders = [
            name
            for name in sorted(output_names)
            for forbidden in LLM_EXTRACTION_FORBIDDEN_OUTPUT_NAME_TERMS
            if forbidden in name.lower()
        ]
        self.assertEqual([], offenders)


if __name__ == "__main__":
    unittest.main()
