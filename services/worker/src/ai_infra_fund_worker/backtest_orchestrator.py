"""Worker shell that processes queued backtest requests.

Reads queued rows from ``audit.backtest_requests``, reconstructs a
``BacktestPipelineInputs``, runs the pure pipeline composition, and
persists ``BacktestRun`` plus ``RunArtifact`` records via the existing
``EvaluationPersistenceRepository``.

The pipeline composition itself lives in
``ai_infra_fund_core.runs.backtest_pipeline``.
"""

from __future__ import annotations

import json
import traceback
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Callable, Protocol

from ai_infra_fund_core.audit.experiment_events import (
    EventSink,
    ExperimentEvent,
    build_event,
)
from ai_infra_fund_core.contracts.evaluation import RunArtifact
from ai_infra_fund_core.runs.backtest_pipeline import (
    BacktestPipelineInputs,
    BacktestRunDraft,
    compose_backtest_pipeline,
)


class BacktestRequestRepositoryProtocol(Protocol):
    def lease_next(
        self, *, leased_by: str, ttl_seconds: int = 300
    ) -> dict[str, Any] | None: ...

    def mark_running(self, *, request_id: str) -> None: ...

    def mark_succeeded(self, *, request_id: str, backtest_run_id: str) -> None: ...

    def mark_failed(self, *, request_id: str, error_summary: str) -> None: ...


class EvaluationPersistenceRepositoryProtocol(Protocol):
    def save_backtest_run(self, run: object) -> object: ...

    def save_run_artifact(self, artifact: object) -> object: ...


Now = Callable[[], datetime]


class BiasCheckFailedError(RuntimeError):
    """Raised when a composed backtest's bias_checks did not pass; must not persist."""


@dataclass(frozen=True, slots=True)
class BacktestProcessOutcome:
    status: str  # 'idle' | 'succeeded' | 'failed'
    request_id: str | None
    backtest_run_id: str | None
    error_summary: str | None


def process_next_backtest(
    *,
    request_repository: BacktestRequestRepositoryProtocol,
    evaluation_repository: EvaluationPersistenceRepositoryProtocol,
    event_sink: EventSink | None = None,
    worker_id: str = "worker",
    now: Now = lambda: datetime.now(timezone.utc),
) -> BacktestProcessOutcome:
    request = request_repository.lease_next(leased_by=worker_id)
    if request is None:
        return BacktestProcessOutcome(
            status="idle",
            request_id=None,
            backtest_run_id=None,
            error_summary=None,
        )

    request_id = str(request["request_id"])
    started_at = now()
    request_repository.mark_running(request_id=request_id)
    _emit(
        event_sink,
        build_event(
            kind="backtest_started",
            run_id=request_id,
            payload={
                "request_id": request_id,
                "strategy_id": request.get("strategy_id"),
                "worker_id": worker_id,
            },
            occurred_at=started_at,
        ),
    )

    try:
        pipeline_inputs = _build_pipeline_inputs(request, started_at=started_at)
        draft = compose_backtest_pipeline(pipeline_inputs)
        if not draft.bias_check.passed:
            raise BiasCheckFailedError(
                f"bias_checks failed: {list(draft.bias_check.violations)}"
            )
        _persist_artifacts(
            evaluation_repository=evaluation_repository,
            draft=draft,
            request_id=request_id,
            started_at=started_at,
            completed_at=now(),
        )
        backtest_run_id = draft.backtest_run.backtest_run_id
        request_repository.mark_succeeded(
            request_id=request_id, backtest_run_id=backtest_run_id
        )
        completed_at = now()
        _emit(
            event_sink,
            build_event(
                kind="shadow_comparison_recorded",
                run_id=request_id,
                payload={
                    "shadow_evaluation_id": draft.shadow_record.evaluation_id,
                    "affects_production": draft.shadow_record.affects_production,
                },
                occurred_at=completed_at,
            ),
        )
        _emit(
            event_sink,
            build_event(
                kind="backtest_completed",
                run_id=request_id,
                payload={
                    "request_id": request_id,
                    "backtest_run_id": backtest_run_id,
                    "status": "succeeded",
                },
                occurred_at=completed_at,
            ),
        )
        return BacktestProcessOutcome(
            status="succeeded",
            request_id=request_id,
            backtest_run_id=backtest_run_id,
            error_summary=None,
        )
    except Exception as error:  # noqa: BLE001 — broad on purpose; we mark and report
        error_summary = f"{type(error).__name__}: {error}"
        request_repository.mark_failed(
            request_id=request_id, error_summary=error_summary
        )
        completed_at = now()
        _emit(
            event_sink,
            build_event(
                kind="backtest_completed",
                run_id=request_id,
                payload={
                    "request_id": request_id,
                    "status": "failed",
                    "error_summary": error_summary,
                    "traceback_lines": _truncated_traceback(),
                },
                occurred_at=completed_at,
                severity="error",
            ),
        )
        return BacktestProcessOutcome(
            status="failed",
            request_id=request_id,
            backtest_run_id=None,
            error_summary=error_summary,
        )


