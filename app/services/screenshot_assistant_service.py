from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import HTTPException

from app.services.quote_service import build_and_save_quote, build_quote_artifacts
from app.storage import (
    assign_analysis_attachments_to_quote,
    assign_attachments_to_analysis,
    get_screenshot_assistant_analysis,
    list_attachments,
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


def _format_analysis(record: dict[str, Any]) -> dict[str, Any]:
    analysis_id = record["analysis_id"]
    attachments = list_attachments(analysis_id=analysis_id, limit=25)
    intake = record.get("intake_json") or {}
    guidance = record.get("guidance_json") or {}
    return {
        "analysis_id": analysis_id,
        "created_at": record["created_at"],
        "updated_at": record["updated_at"],
        "operator_username": record["operator_username"],
        "status": record["status"],
        "quote_id": record.get("quote_id"),
        "intake": intake,
        "normalized_candidate": record.get("normalized_candidate_json") or {},
        "quote_guidance": guidance,
        "attachments": attachments,
        "recommendation_only": bool(guidance.get("recommendation_only", True)),
    }



def create_analysis(
    *,
    analysis_id: str | None,
    operator_username: str,
    message: str | None,
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
    if existing and not attachment_ids:
        attachment_ids = [item["attachment_id"] for item in list_attachments(analysis_id=analysis_id, limit=25)]
    normalized_candidate = _build_normalized_candidate(
        _clean_text(message),
        normalized_candidates,
        normalized_overrides,
    )
    quote_artifacts = build_quote_artifacts(normalized_candidate)

    analysis_id = analysis_id or str(uuid4())
    guidance = {
        **quote_artifacts["response"],
        "service_type": quote_artifacts["normalized_request"]["service_type"],
        "recommendation_only": True,
        "source": "existing_quote_pricing_logic",
    }
    intake = {
        "message": _clean_text(message) or "",
        "screenshot_attachment_ids": attachment_ids,
        "candidate_inputs": normalized_candidates,
        "operator_overrides": normalized_overrides,
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
    return _format_analysis(saved)



def list_analyses(limit: int = 50) -> list[dict[str, Any]]:
    return [_format_analysis(record) for record in list_screenshot_assistant_analyses(limit=limit)]



def get_analysis(analysis_id: str) -> dict[str, Any] | None:
    record = get_screenshot_assistant_analysis(analysis_id)
    if not record:
        return None
    return _format_analysis(record)


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
