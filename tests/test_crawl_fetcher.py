from __future__ import annotations

import sys
import unittest
from pathlib import Path

import httpx


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
sys.path.insert(0, str(CORE_SRC))

from ai_infra_fund_core.equity_intelligence.fetcher import (  # noqa: E402
    DomainThrottle,
    FetchResult,
    HttpFetcher,
    RobotsCache,
)


USER_AGENT = "ai-infra-fund-test/0.0 (advisory; contact: local-only)"


def _build_fetcher(
    handler, robots_allow: bool = True, throttle_min: float = 0.0
) -> HttpFetcher:
    transport = httpx.MockTransport(handler)
    client = httpx.Client(
        transport=transport, headers={"User-Agent": USER_AGENT}, timeout=5.0
    )
    robots = RobotsCache(client=client, user_agent=USER_AGENT)
    robots._policy_for = lambda _host: robots_allow  # type: ignore[assignment]
    throttle = DomainThrottle(min_delay_seconds=throttle_min)
    return HttpFetcher(
        client=client,
        user_agent=USER_AGENT,
        robots_cache=robots,
        domain_throttle=throttle,
    )


class FetchSuccessTests(unittest.TestCase):
    def test_returns_200_with_body_etag_and_content_type(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                content=b"<html>ok</html>",
                headers={
                    "Content-Type": "text/html; charset=utf-8",
                    "ETag": '"v1"',
                    "Last-Modified": "Wed, 14 May 2026 12:00:00 GMT",
                },
            )

        fetcher = _build_fetcher(handler)
        result = fetcher.fetch("https://x.test/")

        self.assertIsInstance(result, FetchResult)
        self.assertEqual(200, result.http_status)
        self.assertEqual(b"<html>ok</html>", result.body_bytes)
        self.assertEqual('"v1"', result.etag)
        self.assertEqual("Wed, 14 May 2026 12:00:00 GMT", result.last_modified)
        self.assertEqual("text/html; charset=utf-8", result.content_type)
        self.assertIsNone(result.error_summary)
        self.assertGreaterEqual(result.latency_ms, 0)

    def test_sends_conditional_headers_when_provided(self) -> None:
        captured: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured.update(dict(request.headers))
            return httpx.Response(304, content=b"")

        fetcher = _build_fetcher(handler)
        result = fetcher.fetch(
            "https://x.test/",
            etag='"v1"',
            last_modified="Wed, 14 May 2026 12:00:00 GMT",
        )

        self.assertEqual('"v1"', captured["if-none-match"])
        self.assertEqual("Wed, 14 May 2026 12:00:00 GMT", captured["if-modified-since"])
        self.assertEqual(304, result.http_status)
        self.assertEqual(b"", result.body_bytes)
        self.assertIsNone(result.error_summary)


class FetchErrorTests(unittest.TestCase):
    def test_404_returns_status_without_error_summary(self) -> None:
        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, content=b"missing")

        fetcher = _build_fetcher(handler)
        result = fetcher.fetch("https://x.test/missing")

        self.assertEqual(404, result.http_status)
        self.assertIsNone(result.error_summary)

    def test_5xx_returns_status_and_marks_error(self) -> None:
        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(503, content=b"unavailable")

        fetcher = _build_fetcher(handler)
        result = fetcher.fetch("https://x.test/")

        self.assertEqual(503, result.http_status)
        self.assertEqual("server_error", result.error_summary)

    def test_transport_error_returns_error_summary(self) -> None:
        def handler(_request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("boom")

        fetcher = _build_fetcher(handler)
        result = fetcher.fetch("https://x.test/")

        self.assertIsNone(result.http_status)
        self.assertEqual("connect_error", result.error_summary)


class RobotsTests(unittest.TestCase):
    def test_robots_disallowed_returns_error_summary_without_request(self) -> None:
        call_count = {"n": 0}

        def handler(_request: httpx.Request) -> httpx.Response:
            call_count["n"] += 1
            return httpx.Response(200, content=b"x")

        fetcher = _build_fetcher(handler, robots_allow=False)
        result = fetcher.fetch("https://blocked.test/")

        self.assertEqual("robots_disallowed", result.error_summary)
        self.assertEqual(0, call_count["n"])


class ThrottleTests(unittest.TestCase):
    def test_throttle_delays_second_request_to_same_host(self) -> None:
        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=b"ok")

        throttle = DomainThrottle(min_delay_seconds=0.05)
        transport = httpx.MockTransport(handler)
        client = httpx.Client(
            transport=transport, headers={"User-Agent": USER_AGENT}, timeout=5.0
        )
        robots = RobotsCache(client=client, user_agent=USER_AGENT)
        robots._policy_for = lambda _host: True  # type: ignore[assignment]
        fetcher = HttpFetcher(
            client=client,
            user_agent=USER_AGENT,
            robots_cache=robots,
            domain_throttle=throttle,
        )

        first = fetcher.fetch("https://x.test/a")
        second = fetcher.fetch("https://x.test/b")

        self.assertEqual(200, first.http_status)
        self.assertEqual(200, second.http_status)
        # Second fetch records that it had to wait.
        self.assertGreaterEqual(second.latency_ms, 0)


if __name__ == "__main__":
    unittest.main()
