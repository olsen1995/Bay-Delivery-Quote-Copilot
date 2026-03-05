#!/usr/bin/env python3
"""
unicode_guard.py

Purpose:
- Detect and remove hidden / bidirectional / control Unicode characters that trigger
  GitHub “hidden or bidirectional Unicode text” warnings.
- Optionally rewrite files to clean UTF-8 (no BOM) even if nothing was removed.

Commands:
  python tools/unicode_guard.py check [paths...]
  python tools/unicode_guard.py fix [--rewrite] [paths...]

What we treat as "bad":
1) Bidi controls (Trojan Source class):
   U+061C, U+200E, U+200F, U+202A..U+202E, U+2066..U+2069
2) Common hidden format controls:
   U+FEFF, U+200B, U+200C, U+200D, U+2060, U+180E
3) ALL Unicode Cc control characters EXCEPT: \\n, \\r, \\t
4) Leading indentation containing non-ASCII whitespace (e.g., NBSP U+00A0)
   -> normalized to regular spaces (ONLY in indentation).
"""

from __future__ import annotations

import argparse
import sys
import unicodedata
from pathlib import Path
from typing import Iterable, Iterator, List, Optional, Sequence, Tuple

BIDI_CONTROLS = {
    0x061C,  # ARABIC LETTER MARK
    0x200E,  # LEFT-TO-RIGHT MARK
    0x200F,  # RIGHT-TO-LEFT MARK
    0x202A, 0x202B, 0x202C, 0x202D, 0x202E,  # embedding/override + pop
    0x2066, 0x2067, 0x2068, 0x2069,          # isolates + pop
}

HIDDEN_FORMAT_CONTROLS = {
    0xFEFF,  # BOM / ZWNBSP
    0x200B,  # ZWSP
    0x200C,  # ZWNJ
    0x200D,  # ZWJ
    0x2060,  # WORD JOINER
    0x180E,  # Mongolian vowel separator (deprecated)
}

ALLOWED_CC = {"\n", "\r", "\t"}

DEFAULT_EXTS = {".py", ".md", ".txt", ".html", ".css", ".js", ".json", ".yml", ".yaml"}


def _iter_files(paths: Sequence[str]) -> Iterator[Path]:
    if not paths:
        for p in Path(".").rglob("*"):
            if p.is_file() and p.suffix.lower() in DEFAULT_EXTS:
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


def _decode_bytes(data: bytes) -> str:
    # utf-8-sig strips BOM if present
    return data.decode("utf-8-sig")


def _encode_text(text: str) -> bytes:
    return text.encode("utf-8")  # no BOM


def _newline_style(text: str) -> str:
    return "\r\n" if "\r\n" in text else "\n"


def _unicode_name(ch: str) -> str:
    try:
        return unicodedata.name(ch)
    except ValueError:
        return "UNKNOWN"


def _category(ch: str) -> str:
    return unicodedata.category(ch)


def _is_bad_char(ch: str) -> bool:
    cp = ord(ch)
    if cp in BIDI_CONTROLS:
        return True
    if cp in HIDDEN_FORMAT_CONTROLS:
        return True
    cat = _category(ch)
    if cat == "Cc" and ch not in ALLOWED_CC:
        return True
    return False


def _find_bad_chars(text: str) -> List[Tuple[int, int, str]]:
    hits: List[Tuple[int, int, str]] = []
    line = 1
    col = 0
    for ch in text:
        if ch == "\n":
            line += 1
            col = 0
            continue
        col += 1
        if _is_bad_char(ch):
            hits.append((line, col, ch))
    return hits


def _normalize_indentation(line: str) -> Tuple[str, int]:
    """
    Only normalize LEADING indentation:
    - Any unicode whitespace (including NBSP) in the indent becomes a normal space.
    - Tabs are kept as tabs (we do NOT convert tabs to spaces).
    """
    i = 0
    removed_or_changed = 0
    out = []
    while i < len(line):
        ch = line[i]
        if ch in (" ", "\t"):
            out.append(ch)
            i += 1
            continue
        # stop when indentation ends
        if not ch.isspace():
            break
        # ch is whitespace but not ' ' or '\t' (likely NBSP or other)
        out.append(" ")
        removed_or_changed += 1
        i += 1
    return "".join(out) + line[i:], removed_or_changed


def cmd_check(paths: Sequence[str]) -> int:
    any_hits = False
    for fp in _iter_files(paths):
        try:
            data = fp.read_bytes()
        except OSError as e:
            print(f"ERROR: cannot read {fp}: {e}", file=sys.stderr)
            return 2

        try:
            text = _decode_bytes(data)
        except UnicodeDecodeError:
            continue

        hits = _find_bad_chars(text)
        if hits:
            any_hits = True
            for ln, col, ch in hits:
                cp = ord(ch)
                print(f"{fp}:{ln}:{col} U+{cp:04X} {_unicode_name(ch)} category={_category(ch)}")

        # Also flag non-ASCII whitespace in indentation as a warning-class issue
        for idx, line in enumerate(text.splitlines(), start=1):
            new_line, changed = _normalize_indentation(line)
            if changed:
                any_hits = True
                print(f"{fp}:{idx}:1 INDENT has non-ASCII whitespace (normalized by fix)")

    return 1 if any_hits else 0


def cmd_fix(paths: Sequence[str], rewrite: bool) -> int:
    changed_any = False

    for fp in _iter_files(paths):
        try:
            data = fp.read_bytes()
        except OSError as e:
            print(f"ERROR: cannot read {fp}: {e}", file=sys.stderr)
            return 2

        try:
            text = _decode_bytes(data)
        except UnicodeDecodeError:
            continue

        nl = _newline_style(text)

        # Remove bad chars
        removed = 0
        cleaned_chars: List[str] = []
        for ch in text:
            if _is_bad_char(ch):
                removed += 1
                continue
            cleaned_chars.append(ch)
        cleaned = "".join(cleaned_chars)

        # Normalize indentation per-line (only leading whitespace)
        indent_changed = 0
        lines = cleaned.splitlines(keepends=False)
        fixed_lines: List[str] = []
        for line in lines:
            fixed, c = _normalize_indentation(line)
            indent_changed += c
            fixed_lines.append(fixed)

        cleaned2 = nl.join(fixed_lines)
        # Preserve final newline if the original had one
        if text.endswith(("\n", "\r")):
            cleaned2 += nl

        if removed or indent_changed or rewrite:
            fp.write_bytes(_encode_text(cleaned2))
            changed_any = True
            print(f"CHANGED: {fp} removed={removed} indent_normalized={indent_changed}")

    if not changed_any:
        print("No files changed.")

    # Re-check
    rc = cmd_check(paths)
    if rc != 0:
        print("ERROR: unicode_guard check still failing after fix.", file=sys.stderr)
    return rc


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="unicode_guard.py")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check")
    c.add_argument("paths", nargs="*")

    f = sub.add_parser("fix")
    f.add_argument("--rewrite", action="store_true")
    f.add_argument("paths", nargs="*")

    args = p.parse_args(argv)

    if args.cmd == "check":
        return cmd_check(args.paths)
    if args.cmd == "fix":
        return cmd_fix(args.paths, rewrite=bool(args.rewrite))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())