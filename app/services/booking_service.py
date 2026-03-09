from __future__ import annotations

from typing import Any, Optional
from uuid import uuid4

from fastapi import HTTPException

from app.storage import (
    get_job_by_quote_id,
    get_quote_record,
    get_quote_request,
    get_quote_request_by_quote_id,
    is_token_expired,
    save_job,
    save_quote_request,
    update_quote_request,
)
from app.update_fields import InvalidQuoteRequestTransition, validate_quote_request_transition


def process_customer_decision(
    quote_id: str,
    *,
    action: str,
    accept_token: str,
    notes: Optional[str],
    notes_provided: bool,
    now_iso: str,
) -> dict[str, Any]:
    quote = get_quote_record(quote_id)
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found.")

    existing = get_quote_request_by_quote_id(quote_id)
    normalized_action = (action or "").lower()

    if normalized_action not in {"accept", "decline"}:
        raise HTTPException(status_code=400, detail="Invalid action (use accept|decline).")

    # Validate accept_token against server-persisted token.
    server_token = quote.get("accept_token")
    if not server_token or accept_token != server_token:
        raise HTTPException(status_code=401, detail="Invalid or expired accept token.")

    if not existing:
        initial_status = "customer_pending"
        if normalized_action == "accept":
            initial_status = "customer_accepted"
        elif normalized_action == "decline":
            initial_status = "customer_declined"

        validate_quote_request_transition("__new__", initial_status)

        request_id = str(uuid4())
        save_quote_request(
            {
                "request_id": request_id,
                "created_at": now_iso,
                "status": initial_status,
                "quote_id": quote_id,
                "customer_name": quote["request"].get("customer_name"),
                "customer_phone": quote["request"].get("customer_phone"),
                "job_address": quote["request"].get("job_address"),
                "job_description_customer": quote["request"].get("job_description_customer"),
                "job_description_internal": quote["response"].get("job_description_internal"),
                "service_type": quote["request"].get("service_type"),
                "cash_total_cad": quote["response"].get("cash_total_cad"),
                "emt_total_cad": quote["response"].get("emt_total_cad"),
                "request_json": quote["request"],
                "notes": None,
                "requested_job_date": None,
                "requested_time_window": None,
                "customer_accepted_at": None,
                "admin_approved_at": None,
                "accept_token": server_token,
                "booking_token": None,
                "booking_token_created_at": None,
            }
        )
        existing = get_quote_request_by_quote_id(quote_id)

    if existing is None:
        raise HTTPException(status_code=500, detail="Failed to load quote request")

    if normalized_action == "accept":
        booking_token = str(uuid4())
        update_kwargs: dict[str, Any] = {
            "status": "customer_accepted",
            "customer_accepted_at": now_iso,
            "admin_approved_at": None,
            "booking_token": booking_token,
            "booking_token_created_at": now_iso,
        }
        if notes_provided:
            update_kwargs["notes"] = notes

        updated = update_quote_request(existing["request_id"], **update_kwargs)
        if not updated:
            raise HTTPException(status_code=500, detail="Failed to update quote request")

        return {
            "ok": True,
            "request_id": updated["request_id"],
            "status": updated["status"],
            "booking_token": booking_token,
        }

    update_kwargs = {
        "status": "customer_declined",
        "customer_accepted_at": None,
        "admin_approved_at": None,
    }
    if notes_provided:
        update_kwargs["notes"] = notes

    updated = update_quote_request(existing["request_id"], **update_kwargs)
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update quote request")

    return {"ok": True, "request_id": updated["request_id"], "status": updated["status"]}


def submit_booking_details(
    quote_id: str,
    *,
    booking_token: str,
    requested_job_date: str,
    requested_time_window: str,
    notes: Optional[str],
) -> dict[str, Any]:
    existing = get_quote_request_by_quote_id(quote_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Quote request not found. Accept the quote first.")

    if existing["status"] != "customer_accepted":
        raise HTTPException(status_code=400, detail="Booking can only be submitted for accepted quotes.")

    if existing.get("booking_token") != booking_token:
        raise HTTPException(status_code=401, detail="Invalid or expired booking token.")

    if is_token_expired(existing.get("booking_token_created_at")):
        raise HTTPException(status_code=401, detail="Booking token has expired. Please accept the quote again.")

    updated = update_quote_request(
        existing["request_id"],
        requested_job_date=requested_job_date,
        requested_time_window=requested_time_window,
        notes=notes,
    )
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update booking")

    return {"ok": True, "request_id": updated["request_id"]}


def process_admin_decision(
    request_id: str,
    *,
    action: str,
    notes: Optional[str],
    notes_provided: bool,
    now_iso: str,
) -> dict[str, Any]:
    existing = get_quote_request(request_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Request not found")

    normalized_action = (action or "").lower()
    if normalized_action not in {"approve", "reject"}:
        raise HTTPException(status_code=400, detail="Invalid action (use approve|reject)")

    if normalized_action == "approve":
        update_kwargs: dict[str, Any] = {
            "status": "admin_approved",
            "admin_approved_at": now_iso,
        }
        if notes_provided:
            update_kwargs["notes"] = notes

        updated = update_quote_request(request_id, **update_kwargs)
        if not updated:
            raise HTTPException(status_code=500, detail="Failed to update request")

        created_job: Optional[dict[str, Any]] = None
        if not get_job_by_quote_id(updated["quote_id"]):
            job = {
                "job_id": str(uuid4()),
                "created_at": now_iso,
                "status": "in_progress",
                "quote_id": updated["quote_id"],
                "request_id": updated["request_id"],
                "customer_name": updated.get("customer_name"),
                "customer_phone": updated.get("customer_phone"),
                "job_address": updated.get("job_address"),
                "job_description_customer": updated.get("job_description_customer"),
                "job_description_internal": updated.get("job_description_internal"),
                "service_type": updated["service_type"],
                "cash_total_cad": float(updated["cash_total_cad"]),
                "emt_total_cad": float(updated["emt_total_cad"]),
                "request_json": updated["request_json"],
                "notes": updated.get("notes"),
            }
            save_job(job)
            created_job = job

        return {"ok": True, "request": updated, "job": created_job}

    reject_kwargs: dict[str, Any] = {"status": "rejected", "admin_approved_at": None}
    if notes_provided:
        reject_kwargs["notes"] = notes

    updated = update_quote_request(request_id, **reject_kwargs)
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update request")

    return {"ok": True, "request": updated}
