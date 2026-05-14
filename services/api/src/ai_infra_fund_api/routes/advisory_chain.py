from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

from fastapi import APIRouter, FastAPI
from fastapi.responses import JSONResponse

from ai_infra_fund_core.runtime.config import RuntimeSettings


SettingsProvider = Callable[[], RuntimeSettings]


class AdvisoryChainReadRepository(Protocol):
    def get_demo_chain(self) -> dict[str, object]:
        ...


class AdvisoryChainRepositoryUnavailable(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class PostgresAdvisoryChainReadRepository:
    settings_provider: SettingsProvider

    def get_demo_chain(self) -> dict[str, object]:
        try:
            import psycopg
            from ai_infra_fund_api.repositories.advisory_chain import AdvisoryChainRepository
        except ImportError as error:
            raise AdvisoryChainRepositoryUnavailable("advisory chain repository is not configured") from error

        settings = self.settings_provider()
        with psycopg.connect(settings.database_url) as connection:
            return AdvisoryChainRepository(connection).get_demo_chain()


def register_advisory_chain_routes(
    app: FastAPI,
    *,
    advisory_chain_repository: AdvisoryChainReadRepository | None,
    settings_provider: SettingsProvider,
) -> None:
    repository = advisory_chain_repository or PostgresAdvisoryChainReadRepository(settings_provider)
    router = APIRouter()

    @router.get("/internal/advisory-chain/demo")
    def demo_advisory_chain() -> JSONResponse:
        try:
            payload = repository.get_demo_chain()
        except AdvisoryChainRepositoryUnavailable:
            return _error_response(
                "advisory_chain_unavailable",
                "advisory chain repository is not configured",
                503,
            )
        except Exception:
            return _error_response(
                "advisory_chain_read_failed",
                "advisory chain could not be loaded",
                500,
            )

        return _data_response(payload)

    app.include_router(router)


def _data_response(payload: dict[str, object], status_code: int = 200) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"data": payload})


def _error_response(code: str, message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )
