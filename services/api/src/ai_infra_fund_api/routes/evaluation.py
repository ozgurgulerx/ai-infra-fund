from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
import re
from typing import Callable, Protocol

from fastapi import APIRouter, Body, FastAPI
from fastapi.responses import JSONResponse

from ai_infra_fund_api.repositories.evaluation import EvaluationRepository
from ai_infra_fund_core.contracts.evaluation import BacktestRun
from ai_infra_fund_core.runtime.config import RuntimeSettings


SettingsProvider = Callable[[], RuntimeSettings]
DETERMINISTIC_ID_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)+$")
ALLOWED_EVALUATION_FIELDS = frozenset(
    {
        "backtest_run_id",
        "strategy_id",
        "dataset_snapshot_ids",
        "validation_protocol",
        "cost_assumptions",
        "metrics",
        "artifact_hash",
        "as_of",
        "available_at",
        "created_at",
    }
)


class EvaluationPersistenceRepository(Protocol):
    def save_backtest_run(self, run: BacktestRun) -> object:
        ...


class EvaluationValidationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class PostgresEvaluationRepository:
    settings_provider: SettingsProvider

    def save_backtest_run(self, run: BacktestRun) -> BacktestRun:
        import psycopg

        settings = self.settings_provider()
        with psycopg.connect(settings.database_url) as connection:
            EvaluationRepository(connection).save_backtest_run(run)
        return run


def register_evaluation_routes(
    app: FastAPI,
    *,
    evaluation_repository: EvaluationPersistenceRepository | None,
    settings_provider: SettingsProvider,
) -> None:
    repository = evaluation_repository or PostgresEvaluationRepository(settings_provider)
    router = APIRouter()

    @router.post("/internal/evaluations")
    def persist_evaluation(payload: object = Body(...)) -> JSONResponse:
        try:
            run = prepare_evaluation_record(payload)
        except EvaluationValidationError as error:
            return _error_response("invalid_evaluation_request", str(error), 422)

        try:
            saved = repository.save_backtest_run(run)
            response_payload = _evaluation_payload(saved)
        except EvaluationValidationError:
            return _error_response(
                "evaluation_response_invalid",
                "evaluation record response was invalid",
                500,
            )
        except Exception:
            return _error_response(
                "evaluation_persistence_failed",
                "evaluation record could not be persisted",
                500,
            )

        return _data_response(response_payload, status_code=201)

    app.include_router(router)


def prepare_evaluation_record(payload: object) -> BacktestRun:
    errors: list[str] = []
    if not isinstance(payload, Mapping):
        raise EvaluationValidationError("request body must be an object")

    unknown_fields = sorted(str(field) for field in set(payload) - ALLOWED_EVALUATION_FIELDS)
    if unknown_fields:
        errors.append(f"unsupported fields are not accepted: {unknown_fields}")

    backtest_run_id = _normalize_prefixed_id(
        payload.get("backtest_run_id"),
        "backtest_run_id",
        prefix="evaluation-",
        errors=errors,
    )
    strategy_id = _normalize_prefixed_id(
        payload.get("strategy_id"),
        "strategy_id",
        prefix="strategy-",
        errors=errors,
    )
    dataset_snapshot_ids = _normalize_id_tuple(
        payload.get("dataset_snapshot_ids"),
        "dataset_snapshot_ids",
        prefix="dataset-snapshot-",
        errors=errors,
    )
    validation_protocol = _normalize_required_text(
        payload.get("validation_protocol"),
        "validation_protocol",
        errors,
    )
    cost_assumptions = _normalize_mapping(payload.get("cost_assumptions"), "cost_assumptions", errors)
    metrics = _normalize_mapping(payload.get("metrics"), "metrics", errors)
    _validate_evaluation_metrics(metrics, errors)
    artifact_hash = _normalize_required_text(payload.get("artifact_hash"), "artifact_hash", errors)
    as_of = _parse_datetime(payload.get("as_of"), "as_of", errors)
    available_at = _parse_datetime(payload.get("available_at"), "available_at", errors)
    created_at = _parse_datetime(payload.get("created_at"), "created_at", errors)

    if errors:
        raise EvaluationValidationError("; ".join(errors))

    try:
        return BacktestRun(
            backtest_run_id=backtest_run_id,
            strategy_id=strategy_id,
            dataset_snapshot_ids=dataset_snapshot_ids,
            validation_protocol=validation_protocol,
            cost_assumptions=cost_assumptions,
            metrics=metrics,
            artifact_hash=artifact_hash,
            as_of=as_of,
            available_at=available_at,
            created_at=created_at,
        )
    except ValueError as error:
        raise EvaluationValidationError(str(error)) from error


