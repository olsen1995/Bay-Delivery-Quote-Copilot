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

    return {
        "generated_at": generated_at.isoformat(),
        "counts": {card["key"]: card["count"] for card in cards},
        "cards": cards,
    }


def _utc_now(now: datetime | None) -> datetime:
    if now is None:
        return datetime.now(timezone.utc)
    if now.tzinfo is None:
        return now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc)
