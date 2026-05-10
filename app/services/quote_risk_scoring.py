from __future__ import annotations

from typing import Any

_ROUTE_REQUIRED_SERVICE_TYPES = {"small_move", "item_delivery"}
_ALLOWED_ACCESS_DIFFICULTIES = {"normal", "difficult", "extreme"}
_ALLOWED_TRAVEL_ZONES = {"in_town", "surrounding", "out_of_town"}
_ALLOWED_HAUL_AWAY_BAG_TYPES = {"light", "heavy_mixed", "construction_debris"}
_ALLOWED_HAUL_AWAY_TRAILER_FILL_ESTIMATES = {
    "under_quarter",
    "quarter",
    "half",
    "three_quarter",
    "full",
}
_RISK_FLAG_ORDER = (
    "low_input_signal",
    "missing_structured_scope",
    "dense_material_risk",
    "access_volume_risk",
    "mixed_bulky_load_risk",
    "likely_underestimated_volume",
)
_ADVISORY_FLAG_ORDER = (
    "DENSE_MATERIAL_RISK",
    "MIXED_LOAD_SORTING_RISK",
    "REFRIGERANT_APPLIANCE_RISK",
    "ACCESS_LABOUR_RISK",
    "DEMOLITION_SCOPE_RISK",
    "WEATHER_PROTECTION_RISK",
)
_ADVISORY_SEVERITY_ORDER = {"low": 1, "medium": 2, "high": 3}
_HIGH_DENSE_MATERIAL_TYPES = {"concrete", "brick", "stone", "soil"}
_MEDIUM_DENSE_MATERIAL_TYPES = {"tile", "shingles", "mixed"}
_HIGH_CONSTRUCTION_DEBRIS_TYPES = {"concrete"}
_MEDIUM_CONSTRUCTION_DEBRIS_TYPES = {"tile", "shingles", "mixed"}
_REFRIGERANT_APPLIANCE_TYPES = {"fridge", "freezer", "air_conditioner", "dehumidifier"}
_MOVE_DELIVERY_SERVICE_TYPES = {"small_move", "item_delivery", "moving", "delivery"}


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


def _normalized_allowed_value(value: Any, allowed: set[str]) -> str | None:
    candidate = str(value or "").strip().lower()
    if candidate in allowed:
        return candidate
    return None


def _normalized_text(value: Any) -> str:
    return str(value or "").strip().lower()


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)


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
    valid_bag_type = _normalized_allowed_value(bag_type, _ALLOWED_HAUL_AWAY_BAG_TYPES)
    valid_trailer_fill_estimate = _normalized_allowed_value(
        trailer_fill_estimate,
        _ALLOWED_HAUL_AWAY_TRAILER_FILL_ESTIMATES,
    )
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
        valid_bag_type is not None,
        valid_trailer_fill_estimate is not None,
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
            valid_bag_type is not None,
            valid_trailer_fill_estimate is not None,
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


