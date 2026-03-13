from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

CONFIG_PATH = Path("config/business_profile.json")

# Defaults (used if config is missing fields)
DEFAULT_HST_EMT = 0.13
DEFAULT_GAS = 20.0
DEFAULT_WEAR = 20.0

# Scrap pickup (hard-locked business rule)
SCRAP_CURBSIDE_PRICE = 0.0
SCRAP_INSIDE_PRICE = 30.0

# Mattress/box spring (included in total; customer sees note only)
DEFAULT_MATTRESS_FEE_EACH = 50.0
DEFAULT_BOXSPRING_FEE_EACH = 50.0

# Haul-away disposal allowance tiers (included in total; NOT itemized)
DEFAULT_BAG_TIER_SMALL_MAX = 5
DEFAULT_BAG_TIER_MEDIUM_MAX = 15
DEFAULT_BAG_TIER_LARGE_MAX = 16
DEFAULT_BAG_TIER_XL_MAX = 20
DEFAULT_BAG_TIER_XXL_MAX = 24
DEFAULT_BAG_TIER_SMALL_PRICE = 50.0
DEFAULT_BAG_TIER_MEDIUM_PRICE = 80.0
DEFAULT_BAG_TIER_LARGE_PRICE = 165.0
DEFAULT_BAG_TIER_XL_PRICE = 175.0
DEFAULT_BAG_TIER_XXL_PRICE = 185.0
DEFAULT_BAG_TIER_XXXL_PRICE = 210.0

# Admin-only travel zone adders (profit protection)
TRAVEL_ZONE_ADDERS = {
    "in_town": 0.0,
    "surrounding": 20.0,
    "out_of_town": 40.0,
}

# Access difficulty surcharges — applied after labour/disposal, before minimum check.
# Designed to protect margins on stairs, basements, long carry, tight access.
ACCESS_DIFFICULTY_ADDERS = {
    "normal": 0.0,
    "difficult": 25.0,   # e.g. one flight of stairs, basement, tight parking
    "extreme": 60.0,    # e.g. multiple flights, steep stairs, very narrow doorway
}

# Dense/heavy material labour load multiplier (applied to haul_away labour only).
# Dense materials (drywall, concrete, shingles, tile, wet debris) load much
# slower per bag than typical household junk — protect against undercharging.
DENSE_MATERIAL_LABOUR_MULTIPLIER = 1.35

# Minimum bag count that requires a helper for haul_away (single worker is
# unrealistic above this threshold).
HAUL_AWAY_HELPER_BAG_THRESHOLD = 10

# Small-load protection: for haul_away with 1–SMALL_LOAD_MAX_BAGS light (non-dense)
# bags, the disposal allowance is computed per-bag instead of the flat tier amount.
# This prevents a 1–3 bag job from receiving the same disposal cost as a 5-bag job.
# Dense materials always bypass this protection so margin is preserved.
SMALL_LOAD_MAX_BAGS = 3
SMALL_LOAD_DISPOSAL_PER_BAG = 15.0  # $15 per bag for 1–3 light bags


def load_config() -> Dict[str, Any]:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _get_tax_rates(config: Dict[str, Any]) -> Dict[str, float]:
    tax_policy = config.get("tax_policy") or {}
    cash_rate = float(tax_policy.get("cash_hst_rate", 0.0))
    emt_rate = float(tax_policy.get("emt_hst_rate", DEFAULT_HST_EMT))
    return {"cash": cash_rate, "emt": emt_rate}


def _normalize_service_type(config: Dict[str, Any], service_type: str) -> str:
    # Prefer config aliases if present
    aliases = config.get("service_type_aliases") or {}
    if service_type in aliases:
        return str(aliases[service_type])

    # Back-compat hard aliases
    fallback_aliases = {
        "dump_run": "haul_away",
        "junk_removal": "haul_away",
        "junk": "haul_away",
        "haulaway": "haul_away",
        "moving": "small_move",
        "delivery": "item_delivery",
    }
    return fallback_aliases.get(service_type, service_type)


