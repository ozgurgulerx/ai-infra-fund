from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
API_SRC = ROOT / "services" / "api" / "src"
for path in (CORE_SRC, API_SRC):
    sys.path.insert(0, str(path))


REQUIRED_PATHS: tuple[str, ...] = (
    "/health",
    "/version",
    "/ready",
    "/internal/agent/skill",
    "/internal/agent/openapi.json",
    "/internal/agent/openapi.yaml",
    "/internal/advisory-chain/demo",
    "/internal/advisory-chain/latest",
    "/internal/recommendations",
    "/internal/recommendations/{recommendation_id}",
    "/internal/runs/latest",
    "/internal/runs/{run_id}",
    "/internal/evaluations",
    "/internal/evidence/manual",
    "/internal/evidence/file",
    "/internal/trade-journal/entries",
)


SKILL_DOC = """---
title: ai-infra-fund agent bootstrap
status: advisory-only
---

# ai-infra-fund Agent Bootstrap

This system is **advisory-only**. No live order placement.

Deterministic code owns scores, risk, backtests, and target weights.

PostgreSQL + pgvector is the v1 durable store.

## Forbidden agent actions

Agents must not attempt placing, submitting, routing, or executing
real-world trades from this surface. There is no broker connection.
"""


class AgentBootstrapApiTests(unittest.TestCase):
    def test_skill_endpoint_returns_markdown_with_required_phrases(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        with tempfile.TemporaryDirectory() as workspace:
            skill_path = Path(workspace) / "SKILL.md"
            skill_path.write_text(SKILL_DOC, encoding="utf-8")
            openapi_path = Path(workspace) / "openapi.yaml"
            openapi_path.write_text(
                "openapi: 3.1.0\ninfo:\n  title: Test\n", encoding="utf-8"
            )

            client = TestClient(
                main.create_app(
                    agent_skill_path=skill_path,
                    agent_openapi_yaml_path=openapi_path,
                )
            )

            response = client.get("/internal/agent/skill")

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertIn("data", payload)
        self.assertEqual("markdown", payload["data"]["format"])
        content = payload["data"]["content"]
        self.assertIn("advisory-only", content)
        self.assertIn("No live order placement", content)
        self.assertIn("Deterministic code owns scores", content)
        self.assertIn("PostgreSQL + pgvector", content)

    def test_openapi_json_endpoint_lists_all_required_paths(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        with tempfile.TemporaryDirectory() as workspace:
            skill_path = Path(workspace) / "SKILL.md"
            skill_path.write_text(SKILL_DOC, encoding="utf-8")
            openapi_path = Path(workspace) / "openapi.yaml"
            openapi_path.write_text("openapi: 3.1.0\n", encoding="utf-8")

            client = TestClient(
                main.create_app(
                    agent_skill_path=skill_path,
                    agent_openapi_yaml_path=openapi_path,
                )
            )

            response = client.get("/internal/agent/openapi.json")

        self.assertEqual(200, response.status_code)
        spec = response.json()
        self.assertIn("paths", spec)
        served_paths = set(spec["paths"].keys())
        missing = [path for path in REQUIRED_PATHS if path not in served_paths]
        self.assertEqual([], missing, f"missing OpenAPI paths: {missing}")

    def test_openapi_yaml_endpoint_serves_committed_yaml(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        with tempfile.TemporaryDirectory() as workspace:
            skill_path = Path(workspace) / "SKILL.md"
            skill_path.write_text(SKILL_DOC, encoding="utf-8")
            openapi_path = Path(workspace) / "openapi.yaml"
            openapi_path.write_text(
                "openapi: 3.1.0\ninfo:\n  title: ai-infra-fund\n",
                encoding="utf-8",
            )

            client = TestClient(
                main.create_app(
                    agent_skill_path=skill_path,
                    agent_openapi_yaml_path=openapi_path,
                )
            )

            response = client.get("/internal/agent/openapi.yaml")

        self.assertEqual(200, response.status_code)
        self.assertIn("text/yaml", response.headers["content-type"])
        body = response.text
        self.assertIn("openapi: 3.1.0", body)
        self.assertIn("ai-infra-fund", body)

    def test_skill_endpoint_returns_503_when_skill_doc_missing(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        with tempfile.TemporaryDirectory() as workspace:
            skill_path = Path(workspace) / "missing.md"
            openapi_path = Path(workspace) / "openapi.yaml"
            openapi_path.write_text("openapi: 3.1.0\n", encoding="utf-8")

            client = TestClient(
                main.create_app(
                    agent_skill_path=skill_path,
                    agent_openapi_yaml_path=openapi_path,
                )
            )

            response = client.get("/internal/agent/skill")

        self.assertEqual(503, response.status_code)
        self.assertIn("error", response.json())

    def test_agent_routes_reject_mutation_methods(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        with tempfile.TemporaryDirectory() as workspace:
            skill_path = Path(workspace) / "SKILL.md"
            skill_path.write_text(SKILL_DOC, encoding="utf-8")
            openapi_path = Path(workspace) / "openapi.yaml"
            openapi_path.write_text("openapi: 3.1.0\n", encoding="utf-8")

            client = TestClient(
                main.create_app(
                    agent_skill_path=skill_path,
                    agent_openapi_yaml_path=openapi_path,
                )
            )

            for path in (
                "/internal/agent/skill",
                "/internal/agent/openapi.json",
                "/internal/agent/openapi.yaml",
            ):
                for request in (client.post, client.put, client.patch, client.delete):
                    with self.subTest(path=path, method=request.__name__):
                        response = request(path)
                        self.assertEqual(405, response.status_code)


class SkillDocumentTests(unittest.TestCase):
    def test_committed_skill_doc_exists_and_has_required_phrases(self) -> None:
        skill_path = ROOT / "docs" / "agent" / "SKILL.md"
        self.assertTrue(
            skill_path.is_file(), f"missing committed skill doc: {skill_path}"
        )
        text = skill_path.read_text(encoding="utf-8")
        for phrase in (
            "advisory-only",
            "No live order placement",
            "Deterministic code owns scores",
            "PostgreSQL + pgvector",
        ):
            self.assertIn(phrase, text, f"committed SKILL.md missing phrase: {phrase}")


if __name__ == "__main__":
    unittest.main()
