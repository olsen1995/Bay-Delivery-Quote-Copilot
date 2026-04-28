import hashlib
import json
import sys
from pathlib import Path

from export_gpt_grounding_pack import UPLOAD_SET


REPO_ROOT = Path(__file__).resolve().parents[1]
PACK_DIR = REPO_ROOT / "dist" / "gpt_grounding_pack"
MANIFEST_PATH = PACK_DIR / "manifest.json"
EXCLUDED_UPLOAD_SOURCES = {"docs/gpt/GPT_REFRESH_WORKFLOW.md"}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest() -> list[dict[str, str]]:
    try:
        raw = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Missing manifest: {MANIFEST_PATH.relative_to(REPO_ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid manifest JSON: {exc}") from exc

    upload_set = raw.get("upload_set")
    if not isinstance(upload_set, list):
        raise ValueError("manifest.json must contain an upload_set list.")

    return upload_set


def main() -> int:
    errors: list[str] = []

    if not PACK_DIR.exists():
        errors.append(f"Missing grounding pack directory: {PACK_DIR.relative_to(REPO_ROOT)}")
        upload_set = []
    else:
        try:
            upload_set = load_manifest()
        except ValueError as exc:
            errors.append(str(exc))
            upload_set = []

    expected_sources = list(UPLOAD_SET)
    manifest_sources = [item.get("file") for item in upload_set]
    if manifest_sources != expected_sources:
        errors.append(
            "Manifest upload_set does not match export_gpt_grounding_pack.UPLOAD_SET "
            f"in order. expected={expected_sources!r} actual={manifest_sources!r}"
        )

    expected_outputs = {Path(source).name for source in expected_sources}
    expected_pack_files = expected_outputs | {"manifest.json"}
    if PACK_DIR.exists():
        actual_pack_files = {path.name for path in PACK_DIR.iterdir() if path.is_file()}
        extra_files = sorted(actual_pack_files - expected_pack_files)
        missing_files = sorted(expected_pack_files - actual_pack_files)
        if extra_files:
            errors.append(f"Unexpected files in grounding pack: {extra_files!r}")
        if missing_files:
            errors.append(f"Missing files from grounding pack: {missing_files!r}")

    for source in EXCLUDED_UPLOAD_SOURCES:
        if source in manifest_sources:
            errors.append(f"{source} must not be included in the GPT grounding upload set.")
        if (PACK_DIR / Path(source).name).exists():
            errors.append(f"{Path(source).name} must not be exported into {PACK_DIR.relative_to(REPO_ROOT)}.")

    seen_outputs: set[str] = set()
    for index, item in enumerate(upload_set):
        source = item.get("file")
        output = item.get("output")
        manifest_hash = item.get("sha256")

        if not isinstance(source, str) or not isinstance(output, str) or not isinstance(manifest_hash, str):
            errors.append(f"Manifest entry {index} must contain string file, output, and sha256 values.")
            continue

        expected_output = Path(source).name
        if output != expected_output:
            errors.append(f"Manifest output mismatch for {source}: expected {expected_output!r}, found {output!r}.")

        if output in seen_outputs:
            errors.append(f"Duplicate manifest output entry: {output}")
        seen_outputs.add(output)

        source_path = REPO_ROOT / source
        output_path = PACK_DIR / output
        if not source_path.exists():
            errors.append(f"Missing source file: {source}")
            continue
        if not output_path.exists():
            errors.append(f"Missing exported file: {output_path.relative_to(REPO_ROOT)}")
            continue

        source_hash = sha256_file(source_path)
        output_hash = sha256_file(output_path)
        if manifest_hash != source_hash:
            errors.append(f"Manifest hash for {source} does not match canonical source.")
        if output_hash != source_hash:
            errors.append(f"Exported file {output} does not match canonical source {source}.")

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print(f"GPT grounding pack parity OK: {len(expected_sources)} files match manifest and sources.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
