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
    "/internal/dashboard/watchlist-summary": "get_watchlist_summary",
    "/internal/dashboard/crawl-frontier-health": "get_crawl_frontier_health",
    "/internal/dashboard/latest-equity-events": "get_latest_equity_events",
    "/internal/dashboard/latest-signal-snapshots": "get_latest_signal_snapshots",
    "/internal/dashboard/latest-advisory-run": "get_latest_advisory_run",
}


class DashboardApiTests(unittest.TestCase):
    def test_summary_endpoints_return_read_only_data_from_injected_repository(
        self,
    ) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        repository = FakeDashboardRepository()
        app = main.create_app(dashboard_repository=repository)
        client = TestClient(app)

        for endpoint, method_name in SUMMARY_ENDPOINTS.items():
            with self.subTest(endpoint=endpoint):
                response = client.get(endpoint)

                self.assertEqual(200, response.status_code)
                self.assertEqual(
                    {"data": repository.responses[method_name]}, response.json()
                )

        self.assertEqual(list(SUMMARY_ENDPOINTS.values()), repository.calls)

    def test_status_overview_and_modules_return_data_envelope(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        repository = FakeDashboardRepository()
        client = TestClient(main.create_app(dashboard_repository=repository))

        overview = client.get("/internal/status/overview")
        modules = client.get("/internal/status/modules")

        self.assertEqual(200, overview.status_code)
        self.assertEqual(
            {"data": repository.responses["get_status_overview"]}, overview.json()
        )
        self.assertEqual(200, modules.status_code)
        self.assertEqual(
            {"data": repository.responses["get_status_modules"]}, modules.json()
        )
        self.assertEqual(
            ["get_status_overview", "get_status_modules"], repository.calls
        )

    def test_dashboard_summary_endpoint_rejects_unsupported_methods(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        client = TestClient(
            main.create_app(dashboard_repository=FakeDashboardRepository())
        )
        endpoint = "/internal/dashboard/evidence-summary"

        for request in (client.post, client.put, client.patch, client.delete):
            with self.subTest(method=request.__name__):
                response = request(endpoint)

                self.assertEqual(405, response.status_code)

    def test_ticker_intelligence_endpoint_returns_read_only_ticker_payload(
        self,
    ) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        repository = FakeDashboardRepository()
        client = TestClient(main.create_app(dashboard_repository=repository))

        response = client.get("/internal/dashboard/ticker-intelligence/NVDA")

        self.assertEqual(200, response.status_code)
        self.assertEqual(
            {"data": repository.responses["get_ticker_intelligence_summary"]},
            response.json(),
        )
        self.assertEqual(
            [("get_ticker_intelligence_summary", "NVDA")], repository.ticker_calls
        )

    def test_portfolio_summary_endpoint_returns_data_envelope(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        repository = FakeDashboardRepository()
        client = TestClient(main.create_app(dashboard_repository=repository))

        response = client.get("/internal/dashboard/portfolio-summary")

        self.assertEqual(200, response.status_code)
        self.assertEqual(
            {"data": repository.responses["get_portfolio_summary"]},
            response.json(),
        )
        self.assertIn("get_portfolio_summary", repository.calls)

    def test_latest_recommendations_endpoint_passes_bounded_limit(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        repository = FakeDashboardRepository()
        client = TestClient(main.create_app(dashboard_repository=repository))

        response = client.get("/internal/dashboard/latest-recommendations?limit=5")

        self.assertEqual(200, response.status_code)
        self.assertEqual(
            {"data": repository.responses["get_latest_recommendations"]},
            response.json(),
        )
        self.assertEqual([("get_latest_recommendations", 5)], repository.limit_calls)

    def test_latest_recommendations_endpoint_caps_limit_to_50(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        repository = FakeDashboardRepository()
        client = TestClient(main.create_app(dashboard_repository=repository))

        response = client.get("/internal/dashboard/latest-recommendations?limit=9999")

        self.assertEqual(200, response.status_code)
        self.assertEqual([("get_latest_recommendations", 50)], repository.limit_calls)

    def test_latest_recommendations_endpoint_defaults_to_ten(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        repository = FakeDashboardRepository()
        client = TestClient(main.create_app(dashboard_repository=repository))

        response = client.get("/internal/dashboard/latest-recommendations")

        self.assertEqual(200, response.status_code)
        self.assertEqual([("get_latest_recommendations", 10)], repository.limit_calls)

    def test_dashboard_routes_do_not_expose_broker_order_or_execution_names(
        self,
    ) -> None:
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
        self.assertEqual(
            {"data": repository.responses["get_incident_summary"]}, response.json()
        )


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
            "get_watchlist_summary": {
                "status": "available",
                "total_members": 3,
                "by_watchlist_status": {"active": 2, "watch": 1},
                "members": [{"ticker": "NVDA", "watchlist_status": "active"}],
            },
            "get_crawl_frontier_health": {
                "status": "available",
                "latest_available_at": "2026-05-14T10:00:00+00:00",
                "datasets": [{"dataset_name": "equity_events", "source": "local"}],
            },
            "get_latest_equity_events": {
                "status": "available",
                "events": [{"evidence_id": "evidence-nvda", "tickers": ["NVDA"]}],
            },
            "get_latest_signal_snapshots": {
                "status": "available",
                "snapshots": [{"ticker": "NVDA", "technical_score": "0.61"}],
            },
            "get_latest_advisory_run": {
                "status": "available",
                "run_id": "run-local-advisory-20260514",
                "advisory_label": "advisory_only",
            },
            "get_ticker_intelligence_summary": {
                "status": "available",
                "ticker": "NVDA",
                "watchlist_status": "active",
                "latest_recommendation": {"advisory_label": "advisory_only"},
            },
            "get_portfolio_summary": {
                "status": "available",
                "advisory_label": "advisory_only",
                "snapshot_id": "snap-1",
                "as_of": "2026-05-15T12:00:00+00:00",
                "total_market_value": "1240000",
                "cash_value": "421600",
                "previous_total_market_value": "1218000",
                "day_delta_pct": 0.018,
                "positions": [
                    {
                        "ticker": "NVDA",
                        "quantity": "120",
                        "market_price": "850",
                        "market_value": "102000",
                        "portfolio_weight": "0.18",
                        "unrealized_pnl": "12000",
                    }
                ],
            },
            "get_latest_recommendations": {
                "status": "available",
                "advisory_label": "advisory_only",
                "items": [
                    {
                        "recommendation_id": "rec-nvda-1",
                        "ticker_or_portfolio": "NVDA",
                        "action": "accumulate",
                        "horizon": "1M",
                        "advisory_label": "advisory_only",
                        "evidence_count": 4,
                        "model_run_count": 2,
                        "schema_valid": True,
                        "created_at": "2026-05-15T13:00:00+00:00",
                    }
                ],
            },
        }
        self.ticker_calls: list[tuple[str, str]] = []
        self.limit_calls: list[tuple[str, int]] = []

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

    def get_watchlist_summary(self) -> dict[str, object]:
        return self._record("get_watchlist_summary")

    def get_crawl_frontier_health(self) -> dict[str, object]:
        return self._record("get_crawl_frontier_health")

    def get_latest_equity_events(self) -> dict[str, object]:
        return self._record("get_latest_equity_events")

    def get_latest_signal_snapshots(self) -> dict[str, object]:
        return self._record("get_latest_signal_snapshots")

    def get_latest_advisory_run(self) -> dict[str, object]:
        return self._record("get_latest_advisory_run")

    def get_ticker_intelligence_summary(self, ticker: str) -> dict[str, object]:
        self.ticker_calls.append(("get_ticker_intelligence_summary", ticker))
        return self.responses["get_ticker_intelligence_summary"]

    def get_portfolio_summary(self) -> dict[str, object]:
        return self._record("get_portfolio_summary")

    def get_latest_recommendations(self, limit: int = 10) -> dict[str, object]:
        self.limit_calls.append(("get_latest_recommendations", limit))
        return self.responses["get_latest_recommendations"]

    def _record(self, method_name: str) -> dict[str, object]:
        self.calls.append(method_name)
        return self.responses[method_name]
