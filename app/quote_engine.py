from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any, Dict

CONFIG_PATH = Path("config/business_profile.json")

# Defaults (used if config is missing fields)
DEFAULT_HST_EMT = 0.13
DEFAULT_GAS = 20.0
DEFAULT_WEAR = 20.0
GLOBAL_MIN_TOTAL_CAD = 60.0

# Scrap pickup base amounts before the universal minimum floor is applied.
SCRAP_CURBSIDE_BASE_CAD = 0.0
SCRAP_INSIDE_BASE_CAD = 30.0

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
SMALL_LOAD_DISPOSAL_SINGLE_BAG = 20.0
SMALL_LOAD_DISPOSAL_TWO_BAGS = 35.0

# Mid-band haul-away progression adder for 10-15 bag light jobs.
# This avoids flat pricing in the 12-15 range while leaving heavy tiers unchanged.
MID_BAND_START_BAGS = 10
MID_BAND_END_BAGS = 15
MID_BAND_ADDER_PER_BAG = 3.0

RISK_MARGIN_PROTECTION_STRONG_FLAGS = frozenset(
    {
        "likely_underestimated_volume",
        "dense_material_risk",
        "mixed_bulky_load_risk",
        "access_volume_risk",
    }
)

_TEXT_NORMALIZE_RE = re.compile(r"[^a-z0-9]+")
_FIXED_BULKY_PHRASES = (
    "mattress",
    "mattresses",
    "box spring",
    "box springs",
    "boxspring",
    "boxsprings",
    "couch",
    "sofa",
    "recliner",
    "loveseat",
)
_EASY_FIXED_BULKY_ACCESS_PHRASES = (
    "curbside",
    "curb side",
    "driveway",
    "drive way",
    "outside",
    "outdoor",
    "garage",
)
_DIFFICULT_FIXED_BULKY_ACCESS_PHRASES = (
    "stairs",
    "stair",
    "basement",
    "upstairs",
    "downstairs",
    "tight",
    "narrow",
    "maneuver",
    "manoeuver",
    "awkward",
    "won t fit",
    "wont fit",
)
_MULTI_STOP_COMPLEXITY_PHRASES = (
    "remove old",
    "take away old",
    "haul away old",
    "pickup dropoff removal",
    "pick up drop off removal",
    "pickup and dropoff and removal",
    "pickup and drop off and removal",
    "deliver and remove",
    "delivery and removal",
    "pickup dropoff and dump",
    "pickup drop off and dump",
    "multiple stops",
    "two stops",
    "three stops",
    "second stop",
    "stop at storage",
    "stop at dump",
    "stop at donation",
    "donation drop off",
    "drop off at donation",
)
_MULTI_STOP_EXCHANGE_PHRASES = (
    "remove old",
    "take away old",
    "haul away old",
    "old item",
    "old couch",
    "old mattress",
    "existing item",
    "existing couch",
    "existing mattress",
    "swap out",
)
_DISASSEMBLY_PHRASES = (
    "take apart",
    "break down",
    "disassemble",
    "disassembly",
    "remove legs",
    "remove doors",
    "won t fit as is",
    "wont fit as is",
    "won t fit",
    "wont fit",
)
_SMALL_LOAD_PHRASES = (
    "small load",
    "few things",
    "few items",
    "just a few",
    "not much",
    "small amount",
)
_AWKWARD_ITEM_PHRASES = (
    "sectional",
    "dresser",
    "desk",
    "table",
    "chair",
    "frame",
)
_SINGLE_ITEM_PHRASES = (
    "one ",
    "single ",
    "just one ",
)


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


def _get_item_delivery_protected_base_floor(service_conf: Dict[str, Any]) -> float:
    """Protected pre-access floor for item_delivery to avoid soft two-address quotes."""
    val = service_conf.get("item_delivery_protected_base_floor_cad")
    if val is None:
        return 0.0
    return float(val)


