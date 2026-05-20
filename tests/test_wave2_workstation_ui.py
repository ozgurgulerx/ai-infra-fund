from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / "apps" / "web"


def read_web(relative_path: str) -> str:
    return (WEB_ROOT / relative_path).read_text(encoding="utf-8")


def combined_web_source() -> str:
    source = []
    for path in WEB_ROOT.rglob("*"):
        if path.is_file() and path.suffix in {".ts", ".tsx", ".css"}:
            if "node_modules" in path.parts or ".next" in path.parts:
                continue
            source.append(path.read_text(encoding="utf-8"))
    return "\n".join(source)


class Wave2WorkstationUiTests(unittest.TestCase):
    def test_wave2_routes_exist(self) -> None:
        required = [
            "app/page.tsx",
            "app/segments/page.tsx",
            "app/radar/page.tsx",
            "app/ticker/[ticker]/page.tsx",
            "app/trade-plans/page.tsx",
            "app/trade-intents/page.tsx",
            "app/trade-journal/page.tsx",
            "lib/situational-awareness/mock-workstation-data.ts",
        ]
        missing = [path for path in required if not (WEB_ROOT / path).is_file()]
        self.assertEqual([], missing)

    def test_daily_trading_cockpit_renders_api_backed_advisory_workstation_sections(self) -> None:
        page = read_web("app/page.tsx")
        required = [
            "Daily Trading Cockpit",
            "AI infrastructure regime",
            "Executive summary",
            "Top MarketEvents",
            "Segment impact snapshot",
            "Equity impact assessments",
            "Risk regime updates",
            "LLM analyst notes",
            "Suggested actions",
            "Open trade plans",
            "Portfolio exposure snapshot",
            "Invalidation watchlist",
            "readCockpitPayload",
            "API read model",
        ]
        self.assertEqual([], [text for text in required if text not in page])
        self.assertIn("/internal/analyst-brief/latest", page)
        self.assertIn("/internal/source-signals/latest", page)
        self.assertNotIn("mockWorkstationData", page)

    def test_premium_workstation_components_and_evidence_disclosure_exist(self) -> None:
        components = read_web("components/workstation.tsx")
        page = read_web("app/page.tsx")
        ticker_page = read_web("app/ticker/[ticker]/page.tsx")
        css = read_web("app/globals.css")

        required_components = [
            "PageHeader",
            "MetricTile",
            "StatusChip",
            "AdvisoryTable",
            "EvidenceDrawer",
            "SectionCard",
            "EmptyState",
            "RiskBadge",
            "LlmReviewBadge",
        ]
        self.assertEqual(
            [],
            [component for component in required_components if component not in components],
        )
        self.assertIn("EvidenceDrawer", page)
        self.assertIn("EvidenceDrawer", ticker_page)
        self.assertIn("evidence-drawer", components)
        self.assertIn("evidence-drawer", css)
        self.assertNotIn("No invalidation condition reported", page)
        self.assertIn("Invalidation not yet defined", page)

    def test_ticker_workbench_evidence_drawer_uses_all_theme_and_payload_evidence(self) -> None:
        ticker_page = read_web("app/ticker/[ticker]/page.tsx")

        required_sources = [
            "theme_groups.flatMap((theme) => theme.evidence_ids)",
            "payload.source_signals",
            "payload.market_events",
            "payload.equity_impact_assessments",
            "payload.trading_advisories",
        ]
        self.assertEqual([], [source for source in required_sources if source not in ticker_page])
        self.assertNotIn("primaryGroup?.evidence_ids ?? evidenceIds", ticker_page)

    def test_daily_cockpit_keeps_low_confidence_events_out_of_top_events(self) -> None:
        page = read_web("app/page.tsx")

        self.assertIn("const lowConfidenceEvents = marketEvents.filter", page)
        self.assertIn("const coreMarketEvents = marketEvents.filter", page)
        self.assertIn("const topEvents = coreMarketEvents.slice(0, 4);", page)
        self.assertNotIn("const topEvents = marketEvents.slice(0, 4);", page)

    def test_value_chain_atlas_is_candidate_matrix_with_ai_grid_lens(self) -> None:
        page = read_web("app/themes/page.tsx")
        component = read_web("components/value-chain-candidate-matrix.tsx")
        css = read_web("app/globals.css")
        combined = f"{page}\n{component}\n{css}"
        required = [
            "Value-Chain Candidate Matrix",
            "AI Grid",
            "Candidate matrix",
            "readLatestWatchlistRatings",
            "Current advisory stance",
            "Risk / invalidation",
            "Evidence refs",
            "Accumulate candidates",
            "Watch / review",
            "Ticker workbench",
            "value-chain-candidate-row",
            "value-chain-lens-bar",
        ]

        self.assertEqual([], [text for text in required if text not in combined])
        self.assertNotIn("Must Buy", combined)

    def test_segment_map_ticker_workbench_trade_and_radar_screens_have_wave2_content(self) -> None:
        expectations = {
            "app/segments/page.tsx": [
                "AI Infrastructure Ecosystem Map",
                "first-order beneficiaries",
                "second-order beneficiaries",
                "negatively exposed",
                "related MarketEvents",
            ],
            "app/ticker/[ticker]/page.tsx": [
                "Ticker Analyst Workbench",
                "Summary",
                "Themes",
                "News / Events",
                "Related Tickers",
                "Evidence",
                "Bull case",
                "Bear case",
                "Price target scenarios",
                "Entry / add / invalidation levels",
                "LLM analyst critique",
            ],
            "app/trade-plans/page.tsx": [
                "Trade Plan Workbench",
                "planning guidance only",
                "position-sizing note",
                "portfolio impact",
                "LLM critique",
            ],
            "app/trade-journal/page.tsx": [
                "Trade Journal + PnL Review",
                "manual journal only",
                "realized/unrealized PnL",
                "post-trade LLM review",
                "PnL by segment",
            ],
            "app/radar/page.tsx": [
                "Live Market / Sentiment Radar",
                "classified intelligence",
                "event feed",
                "review priority",
                "LLM scout notes",
                "correlation/sector movement",
            ],
        }
        for relative_path, required in expectations.items():
            text = read_web(relative_path)
            normalized = text.lower()
            with self.subTest(relative_path=relative_path):
                self.assertEqual(
                    [],
                    [item for item in required if item.lower() not in normalized],
                )

    def test_wave2_static_adapter_preserves_evidence_and_invalidation_links(self) -> None:
        adapter = read_web("lib/situational-awareness/mock-workstation-data.ts")
        required = [
            "marketEvents",
            "segmentImpacts",
            "equityAssessments",
            "riskRegimes",
            "llmAnalystNotes",
            "suggestedActions",
            "openTradePlans",
            "portfolioSnapshot",
            "priceTargetScenarios",
            "entryExitLevels",
            "correlationExposures",
            "evidenceIds",
            "modelRunIds",
            "riskFlags",
            "invalidationCondition",
        ]
        self.assertEqual([], [item for item in required if item not in adapter])

    def test_wave2_ui_has_no_broker_order_or_execution_controls(self) -> None:
        combined = combined_web_source()
        forbidden_patterns = [
            r">\s*Place\s+Order\s*<",
            r">\s*Submit\s+Order\s*<",
            r">\s*Execute\s+Trade\s*<",
            r">\s*Connect\s+Broker\s*<",
            r">\s*Start\s+Live\s+Trading\s*<",
            r"method:\s*[\"'](?:PUT|PATCH|DELETE)[\"']",
            r"/internal/(?:orders|executions|broker)",
        ]
        offenders = [
            pattern
            for pattern in forbidden_patterns
            if re.search(pattern, combined, re.IGNORECASE)
        ]
        self.assertEqual([], offenders)


if __name__ == "__main__":
    unittest.main()
