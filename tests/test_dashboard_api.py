from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
API_SRC = ROOT / "services" / "api" / "src"
for path in (CORE_SRC, API_SRC):
    sys.path.insert(0, str(path))


SUMMARY_ENDPOINTS = {
    "/internal/dashboard/evidence-summary": "get_evidence_summary",
    "/internal/dashboard/recommendation-summary": "get_recommendation_summary",
    "/internal/dashboard/evaluation-summary": "get_evaluation_summary",
    "/internal/dashboard/model-run-summary": "get_model_run_summary",
    "/internal/dashboard/data-quality-summary": "get_data_quality_summary",
    "/internal/dashboard/incident-summary": "get_incident_summary",
}


class DashboardApiTests(unittest.TestCase):
    def test_summary_endpoints_return_read_only_data_from_injected_repository(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        repository = FakeDashboardRepository()
        app = main.create_app(dashboard_repository=repository)
        client = TestClient(app)

        for endpoint, method_name in SUMMARY_ENDPOINTS.items():
            with self.subTest(endpoint=endpoint):
                response = client.get(endpoint)

                self.assertEqual(200, response.status_code)
                self.assertEqual({"data": repository.responses[method_name]}, response.json())

        self.assertEqual(list(SUMMARY_ENDPOINTS.values()), repository.calls)

    def test_status_overview_and_modules_return_data_envelope(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        repository = FakeDashboardRepository()
        client = TestClient(main.create_app(dashboard_repository=repository))

        overview = client.get("/internal/status/overview")
        modules = client.get("/internal/status/modules")

        self.assertEqual(200, overview.status_code)
        self.assertEqual({"data": repository.responses["get_status_overview"]}, overview.json())
        self.assertEqual(200, modules.status_code)
        self.assertEqual({"data": repository.responses["get_status_modules"]}, modules.json())
        self.assertEqual(["get_status_overview", "get_status_modules"], repository.calls)

    def test_dashboard_summary_endpoint_rejects_unsupported_methods(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        client = TestClient(main.create_app(dashboard_repository=FakeDashboardRepository()))
        endpoint = "/internal/dashboard/evidence-summary"

        for request in (client.post, client.put, client.patch, client.delete):
            with self.subTest(method=request.__name__):
                response = request(endpoint)

                self.assertEqual(405, response.status_code)

    def test_dashboard_routes_do_not_expose_broker_order_or_execution_names(self) -> None:
        from ai_infra_fund_api import main

        app = main.create_app(dashboard_repository=FakeDashboardRepository())
        dashboard_paths = [
            route.path
            for route in app.routes
            if route.path.startswith("/internal/dashboard/")
            or route.path.startswith("/internal/status/")
        ]
        forbidden = ("broker", "order", "execution")
        offenders = [
            f"{path} contains {word}"
            for path in dashboard_paths
            for word in forbidden
            if word in path.lower()
        ]

        self.assertEqual([], offenders)

    def test_create_app_accepts_optional_dashboard_repository_injection(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        repository = FakeDashboardRepository()
        app = main.create_app(dashboard_repository=repository)

        response = TestClient(app).get("/internal/dashboard/incident-summary")

        self.assertEqual(200, response.status_code)
        self.assertEqual({"data": repository.responses["get_incident_summary"]}, response.json())


class FakeDashboardRepository:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.responses: dict[str, dict[str, object]] = {
            "get_status_overview": {
                "generated_at": "2026-05-14T10:00:00+00:00",
                "system_status": "nominal",
                "open_incidents": 0,
            },
            "get_status_modules": {
                "modules": [
                    {"name": "evidence", "status": "ready"},
                    {"name": "recommendations", "status": "ready"},
                ],
            },
            "get_evidence_summary": {
                "total_items": 12,
                "items_by_source_type": {"manual_report": 7, "manual_note": 5},
            },
            "get_recommendation_summary": {
                "total_recommendations": 4,
                "latest_recommendation_id": "recommendation-20260514-nvda",
            },
            "get_evaluation_summary": {
                "total_backtests": 3,
                "latest_backtest_run_id": "evaluation-20260514-nvda",
            },
            "get_model_run_summary": {
                "total_runs": 6,
                "latest_model_run_id": "model-run-20260514-narrative",
            },
            "get_data_quality_summary": {
                "freshness_status": "current",
                "stale_dataset_count": 0,
            },
            "get_incident_summary": {
                "open_incidents": 0,
                "latest_incident_id": None,
            },
        }

    def get_status_overview(self) -> dict[str, object]:
        return self._record("get_status_overview")

    def get_status_modules(self) -> dict[str, object]:
        return self._record("get_status_modules")

    def get_evidence_summary(self) -> dict[str, object]:
        return self._record("get_evidence_summary")

    def get_recommendation_summary(self) -> dict[str, object]:
        return self._record("get_recommendation_summary")

    def get_evaluation_summary(self) -> dict[str, object]:
        return self._record("get_evaluation_summary")

    def get_model_run_summary(self) -> dict[str, object]:
        return self._record("get_model_run_summary")

    def get_data_quality_summary(self) -> dict[str, object]:
        return self._record("get_data_quality_summary")

    def get_incident_summary(self) -> dict[str, object]:
        return self._record("get_incident_summary")

    def _record(self, method_name: str) -> dict[str, object]:
        self.calls.append(method_name)
        return self.responses[method_name]
