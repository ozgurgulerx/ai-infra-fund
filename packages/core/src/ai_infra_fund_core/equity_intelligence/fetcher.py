from __future__ import annotations

import time
import urllib.robotparser as _rp
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Mapping
from urllib.parse import urlparse

import httpx


@dataclass(frozen=True, slots=True)
class FetchResult:
    final_url: str
    http_status: int | None
    content_type: str | None
    body_bytes: bytes
    etag: str | None
    last_modified: str | None
    latency_ms: int
    fetch_method: str
    error_summary: str | None


class RobotsCache:
    """Cache of per-host robots.txt parsers with a TTL.

    Falls open on fetch failure (treats as allowed) — robots is advisory
    when the server itself is unreachable. Real disallow rules block crawls.
    """

    def __init__(
        self,
        *,
        client: httpx.Client,
        user_agent: str,
        ttl: timedelta = timedelta(hours=1),
    ) -> None:
        self._client = client
        self._user_agent = user_agent
        self._ttl = ttl
        self._cache: dict[str, tuple[datetime, _rp.RobotFileParser]] = {}

    def allowed(self, url: str) -> bool:
        parsed = urlparse(url)
        host = parsed.netloc
        if not host:
            return True
        return (
            self._policy_for(host).can_fetch(self._user_agent, url)
            if hasattr(self._policy_for(host), "can_fetch")
            else bool(self._policy_for(host))
        )

    def _policy_for(self, host: str) -> _rp.RobotFileParser:
        now = datetime.now(tz=timezone.utc)
        cached = self._cache.get(host)
        if cached is not None and (now - cached[0]) < self._ttl:
            return cached[1]
        parser = _rp.RobotFileParser()
        try:
            response = self._client.get(f"https://{host}/robots.txt", timeout=5.0)
            if response.status_code == 200:
                parser.parse(response.text.splitlines())
            else:
                parser.parse([])
        except httpx.HTTPError:
            parser.parse([])
        self._cache[host] = (now, parser)
        return parser


class DomainThrottle:
    """Sync per-host throttle. Sleeps just long enough to satisfy min_delay."""

    def __init__(self, *, min_delay_seconds: float = 2.0) -> None:
        if min_delay_seconds < 0:
            raise ValueError("min_delay_seconds must be >= 0")
        self._min = float(min_delay_seconds)
        self._last: dict[str, float] = {}

    def wait(self, host: str) -> None:
        if not host:
            return
        now = time.monotonic()
        last = self._last.get(host)
        if last is not None and self._min > 0:
            delta = now - last
            if delta < self._min:
                time.sleep(self._min - delta)
        self._last[host] = time.monotonic()


class HttpFetcher:
    """Sync httpx-based fetcher with robots + per-host throttle + conditional GET.

    No internal retry: failures are surfaced so the frontier records them
    and the deterministic backoff (`core.equity_intelligence.frontier`) decides
    the next attempt time.
    """

    def __init__(
        self,
        *,
        client: httpx.Client,
        user_agent: str,
        robots_cache: RobotsCache,
        domain_throttle: DomainThrottle,
    ) -> None:
        self._client = client
        self._user_agent = user_agent
        self._robots = robots_cache
        self._throttle = domain_throttle

    def fetch(
        self,
        url: str,
        *,
        etag: str | None = None,
        last_modified: str | None = None,
    ) -> FetchResult:
        parsed = urlparse(url)
        host = parsed.netloc
        if not self._robots.allowed(url):
            return FetchResult(
                final_url=url,
                http_status=None,
                content_type=None,
                body_bytes=b"",
                etag=None,
                last_modified=None,
                latency_ms=0,
                fetch_method="error",
                error_summary="robots_disallowed",
            )

        headers: dict[str, str] = {"User-Agent": self._user_agent}
        if etag:
            headers["If-None-Match"] = etag
        if last_modified:
            headers["If-Modified-Since"] = last_modified

        self._throttle.wait(host)

        started = time.monotonic()
        try:
            response = self._client.get(url, headers=headers, follow_redirects=True)
        except httpx.TimeoutException:
            elapsed = int((time.monotonic() - started) * 1000)
            return FetchResult(
                final_url=url,
                http_status=None,
                content_type=None,
                body_bytes=b"",
                etag=None,
                last_modified=None,
                latency_ms=elapsed,
                fetch_method="error",
                error_summary="timeout",
            )
        except httpx.ConnectError:
            elapsed = int((time.monotonic() - started) * 1000)
            return FetchResult(
                final_url=url,
                http_status=None,
                content_type=None,
                body_bytes=b"",
                etag=None,
                last_modified=None,
                latency_ms=elapsed,
                fetch_method="error",
                error_summary="connect_error",
            )
        except httpx.HTTPError:
            elapsed = int((time.monotonic() - started) * 1000)
            return FetchResult(
                final_url=url,
                http_status=None,
                content_type=None,
                body_bytes=b"",
                etag=None,
                last_modified=None,
                latency_ms=elapsed,
                fetch_method="error",
                error_summary="transport_error",
            )

        latency_ms = int((time.monotonic() - started) * 1000)
        status = response.status_code
        fetch_method = "http_304" if status == 304 else "http_get"
        error_summary: str | None = None
        if status >= 500:
            error_summary = "server_error"

        return FetchResult(
            final_url=str(response.url),
            http_status=status,
            content_type=_header(response.headers, "content-type"),
            body_bytes=b"" if status == 304 else response.content,
            etag=_header(response.headers, "etag"),
            last_modified=_header(response.headers, "last-modified"),
            latency_ms=latency_ms,
            fetch_method=fetch_method,
            error_summary=error_summary,
        )


def _header(headers: Mapping[str, str], name: str) -> str | None:
    value = headers.get(name)
    if value is None:
        # httpx headers are case-insensitive Mapping; still guard.
        for key, val in headers.items():
            if key.lower() == name.lower():
                return val
        return None
    return value


__all__ = ["DomainThrottle", "FetchResult", "HttpFetcher", "RobotsCache"]
