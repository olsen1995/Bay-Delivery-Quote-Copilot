def calculate_quote(analysis: dict) -> dict:
    if "error" in analysis:
        return {
            "error": "Cannot calculate quote due to analysis error",
            "details": analysis
        }

    job_type = analysis.get("job_type", "junk_removal")
    difficulty = analysis.get("difficulty", "easy")
    heavy_items = analysis.get("heavy_items", [])
    volume = analysis.get("estimated_volume_cubic_yards", 0)

    minimum_charge = 50
    wear_and_tear = 20

    difficulty_multiplier = {
        "easy": 1.0,
        "moderate": 1.2,
        "hard": 1.5
    }.get(difficulty, 1.0)

    # -----------------------
    # Gas Scaling Logic
    # -----------------------
    if volume <= 1:
        gas_fee = 30
    elif volume <= 3:
        gas_fee = 40
    else:
        gas_fee = 60

    if difficulty == "hard":
        gas_fee += 20

    final_price = 0
    breakdown = {}

    # -----------------------
    # Junk Removal
    # -----------------------
    if job_type == "junk_removal":

        base_rate_per_yard = 90
        heavy_item_fee = 35

        base_cost = volume * base_rate_per_yard

        # Mattress / Box Spring Special Rule
        mattress_count = sum(
            1 for item in heavy_items
            if "mattress" in item.lower() or "box spring" in item.lower()
        )

        mattress_fee = mattress_count * 50

        # Prevent double charging
        other_heavy_items = [
            item for item in heavy_items
            if "mattress" not in item.lower() and "box spring" not in item.lower()
        ]

        heavy_cost = len(other_heavy_items) * heavy_item_fee

        subtotal = (base_cost + heavy_cost + mattress_fee) * difficulty_multiplier
        total = subtotal + gas_fee + wear_and_tear
        final_price = max(total, minimum_charge)

        breakdown = {
            "volume_cost": base_cost,
            "heavy_item_cost": heavy_cost,
            "mattress_fee": mattress_fee,
            "difficulty_multiplier": difficulty_multiplier,
            "gas_fee": gas_fee,
            "wear_and_tear": wear_and_tear,
            "subtotal_before_minimum": round(total, 2)
        }

    # -----------------------
    # Small Moving
    # -----------------------
    elif job_type == "moving":
        hourly_rate = 80
        minimum_hours = 2

        estimated_hours = max(analysis.get("estimated_hours", 2), minimum_hours)

        subtotal = (estimated_hours * hourly_rate) * difficulty_multiplier
        final_price = subtotal + gas_fee + wear_and_tear

        breakdown = {
            "estimated_hours": estimated_hours,
            "hourly_rate": hourly_rate,
            "difficulty_multiplier": difficulty_multiplier,
            "gas_fee": gas_fee,
            "wear_and_tear": wear_and_tear
        }

    # -----------------------
    # Marketplace Delivery
    # -----------------------
    elif job_type == "delivery":
        base_delivery = 60
        final_price = base_delivery + gas_fee

        breakdown = {
            "base_delivery": base_delivery,
            "gas_fee": gas_fee
        }

    # -----------------------
    # Scrap Pickup
    # -----------------------
    elif job_type == "scrap_pickup":
        if difficulty == "easy":
            final_price = 30
        elif difficulty == "moderate":
            final_price = 60
        else:
            final_price = 100

        breakdown = {
            "difficulty": difficulty
        }

    # -----------------------
    # Fallback
    # -----------------------
    else:
        final_price = 100
        breakdown = {
            "fallback_reason": "Unknown job type"
        }

    return {
        "job_type": job_type,
        "estimated_price": round(final_price, 2),
        "breakdown": breakdown
    }
