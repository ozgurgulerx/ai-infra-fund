from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Protocol

from fastapi import APIRouter, FastAPI, Query
from fastapi.responses import JSONResponse

from ai_infra_fund_core.runtime.config import RuntimeSettings


SettingsProvider = Callable[[], RuntimeSettings]


class ExperimentEventsReadRepository(Protocol):
    def list_recent(
        self,
        *,
        limit: int = 50,
        since: datetime | None = None,
    ) -> list[dict[str, object]]: ...

    def list_for_run(
        self, run_id: str, *, limit: int = 200
    ) -> list[dict[str, object]]: ...


class ExperimentEventsRepositoryUnavailable(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class PostgresExperimentEventsReadRepository:
    settings_provider: SettingsProvider

    def list_recent(
        self,
        *,
        limit: int = 50,
        since: datetime | None = None,
    ) -> list[dict[str, object]]:
        return self._read(
            lambda repository: repository.list_recent(limit=limit, since=since)
        )

    def list_for_run(self, run_id: str, *, limit: int = 200) -> list[dict[str, object]]:
        return self._read(
            lambda repository: repository.list_for_run(run_id, limit=limit)
        )

    def _read(
        self,
        reader: Callable[["ExperimentEventsReadRepository"], list[dict[str, object]]],
    ) -> list[dict[str, object]]:
        try:
            import psycopg
            from ai_infra_fund_api.repositories.experiment_events import (
                ExperimentEventRepository,
            )
        except ImportError as error:
            raise ExperimentEventsRepositoryUnavailable(
                "experiment events repository is not configured"
            ) from error

        settings = self.settings_provider()
        with psycopg.connect(settings.database_url) as connection:
            return reader(ExperimentEventRepository(connection))


def register_events_routes(
    app: FastAPI,
    *,
    events_repository: ExperimentEventsReadRepository | None,
    settings_provider: SettingsProvider,
) -> None:
    repository = events_repository or PostgresExperimentEventsReadRepository(
        settings_provider
    )
    router = APIRouter()

    @router.get("/internal/events/recent")
    def recent_events(
        limit: int = Query(default=50, ge=1),
        since: datetime | None = Query(default=None),
    ) -> JSONResponse:
        bounded_limit = min(max(limit, 1), 500)
        try:
            events = repository.list_recent(limit=bounded_limit, since=since)
        except ExperimentEventsRepositoryUnavailable:
            return _error_response(
                "events_unavailable",
                "experiment events repository is not configured",
                503,
            )
        except Exception:
            return _error_response(
                "events_read_failed",
                "experiment events could not be loaded",
                500,
            )
        return _data_response({"events": events, "count": len(events)})

    @router.get("/internal/events/by-run/{run_id}")
    def for_run_events(
        run_id: str,
        limit: int = Query(default=200, ge=1),
    ) -> JSONResponse:
        bounded_limit = min(max(limit, 1), 500)
        try:
            events = repository.list_for_run(run_id, limit=bounded_limit)
        except ExperimentEventsRepositoryUnavailable:
            return _error_response(
                "events_unavailable",
                "experiment events repository is not configured",
                503,
            )
        except Exception:
            return _error_response(
                "events_read_failed",
                "experiment events could not be loaded",
                500,
            )
        return _data_response({"events": events, "count": len(events)})

    app.include_router(router)


def _data_response(payload: dict[str, object], status_code: int = 200) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"data": payload})


def _error_response(code: str, message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


__all__ = ["ExperimentEventsReadRepository", "register_events_routes"]
