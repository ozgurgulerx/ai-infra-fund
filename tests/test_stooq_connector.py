from __future__ import annotations

import sys
import unittest
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
WORKER_SRC = ROOT / "services" / "worker" / "src"
for path in (CORE_SRC, WORKER_SRC):
    sys.path.insert(0, str(path))


NOW = datetime(2026, 5, 14, 21, 5, tzinfo=timezone.utc)


@dataclass
class StubHttpResponse:
    status_code: int
    content: str
    headers: dict[str, str]


class StubFetcher:
    def __init__(self, responses: dict[str, StubHttpResponse]) -> None:
        self.responses = responses
        self.calls: list[str] = []

    def get(self, url: str, *, headers: dict[str, str]) -> StubHttpResponse:
        self.calls.append(url)
        if url not in self.responses:
            raise AssertionError(f"unexpected URL fetched: {url}")
        return self.responses[url]


STOOQ_URL = "https://stooq.com/q/d/l/?s=nvda.us&i=d"

STOOQ_CSV = (
    "Date,Open,High,Low,Close,Volume\n"
    "2026-05-13,948.10,952.50,946.00,950.00,46123100\n"
    "2026-05-14,950.50,955.00,945.00,950.02,47823200\n"
)


class StooqSnapshotConnectorTests(unittest.TestCase):
    def _build(self, *, responses: dict[str, StubHttpResponse]):
        from ai_infra_fund_worker.connectors.stooq import StooqSnapshotConnector

        fetcher = StubFetcher(responses)
        return (
            StooqSnapshotConnector(fetcher=fetcher, clock=lambda: NOW),
            fetcher,
        )

    def test_fetch_snapshot_uses_last_row_of_csv(self) -> None:
        connector, _ = self._build(
            responses={
                STOOQ_URL: StubHttpResponse(
                    status_code=200, content=STOOQ_CSV, headers={}
                )
            }
        )

        snapshot = connector.fetch_snapshot("NVDA")

        self.assertEqual("NVDA", snapshot.ticker)
        self.assertEqual(Decimal("950.02"), snapshot.close_price)
        self.assertEqual(47823200, snapshot.volume)
        self.assertEqual("stooq", snapshot.source)
        self.assertEqual(datetime(2026, 5, 14, tzinfo=timezone.utc), snapshot.as_of)

    def test_fetches_lowercase_ticker_url(self) -> None:
        connector, fetcher = self._build(
            responses={
                STOOQ_URL: StubHttpResponse(
                    status_code=200, content=STOOQ_CSV, headers={}
                )
            }
        )
        connector.fetch_snapshot("NVDA")
        self.assertEqual([STOOQ_URL], fetcher.calls)

    def test_rejects_empty_csv(self) -> None:
        empty = "Date,Open,High,Low,Close,Volume\n"
        connector, _ = self._build(
            responses={
                STOOQ_URL: StubHttpResponse(status_code=200, content=empty, headers={})
            }
        )
        with self.assertRaisesRegex(LookupError, "NVDA"):
            connector.fetch_snapshot("NVDA")

    def test_rejects_404(self) -> None:
        connector, _ = self._build(
            responses={
                STOOQ_URL: StubHttpResponse(
                    status_code=404, content="not found", headers={}
                )
            }
        )
        with self.assertRaisesRegex(RuntimeError, "404"):
            connector.fetch_snapshot("NVDA")

    def test_connector_id_default(self) -> None:
        connector, _ = self._build(responses={})
        self.assertEqual("stooq", connector.connector_id)


if __name__ == "__main__":
    unittest.main()
