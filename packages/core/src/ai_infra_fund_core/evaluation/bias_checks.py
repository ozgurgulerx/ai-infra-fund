from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any


@dataclass(frozen=True, slots=True)
class BiasCheckResult:
    passed: bool
    violations: tuple[str, ...]


def check_lookahead_bias(
    features: Sequence[Mapping[str, Any]],
    predictions: Sequence[Mapping[str, Any]],
) -> BiasCheckResult:
    feature_available_at: dict[str, datetime] = {}
    for feature in features:
        feature_id = _require_text(feature, "feature_id")
        if feature_id in feature_available_at:
            raise ValueError(f"duplicate feature_id {feature_id}")
        available_at = _require_aware_datetime(feature.get("available_at"), "available_at")
        feature_available_at[feature_id] = available_at

    violations: list[str] = []
    for prediction in predictions:
        prediction_id = _require_text(prediction, "prediction_id")
        as_of = _require_aware_datetime(prediction.get("as_of"), "as_of")
        for feature_id in _feature_ids(prediction):
            if feature_id not in feature_available_at:
                raise ValueError(f"prediction {prediction_id} references unknown feature {feature_id}")
            available_at = feature_available_at[feature_id]
            if available_at > as_of:
                violations.append(
                    f"prediction {prediction_id} used feature {feature_id} available at {available_at.isoformat()} "
                    f"after prediction as_of {as_of.isoformat()}"
                )

    return BiasCheckResult(passed=not violations, violations=tuple(violations))


def check_recursive_indicator_consistency(
    baseline: Sequence[object],
    recomputed: Sequence[object],
    tolerance: object = 0,
) -> BiasCheckResult:
    tolerance_value = _to_decimal(tolerance, "tolerance")
    if tolerance_value < Decimal("0"):
        raise ValueError("tolerance must be non-negative")
    if len(recomputed) < len(baseline):
        return BiasCheckResult(
            passed=False,
            violations=(f"recomputed output shorter than baseline: baseline={len(baseline)} recomputed={len(recomputed)}",),
        )

    violations: list[str] = []
    for index, baseline_value in enumerate(baseline):
        recomputed_value = recomputed[index]
        difference = abs(_to_decimal(baseline_value, "baseline") - _to_decimal(recomputed_value, "recomputed"))
        if difference > tolerance_value:
            violations.append(
                f"indicator changed at index {index}: baseline={baseline_value} recomputed={recomputed_value}"
            )

    return BiasCheckResult(passed=not violations, violations=tuple(violations))


def _feature_ids(prediction: Mapping[str, Any]) -> tuple[str, ...]:
    raw_feature_ids = prediction.get("feature_ids")
    if raw_feature_ids is None:
        raw_feature_id = prediction.get("feature_id")
        if raw_feature_id is None:
            raise ValueError("prediction must include feature_ids or feature_id")
        raw_feature_ids = (raw_feature_id,)
    if isinstance(raw_feature_ids, str):
        raw_feature_ids = (raw_feature_ids,)
    feature_ids = tuple(str(feature_id).strip() for feature_id in raw_feature_ids)
    if not feature_ids or any(not feature_id for feature_id in feature_ids):
        raise ValueError("feature_ids must not be empty")
    return feature_ids


def _require_text(record: Mapping[str, Any], field_name: str) -> str:
    value = record.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _require_aware_datetime(value: object, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise ValueError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value


def _to_decimal(value: object, field_name: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field_name} must be numeric") from exc
