import ast
from pathlib import Path

CANON_SRC_PATH = Path("lifeos/canon")
ALLOWED_READ_MODULES = {"read_gate", "read_routes"}
ALLOWED_READ_FUNCTIONS = {"load_canon_json", "load_strategy_json", "load_tree_json"}


def is_canon_read_call(node: ast.Call) -> bool:
    """Check if a function call reads a file directly."""
    if isinstance(node.func, ast.Attribute):
        if node.func.attr in {"read_text", "open", "read_bytes"}:
            return True
    return False


def test_all_canon_reads_use_read_gate():
    for py_file in CANON_SRC_PATH.rglob("*.py"):
        mod_name = py_file.stem
        if mod_name in ALLOWED_READ_MODULES:
            continue  # skip read_gate and read_routes

        tree = ast.parse(py_file.read_text(encoding="utf-8"))

        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and is_canon_read_call(node):
                raise AssertionError(
                    f"Unauthorized file read in {py_file}: {ast.unparse(node)}"
                )
