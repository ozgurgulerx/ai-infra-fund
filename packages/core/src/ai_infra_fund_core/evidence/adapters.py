from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TypeAlias

from ai_infra_fund_core.contracts.common import DataClass, require_text
from ai_infra_fund_core.contracts.evidence import EvidenceItem

from .provenance import build_evidence_item
from .sources import EvidenceSourceMetadata, normalize_evidence_source_metadata


PathLike: TypeAlias = str | Path
PdfTextExtractor: TypeAlias = Callable[[Path], str]


class UnsafeLocalEvidencePathError(ValueError):
    """Raised when a local evidence path escapes its configured root."""


class PdfAdapterUnavailableError(RuntimeError):
    """Raised when PDF text extraction is disabled or unavailable."""


@dataclass(frozen=True, slots=True)
class LocalEvidenceDocument:
    path: Path
    content: str
    source_metadata: EvidenceSourceMetadata
    evidence_item: EvidenceItem


def read_local_text_evidence(
    path: PathLike,
    *,
    allowed_root: PathLike,
    title: str,
    ingested_at: datetime,
    license_label: str,
    data_class: DataClass | str = DataClass.PRIVATE_RESEARCH,
    publisher: str | None = None,
    author: str | None = None,
    published_at: datetime | None = None,
    tickers: Iterable[str] | None = None,
    themes: Iterable[str] | None = None,
    summary: str | None = None,
    encoding: str = "utf-8",
) -> LocalEvidenceDocument:
    resolved_path = _resolve_safe_existing_file(path, allowed_root=allowed_root)
    content = resolved_path.read_text(encoding=encoding)
    return _build_local_document(
        resolved_path=resolved_path,
        content=content,
        title=title,
        publisher=publisher,
        author=author,
        published_at=published_at,
        ingested_at=ingested_at,
        license_label=license_label,
        data_class=data_class,
        tickers=tickers,
        themes=themes,
        summary=summary,
    )


def read_local_markdown_evidence(
    path: PathLike,
    *,
    allowed_root: PathLike,
    title: str,
    ingested_at: datetime,
    license_label: str,
    data_class: DataClass | str = DataClass.PRIVATE_RESEARCH,
    publisher: str | None = None,
    author: str | None = None,
    published_at: datetime | None = None,
    tickers: Iterable[str] | None = None,
    themes: Iterable[str] | None = None,
    summary: str | None = None,
    encoding: str = "utf-8",
) -> LocalEvidenceDocument:
    return read_local_text_evidence(
        path,
        allowed_root=allowed_root,
        title=title,
        publisher=publisher,
        author=author,
        published_at=published_at,
        ingested_at=ingested_at,
        license_label=license_label,
        data_class=data_class,
        tickers=tickers,
        themes=themes,
        summary=summary,
        encoding=encoding,
    )


def read_local_pdf_evidence(
    path: PathLike,
    *,
    allowed_root: PathLike,
    title: str,
    ingested_at: datetime,
    license_label: str,
    data_class: DataClass | str = DataClass.PRIVATE_RESEARCH,
    publisher: str | None = None,
    author: str | None = None,
    published_at: datetime | None = None,
    tickers: Iterable[str] | None = None,
    themes: Iterable[str] | None = None,
    summary: str | None = None,
    enabled: bool = True,
    text_extractor: PdfTextExtractor | None = None,
) -> LocalEvidenceDocument:
    if not enabled:
        raise PdfAdapterUnavailableError("PDF evidence adapter is disabled by configuration")

    resolved_path = _resolve_safe_existing_file(path, allowed_root=allowed_root)
    content = (
        text_extractor(resolved_path)
        if text_extractor is not None
        else _extract_pdf_text_with_optional_dependency(resolved_path)
    )
    content = require_text(content, "pdf_text")
    return _build_local_document(
        resolved_path=resolved_path,
        content=content,
        title=title,
        publisher=publisher,
        author=author,
        published_at=published_at,
        ingested_at=ingested_at,
        license_label=license_label,
        data_class=data_class,
        tickers=tickers,
        themes=themes,
        summary=summary,
    )


def _build_local_document(
    *,
    resolved_path: Path,
    content: str,
    title: str,
    publisher: str | None,
    author: str | None,
    published_at: datetime | None,
    ingested_at: datetime,
    license_label: str,
    data_class: DataClass | str,
    tickers: Iterable[str] | None,
    themes: Iterable[str] | None,
    summary: str | None,
) -> LocalEvidenceDocument:
    source_uri = resolved_path.as_uri()
    source_metadata = normalize_evidence_source_metadata(
        source_uri=source_uri,
        license_label=license_label,
        data_class=data_class,
    )
    evidence_item = build_evidence_item(
        text=content,
        source_uri=source_metadata.source_uri,
        source_type=source_metadata.source_type,
        title=title,
        publisher=publisher,
        author=author,
        published_at=published_at,
        ingested_at=ingested_at,
        license_label=source_metadata.license_label,
        data_class=source_metadata.data_class,
        tickers=tickers,
        themes=themes,
        summary=summary,
        storage_uri=source_metadata.source_uri,
    )
    return LocalEvidenceDocument(
        path=resolved_path,
        content=content,
        source_metadata=source_metadata,
        evidence_item=evidence_item,
    )


def _resolve_safe_existing_file(path: PathLike, *, allowed_root: PathLike) -> Path:
    root = Path(allowed_root).expanduser().resolve(strict=True)
    candidate = Path(path).expanduser()
    candidate_path = candidate if candidate.is_absolute() else root / candidate

    try:
        resolved_path = candidate_path.resolve(strict=True)
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"local evidence file not found: {candidate}") from exc

    if not resolved_path.is_file():
        raise FileNotFoundError(f"local evidence path is not a file: {candidate}")

    try:
        resolved_path.relative_to(root)
    except ValueError as exc:
        raise UnsafeLocalEvidencePathError(
            f"local evidence path must stay within allowed_root: {candidate}"
        ) from exc

    return resolved_path


def _extract_pdf_text_with_optional_dependency(path: Path) -> str:
    reader_type = _load_pdf_reader()
    reader = reader_type(str(path))
    page_text = tuple((page.extract_text() or "") for page in reader.pages)
    return "\n".join(text for text in page_text if text)


def _load_pdf_reader() -> type:
    try:
        from pypdf import PdfReader

        return PdfReader
    except ModuleNotFoundError:
        pass

    try:
        from PyPDF2 import PdfReader

        return PdfReader
    except ModuleNotFoundError as exc:
        raise PdfAdapterUnavailableError(
            "PDF evidence extraction requires optional dependency pypdf or PyPDF2, "
            "or an explicit text_extractor"
        ) from exc


__all__ = [
    "LocalEvidenceDocument",
    "PdfAdapterUnavailableError",
    "UnsafeLocalEvidencePathError",
    "read_local_markdown_evidence",
    "read_local_pdf_evidence",
    "read_local_text_evidence",
]
