from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
API_SRC = ROOT / "services" / "api" / "src"
for path in (CORE_SRC, API_SRC):
    sys.path.insert(0, str(path))


class AdvisoryChainApiTests(unittest.TestCase):
    def test_latest_chain_endpoint_returns_read_only_payload(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        repository = FakeAdvisoryChainRepository(
            {
                "status": "available",
                "chain_id": "latest-local-advisory",
                "advisory_label": "advisory_only",
                "ids": {
                    "evidence_id": "evidence-local-nvda",
                    "model_run_ids": ["model-run-local-deterministic-no-model"],
                    "signal_bundle_id": "signal-bundle-local-nvda",
                    "target_weights_id": "target-weights-local",
                    "recommendation_id": "recommendation-local-nvda",
                    "audit_id": "recommendation-audit-local-nvda",
                },
            }
        )
        client = TestClient(main.create_app(advisory_chain_repository=repository))

        response = client.get("/internal/advisory-chain/latest")

        self.assertEqual(200, response.status_code)
        self.assertEqual({"data": repository.payload}, response.json())
        self.assertEqual(1, repository.latest_calls)
        self.assertEqual(0, repository.demo_calls)

    def test_demo_chain_endpoint_returns_read_only_payload(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        repository = FakeAdvisoryChainRepository(
            {
                "status": "available",
                "chain_id": "demo-ai-infra-nvda",
                "advisory_label": "advisory_only",
                "ids": {
                    "evidence_id": "evidence-demo-ai-infra-nvda",
                    "model_run_ids": ["model-run-demo-local-review"],
                    "signal_bundle_id": "signal-bundle-demo-nvda",
                    "target_weights_id": "target-weights-demo-ai-infra",
                    "recommendation_id": "recommendation-demo-nvda",
                    "audit_id": "recommendation-audit-demo-nvda",
                },
            }
        )
        client = TestClient(main.create_app(advisory_chain_repository=repository))

        response = client.get("/internal/advisory-chain/demo")

        self.assertEqual(200, response.status_code)
        self.assertEqual({"data": repository.payload}, response.json())
        self.assertEqual(1, repository.demo_calls)

    def test_missing_demo_chain_returns_empty_read_only_state(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        repository = FakeAdvisoryChainRepository(
            {
                "status": "empty",
                "chain_id": "demo-ai-infra-nvda",
                "detail": "Demo advisory chain has not been seeded.",
            }
        )
        client = TestClient(main.create_app(advisory_chain_repository=repository))

        response = client.get("/internal/advisory-chain/demo")

        self.assertEqual(200, response.status_code)
        self.assertEqual("empty", response.json()["data"]["status"])

    def test_demo_chain_endpoint_rejects_mutation_methods(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        client = TestClient(main.create_app(advisory_chain_repository=FakeAdvisoryChainRepository({})))

        for path in ("/internal/advisory-chain/demo", "/internal/advisory-chain/latest"):
            for request in (client.post, client.put, client.patch, client.delete):
                with self.subTest(path=path, method=request.__name__):
                    response = request(path)

                    self.assertEqual(405, response.status_code)

    def test_advisory_chain_routes_do_not_expose_order_broker_or_execution_names(self) -> None:
        from ai_infra_fund_api import main

        app = main.create_app(advisory_chain_repository=FakeAdvisoryChainRepository({}))
        advisory_paths = [
            route.path
            for route in app.routes
            if route.path.startswith("/internal/advisory-chain/")
        ]
        offenders = [
            f"{path} contains {word}"
            for path in advisory_paths
            for word in ("order", "broker", "execution")
            if word in path.lower()
        ]

        self.assertEqual([], offenders)


class FakeAdvisoryChainRepository:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.demo_calls = 0
        self.latest_calls = 0

    def get_demo_chain(self) -> dict[str, object]:
        self.demo_calls += 1
        return self.payload

    def get_latest_chain(self) -> dict[str, object]:
        self.latest_calls += 1
        return self.payload


if __name__ == "__main__":
    unittest.main()
