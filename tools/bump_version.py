from __future__ import annotations

import argparse
import sys
from pathlib import Path

from version_alignment import (
    VersionAlignmentError,
    parse_strict_version,
    read_required_text,
    read_strict_version_file,
    render_updated_readme,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bump or set the tracked release version markers."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--bump",
        choices=("patch", "minor", "major"),
        help="Increment the current version using semantic-version rules.",
    )
    group.add_argument(
        "--version",
        help="Set an explicit semantic version in X.Y.Z format.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate inputs and print the resolved version without writing files.",
    )
    return parser.parse_args()


def resolve_version(current_version: str, bump: str | None, explicit_version: str | None) -> str:
    if explicit_version is not None:
        return parse_strict_version(explicit_version, "--version")

    major, minor, patch = (int(part) for part in current_version.split("."))
    if bump == "major":
        major += 1
        minor = 0
        patch = 0
    elif bump == "minor":
        minor += 1
        patch = 0
    else:
        patch += 1
    return f"{major}.{minor}.{patch}"


def write_version_file(path: Path, version: str) -> None:
    path.write_text(version + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()

    try:
        current_version = read_strict_version_file(REPO_ROOT / "VERSION", "VERSION")
        read_strict_version_file(REPO_ROOT / "canon_versions.txt", "canon_versions.txt")
        readme_text = read_required_text(REPO_ROOT / "README.md")
        resolved_version = resolve_version(current_version, args.bump, args.version)
        updated_readme = render_updated_readme(readme_text, resolved_version)
    except VersionAlignmentError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if not args.dry_run:
        write_version_file(REPO_ROOT / "VERSION", resolved_version)
        write_version_file(REPO_ROOT / "canon_versions.txt", resolved_version)
        (REPO_ROOT / "README.md").write_text(updated_readme, encoding="utf-8")
    else:
        print("Dry run: no files were changed.", file=sys.stderr)

    print(resolved_version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
