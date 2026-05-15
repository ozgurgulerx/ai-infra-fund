from __future__ import annotations

import json
from datetime import datetime
from hashlib import sha256
from typing import Callable

from ai_infra_fund_core.equity_intelligence.connectors import ConnectorFetchResult
from ai_infra_fund_worker.connectors.http import HttpFetcher


class GdeltDocConnector:
    """Implements NewsRssPublicWebConnector for the GDELT 2.0 DOC API."""

    connector_id: str

    def __init__(
        self,
        *,
        fetcher: HttpFetcher,
        clock: Callable[[], datetime],
        connector_id: str = "gdelt",
    ) -> None:
        self._fetcher = fetcher
        self._clock = clock
        self.connector_id = connector_id

    def fetch(self, url: str) -> ConnectorFetchResult:
        response = self._fetcher.get(url, headers={"Accept": "application/json"})
        if response.status_code != 200:
            raise RuntimeError(
                f"GDELT fetch for {url} returned HTTP {response.status_code}"
            )
        payload = json.loads(response.content)
        articles = payload.get("articles", []) or []
        discovered = tuple(article["url"] for article in articles if article.get("url"))
        content_hash = sha256(response.content.encode("utf-8")).hexdigest()
        return ConnectorFetchResult(
            canonical_url=url,
            status_code=response.status_code,
            fetched_at=self._clock(),
            content=response.content,
            content_hash=content_hash,
            discovered_urls=discovered,
            etag=response.headers.get("ETag"),
            last_modified=response.headers.get("Last-Modified"),
        )


__all__ = ["GdeltDocConnector"]
