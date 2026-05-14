from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from ai_infra_fund_core.contracts.common import DataClass, coerce_enum, require_text


@dataclass(frozen=True, slots=True)
class EvidenceSourceMetadata:
    source_uri: str
    source_type: str
    license_label: str
    data_class: DataClass
    local_only: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_uri", require_text(self.source_uri, "source_uri"))
        object.__setattr__(self, "source_type", require_text(self.source_type, "source_type"))
        object.__setattr__(self, "license_label", require_text(self.license_label, "license_label"))
        object.__setattr__(self, "data_class", coerce_enum(self.data_class, DataClass, "data_class"))
        object.__setattr__(self, "local_only", bool(self.local_only))


def normalize_evidence_source_metadata(
    *,
    source_uri: str,
    license_label: str,
    data_class: DataClass | str,
    local_only: bool | None = None,
) -> EvidenceSourceMetadata:
    normalized_source_uri = require_text(source_uri, "source_uri").strip()
    normalized_license_label = require_text(license_label, "license_label").strip()
    normalized_data_class = coerce_enum(data_class, DataClass, "data_class")
    normalized_local_only = (
        normalized_data_class is DataClass.PRIVATE_RESEARCH
        if local_only is None
        else bool(local_only)
    )

    return EvidenceSourceMetadata(
        source_uri=normalized_source_uri,
        source_type=_source_type_for_uri(normalized_source_uri),
        license_label=normalized_license_label,
        data_class=normalized_data_class,
        local_only=normalized_local_only,
    )


def _source_type_for_uri(source_uri: str) -> str:
    parsed = urlparse(source_uri)
    if parsed.scheme == "file":
        return "file"
    if parsed.scheme == "manual":
        return "manual"
    if parsed.scheme in {"http", "https"}:
        return "public_uri"
    raise ValueError("source_uri must use file, manual, http, or https scheme")
