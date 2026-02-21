from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

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
DEFAULT_BAG_TIER_SMALL_PRICE = 50.0
DEFAULT_BAG_TIER_MEDIUM_PRICE = 80.0
DEFAULT_BAG_TIER_LARGE_PRICE = 120.0


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
        return 0.0
    if bag_count <= DEFAULT_BAG_TIER_SMALL_MAX:
        return DEFAULT_BAG_TIER_SMALL_PRICE
    if bag_count <= DEFAULT_BAG_TIER_MEDIUM_MAX:
        return DEFAULT_BAG_TIER_MEDIUM_PRICE
    return DEFAULT_BAG_TIER_LARGE_PRICE


def _mattress_boxspring_fee(service_conf: Dict[str, Any], m: int, b: int) -> float:
    mb_cfg = service_conf.get("mattress_boxspring") or {}
    fee_each = float(mb_cfg.get("fee_each", DEFAULT_MATTRESS_FEE_EACH))
    # If they ever split fees later, still safe
    mattress_each = float(mb_cfg.get("mattress_fee_each", fee_each))
    box_each = float(mb_cfg.get("boxspring_fee_each", fee_each))
    return float(m * mattress_each + b * box_each)


def calculate_quote(
    service_type: str,
    hours: float,
    *,
    crew_size: int = 1,
    garbage_bag_count: int = 0,
    mattresses_count: int = 0,
    box_springs_count: int = 0,
    scrap_pickup_location: str = "curbside",
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

    # Moving minimum 4 hours (your rule)
    if normalized in ("small_move", "moving"):
        billable_hours = max(billable_hours, 4.0)
        crew_size = max(int(crew_size), 2)
    elif normalized == "demolition":
        crew_size = max(int(crew_size), 2)
    else:
        crew_size = max(int(crew_size), 1)

    travel = _travel_min(config)
    labor = _labor(billable_hours, crew_size, rates["primary"], rates["helper"])

    disposal_allowance = 0.0
    if normalized == "haul_away":
        disposal_allowance = _haul_away_disposal_allowance(svc, int(garbage_bag_count))

    mattress_boxspring = 0.0
    if normalized == "haul_away" and (int(mattresses_count) > 0 or int(box_springs_count) > 0):
        mattress_boxspring = _mattress_boxspring_fee(svc, int(mattresses_count), int(box_springs_count))

    raw_cash = travel + labor + disposal_allowance + mattress_boxspring

    min_total = _get_min_total(svc)
    cash_before_round = max(raw_cash, min_total)

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
            "billable_hours": round(float(billable_hours), 2),
            "primary_rate_cad": round(float(rates["primary"]), 2),
            "helper_rate_cad": round(float(rates["helper"]), 2),
            "travel_min_cad": round(float(travel), 2),
            "labor_cad": round(float(labor), 2),
            "disposal_allowance_cad": round(float(disposal_allowance), 2),
            "mattress_boxspring_cad": round(float(mattress_boxspring), 2),
        },
    }