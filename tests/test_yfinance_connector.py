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


YAHOO_URL = "https://query2.finance.yahoo.com/v7/finance/quote?symbols=NVDA"


def _yahoo_response(price: float, volume: int, market_time: int) -> StubHttpResponse:
    payload = (
        '{"quoteResponse": {"result": ['
        f'{{"symbol": "NVDA", '
        f'"regularMarketPrice": {price}, '
        f'"regularMarketVolume": {volume}, '
        f'"regularMarketTime": {market_time}}}'
        "]}}"
    )
    return StubHttpResponse(status_code=200, content=payload, headers={})


class YFinanceSnapshotConnectorTests(unittest.TestCase):
    def _build(self, *, responses: dict[str, StubHttpResponse]):
        from ai_infra_fund_worker.connectors.yfinance import YFinanceSnapshotConnector

        fetcher = StubFetcher(responses)
        return (
            YFinanceSnapshotConnector(fetcher=fetcher, clock=lambda: NOW),
            fetcher,
        )

    def test_fetch_snapshot_returns_close_volume_and_source(self) -> None:
        connector, _ = self._build(
            responses={YAHOO_URL: _yahoo_response(950.02, 47823200, 1715716800)}
        )

        snapshot = connector.fetch_snapshot("NVDA")

        self.assertEqual("NVDA", snapshot.ticker)
        self.assertEqual(Decimal("950.02"), snapshot.close_price)
        self.assertEqual(47823200, snapshot.volume)
        self.assertEqual("yfinance", snapshot.source)
        self.assertEqual(
            datetime.fromtimestamp(1715716800, tz=timezone.utc),
            snapshot.as_of,
        )

    def test_content_hash_is_deterministic(self) -> None:
        connector, _ = self._build(
            responses={YAHOO_URL: _yahoo_response(950.02, 47823200, 1715716800)}
        )

        first = connector.fetch_snapshot("NVDA")
        connector2, _ = self._build(
            responses={YAHOO_URL: _yahoo_response(950.02, 47823200, 1715716800)}
        )
        second = connector2.fetch_snapshot("NVDA")

        self.assertEqual(first.content_hash, second.content_hash)
        self.assertEqual(64, len(first.content_hash))

    def test_uses_yfinance_url(self) -> None:
        connector, fetcher = self._build(
            responses={YAHOO_URL: _yahoo_response(950.02, 47823200, 1715716800)}
        )
        connector.fetch_snapshot("NVDA")
        self.assertEqual([YAHOO_URL], fetcher.calls)

    def test_lowercase_ticker_is_upcased(self) -> None:
        connector, fetcher = self._build(
            responses={YAHOO_URL: _yahoo_response(950.02, 47823200, 1715716800)}
        )
        snapshot = connector.fetch_snapshot("nvda")
        self.assertEqual("NVDA", snapshot.ticker)
        self.assertEqual([YAHOO_URL], fetcher.calls)

    def test_rejects_empty_result_set(self) -> None:
        empty = StubHttpResponse(
            status_code=200,
            content='{"quoteResponse": {"result": []}}',
            headers={},
        )
        connector, _ = self._build(responses={YAHOO_URL: empty})
        with self.assertRaisesRegex(LookupError, "NVDA"):
            connector.fetch_snapshot("NVDA")

    def test_rejects_non_200_response(self) -> None:
        bad = StubHttpResponse(status_code=429, content="rate limit", headers={})
        connector, _ = self._build(responses={YAHOO_URL: bad})
        with self.assertRaisesRegex(RuntimeError, "429"):
            connector.fetch_snapshot("NVDA")

    def test_connector_id_default(self) -> None:
        connector, _ = self._build(responses={})
        self.assertEqual("yfinance", connector.connector_id)


if __name__ == "__main__":
    unittest.main()
