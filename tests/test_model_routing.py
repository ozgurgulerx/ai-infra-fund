from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
sys.path.insert(0, str(CORE_SRC))

from ai_infra_fund_core.contracts.common import DataClass  # noqa: E402
from ai_infra_fund_core.model_routing.profiles import (  # noqa: E402
    ModelProfileCatalog,
    ModelProfileConfigError,
    load_model_profiles,
)
from ai_infra_fund_core.model_routing.router import (  # noqa: E402
    ModelRouteDenied,
    ModelRouter,
)


CONFIG_PATH = ROOT / "config" / "model_profiles.yaml"
REQUIRED_TASK_ROLES = (
    "source_classification",
    "evidence_summary",
    "evidence_claim_extraction",
    "orchestration_validation",
    "adversarial_review",
    "local_fallback",
    "embeddings",
)
REQUIRED_PROFILE_FIELDS = (
    "model_id",
    "deployment",
    "provider",
    "endpoint_type",
    "task_roles",
    "quota_rpm",
    "quota_tpm",
    "cost_class",
    "max_context",
    "privacy_class",
    "allowed_data_classes",
    "fallback_chain",
    "structured_output_support",
    "notes",
)


class ModelProfileLoadingTests(unittest.TestCase):
    def test_loads_model_profiles_with_required_schema(self) -> None:
        catalog = load_model_profiles(CONFIG_PATH)

        self.assertGreaterEqual(len(catalog.profiles), len(REQUIRED_TASK_ROLES))
        for profile in catalog.profiles.values():
            with self.subTest(profile=profile.profile_id):
                for field_name in REQUIRED_PROFILE_FIELDS:
                    self.assertTrue(hasattr(profile, field_name), field_name)
                self.assertTrue(profile.profile_id)
                self.assertTrue(profile.task_roles)
                self.assertIsInstance(profile.structured_output_support, bool)
                self.assertNotIn(DataClass.SECRETS, profile.allowed_data_classes)

    def test_rejects_invalid_model_profile_config(self) -> None:
        invalid = {
            "version": 1,
            "models": {
                "broken": {
                    "model_id": "broken-model",
                    "deployment": "broken-deployment",
                }
            },
        }

        with self.assertRaises(ModelProfileConfigError):
            ModelProfileCatalog.from_mapping(invalid)

    def test_rejects_unknown_fallback_profile(self) -> None:
        invalid = _single_profile_config(fallback_chain=("missing_profile",))

        with self.assertRaises(ModelProfileConfigError):
            ModelProfileCatalog.from_mapping(invalid)


class ModelRouterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = load_model_profiles(CONFIG_PATH)
        self.router = ModelRouter(self.catalog)

    def test_resolves_each_required_task_role_from_config(self) -> None:
        for task_role in REQUIRED_TASK_ROLES:
            with self.subTest(task_role=task_role):
                route = self.router.resolve(
                    task_role,
                    data_classes=(DataClass.PUBLIC_EVIDENCE,),
                )

                self.assertEqual(task_role, route.task_role)
                self.assertIn(task_role, route.profile.task_roles)
                self.assertTrue(route.profile.model_id)
                self.assertTrue(route.profile.deployment)

    def test_fallback_chain_order_follows_profile_config(self) -> None:
        route = self.router.resolve(
            "source_classification",
            data_classes=(DataClass.PUBLIC_EVIDENCE,),
        )

        fallback_ids = tuple(
            profile.profile_id
            for profile in self.router.resolve_fallback_chain(route.profile.profile_id)
        )

        self.assertEqual(route.profile.fallback_chain, fallback_ids)

    def test_denies_private_research_for_cloud_routes_by_default(self) -> None:
        cloud_only = ModelProfileCatalog.from_mapping(
            _single_profile_config(
                endpoint_type="azure_ai_foundry",
                privacy_class="cloud",
                allowed_data_classes=(DataClass.PUBLIC_EVIDENCE.value,),
            )
        )

        with self.assertRaises(ModelRouteDenied):
            ModelRouter(cloud_only).resolve(
                "evidence_summary",
                data_classes=(DataClass.PRIVATE_RESEARCH,),
            )

        cloud_profiles = [
            profile
            for profile in self.catalog.profiles.values()
            if profile.endpoint_type != "local"
        ]
        self.assertTrue(cloud_profiles)
        for profile in cloud_profiles:
            with self.subTest(profile=profile.profile_id):
                self.assertFalse(
                    self.router.is_allowed(
                        profile,
                        data_classes=(DataClass.PRIVATE_RESEARCH,),
                    )
                )

    def test_allows_private_research_for_local_fallback_and_embeddings(self) -> None:
        for task_role in ("local_fallback", "embeddings"):
            with self.subTest(task_role=task_role):
                route = self.router.resolve(
                    task_role,
                    data_classes=(DataClass.PRIVATE_RESEARCH,),
                )

                self.assertEqual(task_role, route.task_role)
                self.assertIn(DataClass.PRIVATE_RESEARCH, route.profile.allowed_data_classes)
                self.assertEqual("local", route.profile.endpoint_type)

    def test_denies_secrets_for_every_route(self) -> None:
        for task_role in REQUIRED_TASK_ROLES:
            with self.subTest(task_role=task_role):
                with self.assertRaises(ModelRouteDenied):
                    self.router.resolve(task_role, data_classes=(DataClass.SECRETS,))

    def test_model_names_are_not_hard_coded_outside_config_and_tests(self) -> None:
        catalog = load_model_profiles(CONFIG_PATH)
        model_terms = {
            term
            for profile in catalog.profiles.values()
            for term in (profile.profile_id, profile.model_id, profile.deployment)
            if term
        }

        offenders: list[str] = []
        for root in (ROOT / "packages", ROOT / "services", ROOT / "apps", ROOT / "scripts"):
            for path in root.rglob("*"):
                if not path.is_file() or _is_ignored_scan_path(path):
                    continue
                text = path.read_text(encoding="utf-8", errors="ignore")
                for term in model_terms:
                    if term in text:
                        offenders.append(f"{path.relative_to(ROOT)} contains {term}")

        self.assertEqual([], offenders)

    def test_deterministic_modules_do_not_import_model_clients(self) -> None:
        deterministic_roots = [
            CORE_SRC / "ai_infra_fund_core" / "contracts",
        ]
        forbidden = (
            "from azure",
            "import azure",
            "from openai",
            "import openai",
            "from anthropic",
            "import anthropic",
        )

        offenders: list[str] = []
        for root in deterministic_roots:
            for path in root.glob("*.py"):
                text = path.read_text(encoding="utf-8")
                for pattern in forbidden:
                    if pattern in text:
                        offenders.append(f"{path.relative_to(ROOT)} contains {pattern}")

        self.assertEqual([], offenders)


def _single_profile_config(
    *,
    fallback_chain: tuple[str, ...] = (),
    endpoint_type: str = "local",
    privacy_class: str = "local",
    allowed_data_classes: tuple[str, ...] = (DataClass.PUBLIC_EVIDENCE.value,),
) -> dict[str, object]:
    return {
        "version": 1,
        "models": {
            "profile_a": {
                "model_id": "profile-a-model",
                "deployment": "profile-a-deployment",
                "provider": "test-provider",
                "endpoint_type": endpoint_type,
                "task_roles": ["evidence_summary"],
                "quota_rpm": None,
                "quota_tpm": None,
                "cost_class": "test",
                "max_context": "unknown",
                "privacy_class": privacy_class,
                "allowed_data_classes": list(allowed_data_classes),
                "fallback_chain": list(fallback_chain),
                "structured_output_support": True,
                "notes": "Test profile.",
            }
        },
    }


def _is_ignored_scan_path(path: Path) -> bool:
    ignored_parts = {
        ".next",
        "__pycache__",
        "node_modules",
    }
    if ignored_parts & set(path.parts):
        return True
    if path.name in {"package-lock.json"}:
        return True
    return path.suffix not in {".py", ".js", ".mjs", ".ts", ".tsx", ".json", ".sh", ".yaml", ".yml"}


if __name__ == "__main__":
    unittest.main()
