from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import yaml


SOURCE_TIERS = frozenset(
    {
        "tier_0_primary",
        "tier_1_specialist",
        "tier_2_news_api",
        "tier_3_social_attention",
    }
)

SOURCE_DATA_CLASSES = frozenset({"public_evidence", "public_market_data"})
SOURCE_FANOUTS = frozenset({"ticker", "series", "static"})
PRIVATE_OR_SECRET_DATA_CLASSES = frozenset(
    {"private_research", "user_portfolio", "secrets"}
)


@dataclass(frozen=True, slots=True)
class RegistrySource:
    source_id: str
    source_name: str
    tier: str
    source_kind: str
    base_url: str
    license_label: str
    data_class: str
    trust_weight: float
    refresh_interval_minutes: int
    fanout: str
    url_templates: tuple[str, ...]
    requires_secret: bool = False
    secret_env_var: str | None = None
    metadata_only: bool = False
    ticker_allowlist: tuple[str, ...] = ()
    series_ids: tuple[str, ...] = ()
    themes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SourceRegistry:
    version: int
    sources: tuple[RegistrySource, ...]


def load_source_registry(path: str | Path) -> SourceRegistry:
    with Path(path).open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    return validate_source_registry(raw)


def validate_source_registry(raw: object) -> SourceRegistry:
    if not isinstance(raw, dict):
        raise ValueError("source registry YAML must be a mapping")
    version = raw.get("version")
    if version != 1:
        raise ValueError("source registry version must be 1")
    raw_sources = raw.get("sources")
    if not isinstance(raw_sources, list) or not raw_sources:
        raise ValueError("sources must be a non-empty list")

    sources = tuple(_source(item, index) for index, item in enumerate(raw_sources, 1))
    source_ids = [source.source_id for source in sources]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("sources must not contain duplicate source_id values")
    return SourceRegistry(version=version, sources=sources)


def _source(raw: object, index: int) -> RegistrySource:
    if not isinstance(raw, dict):
        raise ValueError(f"source {index} must be a mapping")

    source_id = _required_text(raw, "source_id", index)
    source_name = _required_text(raw, "source_name", index)
    tier = _required_text(raw, "tier", index)
    if tier not in SOURCE_TIERS:
        raise ValueError(f"source {index} tier must be one of {sorted(SOURCE_TIERS)}")

    source_kind = _required_text(raw, "source_kind", index)
    base_url = _required_text(raw, "base_url", index)
    _require_http_url(base_url, f"source {index} base_url")

    license_label = _required_text(raw, "license_label", index)
    data_class = _required_text(raw, "data_class", index)
    if data_class in PRIVATE_OR_SECRET_DATA_CLASSES:
        raise ValueError(
            f"source {index} private/account/secrets data classes are not valid "
            "for public-source crawling"
        )
    if data_class not in SOURCE_DATA_CLASSES:
        raise ValueError(
            f"source {index} data_class must be one of {sorted(SOURCE_DATA_CLASSES)}"
        )

    trust_raw = raw.get("trust_weight")
    if not isinstance(trust_raw, (int, float)):
        raise ValueError(f"source {index} trust_weight must be a number")
    trust_weight = float(trust_raw)
    if not 0.0 <= trust_weight <= 1.0:
        raise ValueError(f"source {index} trust_weight must be in [0, 1]")

    refresh_raw = raw.get("refresh_interval_minutes")
    if not isinstance(refresh_raw, int) or refresh_raw <= 0:
        raise ValueError(
            f"source {index} refresh_interval_minutes must be a positive integer"
        )

    requires_secret = bool(raw.get("requires_secret", False))
    raw_secret = raw.get("secret_env_var")
    secret_env_var = (
        raw_secret.strip()
        if isinstance(raw_secret, str) and raw_secret.strip()
        else None
    )
    if requires_secret and secret_env_var is None:
        raise ValueError(
            f"source {index} secret_env_var is required when requires_secret is true"
        )
    if raw_secret is not None and not isinstance(raw_secret, str):
        raise ValueError(f"source {index} secret_env_var must be a string")

    metadata_only = bool(raw.get("metadata_only", False))
    lowered_license = license_label.lower()
    if (
        any(marker in lowered_license for marker in ("paid", "paywall", "licensed"))
        and "free" not in lowered_license
        and not metadata_only
    ):
        raise ValueError(
            f"source {index} paid/paywalled sources must be metadata_only"
        )

    fanout = _required_text(raw, "fanout", index)
    if fanout not in SOURCE_FANOUTS:
        raise ValueError(f"source {index} fanout must be one of {sorted(SOURCE_FANOUTS)}")

    url_templates = _text_tuple(raw.get("url_templates"), "url_templates", index)
    for template in url_templates:
        _require_http_url(template, f"source {index} url_template")

    ticker_allowlist = tuple(
        ticker.upper()
        for ticker in _optional_text_tuple(raw.get("ticker_allowlist"), "ticker_allowlist", index)
    )
    series_ids = _optional_text_tuple(raw.get("series_ids"), "series_ids", index)
    themes = _optional_text_tuple(raw.get("themes"), "themes", index)

    if fanout == "ticker" and not all(
        _template_has_any(template, ("{ticker}", "{company_name}", "{company_slug}"))
        for template in url_templates
    ):
        raise ValueError(
            f"source {index} ticker fanout requires ticker/company placeholders"
        )
    if fanout == "series":
        if not series_ids:
            raise ValueError(f"source {index} series fanout requires series_ids")
        if not all("{series_id}" in template for template in url_templates):
            raise ValueError(
                f"source {index} series fanout requires {{series_id}} placeholders"
            )
    if fanout == "static" and len(ticker_allowlist) != 1:
        raise ValueError(
            f"source {index} static fanout must bind to exactly one ticker"
        )

    return RegistrySource(
        source_id=source_id,
        source_name=source_name,
        tier=tier,
        source_kind=source_kind,
        base_url=base_url,
        license_label=license_label,
        data_class=data_class,
        trust_weight=trust_weight,
        refresh_interval_minutes=refresh_raw,
        fanout=fanout,
        url_templates=url_templates,
        requires_secret=requires_secret,
        secret_env_var=secret_env_var,
        metadata_only=metadata_only,
        ticker_allowlist=ticker_allowlist,
        series_ids=series_ids,
        themes=themes,
    )


def _required_text(raw: dict[str, object], field_name: str, index: int) -> str:
    value = raw.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} is required on source {index}")
    return value.strip()


def _text_tuple(value: object, field_name: str, index: int) -> tuple[str, ...]:
    values = _optional_text_tuple(value, field_name, index)
    if not values:
        raise ValueError(f"{field_name} must not be empty on source {index}")
    return values


def _optional_text_tuple(
    value: object, field_name: str, index: int
) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list on source {index}")
    return tuple(str(item).strip() for item in value if str(item).strip())


def _require_http_url(url: str, field_name: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"{field_name} must be an absolute HTTP(S) URL")


def _template_has_any(template: str, placeholders: tuple[str, ...]) -> bool:
    return any(placeholder in template for placeholder in placeholders)


__all__ = [
    "RegistrySource",
    "SOURCE_DATA_CLASSES",
    "SOURCE_FANOUTS",
    "SOURCE_TIERS",
    "SourceRegistry",
    "load_source_registry",
    "validate_source_registry",
]
