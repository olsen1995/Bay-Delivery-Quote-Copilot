from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

CONFIG_PATH = Path("config/business_profile.json")

HST_RATE_EMT = 0.13

# Travel minimum always (gas + wear)
MIN_GAS_CAD = 20.0
MIN_WEAR_CAD = 20.0

# Labour rates (internal defaults — tune later)
DEFAULT_PRIMARY_RATE_CAD = 20.0
DEFAULT_HELPER_RATE_CAD = 16.0

# Mattress/boxspring internal fees (included in total; customer sees note only)
MATTRESS_FEE_EACH_CAD = 50.0
BOXSPRING_FEE_EACH_CAD = 50.0

# Haul-away disposal allowance tiers (internal; included in total; not itemized)
BAG_TIER_SMALL_MAX = 5
BAG_TIER_MEDIUM_MAX = 15
BAG_TIER_SMALL_PRICE = 50.0
BAG_TIER_MEDIUM_PRICE = 80.0
BAG_TIER_LARGE_PRICE = 120.0

# Scrap pickup (flat rate, bypasses all other math)
SCRAP_CURBSIDE_PRICE = 0.0
SCRAP_INSIDE_PRICE = 30.0


def load_config() -> Dict[str, Any]:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_service_type(service_type: str) -> str:
    """
    Unify junk + dump into one canonical customer-facing type.
    """
    aliases = {
        "dump_run": "haul_away",
        "junk": "haul_away",
        "junk_removal": "haul_away",
        "haulaway": "haul_away",
        "haul-away": "haul_away",
    }
    return aliases.get(service_type, service_type)


