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
    "app/api/backend/[...path]/route.ts",
    "app/ticker/[ticker]/page.tsx",
    "app/evidence/page.tsx",
    "app/signals/page.tsx",
    "app/runs/page.tsx",
    "app/evaluation/page.tsx",
    "app/ops/page.tsx",
    "app/incidents/page.tsx",
    "app/globals.css",
    "components/app-shell.tsx",
    "components/trade-entry-form.tsx",
    "components/hedge-fund-component-map.tsx",
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
    "Hedge Fund Component Map",
    "Data Spine",
    "Evidence & Research",
    "Signal Factory",
    "Portfolio & Advisory",
    "Governance & Ops",
    "Auto-updates from live module summaries",
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
ALLOWED_MUTATION_ENDPOINTS = {
    "POST": "/internal/trade-journal/entries",
}

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
        combined = "\n".join(
            path.read_text(encoding="utf-8") for path in web_source_files()
        )
        # The Daily Brief landing now surfaces sentiment / news / portfolio /
        # actions. The full control-room artifact set lives at /ops and on the
        # advisory-chain trace endpoint, not on the home page.
        landing_required = [
            "Advisory-only",
            "Portfolio",
            "Evidence",
            "Recommendations",
            "Watchlist Status",
            "Latest Equity Events",
            "Sentiment / Technical / Fundamental",
            "Latest Advisory Run",
        ]
        missing = [text for text in landing_required if text not in combined]
        self.assertEqual([], missing)

    def test_dashboard_is_not_a_marketing_hero(self) -> None:
        page = read_web("app/page.tsx")
        css = read_web("app/globals.css")
        # Forbid marketing-hero patterns (banner/landing/cta-hero), but allow
        # the functional `hero-kpi-strip` used by the Daily Brief.
        combined = f"{page}\n{css}"
        for forbidden in ("hero-banner", "landing-hero", "marketing-hero"):
            self.assertNotIn(
                forbidden,
                combined,
                "dashboard must not use marketing/hero/landing-page layout",
            )
        self.assertIn("control-room-shell", page)
        # The ops-room view now lives at /ops, not /.
        ops_page = read_web("app/ops/page.tsx")
        self.assertIn("ops room", ops_page.lower())

    def test_frontend_design_system_uses_operational_chrome_and_dense_responsive_patterns(
        self,
    ) -> None:
        shell = read_web("components/app-shell.tsx")
        status_tile = read_web("components/status-tile.tsx")
        css = read_web("app/globals.css")
        required_shell_text = [
            "nav-section",
            "nav-section-title",
            "topbar-rail",
            "topbar-chip",
            "workspace-signal",
        ]
        required_status_text = ["status-beacon"]
        required_css_text = [
            "--surface-panel",
            "--accent-amber",
            ".app-frame::before",
            ".topbar-rail",
            ".section-panel::before",
            ".component-map-flow span::before",
            "@media (max-width: 1180px)",
        ]
        self.assertEqual(
            [], [text for text in required_shell_text if text not in shell]
        )
        self.assertEqual(
            [], [text for text in required_status_text if text not in status_tile]
        )
        self.assertEqual([], [text for text in required_css_text if text not in css])

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

    def test_frontend_fetches_read_only_dashboard_summaries_with_get_endpoints(
        self,
    ) -> None:
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
            for method in ("PUT", "PATCH", "DELETE")
            if re.search(rf"method:\s*[\"']{method}[\"']", api)
        ]
        self.assertEqual([], forbidden_methods)

    def test_frontend_has_same_origin_read_only_backend_proxy_for_deployment(
        self,
    ) -> None:
        proxy = read_web("app/api/backend/[...path]/route.ts")
        required = [
            "AI_INFRA_FUND_INTERNAL_API_BASE_URL",
            "GET",
            "forwardReadOnlyBackendRequest",
            'method: "GET"',
            "NextResponse",
        ]
        self.assertEqual([], [text for text in required if text not in proxy])
        self.assertNotIn("export async function POST", proxy)
        self.assertNotIn('method: "POST"', proxy)

    def test_dashboard_summary_fetches_have_degraded_backend_fallbacks(self) -> None:
        api = read_web("lib/api.ts")
        self.assertIn("degraded", api)
        self.assertIn("Backend unavailable", api)
        self.assertIn("createUnavailableDashboardSummary", api)
        self.assertRegex(api, r"catch\s*\(")

    def test_status_model_maps_live_summaries_and_modules_to_visible_statuses(
        self,
    ) -> None:
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
        combined = "\n".join(
            path.read_text(encoding="utf-8") for path in web_source_files()
        )
        offenders = [
            pattern
            for pattern in FORBIDDEN_FRONTEND_IMPORT_PATTERNS
            if re.search(pattern, combined)
        ]
        self.assertEqual([], offenders)

    def test_frontend_only_allows_trade_journal_post_mutation(self) -> None:
        combined = "\n".join(
            path.read_text(encoding="utf-8") for path in web_source_files()
        )
        for method in ("PUT", "PATCH", "DELETE"):
            self.assertNotRegex(combined, rf"method:\s*[\"']{method}[\"']")
        self.assertIn('method: "POST"', combined)
        self.assertIn(ALLOWED_MUTATION_ENDPOINTS["POST"], combined)
        self.assertIn("createTradeJournalEntry", combined)
        self.assertNotIn("/internal/evidence/manual", combined)
        self.assertNotIn("/internal/recommendations", combined)

    def test_dashboard_renders_advisory_chain_sections_from_read_only_payload(
        self,
    ) -> None:
        # The advisory chain trace fetcher and chain field names continue to
        # live in the shared API client / status model after the Daily Brief
        # redesign. The chain itself is rendered on /runs (and any future
        # advisory-chain detail page), not on the landing.
        combined = "\n".join(
            path.read_text(encoding="utf-8") for path in web_source_files()
        )
        required = [
            "advisory_label",
            "model_run_ids",
            "evidence_id",
            "fetchLatestAdvisoryChain",
        ]
        missing = [text for text in required if text not in combined]
        self.assertEqual([], missing)

    def test_dashboard_renders_phase10_read_only_intelligence_sections(self) -> None:
        combined = "\n".join(
            path.read_text(encoding="utf-8") for path in web_source_files()
        )
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
        combined = "\n".join(
            path.read_text(encoding="utf-8") for path in web_source_files()
        )
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

    def test_hedge_fund_component_map_is_data_driven_and_live_updated(self) -> None:
        component = read_web("components/hedge-fund-component-map.tsx")
        ops_page = read_web("app/ops/page.tsx")

        required_component_text = [
            "Hedge Fund Component Map",
            "Data Spine",
            "Evidence & Research",
            "Signal Factory",
            "Portfolio & Advisory",
            "Governance & Ops",
            "ModuleStatusRecord",
            "STATUS_TONE_MAP",
            "modules.map",
            "sourceLabel",
            "status",
            'data-testid="hedge-fund-component-map"',
        ]
        missing = [text for text in required_component_text if text not in component]
        self.assertEqual([], missing)
        # The architecture component map and live-module refresh now live at
        # /ops; the landing is reserved for the Daily Brief.
        self.assertIn("<HedgeFundComponentMap", ops_page)
        self.assertIn("modules={modules}", ops_page)
        self.assertIn("Auto-updates from live module summaries", ops_page)
        self.assertIn("setInterval(refreshOpsModules, 30000)", ops_page)

    def test_manual_trade_intent_workflow_is_local_and_advisory_only(self) -> None:
        combined = "\n".join(
            path.read_text(encoding="utf-8") for path in web_source_files()
        )
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

    def test_manual_trade_entry_form_posts_only_to_local_journal(self) -> None:
        combined = "\n".join(
            path.read_text(encoding="utf-8") for path in web_source_files()
        )
        required = [
            "Add Trade To Local Journal",
            "createTradeJournalEntry",
            "fetchTradeJournalEntries",
            "/internal/trade-journal/entries",
            "Manual buy/sell journal entry",
            "Journal-only record",
            "Trade date",
            "Settlement date",
            "Account label",
            "Local journal only",
            "No broker connection",
        ]
        missing = [text for text in required if text not in combined]
        self.assertEqual([], missing)

    def test_no_order_or_broker_execution_ui_labels_exist(self) -> None:
        combined = "\n".join(
            path.read_text(encoding="utf-8") for path in web_source_files()
        )
        offenders = [
            pattern
            for pattern in FORBIDDEN_UI_LABEL_PATTERNS
            if re.search(pattern, combined, re.IGNORECASE)
        ]
        self.assertEqual([], offenders)


if __name__ == "__main__":
    unittest.main()
