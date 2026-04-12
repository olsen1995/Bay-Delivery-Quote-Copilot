"""
tools/export_gpt_grounding_pack.py

Export the Bay Delivery GPT grounding pack to a local output directory.

Copies exactly the canonical upload-set files defined in docs/gpt/GPT_KNOWLEDGE_PACK.md
and writes a manifest.json with SHA-256 hashes for auditability.

Usage:
    python tools/export_gpt_grounding_pack.py --output-dir dist/gpt_grounding_pack

The output directory is suitable for manual upload to GPT Builder.
Do NOT commit the output directory to the repository.
"""

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Canonical upload set
# Keep this list in sync with docs/gpt/GPT_KNOWLEDGE_PACK.md.
# ---------------------------------------------------------------------------
UPLOAD_SET = [
    "docs/gpt/GPT_SOURCE_OF_TRUTH.md",
    "docs/gpt/GPT_BUSINESS_RULES.md",
    "docs/gpt/GPT_CURRENT_STATE.md",
    "docs/gpt/GPT_SYSTEM_BOUNDARIES.md",
    "docs/gpt/GPT_WORKFLOW_RULES.md",
    "docs/gpt/GPT_BUILDER_INSTRUCTIONS.md",
    "docs/gpt/GPT_ACCEPTANCE_TESTS.md",
    "PROJECT_RULES.md",
    "docs/CURRENT_STATE.md",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_output_dir_for_cleanup(repo_root: Path, output_dir: Path) -> None:
    """
    Allow cleanup only for subdirectories inside <repo>/dist/.
    """
    dist_dir = (repo_root / "dist").resolve()

    if output_dir == repo_root:
        raise ValueError("Refusing to clean repo root.")
    if output_dir == dist_dir:
        raise ValueError("Refusing to clean dist/ root.")

    try:
        relative_to_dist = output_dir.relative_to(dist_dir)
    except ValueError as exc:
        raise ValueError("Output dir must be inside <repo>/dist/.") from exc

    if not relative_to_dist.parts:
        raise ValueError("Output dir must be a subdirectory inside <repo>/dist/.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export the Bay Delivery GPT grounding pack."
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Destination directory for the grounding pack (e.g. dist/gpt_grounding_pack)",
    )
    parser.add_argument(
        "--repo-root",
        default=None,
        help="Repository root directory. Defaults to the parent of the tools/ directory.",
    )
    args = parser.parse_args()

    # Resolve repo root
    tools_dir = Path(__file__).resolve().parent
    repo_root = Path(args.repo_root).resolve() if args.repo_root else tools_dir.parent

    output_dir = Path(args.output_dir).resolve()
    try:
        validate_output_dir_for_cleanup(repo_root=repo_root, output_dir=output_dir)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    manifest = []
    missing = []

    for relative in UPLOAD_SET:
        src = repo_root / relative
        if not src.exists():
            missing.append(relative)
            continue

        dest = output_dir / src.name
        shutil.copy2(src, dest)
        digest = sha256_file(dest)
        manifest.append({"file": relative, "output": src.name, "sha256": digest})
        print(f"  copied  {relative}  ->  {dest.name}")

    if missing:
        print("\nERROR: the following source files were not found:", file=sys.stderr)
        for m in missing:
            print(f"  {m}", file=sys.stderr)
        return 1

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps({"upload_set": manifest}, indent=2), encoding="utf-8"
    )
    print(f"\nmanifest written to {manifest_path}")
    print(f"\nGrounding pack exported to: {output_dir}")
    print(f"Files: {len(manifest)} + manifest.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
