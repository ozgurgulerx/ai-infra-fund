from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
CORE_SRC = ROOT / "packages" / "core" / "src"
sys.path.insert(0, str(CORE_SRC))

from ai_infra_fund_core.contracts.common import DataClass, ModelRunStatus  # noqa: E402
from ai_infra_fund_core.model_routing.profiles import load_model_profiles  # noqa: E402
from ai_infra_fund_core.model_routing.router import ModelRouter  # noqa: E402
from ai_infra_fund_core.shadow_analyst import (  # noqa: E402
    AnalystContextScope,
    DraftReviewStatus,
    GovernedShadowAnalystPipeline,
    build_daily_analyst_context_bundle,
    build_ticker_analyst_context_bundle,
)


NOW = datetime(2026, 5, 16, 9, 30, tzinfo=timezone.utc)
CONFIG_PATH = ROOT / "config" / "model_profiles.yaml"


class ShadowAnalystPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.router = ModelRouter(load_model_profiles(CONFIG_PATH))

    def test_daily_context_bundle_collects_live_analyst_inputs_and_data_classes(self) -> None:
        bundle = build_daily_analyst_context_bundle(_sample_context_rows(), as_of=NOW)

        self.assertEqual(AnalystContextScope.DAILY_BRIEF, bundle.scope)
        self.assertIsNone(bundle.ticker)
        self.assertIn("evidence-nvda-capex", bundle.evidence_ids)
        self.assertIn("source-signal-nvda-capex", bundle.object_ids)
        self.assertIn("market-event-nvda-capex", bundle.object_ids)
        self.assertIn(DataClass.PUBLIC_EVIDENCE, bundle.data_classes)
        self.assertIn(DataClass.DERIVED_ANALYTICS, bundle.data_classes)
        self.assertIn(DataClass.USER_PORTFOLIO, bundle.data_classes)
        self.assertEqual(64, len(bundle.content_hash))

    def test_ticker_context_bundle_filters_to_requested_ticker_and_linked_evidence(self) -> None:
        bundle = build_ticker_analyst_context_bundle(_sample_context_rows(), ticker="NVDA", as_of=NOW)

        self.assertEqual(AnalystContextScope.TICKER, bundle.scope)
        self.assertEqual("NVDA", bundle.ticker)
        self.assertEqual(("evidence-nvda-capex",), bundle.evidence_ids)
        self.assertIn("market-event-nvda-capex", bundle.object_ids)
        self.assertNotIn("market-event-msft-capex", bundle.object_ids)
        self.assertEqual(1, len(bundle.rows["market_events"]))

    def test_stub_model_client_creates_review_required_drafts_and_model_run(self) -> None:
        bundle = build_daily_analyst_context_bundle(_sample_context_rows(), as_of=NOW)
        client = StubAnalystModelClient(_valid_shadow_response())
        recorder = RecordingModelRunRecorder()
        draft_recorder = RecordingDraftRecorder()

        result = GovernedShadowAnalystPipeline(
            router=self.router,
            model_client=client,
            model_run_recorder=recorder,
            draft_recorder=draft_recorder,
            now=lambda: NOW,
        ).run(bundle)

        self.assertEqual("review_required", result.status)
        self.assertFalse(result.fallback_used)
        self.assertEqual(1, len(client.calls))
        self.assertEqual(1, len(recorder.records))
        self.assertEqual(ModelRunStatus.SUCCESS, recorder.records[0].status)
        self.assertTrue(recorder.records[0].schema_valid)
        self.assertEqual(6, len(result.drafts))
        self.assertEqual(result.drafts, tuple(draft_recorder.records))
        self.assertEqual(
            {
                "SegmentImpactDraft",
                "EquityImpactAssessmentDraft",
                "ValuationContextDraft",
                "RiskRegimeUpdateDraft",
                "TradingAdvisoryDraft",
                "AnalystBriefDraft",
            },
            {draft.draft_type for draft in result.drafts},
        )
        for draft in result.drafts:
            with self.subTest(draft=draft.draft_type):
                self.assertEqual(DraftReviewStatus.REVIEW_REQUIRED, draft.review_status)
                self.assertFalse(draft.can_publish_directly)
                self.assertEqual(recorder.records[0].model_run_id, draft.model_run_id)
                self.assertIn("evidence-nvda-capex", draft.evidence_ids)
        analyst_brief = next(draft for draft in result.drafts if draft.draft_type == "AnalystBriefDraft")
        self.assertEqual("NVDA", analyst_brief.ticker_implications[0].ticker)
        self.assertEqual("watch", analyst_brief.ticker_implications[0].advisory_stance)
        self.assertIn("Capex evidence", analyst_brief.supported_claim)

    def test_private_research_bundle_is_denied_and_audited_without_model_call(self) -> None:
        rows = _sample_context_rows()
        rows["evidence_items"] = (
            {
                "evidence_id": "evidence-private-report",
                "data_class": "private_research",
                "content_hash": "p" * 64,
                "summary": "Private thesis notes.",
            },
        )
        rows["source_signals"] = (
            {
                "signal_id": "source-signal-private",
                "evidence_id": "evidence-private-report",
                "data_class": "private_research",
                "tickers": ("NVDA",),
                "themes": ("accelerator demand",),
                "segments": ("accelerators",),
            },
        )
        rows["market_events"] = (
            {
                "event_id": "market-event-private",
                "source_evidence_ids": ("evidence-private-report",),
                "tickers": ("NVDA",),
                "themes": ("accelerator demand",),
            },
        )
        bundle = build_daily_analyst_context_bundle(rows, as_of=NOW)
        client = StubAnalystModelClient(_valid_shadow_response())
        recorder = RecordingModelRunRecorder()

        result = GovernedShadowAnalystPipeline(
            router=self.router,
            model_client=client,
            model_run_recorder=recorder,
            now=lambda: NOW,
        ).run(bundle)

        self.assertEqual("denied", result.status)
        self.assertTrue(result.fallback_used)
        self.assertEqual([], client.calls)
        self.assertEqual(1, len(recorder.records))
        self.assertEqual(ModelRunStatus.DENIED, recorder.records[0].status)
        self.assertIn("private_research", recorder.records[0].error_summary or "")

    def test_invalid_output_is_rejected_and_model_run_records_schema_failure(self) -> None:
        bundle = build_daily_analyst_context_bundle(_sample_context_rows(), as_of=NOW)
        invalid = _valid_shadow_response()
        invalid["trading_advisories"][0]["material_claims"] = (
            {"claim": "Increase target weights immediately.", "evidence_ids": ()},
        )
        invalid["trading_advisories"][0]["payload"]["target_weights"] = {"NVDA": 0.4}
        client = StubAnalystModelClient(invalid)
        recorder = RecordingModelRunRecorder()
        draft_recorder = RecordingDraftRecorder()

        result = GovernedShadowAnalystPipeline(
            router=self.router,
            model_client=client,
            model_run_recorder=recorder,
            draft_recorder=draft_recorder,
            now=lambda: NOW,
        ).run(bundle)

        self.assertEqual("rejected", result.status)
        self.assertFalse(result.fallback_used)
        self.assertEqual(1, len(recorder.records))
        self.assertEqual(ModelRunStatus.FAILURE, recorder.records[0].status)
        self.assertFalse(recorder.records[0].schema_valid)
        self.assertTrue(result.rejection_reasons)
        self.assertTrue(result.drafts)
        self.assertTrue(any(draft.review_status is DraftReviewStatus.REJECTED for draft in result.drafts))
        self.assertEqual(result.drafts, tuple(draft_recorder.records))
        self.assertTrue(any(draft.review_status is DraftReviewStatus.REJECTED for draft in draft_recorder.records))

    def test_llm_unavailable_records_failure_and_uses_deterministic_fallback(self) -> None:
        bundle = build_daily_analyst_context_bundle(_sample_context_rows(), as_of=NOW)
        client = StubAnalystModelClient(RuntimeError("stub outage"))
        recorder = RecordingModelRunRecorder()

        result = GovernedShadowAnalystPipeline(
            router=self.router,
            model_client=client,
            model_run_recorder=recorder,
            now=lambda: NOW,
        ).run(bundle)

        self.assertEqual("fallback", result.status)
        self.assertTrue(result.fallback_used)
        self.assertEqual(1, len(recorder.records))
        self.assertEqual(ModelRunStatus.FAILURE, recorder.records[0].status)
        self.assertIn("stub outage", recorder.records[0].error_summary or "")
        self.assertEqual((), result.drafts)