def _get_enclosed_trailer_adder(service_conf: Dict[str, Any]) -> float:
    """Return the config-backed enclosed trailer adder for the active service."""
    val = service_conf.get("enclosed_trailer_adder_cad")
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
    if bag_count <= DEFAULT_BAG_TIER_MEDIUM_MAX:
        return DEFAULT_BAG_TIER_MEDIUM_PRICE
    if bag_count <= DEFAULT_BAG_TIER_LARGE_MAX:
        return DEFAULT_BAG_TIER_LARGE_PRICE
    if bag_count <= DEFAULT_BAG_TIER_XL_MAX:
        return DEFAULT_BAG_TIER_XL_PRICE
    if bag_count <= DEFAULT_BAG_TIER_XXL_MAX:
        return DEFAULT_BAG_TIER_XXL_PRICE
    return DEFAULT_BAG_TIER_XXXL_PRICE


def _get_haul_away_dense_disposal_multiplier(service_conf: Dict[str, Any]) -> float:
    """Return a safe dense-material disposal multiplier for haul-away jobs.

    Fallback is 1.0 when config is missing, non-numeric, non-finite, or <= 0.
    """
    raw = service_conf.get("dense_material_disposal_multiplier", 1.0)
    try:
        mult = float(raw)
    except (TypeError, ValueError):
        return 1.0
    if not math.isfinite(mult) or mult <= 0.0:
        return 1.0
    return mult


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
    bag_type_key = str(bag_type or "").strip().lower()
    if not bag_type_key:
        return 0.0
    anchors = service_conf.get("bag_type_anchors_cad_per_bag") or {}
    if not isinstance(anchors, dict):
        return 0.0
    anchor = anchors.get(bag_type_key)
    if anchor is None:
        return 0.0
    return float(bag_count) * float(anchor)


def _haul_away_access_difficulty_small_load_floor(
    service_conf: Dict[str, Any], access_difficulty: str | None, small_load_protected: bool
) -> float:
    """Return the config-backed minimum total for tiny awkward haul-away jobs.

    Only applies when the job is small-load protected (see
    small_load_protected definition; typically a small load of non-dense
    materials) AND access is difficult or extreme.  Returns 0 for all other
    combinations so existing pricing is unaffected.
    """
    if not small_load_protected:
        return 0.0
    ad = (access_difficulty or "normal").strip().lower()
    if ad not in ("difficult", "extreme"):
        return 0.0
    anchors = service_conf.get("access_difficulty_small_load_floor_cad") or {}
    if not isinstance(anchors, dict):
        return 0.0
    anchor = anchors.get(ad)
    if anchor is None:
        return 0.0
    return float(anchor)


def _haul_away_trailer_fill_floor(service_conf: Dict[str, Any], trailer_fill_estimate: str | None) -> float:
    trailer_fill_key = str(trailer_fill_estimate or "").strip().lower()
    if not trailer_fill_key:
        return 0.0
    anchors = service_conf.get("trailer_fill_floor_anchors_cad") or {}
    if not isinstance(anchors, dict):
        return 0.0
    anchor = anchors.get(trailer_fill_key)
    if anchor is None:
        return 0.0
    return float(anchor)


_ENCLOSED_TRAILER_CLASSES: frozenset[str] = frozenset({"older_enclosed", "newer_enclosed"})


def _haul_away_trailer_class_fill_floor(
    service_conf: Dict[str, Any],
    trailer_class: str | None,
    trailer_fill_estimate: str | None,
) -> float:
    """Resolve haul-away trailer-fill floor by trailer class.

    When trailer_class is omitted, empty, unrecognized, or an enclosed class,
    fall back to the default trailer-fill anchors so existing behavior is preserved.
    """
    tc_key = str(trailer_class or "").strip().lower()
    fill_key = str(trailer_fill_estimate or "").strip().lower()

    if not fill_key:
        return 0.0

    if tc_key and tc_key not in _ENCLOSED_TRAILER_CLASSES:
        class_tables = service_conf.get("trailer_class_fill_floor_anchors_cad")
        if isinstance(class_tables, dict):
            anchors = class_tables.get(tc_key)
            if isinstance(anchors, dict):
                anchor = anchors.get(fill_key)
                if anchor is not None:
                    return float(anchor)

    return _haul_away_trailer_fill_floor(service_conf, trailer_fill_estimate)


