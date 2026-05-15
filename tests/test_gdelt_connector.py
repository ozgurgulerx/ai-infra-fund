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


GDELT_URL = (
    "https://api.gdeltproject.org/api/v2/doc/doc"
    "?query=NVDA&mode=ArtList&format=json&maxrecords=250"
)

GDELT_RESPONSE = (
    '{"articles": ['
    '{"url": "https://reuters.com/article1", "title": "NVDA earnings beat",'
    ' "domain": "reuters.com", "language": "English",'
    ' "seendate": "20260514T120000Z"},'
    '{"url": "https://ft.com/article2", "title": "China export curbs",'
    ' "domain": "ft.com", "language": "English",'
    ' "seendate": "20260514T130000Z"}'
    "]}"
)


class GdeltDocConnectorTests(unittest.TestCase):
    def _build(self, *, responses: dict[str, StubHttpResponse]):
        from ai_infra_fund_worker.connectors.gdelt import GdeltDocConnector

        fetcher = StubFetcher(responses)
        return (
            GdeltDocConnector(fetcher=fetcher, clock=lambda: NOW),
            fetcher,
        )

    def test_fetch_returns_canonical_url_and_status(self) -> None:
        from ai_infra_fund_core.equity_intelligence.urls import canonicalize_url

        connector, _ = self._build(
            responses={
                GDELT_URL: StubHttpResponse(
                    status_code=200, content=GDELT_RESPONSE, headers={}
                )
            }
        )

        result = connector.fetch(GDELT_URL)

        self.assertEqual(
            canonicalize_url(GDELT_URL).canonical_url, result.canonical_url
        )
        self.assertEqual(200, result.status_code)
        self.assertEqual(NOW, result.fetched_at)
        self.assertEqual(64, len(result.content_hash))

    def test_discovered_urls_includes_article_urls(self) -> None:
        connector, _ = self._build(
            responses={
                GDELT_URL: StubHttpResponse(
                    status_code=200, content=GDELT_RESPONSE, headers={}
                )
            }
        )

        result = connector.fetch(GDELT_URL)

        self.assertEqual(
            {"https://reuters.com/article1", "https://ft.com/article2"},
            set(result.discovered_urls),
        )

    def test_empty_articles_returns_empty_discovered_urls(self) -> None:
        empty_url = (
            "https://api.gdeltproject.org/api/v2/doc/doc"
            "?query=ZZZZ&mode=ArtList&format=json&maxrecords=250"
        )
        connector, _ = self._build(
            responses={
                empty_url: StubHttpResponse(
                    status_code=200, content='{"articles": []}', headers={}
                )
            }
        )

        result = connector.fetch(empty_url)
        self.assertEqual((), result.discovered_urls)

    def test_non_200_raises(self) -> None:
        connector, _ = self._build(
            responses={
                GDELT_URL: StubHttpResponse(
                    status_code=502, content="bad gateway", headers={}
                )
            }
        )
        with self.assertRaisesRegex(RuntimeError, "502"):
            connector.fetch(GDELT_URL)

    def test_connector_id_default(self) -> None:
        connector, _ = self._build(responses={})
        self.assertEqual("gdelt", connector.connector_id)


if __name__ == "__main__":
    unittest.main()
