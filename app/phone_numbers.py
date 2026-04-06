from __future__ import annotations

import re


QUOTE_PHONE_VALIDATION_MESSAGE = "Please enter a valid 10-digit phone number. You can include spaces, dashes, parentheses, or +1."

_ALLOWED_PHONE_CHARS = re.compile(r"^[0-9().+\-\s]+$")


def normalize_north_american_phone(value: str | None) -> str | None:
    if value is None:
        return None

    trimmed = value.strip()
    if not trimmed:
        return None
    if not _ALLOWED_PHONE_CHARS.fullmatch(trimmed):
        return None

    digits = re.sub(r"\D", "", trimmed)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        return None

    return format_north_american_phone(digits)


def format_north_american_phone(digits: str) -> str:
    return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"