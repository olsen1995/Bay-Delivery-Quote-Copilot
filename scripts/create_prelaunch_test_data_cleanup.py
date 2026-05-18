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
        "--list-quotes",
        action="store_true",
        help="Show recent quote records with full quote IDs in read-only mode.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=25,
        help="Maximum number of recent quote records to show with --list-quotes (default: 25).",
    )
    parser.add_argument(
        "--quote-id",
        dest="quote_ids",
        action="append",
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


def _extract_quote_context(quote: storage.QuoteRecord) -> dict[str, object]:
    request = quote.get("request")
    response = quote.get("response")

    customer_name = None
    service_type = None
    job_address = None
    cash_total_cad = None

    if isinstance(request, dict):
        customer_name = request.get("customer_name")
        service_type = request.get("service_type")
        job_address = request.get("job_address")

    if isinstance(response, dict):
        cash_total_cad = response.get("cash_total_cad")
        if service_type is None:
            service_type = response.get("service_type")

    return {
        "quote_id": quote.get("quote_id"),
        "created_at": quote.get("created_at"),
        "customer_name": customer_name,
        "service_type": service_type,
        "job_address": job_address,
        "cash_total_cad": cash_total_cad,
    }


def _render_quote_list(limit: int) -> None:
    try:
        effective_limit = int(limit)
    except (TypeError, ValueError):
        print("REFUSED: --limit must be an integer.")
        raise SystemExit(2)

    if effective_limit <= 0:
        print("REFUSED: --limit must be greater than zero.")
        raise SystemExit(2)

    quotes = storage.list_quotes(limit=effective_limit, include_expired=True)
    rows = [_extract_quote_context(quote) for quote in quotes]

    print(f"Database path: {storage._resolve_db_path()}")
    print(f"Showing {len(rows)} recent quote records (limit {effective_limit}).")
    _print_section("Quotes", rows)


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

    if args.list_quotes:
        if args.apply or args.backup_confirmed or args.quote_ids:
            print("REFUSED: --list-quotes cannot be combined with cleanup flags.")
            return 2
        _render_quote_list(args.limit)
        return 0

    if not args.quote_ids:
        print("REFUSED: at least one --quote-id is required unless --list-quotes is used.")
        return 2

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
