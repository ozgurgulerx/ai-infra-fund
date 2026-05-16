from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
CORE_SRC = ROOT / "packages" / "core" / "src"
sys.path.insert(0, str(CORE_SRC))

from ai_infra_fund_core.contracts.common import AdvisoryLabel, DataClass  # noqa: E402
from ai_infra_fund_core.contracts.workstation import (  # noqa: E402
    AdvisoryChangeDirection,
    AdvisoryReadinessCheck,
    AdvisoryUpdate,
    AnalystBrief,
    AnalystAction,
    FinancialSnapshot,
    MacroRegimeSnapshot,
    OutcomeJournalEntry,
    OutcomeLabel,
    SourceSignal,
    TradingAdvisory,
    ValuationContext,
)


CAPTURED_AT = datetime(2026, 5, 16, 10, 0, tzinfo=timezone.utc)
AVAILABLE_AT = datetime(2026, 5, 16, 10, 2, tzinfo=timezone.utc)
AS_OF = datetime(2026, 5, 16, 10, 5, tzinfo=timezone.utc)


class AdvisoryWorkstationContractTests(unittest.TestCase):
    def test_source_signal_requires_provenance_and_public_data_class(self) -> None:
        signal = self.source_signal(tickers=("nvda", "tsm"))

        self.assertEqual(("NVDA", "TSM"), signal.tickers)
        self.assertEqual(DataClass.PUBLIC_EVIDENCE, signal.data_class)
        self.assertEqual("evidence-1", signal.evidence_id)

        invalid = [
            {"content_hash": ""},
            {"evidence_id": ""},
            {"available_at": CAPTURED_AT.replace(hour=9)},
            {"confidence": Decimal("1.01")},
        ]
        for overrides in invalid:
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValueError):
                    self.source_signal(**overrides)

    def test_financial_snapshot_requires_evidence_and_bounded_revision(self) -> None:
        snapshot = self.financial_snapshot()

        self.assertEqual("NVDA", snapshot.ticker)
        self.assertEqual(("evidence-financials",), snapshot.source_evidence_ids)

        invalid = [
            {"source_evidence_ids": ()},
            {"analyst_estimate_revision": Decimal("-1.01")},
            {"analyst_estimate_revision": Decimal("1.01")},
        ]
        for overrides in invalid:
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValueError):
                    self.financial_snapshot(**overrides)

    def test_valuation_context_requires_model_run_evidence_and_input_hash(self) -> None:
        context = self.valuation_context()

        self.assertEqual("NVDA", context.ticker)
        self.assertEqual("model-run-valuation", context.generated_by_model_run_id)
        self.assertEqual({"bear", "base", "bull"}, set(context.price_target_scenarios))

        invalid = [
            {"evidence_ids": ()},
            {"generated_by_model_run_id": ""},
            {"deterministic_inputs_hash": ""},
            {"price_target_scenarios": {}},
            {"valuation_multiples": {"execution_price": "875"}},
            {"price_target_scenarios": {"target_price": "910"}},
            {"price_target_scenarios": {"bear": "720", "base": "910", "bull": "1120", "broker": "example"}},
        ]
        for overrides in invalid:
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValueError):
                    self.valuation_context(**overrides)

    def test_macro_regime_snapshot_requires_evidence(self) -> None:
        regime = self.macro_regime()

        self.assertEqual("ai_capex_expansion", regime.ai_capex_cycle)
        self.assertEqual(("evidence-macro",), regime.evidence_ids)

        with self.assertRaises(ValueError):
            self.macro_regime(evidence_ids=())

    def test_advisory_readiness_check_requires_audit_inputs_and_bounded_confidence(self) -> None:
        readiness = self.advisory_readiness_check()

        self.assertEqual("evidence-1", readiness.evidence_ids[0])
        self.assertEqual(("model-run-advisory",), readiness.model_run_ids)
        self.assertEqual(Decimal("0.9"), readiness.confidence)

        invalid = [
            {"check_id": ""},
            {"evidence_ids": ()},
            {"model_run_ids": ()},
            {"deterministic_checks": {}},
            {"confidence": Decimal("1.01")},
            {"blocking_failures": ("missing-evidence",)},
        ]
        for overrides in invalid:
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValueError):
                    self.advisory_readiness_check(**overrides)

    def test_trading_advisory_is_advisory_only_and_audited(self) -> None:
        advisory = self.trading_advisory(analyst_action="accumulate")

        self.assertEqual(AdvisoryLabel.ADVISORY_ONLY, advisory.advisory_label)
        self.assertEqual(AnalystAction.ACCUMULATE, advisory.analyst_action)
        self.assertEqual(("evidence-1",), advisory.evidence_ids)
        self.assertEqual(("model-run-advisory",), advisory.model_run_ids)
        self.assertEqual("readiness-1", advisory.readiness_checks[0].check_id)

        invalid = [
            {"advisory_label": "not_advisory"},
            {"analyst_action": "execute"},
            {"evidence_ids": ()},
            {"model_run_ids": ()},
            {"deterministic_checks": {}},
            {"market_event_ids": ()},
            {"segment_impact_ids": ()},
            {"readiness_checks": ()},
            {"target_scenarios": {"bear": "720", "base": "910", "bull": "1120", "order": "buy"}},
        ]
        for overrides in invalid:
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValueError):
                    self.trading_advisory(**overrides)

    def test_analyst_brief_is_evidence_backed_and_advisory_only(self) -> None:
        brief = self.analyst_brief()

        self.assertEqual("NVDA", brief.ticker_or_portfolio)
        self.assertEqual(AdvisoryLabel.ADVISORY_ONLY, brief.advisory_label)
        self.assertEqual(("evidence-1",), brief.evidence_ids)
        self.assertEqual(Decimal("0.82"), brief.confidence)

        invalid = [
            {"brief_id": ""},
            {"advisory_label": "not_advisory"},
            {"key_points": ()},
            {"risk_flags": ()},
            {"evidence_ids": ()},
            {"model_run_ids": ()},
            {"confidence": Decimal("-0.01")},
            {"metadata": {"execution": "forbidden"}},
        ]
        for overrides in invalid:
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValueError):
                    self.analyst_brief(**overrides)

    def test_advisory_update_requires_prior_new_advisory_and_evidence(self) -> None:
        update = self.advisory_update()

        self.assertEqual(AdvisoryChangeDirection.STRENGTHENED, update.thesis_change_direction)
        self.assertEqual(("evidence-2",), update.evidence_ids)

        invalid = [
            {"previous_advisory_id": ""},
            {"new_advisory_id": ""},
            {"thesis_change_direction": "execute"},
            {"evidence_ids": ()},
        ]
        for overrides in invalid:
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValueError):
                    self.advisory_update(**overrides)

    def test_outcome_journal_entry_is_local_only_and_preserves_decision_evidence(self) -> None:
        entry = self.outcome_journal_entry()

        self.assertTrue(entry.local_only)
        self.assertEqual(OutcomeLabel.OPEN, entry.outcome_label)
        self.assertEqual(("evidence-1",), entry.evidence_available_ids)

        invalid = [
            {"local_only": False},
            {"evidence_available_ids": ()},
            {"market_event_ids_available_at_decision": ()},
            {"outcome_label": "routed"},
        ]
        for overrides in invalid:
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValueError):
                    self.outcome_journal_entry(**overrides)

    def source_signal(self, **overrides: object) -> SourceSignal:
        data = {
            "signal_id": "source-signal-1",
            "source_type": "company_ir",
            "source_uri": "https://example.com/nvda-ir",
            "publisher": "Example IR",
            "captured_at": CAPTURED_AT,
            "available_at": AVAILABLE_AT,
            "tickers": ("nvda",),
            "themes": ("hyperscaler_capex",),
            "segments": ("ai_hardware_accelerators",),
            "raw_summary": "Updated AI accelerator demand commentary.",
            "data_class": DataClass.PUBLIC_EVIDENCE,
            "content_hash": "hash-source-signal",
            "evidence_id": "evidence-1",
            "confidence": Decimal("0.8"),
        }
        data.update(overrides)
        return SourceSignal(**data)

    def financial_snapshot(self, **overrides: object) -> FinancialSnapshot:
        data = {
            "ticker": "nvda",
            "as_of": AS_OF,
            "revenue_growth": Decimal("0.55"),
            "gross_margin": Decimal("0.76"),
            "operating_margin": Decimal("0.62"),
            "free_cash_flow": Decimal("28000000000"),
            "capex": Decimal("3500000000"),
            "debt": Decimal("9700000000"),
            "cash": Decimal("31000000000"),
            "forward_pe": Decimal("31.2"),
            "ev_sales": Decimal("18.4"),
            "ev_ebitda": Decimal("26.5"),
            "analyst_estimate_revision": Decimal("0.08"),
            "source_evidence_ids": ("evidence-financials",),
        }
        data.update(overrides)
        return FinancialSnapshot(**data)

    def valuation_context(self, **overrides: object) -> ValuationContext:
        data = {
            "ticker": "nvda",
            "as_of": AS_OF,
            "valuation_summary": "Scenario ranges remain sensitive to accelerator demand durability.",
            "peer_group": ("AMD", "AVGO", "MRVL"),
            "valuation_multiples": {"forward_pe": "31.2", "ev_sales": "18.4"},
            "bear_case_assumptions": ("Capex digestion reduces near-term demand.",),
            "base_case_assumptions": ("AI capex remains strong into the next two quarters.",),
            "bull_case_assumptions": ("Supply remains tight while hyperscaler demand accelerates.",),
            "price_target_scenarios": {"bear": "720", "base": "910", "bull": "1120"},
            "key_sensitivities": ("gross_margin", "hbm_supply", "hyperscaler_capex"),
            "risk_flags": ("valuation_pressure",),
            "evidence_ids": ("evidence-financials", "evidence-1"),
            "generated_by_model_run_id": "model-run-valuation",
            "deterministic_inputs_hash": "hash-valuation-inputs",
        }
        data.update(overrides)
        return ValuationContext(**data)

    def macro_regime(self, **overrides: object) -> MacroRegimeSnapshot:
        data = {
            "as_of": AS_OF,
            "rates_regime": "stable_high",
            "liquidity_regime": "neutral",
            "risk_appetite": "constructive",
            "semiconductor_cycle": "upcycle",
            "ai_capex_cycle": "ai_capex_expansion",
            "credit_conditions": "normal",
            "energy_price_context": "power_constraints_visible",
            "geopolitical_risk_level": "elevated",
            "evidence_ids": ("evidence-macro",),
        }
        data.update(overrides)
        return MacroRegimeSnapshot(**data)

    def advisory_readiness_check(self, **overrides: object) -> AdvisoryReadinessCheck:
        data = {
            "check_id": "readiness-1",
            "check_name": "publication_gate",
            "passed": True,
            "checked_at": AS_OF,
            "evidence_ids": ("evidence-1",),
            "model_run_ids": ("model-run-advisory",),
            "deterministic_checks": {"risk_gate": "pass", "stale_data": "pass"},
            "blocking_failures": (),
            "confidence": Decimal("0.9"),
        }
        data.update(overrides)
        return AdvisoryReadinessCheck(**data)

    def trading_advisory(self, **overrides: object) -> TradingAdvisory:
        data = {
            "advisory_id": "advisory-nvda-1",
            "ticker_or_portfolio": "NVDA",
            "advisory_label": AdvisoryLabel.ADVISORY_ONLY,
            "analyst_action": AnalystAction.WATCH,
            "thesis_summary": "Accelerator demand remains the key positive setup.",
            "catalyst_summary": "Hyperscaler capex signal improved.",
            "valuation_context_id": "valuation-nvda-1",
            "risk_regime_ids": ("risk-regime-1",),
            "market_event_ids": ("market-event-1",),
            "segment_impact_ids": ("segment-impact-1",),
            "entry_zone": "Review only below deterministic support band.",
            "add_zone": "Review only after evidence refresh.",
            "invalidation_level": "Invalidate on capex cuts and margin compression.",
            "target_scenarios": {"bear": "720", "base": "910", "bull": "1120"},
            "time_horizon": "short_to_medium",
            "risk_flags": ("valuation_pressure",),
            "evidence_ids": ("evidence-1",),
            "model_run_ids": ("model-run-advisory",),
            "deterministic_checks": {"risk_gate": "pass", "stale_data": "pass"},
            "readiness_checks": (self.advisory_readiness_check(),),
            "created_at": AS_OF,
        }
        data.update(overrides)
        return TradingAdvisory(**data)

    def analyst_brief(self, **overrides: object) -> AnalystBrief:
        data = {
            "brief_id": "brief-nvda-1",
            "ticker_or_portfolio": "nvda",
            "advisory_label": AdvisoryLabel.ADVISORY_ONLY,
            "headline": "AI accelerator demand remains constructive.",
            "summary": "Evidence-backed brief for analyst review, not an execution instruction.",
            "key_points": ("Hyperscaler capex signal improved.",),
            "risk_flags": ("valuation_pressure",),
            "linked_advisory_id": "advisory-nvda-1",
            "linked_valuation_context_id": "valuation-nvda-1",
            "evidence_ids": ("evidence-1",),
            "model_run_ids": ("model-run-brief",),
            "metadata": {"review_stage": "draft"},
            "created_at": AS_OF,
            "confidence": Decimal("0.82"),
        }
        data.update(overrides)
        return AnalystBrief(**data)

    def advisory_update(self, **overrides: object) -> AdvisoryUpdate:
        data = {
            "update_id": "advisory-update-1",
            "previous_advisory_id": "advisory-nvda-0",
            "new_advisory_id": "advisory-nvda-1",
            "what_changed": "Hyperscaler capex evidence strengthened.",
            "thesis_change_direction": AdvisoryChangeDirection.STRENGTHENED,
            "risk_change_direction": AdvisoryChangeDirection.UNCHANGED,
            "valuation_change_direction": AdvisoryChangeDirection.UNCHANGED,
            "confidence_change": AdvisoryChangeDirection.STRENGTHENED,
            "evidence_ids": ("evidence-2",),
            "created_at": AS_OF,
        }
        data.update(overrides)
        return AdvisoryUpdate(**data)

    def outcome_journal_entry(self, **overrides: object) -> OutcomeJournalEntry:
        data = {
            "outcome_entry_id": "outcome-1",
            "trade_entry_id": "trade-entry-1",
            "ticker": "NVDA",
            "entry_type": "manual_completed_trade",
            "local_only": True,
            "linked_trade_plan_id": "trade-plan-nvda-1",
            "advisory_label_at_time": AdvisoryLabel.ADVISORY_ONLY,
            "recorded_price": Decimal("875.50"),
            "recorded_quantity": Decimal("2"),
            "recorded_at": AS_OF,
            "evidence_available_ids": ("evidence-1",),
            "market_event_ids_available_at_decision": ("market-event-1",),
            "pnl_id": "pnl-nvda-1",
            "realized_pnl": Decimal("0"),
            "unrealized_pnl": Decimal("120.25"),
            "plan_adherence_status": "followed",
            "outcome_label": OutcomeLabel.OPEN,
            "analyst_note": "Manual journal entry for outcome review.",
            "llm_review_note_id": "llm-note-1",
        }
        data.update(overrides)
        return OutcomeJournalEntry(**data)


if __name__ == "__main__":
    unittest.main()
