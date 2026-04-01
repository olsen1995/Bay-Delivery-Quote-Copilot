from pathlib import Path
import sys


version = Path("VERSION").read_text(encoding="utf-8").strip()
canon_version = Path("canon_versions.txt").read_text(encoding="utf-8").strip()

if version != canon_version:
    print(
        "Version marker mismatch: "
        f"VERSION={version!r} vs canon_versions.txt={canon_version!r}. "
        "Update both files to the same value.",
        file=sys.stderr,
    )
    raise SystemExit(1)

print(f"Version markers aligned: {version}")
