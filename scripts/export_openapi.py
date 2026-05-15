"""Export the FastAPI OpenAPI spec to docs/api/openapi.yaml.

This script is intentionally read-only on import: importing it does not
write anywhere. Call `write_openapi_yaml()` (or run as a script) to
refresh the committed snapshot.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = REPO_ROOT / "packages" / "core" / "src"
API_SRC = REPO_ROOT / "services" / "api" / "src"
for path in (CORE_SRC, API_SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

OUTPUT_PATH = REPO_ROOT / "docs" / "api" / "openapi.yaml"


def build_openapi_spec() -> dict[str, Any]:
    from ai_infra_fund_api.main import create_app

    app = create_app()
    return app.openapi()


def build_openapi_yaml() -> str:
    import yaml

    spec = build_openapi_spec()
    return yaml.safe_dump(spec, sort_keys=True, allow_unicode=True)


def write_openapi_yaml(target: Path = OUTPUT_PATH) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(build_openapi_yaml(), encoding="utf-8")
    return target


def main() -> None:
    target = write_openapi_yaml()
    print(f"wrote {target.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
