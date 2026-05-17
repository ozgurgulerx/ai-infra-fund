from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
CORE_SRC = ROOT / "packages" / "core" / "src"
WORKER_SRC = ROOT / "services" / "worker" / "src"
for path in (CORE_SRC, WORKER_SRC):
    sys.path.insert(0, str(path))

from ai_infra_fund_core.shadow_analyst import (  # noqa: E402
    DraftReviewStatus,
    MaterialClaimDraft,
    SegmentImpactDraft,
)


NOW = datetime(2026, 5, 17, 8, 0, tzinfo=timezone.utc)


class ShadowAnalystDraftRepositoryTests(unittest.TestCase):
    def test_save_many_persists_review_required_draft_with_lineage(self) -> None:
        from ai_infra_fund_worker.shadow_analyst_drafts import (
            ShadowAnalystDraftRepository,
        )

        connection = FakeConnection()
        draft = SegmentImpactDraft(
            draft_id="draft-segment-1",
            draft_type="SegmentImpactDraft",
            evidence_ids=("evidence-1",),
            material_claims=(
                MaterialClaimDraft(
                    claim="Accelerator demand is improving.",
                    evidence_ids=("evidence-1",),
                ),
            ),
            payload={"summary": "Review-required segment draft."},
            model_run_id="model-run-1",
            review_status=DraftReviewStatus.REVIEW_REQUIRED,
            segment_name="accelerators",
            linked_event_ids=("market-event-1",),
            first_order_tickers=("NVDA",),
            second_order_tickers=("TSM",),
        )

        saved = ShadowAnalystDraftRepository(connection).save_many(
            (draft,),
            scope="daily",
            ticker=None,
            created_at=NOW,
        )

        self.assertEqual((draft,), saved)
        self.assertEqual(0, connection.commit_count)
        statement, params = connection.cursor_instance.executions[0]
        self.assertIn("INSERT INTO analyst.shadow_analyst_drafts", statement)
        self.assertEqual("draft-segment-1", params[0])
        self.assertEqual("SegmentImpactDraft", params[1])
        self.assertEqual("daily", params[2])
        self.assertIsNone(params[3])
        self.assertEqual("model-run-1", params[4])
        self.assertEqual("review_required", params[5])
        self.assertIn("evidence-1", params[7])
        self.assertEqual([], params[8])
        payload = json.loads(params[6])
        self.assertFalse(payload["can_publish_directly"])
        self.assertEqual("Review-required segment draft.", payload["payload"]["summary"])

    def test_save_status_persists_deterministic_fallback_audit_row(self) -> None:
        from ai_infra_fund_worker.shadow_analyst_drafts import (
            ShadowAnalystDraftRepository,
        )

        connection = FakeConnection()

        ShadowAnalystDraftRepository(connection).save_status(
            draft_id="draft-fallback-1",
            draft_type="ShadowAnalystFallback",
            scope="daily",
            ticker=None,
            model_run_id="model-run-fallback",
            status="fallback",
            payload={"reason": "model client unavailable"},
            evidence_ids=("evidence-1",),
            validation_errors=("model client unavailable",),
            created_at=NOW,
        )

        statement, params = connection.cursor_instance.executions[0]
        self.assertIn("INSERT INTO analyst.shadow_analyst_drafts", statement)
        self.assertEqual("draft-fallback-1", params[0])
        self.assertEqual("ShadowAnalystFallback", params[1])
        self.assertEqual("fallback", params[5])
        self.assertEqual(["evidence-1"], params[7])
        self.assertEqual(["model client unavailable"], params[8])


class FakeCursor:
    def __init__(self) -> None:
        self.executions: list[tuple[str, tuple[object, ...]]] = []

    def execute(self, statement: str, params: tuple[object, ...] | None = None) -> None:
        self.executions.append((statement, params or ()))

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, *_exc: object) -> None:
        return None


class FakeConnection:
    def __init__(self) -> None:
        self.cursor_instance = FakeCursor()
        self.commit_count = 0

    def cursor(self) -> FakeCursor:
        return self.cursor_instance

    def commit(self) -> None:
        self.commit_count += 1


if __name__ == "__main__":
    unittest.main()
