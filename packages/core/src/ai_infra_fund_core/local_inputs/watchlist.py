from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from urllib.parse import urlparse

import yaml


WATCHLIST_PRIORITIES = {"critical", "high", "medium", "low"}
TICKER_PATTERN = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")

PROVIDER_DATA_CLASSES = {
    "public_market_data",
    "public_evidence",
    "user_portfolio",
    "private_research",
    "run_audit",
    "derived_analytics",
    "secrets",
}


@dataclass(frozen=True, slots=True)
class AIEquityWatchlistEntry:
    ticker: str
    company_name: str
    themes: tuple[str, ...]
    sector_tags: tuple[str, ...]
    source_urls: tuple[str, ...]
    priority: str


@dataclass(frozen=True, slots=True)
class AIEquityProvider:
    source_id: str
    source_name: str
    source_type: str
    base_url: str
    license_label: str
    data_class: str
    reliability_score: float
    requires_secret: bool
    secret_env_var: str | None
    ticker_fanout: bool
    series_fanout: tuple[str, ...]
    theme_fanout: bool
    cik_fanout: bool
    cik_lookup_url: str | None  # only meaningful when cik_fanout=True
    url_templates: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AIEquityWatchlist:
    version: int
    entries: tuple[AIEquityWatchlistEntry, ...]
    providers: tuple[AIEquityProvider, ...] = ()


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

    entries = tuple(
        _entry(item, index) for index, item in enumerate(raw_entries, start=1)
    )
    tickers = [entry.ticker for entry in entries]
    if len(tickers) != len(set(tickers)):
        raise ValueError("entries must not contain duplicate ticker values")

    raw_providers = raw.get("providers")
    if raw_providers is None:
        providers: tuple[AIEquityProvider, ...] = ()
    elif isinstance(raw_providers, list):
        providers = tuple(
            _provider(item, index) for index, item in enumerate(raw_providers, start=1)
        )
        provider_ids = [p.source_id for p in providers]
        if len(provider_ids) != len(set(provider_ids)):
            raise ValueError("providers must not contain duplicate source_id values")
    else:
        raise ValueError("providers must be a list when present")

    return AIEquityWatchlist(version=version, entries=entries, providers=providers)


