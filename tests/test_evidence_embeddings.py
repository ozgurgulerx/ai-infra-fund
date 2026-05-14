from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
API_SRC = ROOT / "services" / "api" / "src"
for path in (CORE_SRC, API_SRC):
    sys.path.insert(0, str(path))

from ai_infra_fund_api.repositories.evidence_embeddings import EvidenceEmbeddingRepository  # noqa: E402
from ai_infra_fund_core.contracts.common import DataClass  # noqa: E402
from ai_infra_fund_core.evidence.chunking import EvidenceChunk  # noqa: E402
from ai_infra_fund_core.evidence.embeddings import (  # noqa: E402
    DeterministicEmbeddingProvider,
    EmbeddingContext,
    EmbeddingPolicyError,
    embed_evidence_chunks,
)
from ai_infra_fund_core.model_routing.profiles import load_model_profiles  # noqa: E402
from ai_infra_fund_core.model_routing.router import ModelRouter  # noqa: E402


CONFIG_PATH = ROOT / "config" / "model_profiles.yaml"


class EvidenceEmbeddingCoreTests(unittest.TestCase):
    def test_builds_local_embedding_context_from_configured_route(self) -> None:
        catalog = load_model_profiles(CONFIG_PATH)
        route = ModelRouter(catalog).resolve(
            "embeddings",
            data_classes=(DataClass.PRIVATE_RESEARCH,),
        )

        context = EmbeddingContext.from_model_profile(
            route.profile,
            dimension=4,
            data_classes=route.data_classes,
        )

        self.assertEqual(route.profile.model_id, context.embedding_model)
        self.assertEqual(route.profile.provider, context.provider)
        self.assertEqual(route.profile.endpoint_type, context.endpoint_type)
        self.assertEqual((DataClass.PRIVATE_RESEARCH,), context.data_classes)

    def test_deterministic_provider_returns_stable_configured_vectors(self) -> None:
        context = embedding_context(dimension=4)
        provider = DeterministicEmbeddingProvider()

        first = provider.embed_texts(
            ("GPU supply constraints", "HBM pricing remains tight"),
            context=context,
        )
        second = provider.embed_texts(
            ("GPU supply constraints", "HBM pricing remains tight"),
            context=context,
        )

        self.assertEqual(first, second)
        self.assertEqual([4, 4], [len(vector) for vector in first])
        self.assertNotEqual(first[0], first[1])

    def test_embeds_chunks_without_mutating_original_chunks(self) -> None:
        context = embedding_context(dimension=4)
        chunk = evidence_chunk(embedding_model="request-pending")

        embedded_chunks = embed_evidence_chunks(
            (chunk,),
            provider=DeterministicEmbeddingProvider(),
            context=context,
        )

        self.assertIsNone(chunk.embedding)
        self.assertEqual("request-pending", chunk.embedding_model)
        self.assertEqual(1, len(embedded_chunks))
        self.assertIsNot(chunk, embedded_chunks[0])
        self.assertEqual(context.embedding_model, embedded_chunks[0].embedding_model)
        self.assertIsNotNone(embedded_chunks[0].embedding)
        self.assertEqual(4, len(embedded_chunks[0].embedding or ()))

    def test_rejects_private_research_non_local_embedding_context(self) -> None:
        with self.assertRaisesRegex(EmbeddingPolicyError, "private_research embeddings must use a local profile"):
            EmbeddingContext(
                embedding_model="request-profile",
                provider="request-provider",
                endpoint_type="azure_ai_foundry",
                dimension=4,
                data_classes=(DataClass.PRIVATE_RESEARCH,),
            )

    def test_rejects_provider_dimension_mismatch_before_chunks_are_returned(self) -> None:
        context = embedding_context(dimension=4)

        with self.assertRaisesRegex(ValueError, "embedding dimension mismatch"):
            embed_evidence_chunks(
                (evidence_chunk(),),
                provider=WrongDimensionProvider(),
                context=context,
            )

    def test_embedding_module_has_no_cloud_model_clients_or_broker_surfaces(self) -> None:
        forbidden = [
            "from azure",
            "import azure",
            "from openai",
            "import openai",
            "from anthropic",
            "import anthropic",
            "place_order",
            "submit_order",
            "broker_client",
            "live_order",
            "order_execution",
        ]
        path = CORE_SRC / "ai_infra_fund_core" / "evidence" / "embeddings.py"

        text = path.read_text(encoding="utf-8")

        offenders = [pattern for pattern in forbidden if pattern in text]
        self.assertEqual([], offenders)


