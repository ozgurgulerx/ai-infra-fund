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
    """Recorded-response HTTP stub. No live network ever."""

    def __init__(self, responses: dict[str, StubHttpResponse]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, dict[str, str]]] = []

    def get(self, url: str, *, headers: dict[str, str]) -> StubHttpResponse:
        self.calls.append((url, dict(headers)))
        try:
            return self.responses[url]
        except KeyError as exc:
            raise AssertionError(f"unexpected URL fetched: {url}") from exc


class SecEdgarConnectorTests(unittest.TestCase):
    def _build(
        self,
        *,
        responses: dict[str, StubHttpResponse] | None = None,
        cik_lookup: dict[str, str] | None = None,
        user_agent: str = "AI Infra Fund Research <ozgur@example.com>",
    ):
        from ai_infra_fund_worker.connectors.sec_edgar import SecEdgarConnector

        fetcher = StubFetcher({} if responses is None else responses)
        connector = SecEdgarConnector(
            user_agent=user_agent,
            cik_lookup=({"NVDA": "0001045810"} if cik_lookup is None else cik_lookup),
            fetcher=fetcher,
            clock=lambda: NOW,
        )
        return connector, fetcher

    def test_refuses_to_construct_without_user_agent(self) -> None:
        from ai_infra_fund_worker.connectors.sec_edgar import SecEdgarConnector

        with self.assertRaises(ValueError):
            SecEdgarConnector(
                user_agent="",
                cik_lookup={"NVDA": "0001045810"},
                fetcher=StubFetcher({}),
                clock=lambda: NOW,
            )

    def test_resolves_submissions_frontier_url_to_real_sec_url(self) -> None:
        real_url = "https://data.sec.gov/submissions/CIK0001045810.json"
        responses = {
            real_url: StubHttpResponse(
                status_code=200,
                content='{"name": "NVIDIA Corp"}',
                headers={"ETag": "abc123"},
            )
        }
        connector, fetcher = self._build(responses=responses)

        result = connector.fetch(
            "https://data.sec.gov/submissions/?frontier_ticker=NVDA"
        )

        self.assertEqual(real_url, result.canonical_url)
        self.assertEqual(200, result.status_code)
        self.assertEqual('{"name": "NVIDIA Corp"}', result.content)
        self.assertEqual(NOW, result.fetched_at)
        self.assertEqual("abc123", result.etag)
        self.assertEqual(64, len(result.content_hash))
        self.assertEqual([real_url], [call[0] for call in fetcher.calls])

    def test_resolves_companyfacts_frontier_url_to_real_sec_url(self) -> None:
        real_url = "https://data.sec.gov/api/xbrl/companyfacts/CIK0001045810.json"
        responses = {
            real_url: StubHttpResponse(
                status_code=200, content='{"facts": {}}', headers={}
            )
        }
        connector, _ = self._build(responses=responses)

        result = connector.fetch(
            "https://data.sec.gov/api/xbrl/companyfacts/?frontier_ticker=NVDA"
        )

        self.assertEqual(real_url, result.canonical_url)

    def test_sends_user_agent_header(self) -> None:
        real_url = "https://data.sec.gov/submissions/CIK0001045810.json"
        responses = {
            real_url: StubHttpResponse(status_code=200, content="{}", headers={})
        }
        connector, fetcher = self._build(responses=responses)

        connector.fetch("https://data.sec.gov/submissions/?frontier_ticker=NVDA")

        self.assertEqual(1, len(fetcher.calls))
        _, headers = fetcher.calls[0]
        self.assertEqual(
            "AI Infra Fund Research <ozgur@example.com>", headers["User-Agent"]
        )
        self.assertNotIn("Host", headers)

    def test_rejects_unknown_ticker(self) -> None:
        connector, _ = self._build(cik_lookup={})

        with self.assertRaisesRegex(KeyError, "NVDA"):
            connector.fetch("https://data.sec.gov/submissions/?frontier_ticker=NVDA")

    def test_rejects_url_without_frontier_ticker(self) -> None:
        connector, _ = self._build()

        with self.assertRaisesRegex(ValueError, "frontier_ticker"):
            connector.fetch("https://data.sec.gov/submissions/")

    def test_rejects_unrecognized_sec_path(self) -> None:
        connector, _ = self._build()

        with self.assertRaisesRegex(ValueError, "SEC EDGAR path"):
            connector.fetch("https://data.sec.gov/something-else/?frontier_ticker=NVDA")

    def test_content_hash_is_sha256_of_response_body(self) -> None:
        import hashlib

        real_url = "https://data.sec.gov/submissions/CIK0001045810.json"
        body = '{"name":"NVIDIA"}'
        responses = {
            real_url: StubHttpResponse(status_code=200, content=body, headers={})
        }
        connector, _ = self._build(responses=responses)

        result = connector.fetch(
            "https://data.sec.gov/submissions/?frontier_ticker=NVDA"
        )

        self.assertEqual(
            hashlib.sha256(body.encode("utf-8")).hexdigest(),
            result.content_hash,
        )

    def test_connector_id_default(self) -> None:
        connector, _ = self._build()
        self.assertEqual("sec-edgar", connector.connector_id)


class SecEdgarConnectorSatisfiesProtocolTest(unittest.TestCase):
    def test_exposes_connector_id_and_fetch_method(self) -> None:
        from ai_infra_fund_worker.connectors.sec_edgar import SecEdgarConnector

        connector = SecEdgarConnector(
            user_agent="test-ua",
            cik_lookup={"NVDA": "0001045810"},
            fetcher=StubFetcher({}),
            clock=lambda: NOW,
        )

        self.assertEqual("sec-edgar", connector.connector_id)
        self.assertTrue(callable(connector.fetch))


if __name__ == "__main__":
    unittest.main()
