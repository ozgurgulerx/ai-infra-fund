from __future__ import annotations

from pathlib import Path
from typing import Callable

from fastapi import APIRouter, FastAPI
from fastapi.responses import JSONResponse, Response


SkillPathProvider = Callable[[], Path]
OpenApiYamlPathProvider = Callable[[], Path]


def register_agent_bootstrap_routes(
    app: FastAPI,
    *,
    skill_path_provider: SkillPathProvider,
    openapi_yaml_path_provider: OpenApiYamlPathProvider,
) -> None:
    router = APIRouter()

    @router.get("/internal/agent/skill")
    def agent_skill() -> JSONResponse:
        path = skill_path_provider()
        try:
            content = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return _error_response(
                "agent_skill_unavailable",
                "agent skill document is not available",
                503,
            )
        except OSError:
            return _error_response(
                "agent_skill_read_failed",
                "agent skill document could not be read",
                500,
            )

        return _data_response({"format": "markdown", "content": content})

    @router.get("/internal/agent/openapi.json")
    def agent_openapi_json() -> JSONResponse:
        return JSONResponse(status_code=200, content=app.openapi())

    @router.get("/internal/agent/openapi.yaml")
    def agent_openapi_yaml() -> Response:
        path = openapi_yaml_path_provider()
        try:
            body = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return _error_response(
                "agent_openapi_unavailable",
                "openapi yaml snapshot is not available",
                503,
            )
        except OSError:
            return _error_response(
                "agent_openapi_read_failed",
                "openapi yaml snapshot could not be read",
                500,
            )

        return Response(content=body, media_type="text/yaml")

    app.include_router(router)


def _data_response(payload: dict[str, object], status_code: int = 200) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"data": payload})


def _error_response(code: str, message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


__all__ = ["register_agent_bootstrap_routes"]
