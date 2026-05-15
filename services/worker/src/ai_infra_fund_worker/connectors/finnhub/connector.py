from __future__ import annotations

import json
from datetime import datetime, timedelta
from hashlib import sha256
from typing import Callable
from urllib.parse import parse_qs, urlparse

from ai_infra_fund_core.equity_intelligence.connectors import ConnectorFetchResult
from ai_infra_fund_worker.connectors.http import HttpFetcher


_COMPANY_NEWS_PATH = "/api/v1/company-news"


class FinnhubNewsConnector:
    """Implements NewsRssPublicWebConnector for Finnhub `/company-news`.

    The frontier URL stored by the seeder is the bare endpoint with a
    `symbol` query param. At fetch time the connector adds `from`/`to`
    (rolling lookback window) and `token` (the API key) — keeping the
    api key out of the stored frontier and crawl-log rows.
    """

    connector_id: str

    def __init__(
        self,
        *,
        api_key: str,
        fetcher: HttpFetcher,
        clock: Callable[[], datetime],
        lookback_days: int = 30,
        connector_id: str = "finnhub",
    ) -> None:
        if not api_key or not api_key.strip():
            raise ValueError(
                "Finnhub requires a non-empty api_key (set FINNHUB_API_KEY)"
            )
        if lookback_days <= 0:
            raise ValueError("lookback_days must be positive")
        self._api_key = api_key.strip()
        self._fetcher = fetcher
        self._clock = clock
        self._lookback_days = lookback_days
        self.connector_id = connector_id

    def fetch(self, url: str) -> ConnectorFetchResult:
        parsed = urlparse(url)
        if parsed.path != _COMPANY_NEWS_PATH:
            raise ValueError(f"unrecognized Finnhub path {parsed.path!r} in {url}")
        query = parse_qs(parsed.query)
        symbols = query.get("symbol")
        if not symbols:
            raise ValueError(f"Finnhub frontier URL is missing symbol query: {url}")
        symbol = symbols[0].upper()
        now = self._clock()
        to_date = now.date()
        from_date = (now - timedelta(days=self._lookback_days)).date()
        real_url = (
            f"https://finnhub.io{_COMPANY_NEWS_PATH}"
            f"?symbol={symbol}&from={from_date.isoformat()}"
            f"&to={to_date.isoformat()}&token={self._api_key}"
        )
        canonical_url = (
            f"https://finnhub.io{_COMPANY_NEWS_PATH}"
            f"?symbol={symbol}&from={from_date.isoformat()}"
            f"&to={to_date.isoformat()}"
        )
        response = self._fetcher.get(real_url, headers={"Accept": "application/json"})
        if response.status_code != 200:
            raise RuntimeError(
                f"Finnhub fetch for {symbol} returned HTTP {response.status_code}"
            )
        payload = json.loads(response.content)
        if not isinstance(payload, list):
            raise RuntimeError(f"Finnhub returned non-list payload for {symbol}")
        discovered = tuple(article["url"] for article in payload if article.get("url"))
        content_hash = sha256(response.content.encode("utf-8")).hexdigest()
        return ConnectorFetchResult(
            canonical_url=canonical_url,
            status_code=response.status_code,
            fetched_at=now,
            content=response.content,
            content_hash=content_hash,
            discovered_urls=discovered,
            etag=response.headers.get("ETag"),
            last_modified=response.headers.get("Last-Modified"),
        )


__all__ = ["FinnhubNewsConnector"]
