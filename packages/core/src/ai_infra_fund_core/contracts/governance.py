from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from .common import (
    DataQualityStatus,
    IncidentSeverity,
    coerce_enum,
    normalize_tuple,
    require_aware_datetime,
    require_non_empty_tuple,
    require_text,
)


@dataclass(frozen=True, slots=True)
class ModelInventoryEntry:
    model_inventory_id: str
    owner: str
    purpose: str
    inputs: tuple[str, ...]
    approval_status: str
    validation_date: date | None
    retraining_trigger: str
    retirement_criteria: str
    created_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "model_inventory_id", require_text(self.model_inventory_id, "model_inventory_id"))
        object.__setattr__(self, "owner", require_text(self.owner, "owner"))
        object.__setattr__(self, "purpose", require_text(self.purpose, "purpose"))
        object.__setattr__(self, "inputs", require_non_empty_tuple(normalize_tuple(self.inputs, "inputs"), "inputs"))
        object.__setattr__(self, "approval_status", require_text(self.approval_status, "approval_status"))
        object.__setattr__(self, "retraining_trigger", require_text(self.retraining_trigger, "retraining_trigger"))
        object.__setattr__(self, "retirement_criteria", require_text(self.retirement_criteria, "retirement_criteria"))
        require_aware_datetime(self.created_at, "created_at")


@dataclass(frozen=True, slots=True)
class IncidentRecord:
    incident_id: str
    severity: IncidentSeverity
    affected_artifacts: tuple[str, ...]
    freeze_status: str
    root_cause: str | None
    remediation: str | None
    reopen_criteria: str | None
    created_at: datetime
    resolved_at: datetime | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "incident_id", require_text(self.incident_id, "incident_id"))
        object.__setattr__(self, "severity", coerce_enum(self.severity, IncidentSeverity, "severity"))
        object.__setattr__(
            self,
            "affected_artifacts",
            require_non_empty_tuple(normalize_tuple(self.affected_artifacts, "affected_artifacts"), "affected_artifacts"),
        )
        object.__setattr__(self, "freeze_status", require_text(self.freeze_status, "freeze_status"))
        require_aware_datetime(self.created_at, "created_at")
        if self.resolved_at is not None:
            require_aware_datetime(self.resolved_at, "resolved_at")


@dataclass(frozen=True, slots=True)
class DataQualityCheck:
    check_id: str
    dataset_id: str | None
    check_name: str
    status: DataQualityStatus
    severity: IncidentSeverity
    observed_value: str | None
    threshold: str | None
    checked_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "check_id", require_text(self.check_id, "check_id"))
        object.__setattr__(self, "check_name", require_text(self.check_name, "check_name"))
        object.__setattr__(self, "status", coerce_enum(self.status, DataQualityStatus, "status"))
        object.__setattr__(self, "severity", coerce_enum(self.severity, IncidentSeverity, "severity"))
        require_aware_datetime(self.checked_at, "checked_at")