class StubAnalystModelClient:
    def __init__(self, response_or_error: object) -> None:
        self.response_or_error = response_or_error
        self.calls: list[dict[str, object]] = []

    def generate_structured(self, *, route: object, bundle: object, output_schema: str) -> dict[str, object]:
        self.calls.append({"route": route, "bundle": bundle, "output_schema": output_schema})
        if isinstance(self.response_or_error, BaseException):
            raise self.response_or_error
        return self.response_or_error  # type: ignore[return-value]


class RecordingModelRunRecorder:
    def __init__(self) -> None:
        self.records = []

    def save(self, run: object) -> object:
        self.records.append(run)
        return run


class RecordingDraftRecorder:
    def __init__(self) -> None:
        self.records = []

    def save_many(self, drafts: object) -> object:
        self.records.extend(drafts)
        return drafts


def _sample_context_rows() -> dict[str, tuple[dict[str, object], ...]]:
    return {
        "source_signals": (
            {
                "signal_id": "source-signal-nvda-capex",
                "evidence_id": "evidence-nvda-capex",
                "data_class": "public_evidence",
                "tickers": ("NVDA",),
                "themes": ("accelerator demand",),
                "segments": ("accelerators",),
            },
            {
                "signal_id": "source-signal-msft-capex",
                "evidence_id": "evidence-msft-capex",
                "data_class": "public_evidence",
                "tickers": ("MSFT",),
                "themes": ("hyperscaler capex",),
                "segments": ("hyperscalers",),
            },
        ),
        "evidence_items": (
            {
                "evidence_id": "evidence-nvda-capex",
                "data_class": "public_evidence",
                "content_hash": "a" * 64,
                "summary": "Hyperscaler capex implies accelerator demand.",
            },
            {
                "evidence_id": "evidence-msft-capex",
                "data_class": "public_evidence",
                "content_hash": "b" * 64,
                "summary": "Azure capex remains elevated.",
            },
        ),
        "market_events": (
            {
                "event_id": "market-event-nvda-capex",
                "source_evidence_ids": ("evidence-nvda-capex",),
                "tickers": ("NVDA",),
                "themes": ("accelerator demand",),
                "extracted_by_model_run_id": "model-run-event-nvda",
            },
            {
                "event_id": "market-event-msft-capex",
                "source_evidence_ids": ("evidence-msft-capex",),
                "tickers": ("MSFT",),
                "themes": ("hyperscaler capex",),
            },
        ),
        "segment_impacts": (
            {
                "segment_impact_id": "segment-impact-gpu",
                "linked_event_ids": ("market-event-nvda-capex",),
                "source_evidence_ids": ("evidence-nvda-capex",),
                "primary_tickers": ("NVDA",),
                "first_order_tickers": ("NVDA",),
                "second_order_tickers": ("TSM", "AVGO"),
                "data_class": "derived_analytics",
            },
        ),
        "equity_impact_assessments": (
            {
                "assessment_id": "assessment-nvda",
                "ticker": "NVDA",
                "linked_event_ids": ("market-event-nvda-capex",),
                "source_evidence_ids": ("evidence-nvda-capex",),
                "model_run_ids": ("model-run-assessment-nvda",),
                "data_class": "derived_analytics",
            },
        ),
        "valuation_contexts": (
            {
                "valuation_context_id": "valuation-nvda",
                "ticker": "NVDA",
                "evidence_ids": ("evidence-nvda-capex",),
                "data_class": "derived_analytics",
            },
        ),
        "risk_regime_updates": (
            {
                "regime_id": "risk-export-controls",
                "affected_tickers": ("NVDA",),
                "source_evidence_ids": ("evidence-nvda-capex",),
                "data_class": "derived_analytics",
            },
        ),
        "portfolio_exposures": (
            {
                "snapshot_id": "portfolio-latest",
                "positions": ({"ticker": "NVDA", "portfolio_weight": "0.25"},),
                "data_class": "user_portfolio",
            },
        ),
        "prior_advisories": (
            {
                "advisory_id": "advisory-nvda-prior",
                "ticker_or_portfolio": "NVDA",
                "evidence_ids": ("evidence-nvda-capex",),
                "model_run_ids": ("model-run-prior",),
                "data_class": "derived_analytics",
            },
        ),
        "outcome_journal_entries": (
            {
                "outcome_entry_id": "outcome-nvda",
                "ticker": "NVDA",
                "evidence_available_ids": ("evidence-nvda-capex",),
                "data_class": "user_portfolio",
            },
        ),
    }


