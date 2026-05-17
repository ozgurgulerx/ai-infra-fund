from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
API_SRC = ROOT / "services" / "api" / "src"
sys.path.insert(0, str(API_SRC))


class ShadowAnalystReviewApiTests(unittest.TestCase):
    def test_manual_review_endpoint_records_accepted_publication_decision(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        service = FakeShadowAnalystReviewService()
        client = TestClient(main.create_app(shadow_analyst_review_service=service))

        response = client.post(
            "/internal/shadow-analyst/drafts/draft-brief-1/review",
            json={
                "decision": "accepted_for_publication",
                "reviewer": "ozgur",
                "notes": "Manual review passed.",
            },
        )

        self.assertEqual(200, response.status_code)
        payload = response.json()["data"]
        self.assertEqual("accepted_for_publication", payload["decision"])
        self.assertEqual("advisory_only", payload["accepted_payload"]["advisory_label"])
        self.assertEqual("model-run-1", payload["accepted_payload"]["source_model_run_id"])
        self.assertEqual(["evidence-capex"], payload["accepted_payload"]["evidence_ids"])
        self.assertEqual(
            [
                {
                    "draft_id": "draft-brief-1",
                    "decision": "accepted_for_publication",
                    "reviewer": "ozgur",
                    "notes": "Manual review passed.",
                }
            ],
            service.calls,
        )

    def test_manual_review_endpoint_rejects_invalid_acceptance(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        service = FakeShadowAnalystReviewService()
        service.raise_value_error = True
        client = TestClient(main.create_app(shadow_analyst_review_service=service))

        response = client.post(
            "/internal/shadow-analyst/drafts/draft-brief-1/review",
            json={
                "decision": "accepted_for_publication",
                "reviewer": "ozgur",
            },
        )

        self.assertEqual(422, response.status_code)
        self.assertEqual("shadow_draft_review_rejected", response.json()["error"]["code"])

    def test_manual_review_endpoint_validates_payload(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        client = TestClient(main.create_app(shadow_analyst_review_service=FakeShadowAnalystReviewService()))

        response = client.post(
            "/internal/shadow-analyst/drafts/draft-brief-1/review",
            json={"decision": "accepted_for_publication"},
        )

        self.assertEqual(422, response.status_code)
        self.assertEqual("invalid_shadow_draft_review", response.json()["error"]["code"])

    def test_shadow_review_route_has_no_execution_surface(self) -> None:
        from ai_infra_fund_api import main

        app = main.create_app(shadow_analyst_review_service=FakeShadowAnalystReviewService())
        paths = sorted(
            route.path for route in app.routes if route.path.startswith("/internal/shadow-analyst")
        )
        offenders = [
            f"{path} contains {word}"
            for path in paths
            for word in ("broker", "order", "execution", "execute")
            if word in path.lower()
        ]

        self.assertEqual(["/internal/shadow-analyst/drafts/{draft_id}/review"], paths)
        self.assertEqual([], offenders)


class FakeShadowAnalystReviewService:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []
        self.raise_value_error = False

    def review_draft(
        self,
        *,
        draft_id: str,
        decision: str,
        reviewer: str,
        notes: str | None = None,
    ) -> dict[str, object]:
        self.calls.append(
            {
                "draft_id": draft_id,
                "decision": decision,
                "reviewer": reviewer,
                "notes": notes,
            }
        )
        if self.raise_value_error:
            raise ValueError("quality checks did not pass")
        return {
            "review_id": "review-1",
            "draft_id": draft_id,
            "decision": decision,
            "draft_status": decision,
            "draft_quality_score": 91,
            "blocking_issues": [],
            "non_blocking_warnings": [],
            "accepted_payload": {
                "advisory_label": "advisory_only",
                "source_model_run_id": "model-run-1",
                "evidence_ids": ["evidence-capex"],
                "readiness_checks": ["quality_checks_passed"],
            },
        }


if __name__ == "__main__":
    unittest.main()