class EvidenceEmbeddingRepositoryTests(unittest.TestCase):
    def test_updates_chunk_embedding_with_parameterized_sql(self) -> None:
        connection = FakeConnection()
        chunk = evidence_chunk(
            embedding_model="configured-local-embedding",
            embedding=(0.25, 0.5, 0.75, 1.0),
        )

        saved = EvidenceEmbeddingRepository(connection, vector_dimension=4).save_chunk_embedding(chunk)

        self.assertEqual(chunk, saved)
        self.assertEqual(1, connection.commit_count)
        statement, params = connection.cursor_instance.executions[0]
        self.assertIn("UPDATE evidence.evidence_chunks", statement)
        self.assertIn("embedding = %s::vector", statement)
        self.assertNotIn(chunk.chunk_id, statement)
        self.assertNotIn(chunk.embedding_model, statement)
        self.assertNotIn("0.25", statement)
        self.assertEqual(
            (
                chunk.embedding_model,
                "[0.25,0.5,0.75,1.0]",
                chunk.chunk_id,
            ),
            params,
        )

    def test_rejects_dimension_mismatch_before_sql_execution(self) -> None:
        connection = FakeConnection()
        chunk = evidence_chunk(embedding=(0.25, 0.5))

        with self.assertRaisesRegex(ValueError, "embedding dimension mismatch"):
            EvidenceEmbeddingRepository(connection, vector_dimension=4).save_chunk_embedding(chunk)

        self.assertEqual(0, connection.commit_count)
        self.assertEqual([], connection.cursor_instance.executions)

    def test_rejects_batch_dimension_mismatch_before_any_sql_execution(self) -> None:
        connection = FakeConnection()
        valid_chunk = evidence_chunk(
            chunk_id="chunk-valid",
            content_hash="hash-valid",
            embedding=(0.25, 0.5, 0.75, 1.0),
        )
        invalid_chunk = evidence_chunk(
            chunk_id="chunk-invalid",
            content_hash="hash-invalid",
            embedding=(0.25, 0.5),
        )

        with self.assertRaisesRegex(ValueError, "embedding dimension mismatch"):
            EvidenceEmbeddingRepository(connection, vector_dimension=4).save_chunk_embeddings(
                (valid_chunk, invalid_chunk)
            )

        self.assertEqual(0, connection.commit_count)
        self.assertEqual([], connection.cursor_instance.executions)


class WrongDimensionProvider:
    def embed_texts(
        self,
        texts: tuple[str, ...],
        *,
        context: EmbeddingContext,
    ) -> tuple[tuple[float, ...], ...]:
        return tuple((0.1, 0.2) for _text in texts)


class FakeCursor:
    def __init__(self) -> None:
        self.executions: list[tuple[str, tuple[object, ...]]] = []

    def execute(self, statement: str, params: tuple[object, ...] | None = None) -> None:
        self.executions.append((statement, params or ()))

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, *_exc: object) -> None:
        return None


class FakeConnection:
    def __init__(self) -> None:
        self.cursor_instance = FakeCursor()
        self.commit_count = 0

    def cursor(self) -> FakeCursor:
        return self.cursor_instance

    def commit(self) -> None:
        self.commit_count += 1


def embedding_context(*, dimension: int) -> EmbeddingContext:
    return EmbeddingContext(
        embedding_model="configured-local-embedding",
        provider="local-test-provider",
        endpoint_type="local",
        dimension=dimension,
        data_classes=(DataClass.PRIVATE_RESEARCH,),
    )


def evidence_chunk(**overrides: object) -> EvidenceChunk:
    data = {
        "chunk_id": "chunk-1",
        "evidence_id": "evidence-1",
        "chunk_index": 0,
        "chunk_text": "HBM supply remains constrained for leading AI accelerators.",
        "span_ref": "p1:l2-l5",
        "content_hash": "hash-chunk-1",
        "embedding_model": "configured-local-embedding",
        "embedding": None,
    }
    data.update(overrides)
    return EvidenceChunk(**data)


if __name__ == "__main__":
    unittest.main()
