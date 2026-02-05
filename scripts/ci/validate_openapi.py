from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Set, NoReturn, cast


OPENAPI_PATH = Path("public/.well-known/openapi.json")
EXPECTED_SERVER = "https://life-os-private-practical-co-pilot.onrender.com"

REQUIRED_ROUTES = {
    "/ask": ["get", "post"],
    "/memory": ["get", "post", "delete"],
}

REQUIRED_OPERATION_FLAGS = {"x-openai-isConsequential"}
REQUIRED_RESPONSE_KEYS = {"summary"}


def fail(msg: str) -> NoReturn:
    print(f"❌ OpenAPI Drift Guard Failure: {msg}")
    sys.exit(1)


def load_json(path: Path) -> Dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
        parsed: Any = json.loads(raw)
    except FileNotFoundError:
        fail(f"OpenAPI file not found: {path}")
    except json.JSONDecodeError as e:
        fail(f"Invalid JSON in OpenAPI file: {e}")

    if not isinstance(parsed, dict):
        fail(f"OpenAPI root must be a JSON object: {path}")

    return parsed


def assert_servers(data: Dict[str, Any]) -> None:
    raw = data.get("servers")
    if not isinstance(raw, list):
        fail("servers must be a list")
    servers: List[Any] = raw

    found = any(
        (s.get("url") == EXPECTED_SERVER) if isinstance(s, dict) else False
        for s in servers
    )
    if not found:
        fail(f"Expected server URL missing. Required: {EXPECTED_SERVER}")


def assert_paths(paths_raw: Any) -> None:
    if not isinstance(paths_raw, dict):
        fail("paths must be an object")
    paths: Dict[str, Any] = paths_raw

    for route in sorted(REQUIRED_ROUTES.keys()):
        if route not in paths:
            fail(f"Missing required path: {route}")

        route_raw = paths[route]
        if not isinstance(route_raw, dict):
            fail(f"Path entry must be an object: {route}")
        route_obj: Dict[str, Any] = route_raw

        for method in sorted(REQUIRED_ROUTES[route]):
            if method not in route_obj:
                fail(f"Missing required method: {method.upper()} {route}")

            op_raw = route_obj[method]
            if not isinstance(op_raw, dict):
                fail(f"Operation must be an object: {method.upper()} {route}")
            op: Dict[str, Any] = op_raw

            if op.get("x-openai-isConsequential") is not False:
                fail(
                    f"Missing or incorrect x-openai-isConsequential on {method.upper()} {route}"
                )

            assert_responses(route, method, op)


def assert_responses(route: str, method: str, op: Dict[str, Any]) -> None:
    responses_raw = op.get("responses")
    if not isinstance(responses_raw, dict):
        fail(f"Missing or invalid responses object on {method.upper()} {route}")
    responses: Dict[str, Any] = responses_raw

    if "200" not in responses:
        fail(f"Missing 200 response on {method.upper()} {route}")

    resp_200_raw = responses["200"]
    if not isinstance(resp_200_raw, dict):
        fail(f"200 response must be an object on {method.upper()} {route}")
    resp_200: Dict[str, Any] = resp_200_raw

    content_raw = resp_200.get("content")
    if not isinstance(content_raw, dict):
        fail(f"Missing content object on 200 response {method.upper()} {route}")
    content: Dict[str, Any] = content_raw

    json_content_raw = content.get("application/json")
    if not isinstance(json_content_raw, dict):
        fail(f"Missing application/json response schema on {method.upper()} {route}")
    json_content: Dict[str, Any] = json_content_raw

    schema_raw = json_content.get("schema")
    if not isinstance(schema_raw, dict):
        fail(f"Missing schema on {method.upper()} {route}")
    schema: Dict[str, Any] = schema_raw

    properties_raw = schema.get("properties")
    if not isinstance(properties_raw, dict):
        fail(f"Schema properties must be object on {method.upper()} {route}")
    properties: Dict[str, Any] = properties_raw

    prop_keys: Set[str] = set(properties.keys())

    missing = REQUIRED_RESPONSE_KEYS - prop_keys
    if missing:
        fail(
            f"Missing required response properties {sorted(missing)} on {method.upper()} {route}"
        )

    undocumented = prop_keys - REQUIRED_RESPONSE_KEYS
    if undocumented:
        fail(
            f"Undocumented response properties detected {sorted(undocumented)} on {method.upper()} {route}"
        )


def main() -> None:
    if not OPENAPI_PATH.exists():
        fail(f"Missing required file: {OPENAPI_PATH}")

    raw = load_json(OPENAPI_PATH)
    data: Dict[str, Any] = raw

    if data.get("openapi") != "3.1.0":
        fail("OpenAPI version must be 3.1.0")

    assert_servers(data)

    paths_raw = data.get("paths")
    assert_paths(paths_raw)

    print("✅ OpenAPI schema validation passed (type-safe & deterministic).")


if __name__ == "__main__":
    main()