def _normalize_id_tuple(
    value: object,
    field_name: str,
    *,
    prefix: str,
    errors: list[str],
) -> tuple[str, ...]:
    if isinstance(value, str) or not isinstance(value, list):
        errors.append(f"{field_name} must be a list")
        return ()

    normalized: list[str] = []
    seen: set[str] = set()
    for index, raw_item in enumerate(value):
        item = _normalize_prefixed_id(
            raw_item,
            f"{field_name}[{index}]",
            prefix=prefix,
            errors=errors,
        )
        if not item:
            continue
        if item in seen:
            errors.append(f"{field_name} must not contain duplicate IDs")
            continue
        seen.add(item)
        normalized.append(item)

    if not normalized:
        errors.append(f"{field_name} must include at least one ID")

    return tuple(normalized)


def _normalize_prefixed_id(
    value: object,
    field_name: str,
    *,
    prefix: str,
    errors: list[str],
) -> str:
    raw = _normalize_required_text(value, field_name, errors)
    if not raw:
        return ""
    if not DETERMINISTIC_ID_PATTERN.fullmatch(raw):
        errors.append(f"{field_name} must be a deterministic lowercase reference ID")
        return raw
    if not raw.startswith(prefix):
        errors.append(f"{field_name} must start with {prefix}")
    return raw


def _normalize_required_text(value: object, field_name: str, errors: list[str]) -> str:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{field_name} is required")
        return ""
    return value.strip()


def _normalize_mapping(value: object, field_name: str, errors: list[str]) -> dict[str, object]:
    if not isinstance(value, Mapping):
        errors.append(f"{field_name} must be an object")
        return {}
    normalized = {str(key): item for key, item in value.items()}
    if not normalized:
        errors.append(f"{field_name} must not be empty")
    return normalized


def _validate_evaluation_metrics(metrics: Mapping[str, object], errors: list[str]) -> None:
    formula_versions = metrics.get("formula_versions")
    if not isinstance(formula_versions, Mapping) or not formula_versions:
        errors.append("metrics.formula_versions is required")
    else:
        for raw_key, raw_value in formula_versions.items():
            key = str(raw_key)
            if not key.strip() or not isinstance(raw_value, str) or not raw_value.strip():
                errors.append("metrics.formula_versions must map formula names to version strings")
                break

    benchmark_version = metrics.get("benchmark_version")
    if not isinstance(benchmark_version, str) or not benchmark_version.strip():
        errors.append("metrics.benchmark_version is required")


def _parse_datetime(value: object, field_name: str, errors: list[str]) -> datetime:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{field_name} is required")
        return datetime.min
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{field_name} must be an ISO-8601 datetime")
        return datetime.min

    if parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) is None:
        errors.append(f"{field_name} must be timezone-aware")
    return parsed


def _evaluation_payload(record: object) -> dict[str, object]:
    run = _to_jsonable(record)
    if not isinstance(run, dict):
        raise EvaluationValidationError("evaluation record response was invalid")
    metrics = run.get("metrics")
    if not isinstance(metrics, Mapping):
        raise EvaluationValidationError("evaluation record metrics were invalid")
    return {
        **run,
        "dataset_snapshot_ids": list(run.get("dataset_snapshot_ids", ())),
        "formula_versions": _to_jsonable(metrics.get("formula_versions")),
        "benchmark_version": metrics.get("benchmark_version"),
    }


def _to_jsonable(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _to_jsonable(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, Mapping):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(item) for item in value]
    return value


def _data_response(payload: dict[str, object], status_code: int = 200) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"data": payload})


def _error_response(code: str, message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


__all__ = ["EvaluationPersistenceRepository", "register_evaluation_routes"]
