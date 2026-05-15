from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

from fastapi import APIRouter, FastAPI
from fastapi.responses import JSONResponse

from ai_infra_fund_core.runtime.config import RuntimeSettings


SettingsProvider = Callable[[], RuntimeSettings]


class DashboardReadRepository(Protocol):
    def get_status_overview(self) -> dict[str, object]: ...

    def get_status_modules(self) -> dict[str, object]: ...

    def get_evidence_summary(self) -> dict[str, object]: ...

    def get_recommendation_summary(self) -> dict[str, object]: ...

    def get_evaluation_summary(self) -> dict[str, object]: ...

    def get_model_run_summary(self) -> dict[str, object]: ...

    def get_data_quality_summary(self) -> dict[str, object]: ...

    def get_incident_summary(self) -> dict[str, object]: ...

    def get_watchlist_summary(self) -> dict[str, object]: ...

    def get_crawl_frontier_health(self) -> dict[str, object]: ...

    def get_latest_equity_events(self) -> dict[str, object]: ...

    def get_latest_signal_snapshots(self) -> dict[str, object]: ...

    def get_latest_advisory_run(self) -> dict[str, object]: ...

    def get_ticker_intelligence_summary(self, ticker: str) -> dict[str, object]: ...

    def get_portfolio_summary(self) -> dict[str, object]: ...

    def get_latest_recommendations(self, limit: int = 10) -> dict[str, object]: ...


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

    def get_watchlist_summary(self) -> dict[str, object]:
        return self._read("get_watchlist_summary")

    def get_crawl_frontier_health(self) -> dict[str, object]:
        return self._read("get_crawl_frontier_health")

    def get_latest_equity_events(self) -> dict[str, object]:
        return self._read("get_latest_equity_events")

    def get_latest_signal_snapshots(self) -> dict[str, object]:
        return self._read("get_latest_signal_snapshots")

    def get_latest_advisory_run(self) -> dict[str, object]:
        return self._read("get_latest_advisory_run")

    def get_ticker_intelligence_summary(self, ticker: str) -> dict[str, object]:
        return self._read_with_argument(
            "get_ticker_intelligence_summary", ticker.upper()
        )

    def get_portfolio_summary(self) -> dict[str, object]:
        return self._read("get_portfolio_summary")

    def get_latest_recommendations(self, limit: int = 10) -> dict[str, object]:
        return self._read_with_argument("get_latest_recommendations", limit)

    def _read(self, method_name: str) -> dict[str, object]:
        try:
            import psycopg
            from ai_infra_fund_api.repositories.dashboard import DashboardRepository
        except ImportError as error:
            raise DashboardRepositoryUnavailable(
                "dashboard repository is not configured"
            ) from error

        settings = self.settings_provider()
        with psycopg.connect(settings.database_url) as connection:
            repository = DashboardRepository(connection)
            read_method = getattr(repository, method_name)
            return read_method()

    def _read_with_argument(
        self, method_name: str, argument: object
    ) -> dict[str, object]:
        try:
            import psycopg
            from ai_infra_fund_api.repositories.dashboard import DashboardRepository
        except ImportError as error:
            raise DashboardRepositoryUnavailable(
                "dashboard repository is not configured"
            ) from error

        settings = self.settings_provider()
        with psycopg.connect(settings.database_url) as connection:
            repository = DashboardRepository(connection)
            read_method = getattr(repository, method_name)
            return read_method(argument)


def register_dashboard_routes(
    app: FastAPI,
    *,
    dashboard_repository: DashboardReadRepository | None,
    settings_provider: SettingsProvider,
) -> None:
    repository = dashboard_repository or PostgresDashboardReadRepository(
        settings_provider
    )
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

    @router.get("/internal/dashboard/watchlist-summary")
    def watchlist_summary() -> JSONResponse:
        return _read_summary(repository.get_watchlist_summary)

    @router.get("/internal/dashboard/crawl-frontier-health")
    def crawl_frontier_health() -> JSONResponse:
        return _read_summary(repository.get_crawl_frontier_health)

    @router.get("/internal/dashboard/latest-equity-events")
    def latest_equity_events() -> JSONResponse:
        return _read_summary(repository.get_latest_equity_events)

    @router.get("/internal/dashboard/latest-signal-snapshots")
    def latest_signal_snapshots() -> JSONResponse:
        return _read_summary(repository.get_latest_signal_snapshots)

    @router.get("/internal/dashboard/latest-advisory-run")
    def latest_advisory_run() -> JSONResponse:
        return _read_summary(repository.get_latest_advisory_run)

    @router.get("/internal/dashboard/ticker-intelligence/{ticker}")
    def ticker_intelligence(ticker: str) -> JSONResponse:
        return _read_summary(
            lambda: repository.get_ticker_intelligence_summary(ticker.upper())
        )

    @router.get("/internal/dashboard/portfolio-summary")
    def portfolio_summary() -> JSONResponse:
        return _read_summary(repository.get_portfolio_summary)

    @router.get("/internal/dashboard/latest-recommendations")
    def latest_recommendations(limit: int = 10) -> JSONResponse:
        bounded = max(1, min(int(limit), 50))
        return _read_summary(lambda: repository.get_latest_recommendations(bounded))

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
