from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / "apps" / "web"

REQUIRED_UI_FILES = [
    "app/page.tsx",
    "app/portfolio/page.tsx",
    "app/trade-intents/page.tsx",
    "app/trade-journal/page.tsx",
    "app/watchlist/page.tsx",
    "app/ticker/[ticker]/page.tsx",
    "app/evidence/page.tsx",
    "app/signals/page.tsx",
    "app/runs/page.tsx",
    "app/evaluation/page.tsx",
    "app/ops/page.tsx",
    "app/incidents/page.tsx",
    "app/globals.css",
    "components/app-shell.tsx",
    "components/status-tile.tsx",
    "components/module-grid.tsx",
    "components/section-panel.tsx",
    "lib/api.ts",
    "lib/portfolio-data.ts",
    "lib/status-model.ts",
]

REQUIRED_DASHBOARD_TEXT = [
    "AI Infrastructure Fund Control Room",
    "Advisory-only",
    "System Status",
    "Portfolio",
    "Evidence",
    "Recommendations",
    "Evaluation",
    "Model Runs",
    "Data Quality",
    "Incidents",
    "System Architecture",
    "Watchlist Status",
    "Crawl Freshness",
    "Latest Equity Events",
    "Sentiment / Technical / Fundamental",
    "Latest Advisory Run",
    "Ticker Intelligence",
    "Evidence And Audit Trace",
    "Portfolio Workbench",
    "Manual Trade Intents",
    "Trade Journal",
    "Ticker Workbench",
    "Signals",
    "Runs",
    "Ops Room",
    "Latest Advisory Chain",
    "Evidence -> Chunk -> Claim -> SignalBundle -> TargetWeights -> Recommendation -> Audit -> Evaluation",
    "recommendation-demo-nvda",
    "target-weights-demo-ai-infra",
    "signal-bundle-demo-nvda",
]

REQUIRED_MODULE_IDS = [
    "api",
    "worker",
    "postgres",
    "ui",
    "data-plane",
    "evidence-plane",
    "signal-plane",
    "portfolio-engine",
    "model-router",
    "recommendation-artifacts",
    "evaluation-harness",
    "trade-journal",
]

FORBIDDEN_UI_LABEL_PATTERNS = [
    r">\s*Place\s+Order\s*<",
    r">\s*Submit\s+Order\s*<",
    r">\s*Execute\s+Order\s*<",
    r">\s*Connect\s+Broker\s*<",
    r">\s*Start\s+Live\s+Trading\s*<",
]

READ_ONLY_DASHBOARD_ENDPOINTS = [
    "/internal/status/overview",
    "/internal/status/modules",
    "/internal/dashboard/evidence-summary",
    "/internal/dashboard/recommendation-summary",
    "/internal/dashboard/evaluation-summary",
    "/internal/dashboard/model-run-summary",
    "/internal/dashboard/data-quality-summary",
    "/internal/dashboard/incident-summary",
    "/internal/dashboard/watchlist-summary",
    "/internal/dashboard/crawl-frontier-health",
    "/internal/dashboard/latest-equity-events",
    "/internal/dashboard/latest-signal-snapshots",
    "/internal/dashboard/latest-advisory-run",
    "/internal/dashboard/ticker-intelligence/NVDA",
    "/internal/advisory-chain/latest",
    "/internal/advisory-chain/demo",
]

FORBIDDEN_FETCH_METHODS = ["POST", "PUT", "PATCH", "DELETE"]

FORBIDDEN_FRONTEND_IMPORT_PATTERNS = [
    r"from\s+[\"'].*backend",
    r"from\s+[\"'].*repository",
    r"from\s+[\"'].*repositories",
    r"from\s+[\"'].*database",
    r"from\s+[\"'].*db",
    r"@/backend",
    r"@/repositories",
    r"@/database",
]


def read_web(relative_path: str) -> str:
    return (WEB_ROOT / relative_path).read_text(encoding="utf-8")


def web_source_files() -> list[Path]:
    return [
        path
        for path in WEB_ROOT.rglob("*")
        if path.is_file()
        and "node_modules" not in path.parts
        and ".next" not in path.parts
        and path.suffix in {".css", ".ts", ".tsx"}
    ]


