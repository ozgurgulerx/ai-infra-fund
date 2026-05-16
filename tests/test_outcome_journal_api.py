from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
API_SRC = ROOT / "services" / "api" / "src"
for path in (CORE_SRC, API_SRC):
    sys.path.insert(0, str(path))


class OutcomeJournalApiTests(unittest.TestCase):
    def test_latest_outcome_journal_returns_empty_response(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        client = TestClient(
            main.create_app(outcome_journal_repository=FakeOutcomeJournalRepository([]))
        )

        response = client.get("/internal/outcome-journal/latest")

        self.assertEqual(200, response.status_code)
        self.assertEqual(
            {
                "status": "empty",
                "advisory_label": "advisory_only",
                "total_entries": 0,
                "items": [],
            },
            response.json()["data"],
        )

    def test_latest_outcome_journal_returns_available_response(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        client = TestClient(
            main.create_app(
                outcome_journal_repository=FakeOutcomeJournalRepository(
                    [
                        {
                            "outcome_id": "outcome-1",
                            "manual_journal_entry_id": "manual-trade-1",
                            "advisory_id": "advisory-1",
                            "market_event_ids": ["market-event-1"],
                            "evidence_ids": ["evidence-1"],
                            "net_pnl_amount": "120.50",
                        }
                    ]
                )
            )
        )

        response = client.get("/internal/outcome-journal/latest")

        self.assertEqual(200, response.status_code)
        payload = response.json()["data"]
        self.assertEqual("available", payload["status"])
        self.assertEqual("advisory_only", payload["advisory_label"])
        self.assertEqual(1, payload["total_entries"])
        self.assertEqual("outcome-1", payload["items"][0]["outcome_id"])
        self.assertEqual(["evidence-1"], payload["items"][0]["evidence_ids"])

    def test_latest_outcome_journal_rejects_mutation_methods(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        client = TestClient(
            main.create_app(outcome_journal_repository=FakeOutcomeJournalRepository([]))
        )

        for request in (client.post, client.put, client.patch, client.delete):
            with self.subTest(method=request.__name__):
                response = request("/internal/outcome-journal/latest")
                self.assertEqual(405, response.status_code)

    def test_outcome_journal_route_has_no_broker_order_or_execution_surface(self) -> None:
        from ai_infra_fund_api import main

        app = main.create_app(outcome_journal_repository=FakeOutcomeJournalRepository([]))
        paths = sorted(
            {
                route.path
                for route in app.routes
                if route.path.startswith("/internal/outcome-journal")
            }
        )
        offenders = [
            f"{path} contains {word}"
            for path in paths
            for word in ("broker", "order", "execution", "execute")
            if word in path.lower()
        ]

        self.assertEqual(["/internal/outcome-journal/latest"], paths)
        self.assertEqual([], offenders)


class FakeOutcomeJournalRepository:
    def __init__(self, items: list[dict[str, object]]) -> None:
        self._items = items

    def get_latest_outcomes(self) -> dict[str, object]:
        return {
            "status": "available" if self._items else "empty",
            "advisory_label": "advisory_only",
            "total_entries": len(self._items),
            "items": self._items,
        }


if __name__ == "__main__":
    unittest.main()
