#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
import unicodedata
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
    0x061C,  # ARABIC LETTER MARK
    0x200E,  # LEFT-TO-RIGHT MARK
    0x200F,  # RIGHT-TO-LEFT MARK
    0x202A,  # LEFT-TO-RIGHT EMBEDDING
    0x202B,  # RIGHT-TO-LEFT EMBEDDING
    0x202C,  # POP DIRECTIONAL FORMATTING
    0x202D,  # LEFT-TO-RIGHT OVERRIDE
    0x202E,  # RIGHT-TO-LEFT OVERRIDE
    0x2066,  # LEFT-TO-RIGHT ISOLATE
    0x2067,  # RIGHT-TO-LEFT ISOLATE
    0x2068,  # FIRST STRONG ISOLATE
    0x2069,  # POP DIRECTIONAL ISOLATE
}


def iter_text_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if ".git" in path.parts:
            continue
        if path.suffix.lower() in TEXT_EXTENSIONS:
            yield path


def find_bidi_controls(text: str):
    line = 1
    col = 1
    for ch in text:
        cp = ord(ch)
        if cp in BIDI_CODEPOINTS:
            yield line, col, cp
        if ch == "\n":
            line += 1
            col = 1
        else:
            col += 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan repository for bidi control characters.")
    parser.add_argument("--root", default=".", help="Root directory to scan (default: current directory)")
    parser.add_argument("--fail", action="store_true", help="Exit 1 when bidi control characters are found")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    hits = 0

    for path in iter_text_files(root):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        for line, col, cp in find_bidi_controls(text):
            hits += 1
            name = unicodedata.name(chr(cp), "UNKNOWN")
            rel = path.relative_to(root)
            print(f"{rel}:{line}:{col} U+{cp:04X} {name}")

    if hits == 0:
        print("No bidi control characters found.")

    if args.fail and hits > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