def _normalize_load_mode(load_mode: str | None) -> str:
    mode = str(load_mode or "").strip().lower()
    if mode == "space_fill":
        return "space_fill"
    return "standard"


def _space_fill_class_from_trailer_fill(trailer_fill_estimate: str | None) -> int:
    fill_key = str(trailer_fill_estimate or "").strip().lower()
    if fill_key == "under_quarter":
        return 0
    if fill_key in {"quarter", "half"}:
        return 1
    if fill_key == "three_quarter":
        return 2
    if fill_key == "full":
        return 3
    return -1


def _space_fill_class_from_bag_count(garbage_bag_count: int) -> int:
    bags = int(garbage_bag_count)
    if bags >= 16:
        return 3
    if bags >= 10:
        return 2
    if bags >= 5:
        return 1
    return 0


def _space_fill_floor_for_class(size_class: int) -> float:
    if size_class == 0:
        return 225.0
    if size_class == 1:
        return 300.0
    if size_class == 2:
        return 375.0
    return 0.0


def _risk_margin_protection(assessment: dict[str, Any] | None) -> tuple[float, list[str]]:
    if not isinstance(assessment, dict):
        return 0.0, []

    raw_flags = assessment.get("risk_flags")
    if not isinstance(raw_flags, list):
        return 0.0, []

    contributing_flags: list[str] = []
    seen_flags: set[str] = set()
    for raw_flag in raw_flags:
        if not isinstance(raw_flag, str):
            continue
        if raw_flag not in RISK_MARGIN_PROTECTION_STRONG_FLAGS:
            continue
        if raw_flag in seen_flags:
            continue
        contributing_flags.append(raw_flag)
        seen_flags.add(raw_flag)

    strong_flag_count = len(contributing_flags)
    if strong_flag_count == 1:
        return 50.0, contributing_flags
    if strong_flag_count == 2:
        return 75.0, contributing_flags
    if strong_flag_count >= 3:
        return 100.0, contributing_flags
    return 0.0, []


def _normalized_signal_text(*parts: Any) -> str:
    raw = " ".join(str(part or "") for part in parts if part is not None)
    normalized = _TEXT_NORMALIZE_RE.sub(" ", raw.lower())
    return " ".join(normalized.split())


def _contains_any_phrase(text: str, phrases: tuple[str, ...]) -> bool:
    if not text:
        return False
    padded_text = f" {text} "
    for phrase in phrases:
        normalized_phrase = _normalized_signal_text(phrase)
        if normalized_phrase and f" {normalized_phrase} " in padded_text:
            return True
    return False


def _count_matched_phrases(text: str, phrases: tuple[str, ...]) -> int:
    if not text:
        return 0
    padded_text = f" {text} "
    matched = 0
    for phrase in phrases:
        normalized_phrase = _normalized_signal_text(phrase)
        if normalized_phrase and f" {normalized_phrase} " in padded_text:
            matched += 1
    return matched


def _has_fixed_bulky_item_signal(text: str, mattresses_count: int, box_springs_count: int) -> bool:
    if mattresses_count > 0 or box_springs_count > 0:
        return True
    return _contains_any_phrase(text, _FIXED_BULKY_PHRASES)


def _is_single_bulky_item_job(
    text: str,
    mattresses_count: int,
    box_springs_count: int,
    garbage_bag_count: int,
) -> bool:
    structured_bulky_count = max(int(mattresses_count), 0) + max(int(box_springs_count), 0)
    if structured_bulky_count == 1 and int(garbage_bag_count) <= SMALL_LOAD_MAX_BAGS:
        return True
    return (
        int(garbage_bag_count) <= SMALL_LOAD_MAX_BAGS
        and _contains_any_phrase(text, _FIXED_BULKY_PHRASES)
        and _contains_any_phrase(text, _SINGLE_ITEM_PHRASES)
    )


