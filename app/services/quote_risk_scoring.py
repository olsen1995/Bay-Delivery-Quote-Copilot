from __future__ import annotations

from typing import Any

_ROUTE_REQUIRED_SERVICE_TYPES = {"small_move", "item_delivery"}
_ALLOWED_ACCESS_DIFFICULTIES = {"normal", "difficult", "extreme"}
_ALLOWED_TRAVEL_ZONES = {"in_town", "surrounding", "out_of_town"}
_RISK_FLAG_ORDER = (
    "low_input_signal",
    "missing_structured_scope",
    "dense_material_risk",
    "access_volume_risk",
    "mixed_bulky_load_risk",
    "likely_underestimated_volume",
)


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _has_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _ordered_flags(flags: set[str]) -> list[str]:
    return [flag for flag in _RISK_FLAG_ORDER if flag in flags]


def _normalized_enum(
    *candidates: Any,
    allowed: set[str],
    default: str,
) -> str:
    for candidate in candidates:
        value = str(candidate or "").strip().lower()
        if value in allowed:
            return value
    return default


def build_quote_risk_assessment(
    *,
    normalized_request: dict[str, Any],
    engine_quote: dict[str, Any],
) -> dict[str, Any]:
    request = normalized_request or {}
    quote = engine_quote or {}
    internal = quote.get("_internal") or {}

    service_type = str(request.get("service_type") or quote.get("service_type") or "").strip().lower()
    garbage_bag_count = max(_as_int(request.get("garbage_bag_count")), 0)
    estimated_hours = max(_as_float(request.get("estimated_hours")), 0.0)
    crew_size = max(_as_int(request.get("crew_size"), 1), 1)
    mattresses_count = max(_as_int(request.get("mattresses_count")), 0)
    box_springs_count = max(_as_int(request.get("box_springs_count")), 0)
    bulky_item_count = mattresses_count + box_springs_count
    trailer_fill_estimate = request.get("trailer_fill_estimate")
    trailer_class = request.get("trailer_class")
    bag_type = request.get("bag_type")
    has_dense_materials = bool(request.get("has_dense_materials") or internal.get("dense_materials"))
    access_difficulty = _normalized_enum(
        internal.get("access_difficulty"),
        request.get("access_difficulty"),
        allowed=_ALLOWED_ACCESS_DIFFICULTIES,
        default="normal",
    )
    travel_zone = _normalized_enum(
        internal.get("travel_zone"),
        request.get("travel_zone"),
        allowed=_ALLOWED_TRAVEL_ZONES,
        default="in_town",
    )
    route_complete = _has_text(request.get("pickup_address")) and _has_text(request.get("dropoff_address"))

    flags: set[str] = set()

    scope_signal_count = 0
    for is_present in (
        garbage_bag_count > 0,
        _has_text(bag_type),
        _has_text(trailer_fill_estimate),
        _has_text(trailer_class),
        bulky_item_count > 0,
        has_dense_materials,
        access_difficulty != "normal",
        travel_zone != "in_town",
        estimated_hours > 1.0,
        crew_size > 1,
    ):
        if is_present:
            scope_signal_count += 1

    has_haul_away_scope = any(
        (
            garbage_bag_count > 0,
            _has_text(bag_type),
            _has_text(trailer_fill_estimate),
            bulky_item_count > 0,
        )
    )
    if service_type == "haul_away" and not has_haul_away_scope:
        flags.add("missing_structured_scope")
    if service_type in _ROUTE_REQUIRED_SERVICE_TYPES and not route_complete:
        flags.add("missing_structured_scope")

    if scope_signal_count <= 1:
        flags.add("low_input_signal")
    if service_type == "haul_away" and garbage_bag_count == 0 and bulky_item_count == 0 and not _has_text(trailer_fill_estimate):
        flags.add("low_input_signal")

    if has_dense_materials:
        flags.add("dense_material_risk")

    trailer_fill_floor_cad = _as_float(internal.get("trailer_fill_floor_cad"))
    awkward_small_load_floor_cad = _as_float(internal.get("awkward_small_load_floor_cad"))
    small_load_protected = bool(internal.get("small_load_protected"))

    if access_difficulty in {"difficult", "extreme"} and any(
        (
            garbage_bag_count >= 4,
            bulky_item_count > 0,
            trailer_fill_floor_cad > 0.0,
            awkward_small_load_floor_cad > 0.0,
            small_load_protected,
        )
    ):
        flags.add("access_volume_risk")

    if service_type == "haul_away" and any(
        (
            bulky_item_count > 0 and (garbage_bag_count > 0 or estimated_hours > 1.0),
            1 <= garbage_bag_count <= 8 and crew_size >= 2 and estimated_hours >= 2.0 and not has_dense_materials,
        )
    ):
        flags.add("mixed_bulky_load_risk")

    if service_type == "haul_away" and any(
        (
            garbage_bag_count <= 3 and trailer_fill_floor_cad > 0.0,
            garbage_bag_count <= 5 and crew_size >= 2 and estimated_hours >= 2.0 and not has_dense_materials,
            garbage_bag_count <= 3 and small_load_protected and access_difficulty in {"difficult", "extreme"},
        )
    ):
        flags.add("likely_underestimated_volume")

    ordered_flags = _ordered_flags(flags)
    confidence = "high"
    if (
        "missing_structured_scope" in flags
        or {"low_input_signal", "likely_underestimated_volume"}.issubset(flags)
        or len(ordered_flags) >= 3
    ):
        confidence = "low"
    elif ordered_flags:
        confidence = "medium"

    return {
        "confidence_level": confidence,
        "risk_flags": ordered_flags,
    }
