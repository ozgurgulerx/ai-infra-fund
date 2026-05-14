from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping

from ai_infra_fund_core.contracts.common import (
    normalize_tuple,
    require_aware_datetime,
    require_non_empty_tuple,
    require_text,
    stable_hash_payload,
)


@dataclass(frozen=True, slots=True)
class ShadowModeEvaluationRecord:
    evaluation_id: str
    production_recommendation_id: str
    strategy_id: str
    data_snapshot_ids: tuple[str, ...]
    run_artifact_ids: tuple[str, ...]
    model_run_id: str
    shadow_output_id: str
    formula_version: str
    benchmark_version: str
    model_output_metadata: dict[str, Any]
    metrics: dict[str, Any]
    affects_production: bool
    created_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "evaluation_id", require_text(self.evaluation_id, "evaluation_id"))
        object.__setattr__(
            self,
            "production_recommendation_id",
            require_text(self.production_recommendation_id, "production_recommendation_id"),
        )
        object.__setattr__(self, "strategy_id", require_text(self.strategy_id, "strategy_id"))
        object.__setattr__(
            self,
            "data_snapshot_ids",
            require_non_empty_tuple(normalize_tuple(self.data_snapshot_ids, "data_snapshot_ids"), "data_snapshot_ids"),
        )
        object.__setattr__(
            self,
            "run_artifact_ids",
            require_non_empty_tuple(normalize_tuple(self.run_artifact_ids, "run_artifact_ids"), "run_artifact_ids"),
        )
        object.__setattr__(self, "model_run_id", require_text(self.model_run_id, "model_run_id"))
        object.__setattr__(self, "shadow_output_id", require_text(self.shadow_output_id, "shadow_output_id"))
        object.__setattr__(self, "formula_version", require_text(self.formula_version, "formula_version"))
        object.__setattr__(self, "benchmark_version", require_text(self.benchmark_version, "benchmark_version"))
        if not self.model_output_metadata:
            raise ValueError("model_output_metadata must not be empty")
        if not self.metrics:
            raise ValueError("metrics must not be empty")
        if self.affects_production:
            raise ValueError("shadow-mode evaluation records must not affect production recommendations")
        object.__setattr__(self, "model_output_metadata", dict(self.model_output_metadata))
        object.__setattr__(self, "metrics", dict(self.metrics))
        require_aware_datetime(self.created_at, "created_at")

    @property
    def recommendation_id(self) -> str:
        return self.production_recommendation_id


def create_shadow_mode_record(
    *,
    production_recommendation_id: str,
    strategy_id: str,
    data_snapshot_ids: tuple[str, ...],
    run_artifact_ids: tuple[str, ...],
    model_run_id: str,
    shadow_output_id: str,
    formula_version: str,
    benchmark_version: str,
    model_output_metadata: Mapping[str, Any],
    metrics: Mapping[str, Any],
    created_at: datetime,
) -> ShadowModeEvaluationRecord:
    normalized_snapshots = require_non_empty_tuple(normalize_tuple(data_snapshot_ids, "data_snapshot_ids"), "data_snapshot_ids")
    normalized_artifacts = require_non_empty_tuple(normalize_tuple(run_artifact_ids, "run_artifact_ids"), "run_artifact_ids")
    metadata = dict(model_output_metadata)
    metric_values = dict(metrics)
    evaluation_id = _shadow_evaluation_id(
        production_recommendation_id=production_recommendation_id,
        strategy_id=strategy_id,
        data_snapshot_ids=normalized_snapshots,
        run_artifact_ids=normalized_artifacts,
        model_run_id=model_run_id,
        shadow_output_id=shadow_output_id,
        formula_version=formula_version,
        benchmark_version=benchmark_version,
        model_output_metadata=metadata,
        metrics=metric_values,
        created_at=created_at,
    )
    return ShadowModeEvaluationRecord(
        evaluation_id=evaluation_id,
        production_recommendation_id=production_recommendation_id,
        strategy_id=strategy_id,
        data_snapshot_ids=normalized_snapshots,
        run_artifact_ids=normalized_artifacts,
        model_run_id=model_run_id,
        shadow_output_id=shadow_output_id,
        formula_version=formula_version,
        benchmark_version=benchmark_version,
        model_output_metadata=metadata,
        metrics=metric_values,
        affects_production=False,
        created_at=created_at,
    )


def _shadow_evaluation_id(
    *,
    production_recommendation_id: str,
    strategy_id: str,
    data_snapshot_ids: tuple[str, ...],
    run_artifact_ids: tuple[str, ...],
    model_run_id: str,
    shadow_output_id: str,
    formula_version: str,
    benchmark_version: str,
    model_output_metadata: Mapping[str, Any],
    metrics: Mapping[str, Any],
    created_at: datetime,
) -> str:
    digest = stable_hash_payload(
        {
            "production_recommendation_id": production_recommendation_id,
            "strategy_id": strategy_id,
            "data_snapshot_ids": data_snapshot_ids,
            "run_artifact_ids": run_artifact_ids,
            "model_run_id": model_run_id,
            "shadow_output_id": shadow_output_id,
            "formula_version": formula_version,
            "benchmark_version": benchmark_version,
            "model_output_metadata": dict(model_output_metadata),
            "metrics": dict(metrics),
            "created_at": created_at,
        }
    )
    return f"shadow-eval-{digest[:16]}"