class ControlRoomUiTests(unittest.TestCase):
    def test_required_ui_files_exist(self) -> None:
        missing = [
            relative_path
            for relative_path in REQUIRED_UI_FILES
            if not (WEB_ROOT / relative_path).is_file()
        ]
        self.assertEqual([], missing)

    def test_dashboard_renders_required_sections_and_advisory_label(self) -> None:
        combined = "\n".join(path.read_text(encoding="utf-8") for path in web_source_files())
        missing = [text for text in REQUIRED_DASHBOARD_TEXT if text not in combined]
        self.assertEqual([], missing)

    def test_dashboard_is_not_a_marketing_hero(self) -> None:
        page = read_web("app/page.tsx")
        css = read_web("app/globals.css")
        self.assertNotRegex(f"{page}\n{css}", r"\bhero\b", "dashboard must not use hero/landing-page layout")
        self.assertIn("control-room-shell", page)
        self.assertIn("ops-room", page)

    def test_module_statuses_have_colors_and_sources(self) -> None:
        model = read_web("lib/status-model.ts")
        for status in ("passing", "degraded", "failing", "planned"):
            self.assertIn(status, model)
        for tone in ("green", "yellow", "red", "gray"):
            self.assertIn(tone, model)
        for module_id in REQUIRED_MODULE_IDS:
            self.assertIn(f'id: "{module_id}"', model)
        self.assertIn("sourceType", model)
        self.assertIn("sourceLabel", model)

    def test_api_status_fetch_handles_unavailable_backend(self) -> None:
        api = read_web("lib/api.ts")
        self.assertIn("fetchApiHealth", api)
        self.assertIn("fetchApiReadiness", api)
        self.assertIn("unavailable", api)
        self.assertIn("Backend unavailable", api)
        self.assertRegex(api, r"catch\s*\(")

    def test_frontend_fetches_read_only_dashboard_summaries_with_get_endpoints(self) -> None:
        api = read_web("lib/api.ts")
        for endpoint in READ_ONLY_DASHBOARD_ENDPOINTS:
            self.assertIn(endpoint, api)
        for summary_fetch in (
            "fetchDashboardOverview",
            "fetchDashboardModules",
            "fetchEvidenceSummary",
            "fetchRecommendationSummary",
            "fetchEvaluationSummary",
            "fetchModelRunSummary",
            "fetchDataQualitySummary",
            "fetchIncidentSummary",
            "fetchWatchlistSummary",
            "fetchCrawlFrontierHealth",
            "fetchLatestEquityEvents",
            "fetchLatestSignalSnapshots",
            "fetchLatestAdvisoryRun",
            "fetchTickerIntelligenceSummary",
            "fetchLatestAdvisoryChain",
            "fetchDemoAdvisoryChain",
        ):
            self.assertIn(summary_fetch, api)
        self.assertRegex(api, r"method:\s*[\"']GET[\"']")
        forbidden_methods = [
            method
            for method in FORBIDDEN_FETCH_METHODS
            if re.search(rf"method:\s*[\"']{method}[\"']", api)
        ]
        self.assertEqual([], forbidden_methods)

    def test_dashboard_summary_fetches_have_degraded_backend_fallbacks(self) -> None:
        api = read_web("lib/api.ts")
        self.assertIn("degraded", api)
        self.assertIn("Backend unavailable", api)
        self.assertIn("createUnavailableDashboardSummary", api)
        self.assertRegex(api, r"catch\s*\(")

    def test_status_model_maps_live_summaries_and_modules_to_visible_statuses(self) -> None:
        model = read_web("lib/status-model.ts")
        for symbol in (
            "DashboardOverviewSummary",
            "DashboardModuleSummary",
            "DashboardSummaryFeed",
            "applyLiveModuleSummaries",
            "moduleStatusFromSummary",
            "dashboardFeedToRuntimeProbe",
        ):
            self.assertIn(symbol, model)
        for status in ("passing", "degraded", "failing", "planned"):
            self.assertIn(status, model)
        self.assertIn("visibleValue", model)
        self.assertIn("sourceLabel", model)

    def test_frontend_has_no_db_backend_repository_imports(self) -> None:
        combined = "\n".join(path.read_text(encoding="utf-8") for path in web_source_files())
        offenders = [
            pattern
            for pattern in FORBIDDEN_FRONTEND_IMPORT_PATTERNS
            if re.search(pattern, combined)
        ]
        self.assertEqual([], offenders)

    def test_frontend_has_no_mutation_fetch_methods(self) -> None:
        combined = "\n".join(path.read_text(encoding="utf-8") for path in web_source_files())
        forbidden_methods = [
            method
            for method in FORBIDDEN_FETCH_METHODS
            if re.search(rf"method:\s*[\"']{method}[\"']", combined)
        ]
        self.assertEqual([], forbidden_methods)

    def test_dashboard_renders_advisory_chain_sections_from_read_only_payload(self) -> None:
        combined = "\n".join(path.read_text(encoding="utf-8") for path in web_source_files())
        required = [
            "Latest Advisory Chain",
            "Evidence",
            "Chunk",
            "Claim",
            "SignalBundle",
            "TargetWeights",
            "Recommendation",
            "Audit",
            "Evaluation",
            "advisory_label",
            "model_run_ids",
            "evidence_id",
            "fetchLatestAdvisoryChain",
        ]
        missing = [text for text in required if text not in combined]
        self.assertEqual([], missing)

    def test_dashboard_renders_phase10_read_only_intelligence_sections(self) -> None:
        combined = "\n".join(path.read_text(encoding="utf-8") for path in web_source_files())
        required = [
            "Watchlist Status",
            "Crawl Freshness",
            "Latest Equity Events",
            "Sentiment / Technical / Fundamental",
            "Latest Advisory Run",
            "Ticker Intelligence",
            "Evidence And Audit Trace",
            "sentiment_score",
            "technical_score",
            "fundamental_score",
            "advisory_label",
            "evidence_ids",
            "model_run_ids",
            "audit_id",
        ]
        missing = [text for text in required if text not in combined]
        self.assertEqual([], missing)

    def test_dashboard_has_empty_state_for_missing_advisory_chain(self) -> None:
        combined = "\n".join(path.read_text(encoding="utf-8") for path in web_source_files())
        self.assertIn("No local advisory chain has been produced", combined)
        self.assertIn("empty", combined)

    def test_frontend_has_multi_page_control_room_routes(self) -> None:
        for relative_path in (
            "app/portfolio/page.tsx",
            "app/trade-intents/page.tsx",
            "app/trade-journal/page.tsx",
            "app/watchlist/page.tsx",
            "app/ticker/[ticker]/page.tsx",
            "app/evidence/page.tsx",
            "app/signals/page.tsx",
            "app/runs/page.tsx",
            "app/evaluation/page.tsx",
            "app/ops/page.tsx",
            "app/incidents/page.tsx",
        ):
            self.assertTrue((WEB_ROOT / relative_path).is_file(), relative_path)

    def test_manual_trade_intent_workflow_is_local_and_advisory_only(self) -> None:
        combined = "\n".join(path.read_text(encoding="utf-8") for path in web_source_files())
        required = [
            "Manual Trade Intents",
            "Read-Only Planning Placeholder",
            "Intent capture remains disabled",
            "No local save action",
            "does not write browser storage",
            "recommendation_id",
            "evidence_ids",
            "model_run_ids",
            "audit_id",
            "Local journal only",
            "No broker connection",
        ]
        missing = [text for text in required if text not in combined]
        self.assertEqual([], missing)
        self.assertNotIn("localStorage.setItem", combined)
        self.assertNotIn("Save Trade Intent", combined)

    def test_no_order_or_broker_execution_ui_labels_exist(self) -> None:
        combined = "\n".join(path.read_text(encoding="utf-8") for path in web_source_files())
        offenders = [
            pattern
            for pattern in FORBIDDEN_UI_LABEL_PATTERNS
            if re.search(pattern, combined, re.IGNORECASE)
        ]
        self.assertEqual([], offenders)


if __name__ == "__main__":
    unittest.main()
