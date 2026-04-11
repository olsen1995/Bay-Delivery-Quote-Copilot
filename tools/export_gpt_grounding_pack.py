#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = ROOT / "dist" / "gpt_grounding_pack"
KNOWLEDGE_PACK_FILES = [
    Path("docs/gpt/GPT_SOURCE_OF_TRUTH.md"),
    Path("docs/gpt/GPT_SYSTEM_BOUNDARIES.md"),
    Path("docs/gpt/GPT_BUSINESS_RULES.md"),
    Path("docs/gpt/GPT_WORKFLOW_RULES.md"),
    Path("docs/gpt/GPT_CURRENT_STATE.md"),
    Path("PROJECT_RULES.md"),
    Path("docs/CURRENT_STATE.md"),
    Path("README.md"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the curated Bay Delivery GPT grounding pack to a single folder."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Destination folder for copied grounding files (default: {DEFAULT_OUTPUT_DIR})",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir
    if not output_dir.is_absolute():
        output_dir = ROOT / output_dir

    output_dir.mkdir(parents=True, exist_ok=True)

    manifest_lines = [
        "Bay Delivery GPT Knowledge Pack",
        "",
        "Upload these files to the custom GPT Knowledge panel:",
        "",
    ]

    for relative_path in KNOWLEDGE_PACK_FILES:
        source = ROOT / relative_path
        if not source.exists():
            raise FileNotFoundError(f"Missing grounding file: {relative_path}")
        destination = output_dir / source.name
        shutil.copy2(source, destination)
        manifest_lines.append(f"- {relative_path.as_posix()}")

    manifest_lines.extend(
        [
            "",
            "Builder instructions source:",
            "- docs/gpt/GPT_BUILDER_INSTRUCTIONS.md",
            "",
            "Acceptance tests source:",
            "- docs/gpt/GPT_ACCEPTANCE_TESTS.md",
        ]
    )

    (output_dir / "UPLOAD_MANIFEST.txt").write_text(
        "\n".join(manifest_lines) + "\n",
        encoding="utf-8",
    )

    print(f"Exported {len(KNOWLEDGE_PACK_FILES)} grounding files to {output_dir}")
    print(f"Wrote upload manifest to {output_dir / 'UPLOAD_MANIFEST.txt'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
