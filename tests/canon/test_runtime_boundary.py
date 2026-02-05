import ast
from pathlib import Path

CANON_PATH = Path("lifeos/canon")
FORBIDDEN_IMPORTS = [
    "lifeos.main",
    "lifeos.routes",
    "lifeos.services",
    "lifeos.runtime",
]


def test_no_runtime_imports_in_canon():
    for py_file in CANON_PATH.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"))

        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                else:
                    names = [node.module or ""]

                for name in names:
                    if any(name.startswith(bad) for bad in FORBIDDEN_IMPORTS):
                        raise AssertionError(
                            f"Forbidden import in {py_file}: {name}"
                        )
