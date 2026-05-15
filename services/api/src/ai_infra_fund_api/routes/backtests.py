from __future__ import annotations

import json
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Iterator, Mapping, Protocol

from fastapi import APIRouter, FastAPI, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ai_infra_fund_core.runtime.config import RuntimeSettings


SettingsProvider = Callable[[], RuntimeSettings]
MAX_PIPELINE_INPUTS_BYTES = 1_048_576  # 1 MiB serialized cap


class BacktestRequestService(Protocol):
    def enqueue(self, payload: dict[str, object]) -> dict[str, object]: ...

    def get(self, request_id: str) -> dict[str, object] | None: ...

    def list_recent(self, *, limit: int = 50) -> list[dict[str, object]]: ...


class BacktestRequestServiceUnavailable(RuntimeError):
    pass


class BacktestRequestBody(BaseModel):
    strategy_id: str = Field(..., min_length=1)
    dataset_snapshot_ids: list[str] = Field(..., min_length=1)
    validation_protocol: str = Field(..., min_length=1)
    cost_assumptions: dict[str, Any] = Field(...)
    pipeline_inputs: dict[str, Any] = Field(default_factory=dict)
    formula_version: str = Field(..., min_length=1)
    model_run_id: str = Field(..., min_length=1)
    git_sha: str = Field(..., min_length=1)
    as_of: datetime


@dataclass(frozen=True, slots=True)
class PostgresBacktestRequestService:
    settings_provider: SettingsProvider

    def enqueue(self, payload: dict[str, object]) -> dict[str, object]:
        request_id = _generate_request_id()
        with self._repository() as repository:
            repository.enqueue(
                request_id=request_id,
                strategy_id=str(payload["strategy_id"]),
                dataset_snapshot_ids=_coerce_string_sequence(
                    payload["dataset_snapshot_ids"]
                ),
                validation_protocol=str(payload["validation_protocol"]),
                cost_assumptions=_coerce_mapping(payload["cost_assumptions"]),
                pipeline_inputs=_coerce_mapping(payload.get("pipeline_inputs", {})),
                formula_version=str(payload["formula_version"]),
                model_run_id=str(payload["model_run_id"]),
                git_sha=str(payload["git_sha"]),
                as_of=_coerce_datetime(payload["as_of"]),
            )
            stored = repository.get_by_id(request_id) or {}
        stored.setdefault("request_id", request_id)
        stored.setdefault("status", "queued")
        return stored

    def get(self, request_id: str) -> dict[str, object] | None:
        with self._repository() as repository:
            return repository.get_by_id(request_id)

    def list_recent(self, *, limit: int = 50) -> list[dict[str, object]]:
        with self._repository() as repository:
            return repository.list_recent(limit=limit)

    @contextmanager
    def _repository(self) -> Iterator[Any]:
        try:
            import psycopg
            from ai_infra_fund_api.repositories.backtest_requests import (
                BacktestRequestRepository,
            )
        except ImportError as error:
            raise BacktestRequestServiceUnavailable(
                "backtest request repository is not configured"
            ) from error

        settings = self.settings_provider()
        with psycopg.connect(settings.database_url) as connection:
            yield BacktestRequestRepository(connection)


def register_backtest_routes(
    app: FastAPI,
    *,
    backtest_request_service: BacktestRequestService | None,
    settings_provider: SettingsProvider,
) -> None:
    service = backtest_request_service or PostgresBacktestRequestService(
        settings_provider
    )
    router = APIRouter()

    @router.post("/internal/backtests", status_code=201)
    def create_backtest(body: BacktestRequestBody) -> JSONResponse:
        serialized_inputs = json.dumps(body.pipeline_inputs, separators=(",", ":"))
        if len(serialized_inputs) > MAX_PIPELINE_INPUTS_BYTES:
            return _error_response(
                "invalid_backtest_request",
                (
                    f"pipeline_inputs serialized to {len(serialized_inputs)} bytes "
                    f"(cap {MAX_PIPELINE_INPUTS_BYTES})"
                ),
                413,
            )
        try:
            stored = service.enqueue(_request_payload(body))
        except BacktestRequestServiceUnavailable:
            return _error_response(
                "backtests_unavailable",
                "backtest request service is not configured",
                503,
            )
        except ValueError as error:
            return _error_response(
                "invalid_backtest_request",
                str(error),
                422,
            )
        except Exception:
            return _error_response(
                "backtest_enqueue_failed",
                "backtest request could not be enqueued",
                500,
            )
        return _data_response(stored, status_code=201)

    @router.get("/internal/backtests/recent")
    def recent_backtests(
        limit: int = Query(default=50, ge=1),
    ) -> JSONResponse:
        bounded_limit = min(max(limit, 1), 500)
        try:
            recent = service.list_recent(limit=bounded_limit)
        except BacktestRequestServiceUnavailable:
            return _error_response(
                "backtests_unavailable",
                "backtest request service is not configured",
                503,
            )
        except Exception:
            return _error_response(
                "backtest_read_failed",
                "backtest requests could not be loaded",
                500,
            )
        return _data_response({"requests": recent, "count": len(recent)})

    @router.get("/internal/backtests/{request_id}")
    def get_backtest(request_id: str) -> JSONResponse:
        try:
            payload = service.get(request_id)
        except BacktestRequestServiceUnavailable:
            return _error_response(
                "backtests_unavailable",
                "backtest request service is not configured",
                503,
            )
        except Exception:
            return _error_response(
                "backtest_read_failed",
                "backtest request could not be loaded",
                500,
            )
        if payload is None:
            return _error_response(
                "backtest_request_not_found",
                "backtest request was not found",
                404,
            )
        return _data_response(payload)

    app.include_router(router)


def _request_payload(body: BacktestRequestBody) -> dict[str, object]:
    return {
        "strategy_id": body.strategy_id,
        "dataset_snapshot_ids": list(body.dataset_snapshot_ids),
        "validation_protocol": body.validation_protocol,
        "cost_assumptions": dict(body.cost_assumptions),
        "pipeline_inputs": dict(body.pipeline_inputs),
        "formula_version": body.formula_version,
        "model_run_id": body.model_run_id,
        "git_sha": body.git_sha,
        "as_of": body.as_of,
    }


def _generate_request_id() -> str:
    return f"backtest-req-{uuid.uuid4().hex[:24]}"


def _coerce_mapping(value: object) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    raise ValueError("expected mapping value")


def _coerce_string_sequence(value: object) -> list[str]:
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value]
    if isinstance(value, str):
        return [value]
    raise ValueError("expected list of strings")


def _coerce_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    if isinstance(value, str):
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed
    raise ValueError("expected ISO 8601 timestamp")


def _data_response(payload: dict[str, object], status_code: int = 200) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"data": payload})


def _error_response(code: str, message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


__all__ = [
    "BacktestRequestService",
    "BacktestRequestServiceUnavailable",
    "register_backtest_routes",
]
