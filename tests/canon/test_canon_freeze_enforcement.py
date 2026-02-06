import json
import subprocess
from pathlib import Path
from typing import Any, Mapping


FREEZE_FILE = Path("lifeos/FREEZE.json")
CANON_PATH = Path("lifeos/canon")


def _git_diff_exists(path: Path) -> bool:
    """
    Returns True if git reports changes under the given path.
    """
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD", "--", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    return bool(result.stdout.strip())


def test_canon_is_immutable_when_frozen():
    """
    Canon must not change when a freeze is active with scope:
    - canon
    - global

    This test enforces immutability without modifying Canon data.
    """

    if not FREEZE_FILE.exists():
        # No freeze declared — Canon changes allowed
        return

    data: Any = json.loads(FREEZE_FILE.read_text(encoding="utf-8"))

    assert isinstance(data, Mapping), "FREEZE.json must be a JSON object"

    scope = data.get("scope")

    if scope not in {"canon", "global"}:
        # Freeze does not apply to Canon
        return

    assert not _git_diff_exists(CANON_PATH), (
        "Canon is frozen but changes were detected under lifeos/canon/. "
        "Remove the freeze or revert Canon changes."
    )