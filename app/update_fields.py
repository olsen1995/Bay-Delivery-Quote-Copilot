from __future__ import annotations

from typing import Any


QUOTE_REQUEST_ALLOWED_TRANSITIONS: dict[str, list[str]] = {
    "customer_pending": ["customer_accepted", "customer_declined"],
    "customer_accepted": ["admin_approved", "rejected"],
    "customer_declined": [],
    "admin_approved": [],
    "rejected": [],
}

QUOTE_REQUEST_INITIAL_ALLOWED: list[str] = [
    "customer_pending",
    "customer_accepted",
    "customer_declined",
]

JOB_ALLOWED_TRANSITIONS: dict[str, list[str]] = {
    "approved": ["scheduled", "in_progress", "cancelled"],
    "scheduled": ["in_progress", "cancelled"],
    "in_progress": ["completed", "cancelled"],
    "completed": [],
    "cancelled": [],
}


class InvalidQuoteRequestTransition(ValueError):
    def __init__(self, from_status: str, to_status: str, allowed: list[str]):
        self.from_status = from_status
        self.to_status = to_status
        self.allowed = allowed
        super().__init__(f"invalid quote_request status transition: from={from_status}, to={to_status}, allowed={allowed}")


class InvalidJobTransition(ValueError):
    def __init__(self, from_status: str, to_status: str, allowed: list[str]):
        self.from_status = from_status
        self.to_status = to_status
        self.allowed = allowed
        super().__init__(f"invalid job status transition: from={from_status}, to={to_status}, allowed={allowed}")


def validate_quote_request_transition(old_status: str, new_status: str) -> list[str]:
    if old_status == "__new__":
        allowed = list(QUOTE_REQUEST_INITIAL_ALLOWED)
        if new_status not in allowed:
            raise InvalidQuoteRequestTransition(old_status, new_status, allowed)
        return allowed

    allowed = list(QUOTE_REQUEST_ALLOWED_TRANSITIONS.get(old_status, []))

    if old_status == new_status:
        return allowed

    if new_status not in allowed:
        raise InvalidQuoteRequestTransition(old_status, new_status, allowed)

    return allowed


def validate_job_transition(old_status: str, new_status: str) -> list[str]:
    allowed = list(JOB_ALLOWED_TRANSITIONS.get(old_status, []))

    if old_status == new_status:
        raise InvalidJobTransition(old_status, new_status, allowed)

    if new_status not in allowed:
        raise InvalidJobTransition(old_status, new_status, allowed)

    return allowed


def include_optional_update_fields(
    body: Any,
    update_kwargs: dict[str, Any],
    field_names: tuple[str, ...],
) -> None:
    """Include optional fields in update kwargs even when explicitly set to null.

    For Optional[...] request fields, parsing often maps both an omitted field and an
    explicit JSON null to `None`. We must distinguish *provided* vs *omitted*.

    Uses Pydantic's field tracking when available:
      - Pydantic v2: body.model_fields_set
      - Pydantic v1: body.__fields_set__
    """
    provided_fields = getattr(body, "model_fields_set", None)
    if provided_fields is None:
        provided_fields = getattr(body, "__fields_set__", set())

    for field_name in field_names:
        if field_name in provided_fields:
            update_kwargs[field_name] = getattr(body, field_name)
