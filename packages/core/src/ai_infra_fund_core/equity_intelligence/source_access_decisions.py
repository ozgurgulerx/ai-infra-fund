from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from urllib.parse import urlparse

import yaml


DECISION_STATUSES = frozenset(
    {
        "needs_optional_api_key",
        "deferred_access_blocked",
        "deferred_account_required",
        "deferred_terms_review",
        "deferred_provider_design",
        "deferred_not_in_watchlist",
        "deferred_global_fanout",
        "deferred_unstable_endpoint",
        "deferred_low_value_static_page",
        "restricted_paid_or_subscription",
        "restricted_private_or_account_material",
    }
)
ENV_VAR_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")


@dataclass(frozen=True, slots=True)
class OptionalPublicApiKeyDecision:
    env_var: str
    provider: str
    source_ids: tuple[str, ...]
    decision: str
    notes: str


@dataclass(frozen=True, slots=True)
class SourceAccessDecision:
    source_id: str
    source_name: str
    url: str
    source_family: str
    decision: str
    crawl_enabled: bool
    required_action: str
    notes: str
    secret_env_var: str | None = None


@dataclass(frozen=True, slots=True)
class SourceAccessDecisionRegistry:
    version: int
    optional_public_api_keys: tuple[OptionalPublicApiKeyDecision, ...]
    source_decisions: tuple[SourceAccessDecision, ...]


def load_source_access_decisions(path: str | Path) -> SourceAccessDecisionRegistry:
    with Path(path).open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    return validate_source_access_decisions(raw)


def validate_source_access_decisions(raw: object) -> SourceAccessDecisionRegistry:
    if not isinstance(raw, dict):
        raise ValueError("source access decisions YAML must be a mapping")
    version = raw.get("version")
    if version != 1:
        raise ValueError("source access decisions version must be 1")

    raw_keys = raw.get("optional_public_api_keys")
    if not isinstance(raw_keys, list) or not raw_keys:
        raise ValueError("optional_public_api_keys must be a non-empty list")
    optional_keys = tuple(_optional_key(item, index) for index, item in enumerate(raw_keys, 1))

    raw_decisions = raw.get("source_decisions")
    if not isinstance(raw_decisions, list) or not raw_decisions:
        raise ValueError("source_decisions must be a non-empty list")
    source_decisions = tuple(
        _source_decision(item, index) for index, item in enumerate(raw_decisions, 1)
    )

    env_vars = [item.env_var for item in optional_keys]
    if len(env_vars) != len(set(env_vars)):
        raise ValueError("optional_public_api_keys must not contain duplicate env_var values")

    source_ids = [item.source_id for item in source_decisions]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("source_decisions must not contain duplicate source_id values")

    return SourceAccessDecisionRegistry(
        version=version,
        optional_public_api_keys=optional_keys,
        source_decisions=source_decisions,
    )


def _optional_key(raw: object, index: int) -> OptionalPublicApiKeyDecision:
    if not isinstance(raw, dict):
        raise ValueError(f"optional public API key {index} must be a mapping")
    env_var = _required_text(raw, "env_var", index)
    _require_env_var(env_var, f"optional public API key {index} env_var")
    provider = _required_text(raw, "provider", index)
    source_ids = _text_tuple(raw.get("source_ids"), "source_ids", index)
    decision = _required_text(raw, "decision", index)
    if decision != "approve_to_activate_when_secret_configured":
        raise ValueError(
            f"optional public API key {index} decision must be "
            "'approve_to_activate_when_secret_configured'"
        )
    notes = _required_text(raw, "notes", index)
    return OptionalPublicApiKeyDecision(
        env_var=env_var,
        provider=provider,
        source_ids=source_ids,
        decision=decision,
        notes=notes,
    )


def _source_decision(raw: object, index: int) -> SourceAccessDecision:
    if not isinstance(raw, dict):
        raise ValueError(f"source access decision {index} must be a mapping")
    source_id = _required_text(raw, "source_id", index)
    source_name = _required_text(raw, "source_name", index)
    url = _required_text(raw, "url", index)
    _require_http_url(url, f"source access decision {index} url")
    source_family = _required_text(raw, "source_family", index)
    decision = _required_text(raw, "decision", index)
    if decision not in DECISION_STATUSES:
        raise ValueError(
            f"source access decision {index} decision must be one of "
            f"{sorted(DECISION_STATUSES)}"
        )
    crawl_enabled = raw.get("crawl_enabled")
    if crawl_enabled is not False:
        raise ValueError(f"source access decision {index} crawl_enabled must be false")
    required_action = _required_text(raw, "required_action", index)
    notes = _required_text(raw, "notes", index)
    secret_env_var = raw.get("secret_env_var")
    if secret_env_var is not None:
        if not isinstance(secret_env_var, str) or not secret_env_var.strip():
            raise ValueError(
                f"source access decision {index} secret_env_var must be a non-empty string"
            )
        secret_env_var = secret_env_var.strip()
        _require_env_var(secret_env_var, f"source access decision {index} secret_env_var")
        if decision != "needs_optional_api_key":
            raise ValueError(
                f"source access decision {index} secret_env_var is only valid for "
                "needs_optional_api_key"
            )
    elif decision == "needs_optional_api_key":
        raise ValueError(
            f"source access decision {index} secret_env_var is required for "
            "needs_optional_api_key"
        )
    return SourceAccessDecision(
        source_id=source_id,
        source_name=source_name,
        url=url,
        source_family=source_family,
        decision=decision,
        crawl_enabled=crawl_enabled,
        required_action=required_action,
        notes=notes,
        secret_env_var=secret_env_var,
    )


def _required_text(raw: dict[str, object], field_name: str, index: int) -> str:
    value = raw.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} is required on item {index}")
    return value.strip()


def _text_tuple(value: object, field_name: str, index: int) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{field_name} must be a non-empty list on item {index}")
    values = tuple(str(item).strip() for item in value if str(item).strip())
    if not values:
        raise ValueError(f"{field_name} must contain non-empty strings on item {index}")
    return values


def _require_http_url(url: str, field_name: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"{field_name} must be an absolute HTTP(S) URL")


def _require_env_var(value: str, field_name: str) -> None:
    if not ENV_VAR_PATTERN.match(value):
        raise ValueError(f"{field_name} must be an environment variable name")


__all__ = [
    "DECISION_STATUSES",
    "OptionalPublicApiKeyDecision",
    "SourceAccessDecision",
    "SourceAccessDecisionRegistry",
    "load_source_access_decisions",
    "validate_source_access_decisions",
]
