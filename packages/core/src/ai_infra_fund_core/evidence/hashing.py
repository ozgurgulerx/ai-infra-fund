from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ai_infra_fund_core.contracts.common import stable_hash_payload


def compute_content_hash(content: str | bytes, *, metadata: Mapping[str, Any] | None = None) -> str:
    """Return a stable SHA-256 hash for source content and optional metadata."""
    if isinstance(content, bytes):
        payload: dict[str, Any] = {
            "content_encoding": "bytes.hex",
            "content": content.hex(),
        }
    elif isinstance(content, str):
        payload = {
            "content_encoding": "utf-8",
            "content": content,
        }
    else:
        raise TypeError("content must be str or bytes")

    if metadata is not None:
        if not isinstance(metadata, Mapping):
            raise TypeError("metadata must be a mapping")
        payload["metadata"] = dict(metadata)

    return stable_hash_payload(payload)


__all__ = ["compute_content_hash"]
