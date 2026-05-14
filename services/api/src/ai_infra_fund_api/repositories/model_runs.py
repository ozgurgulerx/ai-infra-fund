from __future__ import annotations

from typing import Protocol

from ai_infra_fund_core.contracts.model_runs import ModelRun


class Cursor(Protocol):
    def execute(self, statement: str, params: tuple[object, ...] | None = None) -> None:
        ...


class Connection(Protocol):
    def cursor(self) -> object:
        ...

    def commit(self) -> None:
        ...


INSERT_MODEL_RUN_SQL = """
INSERT INTO audit.model_runs (
    model_run_id,
    task_role,
    model_id,
    deployment,
    provider,
    prompt_version,
    input_hash,
    output_hash,
    latency_ms,
    token_estimate_input,
    token_estimate_output,
    cost_estimate,
    schema_valid,
    retry_count,
    data_classes,
    status,
    error_summary,
    created_at
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
);
"""


class ModelRunRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def save(self, model_run: ModelRun) -> ModelRun:
        with self._connection.cursor() as cursor:
            cursor.execute(INSERT_MODEL_RUN_SQL, _params(model_run))
        self._connection.commit()
        return model_run


def _params(model_run: ModelRun) -> tuple[object, ...]:
    return (
        model_run.model_run_id,
        model_run.task_role,
        model_run.model_id,
        model_run.deployment,
        model_run.provider,
        model_run.prompt_version,
        model_run.input_hash,
        model_run.output_hash,
        model_run.latency_ms,
        model_run.token_estimate_input,
        model_run.token_estimate_output,
        None,
        model_run.schema_valid,
        model_run.retry_count,
        [data_class.value for data_class in model_run.data_classes],
        model_run.status.value,
        model_run.error_summary,
        model_run.created_at,
    )
