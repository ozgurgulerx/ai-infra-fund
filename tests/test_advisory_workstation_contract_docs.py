from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
OBJECT_MODEL_PATH = ROOT / "docs" / "ANALYST_OBJECT_MODEL.md"
DATA_CONTRACTS_PATH = ROOT / "docs" / "specs" / "0003-data-contracts.md"

ADVISORY_WORKSTATION_OBJECTS = {
    "SourceSignal": [
        "signal_id",
        "source_type",
        "source_uri",
        "publisher",
        "captured_at",
        "available_at",
        "tickers",
        "themes",
        "segments",
        "raw_summary",
        "data_class",
        "content_hash",
        "evidence_id",
        "confidence",
    ],
    "FinancialSnapshot": [
        "ticker",
        "as_of",
        "revenue_growth",
        "gross_margin",
        "operating_margin",
        "free_cash_flow",
        "capex",
        "debt",
        "cash",
        "forward_pe",
        "ev_sales",
        "ev_ebitda",
        "analyst_estimate_revision",
        "source_evidence_ids",
    ],
    "ValuationContext": [
        "ticker",
        "as_of",
        "valuation_summary",
        "peer_group",
        "valuation_multiples",
        "bear_case_assumptions",
        "base_case_assumptions",
        "bull_case_assumptions",
        "price_target_scenarios",
        "key_sensitivities",
        "risk_flags",
        "evidence_ids",
        "generated_by_model_run_id",
        "deterministic_inputs_hash",
    ],
    "MacroRegimeSnapshot": [
        "as_of",
        "rates_regime",
        "liquidity_regime",
        "risk_appetite",
        "semiconductor_cycle",
        "ai_capex_cycle",
        "credit_conditions",
        "energy_price_context",
        "geopolitical_risk_level",
        "evidence_ids",
    ],
    "SegmentImpact": [
        "segment_id",
        "segment_name",
        "linked_event_ids",
        "primary_tickers",
        "first_order_tickers",
        "second_order_tickers",
        "impact_direction",
        "impact_summary",
        "confidence",
        "time_horizon",
        "risk_flags",
        "invalidation_condition",
        "latest_evidence_at",
        "source_evidence_ids",
    ],
    "EquityImpactAssessment": [
        "assessment_id",
        "ticker",
        "company",
        "linked_event_ids",
        "segment_ids",
        "assessment",
        "bull_case",
        "base_case",
        "bear_case",
        "risk_flags",
        "invalidation_condition",
        "watch_items",
        "advisory_implication",
        "confidence",
        "as_of",
        "source_evidence_ids",
        "model_run_ids",
    ],
    "RiskRegimeUpdate": [
        "regime_id",
        "risk_type",
        "status",
        "severity",
        "confidence",
        "linked_event_ids",
        "affected_segments",
        "affected_tickers",
        "summary",
        "portfolio_monitoring_note",
        "relief_condition",
        "invalidation_condition",
        "as_of",
        "available_at",
        "source_evidence_ids",
    ],
    "TradingAdvisory": [
        "advisory_id",
        "ticker_or_portfolio",
        "advisory_label",
        "analyst_action",
        "thesis_summary",
        "catalyst_summary",
        "valuation_context_id",
        "risk_regime_ids",
        "market_event_ids",
        "segment_impact_ids",
        "entry_zone",
        "add_zone",
        "invalidation_level",
        "target_scenarios",
        "time_horizon",
        "risk_flags",
        "evidence_ids",
        "model_run_ids",
        "deterministic_checks",
        "created_at",
    ],
    "TradePlan": [
        "trade_plan_id",
        "ticker",
        "company",
        "status",
        "advisory_action",
        "linked_event_ids",
        "linked_signal_bundle_id",
        "linked_recommendation_artifact_id",
        "entry_exit_levels_id",
        "price_target_scenario_id",
        "target_weights_id",
        "deterministic_check_ids",
        "readiness",
        "blocking_reasons",
        "manual_journal_only",
        "last_reviewed_at",
    ],
    "PortfolioExposureSnapshot": [
        "snapshot_id",
        "as_of",
        "currency",
        "source",
        "advisory_label",
        "total_market_value",
        "cash_placeholder",
        "gross_equity_exposure",
        "position_count",
        "positions",
        "correlation_exposure_ids",
        "pnl_summary_id",
        "target_weights_id",
        "concentration_flags",
        "stale_price_flags",
    ],
    "AnalystBrief": [
        "brief_id",
        "as_of",
        "generated_at",
        "title",
        "advisory_label",
        "executive_summary",
        "highest_conviction_theme_updates",
        "ticker_focus_list",
        "open_questions",
        "next_review_triggers",
        "market_event_ids",
        "segment_impact_ids",
        "risk_regime_update_ids",
        "suggested_action_ids",
        "model_run_ids",
        "freshness_status",
    ],
    "AdvisoryUpdate": [
        "update_id",
        "previous_advisory_id",
        "new_advisory_id",
        "what_changed",
        "thesis_change_direction",
        "risk_change_direction",
        "valuation_change_direction",
        "confidence_change",
        "evidence_ids",
        "created_at",
    ],
    "OutcomeJournalEntry": [
        "outcome_entry_id",
        "trade_entry_id",
        "ticker",
        "entry_type",
        "local_only",
        "linked_trade_plan_id",
        "advisory_label_at_time",
        "recorded_price",
        "recorded_quantity",
        "recorded_at",
        "evidence_available_ids",
        "market_event_ids_available_at_decision",
        "pnl_id",
        "realized_pnl",
        "unrealized_pnl",
        "plan_adherence_status",
        "outcome_label",
        "analyst_note",
        "llm_review_note_id",
    ],
    "LLMAnalystNote": [
        "note_id",
        "model_run_id",
        "scope",
        "allowed_role",
        "reviewed_object_ids",
        "evidence_ids",
        "note",
        "deterministic_fields_not_modified",
        "created_at",
        "review_status",
    ],
}

