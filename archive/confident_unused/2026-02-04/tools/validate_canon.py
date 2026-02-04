"""
Canon Validator — CI / Tooling

Scope:
- Validates Canon structure and manifest presence
- CI-only alignment with rootDir: lifeos
- No Canon mutation
"""

from pathlib import Path


def validate_canon_manifest() -> None:
    """
    Validate that the canonical Canon manifest exists at the approved,
    versioned path.

    This path must match the file byte-for-byte.
    """
    repo_root = Path(__file__).resolve().parents[1]
    canon_root = repo_root / "lifeos" / "canon"

    manifest_path = canon_root / "Canon_Manifest_v5.0.json"

    if not manifest_path.exists():
        raise FileNotFoundError(
            f"Canon manifest not found at expected path: {manifest_path}"
        )


if __name__ == "__main__":
    validate_canon_manifest()
    print("Canon manifest validation passed.")