def _haul_away_fixed_bulky_floor(
    *,
    access_difficulty: str,
    text: str,
    mattresses_count: int,
    box_springs_count: int,
    garbage_bag_count: int,
) -> float:
    if access_difficulty == "extreme":
        return 0.0
    if not (
        _has_fixed_bulky_item_signal(text, mattresses_count, box_springs_count)
        or _is_single_bulky_item_job(text, mattresses_count, box_springs_count, garbage_bag_count)
    ):
        return 0.0
    if access_difficulty == "difficult" or _contains_any_phrase(text, _DIFFICULT_FIXED_BULKY_ACCESS_PHRASES):
        return 110.0
    if _contains_any_phrase(text, _EASY_FIXED_BULKY_ACCESS_PHRASES):
        return 90.0
    return 100.0


def _multi_stop_complexity_adder(
    *,
    route_complete: bool,
    service_type: str,
    travel_zone: str,
    access_difficulty: str,
    text: str,
) -> float:
    if service_type not in {"small_move", "item_delivery"} or not route_complete:
        return 0.0
    has_complex_multi_stop_signal = _contains_any_phrase(text, _MULTI_STOP_COMPLEXITY_PHRASES)
    has_routed_removal_blend = (
        _contains_any_phrase(text, _MULTI_STOP_EXCHANGE_PHRASES)
        and ("pickup" in text or "pick up" in text or "dropoff" in text or "drop off" in text or "delivery" in text)
    )
    if not (has_complex_multi_stop_signal or has_routed_removal_blend):
        return 0.0
    if (
        access_difficulty in {"difficult", "extreme"}
        or travel_zone != "in_town"
        or _contains_any_phrase(text, ("three stops", "multiple stops", "second stop", "stop at storage"))
    ):
        return 100.0
    return 75.0


def _disassembly_complexity_adder(
    *,
    access_difficulty: str,
    text: str,
) -> float:
    if not _contains_any_phrase(text, _DISASSEMBLY_PHRASES):
        return 0.0
    if access_difficulty in {"difficult", "extreme"}:
        return 75.0
    return 50.0


def _small_load_bulky_trap_adder(
    *,
    text: str,
    garbage_bag_count: int,
    mattresses_count: int,
    box_springs_count: int,
) -> float:
    if int(garbage_bag_count) > SMALL_LOAD_MAX_BAGS:
        return 0.0
    if not _contains_any_phrase(text, _SMALL_LOAD_PHRASES):
        return 0.0

    fixed_bulky_matches = _count_matched_phrases(text, _FIXED_BULKY_PHRASES)
    awkward_matches = _count_matched_phrases(text, _AWKWARD_ITEM_PHRASES)
    structured_bulky_matches = min(max(int(mattresses_count), 0) + max(int(box_springs_count), 0), 2)
    total_signal_count = fixed_bulky_matches + awkward_matches + structured_bulky_matches

    if total_signal_count >= 3 or (fixed_bulky_matches + structured_bulky_matches >= 2 and awkward_matches >= 1):
        return 60.0
    if total_signal_count >= 2:
        return 35.0
    return 0.0


