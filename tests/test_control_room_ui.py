from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / "apps" / "web"

REQUIRED_UI_FILES = [
    "app/page.tsx",
    "app/globals.css",
    "components/status-tile.tsx",
    "components/module-grid.tsx",
    "components/section-panel.tsx",
    "lib/api.ts",
    "lib/status-model.ts",
]

REQUIRED_DASHBOARD_TEXT = [
    "AI Infrastructure Fund Control Room",
    "Advisory-only",
    "System Status",
    "Portfolio",
    "Evidence",
    "Recommendations",
    "Evaluation",
    "Model Runs",
    "Data Quality",
    "Incidents",
    "System Architecture",
]

REQUIRED_MODULE_IDS = [
    "api",
    "worker",
    "postgres",
    "ui",
    "data-plane",
    "evidence-plane",
    "signal-plane",
    "portfolio-engine",
    "model-router",
    "recommendation-artifacts",
    "evaluation-harness",
    "trade-journal",
]

FORBIDDEN_UI_LABEL_PATTERNS = [
    r">\s*Place\s+Order\s*<",
    r">\s*Submit\s+Order\s*<",
    r">\s*Execute\s+Order\s*<",
    r">\s*Connect\s+Broker\s*<",
    r">\s*Start\s+Live\s+Trading\s*<",
]


def read_web(relative_path: str) -> str:
    return (WEB_ROOT / relative_path).read_text(encoding="utf-8")


def web_source_files() -> list[Path]:
    return [
        path
        for path in WEB_ROOT.rglob("*")
        if path.is_file()
        and "node_modules" not in path.parts
        and ".next" not in path.parts
        and path.suffix in {".css", ".ts", ".tsx"}
    ]


class ControlRoomUiTests(unittest.TestCase):
    def test_required_ui_files_exist(self) -> None:
        missing = [
            relative_path
            for relative_path in REQUIRED_UI_FILES
            if not (WEB_ROOT / relative_path).is_file()
        ]
        self.assertEqual([], missing)

    def test_dashboard_renders_required_sections_and_advisory_label(self) -> None:
        combined = "\n".join(path.read_text(encoding="utf-8") for path in web_source_files())
        missing = [text for text in REQUIRED_DASHBOARD_TEXT if text not in combined]
        self.assertEqual([], missing)

    def test_dashboard_is_not_a_marketing_hero(self) -> None:
        page = read_web("app/page.tsx")
        css = read_web("app/globals.css")
        self.assertNotRegex(f"{page}\n{css}", r"\bhero\b", "dashboard must not use hero/landing-page layout")
        self.assertIn("control-room-shell", page)
        self.assertIn("ops-room", page)

    def test_module_statuses_have_colors_and_sources(self) -> None:
        model = read_web("lib/status-model.ts")
        for status in ("passing", "degraded", "failing", "planned"):
            self.assertIn(status, model)
        for tone in ("green", "yellow", "red", "gray"):
            self.assertIn(tone, model)
        for module_id in REQUIRED_MODULE_IDS:
            self.assertIn(f'id: "{module_id}"', model)
        self.assertIn("sourceType", model)
        self.assertIn("sourceLabel", model)

    def test_api_status_fetch_handles_unavailable_backend(self) -> None:
        api = read_web("lib/api.ts")
        self.assertIn("fetchApiHealth", api)
        self.assertIn("fetchApiReadiness", api)
        self.assertIn("unavailable", api)
        self.assertIn("Backend unavailable", api)
        self.assertRegex(api, r"catch\s*\(")

    def test_no_order_or_broker_execution_ui_labels_exist(self) -> None:
        combined = "\n".join(path.read_text(encoding="utf-8") for path in web_source_files())
        offenders = [
            pattern
            for pattern in FORBIDDEN_UI_LABEL_PATTERNS
            if re.search(pattern, combined, re.IGNORECASE)
        ]
        self.assertEqual([], offenders)


if __name__ == "__main__":
    unittest.main()
