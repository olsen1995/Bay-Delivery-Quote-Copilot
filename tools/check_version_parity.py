import sys

from pathlib import Path

from version_alignment import (
    VersionAlignmentError,
    parse_readme_markers,
    read_required_text,
    read_strict_version_file,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    errors: list[str] = []

    try:
        version = read_strict_version_file(REPO_ROOT / "VERSION", "VERSION")
        canon_version = read_strict_version_file(
            REPO_ROOT / "canon_versions.txt", "canon_versions.txt"
        )
        readme_markers = parse_readme_markers(read_required_text(REPO_ROOT / "README.md"))
    except VersionAlignmentError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if canon_version != version:
        errors.append(
            "Version marker mismatch: "
            f"VERSION={version!r} vs canon_versions.txt={canon_version!r}."
        )

    if readme_markers["current_version"] != version:
        errors.append(
            "README current stable milestone mismatch: "
            f"expected {version!r}, found {readme_markers['current_version']!r}."
        )

    release_version = readme_markers["release_version"]
    release_canon_version = readme_markers["release_canon_version"]
    if release_version != version or release_canon_version != version:
        errors.append(
            "README release markers mismatch: "
            f"expected VERSION={version!r} and canon_versions.txt={version!r}, "
            f"found VERSION={release_version!r} and "
            f"canon_versions.txt={release_canon_version!r}."
        )

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print(f"Version markers aligned: {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
