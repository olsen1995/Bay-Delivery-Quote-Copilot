from __future__ import annotations

from typing import Dict, Any


def _normalize_job_type(job_type: str) -> str:
    """
    Align analysis-driven job types with canonical service types.
    """
    aliases = {
        "dump_run": "haul_away",
        "junk_removal": "haul_away",
        "junk": "haul_away",
        "haulaway": "haul_away",
        "moving": "small_move",
        "delivery": "item_delivery",
    }
    return aliases.get(job_type, job_type)


def _infer_scrap_location(analysis: Dict[str, Any]) -> str:
    """
    Scrap rule is NOT difficulty-based; it’s location-based.
    We infer as best we can from analysis fields.
    """
    # Direct explicit fields (preferred)
    for key in ("scrap_pickup_location", "pickup_location", "location"):
        val = analysis.get(key)
        if isinstance(val, str) and val.lower() in ("curbside", "outside"):
            return "curbside"
        if isinstance(val, str) and val.lower() in ("inside", "indoors", "in_home", "in-house"):
            return "inside"

    # Boolean hints
    if analysis.get("inside") is True:
        return "inside"
    if analysis.get("curbside") is True or analysis.get("outside") is True:
        return "curbside"

    # Fallback: if model marked difficulty as anything other than easy,
    # assume inside (safer for pricing).
    difficulty = str(analysis.get("difficulty", "easy")).lower()
    if difficulty in ("moderate", "hard"):
        return "inside"

    return "curbside"


