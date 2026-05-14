from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class LocalFileStatus(str, Enum):
    ACCEPTED = "accepted"
    QUARANTINED = "quarantined"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class LocalFileValidation:
    path: Path
    status: LocalFileStatus
    reason: str


ALLOWED_EVIDENCE_SUFFIXES = {".csv", ".md", ".pdf", ".txt"}
SENSITIVE_PDF_MARKERS = (
    "schwab",
    "routing number",
    "wire transfer",
    "account transfer",
    "transfer instructions",
)


def validate_local_file_candidate(path: str | Path) -> LocalFileValidation:
    candidate = Path(path)
    if not candidate.exists():
        return LocalFileValidation(candidate, LocalFileStatus.REJECTED, "file does not exist")
    if not candidate.is_file():
        return LocalFileValidation(candidate, LocalFileStatus.REJECTED, "path must be a file")

    suffix = candidate.suffix.lower()
    if suffix not in ALLOWED_EVIDENCE_SUFFIXES:
        return LocalFileValidation(candidate, LocalFileStatus.REJECTED, f"unsupported file extension: {suffix}")

    if suffix == ".pdf" and _looks_like_sensitive_pdf(candidate):
        return LocalFileValidation(candidate, LocalFileStatus.QUARANTINED, "sensitive PDF quarantined")

    return LocalFileValidation(candidate, LocalFileStatus.ACCEPTED, "accepted")


def ensure_local_file_accepted(path: str | Path) -> Path:
    validation = validate_local_file_candidate(path)
    if validation.status is not LocalFileStatus.ACCEPTED:
        raise ValueError(f"{validation.path.name} {validation.status.value}: {validation.reason}")
    return validation.path


def _looks_like_sensitive_pdf(path: Path) -> bool:
    haystack = path.name.lower()
    try:
        haystack = f"{haystack}\n{path.read_bytes()[:8192].decode('utf-8', errors='ignore').lower()}"
    except OSError:
        return True
    return any(marker in haystack for marker in SENSITIVE_PDF_MARKERS)
