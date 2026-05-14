from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from ai_infra_fund_core.contracts.common import (
    AdvisoryLabel,
    require_aware_datetime,
    stable_hash_payload,
)
from ai_infra_fund_core.contracts.evaluation import RunArtifact


ADVISORY_RUN_TYPE = "controlled_advisory_run"
ADVISORY_RUN_ID_PREFIX = "advisory-run"
ADVISORY_RUN_ARTIFACT_PREFIX = "artifact://runs"
RUN_STATUS_SUCCEEDED = "succeeded"
RUN_STATUS_FAILED = "failed"


@dataclass(frozen=True, slots=True)
class AdvisoryRunInputs:
    evidence_ids: Sequence[str] | None
    claim_ids: Sequence[str] | None
    model_run_ids: Sequence[str] | None
    signal_bundle_id: str | None
    target_weights_id: str | None
    recommendation_id: str | None
    audit_id: str | None
    evaluation_id: str | None = None
    backtest_run_id: str | None = None
    advisory_label: AdvisoryLabel | str = AdvisoryLabel.ADVISORY_ONLY

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence_ids", _immutable_sequence(self.evidence_ids))
        object.__setattr__(self, "claim_ids", _immutable_sequence(self.claim_ids))
        object.__setattr__(self, "model_run_ids", _immutable_sequence(self.model_run_ids))


@dataclass(frozen=True, slots=True)
class AdvisoryRunTraceability:
    evidence_ids: tuple[str, ...]
    claim_ids: tuple[str, ...]
    model_run_ids: tuple[str, ...]
    signal_bundle_id: str
    target_weights_id: str
    recommendation_id: str
    audit_id: str
    evaluation_id: str | None
    backtest_run_id: str | None
    advisory_label: AdvisoryLabel


@dataclass(frozen=True, slots=True)
class AdvisoryRunResult:
    artifact: RunArtifact
    traceability: AdvisoryRunTraceability | None
    validation_errors: tuple[str, ...]

    @property
    def succeeded(self) -> bool:
        return self.artifact.status == RUN_STATUS_SUCCEEDED


def advisory_inputs_hash(inputs: AdvisoryRunInputs) -> str:
    return stable_hash_payload(_advisory_inputs_payload(inputs))


def advisory_run_id(inputs_hash: str) -> str:
    return f"{ADVISORY_RUN_ID_PREFIX}-{inputs_hash[:16]}"


def advisory_artifact_uri(run_id: str) -> str:
    return f"{ADVISORY_RUN_ARTIFACT_PREFIX}/{run_id}"


def advisory_run_output_hash(*, inputs_hash: str, traceability: AdvisoryRunTraceability) -> str:
    return stable_hash_payload(
        {
            "inputs_hash": inputs_hash,
            "run_type": ADVISORY_RUN_TYPE,
            "status": RUN_STATUS_SUCCEEDED,
            "traceability": advisory_traceability_payload(traceability),
        }
    )


def advisory_traceability_payload(traceability: AdvisoryRunTraceability) -> dict[str, object]:
    return {
        "evidence_ids": traceability.evidence_ids,
        "claim_ids": traceability.claim_ids,
        "model_run_ids": traceability.model_run_ids,
        "signal_bundle_id": traceability.signal_bundle_id,
        "target_weights_id": traceability.target_weights_id,
        "recommendation_id": traceability.recommendation_id,
        "audit_id": traceability.audit_id,
        "evaluation_id": traceability.evaluation_id,
        "backtest_run_id": traceability.backtest_run_id,
        "advisory_label": traceability.advisory_label,
    }


def build_advisory_run_artifact(
    inputs: AdvisoryRunInputs,
    *,
    started_at: datetime,
    completed_at: datetime,
    status: str,
    output_hash: str | None,
    artifact_uri: str | None,
    error_summary: str | None,
    created_at: datetime | None = None,
) -> RunArtifact:
    require_aware_datetime(started_at, "started_at")
    require_aware_datetime(completed_at, "completed_at")
    artifact_created_at = created_at or completed_at
    require_aware_datetime(artifact_created_at, "created_at")
    if completed_at < started_at:
        raise ValueError("completed_at must be greater than or equal to started_at")

    inputs_hash = advisory_inputs_hash(inputs)
    return RunArtifact(
        run_id=advisory_run_id(inputs_hash),
        run_type=ADVISORY_RUN_TYPE,
        started_at=started_at,
        completed_at=completed_at,
        inputs_hash=inputs_hash,
        output_hash=output_hash,
        artifact_uri=artifact_uri,
        status=status,
        error_summary=error_summary,
        created_at=artifact_created_at,
    )


def _advisory_inputs_payload(inputs: AdvisoryRunInputs) -> dict[str, object]:
    return {
        "evidence_ids": _sequence_payload(inputs.evidence_ids),
        "claim_ids": _sequence_payload(inputs.claim_ids),
        "model_run_ids": _sequence_payload(inputs.model_run_ids),
        "signal_bundle_id": inputs.signal_bundle_id,
        "target_weights_id": inputs.target_weights_id,
        "recommendation_id": inputs.recommendation_id,
        "audit_id": inputs.audit_id,
        "evaluation_id": inputs.evaluation_id,
        "backtest_run_id": inputs.backtest_run_id,
        "advisory_label": inputs.advisory_label,
    }


def _sequence_payload(values: Sequence[str] | None) -> object:
    return _immutable_sequence(values)


def _immutable_sequence(values: Sequence[str] | None) -> object:
    if values is None or isinstance(values, str):
        return values
    return tuple(values)
