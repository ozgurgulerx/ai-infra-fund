from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

from fastapi import APIRouter, FastAPI
from fastapi.responses import JSONResponse

from ai_infra_fund_core.runtime.config import RuntimeSettings


SettingsProvider = Callable[[], RuntimeSettings]


class AdvisoryWorkstationReadRepository(Protocol):
    def get_latest_source_signals(self) -> dict[str, object]: ...

    def get_latest_market_events(self) -> dict[str, object]: ...

    def get_market_events_for_ticker(self, ticker: str) -> dict[str, object]: ...

    def get_latest_analyst_brief(self) -> dict[str, object]: ...

    def get_latest_trading_advisory(self) -> dict[str, object]: ...

    def get_ticker_analyst_summary(self, ticker: str) -> dict[str, object]: ...


class AdvisoryWorkstationRepositoryUnavailable(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class PostgresAdvisoryWorkstationReadRepository:
    settings_provider: SettingsProvider

    def get_latest_source_signals(self) -> dict[str, object]:
        return self._read("get_latest_source_signals")

    def get_latest_market_events(self) -> dict[str, object]:
        return self._read("get_latest_market_events")

    def get_market_events_for_ticker(self, ticker: str) -> dict[str, object]:
        return self._read_with_argument("get_market_events_for_ticker", ticker.upper())

    def get_latest_analyst_brief(self) -> dict[str, object]:
        return self._read("get_latest_analyst_brief")

    def get_latest_trading_advisory(self) -> dict[str, object]:
        return self._read("get_latest_trading_advisory")

    def get_ticker_analyst_summary(self, ticker: str) -> dict[str, object]:
        return self._read_with_argument("get_ticker_analyst_summary", ticker.upper())

    def _read(self, method_name: str) -> dict[str, object]:
        try:
            import psycopg
            from ai_infra_fund_api.repositories.advisory_workstation import (
                AdvisoryWorkstationRepository,
            )
        except ImportError as error:
            raise AdvisoryWorkstationRepositoryUnavailable(
                "advisory workstation repository is not configured"
            ) from error

        settings = self.settings_provider()
        with psycopg.connect(settings.database_url) as connection:
            repository = AdvisoryWorkstationRepository(connection)
            read_method = getattr(repository, method_name)
            return read_method()

    def _read_with_argument(
        self, method_name: str, argument: object
    ) -> dict[str, object]:
        try:
            import psycopg
            from ai_infra_fund_api.repositories.advisory_workstation import (
                AdvisoryWorkstationRepository,
            )
        except ImportError as error:
            raise AdvisoryWorkstationRepositoryUnavailable(
                "advisory workstation repository is not configured"
            ) from error

        settings = self.settings_provider()
        with psycopg.connect(settings.database_url) as connection:
            repository = AdvisoryWorkstationRepository(connection)
            read_method = getattr(repository, method_name)
            return read_method(argument)


def register_advisory_workstation_routes(
    app: FastAPI,
    *,
    advisory_workstation_repository: AdvisoryWorkstationReadRepository | None,
    settings_provider: SettingsProvider,
) -> None:
    repository = advisory_workstation_repository or PostgresAdvisoryWorkstationReadRepository(
        settings_provider
    )
    router = APIRouter()

    @router.get("/internal/source-signals/latest")
    def latest_source_signals() -> JSONResponse:
        return _read(repository.get_latest_source_signals)

    @router.get("/internal/market-events/latest")
    def latest_market_events() -> JSONResponse:
        return _read(repository.get_latest_market_events)

    @router.get("/internal/market-events/{ticker}")
    def market_events_for_ticker(ticker: str) -> JSONResponse:
        return _read(lambda: repository.get_market_events_for_ticker(ticker.upper()))

    @router.get("/internal/analyst-brief/latest")
    def latest_analyst_brief() -> JSONResponse:
        return _read(repository.get_latest_analyst_brief)

    @router.get("/internal/trading-advisory/latest")
    def latest_trading_advisory() -> JSONResponse:
        return _read(repository.get_latest_trading_advisory)

    @router.get("/internal/ticker/{ticker}/analyst-summary")
    def ticker_analyst_summary(ticker: str) -> JSONResponse:
        return _read(lambda: repository.get_ticker_analyst_summary(ticker.upper()))

    app.include_router(router)


def _read(loader: Callable[[], dict[str, object]]) -> JSONResponse:
    try:
        payload = loader()
    except AdvisoryWorkstationRepositoryUnavailable:
        return _error_response(
            "advisory_workstation_unavailable",
            "advisory workstation repository is not configured",
            503,
        )
    except Exception:
        return _error_response(
            "advisory_workstation_read_failed",
            "advisory workstation data could not be loaded",
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
