from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
sys.path.insert(0, str(CORE_SRC))

from ai_infra_fund_core.contracts.common import AdvisoryLabel, RecommendationAction  # noqa: E402
from ai_infra_fund_core.contracts.evidence import EvidenceClaim  # noqa: E402
from ai_infra_fund_core.contracts.recommendations import (  # noqa: E402
    RecommendationArtifact,
    RecommendationAudit,
)
from ai_infra_fund_core.contracts.signals import SignalBundle, TargetWeights  # noqa: E402
from ai_infra_fund_core.recommendations import (  # noqa: E402
    RecommendationPolicyContext,
    build_recommendation,
)


NOW = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)
LATER = datetime(2026, 5, 14, 12, 5, tzinfo=timezone.utc)


class RecommendationBuilderTests(unittest.TestCase):
    def test_builds_advisory_artifact_and_audit_from_deterministic_inputs(self) -> None:
        result = build_recommendation(
            signal_bundle=signal(),
            target_weights=target_weights(),
            evidence_claims=(claim(),),
            model_run_ids=("model-run-summary", "model-run-review"),
            created_at=NOW,
        )

        self.assertTrue(result.should_publish)
        self.assertEqual((), result.suppression_reasons)
        self.assertIsInstance(result.artifact, RecommendationArtifact)
        self.assertIsInstance(result.audit, RecommendationAudit)
        self.assertEqual(AdvisoryLabel.ADVISORY_ONLY, result.artifact.advisory_label)
        self.assertEqual(RecommendationAction.ACCUMULATE, result.artifact.action)
        self.assertEqual(("evidence-1",), result.artifact.evidence_ids)
        self.assertEqual(("model-run-summary", "model-run-review"), result.artifact.model_run_ids)
        self.assertEqual("signal-bundle-1", result.artifact.signal_bundle_id)
        self.assertEqual("target-weights-1", result.artifact.target_weights_id)
        self.assertEqual("published", result.artifact.final_payload["publication_status"])
        self.assertEqual("deterministic_placeholder_with_audited_model_runs", result.artifact.final_payload["narrative_source"])
        self.assertTrue(result.audit.deterministic_checks["target_weights_validated"])
        self.assertTrue(result.audit.deterministic_checks["evidence_covers_signal"])
        self.assertEqual({"status": "deterministic_placeholder", "model_run_ids": ("model-run-summary", "model-run-review")}, result.audit.reviewer_findings)

    def test_suppresses_publication_for_stale_quarantined_or_frozen_inputs(self) -> None:
        result = build_recommendation(
            signal_bundle=signal(),
            target_weights=target_weights(),
            evidence_claims=(claim(),),
            model_run_ids=("model-run-summary",),
            created_at=NOW,
            policy_context=RecommendationPolicyContext(
                stale_evidence_ids=("evidence-1",),
                quarantined_evidence_ids=("evidence-2",),
                incident_freeze_active=True,
            ),
        )

        self.assertFalse(result.should_publish)
        self.assertEqual(
            ("stale_evidence", "quarantined_evidence", "incident_freeze_active"),
            result.suppression_reasons,
        )
        self.assertEqual("suppressed", result.artifact.final_payload["publication_status"])
        self.assertFalse(result.audit.schema_valid)
        self.assertEqual(("evidence-1",), result.audit.deterministic_checks["stale_evidence_ids"])
        self.assertEqual(("evidence-2",), result.audit.deterministic_checks["quarantined_evidence_ids"])

    def test_suppresses_publication_for_missing_relevant_evidence(self) -> None:
        result = build_recommendation(
            signal_bundle=signal(ticker="NVDA"),
            target_weights=target_weights(),
            evidence_claims=(claim(evidence_id="evidence-msft", ticker_or_theme="MSFT"),),
            model_run_ids=("model-run-summary",),
            created_at=NOW,
        )

        self.assertFalse(result.should_publish)
        self.assertEqual(("missing_evidence",), result.suppression_reasons)
        self.assertFalse(result.audit.deterministic_checks["evidence_covers_signal"])

    def test_rejects_missing_required_audit_link_ids(self) -> None:
        with self.assertRaisesRegex(ValueError, "evidence_claims must not be empty"):
            build_recommendation(
                signal_bundle=signal(),
                target_weights=target_weights(),
                evidence_claims=(),
                model_run_ids=("model-run-summary",),
                created_at=NOW,
            )

        with self.assertRaisesRegex(ValueError, "model_run_ids must not be empty"):
            build_recommendation(
                signal_bundle=signal(),
                target_weights=target_weights(),
                evidence_claims=(claim(),),
                model_run_ids=(),
                created_at=NOW,
            )

        with self.assertRaisesRegex(ValueError, "signal_bundle_id is required"):
            build_recommendation(
                signal_bundle={**signal_record(), "signal_bundle_id": ""},
                target_weights=target_weights(),
                evidence_claims=(claim(),),
                model_run_ids=("model-run-summary",),
                created_at=NOW,
            )

        with self.assertRaisesRegex(ValueError, "target_weights_id is required"):
            build_recommendation(
                signal_bundle=signal(),
                target_weights={**target_weights_record(), "target_weights_id": ""},
                evidence_claims=(claim(),),
                model_run_ids=("model-run-summary",),
                created_at=NOW,
            )

    def test_rejects_raw_llm_or_model_output_target_weights(self) -> None:
        with self.assertRaisesRegex(ValueError, "TargetWeights must be generated by deterministic portfolio code"):
            build_recommendation(
                signal_bundle=signal(),
                target_weights={**target_weights_record(), "generated_by": "model_output"},
                evidence_claims=(claim(),),
                model_run_ids=("model-run-summary",),
                created_at=NOW,
            )

        with self.assertRaisesRegex(ValueError, "persisted TargetWeights record"):
            build_recommendation(
                signal_bundle=signal(),
                target_weights={"NVDA": Decimal("0.40")},
                evidence_claims=(claim(),),
                model_run_ids=("model-run-summary",),
                created_at=NOW,
            )

    def test_suppresses_publication_for_invalid_target_weights_or_validation_failure(self) -> None:
        invalid_weights = {**target_weights_record(), "validation_status": "failed"}

        result = build_recommendation(
            signal_bundle=signal(),
            target_weights=invalid_weights,
            evidence_claims=(claim(),),
            model_run_ids=("model-run-summary",),
            created_at=NOW,
        )

        self.assertFalse(result.should_publish)
        self.assertEqual(("invalid_target_weights",), result.suppression_reasons)
        self.assertFalse(result.audit.deterministic_checks["target_weights_validated"])
        self.assertFalse(result.audit.schema_valid)

        unlinked_target = {**target_weights_record(), "source_signal_bundle_ids": ("other-signal-bundle",)}
        unlinked_result = build_recommendation(
            signal_bundle=signal(),
            target_weights=unlinked_target,
            evidence_claims=(claim(),),
            model_run_ids=("model-run-summary",),
            created_at=NOW,
        )

        self.assertFalse(unlinked_result.should_publish)
        self.assertEqual(("deterministic_validation_failed",), unlinked_result.suppression_reasons)
        self.assertFalse(unlinked_result.audit.deterministic_checks["source_signal_bundle_linked"])

        negative_weight_result = build_recommendation(
            signal_bundle=signal(),
            target_weights={
                **target_weights_record(),
                "cash_weight": Decimal("0.40"),
                "weights": {"NVDA": Decimal("-0.10"), "MSFT": Decimal("0.70")},
            },
            evidence_claims=(claim(),),
            model_run_ids=("model-run-summary",),
            created_at=NOW,
        )

        self.assertFalse(negative_weight_result.should_publish)
        self.assertEqual(("invalid_target_weights",), negative_weight_result.suppression_reasons)
        self.assertFalse(negative_weight_result.audit.deterministic_checks["target_weights_unit_bounds_valid"])

    def test_recommendation_modules_do_not_import_model_clients_or_execution_surface(self) -> None:
        forbidden = (
            "from azure",
            "import azure",
            "from openai",
            "import openai",
            "from anthropic",
            "import anthropic",
            "place_order",
            "submit_order",
            "broker_client",
            "live_order",
            "order_execution",
            "model_routing",
        )
        offenders: list[str] = []
        package_root = CORE_SRC / "ai_infra_fund_core" / "recommendations"
        for path in package_root.glob("*.py"):
            text = path.read_text(encoding="utf-8")
            for pattern in forbidden:
                if pattern in text:
                    offenders.append(f"{path.relative_to(ROOT)} contains {pattern}")

        self.assertEqual([], offenders)


