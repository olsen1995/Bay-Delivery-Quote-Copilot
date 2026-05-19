from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from email.message import EmailMessage
import json
import logging
import os
import smtplib
from typing import Any, Optional

from app import storage

logger = logging.getLogger(__name__)

BOOKING_SUBMITTED_EVENT_TYPE = "customer_booking_submitted"
BOOKING_NOTIFICATION_CHANNEL = "email"


@dataclass(frozen=True)
class BookingNotificationConfig:
    enabled: bool
    email_to: Optional[str]
    email_from: Optional[str]
    smtp_host: Optional[str]
    smtp_port: int
    smtp_username: Optional[str]
    smtp_password: Optional[str] = field(repr=False)
    smtp_starttls: bool
    email_reply_to: Optional[str]
    app_base_url: Optional[str]

    def missing_required(self) -> list[str]:
        required = {
            "BOOKING_NOTIFICATION_EMAIL_TO": self.email_to,
            "BOOKING_NOTIFICATION_EMAIL_FROM": self.email_from,
            "BOOKING_NOTIFICATION_SMTP_HOST": self.smtp_host,
            "BOOKING_NOTIFICATION_SMTP_USERNAME": self.smtp_username,
            "BOOKING_NOTIFICATION_SMTP_PASSWORD": self.smtp_password,
        }
        return [name for name, value in required.items() if not str(value or "").strip()]


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _env_bool(name: str, *, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_str(name: str) -> Optional[str]:
    value = os.getenv(name)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _env_int(name: str, *, default: int) -> int:
    raw = _env_str(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def load_notification_config() -> BookingNotificationConfig:
    return BookingNotificationConfig(
        enabled=_env_bool("BOOKING_REQUEST_NOTIFICATIONS_ENABLED", default=False),
        email_to=_env_str("BOOKING_NOTIFICATION_EMAIL_TO"),
        email_from=_env_str("BOOKING_NOTIFICATION_EMAIL_FROM"),
        smtp_host=_env_str("BOOKING_NOTIFICATION_SMTP_HOST"),
        smtp_port=_env_int("BOOKING_NOTIFICATION_SMTP_PORT", default=587),
        smtp_username=_env_str("BOOKING_NOTIFICATION_SMTP_USERNAME"),
        smtp_password=_env_str("BOOKING_NOTIFICATION_SMTP_PASSWORD"),
        smtp_starttls=_env_bool("BOOKING_NOTIFICATION_SMTP_STARTTLS", default=True),
        email_reply_to=_env_str("BOOKING_NOTIFICATION_EMAIL_REPLY_TO"),
        app_base_url=_env_str("APP_BASE_URL"),
    )


def _request_json(record: dict[str, Any]) -> dict[str, Any]:
    raw = record.get("request_json")
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            loaded = json.loads(raw)
        except Exception:
            return {}
        if isinstance(loaded, dict):
            return loaded
    return {}


def _first_present(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return "N/A"


def _format_money(value: Any) -> str:
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return "N/A"
    return f"${amount:,.2f}"


def compose_booking_notification_email(record: dict[str, Any]) -> tuple[str, str]:
    request_json = _request_json(record)
    request_id = _first_present(record.get("request_id"))
    quote_id = _first_present(record.get("quote_id"))
    customer_name = _first_present(record.get("customer_name"), "Unknown customer")
    subject_label = _first_present(record.get("customer_name"), record.get("service_type"), request_id)
    subject = f"New Bay Delivery booking request: {subject_label} ({request_id})"

    app_base_url = _env_str("APP_BASE_URL")
    admin_url = f"{app_base_url.rstrip('/')}/admin" if app_base_url else "N/A"
    pickup_address = _first_present(
        request_json.get("pickup_address"),
        request_json.get("pickup_location"),
        request_json.get("origin_address"),
    )
    dropoff_address = _first_present(
        request_json.get("dropoff_address"),
        request_json.get("dropoff_location"),
        request_json.get("destination_address"),
    )

    body_lines = [
        "New internal booking request received.",
        "",
        f"Customer name: {customer_name}",
        f"Customer phone: {_first_present(record.get('customer_phone'))}",
        f"Service type: {_first_present(record.get('service_type'))}",
        f"Job address: {_first_present(record.get('job_address'))}",
        f"Pickup address: {pickup_address}",
        f"Dropoff address: {dropoff_address}",
        f"Requested date: {_first_present(record.get('requested_job_date'))}",
        f"Requested time window: {_first_present(record.get('requested_time_window'))}",
        f"Cash total: {_format_money(record.get('cash_total_cad'))}",
        f"EMT total: {_format_money(record.get('emt_total_cad'))}",
        f"Customer notes: {_first_present(record.get('notes'))}",
        f"Admin URL: {admin_url}",
        f"Quote ID: {quote_id}",
        f"Request ID: {request_id}",
    ]
    return subject, "\n".join(body_lines)


def _send_smtp_email(config: BookingNotificationConfig, subject: str, body: str) -> None:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = str(config.email_from or "")
    message["To"] = str(config.email_to or "")
    if config.email_reply_to:
        message["Reply-To"] = config.email_reply_to
    message.set_content(body)

    with smtplib.SMTP(str(config.smtp_host or ""), config.smtp_port, timeout=10) as smtp:
        if config.smtp_starttls:
            smtp.starttls()
        smtp.login(str(config.smtp_username or ""), str(config.smtp_password or ""))
        smtp.send_message(message)


def _sanitize_error(exc: BaseException, config: BookingNotificationConfig) -> str:
    text = f"{exc.__class__.__name__}: {exc}"
    secrets = [
        config.smtp_password,
        config.smtp_username,
    ]
    for secret in secrets:
        if secret:
            text = text.replace(secret, "[redacted]")
    return text[:240]


def notify_customer_booking_submitted(request_id: str) -> dict[str, Any]:
    config = load_notification_config()
    attempt_reserved = False
    quote_id: Optional[str] = None

    try:
        record = storage.get_quote_request_record(request_id)
        if not record:
            logger.warning(
                "Booking notification skipped because request_id=%s was not found",
                request_id,
            )
            return {"status": "skipped", "reason": "request not found"}

        quote_id = record.get("quote_id")
        now_iso = _now_iso()
        attempt = storage.reserve_notification_attempt(
            request_id=request_id,
            event_type=BOOKING_SUBMITTED_EVENT_TYPE,
            quote_id=quote_id,
            channel=BOOKING_NOTIFICATION_CHANNEL,
            recipient=config.email_to,
            created_at=now_iso,
        )
        if attempt is None:
            return {"status": "duplicate"}
        attempt_reserved = True

        if not config.enabled:
            storage.mark_notification_attempt_skipped(
                request_id,
                BOOKING_SUBMITTED_EVENT_TYPE,
                skipped_at=_now_iso(),
                last_error="notifications disabled",
            )
            return {"status": "skipped", "reason": "notifications disabled"}

        missing = config.missing_required()
        if missing:
            reason = "missing notification config: " + ", ".join(sorted(missing))
            storage.mark_notification_attempt_skipped(
                request_id,
                BOOKING_SUBMITTED_EVENT_TYPE,
                skipped_at=_now_iso(),
                last_error=reason,
            )
            logger.warning(
                "Booking notification skipped for request_id=%s quote_id=%s event_type=%s channel=%s reason=%s",
                request_id,
                quote_id,
                BOOKING_SUBMITTED_EVENT_TYPE,
                BOOKING_NOTIFICATION_CHANNEL,
                reason,
            )
            return {"status": "skipped", "reason": reason}

        subject, body = compose_booking_notification_email(dict(record))
        _send_smtp_email(config, subject, body)
        storage.mark_notification_attempt_sent(
            request_id,
            BOOKING_SUBMITTED_EVENT_TYPE,
            sent_at=_now_iso(),
        )
        return {"status": "sent"}
    except Exception as exc:
        sanitized = _sanitize_error(exc, config)
        if attempt_reserved:
            try:
                storage.mark_notification_attempt_failed(
                    request_id,
                    BOOKING_SUBMITTED_EVENT_TYPE,
                    failed_at=_now_iso(),
                    last_error=sanitized,
                )
            except Exception:
                pass
        logger.warning(
            "Booking notification failed for request_id=%s quote_id=%s event_type=%s channel=%s error=%s",
            request_id,
            quote_id,
            BOOKING_SUBMITTED_EVENT_TYPE,
            BOOKING_NOTIFICATION_CHANNEL,
            sanitized,
        )
        return {"status": "failed", "error": sanitized}
