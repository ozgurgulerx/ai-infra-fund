from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
API_SRC = ROOT / "services" / "api" / "src"
for path in (CORE_SRC, API_SRC):
    sys.path.insert(0, str(path))


SAMPLE_EVENTS = [
    {
        "event_id": "audit-evt-aaaa1111bbbb2222cccc3333",
        "kind": "recommendation_issued",
        "run_id": "run-demo-001",
        "severity": "info",
        "payload": {"ticker": "NVDA", "action": "buy"},
        "occurred_at": "2026-04-01T12:30:00+00:00",
        "created_at": "2026-04-01T12:30:01+00:00",
    },
    {
        "event_id": "audit-evt-aaaa2222bbbb3333cccc4444",
        "kind": "weights_generated",
        "run_id": "run-demo-001",
        "severity": "info",
        "payload": {"portfolio_id": "ai-infra"},
        "occurred_at": "2026-04-01T12:25:00+00:00",
        "created_at": "2026-04-01T12:25:01+00:00",
    },
]


class FakeExperimentEventsRepository:
    def __init__(self, payload: list[dict[str, object]]) -> None:
        self.payload = payload
        self.recent_calls = 0
        self.recent_kwargs: dict[str, object] | None = None
        self.for_run_calls = 0
        self.for_run_run_id: str | None = None

    def list_recent(
        self, *, limit: int = 50, since: object = None
    ) -> list[dict[str, object]]:
        self.recent_calls += 1
        self.recent_kwargs = {"limit": limit, "since": since}
        return self.payload

    def list_for_run(self, run_id: str, *, limit: int = 200) -> list[dict[str, object]]:
        self.for_run_calls += 1
        self.for_run_run_id = run_id
        return [event for event in self.payload if event["run_id"] == run_id]


class EventsApiTests(unittest.TestCase):
    def test_recent_events_endpoint_returns_payload_in_envelope(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        repository = FakeExperimentEventsRepository(list(SAMPLE_EVENTS))
        client = TestClient(main.create_app(events_repository=repository))

        response = client.get("/internal/events/recent")

        self.assertEqual(200, response.status_code)
        body = response.json()
        self.assertEqual({"data": {"events": SAMPLE_EVENTS, "count": 2}}, body)
        self.assertEqual(1, repository.recent_calls)
        assert repository.recent_kwargs is not None
        self.assertEqual(50, repository.recent_kwargs["limit"])

    def test_recent_events_endpoint_clamps_limit_within_range(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        repository = FakeExperimentEventsRepository(list(SAMPLE_EVENTS))
        client = TestClient(main.create_app(events_repository=repository))

        response = client.get("/internal/events/recent?limit=9999")

        self.assertEqual(200, response.status_code)
        assert repository.recent_kwargs is not None
        self.assertLessEqual(repository.recent_kwargs["limit"], 500)

    def test_for_run_endpoint_returns_filtered_payload(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        repository = FakeExperimentEventsRepository(list(SAMPLE_EVENTS))
        client = TestClient(main.create_app(events_repository=repository))

        response = client.get("/internal/events/by-run/run-demo-001")

        self.assertEqual(200, response.status_code)
        body = response.json()
        self.assertEqual(2, body["data"]["count"])
        self.assertEqual("run-demo-001", repository.for_run_run_id)

    def test_events_routes_reject_mutation_methods(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        repository = FakeExperimentEventsRepository(list(SAMPLE_EVENTS))
        client = TestClient(main.create_app(events_repository=repository))

        for path in (
            "/internal/events/recent",
            "/internal/events/by-run/run-demo-001",
        ):
            for request in (client.post, client.put, client.patch, client.delete):
                with self.subTest(path=path, method=request.__name__):
                    response = request(path)
                    self.assertEqual(405, response.status_code)


if __name__ == "__main__":
    unittest.main()
