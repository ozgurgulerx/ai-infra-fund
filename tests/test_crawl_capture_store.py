from __future__ import annotations

import json
import sys
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
sys.path.insert(0, str(CORE_SRC))

from ai_infra_fund_core.equity_intelligence.capture import (  # noqa: E402
    LocalCaptureStore,
    StoredCapture,
)


class LocalCaptureStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def test_store_writes_body_under_sha_shard_and_returns_stored_capture(self) -> None:
        store = LocalCaptureStore(self.root)
        body = b"<html><body>NVIDIA Q1 results</body></html>"

        stored = store.store(body, response_headers={"Content-Type": "text/html"})

        self.assertIsInstance(stored, StoredCapture)
        expected_hash = sha256(body).hexdigest()
        self.assertEqual(expected_hash, stored.content_hash)
        self.assertEqual(len(body), stored.byte_size)
        expected_path = (
            self.root / "captures" / expected_hash[:2] / f"{expected_hash}.body"
        )
        self.assertTrue(expected_path.exists())
        self.assertEqual(body, expected_path.read_bytes())
        self.assertEqual(
            f"file://captures/{expected_hash[:2]}/{expected_hash}.body",
            stored.storage_uri,
        )

    def test_store_writes_sidecar_metadata_with_response_headers(self) -> None:
        store = LocalCaptureStore(self.root)
        body = b"hello world"
        headers = {
            "Content-Type": "application/json",
            "Etag": "abc",
            "Last-Modified": "Wed",
        }

        stored = store.store(body, response_headers=headers)
        sidecar = (
            self.root
            / "captures"
            / stored.content_hash[:2]
            / f"{stored.content_hash}.meta.json"
        )

        self.assertTrue(sidecar.exists())
        metadata = json.loads(sidecar.read_text(encoding="utf-8"))
        self.assertEqual(metadata["response_headers"], headers)
        self.assertEqual(metadata["byte_size"], len(body))

    def test_store_is_idempotent_on_repeated_writes_of_same_bytes(self) -> None:
        store = LocalCaptureStore(self.root)
        body = b"same body twice"

        first = store.store(body, response_headers={})
        second = store.store(body, response_headers={})

        self.assertEqual(first.content_hash, second.content_hash)
        self.assertEqual(first.storage_uri, second.storage_uri)
        # Single body file on disk under the shard.
        shard_dir = self.root / "captures" / first.content_hash[:2]
        body_files = list(shard_dir.glob("*.body"))
        self.assertEqual(1, len(body_files))

    def test_store_rejects_empty_body(self) -> None:
        store = LocalCaptureStore(self.root)
        with self.assertRaises(ValueError):
            store.store(b"", response_headers={})


if __name__ == "__main__":
    unittest.main()
