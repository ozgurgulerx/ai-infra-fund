from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
import re
from typing import Protocol

from fastapi import APIRouter, Body, FastAPI
from fastapi.responses import JSONResponse


ALLOWED_CREATE_FIELDS = frozenset(
    {
        "ticker_or_portfolio",
        "horizon",
        "target_weights_id",
        "signal_bundle_id",
        "evidence_ids",
        "model_run_ids",
        "run_id",
        "requested_by",
    }
)
DETERMINISTIC_ID_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)+$")


@dataclass(frozen=True, slots=True)
class RecommendationCreateRequest:
    ticker_or_portfolio: str
    horizon: str
    target_weights_id: str
    signal_bundle_id: str
    evidence_ids: tuple[str, ...]
    model_run_ids: tuple[str, ...]
    run_id: str | None = None
    requested_by: str | None = None


class RecommendationService(Protocol):
    def create_recommendation(self, request: RecommendationCreateRequest) -> object:
        ...

    def get_recommendation(self, recommendation_id: str) -> object | None:
        ...


class RecommendationValidationError(ValueError):
    pass


class RecommendationPayloadError(ValueError):
    pass


class RecommendationServiceUnavailable(RuntimeError):
    pass


class UnconfiguredRecommendationService:
    def create_recommendation(self, request: RecommendationCreateRequest) -> object:
        raise RecommendationServiceUnavailable("recommendation service is not configured")

    def get_recommendation(self, recommendation_id: str) -> object | None:
        raise RecommendationServiceUnavailable("recommendation service is not configured")


def register_recommendation_routes(
    app: FastAPI,
    *,
    recommendation_service: RecommendationService | None,
) -> None:
    service = recommendation_service or UnconfiguredRecommendationService()
    router = APIRouter()

    @router.post("/internal/recommendations")
    def create_recommendation(payload: object = Body(...)) -> JSONResponse:
        try:
            request = prepare_recommendation_create_request(payload)
        except RecommendationValidationError as error:
            return _error_response("invalid_recommendation_request", str(error), 422)

        try:
            record = service.create_recommendation(request)
            response_payload = _recommendation_payload(record)
        except RecommendationServiceUnavailable:
            return _error_response(
                "recommendations_unavailable",
                "recommendation service is not configured",
                503,
            )
        except RecommendationPayloadError:
            return _error_response(
                "recommendation_response_invalid",
                "recommendation artifact response was invalid",
                500,
            )
        except Exception:
            return _error_response(
                "recommendation_persistence_failed",
                "recommendation artifact could not be persisted",
                500,
            )

        return _data_response(response_payload, status_code=201)

    @router.get("/internal/recommendations/{recommendation_id}")
    def get_recommendation(recommendation_id: str) -> JSONResponse:
        errors: list[str] = []
        normalized_id = _normalize_prefixed_id(
            recommendation_id,
            "recommendation_id",
            prefix="recommendation-",
            errors=errors,
        )
        if errors:
            return _error_response("invalid_recommendation_request", "; ".join(errors), 422)

        try:
            record = service.get_recommendation(normalized_id)
            if record is None:
                return _error_response(
                    "recommendation_not_found",
                    "recommendation artifact was not found",
                    404,
                )
            response_payload = _recommendation_payload(record)
        except RecommendationServiceUnavailable:
            return _error_response(
                "recommendations_unavailable",
                "recommendation service is not configured",
                503,
            )
        except RecommendationPayloadError:
            return _error_response(
                "recommendation_response_invalid",
                "recommendation artifact response was invalid",
                500,
            )
        except Exception:
            return _error_response(
                "recommendation_lookup_failed",
                "recommendation artifact could not be loaded",
                500,
            )

        return _data_response(response_payload)

    app.include_router(router)


