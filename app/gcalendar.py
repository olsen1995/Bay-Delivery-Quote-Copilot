from __future__ import annotations

import base64
import json
import os
import re
from dataclasses import dataclass
from typing import Dict, Optional, TYPE_CHECKING

# IMPORTANT:
# We intentionally DO NOT import google-auth libraries at module import time.
# This repo should be importable + testable even when Calendar deps are not installed.
# We lazy-import them only when a Calendar call is actually executed.
if TYPE_CHECKING:
    # Only for type-checkers; won't execute at runtime.
    from googleapiclient.discovery import Resource  # pragma: no cover
    from app.storage import Job


GCALENDAR_CALENDAR_ID_ENV = "GCALENDAR_CALENDAR_ID"
GCALENDAR_SA_KEY_B64_ENV = "GCALENDAR_SA_KEY_B64"

CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar"


class CalendarNotConfigured(RuntimeError):
    pass


@dataclass
class CalendarEvent:
    event_id: str
    summary: str
    start: Dict[str, str]
    end: Dict[str, str]


def is_configured() -> bool:
    return bool(os.getenv(GCALENDAR_CALENDAR_ID_ENV)) and bool(os.getenv(GCALENDAR_SA_KEY_B64_ENV))


def _require_google_libs():
    """
    Import google auth libs lazily so tests/local dev can run without installing them.
    Raises CalendarNotConfigured with a clear message if not installed.
    """
    try:
        from google.oauth2 import service_account  # type: ignore
        from googleapiclient.discovery import build  # type: ignore
    except ModuleNotFoundError as e:
        raise CalendarNotConfigured(
            "Google Calendar support requires google-api-python-client and google-auth libraries, but they're not installed. "
            "Either install dependencies OR disable Calendar features by "
            "leaving GCALENDAR_CALENDAR_ID / GCALENDAR_SA_KEY_B64 unset."
        ) from e

    return service_account, build


def _load_service_account_info() -> Dict[str, Any]:
    b64 = os.getenv(GCALENDAR_SA_KEY_B64_ENV, "").strip()
    if not b64:
        raise CalendarNotConfigured("Missing GCALENDAR_SA_KEY_B64 environment variable.")
    try:
        raw = base64.b64decode(b64.encode("utf-8")).decode("utf-8")
        return json.loads(raw)
    except Exception as e:
        raise CalendarNotConfigured(f"Failed to decode GCALENDAR_SA_KEY_B64: {e}")


def _service():
    service_account, build = _require_google_libs()
    info = _load_service_account_info()
    creds = service_account.Credentials.from_service_account_info(info, scopes=[CALENDAR_SCOPE])
    return build('calendar', 'v3', credentials=creds)


def _calendar_id() -> str:
    calendar_id = os.getenv(GCALENDAR_CALENDAR_ID_ENV, "").strip()
    if not calendar_id:
        raise CalendarNotConfigured("Missing GCALENDAR_CALENDAR_ID environment variable.")
    return calendar_id


def _compact_service_label(service_type: str) -> str:
    value = str(service_type or "").strip().replace("_", " ")
    return re.sub(r"\s+", " ", value).title() or "Job"


def _event_summary(job: "Job") -> str:
    service_label = _compact_service_label(job.get("service_type", ""))
    job_id = str(job.get("job_id") or "N/A").strip() or "N/A"
    return f"{service_label} - Job {job_id}"[:120]


def _event_description(job: "Job") -> str:
    scheduling_context = job.get("scheduling_context") or {}
    lines = [
        f"Job ID: {job.get('job_id') or 'N/A'}",
        f"Quote ID: {job.get('quote_id') or 'N/A'}",
        f"Request ID: {scheduling_context.get('request_id') or job.get('request_id') or 'N/A'}",
        f"Service: {_compact_service_label(job.get('service_type', ''))}",
        f"Requested Date: {scheduling_context.get('requested_job_date') or 'Not provided'}",
        f"Requested Window: {scheduling_context.get('requested_time_window') or 'Not provided'}",
        "Location details in Bay Delivery system",
    ]
    return "\n".join(lines)


def create_event(job: "Job", start_utc: str, end_utc: str) -> str:
    """
    Create a minimal mirror Calendar event for the job.
    Title: {service_type} - Job {job_id}
    Description: safe internal identifiers and scheduling context only.
    """
    service = _service()
    calendar_id = _calendar_id()

    summary = _event_summary(job)
    description = _event_description(job)

    event = {
        'summary': summary,
        'description': description,
        'start': {'dateTime': start_utc, 'timeZone': 'UTC'},
        'end': {'dateTime': end_utc, 'timeZone': 'UTC'},
    }

    created_event = service.events().insert(calendarId=calendar_id, body=event).execute()
    return created_event['id']


def update_event(job: "Job", event_id: str, start_utc: str, end_utc: str) -> None:
    """
    Update an existing Calendar event's times.
    """
    service = _service()
    calendar_id = _calendar_id()

    event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
    event['summary'] = _event_summary(job)
    event['description'] = _event_description(job)
    event['start'] = {'dateTime': start_utc, 'timeZone': 'UTC'}
    event['end'] = {'dateTime': end_utc, 'timeZone': 'UTC'}

    service.events().update(calendarId=calendar_id, eventId=event_id, body=event).execute()


def delete_event(event_id: str) -> None:
    """
    Delete a Calendar event.
    """
    service = _service()
    calendar_id = _calendar_id()

    service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
