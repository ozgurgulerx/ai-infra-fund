from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .config import RuntimeSettings


CHECK_OK = "ok"
CHECK_WARN = "warn"
CHECK_FAILED = "failed"


@dataclass(frozen=True, slots=True)
class RuntimeCheck:
    name: str
    status: str
    detail: str
    blocking: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "status": self.status,
            "detail": self.detail,
            "blocking": self.blocking,
        }


@dataclass(frozen=True, slots=True)
class RuntimePreflightReport:
    service: str
    environment: str
    checks: tuple[RuntimeCheck, ...]

    @property
    def ready(self) -> bool:
        return not any(
            check.blocking and check.status == CHECK_FAILED for check in self.checks
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "service": self.service,
            "status": "ready" if self.ready else "not_ready",
            "environment": self.environment,
            "advisory_boundary": {
                "advisory_only": True,
                "manual_journal_only": True,
                "broker_integration": "forbidden",
                "live_order_placement": "forbidden",
                "execution_endpoint": "forbidden",
                "automated_trading": "forbidden",
            },
            "checks": {check.name: check.status for check in self.checks},
            "runtime_checks": [check.to_dict() for check in self.checks],
        }


def build_runtime_preflight(
    settings: RuntimeSettings,
    *,
    service: str,
    database_available: bool | None = None,
    internal_token_configured: bool = False,
    require_internal_token: bool = False,
    require_model_profiles: bool = True,
    require_crawl_user_agent: bool = False,
    env: Mapping[str, str] | None = None,
) -> RuntimePreflightReport:
    source_env = env or {}
    checks = [
        _database_check(database_available),
        _model_profiles_check(
            settings.model_profiles_path, required=require_model_profiles
        ),
        _data_dir_check(settings.data_dir),
        _internal_token_check(
            configured=internal_token_configured,
            required=require_internal_token,
        ),
        _crawl_user_agent_check(
            value=str(source_env.get("SEC_EDGAR_USER_AGENT", "")).strip(),
            required=require_crawl_user_agent,
        ),
        RuntimeCheck(
            name="advisory_boundary",
            status=CHECK_OK,
            detail=(
                "Runtime is advisory/reporting-only: no broker integration, "
                "no live order placement, no execution endpoint, and no "
                "automated trading."
            ),
        ),
        RuntimeCheck(
            name="source_policy",
            status=CHECK_OK,
            detail=(
                "Crawler may use configured public sources only and must not "
                "crawl private documents, paid reports, account portals, or "
                "arbitrary internet sources."
            ),
        ),
    ]
    return RuntimePreflightReport(
        service=_clean_label(service, default="service"),
        environment=_clean_label(settings.environment, default="local"),
        checks=tuple(checks),
    )


def _database_check(database_available: bool | None) -> RuntimeCheck:
    if database_available is None:
        return RuntimeCheck(
            name="database",
            status=CHECK_WARN,
            detail="Database connectivity was not checked in this context.",
        )
    if database_available:
        return RuntimeCheck(
            name="database",
            status=CHECK_OK,
            detail="PostgreSQL accepted the readiness probe.",
        )
    return RuntimeCheck(
        name="database",
        status=CHECK_FAILED,
        detail="Database is unavailable.",
        blocking=True,
    )


def _model_profiles_check(path: str, *, required: bool) -> RuntimeCheck:
    if not path.strip():
        return RuntimeCheck(
            name="model_profiles",
            status=CHECK_FAILED if required else CHECK_WARN,
            detail="AI_INFRA_FUND_MODEL_PROFILES is not configured.",
            blocking=required,
        )
    if Path(path).exists():
        return RuntimeCheck(
            name="model_profiles",
            status=CHECK_OK,
            detail="Model profile routing config is present.",
        )
    return RuntimeCheck(
        name="model_profiles",
        status=CHECK_FAILED if required else CHECK_WARN,
        detail="Model profile routing config is not present at the configured path.",
        blocking=required,
    )


def _data_dir_check(path: str) -> RuntimeCheck:
    if not path.strip():
        return RuntimeCheck(
            name="data_dir",
            status=CHECK_FAILED,
            detail="AI_INFRA_FUND_DATA_DIR is not configured.",
            blocking=True,
        )
    if Path(path).exists():
        return RuntimeCheck(
            name="data_dir",
            status=CHECK_OK,
            detail="Configured data directory exists.",
        )
    return RuntimeCheck(
        name="data_dir",
        status=CHECK_WARN,
        detail="Configured data directory is not present in this runtime context.",
    )


def _internal_token_check(*, configured: bool, required: bool) -> RuntimeCheck:
    if configured:
        return RuntimeCheck(
            name="production_internal_token",
            status=CHECK_OK,
            detail="Internal API token is configured; value is redacted.",
        )
    if required:
        return RuntimeCheck(
            name="production_internal_token",
            status=CHECK_FAILED,
            detail="AI_INFRA_FUND_INTERNAL_TOKEN is required for production.",
            blocking=True,
        )
    return RuntimeCheck(
        name="production_internal_token",
        status=CHECK_WARN,
        detail="Internal API token is not configured; acceptable only outside production.",
    )


def _crawl_user_agent_check(*, value: str, required: bool) -> RuntimeCheck:
    if not required:
        return RuntimeCheck(
            name="crawl_user_agent",
            status=CHECK_WARN,
            detail="Crawl user-agent contact check is not required for this service mode.",
        )
    if not value:
        return RuntimeCheck(
            name="crawl_user_agent",
            status=CHECK_FAILED,
            detail="SEC_EDGAR_USER_AGENT must include a contact email or URL for crawl mode.",
            blocking=True,
        )
    if "@" in value or "http://" in value.lower() or "https://" in value.lower():
        return RuntimeCheck(
            name="crawl_user_agent",
            status=CHECK_OK,
            detail="Crawl user-agent includes operator contact information.",
        )
    return RuntimeCheck(
        name="crawl_user_agent",
        status=CHECK_FAILED,
        detail="SEC_EDGAR_USER_AGENT must include a contact email or URL for crawl mode.",
        blocking=True,
    )


def _clean_label(value: str, *, default: str) -> str:
    text = str(value or "").strip()
    return text or default


__all__ = [
    "CHECK_FAILED",
    "CHECK_OK",
    "CHECK_WARN",
    "RuntimeCheck",
    "RuntimePreflightReport",
    "build_runtime_preflight",
]
