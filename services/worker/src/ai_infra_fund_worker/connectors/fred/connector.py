from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
from typing import Callable

from ai_infra_fund_core.equity_intelligence.connectors import MacroSeriesObservation
from ai_infra_fund_worker.connectors.http import HttpFetcher


_OBSERVATIONS_URL = "https://api.stlouisfed.org/fred/series/observations"


class FredSeriesConnector:
    """Implements MacroSeriesConnector for FRED `/series/observations`.

    `fetch_series` returns the CURRENT FRED vintage; each call captures
    one snapshot of latest revisions. Over multiple daily runs revisions
    surface as new rows distinguished by `vintage_id`. To request a
    specific historical vintage ("what was known on date D"), use
    `fetch_series_at_vintage` — it adds ALFRED `realtime_start`/
    `realtime_end` params so backtest backfill can synthesize the
    point-in-time view that protects against look-ahead bias.
    """

    connector_id: str

    def __init__(
        self,
        *,
        api_key: str,
        fetcher: HttpFetcher,
        clock: Callable[[], datetime],
        connector_id: str = "fred",
    ) -> None:
        if not api_key or not api_key.strip():
            raise ValueError("FRED requires a non-empty api_key (set FRED_API_KEY)")
        self._api_key = api_key.strip()
        self._fetcher = fetcher
        self._clock = clock
        self.connector_id = connector_id

    def fetch_series(
        self, series_id: str, *, since: datetime | None
    ) -> tuple[MacroSeriesObservation, ...]:
        normalized = series_id.strip().upper()
        url = self._base_url(normalized)
        if since is not None:
            url += f"&observation_start={since.date().isoformat()}"
        return self._fetch_and_parse(normalized, url)

    def fetch_series_at_vintage(
        self, series_id: str, *, vintage_date: datetime
    ) -> tuple[MacroSeriesObservation, ...]:
        """Return observations as known on `vintage_date` (ALFRED-style query)."""
        if vintage_date.tzinfo is None:
            raise ValueError("vintage_date must be timezone-aware (set tzinfo)")
        normalized = series_id.strip().upper()
        iso = vintage_date.date().isoformat()
        url = (
            f"{self._base_url(normalized)}" f"&realtime_start={iso}&realtime_end={iso}"
        )
        return self._fetch_and_parse(normalized, url)

    def _base_url(self, series_id_normalized: str) -> str:
        return (
            f"{_OBSERVATIONS_URL}"
            f"?series_id={series_id_normalized}"
            f"&api_key={self._api_key}&file_type=json"
        )

    def _fetch_and_parse(
        self, series_id_normalized: str, url: str
    ) -> tuple[MacroSeriesObservation, ...]:
        response = self._fetcher.get(url, headers={"Accept": "application/json"})
        if response.status_code != 200:
            raise RuntimeError(
                f"FRED fetch for {series_id_normalized} returned HTTP "
                f"{response.status_code}"
            )
        payload = json.loads(response.content)
        observations = payload.get("observations", [])
        results: list[MacroSeriesObservation] = []
        for entry in observations:
            raw_value = entry.get("value", ".")
            value = None if raw_value in {"", "."} else Decimal(str(raw_value))
            as_of = datetime.strptime(entry["date"], "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
            vintage_id = entry.get(
                "realtime_start", payload.get("realtime_start", "unknown")
            )
            digest_seed = (
                f"fred|{series_id_normalized}|{as_of.isoformat()}|"
                f"{raw_value}|{vintage_id}"
            )
            content_hash = sha256(digest_seed.encode("utf-8")).hexdigest()
            results.append(
                MacroSeriesObservation(
                    series_id=series_id_normalized,
                    as_of=as_of,
                    value=value,
                    unit="native",
                    vintage_id=vintage_id,
                    source="fred",
                    content_hash=content_hash,
                )
            )
        return tuple(results)


__all__ = ["FredSeriesConnector"]
