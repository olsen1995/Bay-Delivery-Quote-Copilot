"""
OpenAPI Drift Guard Validator

Validates that the static OpenAPI file exists and contains the required
paths/methods expected by the LifeOS Co-Pilot API.

This script is intended to run in CI, but can be run locally too:
  python scripts/ci/validate_openapi.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict


REPO_ROOT = Path(__file__).resolve().parents[2]
OPENAPI_FILE = REPO_ROOT / "public" / ".well-known" / "openapi.json"

EXPECTED_OPENAPI_VERSION = "3.1.0"
EXPECTED_SERVER_SUBSTR = "https://life-os-private-practical-co-pilot.onrender.com"

REQUIRED: dict[str, list[str]] = {
    "/ask": ["get", "post"],
    "/memory": ["get", "post", "delete"],
}


def fail(msg: str, code: int = 1) -> None:
    print(msg)
    raise SystemExit(code)


def main() -> None:
    if not OPENAPI_FILE.exists():
        fail(f"❌ ERROR: OpenAPI file not found: {OPENAPI_FILE}")

    # ✅ Initialize data so static analyzers (Pylance) know it's always defined.
    data: Dict[str, Any] = {}

    try:
        data = json.loads(OPENAPI_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        fail(f"❌ ERROR: Failed to parse JSON in {OPENAPI_FILE}: {e}")

    # 1) Basic structure checks
    if data.get("openapi") != EXPECTED_OPENAPI_VERSION:
        fail(f"❌ ERROR: openapi version must be {EXPECTED_OPENAPI_VERSION}")

    servers = data.get("servers", [])
    if not isinstance(servers, list):
        fail("❌ ERROR: 'servers' must be a list")

    if not any(EXPECTED_SERVER_SUBSTR in str(s.get("url", "")) for s in servers if isinstance(s, dict)):
        fail("❌ ERROR: expected Render server URL not found in servers block")

    paths = data.get("paths", {})
    if not isinstance(paths, dict):
        fail("❌ ERROR: 'paths' must be an object")

    # 2) Required paths + methods + x-openai-isConsequential checks
    missing: list[str] = []

    for path, methods in REQUIRED.items():
        if path not in paths:
            missing.append(f"Missing path: {path}")
            continue

        if not isinstance(paths[path], dict):
            missing.append(f"Invalid path object (expected dict): {path}")
            continue

        for method in methods:
            if method not in paths[path]:
                missing.append(f"Missing method: {method.upper()} on {path}")
                continue

            op = paths[path][method]
            if not isinstance(op, dict):
                missing.append(f"Invalid operation object: {method.upper()} on {path}")
                continue

            if op.get("x-openai-isConsequential") is not False:
                missing.append(f"{method.upper()} on {path} missing x-openai-isConsequential: false")

    if missing:
        for m in missing:
            print("❌", m)
        fail("❌ ERROR: OpenAPI schema failed validation.")

    print("✅ OpenAPI schema is valid.")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        print(f"❌ ERROR: Unexpected failure: {e}")
        sys.exit(1)
