from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
API_SRC = ROOT / "services" / "api" / "src"
for path in (CORE_SRC, API_SRC):
    sys.path.insert(0, str(path))


RUN_PAYLOAD = {
    "run_id": "run-20260514-daily-advisory",
    "run_type": "daily-advisory",
    "started_at": "2026-05-14T09:00:00+00:00",
    "completed_at": "2026-05-14T09:12:00+00:00",
    "inputs_hash": "a" * 64,
    "output_hash": "b" * 64,
    "artifact_uri": "postgres://audit/run_artifacts/run-20260514-daily-advisory",
    "status": "succeeded",
    "error_summary": None,
    "created_at": "2026-05-14T09:00:00+00:00",
}


class RunApiTests(unittest.TestCase):
    def test_latest_run_endpoint_returns_read_only_data_from_injected_repository(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        repository = FakeRunRepository(latest=RUN_PAYLOAD)
        client = TestClient(main.create_app(run_repository=repository))

        response = client.get("/internal/runs/latest")

        self.assertEqual(200, response.status_code)
        self.assertEqual({"data": RUN_PAYLOAD}, response.json())
        self.assertEqual(["get_latest_run"], repository.calls)

    def test_run_by_id_endpoint_returns_requested_run_from_injected_repository(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        repository = FakeRunRepository(runs={RUN_PAYLOAD["run_id"]: RUN_PAYLOAD})
        client = TestClient(main.create_app(run_repository=repository))

        response = client.get(f"/internal/runs/{RUN_PAYLOAD['run_id']}")

        self.assertEqual(200, response.status_code)
        self.assertEqual({"data": RUN_PAYLOAD}, response.json())
        self.assertEqual([("get_run", RUN_PAYLOAD["run_id"])], repository.calls)

    def test_missing_run_returns_error_envelope_without_triggering_mutation(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        repository = FakeRunRepository()
        client = TestClient(main.create_app(run_repository=repository))

        response = client.get("/internal/runs/run-missing-advisory")

        self.assertEqual(404, response.status_code)
        self.assertEqual(
            {
                "error": {
                    "code": "run_not_found",
                    "message": "run artifact was not found",
                }
            },
            response.json(),
        )
        self.assertEqual([("get_run", "run-missing-advisory")], repository.calls)

    def test_latest_missing_run_returns_error_envelope(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        repository = FakeRunRepository()
        client = TestClient(main.create_app(run_repository=repository))

        response = client.get("/internal/runs/latest")

        self.assertEqual(404, response.status_code)
        self.assertEqual(
            {
                "error": {
                    "code": "run_not_found",
                    "message": "run artifact was not found",
                }
            },
            response.json(),
        )
        self.assertEqual(["get_latest_run"], repository.calls)

    def test_run_endpoints_reject_mutation_methods(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        client = TestClient(main.create_app(run_repository=FakeRunRepository(latest=RUN_PAYLOAD)))

        for endpoint in ("/internal/runs/latest", f"/internal/runs/{RUN_PAYLOAD['run_id']}"):
            for request in (client.post, client.put, client.patch, client.delete):
                with self.subTest(endpoint=endpoint, method=request.__name__):
                    response = request(endpoint)

                    self.assertEqual(405, response.status_code)

    def test_run_routes_do_not_expose_trigger_broker_order_or_execution_names(self) -> None:
        from ai_infra_fund_api import main

        app = main.create_app(run_repository=FakeRunRepository(latest=RUN_PAYLOAD))
        run_paths = [
            route.path
            for route in app.routes
            if route.path.startswith("/internal/runs")
        ]
        forbidden = ("trigger", "broker", "order", "execution")
        offenders = [
            f"{path} contains {word}"
            for path in run_paths
            for word in forbidden
            if word in path.lower()
        ]

        self.assertEqual([], offenders)


class FakeRunRepository:
    def __init__(
        self,
        *,
        latest: dict[str, object] | None = None,
        runs: dict[str, dict[str, object]] | None = None,
    ) -> None:
        self.latest = latest
        self.runs = runs or {}
        self.calls: list[object] = []

    def get_latest_run(self) -> dict[str, object] | None:
        self.calls.append("get_latest_run")
        return self.latest

    def get_run(self, run_id: str) -> dict[str, object] | None:
        self.calls.append(("get_run", run_id))
        return self.runs.get(run_id)


if __name__ == "__main__":
    unittest.main()
