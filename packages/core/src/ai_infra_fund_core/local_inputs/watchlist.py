from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from urllib.parse import urlparse

import yaml


WATCHLIST_PRIORITIES = {"critical", "high", "medium", "low"}
TICKER_PATTERN = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")


@dataclass(frozen=True, slots=True)
class AIEquityWatchlistEntry:
    ticker: str
    company_name: str
    themes: tuple[str, ...]
    sector_tags: tuple[str, ...]
    source_urls: tuple[str, ...]
    priority: str


@dataclass(frozen=True, slots=True)
class AIEquityWatchlist:
    version: int
    entries: tuple[AIEquityWatchlistEntry, ...]


def load_ai_equity_watchlist(path: str | Path) -> AIEquityWatchlist:
    with Path(path).open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    return validate_ai_equity_watchlist(raw)


def validate_ai_equity_watchlist(raw: object) -> AIEquityWatchlist:
    if not isinstance(raw, dict):
        raise ValueError("watchlist YAML must be a mapping")
    version = raw.get("version")
    if version != 1:
        raise ValueError("watchlist version must be 1")
    raw_entries = raw.get("entries")
    if not isinstance(raw_entries, list) or not raw_entries:
        raise ValueError("entries must be a non-empty list")

    entries = tuple(_entry(item, index) for index, item in enumerate(raw_entries, start=1))
    tickers = [entry.ticker for entry in entries]
    if len(tickers) != len(set(tickers)):
        raise ValueError("entries must not contain duplicate ticker values")
    return AIEquityWatchlist(version=version, entries=entries)


def _entry(raw: object, index: int) -> AIEquityWatchlistEntry:
    if not isinstance(raw, dict):
        raise ValueError(f"entry {index} must be a mapping")
    ticker = _required_text(raw, "ticker", index).upper()
    if not TICKER_PATTERN.match(ticker):
        raise ValueError(f"ticker is invalid on entry {index}")
    priority = _required_text(raw, "priority", index).lower()
    if priority not in WATCHLIST_PRIORITIES:
        raise ValueError(f"priority must be one of {sorted(WATCHLIST_PRIORITIES)} on entry {index}")
    source_urls = _text_tuple(raw.get("source_urls"), "source_urls", index, required=False)
    for url in source_urls:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(f"source_urls must contain absolute HTTP(S) URLs on entry {index}")
    return AIEquityWatchlistEntry(
        ticker=ticker,
        company_name=_required_text(raw, "company_name", index),
        themes=_text_tuple(raw.get("themes"), "themes", index, required=True),
        sector_tags=_text_tuple(raw.get("sector_tags"), "sector_tags", index, required=True),
        source_urls=source_urls,
        priority=priority,
    )


def _required_text(raw: dict[str, object], field_name: str, index: int) -> str:
    value = raw.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} is required on entry {index}")
    return value.strip()


def _text_tuple(value: object, field_name: str, index: int, *, required: bool) -> tuple[str, ...]:
    if value is None:
        values: tuple[str, ...] = ()
    elif isinstance(value, list):
        values = tuple(str(item).strip() for item in value if str(item).strip())
    else:
        raise ValueError(f"{field_name} must be a list on entry {index}")
    if required and not values:
        raise ValueError(f"{field_name} must not be empty on entry {index}")
    return values
