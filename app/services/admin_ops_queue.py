from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.storage import load_admin_ops_queue_sources

STALE_PENDING_ESTIMATE_DAYS = 7

BOARD_CARDS = (
    (
        "new_requests",
        "New Requests",
        "Recent quote requests that still need admin attention.",
    ),
    (
        "needs_followup",
        "Needs Follow-Up",
        "Requests marked for follow-up or waiting on the next manual step.",
    ),
    (
        "accepted_not_booked",
        "Accepted, Not Booked",
        "Accepted or approved work that is not yet on the schedule.",
    ),
    (
        "upcoming_jobs",
        "Upcoming Jobs",
        "Scheduled jobs with a valid future start time.",
    ),
    (
        "completed_missing_costs",
        "Completed, Missing Costs",
        "Completed jobs missing required closeout or actual costing fields.",
    ),
    (
        "owner_review",
        "Owner Review",
        "Active work whose existing request details recommend manual owner review.",
    ),
    (
        "stale_quotes",
        "Stale Quotes",
        "Pending estimates older than the stale-quote review window.",
    ),
)


def build_admin_ops_queue(*, now: datetime | None = None) -> dict[str, Any]:
    generated_at = _utc_now(now)
    stale_pending_before = generated_at - timedelta(days=STALE_PENDING_ESTIMATE_DAYS)
    sources = load_admin_ops_queue_sources(
        stale_pending_before_iso=stale_pending_before.isoformat(),
        upcoming_start_iso=generated_at.isoformat(),
    )

    counts = {key: int(sources["counts"].get(key, 0)) for key, _label, _desc in BOARD_CARDS}

    cards = [
        {
            "key": key,
            "label": label,
            "count": int(counts.get(key, 0)),
            "description": description,
        }
        for key, label, description in BOARD_CARDS
    ]

    accepted_not_booked_items = [
        _normalize_accepted_not_booked_item(item)
        for item in sources.get("accepted_not_booked_detail_sources", [])
    ]

    return {
        "generated_at": generated_at.isoformat(),
        "counts": {card["key"]: card["count"] for card in cards},
        "cards": cards,
        "accepted_not_booked_items": accepted_not_booked_items,
    }


def _utc_now(now: datetime | None) -> datetime:
    if now is None:
        return datetime.now(timezone.utc)
    if now.tzinfo is None:
        return now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc)


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    return False


def _friendly_time_window(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "Not provided"
    return raw.replace("_", " ").title()


def _normalize_accepted_not_booked_item(source: dict[str, Any]) -> dict[str, Any]:
    item_type = str(source.get("item_type") or "request")
    job_id = source.get("job_id")
    status = str(source.get("status") or "")
    requested_job_date = source.get("requested_job_date")
    requested_time_window = source.get("requested_time_window")
    scheduled_start = source.get("scheduled_start")
    scheduled_end = source.get("scheduled_end")
    google_calendar_event_id = source.get("google_calendar_event_id")

    missing_scheduling_fields: list[str] = []
    if _is_missing(job_id):
        missing_scheduling_fields.append("job_id")
    if _is_missing(requested_job_date):
        missing_scheduling_fields.append("requested_job_date")
    if _is_missing(requested_time_window):
        missing_scheduling_fields.append("requested_time_window")
    if _is_missing(scheduled_start):
        missing_scheduling_fields.append("scheduled_start")
    if _is_missing(scheduled_end):
        missing_scheduling_fields.append("scheduled_end")

    if _is_missing(job_id):
        scheduling_ready = False
        if status == "customer_accepted":
            scheduling_summary = "Accepted request still needs admin approval before a job can be scheduled."
            recommended_action = "approve_request"
        elif status == "admin_approved":
            scheduling_summary = "Approved request still needs a job record before scheduling can open."
            recommended_action = "needs_job"
        else:
            scheduling_summary = "Scheduling is waiting on an admin workflow step before a job can be opened."
            recommended_action = "review_request"
    else:
        scheduling_ready = True
        if _is_missing(requested_job_date) or _is_missing(requested_time_window):
            scheduling_summary = "Ready to schedule now. Customer preference details are incomplete, so confirm timing manually if needed."
        else:
            scheduling_summary = "Ready to schedule now using the saved customer date and time preferences."
        recommended_action = "schedule_job"

    return {
        "item_type": item_type,
        "item_id": source.get("item_id"),
        "request_id": source.get("request_id"),
        "job_id": job_id,
        "quote_id": source.get("quote_id"),
        "customer_name": source.get("customer_name"),
        "customer_phone": source.get("customer_phone"),
        "service_type": source.get("service_type"),
        "job_address": source.get("job_address"),
        "status": status,
        "requested_job_date": requested_job_date,
        "requested_time_window": requested_time_window,
        "scheduled_start": scheduled_start,
        "scheduled_end": scheduled_end,
        "google_calendar_event_id": google_calendar_event_id,
        "scheduling_ready": scheduling_ready,
        "missing_scheduling_fields": missing_scheduling_fields,
        "scheduling_summary": scheduling_summary,
        "recommended_action": recommended_action,
        "created_at": source.get("created_at"),
        "submitted_at": source.get("submitted_at"),
        "notes": source.get("notes"),
        "preferred_window_label": _friendly_time_window(requested_time_window),
    }
