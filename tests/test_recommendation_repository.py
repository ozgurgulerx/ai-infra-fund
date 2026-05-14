from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
API_SRC = ROOT / "services" / "api" / "src"
for path in (CORE_SRC, API_SRC):
    sys.path.insert(0, str(path))

from ai_infra_fund_api.repositories.recommendations import RecommendationRepository  # noqa: E402
from ai_infra_fund_core.contracts.common import AdvisoryLabel, RecommendationAction  # noqa: E402
from ai_infra_fund_core.contracts.recommendations import (  # noqa: E402
    RecommendationArtifact,
    RecommendationAudit,
)


NOW = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)

ARTIFACT_FIELDS = (
    "recommendation_id",
    "ticker_or_portfolio",
    "advisory_label",
    "action",
    "horizon",
    "score_breakdown",
    "target_weights_id",
    "evidence_ids",
    "model_run_ids",
    "signal_bundle_id",
    "risks",
    "contradictions",
    "final_payload",
    "created_at",
)

AUDIT_FIELDS = (
    "audit_id",
    "recommendation_id",
    "target_weights_id",
    "signal_bundle_id",
    "evidence_ids",
    "model_run_ids",
    "deterministic_checks",
    "reviewer_findings",
    "schema_valid",
    "created_at",
)

RETRIEVAL_COLUMNS = (
    "recommendation_id",
    "ticker_or_portfolio",
    "advisory_label",
    "action",
    "horizon",
    "score_breakdown_json",
    "target_weights_id",
    "signal_bundle_id",
    "evidence_ids",
    "model_run_ids",
    "risks_json",
    "contradictions_json",
    "final_payload_json",
    "created_at",
    "audit_id",
    "audit_recommendation_id",
    "audit_target_weights_id",
    "audit_signal_bundle_id",
    "audit_evidence_ids",
    "audit_model_run_ids",
    "deterministic_checks_json",
    "reviewer_findings_json",
    "schema_valid",
    "audit_created_at",
)


class RecommendationRepositoryTests(unittest.TestCase):
    def test_persists_recommendation_artifact_with_parameterized_insert(self) -> None:
        connection = FakeConnection()
        artifact = recommendation_artifact()

        saved = RecommendationRepository(connection).save_artifact(artifact)

        self.assertEqual(artifact, saved)
        self.assertEqual(1, connection.commit_count)
        statement, params = connection.cursor_instance.executions[0]
        self.assertIn("INSERT INTO recommendations.recommendation_artifacts", statement)
        self.assertNotIn(artifact.recommendation_id, statement)
        self.assertNotIn("Advisory-only accumulate", statement)
        self.assertNotIn("evidence-1", statement)
        self.assertEqual(artifact.recommendation_id, params[0])
        self.assertEqual(AdvisoryLabel.ADVISORY_ONLY.value, params[2])
        self.assertEqual(RecommendationAction.ACCUMULATE.value, params[3])
        self.assertEqual(artifact.target_weights_id, params[6])
        self.assertEqual(artifact.signal_bundle_id, params[7])
        self.assertEqual(["evidence-1", "evidence-2"], params[8])
        self.assertEqual(["model-run-1"], params[9])
        self.assertEqual(artifact.score_breakdown, json.loads(params[5]))
        self.assertEqual(list(artifact.risks), json.loads(params[10]))
        self.assertEqual(list(artifact.contradictions), json.loads(params[11]))
        self.assertEqual(artifact.final_payload, json.loads(params[12]))

    def test_persists_recommendation_audit_with_parameterized_insert(self) -> None:
        connection = FakeConnection()
        audit = recommendation_audit()

        saved = RecommendationRepository(connection).save_audit(audit)

        self.assertEqual(audit, saved)
        self.assertEqual(1, connection.commit_count)
        statement, params = connection.cursor_instance.executions[0]
        self.assertIn("INSERT INTO recommendations.recommendation_audits", statement)
        self.assertNotIn(audit.audit_id, statement)
        self.assertNotIn("evidence-1", statement)
        self.assertEqual(audit.audit_id, params[0])
        self.assertEqual(audit.recommendation_id, params[1])
        self.assertEqual(audit.target_weights_id, params[2])
        self.assertEqual(audit.signal_bundle_id, params[3])
        self.assertEqual(["evidence-1", "evidence-2"], params[4])
        self.assertEqual(["model-run-1"], params[5])
        self.assertEqual(audit.deterministic_checks, json.loads(params[6]))
        self.assertEqual(audit.reviewer_findings, json.loads(params[7]))
        self.assertEqual(True, params[8])

    def test_rejects_artifact_without_advisory_label_before_execute(self) -> None:
        connection = FakeConnection()
        incomplete = artifact_record(advisory_label=None)

        with self.assertRaisesRegex(ValueError, "advisory_label"):
            RecommendationRepository(connection).save_artifact(incomplete)

        self.assertEqual(0, connection.commit_count)
        self.assertEqual([], connection.cursor_instance.executions)

    def test_rejects_artifact_without_required_lineage_before_execute(self) -> None:
        invalid_records = (
            (artifact_record(evidence_ids=()), "evidence_ids must not be empty"),
            (artifact_record(model_run_ids=()), "model_run_ids must not be empty"),
            (artifact_record(signal_bundle_id=""), "signal_bundle_id is required"),
            (artifact_record(target_weights_id=""), "target_weights_id is required"),
        )

        for invalid_record, error_message in invalid_records:
            with self.subTest(error_message=error_message):
                connection = FakeConnection()
                with self.assertRaisesRegex(ValueError, error_message):
                    RecommendationRepository(connection).save_artifact(invalid_record)

                self.assertEqual(0, connection.commit_count)
                self.assertEqual([], connection.cursor_instance.executions)

    def test_retrieves_artifact_with_linked_audit_rows_as_dict(self) -> None:
        row = (
            "rec-1",
            "NVDA",
            "advisory_only",
            "accumulate",
            "6m",
            {"strategic_thesis": 0.77},
            "target-weights-1",
            "signal-bundle-1",
            ["evidence-1"],
            ["model-run-1"],
            ["valuation risk"],
            ["export controls could tighten"],
            {"summary": "Advisory-only accumulate"},
            NOW,
            "audit-1",
            "rec-1",
            "target-weights-1",
            "signal-bundle-1",
            ["evidence-1"],
            ["model-run-1"],
            {"schema_valid": True, "no_order_execution": True},
            {"reviewer": "passed"},
            True,
            NOW,
        )
        connection = FakeConnection(rows=[row], columns=RETRIEVAL_COLUMNS)

        found = RecommendationRepository(connection).get_artifact_with_audits("rec-1")

        statement, params = connection.cursor_instance.executions[0]
        self.assertIn("WHERE artifact.recommendation_id = %s", statement)
        self.assertNotIn("rec-1", statement)
        self.assertEqual(("rec-1",), params)
        self.assertEqual(
            {
                "recommendation_id": "rec-1",
                "ticker_or_portfolio": "NVDA",
                "advisory_label": "advisory_only",
                "action": "accumulate",
                "horizon": "6m",
                "score_breakdown": {"strategic_thesis": 0.77},
                "target_weights_id": "target-weights-1",
                "signal_bundle_id": "signal-bundle-1",
                "evidence_ids": ["evidence-1"],
                "model_run_ids": ["model-run-1"],
                "risks": ["valuation risk"],
                "contradictions": ["export controls could tighten"],
                "final_payload": {"summary": "Advisory-only accumulate"},
                "created_at": NOW,
                "audits": [
                    {
                        "audit_id": "audit-1",
                        "recommendation_id": "rec-1",
                        "target_weights_id": "target-weights-1",
                        "signal_bundle_id": "signal-bundle-1",
                        "evidence_ids": ["evidence-1"],
                        "model_run_ids": ["model-run-1"],
                        "deterministic_checks": {
                            "schema_valid": True,
                            "no_order_execution": True,
                        },
                        "reviewer_findings": {"reviewer": "passed"},
                        "schema_valid": True,
                        "created_at": NOW,
                    }
                ],
            },
            found,
        )


