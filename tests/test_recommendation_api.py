from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
API_SRC = ROOT / "services" / "api" / "src"
for path in (CORE_SRC, API_SRC):
    sys.path.insert(0, str(path))


VALID_CREATE_REQUEST = {
    "ticker_or_portfolio": "NVDA",
    "horizon": "medium_term",
    "target_weights_id": "target-weights-20260514-nvda",
    "signal_bundle_id": "signal-bundle-20260514-nvda",
    "evidence_ids": ["evidence-20260514-nvda-demand"],
    "model_run_ids": ["model-run-20260514-narrative"],
    "run_id": "run-20260514-daily",
    "requested_by": "phase-6-worker-c",
}


class RecommendationApiTests(unittest.TestCase):
    def test_creates_recommendation_from_deterministic_references_only(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        service = FakeRecommendationService()
        app = main.create_app(recommendation_service=service)

        response = TestClient(app).post("/internal/recommendations", json=VALID_CREATE_REQUEST)

        self.assertEqual(201, response.status_code)
        payload = response.json()["data"]
        artifact = payload["artifact"]
        audit_links = payload["audit_links"]

        self.assertEqual("recommendation-20260514-nvda", artifact["recommendation_id"])
        self.assertEqual("advisory_only", artifact["advisory_label"])
        self.assertEqual("target-weights-20260514-nvda", artifact["target_weights_id"])
        self.assertEqual(["evidence-20260514-nvda-demand"], artifact["evidence_ids"])
        self.assertEqual(["model-run-20260514-narrative"], artifact["model_run_ids"])
        self.assertEqual("recommendation-audit-20260514-nvda", audit_links["audit_id"])
        self.assertEqual("signal-bundle-20260514-nvda", audit_links["signal_bundle_id"])

        self.assertEqual(1, len(service.create_requests))
        create_request = service.create_requests[0]
        self.assertEqual("target-weights-20260514-nvda", create_request.target_weights_id)
        self.assertEqual("signal-bundle-20260514-nvda", create_request.signal_bundle_id)
        self.assertEqual(("evidence-20260514-nvda-demand",), create_request.evidence_ids)
        self.assertEqual(("model-run-20260514-narrative",), create_request.model_run_ids)

    def test_rejects_raw_weights_scores_and_unknown_generation_fields(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        invalid_payloads = [
            {**VALID_CREATE_REQUEST, "target_weights": {"NVDA": "0.42"}},
            {**VALID_CREATE_REQUEST, "score_breakdown": {"strategic_thesis_score": "0.82"}},
            {**VALID_CREATE_REQUEST, "scores": {"NVDA": "0.91"}},
            {**VALID_CREATE_REQUEST, "action": "accumulate"},
        ]

        for payload in invalid_payloads:
            with self.subTest(field=set(payload) - set(VALID_CREATE_REQUEST)):
                service = FakeRecommendationService()
                app = main.create_app(recommendation_service=service)

                response = TestClient(app).post("/internal/recommendations", json=payload)

                self.assertEqual(422, response.status_code)
                self.assertEqual("invalid_recommendation_request", response.json()["error"]["code"])
                self.assertEqual([], service.create_requests)

    def test_rejects_non_deterministic_or_incomplete_reference_ids(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        invalid_payloads = [
            {**VALID_CREATE_REQUEST, "target_weights_id": "llm-output-weights"},
            {**VALID_CREATE_REQUEST, "signal_bundle_id": "signal bundle 1"},
            {**VALID_CREATE_REQUEST, "evidence_ids": []},
            {**VALID_CREATE_REQUEST, "model_run_ids": ["model-output"]},
        ]

        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                service = FakeRecommendationService()
                app = main.create_app(recommendation_service=service)

                response = TestClient(app).post("/internal/recommendations", json=payload)

                self.assertEqual(422, response.status_code)
                self.assertEqual("invalid_recommendation_request", response.json()["error"]["code"])
                self.assertEqual([], service.create_requests)

    def test_retrieves_recommendation_artifact_with_audit_links(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        service = FakeRecommendationService()
        service.records["recommendation-20260514-nvda"] = recommendation_record()
        app = main.create_app(recommendation_service=service)

        response = TestClient(app).get("/internal/recommendations/recommendation-20260514-nvda")

        self.assertEqual(200, response.status_code)
        payload = response.json()["data"]

        self.assertEqual("recommendation-20260514-nvda", payload["artifact"]["recommendation_id"])
        self.assertEqual("advisory_only", payload["artifact"]["advisory_label"])
        self.assertEqual(
            {
                "audit_id": "recommendation-audit-20260514-nvda",
                "recommendation_id": "recommendation-20260514-nvda",
                "target_weights_id": "target-weights-20260514-nvda",
                "signal_bundle_id": "signal-bundle-20260514-nvda",
                "evidence_ids": ["evidence-20260514-nvda-demand"],
                "model_run_ids": ["model-run-20260514-narrative"],
            },
            payload["audit_links"],
        )
        self.assertEqual("recommendation-audit-20260514-nvda", payload["audit"]["audit_id"])

    def test_missing_recommendation_returns_error_envelope(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        app = main.create_app(recommendation_service=FakeRecommendationService())

        response = TestClient(app).get("/internal/recommendations/recommendation-20260514-missing")

        self.assertEqual(404, response.status_code)
        self.assertEqual("recommendation_not_found", response.json()["error"]["code"])

    def test_recommendation_api_has_no_model_or_broker_execution_surface(self) -> None:
        forbidden = [
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
            "execute_order",
        ]
        paths = [
            API_SRC / "ai_infra_fund_api" / "routes" / "recommendations.py",
            API_SRC / "ai_infra_fund_api" / "main.py",
        ]

        offenders: list[str] = []
        for path in paths:
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            for pattern in forbidden:
                if pattern in text:
                    offenders.append(f"{path.relative_to(ROOT)} contains {pattern}")

        self.assertEqual([], offenders)


class FakeRecommendationService:
    def __init__(self) -> None:
        self.create_requests: list[object] = []
        self.records: dict[str, dict[str, object]] = {}

    def create_recommendation(self, request: object) -> dict[str, object]:
        self.create_requests.append(request)
        record = recommendation_record()
        self.records["recommendation-20260514-nvda"] = record
        return record

    def get_recommendation(self, recommendation_id: str) -> dict[str, object] | None:
        return self.records.get(recommendation_id)


def recommendation_record() -> dict[str, object]:
    artifact = {
        "recommendation_id": "recommendation-20260514-nvda",
        "ticker_or_portfolio": "NVDA",
        "advisory_label": "advisory_only",
        "action": "accumulate",
        "horizon": "medium_term",
        "score_breakdown": {"strategic_thesis_score": "0.82"},
        "target_weights_id": "target-weights-20260514-nvda",
        "evidence_ids": ("evidence-20260514-nvda-demand",),
        "model_run_ids": ("model-run-20260514-narrative",),
        "signal_bundle_id": "signal-bundle-20260514-nvda",
        "risks": ("valuation",),
        "contradictions": ("supply normalization",),
        "final_payload": {"summary": "Accumulate advisory-only."},
        "created_at": "2026-05-14T09:00:00+00:00",
    }
    audit = {
        "audit_id": "recommendation-audit-20260514-nvda",
        "recommendation_id": "recommendation-20260514-nvda",
        "target_weights_id": "target-weights-20260514-nvda",
        "signal_bundle_id": "signal-bundle-20260514-nvda",
        "evidence_ids": ("evidence-20260514-nvda-demand",),
        "model_run_ids": ("model-run-20260514-narrative",),
        "deterministic_checks": {"constraints_passed": True},
        "reviewer_findings": {"contradictions": 1},
        "schema_valid": True,
        "created_at": "2026-05-14T09:00:01+00:00",
    }
    return {"artifact": artifact, "audit": audit}


if __name__ == "__main__":
    unittest.main()
