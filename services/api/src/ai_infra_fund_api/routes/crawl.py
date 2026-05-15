from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Protocol

from fastapi import APIRouter, FastAPI
from fastapi.responses import JSONResponse

from ai_infra_fund_core.runtime.config import RuntimeSettings


SettingsProvider = Callable[[], RuntimeSettings]


class CrawlActivityRepository(Protocol):
    def get_crawl_activity_summary(self) -> dict[str, object]: ...


class CrawlActivityRepositoryUnavailable(RuntimeError):
    """Raised when the crawl_logs repository cannot be reached."""


@dataclass(frozen=True, slots=True)
class PostgresCrawlActivityRepository:
    settings_provider: SettingsProvider
    window: timedelta = timedelta(hours=24)

    def get_crawl_activity_summary(self) -> dict[str, object]:
        try:
            import psycopg

            from ai_infra_fund_api.repositories.crawl_logs import CrawlLogRepository
        except ImportError as error:
            raise CrawlActivityRepositoryUnavailable(
                "crawl_logs repository is not configured"
            ) from error

        settings = self.settings_provider()
        with psycopg.connect(settings.database_url) as connection:
            repository = CrawlLogRepository(connection)
            summary = repository.summarize_recent(
                window=self.window,
                now=datetime.now(tz=timezone.utc),
            )
        summary["window_hours"] = int(self.window.total_seconds() // 3600)
        return summary


def register_crawl_routes(
    app: FastAPI,
    *,
    crawl_activity_repository: CrawlActivityRepository | None,
    settings_provider: SettingsProvider,
) -> None:
    repository = crawl_activity_repository or PostgresCrawlActivityRepository(
        settings_provider=settings_provider,
    )
    router = APIRouter()

    @router.get("/internal/dashboard/crawl-activity")
    def crawl_activity() -> JSONResponse:
        try:
            payload = repository.get_crawl_activity_summary()
        except CrawlActivityRepositoryUnavailable:
            return JSONResponse(
                status_code=503,
                content={
                    "error": {
                        "code": "crawl_activity_unavailable",
                        "message": "crawl activity repository is not configured",
                    }
                },
            )
        except Exception:
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "crawl_activity_read_failed",
                        "message": "crawl activity summary could not be loaded",
                    }
                },
            )
        return JSONResponse(status_code=200, content={"data": payload})

    app.include_router(router)


__all__ = [
    "CrawlActivityRepository",
    "CrawlActivityRepositoryUnavailable",
    "PostgresCrawlActivityRepository",
    "register_crawl_routes",
]
