from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Protocol

from fastapi import APIRouter, FastAPI, Query
from fastapi.responses import JSONResponse

from ai_infra_fund_core.portfolio.shadow_simulation import LookaheadError
from ai_infra_fund_core.runtime.config import RuntimeSettings


SettingsProvider = Callable[[], RuntimeSettings]


class ShadowPortfolioService(Protocol):
    def get_drift(self, *, as_of: datetime) -> dict[str, object]: ...

    def get_simulation(
        self, *, as_of: datetime, horizon_days: int
    ) -> dict[str, object]: ...


class ShadowPortfolioServiceUnavailable(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class StubShadowPortfolioService:
    """Read-only stub that surfaces the advisory-only safety chip.

    Real Postgres-backed data wiring is intentionally out of v1 scope.
    The stub guarantees the route remains advisory-labelled and returns
    a deterministic envelope so the frontend can render the chip and an
    empty state without needing seed data.
    """

    settings_provider: SettingsProvider

    def get_drift(self, *, as_of: datetime) -> dict[str, object]:
        return {
            "as_of": as_of.isoformat(),
            "rows": [],
            "advisory_label": "advisory_only",
            "status": "no_target_weights_available",
        }

    def get_simulation(
        self, *, as_of: datetime, horizon_days: int
    ) -> dict[str, object]:
        return {
            "as_of": as_of.isoformat(),
            "horizon_days": horizon_days,
            "curve": [],
            "metrics": {},
            "advisory_label": "advisory_only",
            "status": "no_target_weights_available",
        }


def register_shadow_portfolio_routes(
    app: FastAPI,
    *,
    shadow_portfolio_service: ShadowPortfolioService | None,
    settings_provider: SettingsProvider,
) -> None:
    service = shadow_portfolio_service or StubShadowPortfolioService(settings_provider)
    router = APIRouter()

    @router.get("/internal/shadow-portfolio/drift")
    def shadow_drift(
        as_of: datetime | None = Query(default=None),
    ) -> JSONResponse:
        resolved_as_of = _resolve_as_of(as_of)
        try:
            payload = service.get_drift(as_of=resolved_as_of)
        except LookaheadError as error:
            return _error_response(
                "LOOKAHEAD_VIOLATION",
                str(error),
                422,
            )
        except ShadowPortfolioServiceUnavailable:
            return _error_response(
                "shadow_portfolio_unavailable",
                "shadow portfolio service is not configured",
                503,
            )
        except Exception:
            return _error_response(
                "shadow_portfolio_read_failed",
                "shadow portfolio drift could not be computed",
                500,
            )
        return _data_response(payload)

    @router.get("/internal/shadow-portfolio/simulation")
    def shadow_simulation(
        as_of: datetime | None = Query(default=None),
        horizon_days: int = Query(default=30, ge=1, le=365),
    ) -> JSONResponse:
        resolved_as_of = _resolve_as_of(as_of)
        try:
            payload = service.get_simulation(
                as_of=resolved_as_of, horizon_days=horizon_days
            )
        except LookaheadError as error:
            return _error_response(
                "LOOKAHEAD_VIOLATION",
                str(error),
                422,
            )
        except ShadowPortfolioServiceUnavailable:
            return _error_response(
                "shadow_portfolio_unavailable",
                "shadow portfolio service is not configured",
                503,
            )
        except Exception:
            return _error_response(
                "shadow_portfolio_read_failed",
                "shadow portfolio simulation could not be computed",
                500,
            )
        return _data_response(payload)

    app.include_router(router)


def _resolve_as_of(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _data_response(payload: dict[str, object], status_code: int = 200) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"data": payload})


def _error_response(code: str, message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


__all__ = [
    "ShadowPortfolioService",
    "ShadowPortfolioServiceUnavailable",
    "StubShadowPortfolioService",
    "register_shadow_portfolio_routes",
]
