from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

from fastapi import APIRouter, FastAPI
from fastapi.responses import JSONResponse

from ai_infra_fund_core.runtime.config import RuntimeSettings


SettingsProvider = Callable[[], RuntimeSettings]


class DashboardReadRepository(Protocol):
    def get_status_overview(self) -> dict[str, object]:
        ...

    def get_status_modules(self) -> dict[str, object]:
        ...

    def get_evidence_summary(self) -> dict[str, object]:
        ...

    def get_recommendation_summary(self) -> dict[str, object]:
        ...

    def get_evaluation_summary(self) -> dict[str, object]:
        ...

    def get_model_run_summary(self) -> dict[str, object]:
        ...

    def get_data_quality_summary(self) -> dict[str, object]:
        ...

    def get_incident_summary(self) -> dict[str, object]:
        ...


class DashboardRepositoryUnavailable(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class PostgresDashboardReadRepository:
    settings_provider: SettingsProvider

    def get_status_overview(self) -> dict[str, object]:
        return self._read("get_status_overview")

    def get_status_modules(self) -> dict[str, object]:
        return self._read("get_status_modules")

    def get_evidence_summary(self) -> dict[str, object]:
        return self._read("get_evidence_summary")

    def get_recommendation_summary(self) -> dict[str, object]:
        return self._read("get_recommendation_summary")

    def get_evaluation_summary(self) -> dict[str, object]:
        return self._read("get_evaluation_summary")

    def get_model_run_summary(self) -> dict[str, object]:
        return self._read("get_model_run_summary")

    def get_data_quality_summary(self) -> dict[str, object]:
        return self._read("get_data_quality_summary")

    def get_incident_summary(self) -> dict[str, object]:
        return self._read("get_incident_summary")

    def _read(self, method_name: str) -> dict[str, object]:
        try:
            import psycopg
            from ai_infra_fund_api.repositories.dashboard import DashboardRepository
        except ImportError as error:
            raise DashboardRepositoryUnavailable("dashboard repository is not configured") from error

        settings = self.settings_provider()
        with psycopg.connect(settings.database_url) as connection:
            repository = DashboardRepository(connection)
            read_method = getattr(repository, method_name)
            return read_method()


def register_dashboard_routes(
    app: FastAPI,
    *,
    dashboard_repository: DashboardReadRepository | None,
    settings_provider: SettingsProvider,
) -> None:
    repository = dashboard_repository or PostgresDashboardReadRepository(settings_provider)
    router = APIRouter()

    @router.get("/internal/status/overview")
    def status_overview() -> JSONResponse:
        return _read_summary(repository.get_status_overview)

    @router.get("/internal/status/modules")
    def status_modules() -> JSONResponse:
        return _read_summary(repository.get_status_modules)

    @router.get("/internal/dashboard/evidence-summary")
    def evidence_summary() -> JSONResponse:
        return _read_summary(repository.get_evidence_summary)

    @router.get("/internal/dashboard/recommendation-summary")
    def recommendation_summary() -> JSONResponse:
        return _read_summary(repository.get_recommendation_summary)

    @router.get("/internal/dashboard/evaluation-summary")
    def evaluation_summary() -> JSONResponse:
        return _read_summary(repository.get_evaluation_summary)

    @router.get("/internal/dashboard/model-run-summary")
    def model_run_summary() -> JSONResponse:
        return _read_summary(repository.get_model_run_summary)

    @router.get("/internal/dashboard/data-quality-summary")
    def data_quality_summary() -> JSONResponse:
        return _read_summary(repository.get_data_quality_summary)

    @router.get("/internal/dashboard/incident-summary")
    def incident_summary() -> JSONResponse:
        return _read_summary(repository.get_incident_summary)

    app.include_router(router)


def _read_summary(loader: Callable[[], dict[str, object]]) -> JSONResponse:
    try:
        payload = loader()
    except DashboardRepositoryUnavailable:
        return _error_response(
            "dashboard_unavailable",
            "dashboard repository is not configured",
            503,
        )
    except Exception:
        return _error_response(
            "dashboard_read_failed",
            "dashboard summary could not be loaded",
            500,
        )

    return _data_response(payload)


def _data_response(payload: dict[str, object], status_code: int = 200) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"data": payload})


def _error_response(code: str, message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )
