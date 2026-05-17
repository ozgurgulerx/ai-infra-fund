from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse

from ai_infra_fund_core.runtime.config import RuntimeSettings


SettingsProvider = Callable[[], RuntimeSettings]


class ShadowAnalystReviewService(Protocol):
    def review_draft(
        self,
        *,
        draft_id: str,
        decision: str,
        reviewer: str,
        notes: str | None = None,
    ) -> dict[str, object]: ...


class ShadowAnalystReviewRepositoryUnavailable(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class PostgresShadowAnalystReviewService:
    settings_provider: SettingsProvider

    def review_draft(
        self,
        *,
        draft_id: str,
        decision: str,
        reviewer: str,
        notes: str | None = None,
    ) -> dict[str, object]:
        try:
            import psycopg
            from ai_infra_fund_api.repositories.shadow_analyst_reviews import (
                ShadowAnalystReviewRepository,
            )
        except ImportError as error:
            raise ShadowAnalystReviewRepositoryUnavailable(
                "shadow analyst review repository is not configured"
            ) from error

        settings = self.settings_provider()
        with psycopg.connect(settings.database_url) as connection:
            repository = ShadowAnalystReviewRepository(connection)
            return repository.review_draft(
                draft_id=draft_id,
                decision=decision,
                reviewer=reviewer,
                notes=notes,
            )


def register_shadow_analyst_review_routes(
    app: FastAPI,
    *,
    shadow_analyst_review_service: ShadowAnalystReviewService | None,
    settings_provider: SettingsProvider,
) -> None:
    service = shadow_analyst_review_service or PostgresShadowAnalystReviewService(
        settings_provider
    )
    router = APIRouter()

    @router.post("/internal/shadow-analyst/drafts/{draft_id}/review")
    async def review_shadow_analyst_draft(
        draft_id: str,
        request: Request,
    ) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:
            return _error_response(
                "invalid_shadow_draft_review",
                "review payload must be valid JSON",
                422,
            )
        if not isinstance(body, dict):
            return _error_response(
                "invalid_shadow_draft_review",
                "review payload must be a JSON object",
                422,
            )
        decision = body.get("decision")
        reviewer = body.get("reviewer")
        notes = body.get("notes")
        if not isinstance(decision, str) or not isinstance(reviewer, str):
            return _error_response(
                "invalid_shadow_draft_review",
                "decision and reviewer are required",
                422,
            )
        if notes is not None and not isinstance(notes, str):
            return _error_response(
                "invalid_shadow_draft_review",
                "notes must be a string when provided",
                422,
            )
        return _review(
            lambda: service.review_draft(
                draft_id=draft_id,
                decision=decision,
                reviewer=reviewer,
                notes=notes,
            )
        )

    app.include_router(router)


def _review(loader: Callable[[], dict[str, object]]) -> JSONResponse:
    try:
        payload = loader()
    except ShadowAnalystReviewRepositoryUnavailable:
        return _error_response(
            "shadow_draft_review_unavailable",
            "shadow analyst review repository is not configured",
            503,
        )
    except ValueError as error:
        return _error_response(
            "shadow_draft_review_rejected",
            str(error),
            422,
        )
    except Exception:
        return _error_response(
            "shadow_draft_review_failed",
            "shadow analyst draft review could not be recorded",
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