def _valid_shadow_response() -> dict[str, object]:
    claim = {
        "claim": "Hyperscaler capex supports incremental accelerator demand.",
        "evidence_ids": ("evidence-nvda-capex",),
    }
    common = {
        "evidence_ids": ("evidence-nvda-capex",),
        "material_claims": (claim,),
        "payload": {"summary": "Review-required analyst draft."},
    }
    return {
        "segment_impacts": (
            {
                **common,
                "segment_name": "accelerators",
                "linked_event_ids": ("market-event-nvda-capex",),
                "first_order_tickers": ("NVDA",),
                "second_order_tickers": ("TSM", "AVGO"),
            },
        ),
        "equity_impact_assessments": (
            {
                **common,
                "ticker": "NVDA",
                "assessment": "Positive catalyst, valuation sensitivity remains high.",
                "bull_case": "Demand pull-through persists.",
                "bear_case": "Export controls or digestion pressure cap upside.",
                "risk_flags": ("valuation", "export_controls"),
                "invalidation_condition": "Capex revisions roll over.",
            },
        ),
        "valuation_contexts": (
            {
                **common,
                "ticker": "NVDA",
                "valuation_summary": "Premium multiple requires durable accelerator growth.",
            },
        ),
        "risk_regime_updates": (
            {
                **common,
                "risk_type": "export_controls",
                "affected_tickers": ("NVDA",),
                "summary": "Export policy risk remains an overlay.",
            },
        ),
        "trading_advisories": (
            {
                **common,
                "ticker": "NVDA",
                "analyst_action": "watch",
                "rationale": "Catalyst is constructive but needs deterministic gate checks.",
                "context_used": ("evidence-nvda-capex", "market-event-nvda-capex"),
                "market_event_ids": ("market-event-nvda-capex",),
            },
        ),
        "analyst_briefs": (
            {
                **common,
                "headline": "AI capex signal keeps accelerator demand in focus.",
                "summary": "NVDA remains linked to hyperscaler capex evidence.",
                "decision_rationale": "The advisory-only brief links capex evidence to review-required accelerator exposure.",
                "context_used": ("evidence-nvda-capex", "market-event-nvda-capex"),
                "ticker_implications": (
                    {
                        "ticker": "NVDA",
                        "theme_or_segment": "accelerators",
                        "direction": "positive",
                        "confidence_delta": "higher confidence from public capex evidence",
                        "time_horizon": "short-to-medium",
                        "what_changed": "NVDA remains linked to hyperscaler capex.",
                        "why_it_matters": "NVDA accelerator demand is supported by capex evidence.",
                        "risk_flags": ("valuation risk",),
                        "invalidation_signal": "Capex revisions roll over.",
                        "evidence_ids": ("evidence-nvda-capex",),
                        "advisory_stance": "watch",
                    },
                ),
                "supported_claim": "Capex evidence supports NVDA accelerator demand.",
                "weak_inference": "Supplier revenue timing still needs monitoring.",
                "monitor_only_hypothesis": "If capex rolls over, keep this monitor-only.",
            },
        ),
    }


if __name__ == "__main__":
    unittest.main()
