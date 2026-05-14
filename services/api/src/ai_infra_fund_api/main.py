from __future__ import annotations

import os
from typing import Callable

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ai_infra_fund_api.routes.advisory_chain import (
    AdvisoryChainReadRepository,
    register_advisory_chain_routes,
)
from ai_infra_fund_api.routes.dashboard import (
    DashboardReadRepository,
    register_dashboard_routes,
)
from ai_infra_fund_api.routes.evidence import (
    ManualEvidenceRepository,
    register_evidence_routes,
)
from ai_infra_fund_api.routes.evaluation import (
    EvaluationPersistenceRepository,
    register_evaluation_routes,
)
from ai_infra_fund_api.routes.recommendations import (
    RecommendationService,
    register_recommendation_routes,
)
from ai_infra_fund_api.routes.runs import (
    RunReadRepository,
    register_run_routes,
)
from ai_infra_fund_core.runtime.config import RuntimeConfigError, RuntimeSettings
from ai_infra_fund_core.runtime.database import check_database_connection


PROJECT_NAME = "ai-infra-fund"
SERVICE_NAME = "api"
VERSION = "0.1.0"
LOCAL_WEB_ORIGINS = ("http://localhost:3000", "http://127.0.0.1:3000")

ConnectionCheck = Callable[[RuntimeSettings], bool]
SettingsProvider = Callable[[], RuntimeSettings]


def data_response(payload: dict[str, object], status_code: int = 200) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"data": payload})


def error_response(code: str, message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


def default_settings_provider() -> RuntimeSettings:
    return RuntimeSettings.from_env(os.environ, allow_defaults=True)


def create_app(
    *,
    connection_check: ConnectionCheck = check_database_connection,
    settings_provider: SettingsProvider = default_settings_provider,
    evidence_repository: ManualEvidenceRepository | None = None,
    evaluation_repository: EvaluationPersistenceRepository | None = None,
    recommendation_service: RecommendationService | None = None,
    dashboard_repository: DashboardReadRepository | None = None,
    advisory_chain_repository: AdvisoryChainReadRepository | None = None,
    run_repository: RunReadRepository | None = None,
) -> FastAPI:
    app = FastAPI(title="AI Infrastructure Fund API", version=VERSION)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(LOCAL_WEB_ORIGINS),
        allow_credentials=False,
        allow_methods=["GET", "OPTIONS"],
        allow_headers=["Content-Type"],
    )

    @app.get("/health")
    def health() -> JSONResponse:
        return data_response({"service": SERVICE_NAME, "status": "ok"})

    @app.get("/version")
    def version() -> JSONResponse:
        return data_response(
            {
                "project": PROJECT_NAME,
                "service": SERVICE_NAME,
                "version": VERSION,
            }
        )

    @app.get("/ready")
    def ready() -> JSONResponse:
        try:
            settings = settings_provider()
        except RuntimeConfigError as error:
            return error_response("readiness_failed", str(error), 503)

        if not connection_check(settings):
            return error_response("readiness_failed", "database is unavailable", 503)

        return data_response(
            {
                "service": SERVICE_NAME,
                "status": "ready",
                "checks": {"database": "ok"},
            }
        )

    register_evidence_routes(
        app,
        evidence_repository=evidence_repository,
        settings_provider=settings_provider,
    )
    register_evaluation_routes(
        app,
        evaluation_repository=evaluation_repository,
        settings_provider=settings_provider,
    )
    register_recommendation_routes(
        app,
        recommendation_service=recommendation_service,
    )
    register_dashboard_routes(
        app,
        dashboard_repository=dashboard_repository,
        settings_provider=settings_provider,
    )
    register_advisory_chain_routes(
        app,
        advisory_chain_repository=advisory_chain_repository,
        settings_provider=settings_provider,
    )
    register_run_routes(
        app,
        run_repository=run_repository,
        settings_provider=settings_provider,
    )

    return app


app = create_app()


def main() -> None:
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("ai_infra_fund_api.main:app", host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
