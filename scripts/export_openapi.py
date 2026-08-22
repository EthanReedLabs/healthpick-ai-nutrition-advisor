"""Export the current FastAPI contract for generated Web types."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "apps" / "api"
OUTPUT = ROOT / "packages" / "shared" / "openapi" / "healthpick.openapi.json"
sys.path.insert(0, str(API_ROOT))

from healthpick_api.config import Settings  # noqa: E402
from healthpick_api.main import create_app  # noqa: E402


def main() -> int:
    app = create_app(Settings(app_env="test", llm_mode="mock"))
    document = app.openapi()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"OpenAPI {document['info']['version']} -> {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