def prepare_recommendation_create_request(payload: object) -> RecommendationCreateRequest:
    errors: list[str] = []
    if not isinstance(payload, Mapping):
        raise RecommendationValidationError("request body must be an object")

    unknown_fields = sorted(str(field) for field in set(payload) - ALLOWED_CREATE_FIELDS)
    if unknown_fields:
        errors.append(f"unsupported fields are not accepted: {unknown_fields}")

    ticker_or_portfolio = _normalize_required_text(
        payload.get("ticker_or_portfolio"),
        "ticker_or_portfolio",
        errors,
    )
    horizon = _normalize_required_text(payload.get("horizon"), "horizon", errors)
    target_weights_id = _normalize_prefixed_id(
        payload.get("target_weights_id"),
        "target_weights_id",
        prefix="target-weights-",
        errors=errors,
    )
    signal_bundle_id = _normalize_prefixed_id(
        payload.get("signal_bundle_id"),
        "signal_bundle_id",
        prefix="signal-bundle-",
        errors=errors,
    )
    evidence_ids = _normalize_id_tuple(
        payload.get("evidence_ids"),
        "evidence_ids",
        prefix="evidence-",
        errors=errors,
    )
    model_run_ids = _normalize_id_tuple(
        payload.get("model_run_ids"),
        "model_run_ids",
        prefix="model-run-",
        errors=errors,
    )
    run_id = _normalize_optional_prefixed_id(
        payload.get("run_id"),
        "run_id",
        prefix="run-",
        errors=errors,
    )
    requested_by = _normalize_optional_text(payload.get("requested_by"), "requested_by", errors)

    if errors:
        raise RecommendationValidationError("; ".join(errors))

    return RecommendationCreateRequest(
        ticker_or_portfolio=ticker_or_portfolio,
        horizon=horizon,
        target_weights_id=target_weights_id,
        signal_bundle_id=signal_bundle_id,
        evidence_ids=evidence_ids,
        model_run_ids=model_run_ids,
        run_id=run_id,
        requested_by=requested_by,
    )


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


def _normalize_optional_prefixed_id(
    value: object,
    field_name: str,
    *,
    prefix: str,
    errors: list[str],
) -> str | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    return _normalize_prefixed_id(value, field_name, prefix=prefix, errors=errors)


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


def _normalize_optional_text(value: object, field_name: str, errors: list[str]) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        errors.append(f"{field_name} must be text")
        return None
    normalized = value.strip()
    return normalized or None


def _recommendation_payload(record: object) -> dict[str, object]:
    artifact_raw = _lookup_value(record, "artifact")
    audit_raw = _lookup_value(record, "audit")
    if artifact_raw is None or audit_raw is None:
        raise RecommendationPayloadError("recommendation record must include artifact and audit")

    artifact = _to_jsonable(artifact_raw)
    audit = _to_jsonable(audit_raw)
    if not isinstance(artifact, dict) or not isinstance(audit, dict):
        raise RecommendationPayloadError("recommendation artifact and audit must be objects")

    return {
        "artifact": artifact,
        "audit": audit,
        "audit_links": _audit_links(artifact, audit),
    }


def _audit_links(artifact: Mapping[str, object], audit: Mapping[str, object]) -> dict[str, object]:
    recommendation_id = _first_text(audit, artifact, "recommendation_id")
    target_weights_id = _first_text(audit, artifact, "target_weights_id")
    signal_bundle_id = _first_text(audit, artifact, "signal_bundle_id")
    evidence_ids = _first_list(audit, artifact, "evidence_ids")
    model_run_ids = _first_list(audit, artifact, "model_run_ids")
    audit_id = _text_or_none(audit.get("audit_id"))

    if not all([recommendation_id, target_weights_id, signal_bundle_id, evidence_ids, model_run_ids, audit_id]):
        raise RecommendationPayloadError("recommendation audit links are incomplete")

    return {
        "audit_id": audit_id,
        "recommendation_id": recommendation_id,
        "target_weights_id": target_weights_id,
        "signal_bundle_id": signal_bundle_id,
        "evidence_ids": evidence_ids,
        "model_run_ids": model_run_ids,
    }


def _first_text(
    first: Mapping[str, object],
    second: Mapping[str, object],
    field_name: str,
) -> str | None:
    return _text_or_none(first.get(field_name)) or _text_or_none(second.get(field_name))


def _first_list(
    first: Mapping[str, object],
    second: Mapping[str, object],
    field_name: str,
) -> list[object]:
    first_value = first.get(field_name)
    if isinstance(first_value, list) and first_value:
        return first_value

    second_value = second.get(field_name)
    if isinstance(second_value, list) and second_value:
        return second_value

    return []


def _text_or_none(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


def _lookup_value(source: object, field_name: str) -> object | None:
    if isinstance(source, Mapping):
        return source.get(field_name)
    return getattr(source, field_name, None)


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
