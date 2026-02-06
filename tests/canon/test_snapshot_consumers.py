import ast
from pathlib import Path

# Canon snapshot API entrypoint
SNAPSHOT_FUNCTION = "get_snapshot"

# Explicitly allowed snapshot consumers (paths are repo-relative)
ALLOWED_CONSUMERS = {
    "lifeos/main.py",
}

ALLOWED_PREFIXES = (
    "lifeos/routes/",
)


def _python_files(root: Path):
    return [p for p in root.rglob("*.py") if p.is_file()]


def test_canon_snapshot_consumers_are_declared():
    """
    Canon snapshots must only be consumed by declared runtime entrypoints.
    This test fails if any new, undeclared consumer imports get_snapshot.
    """

    repo_root = Path(__file__).resolve().parents[2]
    offenders = []

    for py_file in _python_files(repo_root):
        rel_path = py_file.relative_to(repo_root).as_posix()

        # Skip Canon internals and tests
        if rel_path.startswith("lifeos/canon/"):
            continue
        if rel_path.startswith("tests/"):
            continue

        source = py_file.read_text(encoding="utf-8")
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module == "lifeos.canon.snapshot":
                    for name in node.names:
                        if name.name == SNAPSHOT_FUNCTION:
                            if not (
                                rel_path in ALLOWED_CONSUMERS
                                or rel_path.startswith(ALLOWED_PREFIXES)
                            ):
                                offenders.append(rel_path)

    assert not offenders, (
        "Undeclared Canon snapshot consumers detected:\n"
        + "\n".join(sorted(set(offenders)))
        + "\n\nDeclare new consumers explicitly before usage."
    )