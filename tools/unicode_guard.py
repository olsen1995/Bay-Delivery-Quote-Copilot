#!/usr/bin/env python3
"""
unicode_guard.py

Detect and remove hidden/bidirectional Unicode control characters that can trigger
GitHub "hidden or bidirectional Unicode text" warnings.

Commands:
  python tools/unicode_guard.py check [paths...]
  python tools/unicode_guard.py fix [--rewrite] [paths...]

Behavior:
- Detects/removes:
  * Bidi controls: U+061C, U+200E, U+200F, U+202A..U+202E, U+2066..U+2069
  * Hidden format controls: U+FEFF, U+200B, U+200C, U+200D, U+2060, U+180E
  * ALL Unicode Cc controls except: \\n, \\r, \\t
- Preserves existing newline style (CRLF vs LF) when writing.
- Writes UTF-8 with no BOM. --rewrite forces a clean rewrite pass even if 0 chars removed.
"""

from __future__ import annotations

import argparse
import os
import sys
import unicodedata
from pathlib import Path
from typing import Iterable, Iterator, List, Optional, Sequence, Tuple

# ---- Config: exact codepoints to remove ----

BIDI_CONTROLS = {
    0x061C,  # ARABIC LETTER MARK
    0x200E,  # LEFT-TO-RIGHT MARK
    0x200F,  # RIGHT-TO-LEFT MARK
    # U+202A..U+202E
    0x202A, 0x202B, 0x202C, 0x202D, 0x202E,
    # U+2066..U+2069
    0x2066, 0x2067, 0x2068, 0x2069,
}

HIDDEN_FORMAT_CONTROLS = {
    0xFEFF,  # ZERO WIDTH NO-BREAK SPACE / BOM
    0x200B,  # ZERO WIDTH SPACE
    0x200C,  # ZERO WIDTH NON-JOINER
    0x200D,  # ZERO WIDTH JOINER
    0x2060,  # WORD JOINER
    0x180E,  # MONGOLIAN VOWEL SEPARATOR (deprecated but sometimes present)
}

ALLOWED_CC = {"\n", "\r", "\t"}

DEFAULT_EXTS = {
    ".py", ".md", ".txt", ".html", ".css", ".js", ".json", ".yml", ".yaml",
}


def _iter_files(paths: Sequence[str]) -> Iterator[Path]:
    if not paths:
        root = Path(".")
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            if p.suffix.lower() in DEFAULT_EXTS:
                yield p
        return

    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            for f in p.rglob("*"):
                if f.is_file() and f.suffix.lower() in DEFAULT_EXTS:
                    yield f
        elif p.is_file():
            yield p


def _detect_newline_style(text: str) -> str:
    # If the file has any CRLF, treat it as CRLF style.
    # Otherwise default to LF.
    return "\r\n" if "\r\n" in text else "\n"


def _decode_bytes(data: bytes) -> str:
    # Use utf-8-sig to gracefully remove BOM if present.
    # We still treat FEFF anywhere else as removable.
    return data.decode("utf-8-sig")


def _encode_text(text: str) -> bytes:
    # Force UTF-8 no BOM
    return text.encode("utf-8")


def _is_target_char(ch: str) -> bool:
    cp = ord(ch)
    if cp in BIDI_CONTROLS:
        return True
    if cp in HIDDEN_FORMAT_CONTROLS:
        return True
    cat = unicodedata.category(ch)
    if cat == "Cc" and ch not in ALLOWED_CC:
        return True
    return False


def _unicode_name(ch: str) -> str:
    try:
        return unicodedata.name(ch)
    except ValueError:
        return "UNKNOWN"


def _find_hits(text: str) -> List[Tuple[int, int, str]]:
    """
    Returns list of (line_no_1based, col_no_1based, ch)
    """
    hits: List[Tuple[int, int, str]] = []
    line = 1
    col = 0
    for ch in text:
        if ch == "\n":
            line += 1
            col = 0
            continue
        col += 1
        if _is_target_char(ch):
            hits.append((line, col, ch))
    return hits


def cmd_check(paths: Sequence[str]) -> int:
    any_hits = False
    for file_path in _iter_files(paths):
        try:
            data = file_path.read_bytes()
        except OSError as e:
            print(f"ERROR: cannot read {file_path}: {e}", file=sys.stderr)
            return 2

        try:
            text = _decode_bytes(data)
        except UnicodeDecodeError:
            # Skip non-utf8 files quietly; we only care about our source/text files.
            continue

        hits = _find_hits(text)
        if hits:
            any_hits = True
            for (ln, col, ch) in hits:
                cp = ord(ch)
                u = f"U+{cp:04X}"
                name = _unicode_name(ch)
                cat = unicodedata.category(ch)
                print(f"{file_path}:{ln}:{col} {u} {name} category={cat}")

    return 1 if any_hits else 0


def _strip_targets(text: str) -> Tuple[str, int]:
    out_chars: List[str] = []
    removed = 0
    for ch in text:
        if _is_target_char(ch):
            removed += 1
            continue
        out_chars.append(ch)
    return ("".join(out_chars), removed)


def cmd_fix(paths: Sequence[str], rewrite: bool) -> int:
    changed_files: List[Tuple[Path, int]] = []

    for file_path in _iter_files(paths):
        try:
            data = file_path.read_bytes()
        except OSError as e:
            print(f"ERROR: cannot read {file_path}: {e}", file=sys.stderr)
            return 2

        try:
            text = _decode_bytes(data)
        except UnicodeDecodeError:
            continue

        newline = _detect_newline_style(text)

        stripped_text, removed = _strip_targets(text)

        # Preserve newline style on write:
        if newline == "\r\n":
            stripped_text = stripped_text.replace("\n", "\r\n").replace("\r\r\n", "\r\n")

        if removed > 0 or rewrite:
            try:
                file_path.write_bytes(_encode_text(stripped_text))
            except OSError as e:
                print(f"ERROR: cannot write {file_path}: {e}", file=sys.stderr)
                return 2
            changed_files.append((file_path, removed))

    if changed_files:
        for (p, n) in changed_files:
            print(f"CHANGED: {p} removed={n}")
    else:
        print("No files changed.")

    # Re-check the same targets (or full repo if none provided)
    rc = cmd_check(paths)
    if rc != 0:
        print("ERROR: unicode_guard check still failing after fix.", file=sys.stderr)
    return rc


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="unicode_guard.py")
    sub = parser.add_subparsers(dest="command", required=True)

    p_check = sub.add_parser("check", help="scan for hidden/bidi/control characters")
    p_check.add_argument("paths", nargs="*", help="files/dirs to scan (default: repo-wide)")

    p_fix = sub.add_parser("fix", help="remove hidden/bidi/control characters")
    p_fix.add_argument("--rewrite", action="store_true", help="rewrite files cleanly even if 0 chars removed")
    p_fix.add_argument("paths", nargs="*", help="files/dirs to fix (default: repo-wide)")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "check":
        return cmd_check(args.paths)
    if args.command == "fix":
        return cmd_fix(args.paths, rewrite=bool(args.rewrite))

    return 2


if __name__ == "__main__":
    raise SystemExit(main())