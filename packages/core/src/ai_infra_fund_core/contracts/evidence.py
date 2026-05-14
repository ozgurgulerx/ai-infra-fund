from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from .common import (
    DataClass,
    coerce_enum,
    normalize_tuple,
    require_aware_datetime,
    require_content_hash,
    require_decimal_range,
    require_non_empty_tuple,
    require_text,
)


@dataclass(frozen=True, slots=True)
class DatasetSnapshot:
    snapshot_id: str
    dataset_name: str
    source: str
    license_label: str
    retrieved_at: datetime
    effective_at: datetime | None
    available_at: datetime
    storage_uri: str
    content_hash: str
    schema_version: str
    row_count: int | None
    data_class: DataClass
    created_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "snapshot_id", require_text(self.snapshot_id, "snapshot_id"))
        object.__setattr__(self, "dataset_name", require_text(self.dataset_name, "dataset_name"))
        object.__setattr__(self, "source", require_text(self.source, "source"))
        object.__setattr__(self, "license_label", require_text(self.license_label, "license_label"))
        object.__setattr__(self, "storage_uri", require_text(self.storage_uri, "storage_uri"))
        object.__setattr__(self, "content_hash", require_content_hash(self.content_hash))
        object.__setattr__(self, "schema_version", require_text(self.schema_version, "schema_version"))
        object.__setattr__(self, "data_class", coerce_enum(self.data_class, DataClass, "data_class"))
        require_aware_datetime(self.retrieved_at, "retrieved_at")
        if self.effective_at is not None:
            require_aware_datetime(self.effective_at, "effective_at")
        require_aware_datetime(self.available_at, "available_at")
        require_aware_datetime(self.created_at, "created_at")
        if self.row_count is not None and self.row_count < 0:
            raise ValueError("row_count must be non-negative")


@dataclass(frozen=True, slots=True)
class EvidenceItem:
    evidence_id: str
    source_uri: str
    source_type: str
    title: str | None
    publisher: str | None
    author: str | None
    published_at: datetime | None
    ingested_at: datetime
    content_hash: str
    license_label: str
    data_class: DataClass
    tickers: tuple[str, ...]
    themes: tuple[str, ...]
    summary: str | None
    storage_uri: str | None
    created_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence_id", require_text(self.evidence_id, "evidence_id"))
        object.__setattr__(self, "source_uri", require_text(self.source_uri, "source_uri"))
        object.__setattr__(self, "source_type", require_text(self.source_type, "source_type"))
        object.__setattr__(self, "content_hash", require_content_hash(self.content_hash))
        object.__setattr__(self, "license_label", require_text(self.license_label, "license_label"))
        object.__setattr__(self, "data_class", coerce_enum(self.data_class, DataClass, "data_class"))
        object.__setattr__(self, "tickers", tuple(str(ticker).upper() for ticker in normalize_tuple(self.tickers, "tickers")))
        object.__setattr__(self, "themes", tuple(str(theme) for theme in normalize_tuple(self.themes, "themes")))
        if self.published_at is not None:
            require_aware_datetime(self.published_at, "published_at")
        require_aware_datetime(self.ingested_at, "ingested_at")
        require_aware_datetime(self.created_at, "created_at")


@dataclass(frozen=True, slots=True)
class EvidenceClaim:
    claim_id: str
    evidence_id: str
    chunk_id: str | None
    ticker_or_theme: str
    claim_type: str
    direction: str | None
    magnitude: Decimal | None
    time_horizon: str
    confidence: Decimal
    quote_or_span_ref: str
    extracted_by_model_run_id: str | None
    validated_at: datetime | None
    created_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "claim_id", require_text(self.claim_id, "claim_id"))
        object.__setattr__(self, "evidence_id", require_text(self.evidence_id, "evidence_id"))
        object.__setattr__(self, "ticker_or_theme", require_text(self.ticker_or_theme, "ticker_or_theme"))
        object.__setattr__(self, "claim_type", require_text(self.claim_type, "claim_type"))
        object.__setattr__(self, "time_horizon", require_text(self.time_horizon, "time_horizon"))
        object.__setattr__(self, "confidence", require_decimal_range(self.confidence, "confidence", Decimal("0"), Decimal("1")))
        object.__setattr__(self, "quote_or_span_ref", require_text(self.quote_or_span_ref, "quote_or_span_ref"))
        if self.validated_at is not None:
            require_aware_datetime(self.validated_at, "validated_at")
        require_aware_datetime(self.created_at, "created_at")


@dataclass(frozen=True, slots=True)
class FeatureSet:
    feature_set_id: str
    dataset_snapshot_ids: tuple[str, ...]
    formula_version: str
    point_in_time_rule: str
    owner: str
    as_of: datetime
    available_at: datetime
    input_snapshot_hash: str
    created_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "feature_set_id", require_text(self.feature_set_id, "feature_set_id"))
        object.__setattr__(
            self,
            "dataset_snapshot_ids",
            require_non_empty_tuple(normalize_tuple(self.dataset_snapshot_ids, "dataset_snapshot_ids"), "dataset_snapshot_ids"),
        )
        object.__setattr__(self, "formula_version", require_text(self.formula_version, "formula_version"))
        object.__setattr__(self, "point_in_time_rule", require_text(self.point_in_time_rule, "point_in_time_rule"))
        object.__setattr__(self, "owner", require_text(self.owner, "owner"))
        object.__setattr__(self, "input_snapshot_hash", require_content_hash(self.input_snapshot_hash, "input_snapshot_hash"))
        require_aware_datetime(self.as_of, "as_of")
        require_aware_datetime(self.available_at, "available_at")
        require_aware_datetime(self.created_at, "created_at")
