from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

from fastapi import APIRouter, FastAPI
from fastapi.responses import JSONResponse

from ai_infra_fund_core.runtime.config import RuntimeSettings


SettingsProvider = Callable[[], RuntimeSettings]


class OutcomeJournalReadRepository(Protocol):
    def get_latest_outcomes(self) -> dict[str, object]: ...


class OutcomeJournalRepositoryUnavailable(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class PostgresOutcomeJournalReadRepository:
    settings_provider: SettingsProvider

    def get_latest_outcomes(self) -> dict[str, object]:
        try:
            import psycopg
            from ai_infra_fund_api.repositories.outcome_journal import (
                OutcomeJournalRepository,
            )
        except ImportError as error:
            raise OutcomeJournalRepositoryUnavailable(
                "outcome journal repository is not configured"
            ) from error

        settings = self.settings_provider()
        with psycopg.connect(settings.database_url) as connection:
            return OutcomeJournalRepository(connection).get_latest_outcomes()


def register_outcome_journal_routes(
    app: FastAPI,
    *,
    outcome_journal_repository: OutcomeJournalReadRepository | None,
    settings_provider: SettingsProvider,
) -> None:
    repository = outcome_journal_repository or PostgresOutcomeJournalReadRepository(
        settings_provider
    )
    router = APIRouter()

    @router.get("/internal/outcome-journal/latest")
    def latest_outcome_journal() -> JSONResponse:
        try:
            payload = repository.get_latest_outcomes()
        except OutcomeJournalRepositoryUnavailable:
            return _error_response(
                "outcome_journal_unavailable",
                "outcome journal repository is not configured",
                503,
            )
        except Exception:
            return _error_response(
                "outcome_journal_read_failed",
                "outcome journal data could not be loaded",
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
