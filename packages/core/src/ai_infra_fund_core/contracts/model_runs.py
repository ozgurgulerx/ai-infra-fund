from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .common import (
    DataClass,
    ModelRunStatus,
    coerce_enum,
    normalize_tuple,
    require_aware_datetime,
    require_content_hash,
    require_text,
)


@dataclass(frozen=True, slots=True)
class ModelRun:
    model_run_id: str
    task_role: str
    model_id: str
    deployment: str
    provider: str
    prompt_version: str
    input_hash: str
    output_hash: str | None
    latency_ms: int | None
    token_estimate_input: int | None
    token_estimate_output: int | None
    schema_valid: bool
    retry_count: int
    data_classes: tuple[DataClass, ...]
    status: ModelRunStatus
    error_summary: str | None
    created_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "model_run_id", require_text(self.model_run_id, "model_run_id"))
        object.__setattr__(self, "task_role", require_text(self.task_role, "task_role"))
        object.__setattr__(self, "model_id", require_text(self.model_id, "model_id"))
        object.__setattr__(self, "deployment", require_text(self.deployment, "deployment"))
        object.__setattr__(self, "provider", require_text(self.provider, "provider"))
        object.__setattr__(self, "prompt_version", require_text(self.prompt_version, "prompt_version"))
        object.__setattr__(self, "input_hash", require_content_hash(self.input_hash, "input_hash"))
        if self.output_hash is not None:
            object.__setattr__(self, "output_hash", require_content_hash(self.output_hash, "output_hash"))
        if self.latency_ms is not None and self.latency_ms < 0:
            raise ValueError("latency_ms must be non-negative")
        if self.token_estimate_input is not None and self.token_estimate_input < 0:
            raise ValueError("token_estimate_input must be non-negative")
        if self.token_estimate_output is not None and self.token_estimate_output < 0:
            raise ValueError("token_estimate_output must be non-negative")
        if self.retry_count < 0:
            raise ValueError("retry_count must be non-negative")
        object.__setattr__(
            self,
            "data_classes",
            tuple(coerce_enum(data_class, DataClass, "data_classes") for data_class in normalize_tuple(self.data_classes, "data_classes")),
        )
        object.__setattr__(self, "status", coerce_enum(self.status, ModelRunStatus, "status"))
        if self.status is ModelRunStatus.SUCCESS and not self.output_hash:
            raise ValueError("successful model runs require output_hash")
        require_aware_datetime(self.created_at, "created_at")
