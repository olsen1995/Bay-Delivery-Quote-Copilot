from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from app.storage import load_admin_ops_queue_sources

STALE_PENDING_ESTIMATE_DAYS = 7
SECTION_ITEM_LIMIT = 10

COUNT_KEYS = (
    "accepted_needing_approval",
    "followup_marked",
    "completed_missing_costing",
    "jobs_missing_schedule",
    "jobs_missing_booking_preferences",
    "stale_pending_estimates",
)


def build_admin_ops_queue(*, now: datetime | None = None) -> dict[str, Any]:
    generated_at = _utc_now(now)
    stale_pending_before = generated_at - timedelta(days=STALE_PENDING_ESTIMATE_DAYS)
    sources = load_admin_ops_queue_sources(
        item_limit=SECTION_ITEM_LIMIT,
        stale_pending_before_iso=stale_pending_before.isoformat(),
    )
    source_counts = sources["counts"]
    source_items = sources["items"]

    section_defs = [
        (
            "accepted_needing_approval",
            "Accepted Requests Needing Approval",
            [
                _request_item(
                    request,
                    reason="Customer accepted the estimate and is waiting for admin review.",
                    action_hint="Review Booking Requests, then approve or reject from the existing table.",
                )
                for request in source_items.get("accepted_needing_approval", [])
            ],
        ),
        (
            "followup_marked",
            "Follow-up Marked / Needs Attention",
            [
                _request_item(
                    request,
                    reason=f"Follow-up marker: {_label_followup_status(request.get('followup_status'))}.",
                    action_hint="Use Booking Requests to review the marker, contact status, and next manual step.",
                )
                for request in source_items.get("followup_marked", [])
            ],
        ),
        (
            "completed_missing_costing",
            "Completed Jobs Missing Costing",
            [
                _job_item(
                    job,
                    reason="Job is completed, but completed-job costing has not been filled in.",
                    action_hint="Use Jobs to enter actual hours, costs, payment status, and quote accuracy notes.",
                )
                for job in source_items.get("completed_missing_costing", [])
            ],
        ),
        (
            "jobs_missing_schedule",
            "Jobs Missing Schedule",
            [
                _job_item(
                    job,
                    reason="Job is open and has no scheduled start time.",
                    action_hint="Use Jobs to schedule or reschedule from the existing controls.",
                )
                for job in source_items.get("jobs_missing_schedule", [])
            ],
        ),
        (
            "jobs_missing_booking_preferences",
            "Jobs Missing Booking Preferences",
            [
                _job_item(
                    job,
                    reason=_missing_booking_preferences_reason(job),
                    action_hint="Review the linked request context and follow up manually before scheduling.",
                )
                for job in source_items.get("jobs_missing_booking_preferences", [])
            ],
        ),
        (
            "stale_pending_estimates",
            "Stale Pending Estimates",
            [
                _quote_item(
                    quote,
                    reason=f"Pending estimate is older than {STALE_PENDING_ESTIMATE_DAYS} days.",
                    action_hint="Review Recent Estimates manually; this queue does not expire records.",
                )
                for quote in source_items.get("stale_pending_estimates", [])
            ],
        ),
    ]

    counts: dict[str, int] = {}
    sections: list[dict[str, Any]] = []
    for section_id, title, items in section_defs:
        counts[section_id] = int(source_counts.get(section_id, len(items)))
        sections.append(
            {
                "id": section_id,
                "title": title,
                "count": counts[section_id],
                "items": items,
            }
        )

    for key in COUNT_KEYS:
        counts.setdefault(key, 0)

    return {
        "generated_at": generated_at.isoformat(),
        "counts": counts,
        "sections": sections,
    }


def _utc_now(now: datetime | None) -> datetime:
    if now is None:
        return datetime.now(timezone.utc)
    if now.tzinfo is None:
        return now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc)


def _base_item(kind: str, record: dict[str, Any], *, reason: str, action_hint: str) -> dict[str, Any]:
    return {
        "kind": kind,
        "id": record.get("request_id") or record.get("job_id") or record.get("quote_id"),
        "quote_id": record.get("quote_id"),
        "request_id": record.get("request_id"),
        "job_id": record.get("job_id"),
        "customer_name": record.get("customer_name"),
        "customer_phone": record.get("customer_phone"),
        "service_type": record.get("service_type"),
        "status": record.get("status") or record.get("admin_status"),
        "created_at": record.get("created_at"),
        "reason": reason,
        "action_hint": action_hint,
    }


def _request_item(request: dict[str, Any], *, reason: str, action_hint: str) -> dict[str, Any]:
    return _base_item("quote_request", request, reason=reason, action_hint=action_hint)


def _job_item(job: dict[str, Any], *, reason: str, action_hint: str) -> dict[str, Any]:
    return _base_item("job", job, reason=reason, action_hint=action_hint)


def _quote_item(quote: dict[str, Any], *, reason: str, action_hint: str) -> dict[str, Any]:
    request = _quote_request_payload(quote)
    merged = {
        **request,
        "quote_id": quote.get("quote_id"),
        "created_at": quote.get("created_at"),
        "status": quote.get("admin_status") or "pending",
    }
    return _base_item("quote", merged, reason=reason, action_hint=action_hint)


def _label_followup_status(value: Any) -> str:
    labels = {
        "needs_followup": "Needs follow-up",
        "contacted": "Contacted",
        "waiting_on_customer": "Waiting on customer",
        "not_ready": "Not ready",
    }
    return labels.get(str(value or ""), str(value or "Marked"))


def _quote_request_payload(quote: dict[str, Any]) -> dict[str, Any]:
    if isinstance(quote.get("request"), dict):
        return quote["request"]
    request_json = quote.get("request_json")
    if isinstance(request_json, dict):
        return request_json
    if isinstance(request_json, str):
        try:
            parsed = json.loads(request_json)
        except ValueError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _missing_booking_preferences_reason(job: dict[str, Any]) -> str:
    missing: list[str] = []
    if job.get("missing_quote_request"):
        missing.append("quote_request")
    if job.get("missing_requested_job_date"):
        missing.append("requested_job_date")
    if job.get("missing_requested_time_window"):
        missing.append("requested_time_window")
    if missing:
        return "Missing booking preference fields: " + ", ".join(missing) + "."
    return "Booking preference date or time window is missing."