class FakeCursor:
    def __init__(self, rows: list[tuple[object, ...]], columns: tuple[str, ...]) -> None:
        self.executions: list[tuple[str, tuple[object, ...]]] = []
        self.rows = rows
        self.description = tuple((column,) for column in columns)

    def execute(self, statement: str, params: tuple[object, ...] | None = None) -> None:
        self.executions.append((statement, params or ()))

    def fetchall(self) -> list[tuple[object, ...]]:
        return self.rows

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, *_exc: object) -> None:
        return None


class FakeConnection:
    def __init__(
        self,
        *,
        rows: list[tuple[object, ...]] | None = None,
        columns: tuple[str, ...] = (),
    ) -> None:
        self.cursor_instance = FakeCursor(rows or [], columns)
        self.commit_count = 0

    def cursor(self) -> FakeCursor:
        return self.cursor_instance

    def commit(self) -> None:
        self.commit_count += 1


def recommendation_artifact(**overrides: object) -> RecommendationArtifact:
    data = {
        "recommendation_id": "rec-1",
        "ticker_or_portfolio": "NVDA",
        "advisory_label": AdvisoryLabel.ADVISORY_ONLY,
        "action": RecommendationAction.ACCUMULATE,
        "horizon": "6m",
        "score_breakdown": {"strategic_thesis": 0.77, "portfolio_risk": 0.59},
        "target_weights_id": "target-weights-1",
        "evidence_ids": ("evidence-1", "evidence-2"),
        "model_run_ids": ("model-run-1",),
        "signal_bundle_id": "signal-bundle-1",
        "risks": ("valuation risk",),
        "contradictions": ("export controls could tighten",),
        "final_payload": {"summary": "Advisory-only accumulate"},
        "created_at": NOW,
    }
    data.update(overrides)
    return RecommendationArtifact(**data)


def recommendation_audit(**overrides: object) -> RecommendationAudit:
    data = {
        "audit_id": "audit-1",
        "recommendation_id": "rec-1",
        "target_weights_id": "target-weights-1",
        "signal_bundle_id": "signal-bundle-1",
        "evidence_ids": ("evidence-1", "evidence-2"),
        "model_run_ids": ("model-run-1",),
        "deterministic_checks": {"schema_valid": True, "no_order_execution": True},
        "reviewer_findings": {"reviewer": "passed"},
        "schema_valid": True,
        "created_at": NOW,
    }
    data.update(overrides)
    return RecommendationAudit(**data)


def artifact_record(**overrides: object) -> SimpleNamespace:
    artifact = recommendation_artifact()
    data = {field: getattr(artifact, field) for field in ARTIFACT_FIELDS}
    data.update(overrides)
    return SimpleNamespace(**data)


def audit_record(**overrides: object) -> SimpleNamespace:
    audit = recommendation_audit()
    data = {field: getattr(audit, field) for field in AUDIT_FIELDS}
    data.update(overrides)
    return SimpleNamespace(**data)


if __name__ == "__main__":
    unittest.main()
