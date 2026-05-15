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


URL_BASE = (
    "https://api.stlouisfed.org/fred/series/observations"
    "?series_id=DFF&api_key=FAKE&file_type=json"
)

DFF_RESPONSE = (
    '{"realtime_start": "2026-05-14", "realtime_end": "2026-05-14", "observations": ['
    '{"realtime_start": "2026-05-14", "realtime_end": "2026-05-14", '
    '"date": "2026-05-12", "value": "5.33"},'
    '{"realtime_start": "2026-05-14", "realtime_end": "2026-05-14", '
    '"date": "2026-05-13", "value": "5.33"},'
    '{"realtime_start": "2026-05-14", "realtime_end": "2026-05-14", '
    '"date": "2026-05-14", "value": "."}'
    "]}"
)


class FredSeriesConnectorTests(unittest.TestCase):
    def _build(self, *, responses: dict[str, StubHttpResponse]):
        from ai_infra_fund_worker.connectors.fred import FredSeriesConnector

        fetcher = StubFetcher(responses)
        return (
            FredSeriesConnector(api_key="FAKE", fetcher=fetcher, clock=lambda: NOW),
            fetcher,
        )

    def test_refuses_to_construct_without_api_key(self) -> None:
        from ai_infra_fund_worker.connectors.fred import FredSeriesConnector

        with self.assertRaisesRegex(ValueError, "api_key"):
            FredSeriesConnector(api_key="", fetcher=StubFetcher({}), clock=lambda: NOW)

    def test_fetch_series_returns_observations(self) -> None:
        connector, _ = self._build(
            responses={
                URL_BASE: StubHttpResponse(
                    status_code=200, content=DFF_RESPONSE, headers={}
                )
            }
        )

        observations = connector.fetch_series("DFF", since=None)

        self.assertEqual(3, len(observations))
        first = observations[0]
        self.assertEqual("DFF", first.series_id)
        self.assertEqual(datetime(2026, 5, 12, tzinfo=timezone.utc), first.as_of)
        self.assertEqual(Decimal("5.33"), first.value)
        self.assertEqual("2026-05-14", first.vintage_id)
        self.assertEqual("fred", first.source)

    def test_missing_value_is_none(self) -> None:
        connector, _ = self._build(
            responses={
                URL_BASE: StubHttpResponse(
                    status_code=200, content=DFF_RESPONSE, headers={}
                )
            }
        )

        observations = connector.fetch_series("DFF", since=None)
        self.assertIsNone(observations[2].value)

    def test_since_filter_adds_observation_start_param(self) -> None:
        url_with_since = (
            "https://api.stlouisfed.org/fred/series/observations"
            "?series_id=DFF&api_key=FAKE&file_type=json"
            "&observation_start=2026-05-13"
        )
        connector, fetcher = self._build(
            responses={
                url_with_since: StubHttpResponse(
                    status_code=200,
                    content='{"realtime_start":"2026-05-14","realtime_end":"2026-05-14","observations":[]}',
                    headers={},
                )
            }
        )

        connector.fetch_series("DFF", since=datetime(2026, 5, 13, tzinfo=timezone.utc))

        self.assertEqual([url_with_since], fetcher.calls)

    def test_empty_observations_returns_empty_tuple(self) -> None:
        connector, _ = self._build(
            responses={
                URL_BASE: StubHttpResponse(
                    status_code=200,
                    content='{"realtime_start":"2026-05-14","realtime_end":"2026-05-14","observations":[]}',
                    headers={},
                )
            }
        )
        self.assertEqual((), connector.fetch_series("DFF", since=None))

    def test_non_200_raises(self) -> None:
        connector, _ = self._build(
            responses={
                URL_BASE: StubHttpResponse(
                    status_code=429, content="rate limit", headers={}
                )
            }
        )
        with self.assertRaisesRegex(RuntimeError, "429"):
            connector.fetch_series("DFF", since=None)

    def test_content_hash_is_deterministic_per_observation(self) -> None:
        connector, _ = self._build(
            responses={
                URL_BASE: StubHttpResponse(
                    status_code=200, content=DFF_RESPONSE, headers={}
                )
            }
        )

        observations_a = connector.fetch_series("DFF", since=None)
        connector_b, _ = self._build(
            responses={
                URL_BASE: StubHttpResponse(
                    status_code=200, content=DFF_RESPONSE, headers={}
                )
            }
        )
        observations_b = connector_b.fetch_series("DFF", since=None)

        for a, b in zip(observations_a, observations_b):
            self.assertEqual(a.content_hash, b.content_hash)

    def test_revisions_in_different_vintages_produce_distinct_hashes(self) -> None:
        first_response = (
            '{"realtime_start":"2026-05-14","realtime_end":"2026-05-14","observations":['
            '{"realtime_start":"2026-05-14","realtime_end":"2026-05-14",'
            '"date":"2026-05-12","value":"5.33"}'
            "]}"
        )
        second_response = (
            '{"realtime_start":"2026-06-01","realtime_end":"2026-06-01","observations":['
            '{"realtime_start":"2026-06-01","realtime_end":"2026-06-01",'
            '"date":"2026-05-12","value":"5.34"}'
            "]}"
        )

        connector_a, _ = self._build(
            responses={
                URL_BASE: StubHttpResponse(
                    status_code=200, content=first_response, headers={}
                )
            }
        )
        connector_b, _ = self._build(
            responses={
                URL_BASE: StubHttpResponse(
                    status_code=200, content=second_response, headers={}
                )
            }
        )

        a_obs = connector_a.fetch_series("DFF", since=None)[0]
        b_obs = connector_b.fetch_series("DFF", since=None)[0]
        self.assertEqual(a_obs.as_of, b_obs.as_of)
        self.assertNotEqual(a_obs.content_hash, b_obs.content_hash)
        self.assertNotEqual(a_obs.vintage_id, b_obs.vintage_id)

    def test_connector_id_default(self) -> None:
        connector, _ = self._build(responses={})
        self.assertEqual("fred", connector.connector_id)