def _build_pipeline_inputs(
    request: Mapping[str, Any],
    *,
    started_at: datetime,
) -> BacktestPipelineInputs:
    raw_inputs = request.get("pipeline_inputs")
    if isinstance(raw_inputs, str):
        inputs = json.loads(raw_inputs)
    elif isinstance(raw_inputs, Mapping):
        inputs = dict(raw_inputs)
    else:
        raise ValueError("pipeline_inputs must be a mapping or JSON string")

    cost_assumptions = request.get("cost_assumptions") or {}
    if isinstance(cost_assumptions, str):
        cost_assumptions = json.loads(cost_assumptions)

    return BacktestPipelineInputs(
        strategy_id=_require_text(request, "strategy_id"),
        production_recommendation_id=_require_text(
            inputs, "production_recommendation_id"
        ),
        dataset_snapshot_ids=tuple(request.get("dataset_snapshot_ids") or ()),
        validation_protocol=_require_text(request, "validation_protocol"),
        cost_assumptions=dict(cost_assumptions),
        formula_version=_require_text(request, "formula_version"),
        benchmark_id=_require_text(inputs, "benchmark_id"),
        benchmark_version=_require_text(inputs, "benchmark_version"),
        features=_deserialize_records(
            inputs, "features", datetime_fields=("available_at",)
        ),
        predictions=_deserialize_records(
            inputs, "predictions", datetime_fields=("as_of",)
        ),
        strategy_values=_decimal_sequence(inputs, "strategy_values"),
        benchmark_values=_decimal_sequence(inputs, "benchmark_values"),
        monte_carlo_returns=_decimal_sequence(inputs, "monte_carlo_returns"),
        monte_carlo_simulations=int(inputs["monte_carlo_simulations"]),
        monte_carlo_horizon_periods=int(inputs["monte_carlo_horizon_periods"]),
        monte_carlo_seed=int(inputs["monte_carlo_seed"]),
        model_run_id=_require_text(request, "model_run_id"),
        shadow_output_id=_require_text(inputs, "shadow_output_id"),
        run_artifact_ids=tuple(inputs.get("run_artifact_ids") or ()),
        as_of=_require_datetime(request, "as_of"),
        available_at=_to_datetime(inputs, "available_at", fallback=started_at),
        created_at=_to_datetime(inputs, "created_at", fallback=started_at),
    )


def _persist_artifacts(
    *,
    evaluation_repository: EvaluationPersistenceRepositoryProtocol,
    draft: BacktestRunDraft,
    request_id: str,
    started_at: datetime,
    completed_at: datetime,
) -> None:
    evaluation_repository.save_backtest_run(draft.backtest_run)
    run_artifact = RunArtifact(
        run_id=f"run-{draft.backtest_run.backtest_run_id}",
        run_type="backtest",
        started_at=started_at,
        completed_at=completed_at,
        inputs_hash=draft.backtest_run.artifact_hash,
        output_hash=draft.backtest_run.artifact_hash,
        artifact_uri=f"backtest://{draft.backtest_run.backtest_run_id}?request_id={request_id}",
        status="succeeded",
        error_summary=None,
        created_at=completed_at,
    )
    evaluation_repository.save_run_artifact(run_artifact)


def _emit(event_sink: EventSink | None, event: ExperimentEvent) -> None:
    if event_sink is None:
        return
    event_sink(event)


def _require_text(record: Mapping[str, Any], field_name: str) -> str:
    value = record.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} is required")
    return value


def _require_sequence(record: Mapping[str, Any], field_name: str) -> list[Any]:
    value = record.get(field_name)
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"{field_name} must be a list")
    return list(value)


def _decimal_sequence(record: Mapping[str, Any], field_name: str) -> list[Decimal]:
    sequence = _require_sequence(record, field_name)
    return [Decimal(str(item)) for item in sequence]


def _deserialize_records(
    record: Mapping[str, Any],
    field_name: str,
    *,
    datetime_fields: tuple[str, ...],
) -> list[dict[str, Any]]:
    sequence = _require_sequence(record, field_name)
    deserialized: list[dict[str, Any]] = []
    for item in sequence:
        if not isinstance(item, Mapping):
            raise ValueError(f"{field_name} entries must be mappings")
        normalized = dict(item)
        for dt_field in datetime_fields:
            raw = normalized.get(dt_field)
            if isinstance(raw, str) and raw:
                parsed = datetime.fromisoformat(raw)
                normalized[dt_field] = (
                    parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
                )
        deserialized.append(normalized)
    return deserialized


def _to_datetime(
    record: Mapping[str, Any],
    field_name: str,
    *,
    fallback: datetime,
) -> datetime:
    value = record.get(field_name)
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str) and value:
        parsed = datetime.fromisoformat(value)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    return fallback


def _require_datetime(record: Mapping[str, Any], field_name: str) -> datetime:
    value = record.get(field_name)
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str) and value:
        parsed = datetime.fromisoformat(value)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    raise ValueError(
        f"{field_name} is required and must be a datetime/isoformat string"
    )


def _truncated_traceback(limit: int = 5) -> list[str]:
    formatted = traceback.format_exc().splitlines()
    return formatted[-limit:] if formatted else []


__all__ = [
    "BacktestProcessOutcome",
    "BacktestRequestRepositoryProtocol",
    "BiasCheckFailedError",
    "EvaluationPersistenceRepositoryProtocol",
    "process_next_backtest",
]
