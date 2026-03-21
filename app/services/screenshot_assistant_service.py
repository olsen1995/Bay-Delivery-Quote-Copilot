from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from uuid import uuid4

from fastapi import HTTPException

from app.services.quote_service import build_and_save_quote, build_quote_artifacts
from app.storage import (
    assign_analysis_attachments_to_quote,
    assign_attachments_to_analysis,
    get_screenshot_assistant_analysis,
    list_attachments,
    list_attachments_by_ids,
    list_screenshot_assistant_analyses,
    save_screenshot_assistant_analysis,
)

_TEXT_FIELDS = {
    "customer_name",
    "customer_phone",
    "job_address",
    "job_description_customer",
    "description",
    "service_type",
    "payment_method",
    "pickup_address",
    "dropoff_address",
    "bag_type",
    "trailer_fill_estimate",
    "trailer_class",
    "scrap_pickup_location",
    "travel_zone",
    "access_difficulty",
}
_INT_FIELDS = {"crew_size", "garbage_bag_count", "mattresses_count", "box_springs_count"}
_FLOAT_FIELDS = {"estimated_hours"}
_BOOL_FIELDS = {"has_dense_materials"}
_ALLOWED_CANDIDATE_FIELDS = _TEXT_FIELDS | _INT_FIELDS | _FLOAT_FIELDS | _BOOL_FIELDS
_DEFAULT_CANDIDATE = {
    "customer_name": "",
    "customer_phone": "",
    "job_address": "",
    "description": "",
    "service_type": "haul_away",
    "payment_method": None,
    "pickup_address": None,
    "dropoff_address": None,
    "estimated_hours": 1.0,
    "crew_size": 1,
    "garbage_bag_count": 0,
    "bag_type": None,
    "trailer_fill_estimate": None,
    "trailer_class": None,
    "mattresses_count": 0,
    "box_springs_count": 0,
    "scrap_pickup_location": "curbside",
    "travel_zone": "in_town",
    "access_difficulty": "normal",
    "has_dense_materials": False,
}
_AUTOFILL_FIELDS = (
    "customer_name",
    "customer_phone",
    "job_address",
    "description",
    "requested_job_date",
    "requested_time_window",
)
_TIME_WINDOWS = {"morning", "afternoon", "evening", "flexible"}
_PHONE_PATTERN = re.compile(
    r"(?:(?:\+?1[\s.-]*)?(?:\(?\d{3}\)?[\s.-]*)\d{3}[\s.-]*\d{4})"
)
_ADDRESS_PATTERN = re.compile(
    r"\b\d{1,6}\s+[A-Za-z0-9#.,'\- ]{2,80}\b(?:street|st|avenue|ave|road|rd|drive|dr|lane|ln|court|ct|boulevard|blvd|way|place|pl|terrace|ter)\b\.?",
    re.IGNORECASE,
)
_NAME_PATTERNS = (
    re.compile(r"\b(?:my name is|name is)\s+([A-Za-z][A-Za-z' -]{1,60})", re.IGNORECASE),
    re.compile(r"\b(?:i am|i'm|this is)\s+([A-Za-z][A-Za-z' -]{1,60})", re.IGNORECASE),
)
_MONTH_FORMATS = ("%B %d %Y", "%b %d %Y", "%B %d, %Y", "%b %d, %Y")
_OCR_ATTACHMENT_TEXT_MAX_CHARS = 1200
_COMBINED_OCR_TEXT_MAX_CHARS = 4000


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    return str(value).strip()


def _normalize_candidate_map(raw: dict[str, Any] | None) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    if not isinstance(raw, dict):
        return normalized

    for key in _ALLOWED_CANDIDATE_FIELDS:
        if key not in raw:
            continue
        value = raw.get(key)
        if key in _TEXT_FIELDS:
            cleaned = _clean_text(value)
            normalized[key] = cleaned if cleaned not in {"", None} else None
        elif key in _INT_FIELDS:
            normalized[key] = int(value)
        elif key in _FLOAT_FIELDS:
            normalized[key] = float(value)
        elif key in _BOOL_FIELDS:
            normalized[key] = bool(value)
    return normalized


