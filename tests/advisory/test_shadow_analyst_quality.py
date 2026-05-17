from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
CORE_SRC = ROOT / "packages" / "core" / "src"
sys.path.insert(0, str(CORE_SRC))

from ai_infra_fund_core.shadow_analyst import (  # noqa: E402
    AnalystBriefDraft,
    DraftReviewStatus,
    MaterialClaimDraft,
)
from ai_infra_fund_core.shadow_analyst.quality import (  # noqa: E402
    DraftEvidenceReference,
    DraftQualityContext,
    DraftQualityRecommendation,
    build_sanitized_publication_payload,
    evaluate_shadow_analyst_draft,
)


NOW = datetime(2026, 5, 17, 9, 0, tzinfo=timezone.utc)


class ShadowAnalystDraftQualityTests(unittest.TestCase):
    def test_high_quality_evidence_backed_draft_is_eligible_for_human_review(self) -> None:
        evaluation = evaluate_shadow_analyst_draft(
            _high_quality_brief(),
            _quality_context(),
        )

        self.assertGreaterEqual(evaluation.draft_quality_score, 85)
        self.assertEqual(
            DraftQualityRecommendation.ELIGIBLE_FOR_HUMAN_REVIEW,
            evaluation.recommendation,
        )
        self.assertEqual((), evaluation.blocking_issues)
        self.assertTrue(evaluation.evaluator_findings)

    def test_generic_but_valid_draft_stays_review_required(self) -> None:
        draft = _high_quality_brief(
            summary="Conditions are mixed and should be monitored.",
            decision_rationale=(
                "The situation is uncertain. More confirmation is needed before "
                "changing analyst posture."
            ),
            material_claims=(
                MaterialClaimDraft(
                    claim="Conditions are mixed and should be monitored.",
                    evidence_ids=("evidence-capex",),
                ),
            ),
            headline="Mixed conditions require monitoring",
        )

        evaluation = evaluate_shadow_analyst_draft(draft, _quality_context())

        self.assertEqual(
            DraftQualityRecommendation.KEEP_REVIEW_REQUIRED,
            evaluation.recommendation,
        )
        self.assertEqual((), evaluation.blocking_issues)
        self.assertTrue(
            any("specific" in warning.lower() for warning in evaluation.non_blocking_warnings)
        )

    def test_missing_evidence_blocks_promotion(self) -> None:
        draft = _high_quality_brief(evidence_ids=("evidence-missing",))

        evaluation = evaluate_shadow_analyst_draft(draft, _quality_context())

        self.assertEqual(DraftQualityRecommendation.REJECT, evaluation.recommendation)
        self.assertTrue(
            any("unknown evidence" in issue.lower() for issue in evaluation.blocking_issues)
        )

    def test_unsupported_claim_blocks_promotion(self) -> None:
        draft = _high_quality_brief(
            material_claims=(
                MaterialClaimDraft(
                    claim="Quantum revenue acceleration proves immediate software margin upside.",
                    evidence_ids=("evidence-capex",),
                ),
            )
        )

        evaluation = evaluate_shadow_analyst_draft(draft, _quality_context())

        self.assertEqual(DraftQualityRecommendation.REJECT, evaluation.recommendation)
        self.assertTrue(
            any("unsupported" in issue.lower() for issue in evaluation.blocking_issues)
        )

    def test_forbidden_execution_language_blocks_promotion(self) -> None:
        draft = _high_quality_brief(
            decision_rationale=(
                "The evidence supports entering the setup. Submit order instructions "
                "should be prepared for NVDA after the brief."
            )
        )

        evaluation = evaluate_shadow_analyst_draft(draft, _quality_context())

        self.assertEqual(DraftQualityRecommendation.REJECT, evaluation.recommendation)
        self.assertTrue(
            any("execution" in issue.lower() for issue in evaluation.blocking_issues)
        )

    def test_hallucinated_ticker_or_context_id_blocks_promotion(self) -> None:
        draft = _high_quality_brief(
            payload={"focus": "NVDA and XYZ drive the setup."},
            context_used=("evidence-capex", "source-signal-unknown"),
        )

        evaluation = evaluate_shadow_analyst_draft(draft, _quality_context())

        self.assertEqual(DraftQualityRecommendation.REJECT, evaluation.recommendation)
        self.assertTrue(
            any("unknown context" in issue.lower() for issue in evaluation.blocking_issues)
        )
        self.assertTrue(
            any("unknown ticker" in issue.lower() for issue in evaluation.blocking_issues)
        )

    def test_stale_evidence_blocks_otherwise_strong_draft(self) -> None:
        context = _quality_context(
            evidence=(
                DraftEvidenceReference(
                    evidence_id="evidence-capex",
                    text=(
                        "Hyperscaler capex and NVDA accelerator demand remain strong, "
                        "with HBM and CoWoS bottlenecks supporting suppliers."
                    ),
                    available_at=NOW - timedelta(days=90),
                    source_uri="https://example.com/capex",
                ),
            )
        )

        evaluation = evaluate_shadow_analyst_draft(_high_quality_brief(), context)

        self.assertEqual(DraftQualityRecommendation.REJECT, evaluation.recommendation)
        self.assertTrue(
            any("stale" in issue.lower() for issue in evaluation.blocking_issues)
        )

    def test_sanitized_publication_payload_contains_required_audit_fields_without_raw_payload_copy(self) -> None:
        draft = _high_quality_brief()
        evaluation = evaluate_shadow_analyst_draft(draft, _quality_context())

        payload = build_sanitized_publication_payload(
            draft,
            evaluation,
            reviewer="human-reviewer",
            accepted_at=NOW,
        )

        self.assertEqual("advisory_only", payload["advisory_label"])
        self.assertEqual("model-run-1", payload["source_model_run_id"])
        self.assertEqual(["evidence-capex"], payload["evidence_ids"])
        self.assertIn("quality_checks_passed", payload["readiness_checks"])
        self.assertIn("human_manual_acceptance_recorded", payload["readiness_checks"])
        self.assertNotIn("payload", payload)
        self.assertEqual("human-reviewer", payload["accepted_by"])


