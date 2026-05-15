from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path


@dataclass(frozen=True, slots=True)
class StoredCapture:
    content_hash: str
    storage_uri: str
    byte_size: int
    body_path: Path
    sidecar_path: Path


class LocalCaptureStore:
    """WARC-lite raw capture store backed by the local filesystem.

    Bodies are written to ``<root>/captures/<sha[:2]>/<sha>.body`` with a sidecar
    ``<sha>.meta.json`` recording the response headers. Hash is over the body
    bytes, so identical payloads dedup naturally and align with
    ``evidence.source_raw_captures.content_hash`` UNIQUE.
    """

    def __init__(self, root: Path | str) -> None:
        self._root = Path(root)
        (self._root / "captures").mkdir(parents=True, exist_ok=True)

    def store(
        self, body: bytes, *, response_headers: Mapping[str, str]
    ) -> StoredCapture:
        if not isinstance(body, (bytes, bytearray)):
            raise TypeError("body must be bytes-like")
        if not body:
            raise ValueError("body must be non-empty")

        content_hash = sha256(body).hexdigest()
        shard = content_hash[:2]
        shard_dir = self._root / "captures" / shard
        shard_dir.mkdir(parents=True, exist_ok=True)
        body_path = shard_dir / f"{content_hash}.body"
        sidecar_path = shard_dir / f"{content_hash}.meta.json"

        if not body_path.exists():
            body_path.write_bytes(bytes(body))

        sidecar_path.write_text(
            json.dumps(
                {
                    "byte_size": len(body),
                    "response_headers": dict(response_headers),
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
            encoding="utf-8",
        )

        return StoredCapture(
            content_hash=content_hash,
            storage_uri=f"file://captures/{shard}/{content_hash}.body",
            byte_size=len(body),
            body_path=body_path,
            sidecar_path=sidecar_path,
        )


__all__ = ["LocalCaptureStore", "StoredCapture"]