def _normalize_attachment_ids(raw_ids: list[Any] | None) -> list[str]:
    if not raw_ids:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for raw in raw_ids:
        value = str(raw).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _clean_message_text(value: str | None) -> str:
    if not value:
        return ""
    cleaned = re.sub(r"\s+", " ", value).strip()
    return cleaned


def _trim_suggestion_value(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" \t\r\n,.;:-")


def _normalize_phone(value: str | None) -> str | None:
    if not value:
        return None
    digits = re.sub(r"\D", "", value)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        return _trim_suggestion_value(value) or None
    return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"


def _extract_customer_name(message_text: str) -> str | None:
    for pattern in _NAME_PATTERNS:
        match = pattern.search(message_text)
        if not match:
            continue
        candidate = match.group(1).splitlines()[0]
        candidate = re.split(r"[\-–|,/]|(?:\b(?:and|for|about|at)\b)", candidate, maxsplit=1)[0]
        candidate = _trim_suggestion_value(candidate)
        if candidate:
            return candidate.title()
    return None


def _extract_customer_phone(message_text: str) -> str | None:
    match = _PHONE_PATTERN.search(message_text)
    if not match:
        return None
    return _normalize_phone(match.group(0))


def _extract_job_address(message_text: str) -> str | None:
    address_match = _ADDRESS_PATTERN.search(message_text)
    if address_match:
        return _trim_suggestion_value(address_match.group(0))

    for prefix in ("address is", "located at", "job address is"):
        match = re.search(rf"{prefix}\s+([^.\n]+)", message_text, re.IGNORECASE)
        if match:
            candidate = _trim_suggestion_value(match.group(1))
            if candidate:
                return candidate
    return None