def signal(**overrides: object) -> SignalBundle:
    data = signal_record()
    data.update(overrides)
    return SignalBundle(**data)


def signal_record() -> dict[str, object]:
    return {
        "signal_bundle_id": "signal-bundle-1",
        "ticker": "NVDA",
        "as_of": NOW,
        "strategic_thesis_score": Decimal("0.80"),
        "tactical_technical_score": Decimal("0.60"),
        "forward_indicator_score": Decimal("0.50"),
        "portfolio_risk_score": Decimal("0.30"),
        "formula_versions": {"test": "v1"},
        "input_snapshot_hash": "a" * 64,
        "created_at": NOW,
    }


def target_weights(**overrides: object) -> TargetWeights:
    data = target_weights_record()
    data.update(overrides)
    return TargetWeights(**data)


def target_weights_record() -> dict[str, object]:
    return {
        "target_weights_id": "target-weights-1",
        "as_of": NOW,
        "portfolio_id": "portfolio-1",
        "cash_weight": Decimal("0.40"),
        "weights": {"NVDA": Decimal("0.40"), "MSFT": Decimal("0.20")},
        "constraints": {"cash_floor": "0.10", "formula_version": "v1"},
        "source_signal_bundle_ids": ("signal-bundle-1",),
        "generated_by": "deterministic_portfolio_engine.v1",
        "validation_status": "validated",
        "created_at": NOW,
    }


def claim(**overrides: object) -> EvidenceClaim:
    data = {
        "claim_id": "claim-1",
        "evidence_id": "evidence-1",
        "chunk_id": "chunk-1",
        "ticker_or_theme": "NVDA",
        "claim_type": "supply_constraint",
        "direction": "positive",
        "magnitude": Decimal("0.40"),
        "time_horizon": "12m",
        "confidence": Decimal("0.80"),
        "quote_or_span_ref": "p1:l2-l5",
        "extracted_by_model_run_id": "model-run-summary",
        "validated_at": LATER,
        "created_at": NOW,
    }
    data.update(overrides)
    return EvidenceClaim(**data)


if __name__ == "__main__":
    unittest.main()