def _provider(raw: object, index: int) -> AIEquityProvider:
    if not isinstance(raw, dict):
        raise ValueError(f"provider {index} must be a mapping")
    source_id = _required_text(raw, "source_id", index)
    source_name = _required_text(raw, "source_name", index)
    source_type = _required_text(raw, "source_type", index)
    base_url = _required_text(raw, "base_url", index)
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"provider {index} base_url must be an HTTP(S) URL")
    license_label = _required_text(raw, "license_label", index)
    data_class = _required_text(raw, "data_class", index)
    if data_class not in PROVIDER_DATA_CLASSES:
        raise ValueError(
            f"provider {index} data_class must be one of "
            f"{sorted(PROVIDER_DATA_CLASSES)}; got {data_class!r}"
        )
    score_raw = raw.get("reliability_score")
    if not isinstance(score_raw, (int, float)):
        raise ValueError(f"provider {index} reliability_score must be a number")
    reliability_score = float(score_raw)
    if not 0.0 <= reliability_score <= 1.0:
        raise ValueError(
            f"provider {index} reliability_score must be in [0, 1]; "
            f"got {reliability_score}"
        )
    requires_secret = bool(raw.get("requires_secret", False))
    raw_env = raw.get("secret_env_var")
    env_str: str | None = (
        raw_env.strip() if isinstance(raw_env, str) and raw_env.strip() else None
    )
    if requires_secret:
        if env_str is None:
            raise ValueError(
                f"provider {index} secret_env_var must be a non-empty string "
                f"when requires_secret is true"
            )
        secret_env_var: str | None = env_str
    elif raw_env is not None and not isinstance(raw_env, str):
        raise ValueError(
            f"provider {index} secret_env_var must be a string when present"
        )
    else:
        secret_env_var = env_str
    ticker_fanout = bool(raw.get("ticker_fanout", False))
    theme_fanout = bool(raw.get("theme_fanout", False))
    cik_fanout = bool(raw.get("cik_fanout", False))
    raw_lookup = raw.get("cik_lookup_url")
    lookup_str: str | None = (
        raw_lookup.strip()
        if isinstance(raw_lookup, str) and raw_lookup.strip()
        else None
    )
    if raw_lookup is not None and lookup_str is None:
        raise ValueError(
            f"provider {index} cik_lookup_url must be a non-empty string when present"
        )
    cik_lookup_url: str | None = lookup_str
    series_fanout = _text_tuple(
        raw.get("series_fanout"), "series_fanout", index, required=False
    )
    url_templates = _text_tuple(
        raw.get("url_templates"), "url_templates", index, required=True
    )

    fanout_flags = [
        ("ticker_fanout", ticker_fanout),
        ("series_fanout", bool(series_fanout)),
        ("theme_fanout", theme_fanout),
        ("cik_fanout", cik_fanout),
    ]
    active = [name for name, flag in fanout_flags if flag]
    if len(active) != 1:
        raise ValueError(
            f"provider {index} must declare exactly one fanout dimension "
            f"(ticker_fanout, series_fanout, theme_fanout, or cik_fanout); got {active}"
        )

    if ticker_fanout and not all("{ticker}" in t for t in url_templates):
        raise ValueError(
            f"provider {index} declares ticker_fanout but a url_template "
            f"is missing the {{ticker}} placeholder"
        )
    if series_fanout and not all("{series_id}" in t for t in url_templates):
        raise ValueError(
            f"provider {index} declares series_fanout but a url_template "
            f"is missing the {{series_id}} placeholder"
        )
    if theme_fanout and not all("{theme}" in t for t in url_templates):
        raise ValueError(
            f"provider {index} declares theme_fanout but a url_template "
            f"is missing the {{theme}} placeholder"
        )
    if cik_fanout and not all("{cik}" in t for t in url_templates):
        raise ValueError(
            f"provider {index} declares cik_fanout but a url_template "
            f"is missing the {{cik}} placeholder"
        )

    return AIEquityProvider(
        source_id=source_id,
        source_name=source_name,
        source_type=source_type,
        base_url=base_url,
        license_label=license_label,
        data_class=data_class,
        reliability_score=reliability_score,
        requires_secret=requires_secret,
        secret_env_var=secret_env_var,
        ticker_fanout=ticker_fanout,
        series_fanout=series_fanout,
        theme_fanout=theme_fanout,
        cik_fanout=cik_fanout,
        cik_lookup_url=cik_lookup_url,
        url_templates=url_templates,
    )


def _entry(raw: object, index: int) -> AIEquityWatchlistEntry:
    if not isinstance(raw, dict):
        raise ValueError(f"entry {index} must be a mapping")
    ticker = _required_text(raw, "ticker", index).upper()
    if not TICKER_PATTERN.match(ticker):
        raise ValueError(f"ticker is invalid on entry {index}")
    priority = _required_text(raw, "priority", index).lower()
    if priority not in WATCHLIST_PRIORITIES:
        raise ValueError(
            f"priority must be one of {sorted(WATCHLIST_PRIORITIES)} on entry {index}"
        )
    source_urls = _text_tuple(
        raw.get("source_urls"), "source_urls", index, required=False
    )
    for url in source_urls:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(
                f"source_urls must contain absolute HTTP(S) URLs on entry {index}"
            )
    return AIEquityWatchlistEntry(
        ticker=ticker,
        company_name=_required_text(raw, "company_name", index),
        themes=_text_tuple(raw.get("themes"), "themes", index, required=True),
        sector_tags=_text_tuple(
            raw.get("sector_tags"), "sector_tags", index, required=True
        ),
        source_urls=source_urls,
        priority=priority,
    )


def _required_text(raw: dict[str, object], field_name: str, index: int) -> str:
    value = raw.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} is required on entry {index}")
    return value.strip()


def _text_tuple(
    value: object, field_name: str, index: int, *, required: bool
) -> tuple[str, ...]:
    if value is None:
        values: tuple[str, ...] = ()
    elif isinstance(value, list):
        values = tuple(str(item).strip() for item in value if str(item).strip())
    else:
        raise ValueError(f"{field_name} must be a list on entry {index}")
    if required and not values:
        raise ValueError(f"{field_name} must not be empty on entry {index}")
    return values