def build_quote_risk_advisory(normalized_request: dict[str, Any]) -> dict[str, Any] | None:
    request = normalized_request or {}
    flags: dict[str, dict[str, str]] = {}
    suggested_actions: list[str] = []
    manual_review_recommended = False

    def add_action(action: str) -> None:
        if action not in suggested_actions:
            suggested_actions.append(action)

    def add_flag(
        *,
        code: str,
        severity: str,
        label: str,
        operator_note: str,
        manual_review: bool = False,
        actions: tuple[str, ...] = (),
    ) -> None:
        nonlocal manual_review_recommended
        existing = flags.get(code)
        if existing is None or _ADVISORY_SEVERITY_ORDER[severity] > _ADVISORY_SEVERITY_ORDER[existing["severity"]]:
            flags[code] = {
                "code": code,
                "severity": severity,
                "label": label,
                "operator_note": operator_note,
            }
        if manual_review:
            manual_review_recommended = True
        for action in actions:
            add_action(action)

    dense_material_type = _normalized_text(request.get("dense_material_type"))
    construction_debris_type = _normalized_text(request.get("construction_debris_type"))
    dense_severity: str | None = None
    if dense_material_type in _HIGH_DENSE_MATERIAL_TYPES or construction_debris_type in _HIGH_CONSTRUCTION_DEBRIS_TYPES:
        dense_severity = "high"
    elif dense_material_type in _MEDIUM_DENSE_MATERIAL_TYPES or construction_debris_type in _MEDIUM_CONSTRUCTION_DEBRIS_TYPES:
        dense_severity = "medium"
    if dense_severity:
        add_flag(
            code="DENSE_MATERIAL_RISK",
            severity=dense_severity,
            label="Dense material risk",
            operator_note="Dense disposal material may require owner review before approval.",
            manual_review=dense_severity == "high",
            actions=(
                "Ask for photos before approving.",
                "Confirm material type and amount.",
            ),
        )

    mixed_load = _as_bool(request.get("mixed_load"))
    contains_scrap = _as_bool(request.get("contains_scrap"))
    contains_garbage = _as_bool(request.get("contains_garbage"))
    if mixed_load or (contains_scrap and contains_garbage):
        add_flag(
            code="MIXED_LOAD_SORTING_RISK",
            severity="medium",
            label="Mixed load sorting risk",
            operator_note="Mixed scrap and garbage may need sorting or disposal review before approval.",
            manual_review=mixed_load and contains_scrap and contains_garbage,
            actions=("Confirm what is scrap versus garbage before approving.",),
        )

    appliance_type = _normalized_text(request.get("appliance_type"))
    if _as_bool(request.get("has_refrigerant_appliance")) or appliance_type in _REFRIGERANT_APPLIANCE_TYPES:
        add_flag(
            code="REFRIGERANT_APPLIANCE_RISK",
            severity="medium",
            label="Refrigerant appliance risk",
            operator_note="Refrigerant appliances may require special handling or disposal confirmation.",
            manual_review=True,
            actions=("Confirm appliance type and refrigerant handling before approval.",),
        )

    stairs_count = max(_as_int(request.get("stairs_count")), 0)
    floor_count = max(_as_int(request.get("floor_count")), 0)
    basement_or_inside_removal = _as_bool(request.get("basement_or_inside_removal"))
    if stairs_count >= 2 or floor_count >= 2 or basement_or_inside_removal:
        add_flag(
            code="ACCESS_LABOUR_RISK",
            severity="medium",
            label="Access labour risk",
            operator_note="Stairs, floor count, or inside removal can add labour risk before approval.",
            manual_review=stairs_count >= 3 or (basement_or_inside_removal and stairs_count >= 1),
            actions=("Confirm stairs, floor count, and inside/basement access before approving.",),
        )

    if _as_bool(request.get("demolition_ripout")):
        add_flag(
            code="DEMOLITION_SCOPE_RISK",
            severity="high",
            label="Demolition scope risk",
            operator_note="Rip-out or demolition scope should be reviewed before approval.",
            manual_review=True,
            actions=(
                "Ask for photos before approving.",
                "Confirm rip-out scope and disposal material before approving.",
            ),
        )

    weather_protection_required = _as_bool(request.get("weather_protection_required"))
    if weather_protection_required:
        add_flag(
            code="WEATHER_PROTECTION_RISK",
            severity="low",
            label="Weather protection risk",
            operator_note="Weather-sensitive items may need covered handling or scheduling review.",
            actions=("Confirm weather protection expectations before scheduling.",),
        )

    ordered_flags = [flags[code] for code in _ADVISORY_FLAG_ORDER if code in flags]
    if not ordered_flags:
        return None

    max_severity = max(_ADVISORY_SEVERITY_ORDER[flag["severity"]] for flag in ordered_flags)
    risk_level = "high" if max_severity == 3 else "medium" if max_severity == 2 else "low"

    recommended_trailer = None
    if any(
        flag["code"] == "DEMOLITION_SCOPE_RISK"
        or (flag["code"] == "DENSE_MATERIAL_RISK" and flag["severity"] == "high")
        for flag in ordered_flags
    ):
        recommended_trailer = "double_axle_open_aluminum"
    elif weather_protection_required and _normalized_text(request.get("service_type")) in _MOVE_DELIVERY_SERVICE_TYPES:
        recommended_trailer = "newer_enclosed"

    advisory: dict[str, Any] = {
        "manual_review_recommended": manual_review_recommended,
        "risk_level": risk_level,
        "risk_flags": ordered_flags,
        "suggested_actions": suggested_actions,
        "pricing_effect": "none",
        "customer_visible": False,
    }
    if recommended_trailer:
        advisory["recommended_trailer"] = recommended_trailer
    return advisory
