from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from ai_infra_fund_core.contracts.common import AdvisoryLabel, coerce_enum, require_text

from .artifacts import (
    RUN_STATUS_FAILED,
    RUN_STATUS_SUCCEEDED,
    AdvisoryRunInputs,
    AdvisoryRunResult,
    AdvisoryRunTraceability,
    advisory_artifact_uri,
    advisory_inputs_hash,
    advisory_run_id,
    advisory_run_output_hash,
    build_advisory_run_artifact,
)


def orchestrate_advisory_run(
    inputs: AdvisoryRunInputs,
    *,
    started_at: datetime,
    completed_at: datetime,
    created_at: datetime | None = None,
) -> AdvisoryRunResult:
    traceability, validation_errors = _validate_traceability(inputs)
    if validation_errors:
        artifact = build_advisory_run_artifact(
            inputs,
            started_at=started_at,
            completed_at=completed_at,
            created_at=created_at,
            status=RUN_STATUS_FAILED,
            output_hash=None,
            artifact_uri=None,
            error_summary="; ".join(validation_errors),
        )
        return AdvisoryRunResult(
            artifact=artifact,
            traceability=None,
            validation_errors=validation_errors,
        )

    assert traceability is not None
    inputs_hash = advisory_inputs_hash(inputs)
    run_id = advisory_run_id(inputs_hash)
    output_hash = advisory_run_output_hash(inputs_hash=inputs_hash, traceability=traceability)
    artifact = build_advisory_run_artifact(
        inputs,
        started_at=started_at,
        completed_at=completed_at,
        created_at=created_at,
        status=RUN_STATUS_SUCCEEDED,
        output_hash=output_hash,
        artifact_uri=advisory_artifact_uri(run_id),
        error_summary=None,
    )
    return AdvisoryRunResult(
        artifact=artifact,
        traceability=traceability,
        validation_errors=(),
    )


def _validate_traceability(inputs: AdvisoryRunInputs) -> tuple[AdvisoryRunTraceability | None, tuple[str, ...]]:
    errors: list[str] = []
    evidence_ids = _validated_id_tuple(inputs.evidence_ids, "evidence_ids", errors)
    claim_ids = _validated_id_tuple(inputs.claim_ids, "claim_ids", errors)
    model_run_ids = _validated_id_tuple(inputs.model_run_ids, "model_run_ids", errors)
    signal_bundle_id = _validated_required_text(inputs.signal_bundle_id, "signal_bundle_id", errors)
    target_weights_id = _validated_required_text(inputs.target_weights_id, "target_weights_id", errors)
    recommendation_id = _validated_required_text(inputs.recommendation_id, "recommendation_id", errors)
    audit_id = _validated_required_text(inputs.audit_id, "audit_id", errors)
    evaluation_id = _validated_optional_text(inputs.evaluation_id, "evaluation_id", errors)
    backtest_run_id = _validated_optional_text(inputs.backtest_run_id, "backtest_run_id", errors)
    advisory_label = _validated_advisory_label(inputs.advisory_label, errors)

    if evaluation_id is None and backtest_run_id is None:
        errors.append("evaluation_id or backtest_run_id is required")

    if errors:
        return None, tuple(errors)

    assert advisory_label is not None
    assert signal_bundle_id is not None
    assert target_weights_id is not None
    assert recommendation_id is not None
    assert audit_id is not None
    return (
        AdvisoryRunTraceability(
            evidence_ids=evidence_ids,
            claim_ids=claim_ids,
            model_run_ids=model_run_ids,
            signal_bundle_id=signal_bundle_id,
            target_weights_id=target_weights_id,
            recommendation_id=recommendation_id,
            audit_id=audit_id,
            evaluation_id=evaluation_id,
            backtest_run_id=backtest_run_id,
            advisory_label=advisory_label,
        ),
        (),
    )


def _validated_id_tuple(values: Sequence[str] | None, field_name: str, errors: list[str]) -> tuple[str, ...]:
    if values is None or isinstance(values, str):
        errors.append(f"{field_name} must be a non-empty sequence")
        return ()
    normalized = tuple(values)
    if not normalized:
        errors.append(f"{field_name} must not be empty")
        return ()

    valid_ids: list[str] = []
    for index, value in enumerate(normalized):
        try:
            valid_ids.append(require_text(value, f"{field_name}[{index}]"))
        except ValueError as exc:
            errors.append(str(exc))
    return tuple(valid_ids)


def _validated_required_text(value: str | None, field_name: str, errors: list[str]) -> str | None:
    try:
        return require_text(value, field_name)
    except ValueError as exc:
        errors.append(str(exc))
        return None


def _validated_optional_text(value: str | None, field_name: str, errors: list[str]) -> str | None:
    if value is None:
        return None
    return _validated_required_text(value, field_name, errors)


def _validated_advisory_label(value: AdvisoryLabel | str, errors: list[str]) -> AdvisoryLabel | None:
    try:
        label = coerce_enum(value, AdvisoryLabel, "advisory_label")
    except ValueError as exc:
        errors.append(str(exc))
        return None
    if label is not AdvisoryLabel.ADVISORY_ONLY:
        errors.append("advisory_label must be advisory_only")
        return None
    return label
