from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
API_SRC = ROOT / "services" / "api" / "src"
for path in (CORE_SRC, API_SRC):
    sys.path.insert(0, str(path))


NOW = datetime(2026, 5, 17, 9, 0, tzinfo=timezone.utc)


class ShadowAnalystReviewRepositoryTests(unittest.TestCase):
    def test_manual_acceptance_persists_review_and_updates_draft_only_after_quality_passes(self) -> None:
        from ai_infra_fund_api.repositories.shadow_analyst_reviews import (
            ShadowAnalystReviewRepository,
        )

        connection = FakeConnection(
            draft_row=_draft_row(),
            evidence_rows=(_evidence_row(),),
        )

        result = ShadowAnalystReviewRepository(connection).review_draft(
            draft_id="draft-brief-1",
            decision="accepted_for_publication",
            reviewer="ozgur",
            notes="Manual review passed.",
            reviewed_at=NOW,
        )

        self.assertEqual("accepted_for_publication", result["decision"])
        self.assertEqual("accepted_for_publication", result["draft_status"])
        self.assertGreaterEqual(result["draft_quality_score"], 85)
        self.assertEqual([], result["blocking_issues"])

        statements = [statement for statement, _params in connection.cursor_instance.executions]
        self.assertTrue(any("INSERT INTO analyst.shadow_analyst_draft_reviews" in statement for statement in statements))
        self.assertTrue(any("UPDATE analyst.shadow_analyst_drafts" in statement for statement in statements))

        insert_params = next(
            params
            for statement, params in connection.cursor_instance.executions
            if "INSERT INTO analyst.shadow_analyst_draft_reviews" in statement
        )
        accepted_payload = json.loads(insert_params[10])
        self.assertEqual("advisory_only", accepted_payload["advisory_label"])
        self.assertEqual("model-run-1", accepted_payload["source_model_run_id"])
        self.assertEqual(["evidence-capex"], accepted_payload["evidence_ids"])
        self.assertIn("quality_checks_passed", accepted_payload["readiness_checks"])
        self.assertIn("human_manual_acceptance_recorded", accepted_payload["readiness_checks"])
        self.assertNotIn("payload", accepted_payload)

    def test_manual_acceptance_is_rejected_when_quality_checks_block_publication(self) -> None:
        from ai_infra_fund_api.repositories.shadow_analyst_reviews import (
            ShadowAnalystReviewRepository,
        )

        payload = _draft_payload()
        payload["material_claims"] = [
            {
                "claim": "Quantum software revenue proves immediate margin upside.",
                "evidence_ids": ["evidence-capex"],
            }
        ]
        connection = FakeConnection(
            draft_row=_draft_row(payload_json=payload),
            evidence_rows=(_evidence_row(),),
        )

        with self.assertRaises(ValueError):
            ShadowAnalystReviewRepository(connection).review_draft(
                draft_id="draft-brief-1",
                decision="accepted_for_publication",
                reviewer="ozgur",
                reviewed_at=NOW,
            )

        statements = [statement for statement, _params in connection.cursor_instance.executions]
        self.assertFalse(any("UPDATE analyst.shadow_analyst_drafts" in statement for statement in statements))

    def test_manual_rejection_persists_review_without_publication_payload(self) -> None:
        from ai_infra_fund_api.repositories.shadow_analyst_reviews import (
            ShadowAnalystReviewRepository,
        )

        connection = FakeConnection(
            draft_row=_draft_row(),
            evidence_rows=(_evidence_row(),),
        )

        result = ShadowAnalystReviewRepository(connection).review_draft(
            draft_id="draft-brief-1",
            decision="rejected",
            reviewer="ozgur",
            notes="Too generic for publication.",
            reviewed_at=NOW,
        )

        self.assertEqual("rejected", result["decision"])
        self.assertEqual("rejected", result["draft_status"])
        insert_params = next(
            params
            for statement, params in connection.cursor_instance.executions
            if "INSERT INTO analyst.shadow_analyst_draft_reviews" in statement
        )
        accepted_payload = json.loads(insert_params[10])
        self.assertEqual({}, accepted_payload)


class FakeCursor:
    def __init__(self, draft_row: tuple[object, ...] | None, evidence_rows: tuple[tuple[object, ...], ...]) -> None:
        self.draft_row = draft_row
        self.evidence_rows = list(evidence_rows)
        self.executions: list[tuple[str, tuple[object, ...]]] = []
        self._last_statement = ""

    def execute(self, statement: str, params: tuple[object, ...] | None = None) -> None:
        self._last_statement = statement
        self.executions.append((statement, params or ()))

    def fetchone(self) -> tuple[object, ...] | None:
        if "FROM analyst.shadow_analyst_drafts" in self._last_statement:
            return self.draft_row
        return None

    def fetchall(self) -> list[tuple[object, ...]]:
        if "FROM evidence.evidence_items" in self._last_statement:
            return list(self.evidence_rows)
        if "FROM analyst.source_signals" in self._last_statement:
            return [("source-signal-capex",), ("market-event-capex",)]
        return []

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, *_exc: object) -> None:
        return None


class FakeConnection:
    def __init__(
        self,
        *,
        draft_row: tuple[object, ...] | None,
        evidence_rows: tuple[tuple[object, ...], ...],
    ) -> None:
        self.cursor_instance = FakeCursor(draft_row, evidence_rows)

    def cursor(self) -> FakeCursor:
        return self.cursor_instance


def _draft_row(
    *,
    payload_json: dict[str, object] | None = None,
) -> tuple[object, ...]:
    return (
        "draft-brief-1",
        "AnalystBriefDraft",
        "daily",
        None,
        "model-run-1",
        "review_required",
        payload_json or _draft_payload(),
        ["evidence-capex"],
        [],
        NOW,
    )


def _draft_payload() -> dict[str, object]:
    return {
        "draft_id": "draft-brief-1",
        "draft_type": "AnalystBriefDraft",
        "evidence_ids": ["evidence-capex"],
        "material_claims": [
            {
                "claim": (
                    "Hyperscaler capex supports NVDA accelerator demand, while HBM "
                    "and CoWoS bottlenecks constrain supply."
                ),
                "evidence_ids": ["evidence-capex"],
            }
        ],
        "payload": {
            "advisory_label": "advisory_only",
            "segments": ["accelerators", "hbm", "advanced_packaging"],
            "tickers": ["NVDA", "TSM"],
        },
        "model_run_id": "model-run-1",
        "review_status": "review_required",
        "headline": "AI infrastructure bottlenecks support accelerator suppliers",
        "summary": (
            "Hyperscaler capex, HBM scarcity, and CoWoS bottlenecks support NVDA "
            "and upstream suppliers while policy and valuation risk keep the setup review-required."
        ),
        "decision_rationale": (
            "The draft links evidence-capex to NVDA accelerator demand, HBM scarcity, "
            "and CoWoS packaging constraints. The setup remains advisory-only because "
            "valuation, policy risk, and customer monetization require monitoring."
        ),
        "context_used": ["evidence-capex", "source-signal-capex", "market-event-capex"],
    }


def _evidence_row() -> tuple[object, ...]:
    return (
        "evidence-capex",
        "https://example.com/capex",
        "AI capex check",
        "Example Research",
        NOW - timedelta(days=1),
        NOW,
        "a" * 64,
        "public_evidence",
        ["NVDA", "TSM"],
        ["accelerators", "hbm", "advanced_packaging"],
        (
            "Hyperscaler capex and NVDA accelerator demand remain strong, with HBM "
            "and CoWoS bottlenecks supporting suppliers."
        ),
        NOW,
    )


if __name__ == "__main__":
    unittest.main()