def round_cash_to_nearest_5(x: float) -> float:
    return float(int((x + 2.5) // 5) * 5)


def _calc_travel_min(config: Dict[str, Any]) -> float:
    """
    Prefer config minimum charges if present, otherwise defaults.
    """
    minimums = config.get("minimum_charges", {}) or {}
    gas = float(minimums.get("gas", MIN_GAS_CAD))
    wear = float(minimums.get("wear_and_tear", MIN_WEAR_CAD))
    return gas + wear


def _calc_labor(hours: float, crew_size: int, primary_rate: float, helper_rate: float) -> float:
    if hours <= 0:
        return 0.0
    hourly_total = primary_rate + max(0, crew_size - 1) * helper_rate
    return float(hours * hourly_total)


def _calc_haul_away_disposal(garbage_bag_count: int) -> float:
    if garbage_bag_count <= 0:
        return 0.0
    if garbage_bag_count <= BAG_TIER_SMALL_MAX:
        return float(BAG_TIER_SMALL_PRICE)
    if garbage_bag_count <= BAG_TIER_MEDIUM_MAX:
        return float(BAG_TIER_MEDIUM_PRICE)
    return float(BAG_TIER_LARGE_PRICE)


def _calc_mattress_boxspring(m: int, b: int) -> float:
    return float(m * MATTRESS_FEE_EACH_CAD + b * BOXSPRING_FEE_EACH_CAD)


def _calc_scrap(location: str) -> float:
    """
    location: 'curbside' or 'inside'
    """
    if location == "inside":
        return float(SCRAP_INSIDE_PRICE)
    return float(SCRAP_CURBSIDE_PRICE)


def _service_minimum_from_config(service_config: Dict[str, Any]) -> float:
    """
    Optional per-service minimum charge. If absent, returns 0.
    """
    # Support a few likely keys depending on how config evolves:
    for key in ("minimum_charge", "minimum_total", "min_charge"):
        if key in service_config:
            try:
                return float(service_config[key])
            except Exception:
                pass
    return 0.0


def _service_min_hours_from_config(service_config: Dict[str, Any]) -> float:
    try:
        return float(service_config.get("minimum_hours", 0))
    except Exception:
        return 0.0


def calculate_quote(
    *,
    service_type: str,
    hours: float,
    crew_size: int = 1,
    garbage_bag_count: int = 0,
    mattresses_count: int = 0,
    box_springs_count: int = 0,
    scrap_pickup_location: str = "curbside",
) -> Dict[str, Any]:
    """
    Returns:
      - Customer-facing totals only: total_cash_cad, total_emt_cad, disclaimer
      - Internal breakdown under key: _internal (for admin/logging)
    """
    config = load_config()
    services = config.get("services", {}) or {}

    service_type = normalize_service_type(service_type)

    # -----------------------------
    # 1) Scrap pickup: hard lock
    # -----------------------------
    if service_type == "scrap_pickup":
        cash_total = _calc_scrap(scrap_pickup_location)
        emt_total = round(cash_total * (1.0 + HST_RATE_EMT), 2)
        disclaimer = (
            "Scrap pickup is flat-rate: curbside is free (picked up next time we’re in the area); "
            "inside removal is $30. Cash is tax-free; EMT/e-transfer adds 13% HST."
        )

        return {
            "service_type": service_type,
            "total_cash_cad": round(cash_total, 2),
            "total_emt_cad": round(emt_total, 2),
            "disclaimer": disclaimer,
            "_internal": {
                "crew_size": 1,
                "billable_hours": 0.0,
                "primary_rate_cad": 0.0,
                "helper_rate_cad": 0.0,
                "travel_min_cad": 0.0,
                "labor_cad": 0.0,
                "disposal_allowance_cad": 0.0,
                "mattress_boxspring_cad": 0.0,
                "scrap_cad": round(cash_total, 2),
            },
        }

    # -----------------------------
    # 2) All other services
    # -----------------------------
    if service_type not in services:
        raise ValueError(f"Service type '{service_type}' not found in config.")

    service_config = services[service_type]

    # Hours logic (keep your legacy minimum_hours behaviour)
    min_hours = _service_min_hours_from_config(service_config)
    billable_hours = max(float(hours), float(min_hours))

    # Moving: you stated minimum 4 hours (this is on UI note too)
    if service_type in ("small_move", "small_moving", "moving"):
        billable_hours = max(billable_hours, 4.0)

    # Crew minimums (business rule)
    if service_type in ("small_move", "small_moving", "moving", "demolition"):
        crew_size = max(int(crew_size), 2)
    else:
        crew_size = max(int(crew_size), 1)

    # Rates: use config hourly_rate if present as PRIMARY rate, otherwise defaults
    try:
        primary_rate = float(service_config.get("hourly_rate", DEFAULT_PRIMARY_RATE_CAD))
    except Exception:
        primary_rate = DEFAULT_PRIMARY_RATE_CAD

    helper_rate = DEFAULT_HELPER_RATE_CAD

    travel = _calc_travel_min(config)
    labor = _calc_labor(billable_hours, crew_size, primary_rate, helper_rate)

    disposal_allowance = 0.0
    if service_type == "haul_away":
        disposal_allowance = _calc_haul_away_disposal(int(garbage_bag_count))

    mattress_boxspring = _calc_mattress_boxspring(int(mattresses_count), int(box_springs_count))

    raw_cash = travel + labor + disposal_allowance + mattress_boxspring

    # Optional per-service minimum total (if config includes it)
    service_min_total = _service_minimum_from_config(service_config)
    cash_before_round = max(raw_cash, service_min_total)

    cash_total = round_cash_to_nearest_5(cash_before_round)
    emt_total = round(cash_total * (1.0 + HST_RATE_EMT), 2)

    disclaimer = (
        "This estimate is based on the information provided and may change after an in-person view "
        "(stairs, heavy items, access, actual load size, multiple trips, etc.). "
        "Removal & disposal included (if required). "
        "Mattresses/box springs may have an additional disposal cost if included. "
        "Cash is tax-free; EMT/e-transfer adds 13% HST."
    )

    return {
        "service_type": service_type,
        "total_cash_cad": round(cash_total, 2),
        "total_emt_cad": round(emt_total, 2),
        "disclaimer": disclaimer,
        "_internal": {
            "crew_size": int(crew_size),
            "billable_hours": round(float(billable_hours), 2),
            "primary_rate_cad": round(float(primary_rate), 2),
            "helper_rate_cad": round(float(helper_rate), 2),
            "travel_min_cad": round(float(travel), 2),
            "labor_cad": round(float(labor), 2),
            "disposal_allowance_cad": round(float(disposal_allowance), 2),
            "mattress_boxspring_cad": round(float(mattress_boxspring), 2),
            "scrap_cad": 0.0,
        },
    }