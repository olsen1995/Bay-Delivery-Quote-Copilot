from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app import storage


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Dry-run/apply cleanup tool for explicitly allowlisted pre-launch test "
            "quote lineage."
        )
    )
    parser.add_argument(
        "--quote-id",
        dest="quote_ids",
        action="append",
        required=True,
        help="Quote ID to include in the explicit cleanup allowlist. Repeat for multiple quote IDs.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Delete the resolved lineage. Dry-run is the default when omitted.",
    )
    parser.add_argument(
        "--backup-confirmed",
        action="store_true",
        help=(
            "Required with --apply. Confirms that an operator already captured a backup/export "
            "before running the destructive step."
        ),
    )
    return parser


def _print_section(title: str, payload: object) -> None:
    print(f"\n{title}:")
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))


def _render_plan(plan: storage.PrelaunchCleanupPlan) -> None:
    print(f"Database path: {plan['db_path']}")
    print(f"Requested quote_ids: {', '.join(plan['requested_quote_ids'])}")
    if plan["missing_quote_ids"]:
        print(f"Missing quote_ids: {', '.join(plan['missing_quote_ids'])}")
    else:
        print("Missing quote_ids: none")

    _print_section("Counts", plan["counts"])
    _print_section("Quotes", plan["quotes"])
    _print_section("Quote requests", plan["quote_requests"])
    _print_section("Jobs", plan["jobs"])
    _print_section("Attachments", plan["attachments"])


def _render_result(result: storage.PrelaunchCleanupResult) -> None:
    print("\nApply completed.")
    _print_section(
        "Deleted IDs",
        {
            "quotes": result["deleted_quote_ids"],
            "quote_requests": result["deleted_request_ids"],
            "jobs": result["deleted_job_ids"],
            "attachments": result["deleted_attachment_ids"],
        },
    )
    _print_section("Deleted counts", result["counts"])
    if result["missing_quote_ids"]:
        print(f"Missing quote_ids not deleted: {', '.join(result['missing_quote_ids'])}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        plan = storage.plan_prelaunch_test_data_cleanup(list(args.quote_ids))
    except ValueError as exc:
        print(f"REFUSED: {exc}")
        return 2

    mode = "APPLY" if args.apply else "DRY RUN"
    print(f"Mode: {mode}")
    _render_plan(plan)

    if not args.apply:
        print("\nDry run only. No rows were deleted.")
        return 0

    if not args.backup_confirmed:
        print("\nREFUSED: --apply also requires --backup-confirmed.")
        return 2

    result = storage.apply_prelaunch_test_data_cleanup(list(args.quote_ids))
    _render_result(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())