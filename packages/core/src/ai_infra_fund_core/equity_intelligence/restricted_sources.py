from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from urllib.parse import urlparse

import yaml


RESTRICTION_TYPES = frozenset(
    {
        "api_key_required",
        "account_required",
        "paid_subscription",
        "licensed_data",
        "login_gated",
        "terms_review_required",
        "uncertain_verify_first",
    }
)
DEFAULT_ACTION = "do_not_crawl"
ALLOWED_FIELDS = frozenset(
    {
        "source_id",
        "source_name",
        "url",
        "source_family",
        "restriction_type",
        "default_action",
        "crawl_enabled",
        "notes",
        "secret_env_var",
    }
)
SECRET_FIELD_NAMES = frozenset(
    {
        "api_key",
        "api_token",
        "token",
        "password",
        "secret",
        "client_secret",
        "credential",
    }
)
ENV_VAR_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")


@dataclass(frozen=True, slots=True)
class RestrictedInferenceSource:
    source_id: str
    source_name: str
    url: str
    source_family: str
    restriction_type: str
    default_action: str
    crawl_enabled: bool
    notes: str
    secret_env_var: str | None = None


@dataclass(frozen=True, slots=True)
class RestrictedInferenceSourceRegistry:
    version: int
    sources: tuple[RestrictedInferenceSource, ...]


def load_restricted_inference_sources(
    path: str | Path,
) -> RestrictedInferenceSourceRegistry:
    with Path(path).open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    return validate_restricted_inference_sources(raw)


def validate_restricted_inference_sources(
    raw: object,
) -> RestrictedInferenceSourceRegistry:
    if not isinstance(raw, dict):
        raise ValueError("restricted inference sources YAML must be a mapping")
    version = raw.get("version")
    if version != 1:
        raise ValueError("restricted inference sources version must be 1")
    raw_sources = raw.get("sources")
    if not isinstance(raw_sources, list) or not raw_sources:
        raise ValueError("sources must be a non-empty list")

    sources = tuple(_source(item, index) for index, item in enumerate(raw_sources, 1))
    source_ids = [source.source_id for source in sources]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("restricted sources must not contain duplicate source_id values")
    return RestrictedInferenceSourceRegistry(version=version, sources=sources)


def _source(raw: object, index: int) -> RestrictedInferenceSource:
    if not isinstance(raw, dict):
        raise ValueError(f"restricted source {index} must be a mapping")
    _reject_secret_fields(raw, index)
    unknown_fields = set(raw) - ALLOWED_FIELDS
    if unknown_fields:
        raise ValueError(
            f"restricted source {index} has unsupported fields: {sorted(unknown_fields)}"
        )

    source_id = _required_text(raw, "source_id", index)
    source_name = _required_text(raw, "source_name", index)
    url = _required_text(raw, "url", index)
    _require_http_url(url, f"restricted source {index} url")
    source_family = _required_text(raw, "source_family", index)

    restriction_type = _required_text(raw, "restriction_type", index)
    if restriction_type not in RESTRICTION_TYPES:
        raise ValueError(
            f"restricted source {index} restriction_type must be one of "
            f"{sorted(RESTRICTION_TYPES)}"
        )

    default_action = _required_text(raw, "default_action", index)
    if default_action != DEFAULT_ACTION:
        raise ValueError(
            f"restricted source {index} default_action must be {DEFAULT_ACTION!r}"
        )

    crawl_enabled = raw.get("crawl_enabled")
    if crawl_enabled is not False:
        raise ValueError(f"restricted source {index} crawl_enabled must be false")

    notes = _required_text(raw, "notes", index)
    secret_env_var = _optional_secret_env_var(raw.get("secret_env_var"), index)

    return RestrictedInferenceSource(
        source_id=source_id,
        source_name=source_name,
        url=url,
        source_family=source_family,
        restriction_type=restriction_type,
        default_action=default_action,
        crawl_enabled=crawl_enabled,
        notes=notes,
        secret_env_var=secret_env_var,
    )


def _reject_secret_fields(raw: dict[object, object], index: int) -> None:
    for key in raw:
        key_text = str(key).strip().lower()
        if key_text in SECRET_FIELD_NAMES:
            raise ValueError(
                f"restricted source {index} must not contain secret field {key!r}"
            )


def _required_text(raw: dict[object, object], field_name: str, index: int) -> str:
    value = raw.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} is required on restricted source {index}")
    return value.strip()


def _optional_secret_env_var(value: object, index: int) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"secret_env_var must be a non-empty string on restricted source {index}"
        )
    normalized = value.strip()
    if not ENV_VAR_PATTERN.match(normalized):
        raise ValueError(
            f"secret_env_var must be an environment variable name on restricted source {index}"
        )
    return normalized


def _require_http_url(url: str, field_name: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"{field_name} must be an absolute HTTP(S) URL")


__all__ = [
    "DEFAULT_ACTION",
    "RESTRICTION_TYPES",
    "RestrictedInferenceSource",
    "RestrictedInferenceSourceRegistry",
    "load_restricted_inference_sources",
    "validate_restricted_inference_sources",
]