def _extract_requested_job_date(message_text: str) -> str | None:
    iso_match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", message_text)
    if iso_match:
        return iso_match.group(1)

    month_match = re.search(
        r"\b((?:jan|january|feb|february|mar|march|apr|april|may|jun|june|jul|july|aug|august|sep|sept|september|oct|october|nov|november|dec|december)\s+\d{1,2},?\s+\d{4})\b",
        message_text,
        re.IGNORECASE,
    )
    if not month_match:
        return None

    raw_value = month_match.group(1)
    for fmt in _MONTH_FORMATS:
        try:
            return datetime.strptime(raw_value, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _extract_requested_time_window(message_text: str) -> str | None:
    lowered = message_text.lower()
    if "flexible" in lowered or "any time" in lowered or "anytime" in lowered:
        return "flexible"
    if "morning" in lowered:
        return "morning"
    if "afternoon" in lowered:
        return "afternoon"
    if "evening" in lowered or "tonight" in lowered:
        return "evening"
    return None


def _build_autofill_suggestions(
    *,
    message: str | None,
    attachment_ocr_entries: list[dict[str, Any]] | None,
    candidate_inputs: dict[str, Any],
    operator_overrides: dict[str, Any],
    requested_job_date: str | None,
    requested_time_window: str | None,
) -> tuple[dict[str, dict[str, Any]], list[str], list[str]]:
    message_text = _clean_message_text(message)
    ocr_entries = attachment_ocr_entries or []
    warnings: list[str] = []
    suggestions: dict[str, dict[str, Any]] = {}

    successful_ocr_texts: list[str] = []
    successful_ocr_count = 0
    unsuccessful_ocr_count = 0
    ocr_warning_count = 0

    for entry in ocr_entries:
        status = _clean_text(entry.get("status")) or ""
        warning = _clean_text(entry.get("warning"))
        text = _clean_message_text(_clean_text(entry.get("text")))
        if warning:
            ocr_warning_count += 1
        if status == "success" and text:
            successful_ocr_count += 1
            successful_ocr_texts.append(text[:_OCR_ATTACHMENT_TEXT_MAX_CHARS])
        else:
            unsuccessful_ocr_count += 1

    combined_ocr_text = " ".join(successful_ocr_texts)[:_COMBINED_OCR_TEXT_MAX_CHARS].strip()

    if not message_text and not combined_ocr_text:
        base_warning = "Paste a customer message to generate autofill suggestions."
        if ocr_entries:
            base_warning = "No readable message or screenshot OCR text was available to generate autofill suggestions."
        return suggestions, list(_AUTOFILL_FIELDS), [base_warning]

    message_extracted = {
        "customer_name": _extract_customer_name(message_text) if message_text else None,
        "customer_phone": _extract_customer_phone(message_text) if message_text else None,
        "job_address": _extract_job_address(message_text) if message_text else None,
        "requested_job_date": _extract_requested_job_date(message_text) if message_text else None,
        "requested_time_window": _extract_requested_time_window(message_text) if message_text else None,
    }
    ocr_extracted = {
        "customer_name": _extract_customer_name(combined_ocr_text) if combined_ocr_text else None,
        "customer_phone": _extract_customer_phone(combined_ocr_text) if combined_ocr_text else None,
        "job_address": _extract_job_address(combined_ocr_text) if combined_ocr_text else None,
        "requested_job_date": _extract_requested_job_date(combined_ocr_text) if combined_ocr_text else None,
        "requested_time_window": _extract_requested_time_window(combined_ocr_text) if combined_ocr_text else None,
    }

    extracted_values = {
        "customer_name": message_extracted["customer_name"] or ocr_extracted["customer_name"],
        "customer_phone": message_extracted["customer_phone"] or ocr_extracted["customer_phone"],
        "job_address": message_extracted["job_address"] or ocr_extracted["job_address"],
        "description": message_text or combined_ocr_text,
        "requested_job_date": message_extracted["requested_job_date"] or ocr_extracted["requested_job_date"],
        "requested_time_window": message_extracted["requested_time_window"] or ocr_extracted["requested_time_window"],
    }
    confidence_map = {
        "customer_name": "medium",
        "customer_phone": "high",
        "job_address": "medium",
        "description": "low",
        "requested_job_date": "medium",
        "requested_time_window": "medium",
    }
    source_map = {
        "customer_name": "message",
        "customer_phone": "message",
        "job_address": "message",
        "description": "message" if message_text else "ocr",
        "requested_job_date": "message",
        "requested_time_window": "message",
    }

    for field_name in ("customer_name", "customer_phone", "job_address", "requested_job_date", "requested_time_window"):
        from_message = _clean_text(message_extracted[field_name])
        from_ocr = _clean_text(ocr_extracted[field_name])
        if from_message and from_ocr and _trim_suggestion_value(from_message).lower() == _trim_suggestion_value(from_ocr).lower():
            source_map[field_name] = "message+ocr"
        elif from_message:
            source_map[field_name] = "message"
        elif from_ocr:
            source_map[field_name] = "ocr"

    for field_name, value in extracted_values.items():
        cleaned_value = _clean_text(value)
        if not cleaned_value:
            continue
        suggestions[field_name] = {
            "value": cleaned_value,
            "confidence": confidence_map[field_name],
            "source": source_map[field_name],
            "needs_review": True,
        }

    reviewed_values = {
        "customer_name": _clean_text(operator_overrides.get("customer_name")) or _clean_text(candidate_inputs.get("customer_name")),
        "customer_phone": _clean_text(operator_overrides.get("customer_phone")) or _clean_text(candidate_inputs.get("customer_phone")),
        "job_address": _clean_text(operator_overrides.get("job_address")) or _clean_text(candidate_inputs.get("job_address")),
        "description": _clean_text(operator_overrides.get("description")) or _clean_text(candidate_inputs.get("description")),
        "requested_job_date": _clean_text(requested_job_date),
        "requested_time_window": _clean_text(requested_time_window),
    }
    missing_fields = [
        field_name
        for field_name in _AUTOFILL_FIELDS
        if not reviewed_values.get(field_name) and field_name not in suggestions
    ]

    if "description" in suggestions and len(suggestions["description"]["value"]) > 240:
        if message_text:
            warnings.append("Description suggestion mirrors the pasted message. Trim it before creating a quote draft.")
        else:
            warnings.append("Description suggestion mirrors screenshot OCR text. Trim it before creating a quote draft.")
    if successful_ocr_count:
        warnings.append(f"OCR text was extracted from {successful_ocr_count} screenshot(s) and added to autofill review.")
    if unsuccessful_ocr_count:
        warnings.append(f"OCR was unavailable or empty for {unsuccessful_ocr_count} screenshot(s).")
    if ocr_warning_count and not unsuccessful_ocr_count:
        warnings.append("One or more screenshot OCR warnings were recorded for admin review.")
    if not suggestions:
        warnings.append("No autofill suggestions were detected from the available message or screenshot OCR text.")

    return suggestions, missing_fields, warnings


def _collect_attachment_ocr_entries(attachment_ids: list[str]) -> list[dict[str, Any]]:
    if not attachment_ids:
        return []

    entries: list[dict[str, Any]] = []
    for attachment in list_attachments_by_ids(attachment_ids):
        ocr_payload = attachment.get("ocr_json") or {}
        if not isinstance(ocr_payload, dict):
            continue
        entries.append(
            {
                "attachment_id": attachment.get("attachment_id"),
                "status": _clean_text(ocr_payload.get("status")) or "skipped",
                "text": _clean_text(ocr_payload.get("text")) or "",
                "warning": _clean_text(ocr_payload.get("warning")),
            }
        )
    return entries


def _build_normalized_candidate(message: str | None, candidate_inputs: dict[str, Any], operator_overrides: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(_DEFAULT_CANDIDATE)
    normalized.update(candidate_inputs)
    normalized.update(operator_overrides)

    message_text = _clean_text(message) or ""
    if not normalized.get("description"):
        normalized["description"] = message_text
    if not normalized.get("job_description_customer"):
        normalized["job_description_customer"] = normalized.get("description") or message_text
    if not normalized.get("service_type"):
        normalized["service_type"] = _DEFAULT_CANDIDATE["service_type"]

    for key in list(normalized.keys()):
        if key in _TEXT_FIELDS:
            value = _clean_text(normalized.get(key))
            if key in {"customer_name", "customer_phone", "job_address", "description", "service_type", "job_description_customer"}:
                normalized[key] = value or ""
            else:
                normalized[key] = value or None

    return normalized


def _trim_intake_payload(intake: dict[str, Any], *, include_autofill: bool) -> dict[str, Any]:
    trimmed = {
        "message": intake.get("message") or "",
        "requested_job_date": intake.get("requested_job_date"),
        "requested_time_window": intake.get("requested_time_window"),
        "screenshot_attachment_ids": intake.get("screenshot_attachment_ids") or [],
        "candidate_inputs": intake.get("candidate_inputs") or {},
        "operator_overrides": intake.get("operator_overrides") or {},
    }
    if include_autofill:
        trimmed["autofill_suggestions"] = intake.get("autofill_suggestions") or {}
        trimmed["autofill_missing_fields"] = intake.get("autofill_missing_fields") or []
        trimmed["autofill_warnings"] = intake.get("autofill_warnings") or []
    return trimmed


def _round_up_to_nearest_5(value: float) -> float:
    if value <= 0:
        return 0.0
    rounded = int((float(value) + 4.9999) // 5) * 5
    return float(max(rounded, 0))


def _has_meaningful_reviewed_description(value: Any) -> bool:
    text = _clean_text(value) or ""
    if len(text) < 20:
        return False
    return len([part for part in re.split(r"\s+", text) if part]) >= 4


def _service_type_requires_route_details(service_type: str | None) -> bool:
    normalized = (service_type or "").strip().lower()
    return normalized in {"small_move", "item_delivery"}


def _build_quote_range_guidance(
    *,
    normalized_candidate: dict[str, Any],
    intake: dict[str, Any],
    quote_artifacts: dict[str, Any],
) -> dict[str, Any]:
    response = quote_artifacts.get("response") or {}
    engine_quote = quote_artifacts.get("engine_quote") or {}
    internal = engine_quote.get("_internal") or {}

    target = float(response.get("cash_total_cad", 0.0) or 0.0)
    service_type = _clean_text((quote_artifacts.get("normalized_request") or {}).get("service_type")) or ""
    candidate_inputs = intake.get("candidate_inputs") or {}
    operator_overrides = intake.get("operator_overrides") or {}
    autofill_warnings = intake.get("autofill_warnings") or []
    attachment_ids = intake.get("screenshot_attachment_ids") or []

    unknowns: list[str] = []
    risk_notes: list[str] = []
    floor_drivers: list[str] = []
    width_drivers: list[str] = []

    service_type_reviewed = bool(_clean_text(candidate_inputs.get("service_type")) or _clean_text(operator_overrides.get("service_type")))
    reviewed_description = _has_meaningful_reviewed_description(normalized_candidate.get("job_description_customer"))
    reviewed_job_address = bool(_clean_text(normalized_candidate.get("job_address")))
    route_required = _service_type_requires_route_details(service_type)
    route_complete = bool(_clean_text(normalized_candidate.get("pickup_address")) and _clean_text(normalized_candidate.get("dropoff_address")))
    access_explicit = "access_difficulty" in candidate_inputs or "access_difficulty" in operator_overrides
    load_size_reviewed = any(
        normalized_candidate.get(field) not in {None, "", 0}
        for field in ("garbage_bag_count", "bag_type", "trailer_fill_estimate", "trailer_class")
    )
    ocr_ambiguity = any(
        isinstance(warning, str)
        and any(token in warning.lower() for token in ("ocr", "no autofill", "paste a customer message"))
        for warning in autofill_warnings
    )

    if not service_type_reviewed:
        unknowns.append("Service type is still using the default assistant assumption.")
        width_drivers.append("default_service_type")
    if not reviewed_description:
        unknowns.append("Reviewed description is still minimal.")
        width_drivers.append("limited_reviewed_description")
    if not reviewed_job_address and not route_complete:
        unknowns.append("Job or route address details are not fully reviewed.")
        width_drivers.append("missing_reviewed_address")
    if route_required and not route_complete:
        unknowns.append("Pickup and dropoff details are not fully reviewed.")
        width_drivers.append("incomplete_route_details")
    if not access_explicit:
        unknowns.append("Access difficulty is still at the default assumption.")
        width_drivers.append("default_access_assumption")
    if service_type == "haul_away" and not load_size_reviewed:
        unknowns.append("Load size is not fully confirmed.")
        width_drivers.append("unconfirmed_load_size")
    if attachment_ids and ocr_ambiguity:
        unknowns.append("OCR or message review still has ambiguity.")
        width_drivers.append("ocr_message_ambiguity")

    confidence = "high"
    if route_required and not route_complete:
        confidence = "low"
    elif len(width_drivers) >= 4:
        confidence = "low"
    elif len(width_drivers) >= 2:
        confidence = "medium"

    floor_candidates: list[tuple[str, float]] = [
        ("service_minimum", float(internal.get("min_total_cad", 0.0) or 0.0)),
        ("travel_minimum", float(internal.get("travel_min_cad", 0.0) or 0.0)),
        ("travel_total", float(internal.get("travel_total_cad", 0.0) or 0.0)),
        ("item_delivery_protected_floor", float(internal.get("item_delivery_protected_base_floor_cad", 0.0) or 0.0)),
        ("bag_type_floor", float(internal.get("bag_type_floor_cad", 0.0) or 0.0)),
        ("trailer_fill_floor", float(internal.get("trailer_fill_floor_cad", 0.0) or 0.0)),
        ("awkward_small_load_floor", float(internal.get("awkward_small_load_floor_cad", 0.0) or 0.0)),
        ("protected_subtotal", float(internal.get("pre_access_subtotal_cad", 0.0) or 0.0)),
        ("cash_before_round", float(internal.get("cash_before_round_cad", 0.0) or 0.0)),
    ]
    active_floor_values = []
    for label, value in floor_candidates:
        if value > 0:
            active_floor_values.append(value)
        if value > 0 and label not in {"travel_total", "protected_subtotal", "cash_before_round"}:
            floor_drivers.append(label)

    highest_floor = _round_up_to_nearest_5(max(active_floor_values, default=0.0))
    downward_room = 0.0
    if confidence == "high":
        downward_room = 10.0
    elif confidence == "medium":
        downward_room = 5.0

    if confidence == "low":
        minimum_safe = target
    else:
        minimum_safe = max(highest_floor, target - downward_room)
        minimum_safe = min(minimum_safe, target)

    upward_room = 10.0
    if confidence == "medium":
        upward_room = 15.0
    elif confidence == "low":
        upward_room = 20.0

    if "default_access_assumption" in width_drivers:
        upward_room += 10.0
    if "unconfirmed_load_size" in width_drivers:
        upward_room += 10.0
    if "ocr_message_ambiguity" in width_drivers:
        upward_room += 5.0
    if bool(normalized_candidate.get("has_dense_materials")):
        upward_room += 10.0
        width_drivers.append("dense_material_risk")
    if float(internal.get("trailer_fill_floor_cad", 0.0) or 0.0) > 0:
        upward_room += 5.0
        width_drivers.append("trailer_floor_active")

    upward_room = min(upward_room, 45.0)
    upper_reasonable = target + upward_room

    if "default_access_assumption" in width_drivers:
        risk_notes.append("Avoid quoting the bottom of the band until access is confirmed.")
    if "unconfirmed_load_size" in width_drivers:
        risk_notes.append("Load size is not fully reviewed; trailer-floor pricing may still apply.")
    if bool(normalized_candidate.get("has_dense_materials")):
        risk_notes.append("Dense or heavy material risk may push this job toward the upper end.")
    if float(internal.get("crew_escalated") or 0):
        risk_notes.append("Crew sizing is already margin-protected; avoid quoting below the reviewed target.")
    if not risk_notes and confidence != "high":
        risk_notes.append("Use the recommended target unless the reviewed scope is clearly tighter than the current intake.")

    return {
        "range": {
            "minimum_safe_cash_cad": float(round(minimum_safe, 2)),
            "recommended_target_cash_cad": float(round(target, 2)),
            "upper_reasonable_cash_cad": float(round(upper_reasonable, 2)),
        },
        "confidence": confidence,
        "unknowns": unknowns,
        "risk_notes": risk_notes,
        "range_basis": {
            "anchor": "existing_quote_engine_cash_total",
            "floor_drivers": floor_drivers,
            "width_drivers": width_drivers,
        },
    }


def _format_analysis(record: dict[str, Any], *, include_autofill: bool = True) -> dict[str, Any]:
    analysis_id = record["analysis_id"]
    attachments = list_attachments(analysis_id=analysis_id, limit=25)
    intake = record.get("intake_json") or {}
    guidance = record.get("guidance_json") or {}
    payload = {
        "analysis_id": analysis_id,
        "created_at": record["created_at"],
        "updated_at": record["updated_at"],
        "operator_username": record["operator_username"],
        "status": record["status"],
        "quote_id": record.get("quote_id"),
        "intake": _trim_intake_payload(intake, include_autofill=include_autofill),
        "normalized_candidate": record.get("normalized_candidate_json") or {},
        "quote_guidance": guidance,
        "attachments": attachments,
        "recommendation_only": bool(guidance.get("recommendation_only", True)),
    }
    if include_autofill:
        payload["autofill_suggestions"] = intake.get("autofill_suggestions") or {}
        payload["autofill_missing_fields"] = intake.get("autofill_missing_fields") or []
        payload["autofill_warnings"] = intake.get("autofill_warnings") or []
    return payload



def create_analysis(
    *,
    analysis_id: str | None,
    operator_username: str,
    message: str | None,
    requested_job_date: str | None,
    requested_time_window: str | None,
    candidate_inputs: dict[str, Any] | None,
    operator_overrides: dict[str, Any] | None,
    screenshot_attachment_ids: list[Any] | None,
    now_iso: str,
) -> dict[str, Any]:
    existing = get_screenshot_assistant_analysis(analysis_id) if analysis_id else None
    if analysis_id and not existing:
        raise HTTPException(status_code=404, detail="Screenshot assistant analysis not found.")
    if existing and str(existing.get("quote_id") or "").strip():
        raise HTTPException(status_code=409, detail="Screenshot assistant analysis is locked after quote draft creation.")

    normalized_candidates = _normalize_candidate_map(candidate_inputs)
    normalized_overrides = _normalize_candidate_map(operator_overrides)
    attachment_ids = _normalize_attachment_ids(screenshot_attachment_ids)
    existing_intake = (existing.get("intake_json") or {}) if existing else {}
    if existing and not attachment_ids:
        attachment_ids = [item["attachment_id"] for item in list_attachments(analysis_id=analysis_id, limit=25)]
    if existing and requested_job_date is None:
        requested_job_date = _clean_text(existing_intake.get("requested_job_date"))
    if existing and requested_time_window is None:
        requested_time_window = _clean_text(existing_intake.get("requested_time_window"))

    autofill_suggestions, autofill_missing_fields, autofill_warnings = _build_autofill_suggestions(
        message=message,
        attachment_ocr_entries=_collect_attachment_ocr_entries(attachment_ids),
        candidate_inputs=normalized_candidates,
        operator_overrides=normalized_overrides,
        requested_job_date=requested_job_date,
        requested_time_window=requested_time_window,
    )
    normalized_candidate = _build_normalized_candidate(
        _clean_text(message),
        normalized_candidates,
        normalized_overrides,
    )
    quote_artifacts = build_quote_artifacts(normalized_candidate)
    range_guidance = _build_quote_range_guidance(
        normalized_candidate=quote_artifacts["normalized_request"],
        intake={
            "candidate_inputs": normalized_candidates,
            "operator_overrides": normalized_overrides,
            "autofill_warnings": autofill_warnings,
            "screenshot_attachment_ids": attachment_ids,
        },
        quote_artifacts=quote_artifacts,
    )

    analysis_id = analysis_id or str(uuid4())
    guidance = {
        **quote_artifacts["response"],
        "service_type": quote_artifacts["normalized_request"]["service_type"],
        **range_guidance,
        "recommendation_only": True,
        "source": "existing_quote_pricing_logic",
    }
    intake = {
        "message": _clean_text(message) or "",
        "requested_job_date": _clean_text(requested_job_date),
        "requested_time_window": _clean_text(requested_time_window),
        "screenshot_attachment_ids": attachment_ids,
        "candidate_inputs": normalized_candidates,
        "operator_overrides": normalized_overrides,
        "autofill_suggestions": autofill_suggestions,
        "autofill_missing_fields": autofill_missing_fields,
        "autofill_warnings": autofill_warnings,
    }

    save_screenshot_assistant_analysis(
        {
            "analysis_id": analysis_id,
            "created_at": existing["created_at"] if existing else now_iso,
            "updated_at": now_iso,
            "operator_username": operator_username,
            "status": "draft",
            "intake_json": intake,
            "normalized_candidate_json": quote_artifacts["normalized_request"],
            "guidance_json": guidance,
            "quote_id": existing.get("quote_id") if existing else None,
        }
    )
    assign_attachments_to_analysis(attachment_ids, analysis_id)

    saved = get_screenshot_assistant_analysis(analysis_id)
    if not saved:
        raise RuntimeError("Failed to load saved screenshot assistant analysis")
    return _format_analysis(saved, include_autofill=True)



def list_analyses(limit: int = 50) -> list[dict[str, Any]]:
    return [_format_analysis(record, include_autofill=False) for record in list_screenshot_assistant_analyses(limit=limit)]



def get_analysis(analysis_id: str) -> dict[str, Any] | None:
    record = get_screenshot_assistant_analysis(analysis_id)
    if not record:
        return None
    return _format_analysis(record, include_autofill=True)


def create_quote_draft_from_analysis(*, analysis_id: str, now_iso: str) -> dict[str, Any]:
    existing = get_screenshot_assistant_analysis(analysis_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Screenshot assistant analysis not found.")

    existing_quote_id = str(existing.get("quote_id") or "").strip()
    if existing_quote_id:
        raise HTTPException(status_code=409, detail="Quote draft already exists for this analysis.")

    normalized_candidate = existing.get("normalized_candidate_json") or {}
    if not isinstance(normalized_candidate, dict):
        raise HTTPException(status_code=409, detail="Analysis is missing a normalized candidate.")

    created_quote = build_and_save_quote(normalized_candidate, now_iso=now_iso)
    quote_id = created_quote["quote_id"]

    save_screenshot_assistant_analysis(
        {
            "analysis_id": existing["analysis_id"],
            "created_at": existing["created_at"],
            "updated_at": now_iso,
            "operator_username": existing["operator_username"],
            "status": existing["status"],
            "intake_json": existing.get("intake_json") or {},
            "normalized_candidate_json": normalized_candidate,
            "guidance_json": existing.get("guidance_json") or {},
            "quote_id": quote_id,
        }
    )
    assign_analysis_attachments_to_quote(analysis_id, quote_id)

    updated = get_screenshot_assistant_analysis(analysis_id)
    if not updated:
        raise RuntimeError("Failed to load updated screenshot assistant analysis")

    return {
        "ok": True,
        "analysis": _format_analysis(updated),
        "quote": {
            "quote_id": created_quote["quote_id"],
            "created_at": created_quote["created_at"],
            "request": created_quote["request"],
            "response": created_quote["response"],
        },
    }
