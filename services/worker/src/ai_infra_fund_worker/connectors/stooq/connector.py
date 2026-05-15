from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
from typing import Callable

from ai_infra_fund_core.equity_intelligence.connectors import MarketPriceSnapshot
from ai_infra_fund_worker.connectors.http import HttpFetcher


_CSV_URL_TEMPLATE = "https://stooq.com/q/d/l/?s={ticker}.us&i=d"


class StooqSnapshotConnector:
    """Implements MarketPriceSnapshotConnector against Stooq daily CSV downloads."""

    connector_id: str

    def __init__(
        self,
        *,
        fetcher: HttpFetcher,
        clock: Callable[[], datetime],
        connector_id: str = "stooq",
    ) -> None:
        self._fetcher = fetcher
        self._clock = clock
        self.connector_id = connector_id

    def fetch_snapshot(self, ticker: str) -> MarketPriceSnapshot:
        normalized = ticker.strip().upper()
        url = _CSV_URL_TEMPLATE.format(ticker=normalized.lower())
        response = self._fetcher.get(url, headers={"Accept": "text/csv"})
        if response.status_code != 200:
            raise RuntimeError(
                f"stooq fetch for {normalized} returned HTTP {response.status_code}"
            )

        reader = csv.DictReader(io.StringIO(response.content))
        rows = list(reader)
        if not rows:
            raise LookupError(f"stooq returned no rows for {normalized}")
        last = rows[-1]
        as_of = datetime.strptime(last["Date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        close_price = Decimal(last["Close"])
        volume = int(last["Volume"])
        digest_seed = f"stooq|{normalized}|{as_of.isoformat()}|{close_price}|{volume}"
        content_hash = sha256(digest_seed.encode("utf-8")).hexdigest()
        return MarketPriceSnapshot(
            ticker=normalized,
            as_of=as_of,
            close_price=close_price,
            volume=volume,
            source="stooq",
            content_hash=content_hash,
        )


__all__ = ["StooqSnapshotConnector"]