def _round_cash_to_nearest_5(x: float) -> float:
    return float(int((x + 2.5) // 5) * 5)


def _travel_min(config: Dict[str, Any]) -> float:
    minimums = config.get("minimum_charges") or {}
    gas = float(minimums.get("gas", DEFAULT_GAS))
    wear = float(minimums.get("wear_and_tear", DEFAULT_WEAR))
    return gas + wear


def _service_conf(config: Dict[str, Any], service_type: str) -> Dict[str, Any]:
    services = config.get("services") or {}
    if service_type not in services:
        raise ValueError(f"Service type '{service_type}' not found in config.")
    return services[service_type] or {}


def _get_min_hours(service_conf: Dict[str, Any]) -> float:
    # supports both old + new config styles
    if "minimum_hours" in service_conf:
        return float(service_conf["minimum_hours"])
    return 0.0


def _get_min_total(service_conf: Dict[str, Any]) -> float:
    # supports both old + new config styles
    if "minimum_total" in service_conf:
        return float(service_conf["minimum_total"])
    if "minimum_charge" in service_conf:
        return float(service_conf["minimum_charge"])
    return 0.0


def _get_min_labor_per_crew_hour(service_conf: Dict[str, Any]) -> float:
    """Minimum effective labour rate per crew member per hour.

    Used for small_move calibration: moving crews command a higher effective
    rate than haul-away. When the computed labour falls below this floor the
    floor value is used instead.  Returns 0 (no floor) when the field is absent
    from the service config, so haul_away and other services are unaffected.
    """
    val = service_conf.get("min_labor_per_crew_hour")
    if val is None:
        return 0.0
    return float(val)


def _get_long_job_min_labor_per_crew_hour(service_conf: Dict[str, Any]) -> float:
    """Raised small-move labour floor for billable hours beyond the 4h baseline."""
    val = service_conf.get("long_job_min_labor_per_crew_hour")
    if val is None:
        return 0.0
    return float(val)


def _rates(service_conf: Dict[str, Any]) -> Dict[str, float]:
    """
    Supports:
    - Old config: hourly_rate (single)
    - New config: hourly_rate_primary + hourly_rate_helper
    """
    if "hourly_rate_primary" in service_conf:
        primary = float(service_conf.get("hourly_rate_primary", 20))
        helper = float(service_conf.get("hourly_rate_helper", 16))
        return {"primary": primary, "helper": helper}

    if "hourly_rate" in service_conf:
        # Old style: treat it as "primary", helpers default to 16
        primary = float(service_conf.get("hourly_rate", 20))
        helper = float(service_conf.get("hourly_rate_helper", 16))
        return {"primary": primary, "helper": helper}

    # Fallback
    return {"primary": 20.0, "helper": 16.0}


def _labor(hours: float, crew_size: int, primary_rate: float, helper_rate: float) -> float:
    if hours <= 0:
        return 0.0
    crew_size = max(int(crew_size), 1)
    hourly_total = primary_rate + max(0, crew_size - 1) * helper_rate
    return float(hours * hourly_total)


def _haul_away_disposal_allowance(service_conf: Dict[str, Any], bag_count: int) -> float:
    # Prefer new config structure if present
    disposal_cfg = service_conf.get("disposal_allowance_by_bags") or {}
    tiers = disposal_cfg.get("tiers")
    if isinstance(tiers, list) and tiers:
        for tier in tiers:
            max_bags = int(tier.get("max_bags", 0))
            allowance = float(tier.get("allowance", 0))
            if bag_count <= max_bags:
                return allowance
        # If tiers exist but none matched, use last allowance
        last = tiers[-1]
        return float(last.get("allowance", 0))

    # Fallback to defaults
    if bag_count <= 0:
        # Align with configured tiers: treat 0 (and any non-positive) as the smallest tier
        return DEFAULT_BAG_TIER_SMALL_PRICE
    if bag_count <= DEFAULT_BAG_TIER_SMALL_MAX:
        return DEFAULT_BAG_TIER_SMALL_PRICE
        return DEFAULT_BAG_TIER_MEDIUM_PRICE
    if bag_count <= DEFAULT_BAG_TIER_LARGE_MAX:
        return DEFAULT_BAG_TIER_LARGE_PRICE
    if bag_count <= DEFAULT_BAG_TIER_XL_MAX:
        return DEFAULT_BAG_TIER_XL_PRICE
    if bag_count <= DEFAULT_BAG_TIER_XXL_MAX:
        return DEFAULT_BAG_TIER_XXL_PRICE
    return DEFAULT_BAG_TIER_XXXL_PRICE


def _mattress_boxspring_fee(service_conf: Dict[str, Any], m: int, b: int) -> float:
    mb_cfg = service_conf.get("mattress_boxspring") or {}
    fee_each = float(mb_cfg.get("fee_each", DEFAULT_MATTRESS_FEE_EACH))
    # If they ever split fees later, still safe
    mattress_each = float(mb_cfg.get("mattress_fee_each", fee_each))
    box_each = float(mb_cfg.get("boxspring_fee_each", fee_each))
    return float(m * mattress_each + b * box_each)


def _haul_away_bag_type_floor(service_conf: Dict[str, Any], bag_type: str | None, bag_count: int) -> float:
    if bag_count <= 0:
        return 0.0
    anchors = service_conf.get("bag_type_anchors_cad_per_bag") or {}
    bag_type_key = str(bag_type or "").strip().lower()
    anchor = anchors.get(bag_type_key)
    if anchor is None:
        return 0.0
    return float(bag_count) * float(anchor)


def _haul_away_trailer_fill_floor(service_conf: Dict[str, Any], trailer_fill_estimate: str | None) -> float:
    anchors = service_conf.get("trailer_fill_floor_anchors_cad") or {}
    trailer_fill_key = str(trailer_fill_estimate or "").strip().lower()
    anchor = anchors.get(trailer_fill_key)
    if anchor is None:
        return 0.0
    return float(anchor)


def calculate_quote(
    service_type: str,
    hours: float,
    *,
    crew_size: int = 1,
    garbage_bag_count: int = 0,
    bag_type: str | None = None,
    trailer_fill_estimate: str | None = None,
    mattresses_count: int = 0,
    box_springs_count: int = 0,
    scrap_pickup_location: str = "curbside",
    travel_zone: str = "in_town",
    access_difficulty: str = "normal",
    has_dense_materials: bool = False,
) -> Dict[str, Any]:
    """
    Customer-safe output:
      - total_cash_cad
      - total_emt_cad
      - disclaimer

    Internal breakdown is returned under "_internal" for admin logging only.
    """
    config = load_config()
    tax = _get_tax_rates(config)

    normalized = _normalize_service_type(config, service_type)

    # -------------------------
    # Scrap pickup (hard lock)
    # -------------------------
    if normalized == "scrap_pickup":
        cash_total = SCRAP_INSIDE_PRICE if str(scrap_pickup_location) == "inside" else SCRAP_CURBSIDE_PRICE
        emt_total = round(cash_total * (1.0 + tax["emt"]), 2)

        return {
            "service_type": normalized,
            "total_cash_cad": round(cash_total, 2),
            "total_emt_cad": round(emt_total, 2),
            "disclaimer": (
                "Scrap pickup is flat-rate: curbside is free (picked up next time we’re in the area); "
                "inside removal is $30. Cash is tax-free; EMT/e-transfer adds 13% HST."
            ),
            "_internal": {
                "crew_size": 1,
                "billable_hours": 0.0,
                "travel_min_cad": 0.0,
                "travel_zone": "n/a",
                "travel_zone_adder_cad": 0.0,
                "labor_cad": 0.0,
                "disposal_allowance_cad": 0.0,
                "mattress_boxspring_cad": 0.0,
                "scrap_cad": round(cash_total, 2),
            },
        }

    # -------------------------
    # Other services (config)
    # -------------------------
    svc = _service_conf(config, normalized)
    rates = _rates(svc)

    billable_hours = max(float(hours), _get_min_hours(svc))

    # Resolve and clamp access difficulty
    _ad = (access_difficulty or "normal").strip().lower()
    if _ad not in ACCESS_DIFFICULTY_ADDERS:
        _ad = "normal"
    access_adder = float(ACCESS_DIFFICULTY_ADDERS[_ad])

    # Moving minimum 4 hours (your rule)
    if normalized in ("small_move", "moving"):
        billable_hours = max(billable_hours, 4.0)
        crew_size = max(int(crew_size), 2)
    elif normalized == "demolition":
        crew_size = max(int(crew_size), 2)
    else:
        crew_size = max(int(crew_size), 1)

    # haul_away helper escalation rules
    # 1) Large load (>= HAUL_AWAY_HELPER_BAG_THRESHOLD bags) needs a helper.
    # 2) Dense/heavy materials need a helper regardless of bag count.
    haul_away_crew_escalated = False
    if normalized == "haul_away" and crew_size < 2:
        if int(garbage_bag_count) >= HAUL_AWAY_HELPER_BAG_THRESHOLD or bool(has_dense_materials):
            crew_size = 2
            haul_away_crew_escalated = True

    base_travel = _travel_min(config)

    tz = (travel_zone or "in_town").strip().lower()
    if tz not in TRAVEL_ZONE_ADDERS:
        tz = "in_town"
    travel_adder = float(TRAVEL_ZONE_ADDERS[tz])
    travel = base_travel + travel_adder

    labor = _labor(billable_hours, crew_size, rates["primary"], rates["helper"])

    # Dense material labour surcharge: loading drywall/concrete/etc. takes longer.
    # Applied to haul_away labour only; does not affect travel or disposal allowance.
    if normalized == "haul_away" and bool(has_dense_materials):
        labor = labor * DENSE_MATERIAL_LABOUR_MULTIPLIER

    # Small-move labour floor: moving crews command a higher effective rate than
    # haul-away.  Configured via min_labor_per_crew_hour in the small_move service
    # settings.  Longer jobs can also use a slightly higher floor rate on hours
    # beyond the 4h move baseline. Has no effect when actual labour already meets
    # or exceeds the floor.
    move_labor_floor_applied = False
    move_long_job_floor_applied = False
    if normalized == "small_move":
        _min_rate = _get_min_labor_per_crew_hour(svc)
        _long_job_min_rate = _get_long_job_min_labor_per_crew_hour(svc)
        if _min_rate > 0:
            _base_move_hours = min(float(billable_hours), 4.0)
            _long_move_hours = max(float(billable_hours) - 4.0, 0.0)
            _effective_long_job_rate = _min_rate
            if _long_move_hours > 0 and _long_job_min_rate > _min_rate:
                _effective_long_job_rate = _long_job_min_rate
            _labor_floor = (
                _min_rate * float(crew_size) * _base_move_hours
                + _effective_long_job_rate * float(crew_size) * _long_move_hours
            )
            if labor < _labor_floor:
                labor = _labor_floor
                move_labor_floor_applied = True
                move_long_job_floor_applied = _long_move_hours > 0 and _effective_long_job_rate > _min_rate

    disposal_allowance = 0.0
    small_load_protected = False
    if normalized == "haul_away":
        _bag_count = int(garbage_bag_count)
        if 1 <= _bag_count <= SMALL_LOAD_MAX_BAGS and not bool(has_dense_materials):
            # Small-load protection: scale disposal proportionally for tiny light loads.
            # Dense materials always fall through to the full tier (margin preserved).
            disposal_allowance = float(_bag_count) * SMALL_LOAD_DISPOSAL_PER_BAG
            small_load_protected = True
        else:
            disposal_allowance = _haul_away_disposal_allowance(svc, _bag_count)
            if (
                not bool(has_dense_materials)
                and _ad == "normal"
                and 6 <= _bag_count <= 8
            ):
                # Narrow calibration band for light 6-8 bag jobs only.
                # Keeps 9+ tier anchor unchanged and avoids affecting hard/dense work.
                disposal_allowance = max(0.0, disposal_allowance - float(9 - _bag_count) * 5.0)

    mattress_boxspring = 0.0
    if normalized == "haul_away" and (int(mattresses_count) > 0 or int(box_springs_count) > 0):
        mattress_boxspring = _mattress_boxspring_fee(svc, int(mattresses_count), int(box_springs_count))

    raw_cash = travel + labor + disposal_allowance + mattress_boxspring + access_adder

    min_total = _get_min_total(svc)
    cash_before_round = max(raw_cash, min_total)

    bag_type_floor = 0.0
    trailer_fill_floor = 0.0
    if normalized == "haul_away":
        bag_type_floor = _haul_away_bag_type_floor(svc, bag_type, int(garbage_bag_count))
        trailer_fill_floor = _haul_away_trailer_fill_floor(svc, trailer_fill_estimate)
        cash_before_round = max(cash_before_round, bag_type_floor, trailer_fill_floor)

    cash_total = _round_cash_to_nearest_5(cash_before_round)
    emt_total = round(cash_total * (1.0 + tax["emt"]), 2)

    # Customer disclaimer (no dump fee line items)
    customer_disclaimer = (config.get("customer_disclaimer") or {}).get("base")
    if not customer_disclaimer:
        customer_disclaimer = (
            "This estimate is based on the information provided and may change after an in-person view "
            "(stairs, heavy items, access, actual load size, multiple trips, etc.)."
        )

    disclaimer = (
        f"{customer_disclaimer} "
        "Removal & disposal included (if required). "
        "Mattresses/box springs may have an additional disposal cost if included. "
        "Cash is tax-free; EMT/e-transfer adds 13% HST."
    )

    return {
        "service_type": normalized,
        "total_cash_cad": round(cash_total, 2),
        "total_emt_cad": round(emt_total, 2),
        "disclaimer": disclaimer,
        "_internal": {
            "crew_size": int(crew_size),
            "crew_escalated": haul_away_crew_escalated,
            "move_labor_floor_applied": move_labor_floor_applied,
            "move_long_job_floor_applied": move_long_job_floor_applied,
            "billable_hours": round(float(billable_hours), 2),
            "primary_rate_cad": round(float(rates["primary"]), 2),
            "helper_rate_cad": round(float(rates["helper"]), 2),
            "travel_min_cad": round(float(base_travel), 2),
            "travel_zone": tz,
            "travel_zone_adder_cad": round(float(travel_adder), 2),
            "travel_total_cad": round(float(travel), 2),
            "labor_cad": round(float(labor), 2),
            "dense_materials": bool(has_dense_materials),
            "small_load_protected": small_load_protected,
            "disposal_allowance_cad": round(float(disposal_allowance), 2),
            "mattress_boxspring_cad": round(float(mattress_boxspring), 2),
            "bag_type": bag_type,
            "bag_type_floor_cad": round(float(bag_type_floor), 2),
            "trailer_fill_estimate": trailer_fill_estimate,
            "trailer_fill_floor_cad": round(float(trailer_fill_floor), 2),
            "access_difficulty": _ad,
            "access_difficulty_adder_cad": round(float(access_adder), 2),
        },
    }