def _quality_context(
    *,
    evidence: tuple[DraftEvidenceReference, ...] | None = None,
) -> DraftQualityContext:
    return DraftQualityContext(
        evidence=evidence
        or (
            DraftEvidenceReference(
                evidence_id="evidence-capex",
                text=(
                    "Hyperscaler capex and NVDA accelerator demand remain strong, "
                    "with HBM and CoWoS bottlenecks supporting suppliers."
                ),
                available_at=NOW - timedelta(days=1),
                source_uri="https://example.com/capex",
            ),
        ),
        known_tickers=("NVDA", "AMD", "TSM", "ASML", "MU", "MSFT", "META"),
        known_segments=("accelerators", "hbm", "advanced_packaging", "hyperscaler_capex"),
        known_object_ids=("source-signal-capex", "market-event-capex"),
        as_of=NOW,
        max_evidence_age_days=30,
    )


def _high_quality_brief(**overrides: object) -> AnalystBriefDraft:
    data = {
        "draft_id": "draft-brief-1",
        "draft_type": "AnalystBriefDraft",
        "evidence_ids": ("evidence-capex",),
        "material_claims": (
            MaterialClaimDraft(
                claim=(
                    "Hyperscaler capex supports NVDA accelerator demand, while HBM "
                    "and CoWoS bottlenecks constrain supply."
                ),
                evidence_ids=("evidence-capex",),
            ),
        ),
        "payload": {
            "advisory_label": "advisory_only",
            "segments": ["accelerators", "hbm", "advanced_packaging"],
            "tickers": ["NVDA", "TSM"],
        },
        "model_run_id": "model-run-1",
        "review_status": DraftReviewStatus.REVIEW_REQUIRED,
        "headline": "AI infrastructure bottlenecks support accelerator suppliers",
        "summary": (
            "Hyperscaler capex, HBM scarcity, and CoWoS bottlenecks support NVDA "
            "and upstream suppliers while policy and valuation risk keep the setup "
            "review-required."
        ),
        "decision_rationale": (
            "The draft links evidence-capex to NVDA accelerator demand, HBM scarcity, "
            "and CoWoS packaging constraints. The setup remains advisory-only because "
            "valuation, policy risk, and customer monetization require continued "
            "monitoring before any manual analyst action."
        ),
        "context_used": ("evidence-capex", "source-signal-capex", "market-event-capex"),
    }
    data.update(overrides)
    return AnalystBriefDraft(**data)


if __name__ == "__main__":
    unittest.main()
