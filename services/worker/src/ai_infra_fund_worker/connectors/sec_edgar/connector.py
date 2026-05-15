from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from typing import Callable
from urllib.parse import parse_qs, urlparse

from ai_infra_fund_core.equity_intelligence.connectors import ConnectorFetchResult
from ai_infra_fund_worker.connectors.http import HttpFetcher


_SUBMISSIONS_PATH = "/submissions/"
_COMPANYFACTS_PATH = "/api/xbrl/companyfacts/"


class SecEdgarConnector:
    """Implements `SecFilingConnector` over `data.sec.gov`.

    Accepts a "frontier URL" produced by the seeder with a synthetic
    `frontier_ticker` query parameter, resolves it to the real SEC URL
    (which requires a zero-padded 10-digit CIK), and fetches it with
    the SEC-mandated User-Agent header.
    """

    connector_id: str

    def __init__(
        self,
        *,
        user_agent: str,
        cik_lookup: dict[str, str],
        fetcher: HttpFetcher,
        clock: Callable[[], datetime],
        connector_id: str = "sec-edgar",
    ) -> None:
        if not user_agent or not user_agent.strip():
            raise ValueError(
                "SEC EDGAR requires a non-empty User-Agent (set SEC_EDGAR_USER_AGENT)"
            )
        self._user_agent = user_agent.strip()
        self._cik_lookup = {ticker.upper(): cik for ticker, cik in cik_lookup.items()}
        self._fetcher = fetcher
        self._clock = clock
        self.connector_id = connector_id

    def fetch(self, url: str) -> ConnectorFetchResult:
        real_url = self._resolve(url)
        headers = {"User-Agent": self._user_agent}
        response = self._fetcher.get(real_url, headers=headers)
        content_hash = sha256(response.content.encode("utf-8")).hexdigest()
        return ConnectorFetchResult(
            canonical_url=real_url,
            status_code=response.status_code,
            fetched_at=self._clock(),
            content=response.content,
            content_hash=content_hash,
            etag=response.headers.get("ETag"),
            last_modified=response.headers.get("Last-Modified"),
        )

    def _resolve(self, url: str) -> str:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        ticker_values = query.get("frontier_ticker")
        if not ticker_values:
            raise ValueError(
                f"SEC EDGAR frontier URL is missing frontier_ticker query: {url}"
            )
        ticker = ticker_values[0].upper()
        try:
            cik = self._cik_lookup[ticker]
        except KeyError as exc:
            raise KeyError(f"no CIK registered for ticker {ticker}") from exc
        cik_padded = cik.zfill(10)

        path = parsed.path
        if path == _SUBMISSIONS_PATH:
            return f"https://data.sec.gov/submissions/CIK{cik_padded}.json"
        if path == _COMPANYFACTS_PATH:
            return f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik_padded}.json"
        raise ValueError(f"unrecognized SEC EDGAR path {path!r} in frontier URL {url}")


__all__ = ["SecEdgarConnector"]
