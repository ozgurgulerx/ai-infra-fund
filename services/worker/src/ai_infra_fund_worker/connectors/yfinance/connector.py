from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
from typing import Callable

from ai_infra_fund_core.equity_intelligence.connectors import MarketPriceSnapshot
from ai_infra_fund_worker.connectors.http import HttpFetcher


_QUOTE_URL_TEMPLATE = (
    "https://query2.finance.yahoo.com/v7/finance/quote?symbols={ticker}"
)


class YFinanceSnapshotConnector:
    """Implements MarketPriceSnapshotConnector against the Yahoo quote JSON API."""

    connector_id: str

    def __init__(
        self,
        *,
        fetcher: HttpFetcher,
        clock: Callable[[], datetime],
        connector_id: str = "yfinance",
    ) -> None:
        self._fetcher = fetcher
        self._clock = clock
        self.connector_id = connector_id

    def fetch_snapshot(self, ticker: str) -> MarketPriceSnapshot:
        normalized = ticker.strip().upper()
        url = _QUOTE_URL_TEMPLATE.format(ticker=normalized)
        response = self._fetcher.get(url, headers={"Accept": "application/json"})
        if response.status_code != 200:
            raise RuntimeError(
                f"yfinance fetch for {normalized} returned HTTP {response.status_code}"
            )
        payload = json.loads(response.content)
        results = payload.get("quoteResponse", {}).get("result", [])
        if not results:
            raise LookupError(f"yfinance returned no quote for {normalized}")
        quote = results[0]
        close_price = Decimal(str(quote["regularMarketPrice"]))
        volume = int(quote["regularMarketVolume"])
        market_time = int(quote["regularMarketTime"])
        as_of = datetime.fromtimestamp(market_time, tz=timezone.utc)
        digest_seed = (
            f"yfinance|{normalized}|{as_of.isoformat()}|{close_price}|{volume}"
        )
        content_hash = sha256(digest_seed.encode("utf-8")).hexdigest()
        return MarketPriceSnapshot(
            ticker=normalized,
            as_of=as_of,
            close_price=close_price,
            volume=volume,
            source="yfinance",
            content_hash=content_hash,
        )


__all__ = ["YFinanceSnapshotConnector"]
