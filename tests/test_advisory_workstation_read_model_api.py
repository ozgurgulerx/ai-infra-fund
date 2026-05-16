from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
API_SRC = ROOT / "services" / "api" / "src"
for path in (CORE_SRC, API_SRC):
    sys.path.insert(0, str(path))


class AdvisoryWorkstationReadModelApiTests(unittest.TestCase):
    def test_read_only_advisory_workstation_endpoints_return_repository_payloads(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        repository = FakeAdvisoryWorkstationRepository()
        client = TestClient(
            main.create_app(advisory_workstation_repository=repository)
        )

        expected = {
            "/internal/source-signals/latest": "source-signals",
            "/internal/market-events/latest": "market-events",
            "/internal/market-events/NVDA": "ticker-market-events",
            "/internal/analyst-brief/latest": "analyst-brief",
            "/internal/trading-advisory/latest": "trading-advisory",
            "/internal/ticker/NVDA/analyst-summary": "ticker-summary",
        }
        for path, kind in expected.items():
            with self.subTest(path=path):
                response = client.get(path)
                self.assertEqual(200, response.status_code)
                self.assertEqual(kind, response.json()["data"]["kind"])

        self.assertEqual(["NVDA", "NVDA"], repository.ticker_calls)

    def test_advisory_workstation_endpoints_reject_mutation_methods(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        client = TestClient(
            main.create_app(advisory_workstation_repository=FakeAdvisoryWorkstationRepository())
        )

        for path in (
            "/internal/source-signals/latest",
            "/internal/market-events/latest",
            "/internal/market-events/NVDA",
            "/internal/analyst-brief/latest",
            "/internal/trading-advisory/latest",
            "/internal/ticker/NVDA/analyst-summary",
        ):
            for request in (client.post, client.put, client.patch, client.delete):
                with self.subTest(path=path, method=request.__name__):
                    response = request(path)
                    self.assertEqual(405, response.status_code)

    def test_route_names_do_not_expose_execution_surface(self) -> None:
        from ai_infra_fund_api import main

        app = main.create_app(
            advisory_workstation_repository=FakeAdvisoryWorkstationRepository()
        )
        paths = [
            route.path
            for route in app.routes
            if route.path.startswith("/internal/")
        ]
        advisory_paths = [
            path
            for path in paths
            if any(
                marker in path
                for marker in (
                    "source-signals",
                    "market-events",
                    "analyst-brief",
                    "trading-advisory",
                    "analyst-summary",
                )
            )
        ]
        offenders = [
            f"{path} contains {word}"
            for path in advisory_paths
            for word in ("order", "broker", "execution")
            if word in path.lower()
        ]

        self.assertEqual([], offenders)


class FakeAdvisoryWorkstationRepository:
    def __init__(self) -> None:
        self.ticker_calls: list[str] = []

    def get_latest_source_signals(self) -> dict[str, object]:
        return {"kind": "source-signals", "advisory_label": "advisory_only"}

    def get_latest_market_events(self) -> dict[str, object]:
        return {"kind": "market-events", "advisory_label": "advisory_only"}

    def get_market_events_for_ticker(self, ticker: str) -> dict[str, object]:
        self.ticker_calls.append(ticker)
        return {"kind": "ticker-market-events", "ticker": ticker, "advisory_label": "advisory_only"}

    def get_latest_analyst_brief(self) -> dict[str, object]:
        return {"kind": "analyst-brief", "advisory_label": "advisory_only"}

    def get_latest_trading_advisory(self) -> dict[str, object]:
        return {"kind": "trading-advisory", "advisory_label": "advisory_only"}

    def get_ticker_analyst_summary(self, ticker: str) -> dict[str, object]:
        self.ticker_calls.append(ticker)
        return {"kind": "ticker-summary", "ticker": ticker, "advisory_label": "advisory_only"}


if __name__ == "__main__":
    unittest.main()
