from __future__ import annotations

import sys
import unittest
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
WORKER_SRC = ROOT / "services" / "worker" / "src"
for path in (CORE_SRC, WORKER_SRC):
    sys.path.insert(0, str(path))


NOW = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)


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


FRONTIER_URL = "https://finnhub.io/api/v1/company-news?symbol=NVDA"

REAL_URL = (
    "https://finnhub.io/api/v1/company-news"
    "?symbol=NVDA&from=2026-04-14&to=2026-05-14&token=FAKE"
)

FINNHUB_RESPONSE = (
    "["
    '{"category": "company", "datetime": 1715716800,'
    ' "headline": "NVDA beats estimates", "id": 1,'
    ' "related": "NVDA", "source": "Reuters",'
    ' "summary": "...", "url": "https://reuters.com/a"},'
    '{"category": "company", "datetime": 1715720000,'
    ' "headline": "China export curbs", "id": 2,'
    ' "related": "NVDA", "source": "FT",'
    ' "summary": "...", "url": "https://ft.com/b"}'
    "]"
)


class FinnhubConnectorTests(unittest.TestCase):
    def _build(
        self,
        *,
        responses: dict[str, StubHttpResponse],
        api_key: str = "FAKE",
    ):
        from ai_infra_fund_worker.connectors.finnhub import FinnhubNewsConnector

        fetcher = StubFetcher(responses)
        return (
            FinnhubNewsConnector(
                api_key=api_key,
                fetcher=fetcher,
                clock=lambda: NOW,
                lookback_days=30,
            ),
            fetcher,
        )

    def test_refuses_to_construct_without_api_key(self) -> None:
        from ai_infra_fund_worker.connectors.finnhub import FinnhubNewsConnector

        with self.assertRaisesRegex(ValueError, "api_key"):
            FinnhubNewsConnector(
                api_key="",
                fetcher=StubFetcher({}),
                clock=lambda: NOW,
                lookback_days=30,
            )

    def test_fetch_builds_real_url_with_token_and_date_range(self) -> None:
        connector, fetcher = self._build(
            responses={
                REAL_URL: StubHttpResponse(
                    status_code=200, content=FINNHUB_RESPONSE, headers={}
                )
            }
        )

        result = connector.fetch(FRONTIER_URL)

        self.assertEqual([REAL_URL], fetcher.calls)
        self.assertEqual(200, result.status_code)
        self.assertEqual(64, len(result.content_hash))

    def test_result_canonical_url_does_not_expose_api_token(self) -> None:
        connector, _ = self._build(
            responses={
                REAL_URL: StubHttpResponse(
                    status_code=200, content=FINNHUB_RESPONSE, headers={}
                )
            }
        )

        result = connector.fetch(FRONTIER_URL)

        self.assertNotIn("token=", result.canonical_url)
        self.assertNotIn("FAKE", result.canonical_url)
        self.assertIn("symbol=NVDA", result.canonical_url)

    def test_discovered_urls_includes_article_urls(self) -> None:
        connector, _ = self._build(
            responses={
                REAL_URL: StubHttpResponse(
                    status_code=200, content=FINNHUB_RESPONSE, headers={}
                )
            }
        )

        result = connector.fetch(FRONTIER_URL)
        self.assertEqual(
            {"https://reuters.com/a", "https://ft.com/b"},
            set(result.discovered_urls),
        )

    def test_empty_response_returns_empty_discovered_urls(self) -> None:
        connector, _ = self._build(
            responses={
                REAL_URL: StubHttpResponse(status_code=200, content="[]", headers={})
            }
        )

        result = connector.fetch(FRONTIER_URL)
        self.assertEqual((), result.discovered_urls)

    def test_non_200_raises(self) -> None:
        connector, _ = self._build(
            responses={
                REAL_URL: StubHttpResponse(
                    status_code=429, content="rate limit", headers={}
                )
            }
        )
        with self.assertRaisesRegex(RuntimeError, "429"):
            connector.fetch(FRONTIER_URL)

    def test_rejects_url_missing_symbol(self) -> None:
        connector, _ = self._build(responses={})

        with self.assertRaisesRegex(ValueError, "symbol"):
            connector.fetch("https://finnhub.io/api/v1/company-news")

    def test_connector_id_default(self) -> None:
        connector, _ = self._build(responses={})
        self.assertEqual("finnhub", connector.connector_id)


if __name__ == "__main__":
    unittest.main()
