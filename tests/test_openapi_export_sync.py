from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
API_SRC = ROOT / "services" / "api" / "src"
SCRIPTS_DIR = ROOT / "scripts"
for path in (CORE_SRC, API_SRC, SCRIPTS_DIR):
    sys.path.insert(0, str(path))


class OpenApiExportSyncTests(unittest.TestCase):
    def test_committed_openapi_yaml_matches_export_script_output(self) -> None:
        from export_openapi import build_openapi_yaml

        committed_path = ROOT / "docs" / "api" / "openapi.yaml"
        self.assertTrue(
            committed_path.is_file(),
            f"committed openapi spec missing: {committed_path}",
        )

        generated = build_openapi_yaml()
        committed = committed_path.read_text(encoding="utf-8")

        if generated != committed:
            diff_hint = (
                "Committed docs/api/openapi.yaml is out of date. "
                "Re-run `python scripts/export_openapi.py` to regenerate."
            )
            self.assertEqual(generated, committed, diff_hint)

    def test_generated_yaml_lists_required_paths(self) -> None:
        from export_openapi import build_openapi_spec

        spec = build_openapi_spec()
        served = set(spec.get("paths", {}).keys())
        required = {
            "/health",
            "/version",
            "/ready",
            "/internal/agent/skill",
            "/internal/agent/openapi.json",
            "/internal/agent/openapi.yaml",
            "/internal/runs/latest",
            "/internal/advisory-chain/latest",
        }
        missing = required - served
        self.assertEqual(set(), missing, f"required paths missing: {missing}")


if __name__ == "__main__":
    unittest.main()
