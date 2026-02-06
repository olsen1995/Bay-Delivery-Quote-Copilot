import ast
from pathlib import Path
from typing import Any


RUNTIME_ENTRY = Path("lifeos/main.py")
DECLARATION_NAME = "SUPPORTED_CANON_VERSIONS"


def test_runtime_canon_compatibility_is_explicit_when_declared():
    """
    Runtime ↔ Canon compatibility must be explicit once declared.

    Rules:
    - Absence of SUPPORTED_CANON_VERSIONS is allowed (bootstrap phase)
    - If declared, it MUST:
        * be a static literal
        * be a list or tuple
        * be non-empty
        * contain only literal values
    """

    if not RUNTIME_ENTRY.exists():
        # Runtime entry point missing is outside scope
        return

    source = RUNTIME_ENTRY.read_text(encoding="utf-8")
    tree = ast.parse(source)

    assignments = [
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(t, ast.Name) and t.id == DECLARATION_NAME
            for t in node.targets
        )
    ]

    if not assignments:
        # No compatibility declaration yet — allowed
        return

    assignment = assignments[0]
    value: Any = assignment.value

    assert isinstance(
        value, (ast.List, ast.Tuple)
    ), "SUPPORTED_CANON_VERSIONS must be a static list or tuple"

    assert len(value.elts) > 0, (
        "SUPPORTED_CANON_VERSIONS must not be empty once declared"
    )

    for elt in value.elts:
        assert isinstance(
            elt, ast.Constant
        ), "SUPPORTED_CANON_VERSIONS entries must be literal values"