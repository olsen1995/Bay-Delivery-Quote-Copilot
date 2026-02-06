import ast
from pathlib import Path


RUNTIME_PATHS = [
    Path("lifeos/main.py"),
    Path("lifeos/routes"),
    Path("lifeos/services"),
]

# Runtime is ONLY allowed to depend on Canon via these modules
ALLOWED_CANON_IMPORTS = {
    "lifeos.canon.read_gate",
    "lifeos.canon.read_routes",
}

# Anything deeper than this is forbidden
FORBIDDEN_CANON_PREFIX = "lifeos.canon."


def test_runtime_canon_dependencies_are_explicit():
    """
    Runtime must not depend on Canon internals.
    Canon access is allowed ONLY via declared read-gate modules.
    """

    for base in RUNTIME_PATHS:
        if not base.exists():
            continue

        py_files = (
            [base] if base.is_file() else list(base.rglob("*.py"))
        )

        for py_file in py_files:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))

            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        module = alias.name
                        break
                    else:
                        continue
                else:
                    continue

                if module.startswith(FORBIDDEN_CANON_PREFIX):
                    if module not in ALLOWED_CANON_IMPORTS:
                        raise AssertionError(
                            f"Unauthorized Runtime → Canon dependency in {py_file}: {module}"
                        )