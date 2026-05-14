from __future__ import annotations

from dataclasses import dataclass

from ai_infra_fund_core.contracts.common import DataClass, coerce_enum, normalize_tuple, require_text


@dataclass(frozen=True, slots=True)
class SourcePolicy:
    source_id: str
    publisher: str
    license_label: str
    data_class: DataClass
    allowed_uses: tuple[str, ...]
    requires_attribution: bool = True
    local_only: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_id", require_text(self.source_id, "source_id").strip())
        object.__setattr__(self, "publisher", require_text(self.publisher, "publisher").strip())
        object.__setattr__(self, "license_label", require_text(self.license_label, "license_label").strip())
        object.__setattr__(self, "data_class", coerce_enum(self.data_class, DataClass, "data_class"))
        allowed_uses = tuple(require_text(str(use), "allowed_use").strip() for use in normalize_tuple(self.allowed_uses, "allowed_uses"))
        if not allowed_uses:
            raise ValueError("allowed_uses must not be empty")
        object.__setattr__(self, "allowed_uses", allowed_uses)
        object.__setattr__(self, "requires_attribution", bool(self.requires_attribution))
        object.__setattr__(self, "local_only", bool(self.local_only))
