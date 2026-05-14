from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Protocol

from fastapi import APIRouter, FastAPI
from fastapi.responses import JSONResponse

from ai_infra_fund_core.runtime.config import RuntimeSettings


SettingsProvider = Callable[[], RuntimeSettings]


class RunReadRepository(Protocol):
    def get_latest_run(self) -> dict[str, object] | None:
        ...

    def get_run(self, run_id: str) -> dict[str, object] | None:
        ...


class RunRepositoryUnavailable(RuntimeError):
    pass


class _RunArtifactRepositoryAdapter(Protocol):
    def get_latest(self, run_type: str | None = None) -> dict[str, object] | None:
        ...

    def get_by_id(self, run_id: str) -> dict[str, object] | None:
        ...


@dataclass(frozen=True, slots=True)
class PostgresRunReadRepository:
    settings_provider: SettingsProvider

    def get_latest_run(self) -> dict[str, object] | None:
        return self._read(lambda repository: repository.get_latest("all"))

    def get_run(self, run_id: str) -> dict[str, object] | None:
        return self._read(lambda repository: repository.get_by_id(run_id))

    def _read(
        self,
        reader: Callable[[_RunArtifactRepositoryAdapter], dict[str, object] | None],
    ) -> dict[str, object] | None:
        try:
            import psycopg
            from ai_infra_fund_api.repositories.run_artifacts import RunArtifactRepository
        except ImportError as error:
            raise RunRepositoryUnavailable("run artifact repository is not configured") from error

        settings = self.settings_provider()
        with psycopg.connect(settings.database_url) as connection:
            return reader(RunArtifactRepository(connection))


def register_run_routes(
    app: FastAPI,
    *,
    run_repository: RunReadRepository | None,
    settings_provider: SettingsProvider,
) -> None:
    repository = run_repository or PostgresRunReadRepository(settings_provider)
    router = APIRouter()

    @router.get("/internal/runs/latest")
    def latest_run() -> JSONResponse:
        return _read_run(repository.get_latest_run)

    @router.get("/internal/runs/{run_id}")
    def get_run(run_id: str) -> JSONResponse:
        return _read_run(lambda: repository.get_run(run_id))

    app.include_router(router)


def _read_run(loader: Callable[[], dict[str, object] | None]) -> JSONResponse:
    try:
        payload = loader()
        if payload is None:
            return _error_response("run_not_found", "run artifact was not found", 404)
        response_payload = _json_object(payload)
    except RunRepositoryUnavailable:
        return _error_response(
            "runs_unavailable",
            "run artifact repository is not configured",
            503,
        )
    except Exception:
        return _error_response(
            "run_read_failed",
            "run artifact could not be loaded",
            500,
        )

    return _data_response(response_payload)


def _json_object(payload: Mapping[str, object]) -> dict[str, object]:
    serialized = _to_jsonable(payload)
    if not isinstance(serialized, dict):
        raise ValueError("run artifact response was invalid")
    return serialized


def _to_jsonable(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(item) for item in value]
    return value


def _data_response(payload: dict[str, object], status_code: int = 200) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"data": payload})


def _error_response(code: str, message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


__all__ = ["RunReadRepository", "register_run_routes"]
