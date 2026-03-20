"""
Job Scheduling Service

Manages the complete job scheduling workflow following these principles:
1. Database writes first (source of truth)
2. Google Calendar sync second (mirror only)
3. Sync failures do NOT corrupt DB state
4. Preserve scheduling history on cancel
"""

from datetime import datetime
from typing import Optional

from app.integrations import google_calendar_client
from app.storage import Job, get_job, update_job
from app.update_fields import validate_job_transition


def _validate_datetime_range(start_utc: str, end_utc: str) -> None:
    """Validate that end_utc is after start_utc."""
    try:
        start_dt = datetime.fromisoformat(start_utc)
        end_dt = datetime.fromisoformat(end_utc)
        if end_dt <= start_dt:
            raise ValueError("scheduled_end must be after scheduled_start")
    except ValueError as e:
        raise ValueError(f"Invalid datetime range: {e}") from e


def _require_job(job_id: str) -> Job:
    """Load a job or raise ValueError if not found. Narrows Optional[Job] to Job."""
    job = get_job(job_id)
    if not job:
        raise ValueError("Job not found")
    return job


def _ensure_transition(job: Job, next_status: str) -> None:
    validate_job_transition(str(job.get("status") or ""), next_status)


def schedule_job(job_id: str, scheduled_start: str, scheduled_end: str) -> Job:
    """
    Schedule a job for the first time.

    Flow:
    1. Load and validate job exists and is schedulable
    2. Validate datetime range
    3. Write to DB first (source of truth)
    4. Attempt Google Calendar sync (mirror)
    5. On sync failure, update only sync state/error

    Args:
        job_id: Job ID to schedule
        scheduled_start: UTC ISO datetime string
        scheduled_end: UTC ISO datetime string

    Returns:
        Updated Job record

    Raises:
        ValueError: Job not found, not schedulable, or invalid datetime
        HTTPException: Will be raised by caller (not this layer)
    """
    job = get_job(job_id)
    if not job:
        raise ValueError("Job not found")

    if job.get("status") not in {"approved", "scheduled"}:
        raise ValueError("Job must be approved or scheduled before scheduling")

    _validate_datetime_range(scheduled_start, scheduled_end)

    # DB first: update job with schedule and pending sync status
    updated = update_job(
        job_id,
        scheduled_start=scheduled_start,
        scheduled_end=scheduled_end,
        calendar_sync_status="pending",
    )
    if not updated:
        raise ValueError("Failed to update job in database")

    # Calendar second: attempt to sync
    try:
        if google_calendar_client.is_configured():
            event_id = google_calendar_client.create_event(job, scheduled_start, scheduled_end)
            update_job(job_id, google_calendar_event_id=event_id, calendar_sync_status="synced", calendar_last_error=None)
        else:
            update_job(job_id, calendar_sync_status="not_configured", calendar_last_error=None)
    except Exception as e:
        # Sync failed, but DB is intact. Update only sync state.
        update_job(job_id, calendar_sync_status="failed", calendar_last_error=str(e))

    return _require_job(job_id)


def reschedule_job(job_id: str, scheduled_start: str, scheduled_end: str) -> Job:
    """
    Reschedule an existing job that is already scheduled.

    Flow:
    1. Load and validate job exists, is schedulable, and has a calendar event
    2. Validate datetime range
    3. Write to DB first
    4. Attempt Google Calendar sync to update existing event
    5. On sync failure, update only sync state/error

    Args:
        job_id: Job ID to reschedule
        scheduled_start: UTC ISO datetime string
        scheduled_end: UTC ISO datetime string

    Returns:
        Updated Job record

    Raises:
        ValueError: Job not found, not schedulable, not scheduled, or invalid datetime
    """
    job = get_job(job_id)
    if not job:
        raise ValueError("Job not found")

    if job.get("status") not in {"approved", "scheduled"}:
        raise ValueError("Job must be approved or scheduled before scheduling")

    if not job.get("google_calendar_event_id"):
        raise ValueError("Job not scheduled")

    _validate_datetime_range(scheduled_start, scheduled_end)

    # DB first
    updated = update_job(
        job_id,
        scheduled_start=scheduled_start,
        scheduled_end=scheduled_end,
        calendar_sync_status="pending",
    )
    if not updated:
        raise ValueError("Failed to update job in database")

    # Calendar second
    try:
        event_id = job.get("google_calendar_event_id")
        if google_calendar_client.is_configured() and event_id:
            latest_job = updated
            google_calendar_client.update_event(latest_job, event_id, scheduled_start, scheduled_end)
            update_job(job_id, calendar_sync_status="synced", calendar_last_error=None)
        else:
            update_job(job_id, calendar_sync_status="not_configured", calendar_last_error=None)
    except Exception as e:
        # Sync failed, but DB is intact. Update only sync state.
        update_job(job_id, calendar_sync_status="failed", calendar_last_error=str(e))

    return _require_job(job_id)


def start_job(job_id: str, started_at: str) -> Job:
    """Mark an approved job as in progress."""
    job = _require_job(job_id)
    _ensure_transition(job, "in_progress")

    updated = update_job(
        job_id,
        status="in_progress",
        started_at=started_at,
    )
    if not updated:
        raise ValueError("Failed to update job in database")

    return _require_job(job_id)


def complete_job(job_id: str, completed_at: str, closeout_notes: Optional[str]) -> Job:
    """Mark an in-progress job as completed."""
    job = _require_job(job_id)
    _ensure_transition(job, "completed")

    updated = update_job(
        job_id,
        status="completed",
        completed_at=completed_at,
        closeout_notes=closeout_notes,
    )
    if not updated:
        raise ValueError("Failed to update job in database")

    return _require_job(job_id)


def cancel_job(job_id: str, cancelled_at: Optional[str], closeout_notes: Optional[str] = None) -> Job:
    """
    Cancel an approved or in-progress job.

    Preserves scheduling history (scheduled_start/end remain in DB).

    Flow:
    1. Load and validate job exists
    2. Write cancellation to DB first (preserve history, mark cancelled)
    3. Attempt to delete from Google Calendar (if event exists)
    4. On delete success: clear event_id
    5. On delete failure: update sync state/error, keep event_id

    Args:
        job_id: Job ID to cancel

    Returns:
        Updated Job record (status=cancelled)

    Raises:
        ValueError: Job not found
    """
    job = get_job(job_id)
    if not job:
        raise ValueError("Job not found")
    _ensure_transition(job, "cancelled")

    # DB first: mark cancelled (preserves scheduled_start/end)
    updated = update_job(
        job_id,
        status="cancelled",
        calendar_sync_status="cancelled",
        cancelled_at=cancelled_at,
        closeout_notes=closeout_notes,
    )
    if not updated:
        raise ValueError("Failed to update job in database")

    # Calendar second: attempt delete
    event_id = job.get("google_calendar_event_id")
    if event_id:
        try:
            if google_calendar_client.is_configured():
                google_calendar_client.delete_event(event_id)
                # Delete success: clear event_id
                update_job(job_id, google_calendar_event_id=None, calendar_last_error=None)
            else:
                # Not configured, keep event_id as-is
                pass
        except Exception as e:
            # Delete failed, keep event_id and mark failed
            update_job(job_id, calendar_sync_status="failed", calendar_last_error=str(e))

    return _require_job(job_id)
