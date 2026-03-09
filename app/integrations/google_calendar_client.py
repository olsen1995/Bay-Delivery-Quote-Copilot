"""
Google Calendar Integration Client

Wraps Google Calendar API calls for calendar sync operations.
This module is the ONLY place that should call gcalendar functions.
"""

from typing import TYPE_CHECKING

from app import gcalendar

if TYPE_CHECKING:
    from app.storage import Job


def is_configured() -> bool:
    """Check if Google Calendar is configured."""
    return gcalendar.is_configured()


def create_event(job: "Job", start_utc: str, end_utc: str) -> str:
    """
    Create a Calendar event for the job.
    
    Args:
        job: Job record
        start_utc: UTC ISO datetime string
        end_utc: UTC ISO datetime string
    
    Returns:
        Calendar event ID
    
    Raises:
        CalendarNotConfigured: If Calendar is not configured
        Exception: On API errors
    """
    return gcalendar.create_event(job, start_utc, end_utc)


def update_event(event_id: str, start_utc: str, end_utc: str) -> None:
    """
    Update an existing Calendar event.
    
    Args:
        event_id: Event ID to update
        start_utc: UTC ISO datetime string
        end_utc: UTC ISO datetime string
    
    Raises:
        CalendarNotConfigured: If Calendar is not configured
        Exception: On API errors
    """
    gcalendar.update_event(event_id, start_utc, end_utc)


def delete_event(event_id: str) -> None:
    """
    Delete a Calendar event.
    
    Args:
        event_id: Event ID to delete
    
    Raises:
        CalendarNotConfigured: If Calendar is not configured
        Exception: On API errors
    """
    gcalendar.delete_event(event_id)
