"""
Phase 34 — Canon Read Access Gate

- Single choke point for ALL /canon/* read routes
- Fail-closed on denial or ambiguity
- Subject resolution is STATIC and STRUCTURAL
"""

import json
from pathlib import Path

from lifeos.canon.read_routes import READ_ROUTES
from lifeos.canon.loader import load_canon_json


_POLICY_PATH = Path("lifeos/canon/access_policy.json")


class CanonAccessDenied(Exception):
    pass


def _load_policy() -> dict:
    return json.loads(_POLICY_PATH.read_text(encoding="utf-8"))


def assert_read_allowed(*, route: str, subject: str) -> str:
    """
    Asserts read access for a given subject and route.
    Returns the canonical resource if allowed.
    Raises CanonAccessDenied on failure.
    """
    if route not in READ_ROUTES:
        raise CanonAccessDenied(f"Ungoverned Canon route: {route}")

    resource = READ_ROUTES[route]
    policy = _load_policy()

    for rule in policy["rules"]:
        if rule["subject"] == subject and rule["resource"] == resource:
            if rule["allow"] is True:
                return resource
            break

    raise CanonAccessDenied(
        f"Read access denied (subject={subject}, resource={resource})"
    )


# -------------------------------------------------------------------
# Canon loader export (capability only)
# -------------------------------------------------------------------

read_canon_file = load_canon_json