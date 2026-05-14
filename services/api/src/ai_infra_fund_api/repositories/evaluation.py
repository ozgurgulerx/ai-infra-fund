from __future__ import annotations

from collections.abc import Mapping
import json
from typing import Protocol, TypeVar

from ai_infra_fund_core.contracts.common import canonicalize, require_text
from ai_infra_fund_core.contracts.evaluation import BacktestRun, RunArtifact


class Cursor(Protocol):
    def execute(self, statement: str, params: tuple[object, ...] | None = None) -> None:
        ...


class Connection(Protocol):
    def cursor(self) -> object:
        ...

    def commit(self) -> None:
        ...


BacktestRunT = TypeVar("BacktestRunT")
RunArtifactT = TypeVar("RunArtifactT")

RUN_ARTIFACT_STATUSES = frozenset({"pending", "running", "succeeded", "failed", "cancelled"})


INSERT_BACKTEST_RUN_SQL = """
INSERT INTO audit.backtest_runs (
    backtest_run_id,
    strategy_id,
    dataset_snapshot_ids,
    started_at,
    completed_at,
    walk_forward_config_json,
    summary_metrics_json,
    transaction_cost_model_json,
    status,
    error_summary,
    created_at
) VALUES (
    %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s, %s, %s
);
"""


INSERT_RUN_ARTIFACT_SQL = """
INSERT INTO audit.run_artifacts (
    run_id,
    run_type,
    started_at,
    completed_at,
    inputs_hash,
    output_hash,
    artifact_uri,
    status,
    error_summary,
    created_at
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
);
"""


class EvaluationRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def save_backtest_run(self, run: BacktestRunT) -> BacktestRunT:
        params = _backtest_run_params(run)
        with self._connection.cursor() as cursor:
            cursor.execute(INSERT_BACKTEST_RUN_SQL, params)
        self._connection.commit()
        return run

    def save_run_artifact(self, artifact: RunArtifactT) -> RunArtifactT:
        params = _run_artifact_params(artifact)
        with self._connection.cursor() as cursor:
            cursor.execute(INSERT_RUN_ARTIFACT_SQL, params)
        self._connection.commit()
        return artifact


def _backtest_run_params(run: object) -> tuple[object, ...]:
    normalized = _normalize_backtest_run(run)
    formula_versions = _formula_versions(normalized.metrics)
    benchmark_version = _benchmark_version(normalized.metrics)
    config = {
        "validation_protocol": normalized.validation_protocol,
        "as_of": normalized.as_of,
        "available_at": normalized.available_at,
        "formula_versions": formula_versions,
        "benchmark_version": benchmark_version,
    }
    metrics = {
        **dict(normalized.metrics),
        "artifact_hash": normalized.artifact_hash,
    }
    return (
        normalized.backtest_run_id,
        normalized.strategy_id,
        list(normalized.dataset_snapshot_ids),
        normalized.as_of,
        normalized.available_at,
        _json_param(config),
        _json_param(metrics),
        _json_param(normalized.cost_assumptions),
        "succeeded",
        None,
        normalized.created_at,
    )


def _run_artifact_params(artifact: object) -> tuple[object, ...]:
    normalized = _normalize_run_artifact(artifact)
    if normalized.status not in RUN_ARTIFACT_STATUSES:
        allowed = sorted(RUN_ARTIFACT_STATUSES)
        raise ValueError(f"status must be one of {allowed}")
    return (
        normalized.run_id,
        normalized.run_type,
        normalized.started_at,
        normalized.completed_at,
        normalized.inputs_hash,
        normalized.output_hash,
        normalized.artifact_uri,
        normalized.status,
        normalized.error_summary,
        normalized.created_at,
    )


def _normalize_backtest_run(run: object) -> BacktestRun:
    if isinstance(run, BacktestRun):
        return run
    return BacktestRun(
        backtest_run_id=getattr(run, "backtest_run_id", None),
        strategy_id=getattr(run, "strategy_id", None),
        dataset_snapshot_ids=getattr(run, "dataset_snapshot_ids", None),
        validation_protocol=getattr(run, "validation_protocol", None),
        cost_assumptions=getattr(run, "cost_assumptions", None),
        metrics=getattr(run, "metrics", None),
        artifact_hash=getattr(run, "artifact_hash", None),
        as_of=getattr(run, "as_of", None),
        available_at=getattr(run, "available_at", None),
        created_at=getattr(run, "created_at", None),
    )


def _normalize_run_artifact(artifact: object) -> RunArtifact:
    if isinstance(artifact, RunArtifact):
        return artifact
    return RunArtifact(
        run_id=getattr(artifact, "run_id", None),
        run_type=getattr(artifact, "run_type", None),
        started_at=getattr(artifact, "started_at", None),
        completed_at=getattr(artifact, "completed_at", None),
        inputs_hash=getattr(artifact, "inputs_hash", None),
        output_hash=getattr(artifact, "output_hash", None),
        artifact_uri=getattr(artifact, "artifact_uri", None),
        status=getattr(artifact, "status", None),
        error_summary=getattr(artifact, "error_summary", None),
        created_at=getattr(artifact, "created_at", None),
    )


def _formula_versions(metrics: Mapping[str, object]) -> dict[str, object]:
    value = metrics.get("formula_versions")
    if not isinstance(value, Mapping) or not value:
        raise ValueError("metrics.formula_versions is required")

    normalized: dict[str, object] = {}
    for raw_key, raw_value in value.items():
        key = require_text(str(raw_key), "metrics.formula_versions key")
        if not isinstance(raw_value, str) or not raw_value.strip():
            raise ValueError(f"metrics.formula_versions.{key} is required")
        normalized[key] = raw_value.strip()
    return normalized


def _benchmark_version(metrics: Mapping[str, object]) -> str:
    value = metrics.get("benchmark_version")
    if not isinstance(value, str) or not value.strip():
        raise ValueError("metrics.benchmark_version is required")
    return value.strip()


def _json_param(value: object) -> str:
    return json.dumps(canonicalize(value), sort_keys=True, separators=(",", ":"))


__all__ = ["EvaluationRepository"]
