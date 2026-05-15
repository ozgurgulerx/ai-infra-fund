from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ai_infra_fund_api.routes.advisory_chain import (
    AdvisoryChainReadRepository,
    register_advisory_chain_routes,
)
from ai_infra_fund_api.routes.agent_bootstrap import (
    register_agent_bootstrap_routes,
)
from ai_infra_fund_api.routes.backtests import (
    BacktestRequestService,
    register_backtest_routes,
)
from ai_infra_fund_api.routes.crawl import (
    CrawlActivityRepository,
    register_crawl_routes,
)
from ai_infra_fund_api.routes.dashboard import (
    DashboardReadRepository,
    register_dashboard_routes,
)
from ai_infra_fund_api.routes.events import (
    ExperimentEventsReadRepository,
    register_events_routes,
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
from ai_infra_fund_api.routes.shadow_portfolio import (
    ShadowPortfolioService,
    register_shadow_portfolio_routes,
)
from ai_infra_fund_api.routes.trade_journal import (
    TradeJournalPersistenceRepository,
    register_trade_journal_routes,
)
from ai_infra_fund_core.runtime.config import RuntimeConfigError, RuntimeSettings
from ai_infra_fund_core.runtime.database import check_database_connection


PROJECT_NAME = "ai-infra-fund"
SERVICE_NAME = "api"
VERSION = "0.1.0"
LOCAL_WEB_ORIGINS = ("http://localhost:3000", "http://127.0.0.1:3000")
CORS_ORIGINS_ENV = "AI_INFRA_FUND_CORS_ORIGINS"
INTERNAL_TOKEN_ENV = "AI_INFRA_FUND_INTERNAL_TOKEN"
INTERNAL_TOKEN_HEADER = "X-Internal-Token"
INTERNAL_PATH_PREFIX = "/internal/"


class InternalTokenAuthMiddleware(BaseHTTPMiddleware):
    """Require ``X-Internal-Token`` on ``/internal/*`` paths when configured.

    When ``token`` is falsy the middleware is a no-op — intended only for local
    dev. Production deployments must set ``AI_INFRA_FUND_INTERNAL_TOKEN``.
    """

    def __init__(self, app, *, token: str | None) -> None:
        super().__init__(app)
        self._token = token or None

    async def dispatch(self, request: Request, call_next):
        if (
            self._token is not None
            and request.url.path.startswith(INTERNAL_PATH_PREFIX)
            and request.method != "OPTIONS"
        ):
            if request.headers.get(INTERNAL_TOKEN_HEADER) != self._token:
                return JSONResponse(
                    status_code=401,
                    content={
                        "error": {
                            "code": "unauthorized",
                            "message": (
                                f"valid {INTERNAL_TOKEN_HEADER} header required"
                            ),
                        }
                    },
                )
        return await call_next(request)


REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_AGENT_SKILL_PATH = REPO_ROOT / "docs" / "agent" / "SKILL.md"
DEFAULT_AGENT_OPENAPI_YAML_PATH = REPO_ROOT / "docs" / "api" / "openapi.yaml"

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


def configured_web_origins(
    env: dict[str, str] | os._Environ[str] = os.environ,
) -> tuple[str, ...]:
    configured_origins = tuple(
        origin.strip().rstrip("/")
        for origin in env.get(CORS_ORIGINS_ENV, "").split(",")
        if origin.strip()
    )
    return tuple(dict.fromkeys((*LOCAL_WEB_ORIGINS, *configured_origins)))


def create_app(
    *,
    connection_check: ConnectionCheck = check_database_connection,
    settings_provider: SettingsProvider = default_settings_provider,
    web_origins: tuple[str, ...] | None = None,
    evidence_repository: ManualEvidenceRepository | None = None,
    evaluation_repository: EvaluationPersistenceRepository | None = None,
    recommendation_service: RecommendationService | None = None,
    dashboard_repository: DashboardReadRepository | None = None,
    crawl_activity_repository: CrawlActivityRepository | None = None,
    advisory_chain_repository: AdvisoryChainReadRepository | None = None,
    run_repository: RunReadRepository | None = None,
    trade_journal_repository: TradeJournalPersistenceRepository | None = None,
    events_repository: ExperimentEventsReadRepository | None = None,
    backtest_request_service: BacktestRequestService | None = None,
    shadow_portfolio_service: ShadowPortfolioService | None = None,
    agent_skill_path: Path | None = None,
    agent_openapi_yaml_path: Path | None = None,
    internal_token: str | None | object = ...,
) -> FastAPI:
    app = FastAPI(title="AI Infrastructure Fund API", version=VERSION)
    resolved_internal_token = _resolve_internal_token(internal_token)
    app.add_middleware(
        InternalTokenAuthMiddleware,
        token=resolved_internal_token,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(web_origins or configured_web_origins()),
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
    register_crawl_routes(
        app,
        crawl_activity_repository=crawl_activity_repository,
        settings_provider=settings_provider,
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
    register_trade_journal_routes(
        app,
        trade_journal_repository=trade_journal_repository,
        settings_provider=settings_provider,
    )
    register_events_routes(
        app,
        events_repository=events_repository,
        settings_provider=settings_provider,
    )
    register_backtest_routes(
        app,
        backtest_request_service=backtest_request_service,
        settings_provider=settings_provider,
    )
    register_shadow_portfolio_routes(
        app,
        shadow_portfolio_service=shadow_portfolio_service,
        settings_provider=settings_provider,
    )
    resolved_skill_path = agent_skill_path or DEFAULT_AGENT_SKILL_PATH
    resolved_openapi_yaml_path = (
        agent_openapi_yaml_path or DEFAULT_AGENT_OPENAPI_YAML_PATH
    )
    register_agent_bootstrap_routes(
        app,
        skill_path_provider=lambda: resolved_skill_path,
        openapi_yaml_path_provider=lambda: resolved_openapi_yaml_path,
    )

    return app


def _resolve_internal_token(internal_token: str | None | object) -> str | None:
    token_value = (
        os.environ.get(INTERNAL_TOKEN_ENV) if internal_token is ... else internal_token
    )
    token = token_value.strip() if isinstance(token_value, str) else None
    environment = os.environ.get("AI_INFRA_FUND_ENV", "").strip().lower()
    if environment in {"production", "prod"} and not token:
        raise RuntimeError(
            f"{INTERNAL_TOKEN_ENV} is required when AI_INFRA_FUND_ENV=production"
        )
    return token or None


app = create_app()


def main() -> None:
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("ai_infra_fund_api.main:app", host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
