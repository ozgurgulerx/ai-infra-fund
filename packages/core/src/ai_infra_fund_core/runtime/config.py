from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


DEFAULT_DATABASE_URL = "postgresql://ai_infra_fund:ai_infra_fund@postgres:5432/ai_infra_fund"
DEFAULT_DATA_DIR = "/app/data"
DEFAULT_MODEL_PROFILES = "config/model_profiles.yaml"
DEFAULT_ENVIRONMENT = "local"


class RuntimeConfigError(ValueError):
    """Raised when required runtime configuration is absent or invalid."""


@dataclass(frozen=True)
class RuntimeSettings:
    database_url: str
    data_dir: str
    model_profiles_path: str
    environment: str = DEFAULT_ENVIRONMENT

    @classmethod
    def from_env(
        cls,
        env: Mapping[str, str],
        *,
        allow_defaults: bool = True,
    ) -> "RuntimeSettings":
        database_url = _value(env, "AI_INFRA_FUND_DATABASE_URL")
        data_dir = _value(env, "AI_INFRA_FUND_DATA_DIR")
        model_profiles_path = _value(env, "AI_INFRA_FUND_MODEL_PROFILES")
        environment = _value(env, "AI_INFRA_FUND_ENV")

        if allow_defaults:
            database_url = database_url or DEFAULT_DATABASE_URL
            data_dir = data_dir or DEFAULT_DATA_DIR
            model_profiles_path = model_profiles_path or DEFAULT_MODEL_PROFILES
            environment = environment or DEFAULT_ENVIRONMENT

        missing = [
            name
            for name, value in (
                ("AI_INFRA_FUND_DATABASE_URL", database_url),
                ("AI_INFRA_FUND_DATA_DIR", data_dir),
                ("AI_INFRA_FUND_MODEL_PROFILES", model_profiles_path),
            )
            if not value
        ]
        if missing:
            raise RuntimeConfigError(f"Missing required runtime config: {', '.join(missing)}")

        return cls(
            database_url=database_url,
            data_dir=data_dir,
            model_profiles_path=model_profiles_path,
            environment=environment or DEFAULT_ENVIRONMENT,
        )

    def validate_paths(self, *, require_model_profiles: bool = False) -> None:
        if require_model_profiles and not Path(self.model_profiles_path).exists():
            raise RuntimeConfigError(
                f"Model profile config not found: {self.model_profiles_path}"
            )


def _value(env: Mapping[str, str], key: str) -> str:
    return str(env.get(key, "")).strip()
