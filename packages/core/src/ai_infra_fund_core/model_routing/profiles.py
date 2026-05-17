from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml

from ai_infra_fund_core.contracts.common import DataClass, coerce_enum, require_text


REQUIRED_PROFILE_FIELDS = (
    "model_id",
    "deployment",
    "provider",
    "endpoint_type",
    "task_roles",
    "quota_rpm",
    "quota_tpm",
    "cost_class",
    "max_context",
    "privacy_class",
    "allowed_data_classes",
    "fallback_chain",
    "structured_output_support",
    "notes",
)


class ModelProfileConfigError(ValueError):
    """Raised when model profile configuration is missing or unsafe."""


@dataclass(frozen=True, slots=True)
class ModelProfile:
    profile_id: str
    model_id: str
    deployment: str
    provider: str
    endpoint_type: str
    task_roles: tuple[str, ...]
    quota_rpm: int | None
    quota_tpm: int | None
    cost_class: str
    max_context: int | str
    privacy_class: str
    allowed_data_classes: tuple[DataClass, ...]
    fallback_chain: tuple[str, ...]
    structured_output_support: bool
    notes: str
    reasoning_effort: str | None = None


@dataclass(frozen=True, slots=True)
class ModelProfileCatalog:
    profiles: dict[str, ModelProfile]

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any]) -> "ModelProfileCatalog":
        if not isinstance(mapping, Mapping):
            raise ModelProfileConfigError("model profile config must be a mapping")

        models = mapping.get("models")
        if not isinstance(models, Mapping) or not models:
            raise ModelProfileConfigError("model profile config requires non-empty models")

        profiles: dict[str, ModelProfile] = {}
        for profile_id, raw_profile in models.items():
            profile_id_text = require_text(str(profile_id), "profile_id")
            profiles[profile_id_text] = _profile_from_mapping(profile_id_text, raw_profile)

        _validate_fallbacks(profiles)
        return cls(profiles=profiles)

    def get(self, profile_id: str) -> ModelProfile:
        try:
            return self.profiles[profile_id]
        except KeyError as exc:
            raise ModelProfileConfigError(f"unknown model profile: {profile_id}") from exc

    def profiles_for_role(self, task_role: str) -> tuple[ModelProfile, ...]:
        role = require_text(task_role, "task_role")
        return tuple(
            profile
            for profile in self.profiles.values()
            if role in profile.task_roles
        )


def load_model_profiles(path: str | Path) -> ModelProfileCatalog:
    config_path = Path(path)
    try:
        loaded = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ModelProfileConfigError(f"cannot read model profile config: {config_path}") from exc

    return ModelProfileCatalog.from_mapping(loaded)


def _profile_from_mapping(profile_id: str, raw_profile: object) -> ModelProfile:
    if not isinstance(raw_profile, Mapping):
        raise ModelProfileConfigError(f"{profile_id} must be a mapping")

    missing = [field for field in REQUIRED_PROFILE_FIELDS if field not in raw_profile]
    if missing:
        raise ModelProfileConfigError(
            f"{profile_id} missing required fields: {', '.join(missing)}"
        )

    return ModelProfile(
        profile_id=profile_id,
        model_id=_required_string(raw_profile["model_id"], f"{profile_id}.model_id"),
        deployment=_required_string(raw_profile["deployment"], f"{profile_id}.deployment"),
        provider=_required_string(raw_profile["provider"], f"{profile_id}.provider"),
        endpoint_type=_required_string(raw_profile["endpoint_type"], f"{profile_id}.endpoint_type"),
        task_roles=_string_tuple(raw_profile["task_roles"], f"{profile_id}.task_roles"),
        quota_rpm=_optional_non_negative_int(raw_profile["quota_rpm"], f"{profile_id}.quota_rpm"),
        quota_tpm=_optional_non_negative_int(raw_profile["quota_tpm"], f"{profile_id}.quota_tpm"),
        cost_class=_required_string(raw_profile["cost_class"], f"{profile_id}.cost_class"),
        max_context=_max_context(raw_profile["max_context"], f"{profile_id}.max_context"),
        privacy_class=_required_string(raw_profile["privacy_class"], f"{profile_id}.privacy_class"),
        allowed_data_classes=_data_class_tuple(
            raw_profile["allowed_data_classes"],
            f"{profile_id}.allowed_data_classes",
        ),
        fallback_chain=_string_tuple(raw_profile["fallback_chain"], f"{profile_id}.fallback_chain", allow_empty=True),
        structured_output_support=_required_bool(
            raw_profile["structured_output_support"],
            f"{profile_id}.structured_output_support",
        ),
        notes=_required_string(raw_profile["notes"], f"{profile_id}.notes"),
        reasoning_effort=_optional_reasoning_effort(
            raw_profile.get("reasoning_effort"),
            f"{profile_id}.reasoning_effort",
        ),
    )


def _required_string(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise ModelProfileConfigError(f"{field_name} must be text")
    return require_text(value, field_name)


def _string_tuple(value: object, field_name: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ModelProfileConfigError(f"{field_name} must be a list")
    items = tuple(_required_string(item, field_name) for item in value)
    if not allow_empty and not items:
        raise ModelProfileConfigError(f"{field_name} must not be empty")
    return items


def _data_class_tuple(value: object, field_name: str) -> tuple[DataClass, ...]:
    raw_items = _string_tuple(value, field_name)
    data_classes = tuple(coerce_enum(item, DataClass, field_name) for item in raw_items)
    if DataClass.SECRETS in data_classes:
        raise ModelProfileConfigError(f"{field_name} must not allow secrets")
    return data_classes


def _optional_non_negative_int(value: object, field_name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ModelProfileConfigError(f"{field_name} must be an integer or null")
    if value < 0:
        raise ModelProfileConfigError(f"{field_name} must be non-negative")
    return value


def _max_context(value: object, field_name: str) -> int | str:
    if isinstance(value, int) and not isinstance(value, bool):
        if value <= 0:
            raise ModelProfileConfigError(f"{field_name} must be positive")
        return value
    if isinstance(value, str):
        return require_text(value, field_name)
    raise ModelProfileConfigError(f"{field_name} must be a positive integer or text")


def _required_bool(value: object, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ModelProfileConfigError(f"{field_name} must be a boolean")
    return value


def _optional_reasoning_effort(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    effort = _required_string(value, field_name).lower()
    if effort not in {"low", "medium", "high"}:
        raise ModelProfileConfigError(
            f"{field_name} must be one of: low, medium, high"
        )
    return effort


def _validate_fallbacks(profiles: dict[str, ModelProfile]) -> None:
    profile_ids = set(profiles)
    for profile in profiles.values():
        unknown = [fallback for fallback in profile.fallback_chain if fallback not in profile_ids]
        if unknown:
            raise ModelProfileConfigError(
                f"{profile.profile_id} references unknown fallback profiles: {', '.join(unknown)}"
            )
