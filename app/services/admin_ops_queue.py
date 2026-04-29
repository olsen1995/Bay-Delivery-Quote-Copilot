from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from app.storage import list_jobs, list_quote_requests, list_quotes

STALE_PENDING_ESTIMATE_DAYS = 7
SOURCE_LIST_LIMIT = 100
MAX_SOURCE_RECORDS = 100000
SECTION_ITEM_LIMIT = 10

OPEN_FOLLOWUP_STATUSES = {
    "needs_followup",
    "contacted",
    "waiting_on_customer",
    "not_ready",
}

OPEN_JOB_STATUSES = {"approved", "scheduled", "in_progress"}
SCHEDULE_EXPECTED_STATUSES = {"approved", "scheduled"}

COUNT_KEYS = (
    "accepted_needing_approval",
    "followup_marked",
    "completed_missing_costing",
    "jobs_missing_schedule",
    "jobs_missing_booking_preferences",
    "stale_pending_estimates",
)

CORE_COSTING_FIELDS = (
    "actual_hours",
    "actual_crew_size",
    "final_amount_collected_cad",
    "payment_status",
    "job_profit_status",
)


def build_admin_ops_queue(*, now: datetime | None = None) -> dict[str, Any]:
    generated_at = _utc_now(now)
    quotes = _load_available(lambda limit, offset: list_quotes(limit=limit, offset=offset))
    requests = _load_available(
        lambda limit, offset: list_quote_requests(
            limit=limit,
            include_followup_status=True,
            offset=offset,
        )
    )
    jobs = _load_available(lambda limit, offset: list_jobs(limit=limit, offset=offset))

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
                for request in requests
                if request.get("status") == "customer_accepted"
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
                for request in requests
                if str(request.get("followup_status") or "") in OPEN_FOLLOWUP_STATUSES
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
                for job in jobs
                if job.get("status") == "completed" and _job_costing_missing(job)
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
                for job in jobs
                if str(job.get("status") or "") in SCHEDULE_EXPECTED_STATUSES and not job.get("scheduled_start")
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
                for job in jobs
                if str(job.get("status") or "") in OPEN_JOB_STATUSES and _missing_booking_preferences(job)
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
                for quote in quotes
                if _is_stale_pending_quote(quote, generated_at)
            ],
        ),
    ]

    counts: dict[str, int] = {}
    sections: list[dict[str, Any]] = []
    for section_id, title, items in section_defs:
        counts[section_id] = len(items)
        sections.append(
            {
                "id": section_id,
                "title": title,
                "count": len(items),
                "items": items[:SECTION_ITEM_LIMIT],
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


def _load_available(fetcher: Callable[[int, int], list[Any]]) -> list[Any]:
    out: list[Any] = []
    offset = 0
    while True:
        remaining = MAX_SOURCE_RECORDS - len(out)
        if remaining <= 0:
            return out

        limit = min(SOURCE_LIST_LIMIT, remaining)
        batch = fetcher(limit, offset)
        out.extend(batch)
        if len(batch) < limit:
            return out
        offset += len(batch)


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


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
    request = quote.get("request") if isinstance(quote.get("request"), dict) else {}
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


def _job_costing_missing(job: dict[str, Any]) -> bool:
    return any(job.get(field) in (None, "") for field in CORE_COSTING_FIELDS)


def _missing_booking_preferences(job: dict[str, Any]) -> bool:
    context = job.get("scheduling_context")
    if isinstance(context, dict):
        missing = context.get("missing_fields")
        if isinstance(missing, list):
            return bool(missing)
        return not context.get("requested_job_date") or not context.get("requested_time_window")
    return False


def _missing_booking_preferences_reason(job: dict[str, Any]) -> str:
    context = job.get("scheduling_context")
    if not isinstance(context, dict):
        return "Linked booking preference context is unavailable."
    missing = context.get("missing_fields")
    if isinstance(missing, list) and missing:
        return "Missing booking preference fields: " + ", ".join(str(item) for item in missing) + "."
    return "Booking preference date or time window is missing."


def _is_stale_pending_quote(quote: dict[str, Any], now: datetime) -> bool:
    if quote.get("admin_status", "pending") != "pending":
        return False
    created_at = _parse_datetime(quote.get("created_at"))
    if created_at is None:
        return False
    return created_at <= now - timedelta(days=STALE_PENDING_ESTIMATE_DAYS)
