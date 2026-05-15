from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
API_SRC = ROOT / "services" / "api" / "src"
for path in (CORE_SRC, API_SRC):
    sys.path.insert(0, str(path))


NOW = datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc)


DRIFT_PAYLOAD = {
    "as_of": NOW.isoformat(),
    "rows": [
        {
            "ticker": "NVDA",
            "current_weight": "0.60",
            "target_weight": "0.50",
            "drift": "-0.10",
        },
        {
            "ticker": "MSFT",
            "current_weight": "0.00",
            "target_weight": "0.30",
            "drift": "0.30",
        },
    ],
    "advisory_label": "advisory_only",
}


SIMULATION_PAYLOAD = {
    "as_of": NOW.isoformat(),
    "curve": [
        {"date": NOW.isoformat(), "shadow_value": "1.0", "benchmark_value": "1.0"},
    ],
    "metrics": {"shadow_return": "0.04"},
    "advisory_label": "advisory_only",
}


class FakeShadowPortfolioService:
    def __init__(self) -> None:
        self.drift_calls = 0
        self.simulation_calls = 0
        self.last_as_of: datetime | None = None
        self.last_horizon: int | None = None
        self.raise_lookahead = False

    def get_drift(self, *, as_of: datetime) -> dict[str, object]:
        from ai_infra_fund_core.portfolio.shadow_simulation import LookaheadError

        self.drift_calls += 1
        self.last_as_of = as_of
        if self.raise_lookahead:
            raise LookaheadError("price availability exceeds as_of")
        return DRIFT_PAYLOAD

    def get_simulation(
        self, *, as_of: datetime, horizon_days: int
    ) -> dict[str, object]:
        from ai_infra_fund_core.portfolio.shadow_simulation import LookaheadError

        self.simulation_calls += 1
        self.last_as_of = as_of
        self.last_horizon = horizon_days
        if self.raise_lookahead:
            raise LookaheadError("price availability exceeds as_of")
        return SIMULATION_PAYLOAD


class ShadowPortfolioApiTests(unittest.TestCase):
    def test_drift_endpoint_returns_envelope_with_advisory_label(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        service = FakeShadowPortfolioService()
        client = TestClient(
            main.create_app(shadow_portfolio_service=service),
        )

        response = client.get("/internal/shadow-portfolio/drift")

        self.assertEqual(200, response.status_code)
        body = response.json()
        self.assertEqual(DRIFT_PAYLOAD, body["data"])
        self.assertEqual(1, service.drift_calls)

    def test_drift_endpoint_returns_422_when_lookahead_violated(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        service = FakeShadowPortfolioService()
        service.raise_lookahead = True
        client = TestClient(
            main.create_app(shadow_portfolio_service=service),
        )

        response = client.get("/internal/shadow-portfolio/drift")

        self.assertEqual(422, response.status_code)
        self.assertEqual("LOOKAHEAD_VIOLATION", response.json()["error"]["code"])

    def test_simulation_endpoint_accepts_horizon(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        service = FakeShadowPortfolioService()
        client = TestClient(
            main.create_app(shadow_portfolio_service=service),
        )

        response = client.get("/internal/shadow-portfolio/simulation?horizon_days=14")

        self.assertEqual(200, response.status_code)
        body = response.json()
        self.assertIn("curve", body["data"])
        self.assertEqual(14, service.last_horizon)

    def test_shadow_portfolio_routes_reject_mutation_methods(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        service = FakeShadowPortfolioService()
        client = TestClient(
            main.create_app(shadow_portfolio_service=service),
        )

        for path in (
            "/internal/shadow-portfolio/drift",
            "/internal/shadow-portfolio/simulation",
        ):
            for request in (client.post, client.put, client.patch, client.delete):
                with self.subTest(path=path, method=request.__name__):
                    response = request(path)
                    self.assertEqual(405, response.status_code)


if __name__ == "__main__":
    unittest.main()
