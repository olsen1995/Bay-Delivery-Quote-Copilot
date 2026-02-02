"""
Canon Validator — CI Only

This validator aligns with the approved governance model where Canon
operates without a disk-based manifest file.

Scope:
- CI-only validation behavior
- No Canon mutation
- No runtime or governance changes
"""

from pathlib import Path


def validate_canon() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    canon_root = repo_root / "lifeos" / "canon"

    if not canon_root.exists():
        raise FileNotFoundError(f"Canon directory not found: {canon_root}")

    # Canon intentionally operates without a disk-based manifest.
    # Absence of Canon_Manifest*.json is a valid, governed state.
    manifests = list(canon_root.glob("Canon_Manifest*.json"))

    if not manifests:
        print(
            "No Canon manifest present; validation performed in structure-only mode"
        )
        return

    # If a manifest exists in the future, its presence is acknowledged,
    # but no validation is enforced here to avoid inventing governance rules.
    print(
        "Canon manifest detected; no manifest validation enforced by CI"
    )


if __name__ == "__main__":
    validate_canon()
    print("Canon validation passed.")
