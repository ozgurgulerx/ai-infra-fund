"""Config-driven model routing for advisory-only model assistance."""

from .client import (
    ConfiguredModelClient,
    ConfiguredModelClientSettings,
    ModelClientConfigurationError,
    ModelClientResponseError,
)
from .profiles import ModelProfile, ModelProfileCatalog, ModelProfileConfigError, load_model_profiles
from .router import ModelRouteDenied, ModelRouter, ResolvedModelRoute, SHADOW_ANALYST_TASK_ROLES

__all__ = [
    "ConfiguredModelClient",
    "ConfiguredModelClientSettings",
    "ModelProfile",
    "ModelProfileCatalog",
    "ModelClientConfigurationError",
    "ModelClientResponseError",
    "ModelProfileConfigError",
    "ModelRouteDenied",
    "ModelRouter",
    "ResolvedModelRoute",
    "SHADOW_ANALYST_TASK_ROLES",
    "load_model_profiles",
]