REQUIRED_RULE_PHRASES = [
    "all advisory outputs are advisory-only",
    "every material claim links to evidence_ids",
    "Price targets are scenarios, not predictions",
    "Entry, add, trim, exit, and invalidation levels are planning guidance, not orders",
    "Deterministic code owns PnL, exposure, risk-limit checks, and accounting",
    "LLMs may generate narrative, thesis interpretation, risk critique, and valuation scenario explanation",
]

FORBIDDEN_OBJECT_FIELD_NAMES = {
    "broker",
    "route",
    "exchange",
    "order_id",
    "execution_id",
    "auto_trade",
}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def section(text: str, heading: str) -> str:
    match = re.search(rf"^## {re.escape(heading)}\n(?P<body>.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL)
    if match is None:
        return ""
    return match.group("body")


def field_names_from_section(body: str) -> set[str]:
    fields_match = re.search(r"### Fields\n(?P<body>.*?)(?=^### |\Z)", body, re.MULTILINE | re.DOTALL)
    fields_body = fields_match.group("body") if fields_match else body
    names: set[str] = set()
    for line in fields_body.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- `"):
            continue
        name = stripped.removeprefix("- `").split("`", 1)[0]
        names.add(name)
    return names


class AdvisoryWorkstationContractDocTests(unittest.TestCase):
    def test_object_model_defines_advisory_workstation_objects_and_fields(self) -> None:
        text = read(OBJECT_MODEL_PATH)
        missing: dict[str, list[str]] = {}

        for object_name, fields in ADVISORY_WORKSTATION_OBJECTS.items():
            body = section(text, object_name)
            self.assertTrue(body, object_name)
            names = field_names_from_section(body)
            missing_fields = [field for field in fields if field not in names]
            if missing_fields:
                missing[object_name] = missing_fields

        self.assertEqual({}, missing)

    def test_data_contract_spec_lists_advisory_workstation_objects_and_fields(self) -> None:
        text = read(DATA_CONTRACTS_PATH)
        for object_name, fields in ADVISORY_WORKSTATION_OBJECTS.items():
            self.assertIn(f"- `{object_name}`", text)
            body = section(text, object_name)
            self.assertTrue(body, object_name)
            names = field_names_from_section(body)
            self.assertEqual([], [field for field in fields if field not in names], object_name)

    def test_advisory_contract_rules_keep_reporting_boundary(self) -> None:
        combined = f"{read(OBJECT_MODEL_PATH)}\n{read(DATA_CONTRACTS_PATH)}"
        for phrase in REQUIRED_RULE_PHRASES:
            self.assertIn(phrase, combined)
        for forbidden in FORBIDDEN_OBJECT_FIELD_NAMES:
            self.assertIn(forbidden, combined)

    def test_new_object_field_lists_do_not_include_execution_fields(self) -> None:
        for path in (OBJECT_MODEL_PATH, DATA_CONTRACTS_PATH):
            text = read(path)
            for object_name in ADVISORY_WORKSTATION_OBJECTS:
                body = section(text, object_name)
                names = field_names_from_section(body)
                self.assertFalse(names & FORBIDDEN_OBJECT_FIELD_NAMES, f"{path.name} {object_name}")


if __name__ == "__main__":
    unittest.main()
