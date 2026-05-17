from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ai_infra_fund_core.contracts.common import DataClass, coerce_enum, require_text

from .profiles import ModelProfile, ModelProfileCatalog, ModelProfileConfigError


LOCAL_ENDPOINT_TYPE = "local"
SHADOW_ANALYST_TASK_ROLES = (
    "segment_impact_analysis",
    "equity_impact_assessment",
    "valuation_context_analysis",
    "risk_regime_analysis",
    "trading_advisory_draft",
    "analyst_brief_draft",
)
SHADOW_ANALYST_ROUTE_FALLBACK_ROLE = "evidence_summary"
SHADOW_ANALYST_TASK_ROLE_ALIASES = {
    role: SHADOW_ANALYST_ROUTE_FALLBACK_ROLE for role in SHADOW_ANALYST_TASK_ROLES
}


class ModelRouteDenied(ValueError):
    """Raised when no configured model may process the requested data classes."""


@dataclass(frozen=True, slots=True)
class ResolvedModelRoute:
    task_role: str
    profile: ModelProfile
    data_classes: tuple[DataClass, ...]
    fallback_chain: tuple[ModelProfile, ...]


class ModelRouter:
    def __init__(self, catalog: ModelProfileCatalog) -> None:
        self._catalog = catalog

    def resolve(
        self,
        task_role: str,
        *,
        data_classes: Iterable[DataClass | str],
    ) -> ResolvedModelRoute:
        role = require_text(task_role, "task_role")
        requested_classes = _coerce_data_classes(data_classes)
        if DataClass.SECRETS in requested_classes:
            raise ModelRouteDenied(f"{role} cannot process secrets")

        candidates = self._profiles_for_role(role)
        if not candidates:
            raise ModelRouteDenied(f"no model profile is configured for task role: {role}")

        for profile in candidates:
            if self.is_allowed(profile, data_classes=requested_classes):
                return ResolvedModelRoute(
                    task_role=role,
                    profile=profile,
                    data_classes=requested_classes,
                    fallback_chain=self.resolve_fallback_chain(profile.profile_id),
                )

        class_values = ", ".join(item.value for item in requested_classes)
        raise ModelRouteDenied(
            f"no model profile is allowed for task role {role} and data classes: {class_values}"
        )

    def resolve_fallback_chain(self, profile_id: str) -> tuple[ModelProfile, ...]:
        profile = self._catalog.get(profile_id)
        return tuple(self._catalog.get(fallback_id) for fallback_id in profile.fallback_chain)

    def is_allowed(
        self,
        profile: ModelProfile,
        *,
        data_classes: Iterable[DataClass | str],
    ) -> bool:
        requested_classes = _coerce_data_classes(data_classes)
        if DataClass.SECRETS in requested_classes:
            return False
        if DataClass.PRIVATE_RESEARCH in requested_classes and profile.endpoint_type != LOCAL_ENDPOINT_TYPE:
            return False
        return all(data_class in profile.allowed_data_classes for data_class in requested_classes)

    def _profiles_for_role(self, role: str) -> tuple[ModelProfile, ...]:
        candidates = self._catalog.profiles_for_role(role)
        if candidates:
            return candidates
        alias = SHADOW_ANALYST_TASK_ROLE_ALIASES.get(role)
        if alias is None:
            return ()
        return self._catalog.profiles_for_role(alias)


def _coerce_data_classes(data_classes: Iterable[DataClass | str]) -> tuple[DataClass, ...]:
    values = tuple(coerce_enum(item, DataClass, "data_classes") for item in data_classes)
    if not values:
        raise ModelProfileConfigError("data_classes must not be empty")
    return values