def calculate_quote(analysis: dict) -> dict:
    """
    Analysis-based estimator.
    IMPORTANT: This must not contradict the main quote tool rules.

    Output is compatible with existing callers:
      {
        "job_type": ...,
        "estimated_price": ...,
        "breakdown": {...}
      }

    We do NOT output dump/disposal as a separate customer-facing dollar line.
    If we include a disposal allowance, it is rolled into the estimated_price.
    """
    if "error" in analysis:
        return {
            "error": "Cannot calculate quote due to analysis error",
            "details": analysis,
        }

    job_type = _normalize_job_type(str(analysis.get("job_type", "haul_away")))
    difficulty = str(analysis.get("difficulty", "easy")).lower()
    heavy_items = analysis.get("heavy_items", []) or []
    volume = float(analysis.get("estimated_volume_cubic_yards", 0) or 0)

    # Shared minimums (keep conservative)
    minimum_charge = 50.0
    wear_and_tear = 20.0

    difficulty_multiplier = {
        "easy": 1.0,
        "moderate": 1.2,
        "hard": 1.5,
    }.get(difficulty, 1.0)

    # -----------------------
    # Gas scaling (kept)
    # -----------------------
    if volume <= 1:
        gas_fee = 30.0
    elif volume <= 3:
        gas_fee = 40.0
    else:
        gas_fee = 60.0

    if difficulty == "hard":
        gas_fee += 20.0

    # -----------------------
    # Scrap pickup (hard lock)
    # -----------------------
    if job_type == "scrap_pickup":
        loc = _infer_scrap_location(analysis)
        price = 30.0 if loc == "inside" else 0.0
        return {
            "job_type": "scrap_pickup",
            "estimated_price": round(price, 2),
            "breakdown": {
                "pricing_model": "flat_rate",
                "location": loc,
                "note": "Curbside scrap is free (picked up next time we’re in the area). Inside removal is $30.",
            },
        }

    # -----------------------
    # Haul away (junk/dump)
    # -----------------------
    if job_type == "haul_away":
        # Per-yard baseline estimate (kept for smart estimator only)
        base_rate_per_yard = 90.0
        heavy_item_fee = 35.0

        base_cost = volume * base_rate_per_yard

        # Mattress/Box Spring rule (ONLY special callout we keep)
        mattress_count = sum(
            1 for item in heavy_items
            if "mattress" in str(item).lower() or "box spring" in str(item).lower()
        )
        mattress_fee = float(mattress_count * 50.0)

        # Prevent double charging
        other_heavy_items = [
            item for item in heavy_items
            if "mattress" not in str(item).lower() and "box spring" not in str(item).lower()
        ]
        heavy_cost = float(len(other_heavy_items) * heavy_item_fee)

        # Disposal allowance (hidden; included in total only)
        # We infer bags from volume if the analyzer didn't give bag_count.
        bag_count = analysis.get("garbage_bag_count")
        if bag_count is None:
            # crude mapping: ~5 bags per cubic yard (conservative)
            bag_count = int(round(volume * 5))

        if bag_count <= 0:
            disposal_allowance = 0.0
        elif bag_count <= 5:
            disposal_allowance = 50.0
        elif bag_count <= 15:
            disposal_allowance = 80.0
        else:
            disposal_allowance = 120.0

        subtotal = (base_cost + heavy_cost + mattress_fee) * difficulty_multiplier
        total = subtotal + gas_fee + wear_and_tear + disposal_allowance
        final_price = max(total, minimum_charge)

        return {
            "job_type": "haul_away",
            "estimated_price": round(final_price, 2),
            "breakdown": {
                "volume_cost": round(base_cost, 2),
                "heavy_item_cost": round(heavy_cost, 2),
                "mattress_fee_included": round(mattress_fee, 2),
                "difficulty_multiplier": difficulty_multiplier,
                "gas_fee": round(gas_fee, 2),
                "wear_and_tear": round(wear_and_tear, 2),
                "disposal_included": True,
                "note": "Removal & disposal included (if required). Mattress/box spring may add disposal cost.",
            },
        }

    # -----------------------
    # Small move (estimate)
    # -----------------------
    if job_type == "small_move":
        hourly_rate = 80.0
        minimum_hours = 4.0  # your standard
        estimated_hours = float(analysis.get("estimated_hours", minimum_hours) or minimum_hours)
        billable_hours = max(estimated_hours, minimum_hours)

        subtotal = (billable_hours * hourly_rate) * difficulty_multiplier
        final_price = subtotal + gas_fee + wear_and_tear

        return {
            "job_type": "small_move",
            "estimated_price": round(final_price, 2),
            "breakdown": {
                "estimated_hours": round(billable_hours, 2),
                "hourly_rate": hourly_rate,
                "difficulty_multiplier": difficulty_multiplier,
                "gas_fee": round(gas_fee, 2),
                "wear_and_tear": round(wear_and_tear, 2),
            },
        }

    # -----------------------
    # Item delivery (estimate)
    # -----------------------
    if job_type == "item_delivery":
        base_delivery = 60.0
        final_price = base_delivery + gas_fee

        return {
            "job_type": "item_delivery",
            "estimated_price": round(final_price, 2),
            "breakdown": {
                "base_delivery": base_delivery,
                "gas_fee": round(gas_fee, 2),
            },
        }

    # -----------------------
    # Demolition (estimate)
    # -----------------------
    if job_type == "demolition":
        hourly_rate = 120.0
        minimum_hours = 2.0
        estimated_hours = float(analysis.get("estimated_hours", minimum_hours) or minimum_hours)
        billable_hours = max(estimated_hours, minimum_hours)

        subtotal = (billable_hours * hourly_rate) * difficulty_multiplier
        final_price = subtotal + gas_fee + wear_and_tear

        return {
            "job_type": "demolition",
            "estimated_price": round(final_price, 2),
            "breakdown": {
                "estimated_hours": round(billable_hours, 2),
                "hourly_rate": hourly_rate,
                "difficulty_multiplier": difficulty_multiplier,
                "gas_fee": round(gas_fee, 2),
                "wear_and_tear": round(wear_and_tear, 2),
            },
        }

    # -----------------------
    # Fallback
    # -----------------------
    return {
        "job_type": job_type,
        "estimated_price": 100.0,
        "breakdown": {"fallback_reason": "Unknown job type"},
    }