class FredVintageFetchTests(unittest.TestCase):
    def _build(self, *, responses: dict[str, StubHttpResponse]):
        from ai_infra_fund_worker.connectors.fred import FredSeriesConnector

        fetcher = StubFetcher(responses)
        return (
            FredSeriesConnector(api_key="FAKE", fetcher=fetcher, clock=lambda: NOW),
            fetcher,
        )

    def test_fetch_series_at_vintage_adds_realtime_params(self) -> None:
        url_with_vintage = (
            "https://api.stlouisfed.org/fred/series/observations"
            "?series_id=DFF&api_key=FAKE&file_type=json"
            "&realtime_start=2024-01-15&realtime_end=2024-01-15"
        )
        connector, fetcher = self._build(
            responses={
                url_with_vintage: StubHttpResponse(
                    status_code=200,
                    content=(
                        '{"realtime_start":"2024-01-15","realtime_end":"2024-01-15",'
                        '"observations":['
                        '{"realtime_start":"2024-01-15","realtime_end":"2024-01-15",'
                        '"date":"2024-01-12","value":"5.33"}'
                        "]}"
                    ),
                    headers={},
                )
            }
        )

        observations = connector.fetch_series_at_vintage(
            "DFF",
            vintage_date=datetime(2024, 1, 15, tzinfo=timezone.utc),
        )

        self.assertEqual([url_with_vintage], fetcher.calls)
        self.assertEqual(1, len(observations))
        self.assertEqual("2024-01-15", observations[0].vintage_id)
        self.assertEqual(
            datetime(2024, 1, 12, tzinfo=timezone.utc), observations[0].as_of
        )

    def test_vintage_date_must_be_aware(self) -> None:
        connector, _ = self._build(responses={})

        with self.assertRaisesRegex(ValueError, "tzinfo"):
            connector.fetch_series_at_vintage("DFF", vintage_date=datetime(2024, 1, 15))


if __name__ == "__main__":
    unittest.main()