def calculate_quote(
    service_type: str,
    hours: float,
    *,
    crew_size: int = 1,
    garbage_bag_count: int = 0,
    bag_type: str | None = None,
    trailer_fill_estimate: str | None = None,
    trailer_class: str | None = None,
    mattresses_count: int = 0,
    box_springs_count: int = 0,
    scrap_pickup_location: str = "curbside",
    travel_zone: str = "in_town",
    access_difficulty: str = "normal",
    has_dense_materials: bool = False,
    load_mode: str | None = "standard",
    internal_risk_assessment: dict[str, Any] | None = None,
    description: str | None = None,
    job_description_customer: str | None = None,
    pickup_address: str | None = None,
    dropoff_address: str | None = None,
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
    normalized_load_mode = _normalize_load_mode(load_mode)
    signal_text = _normalized_signal_text(job_description_customer, description)
    route_complete = bool(str(pickup_address or "").strip() and str(dropoff_address or "").strip())

    # ------------------------------------------------------------
    # Scrap pickup uses location-specific base inputs, but the
    # quoted customer total still respects the universal minimum.
    # ------------------------------------------------------------
    if normalized == "scrap_pickup":
        scrap_base = SCRAP_INSIDE_BASE_CAD if str(scrap_pickup_location) == "inside" else SCRAP_CURBSIDE_BASE_CAD
        cash_total = max(float(scrap_base), GLOBAL_MIN_TOTAL_CAD)
        emt_total = round(cash_total * (1.0 + tax["emt"]), 2)

        return {
            "service_type": normalized,
            "total_cash_cad": round(cash_total, 2),
            "total_emt_cad": round(emt_total, 2),
            "disclaimer": (
                "Scrap pickup is included as part of the minimum service charge, covering labor, "
                "travel, and handling. Cash is tax-free; EMT/e-transfer adds 13% HST."
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
                "risk_margin_protection_cad": 0.0,
                "risk_margin_protection_flags": [],
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

    small_move_enclosed_trailer_adder = 0.0
    if normalized == "small_move":
        trailer_class_key = str(trailer_class or "").strip().lower()
        if trailer_class_key in _ENCLOSED_TRAILER_CLASSES:
            small_move_enclosed_trailer_adder = _get_enclosed_trailer_adder(svc)

    disposal_allowance = 0.0
    small_load_protected = False
    if normalized == "haul_away":
        _bag_count = int(garbage_bag_count)
        if 1 <= _bag_count <= SMALL_LOAD_MAX_BAGS and not bool(has_dense_materials):
            # Small-load protection: scale disposal proportionally for tiny light loads.
            # Dense materials always fall through to the full tier (margin preserved).
            if _bag_count == 1:
                disposal_allowance = SMALL_LOAD_DISPOSAL_SINGLE_BAG
            elif _bag_count == 2:
                disposal_allowance = SMALL_LOAD_DISPOSAL_TWO_BAGS
            else:
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
            if (
                not bool(has_dense_materials)
                and MID_BAND_START_BAGS <= _bag_count <= MID_BAND_END_BAGS
            ):
                disposal_allowance += float(_bag_count - MID_BAND_START_BAGS) * MID_BAND_ADDER_PER_BAG
        if bool(has_dense_materials) and _bag_count > 24:
            disposal_allowance = disposal_allowance * _get_haul_away_dense_disposal_multiplier(svc)

    mattress_boxspring = 0.0
    if normalized == "haul_away" and (int(mattresses_count) > 0 or int(box_springs_count) > 0):
        mattress_boxspring = _mattress_boxspring_fee(svc, int(mattresses_count), int(box_springs_count))

    pre_access_subtotal = travel + labor + disposal_allowance + mattress_boxspring + small_move_enclosed_trailer_adder

    item_delivery_protected_base_floor = 0.0
    item_delivery_enclosed_trailer_adder = 0.0
    if normalized == "item_delivery":
        trailer_class_key = str(trailer_class or "").strip().lower()
        if trailer_class_key in _ENCLOSED_TRAILER_CLASSES:
            item_delivery_enclosed_trailer_adder = _get_enclosed_trailer_adder(svc)
        item_delivery_protected_base_floor = _get_item_delivery_protected_base_floor(svc)
        pre_access_subtotal = max(pre_access_subtotal, item_delivery_protected_base_floor)
        pre_access_subtotal += item_delivery_enclosed_trailer_adder

    raw_cash = pre_access_subtotal + access_adder

    min_total = _get_min_total(svc)
    cash_before_round = max(raw_cash, min_total, GLOBAL_MIN_TOTAL_CAD)

    bag_type_floor = 0.0
    trailer_fill_floor = 0.0
    awkward_small_load_floor = 0.0
    fixed_bulky_floor = 0.0
    multi_stop_complexity_adder = 0.0
    disassembly_complexity_adder = 0.0
    small_load_bulky_trap_adder = 0.0
    operational_complexity_adder = 0.0
    if normalized == "haul_away":
        bag_type_floor = _haul_away_bag_type_floor(svc, bag_type, int(garbage_bag_count))
        trailer_fill_floor = _haul_away_trailer_class_fill_floor(svc, trailer_class, trailer_fill_estimate)
        awkward_small_load_floor = _haul_away_access_difficulty_small_load_floor(svc, _ad, small_load_protected)
        cash_before_round = max(cash_before_round, bag_type_floor, trailer_fill_floor, awkward_small_load_floor)

        if normalized_load_mode == "space_fill":
            trailer_class_idx = _space_fill_class_from_trailer_fill(trailer_fill_estimate)
            bag_class_idx = _space_fill_class_from_bag_count(int(garbage_bag_count))
            inferred_size_class = max(trailer_class_idx, bag_class_idx)
            if inferred_size_class < 3:
                discounted_cash = float(cash_before_round) * 0.8
                space_fill_floor = _space_fill_floor_for_class(inferred_size_class)
                cash_before_round = max(discounted_cash, space_fill_floor)

        fixed_bulky_floor = _haul_away_fixed_bulky_floor(
            access_difficulty=_ad,
            text=signal_text,
            mattresses_count=int(mattresses_count),
            box_springs_count=int(box_springs_count),
            garbage_bag_count=int(garbage_bag_count),
        )
        cash_before_round = max(cash_before_round, fixed_bulky_floor)
        small_load_bulky_trap_adder = _small_load_bulky_trap_adder(
            text=signal_text,
            garbage_bag_count=int(garbage_bag_count),
            mattresses_count=int(mattresses_count),
            box_springs_count=int(box_springs_count),
        )

    multi_stop_complexity_adder = _multi_stop_complexity_adder(
        route_complete=route_complete,
        service_type=normalized,
        travel_zone=tz,
        access_difficulty=_ad,
        text=signal_text,
    )
    disassembly_complexity_adder = _disassembly_complexity_adder(
        access_difficulty=_ad,
        text=signal_text,
    )
    operational_complexity_adder = max(multi_stop_complexity_adder, disassembly_complexity_adder)
    cash_before_round += operational_complexity_adder + small_load_bulky_trap_adder

    risk_margin_protection_cad, risk_margin_protection_flags = _risk_margin_protection(internal_risk_assessment)
    cash_before_round += risk_margin_protection_cad
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
            "pre_access_subtotal_cad": round(float(pre_access_subtotal), 2),
            "raw_cash_cad": round(float(raw_cash), 2),
            "min_total_cad": round(float(min_total), 2),
            "cash_before_round_cad": round(float(cash_before_round), 2),
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
            "small_move_enclosed_trailer_adder_cad": round(float(small_move_enclosed_trailer_adder), 2),
            "item_delivery_protected_base_floor_cad": round(float(item_delivery_protected_base_floor), 2),
            "item_delivery_enclosed_trailer_adder_cad": round(float(item_delivery_enclosed_trailer_adder), 2),
            "bag_type": bag_type,
            "bag_type_floor_cad": round(float(bag_type_floor), 2),
            "trailer_fill_estimate": trailer_fill_estimate,
            "trailer_class": trailer_class,
            "trailer_fill_floor_cad": round(float(trailer_fill_floor), 2),
            "awkward_small_load_floor_cad": round(float(awkward_small_load_floor), 2),
            "fixed_bulky_floor_cad": round(float(fixed_bulky_floor), 2),
            "access_difficulty": _ad,
            "access_difficulty_adder_cad": round(float(access_adder), 2),
            "multi_stop_complexity_adder_cad": round(float(multi_stop_complexity_adder), 2),
            "disassembly_complexity_adder_cad": round(float(disassembly_complexity_adder), 2),
            "operational_complexity_adder_cad": round(float(operational_complexity_adder), 2),
            "small_load_bulky_trap_adder_cad": round(float(small_load_bulky_trap_adder), 2),
            "risk_margin_protection_cad": round(float(risk_margin_protection_cad), 2),
            "risk_margin_protection_flags": risk_margin_protection_flags,
        },
    }
