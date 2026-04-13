from __future__ import annotations

from pathlib import Path
import re


STRICT_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
CURRENT_STABLE_PREFIX = "Current stable milestone:"
RELEASE_MARKERS_PREFIX = "Release markers are aligned"
CURRENT_STABLE_LINE_RE = re.compile(
    r"^Current stable milestone: `(?P<version>\d+\.\d+\.\d+)`\.$"
)
RELEASE_MARKERS_LINE_RE = re.compile(
    r"^Release markers are aligned: `VERSION` = `(?P<version>\d+\.\d+\.\d+)` "
    r"and `canon_versions\.txt` = `(?P<canon_version>\d+\.\d+\.\d+)`\.$"
)


class VersionAlignmentError(ValueError):
    """Raised when a tracked version marker is missing or malformed."""


def read_required_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise VersionAlignmentError(f"Required file not found: {path.name}") from exc


def parse_strict_version(raw_text: str, label: str) -> str:
    value = raw_text.strip()
    if not STRICT_VERSION_RE.fullmatch(value):
        raise VersionAlignmentError(
            f"{label} must contain exactly one strict X.Y.Z version value; found {value!r}."
        )
    return value


def read_strict_version_file(path: Path, label: str) -> str:
    return parse_strict_version(read_required_text(path), label)


def _find_single_line(lines: list[str], prefix: str, line_re: re.Pattern[str], label: str) -> tuple[int, re.Match[str]]:
    matching_indexes = [index for index, line in enumerate(lines) if prefix in line]
    if not matching_indexes:
        raise VersionAlignmentError(f"{label} marker not found in README.md.")
    if len(matching_indexes) > 1:
        raise VersionAlignmentError(
            f"{label} marker appears more than once in README.md ({len(matching_indexes)} matches)."
        )

    index = matching_indexes[0]
    line = lines[index]
    match = line_re.fullmatch(line)
    if match is None:
        raise VersionAlignmentError(
            f"{label} marker exists in README.md but does not match the expected structure: {line!r}"
        )
    return index, match


def parse_readme_markers(readme_text: str) -> dict[str, object]:
    lines = readme_text.splitlines()
    current_index, current_match = _find_single_line(
        lines,
        CURRENT_STABLE_PREFIX,
        CURRENT_STABLE_LINE_RE,
        "Current stable milestone",
    )
    release_index, release_match = _find_single_line(
        lines,
        RELEASE_MARKERS_PREFIX,
        RELEASE_MARKERS_LINE_RE,
        "Release markers are aligned",
    )
    return {
        "lines": lines,
        "current_index": current_index,
        "current_version": current_match.group("version"),
        "release_index": release_index,
        "release_version": release_match.group("version"),
        "release_canon_version": release_match.group("canon_version"),
    }


def build_current_stable_line(version: str) -> str:
    return f"Current stable milestone: `{version}`."


def build_release_markers_line(version: str) -> str:
    return (
        f"Release markers are aligned: `VERSION` = `{version}` and "
        f"`canon_versions.txt` = `{version}`."
    )


def render_updated_readme(readme_text: str, version: str) -> str:
    marker_data = parse_readme_markers(readme_text)
    lines = list(marker_data["lines"])
    lines[marker_data["current_index"]] = build_current_stable_line(version)
    lines[marker_data["release_index"]] = build_release_markers_line(version)

    updated = "\n".join(lines)
    if readme_text.endswith("\n"):
        updated += "\n"
    return updated
