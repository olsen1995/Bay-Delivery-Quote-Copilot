from __future__ import annotations


def detect_mode(message: str) -> str:
    """
    Deterministic mode tagger (internal only).

    Contract:
    - Must be deterministic (same input -> same output).
    - Must not perform IO, network calls, or randomness.
    - For now, always returns "default".
    """
    _ = message  # reserved for future rules
    return "default"
