#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

TEXT_EXTENSIONS = {
    ".py",
    ".md",
    ".html",
    ".css",
    ".js",
    ".json",
    ".yml",
    ".yaml",
}

BIDI_CODEPOINTS = {
    0x061C,
    0x200E,
    0x200F,
    0x202A,
    0x202B,
    0x202C,
    0x202D,
    0x202E,
    0x2066,
    0x2067,
    0x2068,
    0x2069,
}


def iter_text_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if ".git" in path.parts:
            continue
        if path.suffix.lower() in TEXT_EXTENSIONS:
            yield path


def strip_chars(text: str) -> tuple[str, int]:
    removed = 0
    out = []
    for ch in text:
        if ord(ch) in BIDI_CODEPOINTS:
            removed += 1
            continue
        out.append(ch)
    return "".join(out), removed


def main() -> int:
    parser = argparse.ArgumentParser(description="Strip bidi control characters from repository text files.")
    parser.add_argument("--root", default=".", help="Root directory to process (default: current directory)")
    parser.add_argument("--backup-ext", default="", help="Optional backup extension (e.g., .bak)")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    changed_files = 0
    removed_total = 0

    for path in iter_text_files(root):
        try:
            original = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        cleaned, removed = strip_chars(original)
        if removed == 0:
            continue

        if args.backup_ext:
            backup_path = path.with_name(path.name + args.backup_ext)
            backup_path.write_text(original, encoding="utf-8")

        path.write_text(cleaned, encoding="utf-8")
        changed_files += 1
        removed_total += removed
        rel = path.relative_to(root)
        print(f"cleaned {rel} (removed {removed} characters)")

    if changed_files == 0:
        print("No files changed.")
    else:
        print(f"Changed {changed_files} file(s); removed {removed_total} character(s).")

    return 0


if __name__ == "__main__":
    sys.exit(main())
